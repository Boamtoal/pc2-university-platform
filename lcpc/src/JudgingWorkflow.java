import edu.csus.ecs.pc2.core.model.*;
/** Native PC2 workflow flags; no frontend-only hold or synthetic verdicts. */
public final class JudgingWorkflow {
 static String mode(Problem p){return !p.isComputerJudged()?"human":p.isManualReview()?"review":"automatic";}
 static void apply(Problem p,String mode){
  if(!java.util.Set.of("automatic","review","human").contains(mode))throw new IllegalArgumentException("Unsupported judging workflow");
  p.setComputerJudged(!mode.equals("human"));p.setManualReview(mode.equals("review"));p.setPrelimaryNotification(false);
 }
 static void holdPreliminaryResults(ContestInformation info){info.setPreliminaryJudgementsUsedByBoard(false);info.setPreliminaryJudgementsTriggerNotifications(false);}
 static String state(Run raw,boolean finalJudged){
  if(finalJudged)return "Final";
  if(raw.getStatus()==Run.RunStates.MANUAL_REVIEW)return "Awaiting human approval";
  if(raw.getStatus()==Run.RunStates.NEW)return "Awaiting human judgement";
  return "Pending";
 }
}
