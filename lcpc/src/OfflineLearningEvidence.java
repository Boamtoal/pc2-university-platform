import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.security.FileSecurity;
import edu.csus.ecs.pc2.profile.ProfileManager;
import org.json.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Reads only existing local PC2 storage. No controller, login, listener or execution. */
public final class OfflineLearningEvidence {
 static long written;
 static Path output;
 static String digest(Path path)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));}
 static Path capsule(Path original)throws Exception{
  Path copy=output.resolve(".native-capsule");Files.createDirectory(copy);Map<String,String> before=new TreeMap<>();
  try(var stream=Files.list(original)){
   for(Path file:stream.filter(p->Set.of("settings.dat","runlist.dat","contest.key","recovery.key").contains(p.getFileName().toString())||p.getFileName().toString().matches("s[0-9]+r[0-9]+(?:\\.JudgementRecord-[A-Za-z0-9-]+)?\\.files")).toList()){
    if(!Files.isRegularFile(file)||Files.isSymbolicLink(file))throw new IllegalArgumentException("Invalid native evidence file");
    String name=file.getFileName().toString();before.put(name,digest(file));Files.copy(file,copy.resolve(name));
   }
  }
  for(var entry:before.entrySet())if(!entry.getValue().equals(digest(original.resolve(entry.getKey())))||!entry.getValue().equals(digest(copy.resolve(entry.getKey()))))throw new IllegalArgumentException("Native evidence changed during capture; retry export");
  return copy;
 }
 static JSONObject file(String relative,SerializedFile source)throws Exception{
  if(source==null||source.getBuffer()==null)return new JSONObject().put("available",false);
  byte[] bytes=source.getBuffer();written+=bytes.length;
  if(written>536870912L)throw new IllegalArgumentException("Evidence exceeds the 512 MiB export limit");
  Path path=output.resolve(relative);Files.createDirectories(path.getParent());Files.write(path,bytes);
  return new JSONObject().put("available",true).put("path",relative).put("bytes",bytes.length).put("sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
 }
 static JSONObject extract(Path state,Path target)throws Exception{
  output=target;written=0;
  var manager=new ProfileManager(state.resolve("server/profiles.properties").toString());
  Profile profile=manager.getDefaultProfile();
  if(profile==null)throw new IllegalArgumentException("No current native profile");
  Path profilePath=Path.of(profile.getProfilePath());
  if(!profilePath.isAbsolute())profilePath=state.resolve("server").resolve(profilePath);
  Path db=profilePath.resolve("db.1").toRealPath();
  if(!db.startsWith(state.resolve("server/profiles").toRealPath()))throw new IllegalArgumentException("Native profile escaped the selected contest");
  db=capsule(db);
  Properties credentials=new Properties();try(var stream=Files.newInputStream(state.resolve("credentials.properties"))){credentials.load(stream);}
  FileSecurity storage=new FileSecurity(db.toString());
  if(!storage.verifyPassword(credentials.getProperty("contest").toCharArray()))throw new IllegalArgumentException("Cannot unlock native evidence");
  Map<?,?> settings=(Map<?,?>)storage.load(db.resolve("settings.dat").toString());
  ContestTime clock=(ContestTime)settings.get("CONTEST_TIME");
  if(clock!=null&&clock.isContestRunning())throw new IllegalArgumentException("Pause and stop the contest server before export");
  Map<?,?> runs=(Map<?,?>)storage.load(db.resolve("runlist.dat").toString());
  Map<ElementId,Problem> problems=new HashMap<>();for(Problem p:(Problem[])settings.get("PROBLEMS"))problems.put(p.getElementId(),p);
  Map<ElementId,String> verdicts=new HashMap<>();for(Judgement j:(Judgement[])settings.get("JUDGEMENTS"))verdicts.put(j.getElementId(),j.getDisplayName());
  JSONArray problemRows=new JSONArray(),runRows=new JSONArray();
  for(ProblemDataFiles data:(ProblemDataFiles[])settings.get("PROBLEM_DATA_FILES")){
   Problem p=problems.get(data.getProblemId());if(p==null)continue;
   String base="native-problems/"+problemRows.length()+"/";JSONArray tests=new JSONArray();
   SerializedFile[] inputs=data.getJudgesDataFiles(),answers=data.getJudgesAnswerFiles();
   for(int i=0;i<p.getNumberTestCases();i++)tests.put(new JSONObject().put("number",i+1).put("input",file(base+(i+1)+".in",inputs!=null&&i<inputs.length?inputs[i]:null)).put("expected",file(base+(i+1)+".ans",answers!=null&&i<answers.length?answers[i]:null)));
   problemRows.put(new JSONObject().put("id",p.getElementId().toString()).put("tests",tests).put("validator",p.getValidatorType().toString()).put("historicRevisionAvailable",false));
  }
  for(Object value:runs.values()){
   Run run=(Run)value;if(TestTeamPolicy.isTest(run.getSubmitter())||run.isDeleted())continue;
   Problem p=problems.get(run.getProblemId());if(p==null)continue;
   String base="native-runs/"+run.getSiteNumber()+"-"+run.getNumber()+"/";JSONObject row=new JSONObject().put("site",run.getSiteNumber()).put("number",run.getNumber()).put("team",run.getSubmitter().getName()).put("problemId",p.getElementId().toString());
   JSONArray sources=new JSONArray(),reports=new JSONArray(),history=new JSONArray();
   Path source=db.resolve("s"+run.getSiteNumber()+"r"+run.getNumber()+".files");
   if(Files.isRegularFile(source)){
    RunFiles files=(RunFiles)storage.load(source.toString());
    if(!run.getElementId().equals(files.getRunId()))throw new IllegalArgumentException("Source identity mismatch");
    List<SerializedFile> all=new ArrayList<>();all.add(files.getMainFile());if(files.getOtherFiles()!=null)all.addAll(Arrays.asList(files.getOtherFiles()));
    int i=0;for(SerializedFile f:all)if(f!=null)sources.put(file(base+"source/"+(++i)+".txt",f).put("name",Path.of(f.getName()).getFileName().toString()));
   }
   JudgementRecord[] decisions=run.getAllJudgementRecords();
   if(decisions!=null)for(JudgementRecord decision:decisions){
    history.put(new JSONObject().put("verdict",verdicts.getOrDefault(decision.getJudgementId(),"")).put("active",decision.isActive()).put("computer",decision.isComputerJudgement()).put("preliminary",decision.isPreliminaryJudgement()).put("actor",decision.getJudgerClientId()==null?"":decision.getJudgerClientId().getName()).put("at",decision.getDate()==null?"":decision.getDate().toInstant().toString()));
    Path report=db.resolve("s"+run.getSiteNumber()+"r"+run.getNumber()+"."+decision.getElementId()+".files");
    if(!Files.isRegularFile(report))continue;
    RunResultFiles f=(RunResultFiles)storage.load(report.toString());if(!run.getElementId().equals(f.getRunId()))throw new IllegalArgumentException("Judge evidence identity mismatch");
    JSONArray projected=RunDiagnostics.reports(new RunResultFiles[]{f},id->verdicts.getOrDefault(id,""));if(projected.length()==0)continue;
    JSONObject item=projected.getJSONObject(0),outputs=new JSONObject();String prefix=base+"reports/"+reports.length()+"/";
    outputs.put("compilerStderr",file(prefix+"compiler-stderr.txt",f.getCompilerStderrFile())).put("compilerStdout",file(prefix+"compiler-stdout.txt",f.getCompilerStdoutFile())).put("executionStderr",file(prefix+"execution-stderr.txt",f.getExecuteStderrFile())).put("executionStdout",file(prefix+"execution-stdout.txt",f.getExecuteStdoutFile())).put("validatorStderr",file(prefix+"validator-stderr.txt",f.getValidatorStderrFile())).put("validatorStdout",file(prefix+"validator-stdout.txt",f.getValidatorStdoutFile()));
    item.put("outputs",outputs).put("decisionId",decision.getElementId().toString()).put("testAssociationAvailable",false);reports.put(item);
   }
   row.put("sources",sources).put("reports",reports).put("history",history).put("cases",RunDiagnostics.cases(run,p,run.isJudged()||run.getComputerJudgementRecord()!=null,id->verdicts.getOrDefault(id,"")));runRows.put(row);
  }
  return new JSONObject().put("schema",1).put("problems",problemRows).put("runs",runRows);
 }
 public static void main(String[] args){try{
  Path state=Path.of(args[0]).toRealPath(),target=Path.of(args[1]).toRealPath();
  JSONObject result=extract(state,target);Files.writeString(target.resolve("evidence.json"),result.toString(),StandardCharsets.UTF_8);
 }catch(Throwable error){System.err.println("Offline learning evidence unavailable ("+error.getClass().getSimpleName()+"). Inspect the native profile and retry.");System.exit(1);}}
}
