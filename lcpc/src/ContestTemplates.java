import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import org.json.*;
import java.nio.file.*;
import java.io.*;
import java.util.*;

/** Private, server-generated templates. Never accepts serialized uploads or copies runs/accounts. */
public class ContestTemplates {
 static String sha(Path file)throws Exception{return HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file)));}
 static JSONObject exportTemplate(DashboardBridge s,boolean include)throws Exception{
  Path dir=s.privateBase.resolve("template-exports");Files.createDirectories(dir);Path file=dir.resolve(UUID.randomUUID()+".bin");
  Problem[] problems=include?s.model().getProblems():new Problem[0];
  ProblemDataFiles[] data=Arrays.stream(problems).map(p->s.model().getProblemDataFile(p)).toArray(ProblemDataFiles[]::new);
  for(Problem p:problems)DashboardBridge.require(!p.isUsingExternalDataFiles(),"Template export requires embedded judge data");
  try(ObjectOutputStream out=new ObjectOutputStream(Files.newOutputStream(file,StandardOpenOption.CREATE_NEW))){out.writeObject(problems);out.writeObject(data);}
  JSONArray languages=new JSONArray();for(Language l:s.model().getLanguages())languages.put(new JSONObject().put("name",l.getDisplayName()).put("active",l.isActive()).put("compilerCmd",l.getCompileCommandLine()).put("execCmd",l.getProgramExecuteCommandLine()).put("exemask",l.getExecutableIdentifierMask()));
  return new JSONObject().put("path",file.toString()).put("sha256",sha(file)).put("languages",languages);
 }
 static JSONObject install(DashboardBridge s)throws Exception{
  DashboardBridge.require(!s.model().getContestTime().isContestRunning()&&s.model().getContestTime().getElapsedSecs()==0&&s.getContest().getRuns().length==0&&(s.model().getProblems().length==0||Files.exists(s.privateBase.resolve("installing"))),"Only an empty or explicitly recovering, unstarted contest may be initialized");
  ContestVerdicts.configure(s);
  JSONObject draft=new JSONObject(Files.readString(s.privateBase.resolve("draft.json")));Path file=s.privateBase.resolve("template.bin");
  DashboardBridge.require(sha(file).equals(draft.getString("templateSha256")),"Template integrity check failed");
  Problem[] templates;ProblemDataFiles[] files;
  try(ObjectInputStream in=new ObjectInputStream(Files.newInputStream(file))){in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("maxdepth=100;maxrefs=1000000;maxbytes=134217728;*"));templates=(Problem[])in.readObject();files=(ProblemDataFiles[])in.readObject();}
  JSONObject ids=new JSONObject();JSONArray rows=draft.getJSONArray("problems");List<Problem> created=new ArrayList<>();List<ProblemDataFiles> data=new ArrayList<>();
  for(int n=0;n<rows.length();n++){
   JSONObject row=rows.getJSONObject(n);String old=row.getString("id");Problem p=null;ProblemDataFiles f=null;
   String shortName=row.getString("shortName");Problem existing=Arrays.stream(s.model().getProblems()).filter(x->shortName.equals(x.getShortName())).findFirst().orElse(null);
   if(existing!=null){
    DashboardBridge.require(existing.getDisplayName().equals(row.getString("name"))&&existing.getLetter().equals(row.getString("letter"))&&existing.getTimeOutInSeconds()==row.getInt("timeLimit")&&existing.getMemoryLimitMB()==row.getInt("memoryLimit")&&JudgingWorkflow.mode(existing).equals(draft.getString("workflow")),"Partial problem settings differ from the draft; review recovery before continuing");
    if(row.has("tests"))DashboardBridge.require(existing.getNumberTestCases()==row.getInt("tests"),"Partial judge data differs from the draft");
    ids.put(old,existing.getElementId().toString());continue;
   }
   for(int k=0;k<templates.length;k++)if(templates[k].getElementId().toString().equals(row.optString("sourceId",old))){p=templates[k].copy(row.getString("name"));p.setElementId(new Problem(row.getString("name")).getElementId());p.removeAllTestCaseFilenames();for(int test=1;test<=templates[k].getNumberTestCases();test++)p.addTestCaseFilenames(templates[k].getDataFileName(test),templates[k].getAnswerFileName(test));p.setDataFileName(templates[k].getDataFileName());p.setAnswerFileName(templates[k].getAnswerFileName());f=files[k].copy(p);break;}
   if(p==null){p=new Problem(row.getString("name"));p.setReadInputDataFromSTDIN(true);p.setUsingExternalDataFiles(false);p.setSandboxType(Problem.SandboxType.PC2_INTERNAL_SANDBOX);p.setSandboxProgramName("pc2sandbox.sh");p.setSandboxCmdLine("./{:sandboxprogramname} {:memlimit} {:timelimit}");f=new ProblemDataFiles(p);p.setStopOnFirstFailedTestCase(true);p.setMaxOutputSizeKB(1024);edu.csus.ecs.pc2.validator.clicsValidator.ClicsValidatorSettings validator=new edu.csus.ecs.pc2.validator.clicsValidator.ClicsValidatorSettings();validator.setCaseSensitive(true);validator.setSpaceSensitive(false);validator.disableFloatRelativeTolerance();validator.disableFloatAbsoluteTolerance();p.setCLICSValidatorSettings(validator);p.setValidatorType(Problem.VALIDATOR_TYPE.CLICSVALIDATOR);}
   p.setDisplayName(row.getString("name"));p.setLetter(row.getString("letter"));p.setShortName(row.getString("shortName"));p.setTimeOutInSeconds(row.getInt("timeLimit"));p.setMemoryLimitMB(row.getInt("memoryLimit"));p.setActive(row.getBoolean("active"));if(!row.optString("colorName","").isBlank())ProblemColors.apply(p,row);JudgingWorkflow.apply(p,draft.getString("workflow"));
   if(row.has("dataDirectory")){
    Path dir=s.privateBase.resolve("judge-data").resolve(row.getString("dataDirectory")).toRealPath();DashboardBridge.require(dir.startsWith(s.privateBase.resolve("judge-data").toRealPath()),"Invalid test directory");
    List<Path> inputs;try(var stream=Files.list(dir)){inputs=stream.filter(x->x.getFileName().toString().endsWith(".in")).sorted().toList();}DashboardBridge.require(inputs.size()>0&&inputs.size()<=250,"Missing judge tests");
    p.removeAllTestCaseFilenames();List<SerializedFile> ins=new ArrayList<>(),ans=new ArrayList<>();
    for(Path input:inputs){String name=input.getFileName().toString(),answer=name.replaceFirst("\\.in$",".ans");p.addTestCaseFilenames(name,answer);ins.add(new SerializedFile(name,Files.readAllBytes(input)));ans.add(new SerializedFile(answer,Files.readAllBytes(dir.resolve(answer))));}
    p.setDataFileName(inputs.get(0).getFileName().toString());p.setAnswerFileName(inputs.get(0).getFileName().toString().replaceFirst("\\.in$",".ans"));f.setJudgesDataFiles(ins.toArray(new SerializedFile[0]));f.setJudgesAnswerFiles(ans.toArray(new SerializedFile[0]));
   }
   JudgeGuardPolicy.verify(p,s.model().getLanguages()[0]);ids.put(old,p.getElementId().toString());created.add(p);data.add(f);
  }
  if(!created.isEmpty())s.control().addNewProblem(created.toArray(new Problem[0]),data.toArray(new ProblemDataFiles[0]));
  for(int n=0;n<100&&s.model().getProblems().length!=rows.length();n++)Thread.sleep(100);
  DashboardBridge.require(s.model().getProblems().length==rows.length(),"Problem installation was not confirmed");
  List<Account> accounts=new ArrayList<>();
  for(int n=0;n<draft.getJSONArray("teams").length();n++){JSONObject t=draft.getJSONArray("teams").getJSONObject(n);int number=t.optInt("number",n+1);DashboardBridge.require(number>0&&number<=TestTeamPolicy.NUMBER,"Invalid team number");DashboardBridge.require(number!=TestTeamPolicy.NUMBER||t.optBoolean("testAccount",false),"Reserved test account collision");accounts.add(TestTeamPolicy.account(s.model().getSiteNumber(),number,t.getString("name"),t.getString("password"),t.optBoolean("enabled",true),t.optBoolean("visible",true)));}
  // The singular PC2 packet generates a new number; the array packet preserves IDs.
  DashboardBridge.require(Arrays.stream(s.model().getAccounts()).filter(a->a.isTeam()).allMatch(a->accounts.stream().anyMatch(want->want.getClientId().equals(a.getClientId()))),"Unexpected accounts in an incomplete installation; review them before recovery");
  s.control().updateAccounts(accounts.toArray(new Account[0]));
  for(int n=0;n<100&&!accountsConfirmed(s,accounts);n++)Thread.sleep(100);
  DashboardBridge.require(accountsConfirmed(s,accounts),"Team installation was not confirmed");
  applySettings(s,draft);
  JSONObject receipt=new JSONObject().put("draftSha256",sha(s.privateBase.resolve("draft.json"))).put("problemIds",ids);
  Path temporary=s.privateBase.resolve("installation-receipt.tmp");Files.writeString(temporary,receipt.toString());Files.move(temporary,s.privateBase.resolve("installation-receipt.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
  return new JSONObject().put("ok",true).put("problemIds",ids);
 }
 static boolean accountsConfirmed(DashboardBridge s,List<Account> wanted){
  return Arrays.stream(s.model().getAccounts()).filter(a->a.isTeam()).count()==wanted.size()&&wanted.stream().allMatch(a->{Account actual=s.model().getAccount(a.getClientId());return actual!=null&&actual.getDisplayName().equals(a.getDisplayName())&&actual.getPassword().equals(a.getPassword());});
 }
 static void applySettings(DashboardBridge s,JSONObject draft)throws Exception{
  ClientId judge=new ClientId(s.model().getSiteNumber(),ClientType.Type.JUDGE,1);ClientSettings settings=s.model().getClientSettings(judge);boolean newSettings=settings==null;if(newSettings)settings=new ClientSettings(judge);Filter filter=new Filter();filter.setUsingProblemFilter(false);filter.setUsingLanguageFilter(false);filter.setUsingRunStatesFilter(true);filter.addRunState(Run.RunStates.QUEUED_FOR_COMPUTER_JUDGEMENT);settings.setAutoJudgeFilter(filter);settings.setAutoJudging(!draft.getString("workflow").equals("human"));if(newSettings)s.control().addNewClientSettings(settings);else s.control().updateClientSettings(settings);
  JSONObject c=draft.getJSONObject("contest");ContestInformation info=s.model().getContestInformation();info.setContestTitle(c.getString("title"));info.setContestShortName(c.getString("shortName"));info.setFreezeTime(c.getString("freezeRemaining"));info.setAutoStartContest(false);info.setAutoStopContest(true);JudgingWorkflow.holdPreliminaryResults(info);
  if(!c.optString("scheduledStart").isBlank()){java.time.Instant instant=java.time.Instant.parse(c.getString("scheduledStart"));info.setScheduledStartDate(Date.from(instant));info.setScheduledStartTime(GregorianCalendar.from(instant.atZone(java.time.ZoneId.of(draft.getString("timeZone")))));}
  Properties scoring=DefaultScoringAlgorithm.getDefaultProperties();scoring.putAll(info.getScoringProperties());scoring.setProperty(DefaultScoringAlgorithm.POINTS_PER_NO,String.valueOf(draft.getInt("penaltyMinutes")));info.setScoringProperties(scoring);s.control().updateContestInformation(info);
  ContestTime time=s.model().getContestTime();time.setContestLengthSecs(c.getLong("lengthSeconds"));time.setHaltContestAtTimeZero(true);s.control().updateContestTime(time);Thread.sleep(500);
 }
}
