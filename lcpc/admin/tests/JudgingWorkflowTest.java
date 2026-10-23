import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.list.RunList;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import java.lang.reflect.Method;
public class JudgingWorkflowTest {
 static int assertions=0;
 static void check(boolean ok,String message){assertions++;if(!ok)throw new AssertionError(message);}
 static final ClientId TEAM=new ClientId(1,ClientType.Type.TEAM,1),AUTO=new ClientId(1,ClientType.Type.JUDGE,1),OWNER=new ClientId(1,ClientType.Type.ADMINISTRATOR,2);
 public static void main(String[] args)throws Exception{
  Method valid=DefaultScoringAlgorithm.class.getDeclaredMethod("isValidJudgement",Run.class);valid.setAccessible(true);DefaultScoringAlgorithm scoring=new DefaultScoringAlgorithm();
  for(String mode:new String[]{"automatic","review","human"})for(boolean accepted:new boolean[]{true,false}){
   Problem p=new Problem("Fixture");JudgingWorkflow.apply(p,mode);Run run=new Run(TEAM,new Language("Fixture"),p);RunList list=new RunList();list.add(run);
   check(JudgingWorkflow.mode(p).equals(mode),"Native flags round trip");
   check(!p.isPrelimaryNotification(),"Provisional team verdicts must be suppressed");
   if(mode.equals("human")){
    check(run.getStatus()==Run.RunStates.NEW,"Human only must not queue automated execution");
    check(!(boolean)valid.invoke(scoring,run),"An unjudged run cannot affect scores");
    run.setStatus(Run.RunStates.BEING_JUDGED);
    list.updateRun(run,new JudgementRecord(new ElementId(accepted?"AC":"WA"),OWNER,accepted,false),p.isManualReview());
   }else{
    check(run.getStatus()==Run.RunStates.QUEUED_FOR_COMPUTER_JUDGEMENT,"Automatic execution must be queued");
    run.setStatus(Run.RunStates.BEING_JUDGED);
    list.updateRun(run,new JudgementRecord(new ElementId(accepted?"AC":"WA"),AUTO,accepted,true,true),p.isManualReview());
    if(mode.equals("review")){
     check(run.getStatus()==Run.RunStates.MANUAL_REVIEW,"Automatic result must wait for a human");
     check(run.getJudgementRecord().isPreliminaryJudgement(),"PC2 must mark it preliminary");
     check(!(boolean)valid.invoke(scoring,run),"Neither provisional AC nor WA may affect scores");
     check(JudgingWorkflow.state(run,false).equals("Awaiting human approval"),"Admin review state");
     list.updateRun(run,new JudgementRecord(run.getComputerJudgementRecord().getJudgementId(),OWNER,accepted,true),p.isManualReview());
    }
   }
   check(run.getStatus()==Run.RunStates.JUDGED,"A final human/automatic judgement must finish");
   check(!run.getJudgementRecord().isPreliminaryJudgement(),"Final decision cannot stay preliminary");
   check((boolean)valid.invoke(scoring,run),"Only the final decision is scoreable");
   check(run.isSolved()==accepted,"Acceptance follows the final decision");
  }
  ContestInformation info=new ContestInformation();info.setPreliminaryJudgementsUsedByBoard(true);info.setPreliminaryJudgementsTriggerNotifications(true);JudgingWorkflow.holdPreliminaryResults(info);
  check(!info.isPreliminaryJudgementsUsedByBoard()&&!info.isPreliminaryJudgementsTriggerNotifications(),"No early scores or notifications");
  System.out.println("Native judging workflow checks passed ("+assertions+" assertions; all three modes, AC and WA)");System.exit(0);
 }
}
