import edu.csus.ecs.pc2.api.ServerConnection;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;
import java.nio.file.*;
import java.util.Properties;
import org.json.XML;
import org.json.JSONObject;
import org.json.JSONArray;
import edu.csus.ecs.pc2.core.model.IInternalContest;
import edu.csus.ecs.pc2.core.model.ContestInformation;
import edu.csus.ecs.pc2.core.model.ContestTime;
import edu.csus.ecs.pc2.core.model.Problem;
import edu.csus.ecs.pc2.core.log.Log;
/** Read-only public standings exporter; never submits runs or changes contest state. */
public class PublicStandings extends ServerConnection {
 static JSONArray array(Object raw){return raw instanceof JSONArray?(JSONArray)raw:raw instanceof JSONObject?new JSONArray().put(raw):new JSONArray();}
 static JSONObject fields(JSONObject source,String... keys)throws Exception{
  JSONObject out=new JSONObject();for(String key:keys)if(source.has(key))out.put(key,source.get(key));return out;
 }
 /** PC² may retain solutionTime on an unsolved frozen cell. Never publish it. */
 static JSONObject publicFields(JSONObject nativePayload)throws Exception{
  JSONObject source=nativePayload.getJSONObject("contestStandings"),header=source.getJSONObject("standingsHeader");
  JSONObject safeHeader=fields(header,"title","currentDate","scoreboardMessage","problemCount","teamCount","totalSolved","totalAttempts");
  JSONArray problems=new JSONArray();for(int i=0;i<array(header.opt("problem")).length();i++)problems.put(fields(array(header.opt("problem")).getJSONObject(i),"id","title","attempts","numberSolved"));safeHeader.put("problem",problems);
  JSONArray teams=new JSONArray(),rawTeams=array(source.opt("teamStanding"));
  for(int i=0;i<rawTeams.length();i++){
   JSONObject raw=rawTeams.getJSONObject(i),team=fields(raw,"teamKey","teamId","teamName","rank","overallRank","solved","points","totalAttempts");
   JSONArray cells=new JSONArray(),rawCells=array(raw.opt("problemSummaryInfo"));
   for(int n=0;n<rawCells.length();n++){
    JSONObject cell=fields(rawCells.getJSONObject(n),"index","isSolved","isPending","attempts","solutionTime");
    if(!cell.optBoolean("isSolved",false))cell.put("solutionTime",0);
    cells.put(cell);
   }
   teams.put(team.put("problemSummaryInfo",cells));
  }
  return new JSONObject().put("contestStandings",new JSONObject().put("standingsHeader",safeHeader).put("teamStanding",teams));
 }
 /** Public presentation metadata only. Native scorer numbers visible active problems in model order. */
 static JSONArray firstToSolve(JSONObject payload,IInternalContest contest,Problem problem,int index)throws Exception{
  long earliest=Long.MAX_VALUE;java.util.Set<String> winners=new java.util.TreeSet<>();
  JSONArray teams=array(payload.getJSONObject("contestStandings").opt("teamStanding"));
  for(edu.csus.ecs.pc2.core.model.Run run:contest.getRuns()){
   edu.csus.ecs.pc2.core.model.JudgementRecord verdict=run.getJudgementRecord();
   if(run.isDeleted()||!run.isJudged()||!run.isSolved()||verdict==null||verdict.isPreliminaryJudgement()||!run.getProblemId().equals(problem.getElementId())||TestTeamPolicy.isTest(run.getSubmitter()))continue;
   String key=run.getSubmitter().getTripletKey();boolean released=false;
   for(int t=0;t<teams.length();t++){
    JSONObject team=teams.getJSONObject(t);if(!team.optString("teamKey","").equals(key))continue;
    JSONArray cells=array(team.opt("problemSummaryInfo"));
    for(int c=0;c<cells.length();c++){
     JSONObject cell=cells.getJSONObject(c);
     if(cell.optInt("index",0)==index&&cell.optBoolean("isSolved",false)&&cell.optLong("solutionTime",-1)==run.getElapsedMS()/60000L)released=true;
    }
   }
   if(!released)continue;
   long time=run.getElapsedMS();if(time<earliest){earliest=time;winners.clear();}if(time==earliest)winners.add(key);
  }
  JSONArray result=new JSONArray();for(String key:winners)result.put(key);return result;
 }
 static JSONObject presentation(JSONObject payload,IInternalContest contest)throws Exception {
  ContestTime time=contest.getContestTime();long length=time.getContestLengthSecs();
  payload.put("clock",new JSONObject().put("schema",1).put("lengthSeconds",length).put("remainingSeconds",Math.max(0,Math.min(length,length-time.getElapsedSecs()))).put("running",time.isContestRunning()));
  JSONArray columns=array(payload.getJSONObject("contestStandings").getJSONObject("standingsHeader").opt("problem"));int index=0;
  for(Problem problem:contest.getProblems())if(problem.isActive()&&problem.canView((java.util.List<edu.csus.ecs.pc2.core.model.Group>)null)){
   int id=++index;
   for(int n=0;n<columns.length();n++){
    JSONObject column=columns.getJSONObject(n);
    if(column.optInt("id",0)!=id||!column.optString("title","").equals(problem.getDisplayName()))continue;
    column.put("firstToSolveTeams",firstToSolve(payload,contest,problem,id));
    String rgb=problem.getColorRGB(),name=problem.getColorName(),letter=problem.getLetter();
    if(letter!=null&&letter.matches("[A-Za-z]{1,3}"))column.put("letter",letter);
    if(rgb!=null&&rgb.matches("#[0-9A-Fa-f]{6}"))column.put("colorRGB",rgb).put("colorName",name==null?"":name);
   }
  }
  return payload;
 }
 static JSONObject released(IInternalContest contest,Log log)throws Exception {
  ContestInformation info=contest.getContestInformation();
  if(info.isPreliminaryJudgementsUsedByBoard())throw new IllegalStateException("Preliminary scoring cannot be published");
  DefaultScoringAlgorithm scoring=new DefaultScoringAlgorithm();scoring.setObeyFreeze(true);
  JSONObject payload=presentation(publicFields(XML.toJSONObject(scoring.getStandings(contest,contest.getRuns(),null,info.getScoringProperties(),log))),contest);
  String message=payload.getJSONObject("contestStandings").getJSONObject("standingsHeader").optString("scoreboardMessage","");
  return payload.put("publishedAt",java.time.Instant.now().toString()).put("release",new JSONObject().put("schema",1).put("frozen",message.toLowerCase(java.util.Locale.ROOT).contains("frozen")).put("thawed",info.getThawed()!=null).put("freezeRemaining",info.getFreezeTime()).put("preliminaryResultsCounted",false));
 }
 public static void main(String[] args) {try{run(args);}catch(Exception e){System.err.println("Public standings unavailable: "+e.getClass().getSimpleName());System.exit(1);}}
 static void run(String[] args) throws Exception {
  PublicStandings s=new PublicStandings();
  Properties p=LCPCLaunch.secrets();s.login("scoreboard1",p.getProperty("scoreboard1"));
  Path output=Path.of(args[0]);Files.createDirectories(output.getParent());
  Runtime.getRuntime().addShutdownHook(new Thread(()->{try{if(s.isLoggedIn())s.logoff();}catch(Exception ignored){}}));
  while(s.isLoggedIn()) {
   try {
    String json=released(s.internalContest,s.controller.getLog()).toString();
    Path tmp=output.resolveSibling("data.tmp");Files.writeString(tmp,json);Files.move(tmp,output,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
   }catch(Exception e){Files.deleteIfExists(output);System.err.println("Public standings refresh failed: "+e.getClass().getSimpleName());}
   Thread.sleep(5000);
  }
  System.exit(1);
 }
}
