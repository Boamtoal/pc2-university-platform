import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.IInternalController;
import edu.csus.ecs.pc2.api.*;
import org.json.*;
import java.nio.file.*;
import java.util.*;
import java.lang.reflect.*;

public class ContestTemplatesTest {
 static int checks=0;static void check(boolean ok,String text){checks++;if(!ok)throw new AssertionError(text);}
 static class Fixture extends DashboardBridge {
  InternalContest data=new InternalContest();edu.csus.ecs.pc2.api.implementation.Contest api;IInternalController commands;
  Fixture(Path dir)throws Exception{
   privateBase=dir;Files.createDirectories(dir);data.setClientId(new ClientId(1,ClientType.Type.ADMINISTRATOR,2));ContestTime t=new ContestTime();t.setSiteNumber(1);data.addContestTime(t);data.addContestInformation(new ContestInformation());
   for(var entry:ContestVerdicts.NAMES.entrySet())data.addJudgement(new Judgement(entry.getValue(),entry.getKey()));
   Language l=new Language("C++17");l.setCompileCommandLine("/opt/lcpc/bin/compile17 {:mainfile} {:basename}");l.setProgramExecuteCommandLine("./{:basename}");l.setExecutableIdentifierMask("{:basename}");data.addLanguage(l);
   commands=(IInternalController)Proxy.newProxyInstance(getClass().getClassLoader(),new Class[]{IInternalController.class},(proxy,method,args)->{
    switch(method.getName()){
     case "addNewProblem":Problem[] ps=(Problem[])args[0];ProblemDataFiles[] fs=(ProblemDataFiles[])args[1];for(int i=0;i<ps.length;i++)data.addProblem(ps[i],fs[i]);break;
     case "addNewAccount":throw new AssertionError("Singular account packets renumber identities on the real server");
     case "addNewAccounts":throw new AssertionError("Installation uses the native account-array upsert packet");
     case "updateAccounts":for(Account account:(Account[])args[0]){if(data.getAccount(account.getClientId())==null)data.addAccount(account);else data.updateAccount(account);}break;
     case "addNewClientSettings":data.addClientSettings((ClientSettings)args[0]);break;
     case "updateClientSettings":data.updateClientSettings((ClientSettings)args[0]);break;
     case "updateContestInformation":data.updateContestInformation((ContestInformation)args[0]);break;
     case "updateContestTime":data.updateContestTime((ContestTime)args[0]);break;
     default:throw new UnsupportedOperationException(method.getName());
    }return null;
   });
   api=new edu.csus.ecs.pc2.api.implementation.Contest(data,commands,null);api.setLoggedIn(true);
  }
  public edu.csus.ecs.pc2.api.implementation.Contest getContest(){return api;}
  edu.csus.ecs.pc2.core.model.IInternalContest model(){return data;}
  IInternalController control(){return commands;}
  public void addAccount(String type,String name,String password){Account a=new Account(new ClientId(1,ClientType.Type.TEAM,data.getAccounts(ClientType.Type.TEAM).size()+1),password,1);a.setDisplayName(name);data.addAccount(a);}
 }
 public static void main(String[]args){try{run(args);}catch(Throwable error){error.printStackTrace();System.exit(1);}}
 static void run(String[]args)throws Exception{
  if(args.length==1){edu.csus.ecs.pc2.core.log.StaticLog.setLog(new edu.csus.ecs.pc2.core.log.Log("fixture"));InternalContest empty=new InternalContest();empty.setClientId(new ClientId(1,ClientType.Type.SERVER,0));new edu.csus.ecs.pc2.imports.ccs.ContestSnakeYAMLLoader().initializeContest(empty,new java.io.File(args[0]));check(empty.getProblems().length==0,"Bootstrap contains no prior problems");check(empty.getAccounts(ClientType.Type.TEAM).size()==0,"Bootstrap contains no default teams");check(!empty.getContestTime().isContestRunning(),"Bootstrap clock remains stopped");check(empty.getLanguages().length>0,"Isolated languages are loaded");System.out.println("Native CDP bootstrap checks passed: "+checks);System.exit(0);}
  Path root=Files.createTempDirectory("native-contest-fixture-");Fixture source=new Fixture(root.resolve("source"));Problem p=new Problem("Original");p.setLetter("A");p.setShortName("alpha");p.setMemoryLimitMB(128);p.setTimeOutInSeconds(2);p.setSandboxType(Problem.SandboxType.PC2_INTERNAL_SANDBOX);p.setSandboxProgramName("pc2sandbox.sh");p.setSandboxCmdLine("./{:sandboxprogramname} {:memlimit} {:timelimit}");p.addTestCaseFilenames("01.in","01.ans");ProblemDataFiles f=new ProblemDataFiles(p);f.setJudgesDataFiles(new SerializedFile[]{new SerializedFile("01.in","1 2".getBytes())});f.setJudgesAnswerFiles(new SerializedFile[]{new SerializedFile("01.ans","3".getBytes())});source.data.addProblem(p,f);
  for(boolean include:new boolean[]{false,true}){
   JSONObject exported=ContestTemplates.exportTemplate(source,include);check(exported.getJSONArray("languages").length()==1,"Language settings are retained");Fixture target=new Fixture(root.resolve("target-"+include));Files.copy(Path.of(exported.getString("path")),target.privateBase.resolve("template.bin"));
   JSONArray rows=new JSONArray();String id=include?p.getElementId().toString():"new-problem";
   JSONObject row=new JSONObject().put("id",id).put("name","Fresh problem").put("letter","A").put("shortName","fresh").put("colorName","Green").put("colorRGB","#00ff00").put("timeLimit",3).put("memoryLimit",256).put("active",true);
   if(!include){Path tests=target.privateBase.resolve("judge-data/cases");Files.createDirectories(tests);Files.writeString(tests.resolve("01.in"),"4 5");Files.writeString(tests.resolve("01.ans"),"9");row.put("dataDirectory","cases");}
   rows.put(row);JSONObject d=new JSONObject().put("templateSha256",exported.getString("sha256")).put("problems",rows).put("teams",new JSONArray().put(new JSONObject().put("number",7).put("name","New team").put("password","fresh-test-password")).put(new JSONObject().put("number",TestTeamPolicy.NUMBER).put("testAccount",true).put("name","Organizer Test Team").put("password","private-diagnostic-password").put("visible",false))).put("workflow","review").put("penaltyMinutes",20).put("timeZone","Africa/Tripoli").put("contest",new JSONObject().put("title","New contest").put("shortName","NEW").put("freezeRemaining","00:30:00").put("scheduledStart","2027-02-01T10:00:00Z").put("lengthSeconds",18000));Files.writeString(target.privateBase.resolve("draft.json"),d.toString());
   JSONObject installed=ContestTemplates.install(target);check(target.data.getProblems()[0].getColorName().equals("Green")&&target.data.getProblems()[0].getColorRGB().equals("#00ff00"),"Draft balloon color survives native installation");check(installed.getJSONObject("problemIds").has(id),"Resources can be mapped to native problem IDs");check(target.data.getProblems().length==1,"Only requested problems are installed");Problem actual=target.data.getProblems()[0];check(actual.getDisplayName().equals("Fresh problem"),"Draft title overrides template");check(actual.getNumberTestCases()==1,"Judge tests retained");check(target.data.getProblemDataFile(actual).getJudgesDataFiles()[0].getBuffer()[0]==(include?'1':'4'),"Input bytes preserved");check(target.data.getClientSettings(new ClientId(1,ClientType.Type.JUDGE,1)).getAutoJudgeFilter().matchesProblem(actual),"Judge filter includes newly installed problems");check(JudgingWorkflow.mode(actual).equals("review"),"Workflow is applied");check(!target.data.getContestTime().isContestRunning()&&target.data.getContestTime().getElapsedSecs()==0,"Clock never starts");check(target.data.getContestTime().getContestLengthSecs()==18000,"Duration applied");check(!target.data.getContestInformation().isAutoStartContest(),"Scheduled date does not auto-start");check(target.data.getAccounts(ClientType.Type.TEAM).size()==2,"Only new team and its private diagnostic account exist");
   check(target.data.getAccount(new ClientId(1,ClientType.Type.TEAM,7))!=null,"Exact participant login survives installation");check(!target.data.getAccount(new ClientId(1,ClientType.Type.TEAM,TestTeamPolicy.NUMBER)).isAllowed(edu.csus.ecs.pc2.core.security.Permission.Type.DISPLAY_ON_SCOREBOARD),"Diagnostic team is hidden from its creation");check(TestTeamPolicy.nextNumber(target.data)==8,"Diagnostic ID cannot alter official numbering");
   Files.writeString(target.privateBase.resolve("installing"),"Recovering fixture");
   ContestTemplates.install(target);check(target.data.getProblems().length==1&&target.data.getAccounts(ClientType.Type.TEAM).size()==2,"Recovery cannot duplicate native records");
   check(Files.exists(target.privateBase.resolve("installation-receipt.json")),"Confirmed installation has a recovery receipt");Files.delete(target.privateBase.resolve("installing"));
   try{ContestTemplates.install(target);throw new AssertionError("Must reject reinstall");}catch(IllegalArgumentException expected){checks++;}
  }
  System.out.println("Contest template checks passed: "+checks);System.exit(0);
 }
}
