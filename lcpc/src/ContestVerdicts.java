import edu.csus.ecs.pc2.core.model.*;
import java.util.*;
/** The CLICS adapter matches its "Wrong Answer" result to a display name.
 * Prefixing that name with "No -" makes this PC2 version fall back to RTE. */
public final class ContestVerdicts {
 static final Map<String,String> NAMES=new LinkedHashMap<>();
 static {NAMES.put("AC","Accepted");NAMES.put("CE","Compilation Error");NAMES.put("RTE","Runtime Error");
  NAMES.put("TLE","Time Limit Exceeded");NAMES.put("WA","Wrong Answer");NAMES.put("MLE","Memory Limit Exceeded");
  NAMES.put("JE","Judge Error");NAMES.put("EO","Excessive Output");NAMES.put("OFE","Output Format Error");NAMES.put("OCS","Other - Contact Staff");}
 static void configure(DashboardBridge s)throws Exception{
  DashboardBridge.require(!s.model().getContestTime().isContestRunning(),"Pause the contest before configuring verdict names");
  for(var entry:NAMES.entrySet()){
   Judgement old=Arrays.stream(s.model().getJudgements()).filter(j->entry.getKey().equals(j.getAcronym())).findFirst().orElse(null);
   if(old==null)s.control().addNewJudgement(new Judgement(entry.getValue(),entry.getKey()));
   else if(!old.getDisplayName().equals(entry.getValue())){Judgement updated=AdministratorFeatures.copy(old);updated.setDisplayName(entry.getValue());s.control().updateJudgement(updated);
    // PC2 does not echo setting updates to the editing client. Mirror its view;
    // fresh judge/scoreboard clients load the server's canonical settings.
    s.model().updateJudgement(updated);}
  }
  for(int n=0;n<100;n++){
   if(NAMES.entrySet().stream().allMatch(e->Arrays.stream(s.model().getJudgements()).anyMatch(j->e.getKey().equals(j.getAcronym())&&e.getValue().equals(j.getDisplayName()))))return;
   Thread.sleep(100);
  }
  throw new IllegalStateException("PC2 did not confirm the canonical verdict names");
 }
}
