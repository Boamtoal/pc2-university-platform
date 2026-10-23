import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.security.*;
import edu.csus.ecs.pc2.core.*;
import edu.csus.ecs.pc2.core.log.StaticLog;
import edu.csus.ecs.pc2.core.list.RunList;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import org.json.*;
import java.util.*;

/** Isolated native scorer fixture. Does not connect to a PC² server. */
public class ScoreboardReleaseTest {
 static int checks=0;
 static void check(boolean ok,String text){checks++;if(!ok)throw new AssertionError(text);}
 static class Model extends InternalContest {
  List<Run> runs=new ArrayList<>();public Run[] getRuns(){return runs.toArray(new Run[0]);}
 }
 static JSONObject team(JSONObject data)throws Exception{Object t=data.getJSONObject("contestStandings").get("teamStanding");return t instanceof JSONArray?((JSONArray)t).getJSONObject(0):(JSONObject)t;}
 static JSONObject result(JSONObject data,int index)throws Exception{Object raw=team(data).get("problemSummaryInfo");JSONArray rows=raw instanceof JSONArray?(JSONArray)raw:new JSONArray().put(raw);for(int n=0;n<rows.length();n++)if(rows.getJSONObject(n).getInt("index")==index)return rows.getJSONObject(n);throw new AssertionError("Missing problem");}
 static Run run(Model m,Problem p,int minute,boolean accepted,boolean preliminary)throws Exception{
  return run(m,p,minute,accepted,preliminary,1);
 }
 static Run run(Model m,Problem p,int minute,boolean accepted,boolean preliminary,int team)throws Exception{
  ClientId who=new ClientId(1,ClientType.Type.TEAM,team);Run r=new Run(who,m.getLanguages()[0],p);r.setElapsedMS(minute*60000L);RunList list=new RunList();list.add(r);r.setStatus(Run.RunStates.BEING_JUDGED);
  Judgement j=Arrays.stream(m.getJudgements()).filter(x->x.getAcronym().equals(accepted?Judgement.ACRONYM_ACCEPTED:Judgement.ACRONYM_WRONG_ANSWER)).findFirst().get();
  list.updateRun(r,new JudgementRecord(j.getElementId(),new ClientId(1,ClientType.Type.JUDGE,1),accepted,true,true),preliminary);m.runs.add(r);return r;
 }
 public static void main(String[] args){try{test();}catch(Throwable error){error.printStackTrace();System.exit(1);}}
 static void test()throws Exception{
  StaticLog.setLog(new edu.csus.ecs.pc2.core.log.Log(java.nio.file.Files.createTempDirectory("scoreboard-log-").toString(),"scoreboard-fixture"));
  Model m=new Model();m.setSiteNumber(1);m.setFinalizeData(new FinalizeData());m.addSite(new Site("Fixture",1));m.setClientId(new ClientId(1,ClientType.Type.SCOREBOARD,1));
  ContestInformation info=new ContestInformation();info.setContestTitle("Frozen fixture");info.setFreezeTime("00:45:00");info.setPreliminaryJudgementsUsedByBoard(false);m.addContestInformation(info);
  ContestTime clock=new ContestTime(1);clock.setContestLengthSecs(120*60);clock.setElapsedSecs(100*60);m.addContestTime(clock);
  Account a=new Account(new ClientId(1,ClientType.Type.TEAM,1),"Fixture-only",1);a.setDisplayName("Fixture team");a.clearListAndLoadPermissions(new PermissionGroup().getPermissionList(ClientType.Type.TEAM));m.addAccount(a);
  m.addLanguage(new Language("Fixture"));m.addJudgement(new Judgement("Accepted",Judgement.ACRONYM_ACCEPTED));m.addJudgement(new Judgement("Wrong Answer",Judgement.ACRONYM_WRONG_ANSWER));
  Problem inactive=new Problem("Inactive problem");inactive.setActive(false);inactive.setColorRGB("#000000");m.addProblem(inactive);Problem before=new Problem("Before freeze");before.setColorName("Red");before.setColorRGB("#E53935");before.setLetter("A");Problem after=new Problem("After freeze");after.setLetter("B");Problem review=new Problem("Human review");review.setLetter("C");m.addProblem(before);m.addProblem(after);m.addProblem(review);
  run(m,before,30,true,false);run(m,after,85,false,false);run(m,after,90,true,false);Run held=run(m,review,95,true,true);
  JSONObject pub=PublicStandings.released(m,StaticLog.getLog());
  check(pub.getJSONObject("clock").getLong("lengthSeconds")==7200&&pub.getJSONObject("clock").getLong("remainingSeconds")==1200&&!pub.getJSONObject("clock").getBoolean("running"),"Published native paused clock survives public freeze");
  JSONObject column=PublicStandings.array(pub.getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(0);
  check(column.getString("title").equals("Before freeze")&&column.getString("colorRGB").equals("#E53935")&&column.getString("colorName").equals("Red"),"Inactive problems cannot shift native color columns");
  clock.startContestClock();check(PublicStandings.presentation(new JSONObject(pub.toString()),m).getJSONObject("clock").getBoolean("running"),"Clock start is reflected without changing standings");clock.stopContestClock();
  clock.setContestLengthSecs(7500);check(PublicStandings.presentation(new JSONObject(pub.toString()),m).getJSONObject("clock").getLong("remainingSeconds")==1500,"Native time extension is reflected");clock.setContestLengthSecs(7200);

  check(column.getJSONArray("firstToSolveTeams").length()==1&&column.getJSONArray("firstToSolveTeams").getString(0).equals(a.getClientId().getTripletKey()),"First solve is a visible final accepted submission");
  check(PublicStandings.array(pub.getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(1).getJSONArray("firstToSolveTeams").length()==0,"Frozen first solve identity is not published");
  check(PublicStandings.array(pub.getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(2).getJSONArray("firstToSolveTeams").length()==0,"Preliminary first solve is not published");
  check(pub.getJSONObject("release").getBoolean("frozen"),"Native freeze detected");check(team(pub).getInt("solved")==1,"Only pre-freeze solution public");check(pub.getJSONObject("contestStandings").getJSONObject("standingsHeader").getInt("totalSolved")==1,"Public aggregate excludes hidden solves");check(!team(pub).has("lastSolved")&&!team(pub).has("firstSolved"),"No private timing metadata");check(team(pub).getInt("points")==30,"Public penalty excludes post-freeze solution");check(result(pub,2).getBoolean("isPending")&&!result(pub,2).getBoolean("isSolved"),"Post-freeze AC stays pending");check(result(pub,2).getInt("solutionTime")==0,"No hidden solution time");
  DefaultScoringAlgorithm live=new DefaultScoringAlgorithm();live.setObeyFreeze(false);JSONObject full=XML.toJSONObject(live.getStandings(m,m.getRuns(),null,info.getScoringProperties(),StaticLog.getLog()));
  check(team(full).getInt("solved")==2,"Live view includes post-freeze final AC");check(team(full).getInt("points")==140,"Native 20-minute wrong-answer penalty retained");check(!result(full,3).getBoolean("isSolved"),"Provisional AC is not accepted");check(result(full,3).getBoolean("isPending"),"Human review remains pending");
  info.setThawed(true);check(team(PublicStandings.released(m,StaticLog.getLog())).getInt("solved")==1,"Thaw without native certification cannot release results");m.getFinalizeData().setCertified(true);JSONObject thawed=PublicStandings.released(m,StaticLog.getLog());check(team(thawed).getInt("solved")==2,"Thaw releases final solutions");check(!thawed.getJSONObject("release").getBoolean("frozen"),"Thawed status");
  RunList list=new RunList();list.add(held);list.updateRun(held,new JudgementRecord(held.getComputerJudgementRecord().getJudgementId(),new ClientId(1,ClientType.Type.ADMINISTRATOR,2),true,true),true);
  check(team(PublicStandings.released(m,StaticLog.getLog())).getInt("solved")==3,"Human approval releases the held result");
  Account second=new Account(new ClientId(1,ClientType.Type.TEAM,2),"Fixture-only",1);second.setDisplayName("Second fixture");second.clearListAndLoadPermissions(new PermissionGroup().getPermissionList(ClientType.Type.TEAM));m.addAccount(second);
  Run later=run(m,before,30,true,false,2);later.setElapsedMS(30*60000L+30000);
  JSONArray first=PublicStandings.array(PublicStandings.released(m,StaticLog.getLog()).getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(0).getJSONArray("firstToSolveTeams");
  check(first.length()==1&&first.getString(0).equals(a.getClientId().getTripletKey()),"Rounded same-minute submissions do not falsely tie");
  later.setElapsedMS(29*60000L+59000);
  first=PublicStandings.array(PublicStandings.released(m,StaticLog.getLog()).getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(0).getJSONArray("firstToSolveTeams");
  check(first.length()==1&&first.getString(0).equals(second.getClientId().getTripletKey()),"Submission time, not approval order, selects first solve");
  later.setDeleted(true);first=PublicStandings.array(PublicStandings.released(m,StaticLog.getLog()).getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem")).getJSONObject(0).getJSONArray("firstToSolveTeams");check(first.length()==1&&first.getString(0).equals(a.getClientId().getTripletKey()),"Removing a result recalculates first solve");
  info.setPreliminaryJudgementsUsedByBoard(true);try{PublicStandings.released(m,StaticLog.getLog());throw new AssertionError("Unsafe preliminary publication");}catch(IllegalStateException expected){checks++;}
  System.out.println("Scoreboard release checks passed ("+checks+" native assertions)");System.exit(0);
 }
}
