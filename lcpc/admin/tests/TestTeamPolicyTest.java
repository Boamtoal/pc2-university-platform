import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.security.*;
import edu.csus.ecs.pc2.core.log.*;
import edu.csus.ecs.pc2.core.list.RunList;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import edu.csus.ecs.pc2.core.util.BalloonHandler;
import org.json.*;
import java.util.*;

/** In-memory native PC2 scoring and actual production agent; no server or submissions. */
public class TestTeamPolicyTest {
 static int checks;static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
 static Run accepted(ScoreboardReleaseTest.Model m,Account team,Problem problem,int minute)throws Exception{
  Run r=new Run(team.getClientId(),m.getLanguages()[0],problem);r.setElapsedMS(minute*60000L);RunList list=new RunList();list.add(r);r.setStatus(Run.RunStates.BEING_JUDGED);
  list.updateRun(r,new JudgementRecord(m.getJudgements()[0].getElementId(),new ClientId(1,ClientType.Type.JUDGE,1),true,true,true),false);m.runs.add(r);return r;
 }
 public static void main(String[] args){try{run();}catch(Throwable e){e.printStackTrace();System.exit(1);}}
 static void run()throws Exception{
  StaticLog.setLog(new Log(java.nio.file.Files.createTempDirectory("test-team-log-").toString(),"fixture"));
  ScoreboardReleaseTest.Model m=new ScoreboardReleaseTest.Model();m.setSiteNumber(1);m.setFinalizeData(new FinalizeData());m.addSite(new Site("Fixture",1));m.setClientId(new ClientId(1,ClientType.Type.SCOREBOARD,1));
  ContestInformation info=new ContestInformation();info.setContestTitle("Diagnostic fixture");info.setFreezeTime("00:30:00");info.setPreliminaryJudgementsUsedByBoard(false);m.addContestInformation(info);
  ContestTime time=new ContestTime(1);time.setContestLengthSecs(7200);time.setElapsedSecs(6000);m.addContestTime(time);
  m.addLanguage(new Language("Fixture"));m.addJudgement(new Judgement("Accepted",Judgement.ACRONYM_ACCEPTED));
  Problem p=new Problem("A");p.setLetter("A");m.addProblem(p);Problem q=new Problem("B");q.setLetter("B");m.addProblem(q);
  Account real=TestTeamPolicy.account(1,7,"Official team","fixture-password",true,true),test=TestTeamPolicy.account(1,TestTeamPolicy.NUMBER,"PRIVATE DIAGNOSTIC TEAM","private-fixture-password",true,false);m.addAccount(real);m.addAccount(test);
  check(test.isAllowed(Permission.Type.LOGIN),"Test account keeps normal participant login");
  check(!test.isAllowed(Permission.Type.EDIT_ACCOUNT),"Test account has no administrator permissions");
  check(TestTeamPolicy.nextNumber(m)==8,"Reserved number does not affect roster numbering");
  // Even accidental/native permission changes must not unhide the reserved identity.
  test.addPermission(Permission.Type.DISPLAY_ON_SCOREBOARD);check(!test.isAllowed(Permission.Type.DISPLAY_ON_SCOREBOARD),"Production agent makes exclusion mandatory");
  Run diagnostic=accepted(m,test,p,1);accepted(m,test,q,2);Run official=accepted(m,real,p,30);
  DefaultScoringAlgorithm scorer=new DefaultScoringAlgorithm();scorer.setObeyFreeze(false);
  JSONObject live=XML.toJSONObject(scorer.getStandings(m,m.getRuns(),null,info.getScoringProperties(),StaticLog.getLog()));
  JSONObject pub=PublicStandings.released(m,StaticLog.getLog());
  for(JSONObject data:List.of(live,pub)){
   check(!data.toString().contains("PRIVATE DIAGNOSTIC TEAM"),"Test identity absent from live/public board");
   JSONArray teams=PublicStandings.array(data.getJSONObject("contestStandings").opt("teamStanding"));check(teams.length()==1,"Only official competitors count");
   check(teams.getJSONObject(0).getInt("solved")==1&&teams.getJSONObject(0).getInt("points")==30,"Official score unchanged");
   JSONObject header=data.getJSONObject("contestStandings").getJSONObject("standingsHeader");check(header.getInt("totalSolved")==1&&header.getInt("totalAttempts")==1,"Diagnostic attempts and solves excluded from aggregates");
   JSONArray cells=PublicStandings.array(teams.getJSONObject(0).get("problemSummaryInfo"));check(cells.getJSONObject(0).getInt("solutionTime")==30,"Early diagnostic solve cannot change official timing");
  }
  BalloonHandler balloons=new BalloonHandler();balloons.setContestAndController(m,null);
  check(!balloons.shouldSendBalloon(diagnostic),"No diagnostic balloons");check(balloons.shouldSendBalloon(official),"Official balloons remain enabled");
  System.out.println("Diagnostic team checks passed: "+checks);System.exit(0);
 }
}
