import edu.csus.ecs.pc2.api.*;
import edu.csus.ecs.pc2.core.*;
import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.security.Permission;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Local JSON pipe for the dashboard. PC2 remains the authority for contest state. */
public class DashboardBridge extends ServerConnection {
  Path privateBase;
  edu.csus.ecs.pc2.core.model.IInternalContest model(){return internalContest;}
  edu.csus.ecs.pc2.core.IInternalController control(){return controller;}
  static final String PREFIX="LCPC_JSON ";
  static void require(boolean value,String message){if(!value)throw new IllegalArgumentException(message);}
  static Properties load(Path path)throws Exception{Properties p=new Properties();try(InputStream in=Files.newInputStream(path)){p.load(in);}return p;}
  static String text(JSONObject a,String key,int max)throws JSONException{String s=a.getString(key).trim();require(!s.isEmpty()&&s.length()<=max&&!s.contains("\0"),"Invalid "+key);return s;}
  static long number(JSONObject a,String key,long min,long max)throws JSONException{long n=a.getLong(key);require(n>=min&&n<=max,"Invalid "+key);return n;}
  Problem problem(String id){return Arrays.stream(internalContest.getProblems()).filter(p->p.getElementId().toString().equals(id)).findFirst().orElseThrow(()->new IllegalArgumentException("Problem not found"));}
  Account team(String login){require(login.matches("team[1-9][0-9]{0,5}"),"Invalid team");return Arrays.stream(internalContest.getAccounts()).filter(a->a.getClientId().getName().equals(login)).findFirst().orElseThrow(()->new IllegalArgumentException("Team not found"));}
  IRun run(JSONObject a)throws Exception{int n=a.getInt("number");return Arrays.stream(getContest().getRuns()).filter(r->r.getNumber()==n&&r.getSiteNumber()==a.optInt("site",1)).findFirst().orElseThrow(()->new IllegalArgumentException("Submission not found"));}
  RunResultFiles[] fetchSavedReports(Run raw)throws Exception{
    // PC2's in-memory client keeps a single result-file slot. Fetch explicitly for
    // each read and capture the matching event, rather than reusing source caches.
    java.util.concurrent.CountDownLatch ready=new java.util.concurrent.CountDownLatch(1);
    java.util.concurrent.atomic.AtomicReference<RunResultFiles[]> saved=new java.util.concurrent.atomic.AtomicReference<>();
    IRunListener listener=new IRunListener(){
      public void runAdded(RunEvent e){runChanged(e);}
      public void runChanged(RunEvent e){if(e.getRun()!=null&&e.getRunFiles()!=null&&raw.getElementId().equals(e.getRun().getElementId())){saved.set(e.getRunResultFiles());ready.countDown();}}
      public void runRemoved(RunEvent e){}public void refreshRuns(RunEvent e){}
    };
    internalContest.addRunListener(listener);
    try{
      ClientId client=internalContest.getClientId();
      // InternalController.fetchRun may return cached source without fetching its
      // discarded result slot. Use the same read-only FETCH_RUN packet directly.
      controller.sendToLocalServer(edu.csus.ecs.pc2.core.packet.PacketFactory.createFetchRun(client,new ClientId(internalContest.getSiteNumber(),ClientType.Type.SERVER,0),raw,client));require(ready.await(20,java.util.concurrent.TimeUnit.SECONDS),"Saved judge files were not returned in time");
      RunResultFiles[] files=saved.get();if(files==null)files=internalContest.getRunResultFiles(raw);
      return files==null?null:Arrays.stream(files).filter(f->f!=null&&raw.getElementId().equals(f.getRunId())).toArray(RunResultFiles[]::new);
    }finally{internalContest.removeRunListener(listener);}
  }
  void commitJudgement(Run raw,Judgement judgement)throws Exception{
    // The bundled API mutates the run before sending RUN_UPDATE. Its server
    // then tries to load a result file for that not-yet-stored judgement and
    // rejects the update. Send the existing record history and the new decision
    // separately, and acknowledge only the server's persisted update event.
    Run updated=AdministratorFeatures.copy(raw);
    JudgementRecord decision=new JudgementRecord(judgement.getElementId(),model().getClientId(),
        Judgement.ACRONYM_ACCEPTED.equals(judgement.getAcronym()),false);
    decision.setPreliminaryJudgement(false);decision.setSendToTeam(true);
    if(raw.getComputerJudgementRecord()!=null)decision.setPreviousComputerJudgementId(raw.getComputerJudgementRecord().getElementId());
    updated.setStatus(Run.RunStates.JUDGED);
    java.util.concurrent.CountDownLatch confirmed=new java.util.concurrent.CountDownLatch(1);
    IRunListener listener=new IRunListener(){
      public void runAdded(RunEvent e){runChanged(e);}
      public void runChanged(RunEvent e){Run r=e.getRun();if(r!=null&&r.getElementId().equals(raw.getElementId())
          &&r.getStatus()==Run.RunStates.JUDGED&&r.getJudgementRecord()!=null
          &&r.getJudgementRecord().getElementId().equals(decision.getElementId()))confirmed.countDown();}
      public void runRemoved(RunEvent e){}public void refreshRuns(RunEvent e){}
    };
    model().addRunListener(listener);
    try{control().updateRun(updated,decision,null);require(confirmed.await(20,java.util.concurrent.TimeUnit.SECONDS),
        "PC2 did not confirm the final judgement. Refresh before retrying.");}
    finally{model().removeRunListener(listener);}
  }
  JSONObject snapshot()throws Exception{
    JSONObject out=new JSONObject();ContestInformation info=internalContest.getContestInformation();ContestTime time=internalContest.getContestTime();
    out.put("contest",new JSONObject().put("title",info.getContestTitle()).put("shortName",info.getContestShortName()).put("running",time.isContestRunning()).put("elapsedSeconds",time.getElapsedSecs()).put("lengthSeconds",time.getContestLengthSecs()).put("remainingSeconds",Math.max(0,time.getContestLengthSecs()-time.getElapsedSecs())).put("freezeRemaining",info.getFreezeTime()).put("thawed",(info.getThawed()!=null)).put("scheduledStart",info.getScheduledStartDate()==null?JSONObject.NULL:info.getScheduledStartDate().toInstant().toString()));
    JSONArray teams=new JSONArray();Set<String> online=new HashSet<>();for(ClientId id:internalContest.getLocalLoggedInClients(ClientType.Type.TEAM))online.add(id.getName());
    for(Account a:internalContest.getAccounts())if(a.isTeam())teams.put(new JSONObject().put("login",a.getClientId().getName()).put("number",a.getClientId().getClientNumber()).put("name",a.getDisplayName()).put("enabled",a.isAllowed(Permission.Type.LOGIN)).put("visible",a.isAllowed(Permission.Type.DISPLAY_ON_SCOREBOARD)).put("online",online.contains(a.getClientId().getName())).put("testAccount",TestTeamPolicy.isTest(a.getClientId())));
    out.put("teams",teams);Set<String> workflows=new HashSet<>();for(Problem p:internalContest.getProblems())workflows.add(JudgingWorkflow.mode(p));out.put("judging",new JSONObject().put("mode",workflows.size()==1?workflows.iterator().next():"mixed").put("preliminaryResultsCounted",info.isPreliminaryJudgementsUsedByBoard()).put("preliminaryNotifications",info.isPreliminaryJudgementsTriggerNotifications()));JSONArray problems=new JSONArray();int index=0;
    for(Problem p:internalContest.getProblems()){String letter=p.getLetter();if(letter==null||letter.isBlank())letter=""+(char)('A'+index);problems.put(new JSONObject().put("id",p.getElementId().toString()).put("letter",letter).put("name",p.getDisplayName()).put("shortName",p.getShortName()).put("timeLimit",p.getTimeOutInSeconds()).put("memoryLimit",p.getMemoryLimitMB()).put("active",p.isActive()).put("tests",p.getNumberTestCases()).put("judgingMode",JudgingWorkflow.mode(p)).put("colorName",p.getColorName()==null?"":p.getColorName()).put("colorRGB",p.getColorRGB()==null?"":p.getColorRGB()));index++;}
    out.put("problems",problems);JSONArray runs=new JSONArray();
    for(IRun r:getContest().getRuns()){
      Run nativeRun=null;long elapsed=0;for(Run raw:internalContest.getRuns())if(raw.getNumber()==r.getNumber()&&raw.getSiteNumber()==r.getSiteNumber()){elapsed=raw.getElapsedMS();nativeRun=raw;break;}
      String pid="";for(Problem p:internalContest.getProblems())if(p.getShortName().equals(r.getProblem().getShortName())){pid=p.getElementId().toString();break;}
      JudgementRecord auto=nativeRun==null?null:nativeRun.getComputerJudgementRecord();Judgement automatic=auto==null?null:internalContest.getJudgement(auto.getJudgementId());
      String workflowState=nativeRun==null?"Pending":JudgingWorkflow.state(nativeRun,r.isFinalJudged());
      runs.put(new JSONObject().put("number",r.getNumber()).put("site",r.getSiteNumber()).put("team",r.getTeam().getLoginName()).put("testAccount",r.getTeam().getLoginName().equals("team"+TestTeamPolicy.NUMBER)).put("teamName",r.getTeam().getDisplayName()).put("problem",r.getProblem().getName()).put("problemId",pid).put("language",r.getLanguage().getName()).put("verdict",r.isFinalJudged()?r.getJudgementName():workflowState).put("final",r.isFinalJudged()).put("preliminary",r.isPreliminaryJudged()).put("automaticVerdict",automatic==null?"":automatic.getDisplayName()).put("workflowState",workflowState).put("accepted",r.isFinalJudged()&&r.isSolved()).put("deleted",r.isDeleted()).put("elapsedMinutes",elapsed/60000.0));
    }out.put("runs",runs);
    JSONArray clarifications=new JSONArray();for(IClarification c:getContest().getClarifications())clarifications.put(new JSONObject().put("number",c.getNumber()).put("site",c.getSiteNumber()).put("team",c.getTeam()==null?"Organizer":c.getTeam().getLoginName()).put("problem",c.getProblem()==null?"General":c.getProblem().getName()).put("question",c.getQuestion()).put("answer",c.getAnswer()==null?"":c.getAnswer()).put("answered",c.isAnswered()).put("all",c.isSendToAll()).put("deleted",c.isDeleted()));
    out.put("clarifications",clarifications);JSONArray languages=new JSONArray();for(Language l:internalContest.getLanguages())languages.put(new JSONObject().put("name",l.getDisplayName()).put("active",l.isActive()));out.put("languages",languages);
    DefaultScoringAlgorithm scoring=new DefaultScoringAlgorithm();scoring.setObeyFreeze(false);
    String xml=scoring.getStandings(internalContest,internalContest.getRuns(),null,info.getScoringProperties(),controller.getLog());out.put("standings",XML.toJSONObject(xml));
    JSONArray judgements=new JSONArray();for(IJudgement j:getContest().getJudgements())judgements.put(new JSONObject().put("name",j.getName()));out.put("judgements",judgements);
    return out.put("updatedAt",java.time.Instant.now().toString());
  }
  JSONObject command(String op,JSONObject a)throws Exception{
    switch(op){
      case "snapshot":return snapshot();
      case "test-team.credentials":{
        Account t=team("team"+TestTeamPolicy.NUMBER);require(TestTeamPolicy.isTest(t.getClientId())&&!t.isAllowed(Permission.Type.DISPLAY_ON_SCOREBOARD),"The managed diagnostic account is unavailable");
        return new JSONObject().put("login",t.getClientId().getName()).put("name",t.getDisplayName()).put("password",t.getPassword());
      }
      case "admin.catalog":return AdministratorFeatures.catalog(this);
      case "admin.query":return AdministratorFeatures.query(this,a);
      case "admin.execute":return AdministratorFeatures.operations(this,a);
      case "admin.report":return AdministratorFeatures.report(this,a);
      case "admin.tests":return AdministratorFeatures.tests(this,a);
      case "admin.logs":return AdministratorFeatures.logs(this,a);
      case "template.export":return ContestTemplates.exportTemplate(this,a.optBoolean("includeProblems",false));
      case "draft.install":return ContestTemplates.install(this);
      case "runtime.shutdown":require(!internalContest.getContestTime().isContestRunning(),"Pause the contest before deactivation");require(Arrays.stream(getContest().getRuns()).allMatch(r->r.isDeleted()||r.isFinalJudged()),"Finalize pending submissions before deactivation");shutdownServer();return new JSONObject().put("ok",true);
      case "source":{
        IRun r=run(a);String[] names=r.getSourceCodeFileNames();byte[][] data=r.getSourceCodeFileContents();JSONArray files=new JSONArray();
        if(data==null||names==null)throw new IllegalStateException("Source is not available from PC2");
        for(int i=0;i<names.length;i++)files.put(new JSONObject().put("name",Path.of(names[i]).getFileName().toString()).put("base64",Base64.getEncoder().encodeToString(data[i])));
        return new JSONObject().put("files",files);
      }
      case "diagnostics":{
        IRun selected=run(a);Run raw=Arrays.stream(internalContest.getRuns()).filter(r->r.getNumber()==selected.getNumber()&&r.getSiteNumber()==selected.getSiteNumber()).findFirst().orElseThrow();Problem p=internalContest.getProblem(raw.getProblemId());
        java.util.function.Function<ElementId,String> verdict=id->{Judgement j=id==null?null:internalContest.getJudgement(id);return j==null?"":j.getDisplayName();};
        JudgementRecord auto=raw.getComputerJudgementRecord();Judgement provisional=auto==null?null:internalContest.getJudgement(auto.getJudgementId());
        JSONObject data=RunDiagnostics.cases(raw,p,selected.isFinalJudged()||selected.isPreliminaryJudged(),verdict).put("number",selected.getNumber()).put("site",selected.getSiteNumber()).put("final",selected.isFinalJudged()).put("preliminary",selected.isPreliminaryJudged()).put("automaticVerdict",provisional==null?"":provisional.getDisplayName()).put("awaitingApproval",raw.getStatus()==Run.RunStates.MANUAL_REVIEW).put("verdict",selected.isFinalJudged()?selected.getJudgementName():JudgingWorkflow.state(raw,false)).put("reports",new JSONArray()).put("reportCount",0);
        if(selected.isFinalJudged()||selected.isPreliminaryJudged())try{
          RunResultFiles[] files=fetchSavedReports(raw);data.put("reports",RunDiagnostics.reports(files,verdict)).put("reportCount",files==null?0:files.length);
        }catch(Exception unavailable){data.put("reportsUnavailable",true);}
        return data;
      }
      case "test-data":{
        IRun selected=run(a);Run raw=Arrays.stream(internalContest.getRuns()).filter(r->r.getNumber()==selected.getNumber()&&r.getSiteNumber()==selected.getSiteNumber()).findFirst().orElseThrow();Problem p=internalContest.getProblem(raw.getProblemId());int test=(int)number(a,"test",1,p.getNumberTestCases());
        return RunDiagnostics.testData(internalContest.getProblemDataFile(p),test);
      }
      case "judging.workflow":{
        require(!internalContest.getContestTime().isContestRunning(),"Pause the contest before changing its judging workflow");
        require(Arrays.stream(getContest().getRuns()).allMatch(r->r.isDeleted()||r.isFinalJudged()),"Finalize all pending submissions before changing the workflow");
        String mode=text(a,"mode",20);require(Set.of("automatic","review","human").contains(mode),"Invalid judging workflow");require(internalContest.getProblems().length>0,"Add a problem first");
        ContestInformation info=internalContest.getContestInformation();JudgingWorkflow.holdPreliminaryResults(info);controller.updateContestInformation(info);
        for(Problem p:internalContest.getProblems()){JudgingWorkflow.apply(p,mode);controller.updateProblem(p);}
        break;
      }
      case "run.approve":{
        require(text(a,"reason",1000).length()>=8,"An approval reason is required");IRun selected=run(a);Run raw=Arrays.stream(internalContest.getRuns()).filter(r->r.getNumber()==selected.getNumber()&&r.getSiteNumber()==selected.getSiteNumber()).findFirst().orElseThrow();
        require(!selected.isDeleted()&&!selected.isFinalJudged()&&raw.getStatus()==Run.RunStates.MANUAL_REVIEW,"This run is not awaiting human approval");
        JudgementRecord automatic=raw.getComputerJudgementRecord();require(automatic!=null,"No automatic verdict is available");Judgement j=internalContest.getJudgement(automatic.getJudgementId());require(j!=null&&j.getDisplayName().equals(text(a,"expectedJudgement",200)),"The automatic verdict changed; refresh before approving");
        commitJudgement(raw,j);break;
      }
      case "clock.start":startContestClock();break;
      case "clock.pause":stopContestClock();break;
      case "clock.extend":{ContestTime t=internalContest.getContestTime();t.setContestLengthSecs(t.getContestLengthSecs()+number(a,"seconds",60,86400));controller.updateContestTime(t);break;}
      case "contest.update":{
        ContestInformation i=internalContest.getContestInformation();
        i.setContestTitle(text(a,"title",200));i.setContestShortName(text(a,"shortName",80));
        String freeze=text(a,"freezeRemaining",12);require(freeze.matches("[0-9]{2,3}:[0-5][0-9]:[0-5][0-9]"),"Use HH:MM:SS for freeze");i.setFreezeTime(freeze);i.setThawed(a.getBoolean("thawed"));
        if(a.has("scheduledStart")&&!a.getString("scheduledStart").isBlank()){java.time.Instant d=java.time.Instant.parse(a.getString("scheduledStart"));i.setScheduledStartDate(Date.from(d));GregorianCalendar c=GregorianCalendar.from(d.atZone(java.time.ZoneId.of(a.optString("scheduleTimeZone","Africa/Tripoli"))));i.setScheduledStartTime(c);}else if(a.has("scheduledStart")){i.setScheduledStartDate(null);i.setScheduledStartTime(null);i.setAutoStartContest(false);}
        controller.updateContestInformation(i);break;
      }
      case "team.update":{
        Account t=team(text(a,"login",30));t.setDisplayName(text(a,"name",200));
        if(a.getBoolean("enabled"))t.addPermission(Permission.Type.LOGIN);else t.removePermission(Permission.Type.LOGIN);
        if(a.getBoolean("visible")&&!TestTeamPolicy.isTest(t.getClientId()))t.addPermission(Permission.Type.DISPLAY_ON_SCOREBOARD);else t.removePermission(Permission.Type.DISPLAY_ON_SCOREBOARD);
        if(a.has("password")&&!a.getString("password").isEmpty()){String password=text(a,"password",128);require(password.length()>=16,"Use at least 16 characters");t.setPassword(password);}
        controller.updateAccount(t);break;
      }
      case "team.create":{
        String name=text(a,"name",200),password=text(a,"password",128);require(password.length()>=16,"Use at least 16 characters");controller.addNewAccount(TestTeamPolicy.account(internalContest.getSiteNumber(),TestTeamPolicy.nextNumber(internalContest),name,password,true,true));break;
      }
      case "problem.update":{
        Problem p=AdministratorFeatures.copy(problem(text(a,"id",240)));boolean colorChanged=ProblemColors.apply(p,a);p.setDisplayName(text(a,"name",200));p.setTimeOutInSeconds((int)number(a,"timeLimit",1,10));p.setMemoryLimitMB((int)number(a,"memoryLimit",32,1024));p.setActive(a.getBoolean("active"));JudgeGuardPolicy.verify(p,internalContest.getLanguages()[0]);controller.updateProblem(p);if(colorChanged)ProblemColors.sync(this,p);break;
      }
      case "problem.create":{
        require(!internalContest.getContestTime().isContestRunning(),"Pause the contest before adding a judged problem");
        String name=text(a,"name",200),letter=text(a,"letter",3);require(letter.matches("[A-Z]{1,3}"),"Use an uppercase problem letter");
        require(Arrays.stream(internalContest.getProblems()).noneMatch(p->letter.equals(p.getLetter())),"Problem letter is already in use");
        Problem template=problem(text(a,"template",240));Problem p=template.copy(name);p.setElementId(new Problem(name).getElementId());p.setShortName("P"+UUID.randomUUID().toString().replace("-", "").substring(0,16));p.setLetter(letter);p.setDisplayName(name);p.setTimeOutInSeconds((int)number(a,"timeLimit",1,10));p.setMemoryLimitMB((int)number(a,"memoryLimit",32,1024));p.setActive(false);p.setUsingExternalDataFiles(false);p.removeAllTestCaseFilenames();ProblemColors.apply(p,a);
        Path directory=Path.of(text(a,"directory",1024)).toRealPath();require(directory.startsWith(privateBase.resolve("judge-data").toRealPath()),"Invalid judge data directory");
        List<Path> inputs;try(var files=Files.list(directory)){inputs=files.filter(f->f.getFileName().toString().endsWith(".in")).sorted().toList();}
        require(!inputs.isEmpty()&&inputs.size()<=250,"Use 1–250 test pairs");List<SerializedFile> data=new ArrayList<>(),answers=new ArrayList<>();
        for(Path input:inputs){String base=input.getFileName().toString().replaceFirst("\\.in$","");Path answer=directory.resolve(base+".ans");require(Files.isRegularFile(answer)&&!Files.isSymbolicLink(answer),"A test answer is missing");p.addTestCaseFilenames(input.getFileName().toString(),answer.getFileName().toString());data.add(new SerializedFile(input.getFileName().toString(),Files.readAllBytes(input)));answers.add(new SerializedFile(answer.getFileName().toString(),Files.readAllBytes(answer)));}
        p.setDataFileName(inputs.get(0).getFileName().toString());p.setAnswerFileName(inputs.get(0).getFileName().toString().replaceFirst("\\.in$",".ans"));JudgeGuardPolicy.verify(p,internalContest.getLanguages()[0]);ProblemDataFiles files=internalContest.getProblemDataFile(template).copy(p);files.setJudgesDataFiles(data.toArray(new SerializedFile[0]));files.setJudgesAnswerFiles(answers.toArray(new SerializedFile[0]));controller.addNewProblem(p,files);
        for(int k=0;k<40&&internalContest.getProblem(p.getElementId())==null;k++)Thread.sleep(100);require(internalContest.getProblem(p.getElementId())!=null,"Problem creation was not confirmed");if(a.has("colorName"))ProblemColors.sync(this,p);return new JSONObject().put("ok",true).put("id",p.getElementId().toString());
      }
      case "run.rejudge":{
        require(text(a,"reason",1000).length()>=8,"A rejudge reason is required");IRun selected=run(a);require(selected.isFinalJudged(),"Only a completed submission can be queued for rejudge");
        Run raw=Arrays.stream(internalContest.getRuns()).filter(r->r.getNumber()==selected.getNumber()&&r.getSiteNumber()==selected.getSiteNumber()).findFirst().orElseThrow();require(internalContest.getProblem(raw.getProblemId()).isComputerJudged(),"Automatic rejudging is disabled in human-only mode; set a final human verdict instead");raw.setStatus(Run.RunStates.QUEUED_FOR_COMPUTER_JUDGEMENT);controller.updateRun(raw,null,null);break;
      }
      case "clarification.answer":{
        int n=a.getInt("number");Clarification c=Arrays.stream(internalContest.getClarifications()).filter(x->x.getNumber()==n&&x.getSiteNumber()==a.optInt("site",1)).findFirst().orElseThrow();
        controller.checkOutClarification(c,true);Thread.sleep(200);c.setAnswer(text(a,"answer",8000),internalContest.getClientId(),internalContest.getContestTime(),a.getBoolean("all"));controller.submitClarificationAnswer(c);break;
      }
      case "announcement":{
        String message=text(a,"message",8000);int before=Arrays.stream(internalContest.getClarifications()).mapToInt(Clarification::getNumber).max().orElse(0);
        controller.submitClarification(internalContest.getGeneralProblem(),message);Clarification c=null;
        for(int retry=0;retry<25&&c==null;retry++){Thread.sleep(150);c=Arrays.stream(internalContest.getClarifications()).filter(x->x.getNumber()>before&&x.getQuestion().equals(message)).findFirst().orElse(null);}
        require(c!=null,"Announcement could not be created");controller.checkOutClarification(c,true);Thread.sleep(200);c.setAnswer(message,internalContest.getClientId(),internalContest.getContestTime(),true);controller.submitClarificationAnswer(c);break;
      }
      case "judgement":{
        require(text(a,"reason",1000).length()>=8,"A review reason is required");IRun r=run(a);String decision=a.getString("judgement");Judgement j=Arrays.stream(internalContest.getJudgements()).filter(x->x.getDisplayName().equals(decision)).findFirst().orElseThrow();Run raw=Arrays.stream(internalContest.getRuns()).filter(x->x.getNumber()==r.getNumber()&&x.getSiteNumber()==r.getSiteNumber()).findFirst().orElseThrow();commitJudgement(raw,j);break;
      }
      default:throw new IllegalArgumentException("Unsupported operation");
    }
    Thread.sleep(300);return new JSONObject().put("ok",true);
  }
  public static void main(String[] args){try{serve(args);}catch(Exception e){System.err.println("Dashboard bridge failed: "+e.getClass().getSimpleName());System.exit(1);}}
  static void serve(String[] args)throws Exception{
    PrintStream protocol=System.out;
    Path credentials=Path.of(args[1]);DashboardBridge s=new DashboardBridge();Properties service=load(credentials);s.privateBase=credentials.toAbsolutePath().getParent();
    Properties redactions=LCPCLaunch.secrets();redactions.putAll(service);PrintStream errors=System.err;System.setOut(new PrintStream(new SecretRedactingOutputStream(errors,redactions),true));System.setErr(new PrintStream(new SecretRedactingOutputStream(errors,redactions),true));
    if(args[0].equals("provision")){
      Properties current=LCPCLaunch.secrets();s.login("administrator1",current.getProperty("administrator1"));
      try{
        String username=service.getProperty("username");Account existing=Arrays.stream(s.internalContest.getAccounts()).filter(a->a.getClientId().getName().equals(username)).findFirst().orElse(null);
        if(existing==null){
          int n=Integer.parseInt(username.substring("administrator".length()));
          Account account=new Account(new ClientId(s.internalContest.getSiteNumber(),ClientType.Type.ADMINISTRATOR,n),service.getProperty("password"),s.internalContest.getSiteNumber());
          account.setDisplayName("University Dashboard Service");account.clearListAndLoadPermissions(new PermissionGroup().getPermissionList(ClientType.Type.ADMINISTRATOR));s.controller.addNewAccount(account);
          for(int k=0;k<30&&Arrays.stream(s.internalContest.getAccounts()).noneMatch(a->a.getClientId().getName().equals(username));k++)Thread.sleep(100);
          require(Arrays.stream(s.internalContest.getAccounts()).anyMatch(a->a.getClientId().getName().equals(username)),"Service account creation did not complete");
        }else require(existing.getPassword().equals(service.getProperty("password")),"Service account name already belongs to another account");
        protocol.println(PREFIX+new JSONObject().put("ok",true).put("account",username));
      }finally{s.logoff();}System.exit(0);
    }
    try{s.login(service.getProperty("username"),service.getProperty("password"));protocol.println(PREFIX+new JSONObject().put("ready",true));}
    catch(Exception error){protocol.println(PREFIX+new JSONObject().put("ready",false).put("error","PC2 service login failed"));System.exit(1);}
    Runtime.getRuntime().addShutdownHook(new Thread(()->{try{if(s.isLoggedIn())s.logoff();}catch(Exception ignored){}}));
    BufferedReader in=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));String line;
    while((line=in.readLine())!=null){JSONObject request=null;try{request=new JSONObject(line);JSONObject data=s.command(request.getString("op"),request.optJSONObject("args")==null?new JSONObject():request.getJSONObject("args"));protocol.println(PREFIX+new JSONObject().put("id",request.getString("id")).put("ok",true).put("data",data));}
      catch(Exception error){protocol.println(PREFIX+new JSONObject().put("id",request==null?"":request.optString("id")).put("ok",false).put("error",error instanceof IllegalArgumentException?error.getMessage():"PC2 operation failed: "+error.getClass().getSimpleName()));}}
    s.logoff();System.exit(0);
  }
}
