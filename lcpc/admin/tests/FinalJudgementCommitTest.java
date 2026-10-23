import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.list.RunList;
import edu.csus.ecs.pc2.core.IInternalController;
import java.lang.reflect.Proxy;
import java.util.*;

public class FinalJudgementCommitTest {
 static int checks=0;
 static void check(boolean ok,String text){checks++;if(!ok)throw new AssertionError(text);}
 public static void main(String[] args){try{run();}catch(Throwable e){e.printStackTrace();System.exit(1);}}
 static void run()throws Exception{
  for(boolean accepted:new boolean[]{true,false}){
   ClientId owner=new ClientId(1,ClientType.Type.ADMINISTRATOR,2);
   List<IRunListener> listeners=new ArrayList<>();
   InternalContest data=new InternalContest(){
    public void addRunListener(IRunListener listener){listeners.add(listener);}
    public void removeRunListener(IRunListener listener){listeners.remove(listener);}
   };data.setClientId(owner);
   Judgement verdict=new Judgement(accepted?"Yes":"Wrong Answer",accepted?Judgement.ACRONYM_ACCEPTED:"WA");
   Problem problem=new Problem("Fixture");JudgingWorkflow.apply(problem,"review");
   Run original=new Run(new ClientId(1,ClientType.Type.TEAM,1),new Language("Fixture"),problem);
   RunList list=new RunList();list.add(original);original.setStatus(Run.RunStates.BEING_JUDGED);
   JudgementRecord automatic=new JudgementRecord(verdict.getElementId(),new ClientId(1,ClientType.Type.JUDGE,1),accepted,true,true);
   list.updateRun(original,automatic,true);
   check(original.getStatus()==Run.RunStates.MANUAL_REVIEW,"Fixture awaits human approval");
   IInternalController commands=(IInternalController)Proxy.newProxyInstance(FinalJudgementCommitTest.class.getClassLoader(),new Class[]{IInternalController.class},(proxy,method,a)->{
    if(!method.getName().equals("updateRun"))throw new UnsupportedOperationException(method.getName());
    Run submitted=(Run)a[0];JudgementRecord decision=(JudgementRecord)a[1];
    check(submitted!=original,"Never mutate the locally cached run before server acknowledgement");
    check(original.getStatus()==Run.RunStates.MANUAL_REVIEW,"Original remains pending before acknowledgement");
    check(submitted.getJudgementRecord().getElementId().equals(automatic.getElementId()),"Server can still locate the existing saved report history");
    check(Arrays.stream(submitted.getAllJudgementRecords()).noneMatch(j->j.getElementId().equals(decision.getElementId())),"New judgement must be sent separately, not in the pre-update history");
    check(decision.isSolved()==accepted&&!decision.isPreliminaryJudgement()&&decision.isSendToTeam(),"Human decision is final and notifies the team");
    check(decision.getPreviousComputerJudgementId().equals(automatic.getElementId()),"Keep automatic judgement provenance");
    submitted.addJudgement(decision);submitted.setStatus(Run.RunStates.JUDGED);
    RunEvent event=new RunEvent(RunEvent.Action.values()[0],submitted,null,null);
    for(IRunListener listener:new ArrayList<>(listeners))listener.runChanged(event);
    return null;
   });
   DashboardBridge bridge=new DashboardBridge(){IInternalContest model(){return data;}IInternalController control(){return commands;}};
   bridge.commitJudgement(original,verdict);
   check(listeners.isEmpty(),"Remove the acknowledgement listener after commit");
  }
  System.out.println("Final judgement commit checks passed: "+checks);System.exit(0);
 }
}
