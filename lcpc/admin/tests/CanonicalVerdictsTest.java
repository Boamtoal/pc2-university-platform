import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.execute.*;
public class CanonicalVerdictsTest {
 static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 public static void main(String[] args){try{run();}catch(Throwable e){e.printStackTrace();System.exit(1);}}
 static void run()throws Exception{
  InternalContest model=new InternalContest();model.setClientId(new ClientId(1,ClientType.Type.JUDGE,1));
  ContestTime clock=new ContestTime();clock.setSiteNumber(1);model.addContestTime(clock);
  for(var e:ContestVerdicts.NAMES.entrySet())if(!java.util.Set.of("MLE","JE").contains(e.getKey()))model.addJudgement(new Judgement("No - "+e.getValue(),e.getKey()));
  var commands=(edu.csus.ecs.pc2.core.IInternalController)java.lang.reflect.Proxy.newProxyInstance(CanonicalVerdictsTest.class.getClassLoader(),new Class[]{edu.csus.ecs.pc2.core.IInternalController.class},(proxy,method,a)->{
   if(method.getName().equals("addNewJudgement")){model.addJudgement((Judgement)a[0]);return null;}
   if(method.getName().equals("updateJudgement"))return null; // Native setting updates are not echoed to their sender.
   throw new UnsupportedOperationException(method.getName());
  });
  DashboardBridge fixture=new DashboardBridge(){IInternalContest model(){return model;}edu.csus.ecs.pc2.core.IInternalController control(){return commands;}};
  ContestVerdicts.configure(fixture);
  for(var e:ContestVerdicts.NAMES.entrySet())check(java.util.Arrays.stream(model.getJudgements()).anyMatch(j->e.getKey().equals(j.getAcronym())&&e.getValue().equals(j.getDisplayName())),"Canonical setup must normalize the fresh native defaults");
  Run run=new Run(new ClientId(1,ClientType.Type.TEAM,1),new Language("Fixture"),new Problem("Fixture"));
  ExecutionData data=new ExecutionData();data.setCompileSuccess(true);data.setExecuteSucess(true);data.setExecuteExitValue(0);data.setValidationSuccess(true);data.setValidationReturnCode(43);data.setValidationResults("Wrong Answer");
  JudgementRecord record=JudgementUtilities.createJudgementRecord(model,run,data,"Wrong Answer");
  check(model.getJudgement(record.getJudgementId()).getAcronym().equals("WA"),"CLICS exit 43 must map to WA, not the fallback RTE");
  check(!record.isSolved(),"Wrong answer cannot be accepted");
  data.setValidationReturnCode(42);data.setValidationResults("accepted");record=JudgementUtilities.createJudgementRecord(model,run,data,"accepted");
  check(model.getJudgement(record.getJudgementId()).getAcronym().equals("AC")&&record.isSolved(),"CLICS acceptance stays accepted");
  data.setCompileSuccess(false);record=JudgementUtilities.createJudgementRecord(model,run,data,"");
  check(model.getJudgement(record.getJudgementId()).getAcronym().equals("CE"),"Compile failures stay distinct");
  System.out.println("Canonical verdict regression checks passed: 14");System.exit(0);
 }
}
