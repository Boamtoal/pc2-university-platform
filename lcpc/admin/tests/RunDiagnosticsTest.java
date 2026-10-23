import edu.csus.ecs.pc2.core.model.*;
import org.json.*;
import java.util.*;
public class RunDiagnosticsTest {
 static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 public static void main(String[] args)throws Exception{
  Problem p=new Problem("Example");p.setStopOnFirstFailedTestCase(true);for(int i=0;i<4;i++)p.addTestCaseFilenames("t"+i+".in","t"+i+".ans");
  Run run=new Run(new ClientId(1,ClientType.Type.TEAM,1),new Language("C++"),p);
  ElementId ac=new ElementId("Accepted"),wa=new ElementId("Wrong Answer"),re=new ElementId("Runtime Error");
  RunTestCase passed=new RunTestCase(run,new JudgementRecord(ac,new ClientId(1,ClientType.Type.JUDGE,1),true,true),1,true);passed.setValidated(true);passed.setElapsedMS(17);run.addTestCase(passed);
  RunTestCase failed=new RunTestCase(run,new JudgementRecord(wa,new ClientId(1,ClientType.Type.JUDGE,1),false,true),2,false);failed.setValidated(true);run.addTestCase(failed);
  RunTestCase crashed=new RunTestCase(run,new JudgementRecord(re,new ClientId(1,ClientType.Type.JUDGE,1),false,true),3,false);run.addTestCase(crashed);
  JSONObject result=RunDiagnostics.cases(run,p,true,ElementId::toString);JSONArray rows=result.getJSONArray("tests");
  check(result.getJSONObject("counts").getInt("passed")==1,"Passed case must survive a different overall judgement");
  check(rows.getJSONObject(1).getString("status").equals("Failed"),"Validated failure");
  check(rows.getJSONObject(2).getString("status").equals("Not validated"),"Crash must not be called a validated wrong answer");
  check(rows.getJSONObject(3).getString("status").equals("Not recorded"),"Missing case must not imply pass or fail");
  check(rows.getJSONObject(0).getLong("elapsedMS")==17,"Saved per-test timing");
  JSONObject pending=RunDiagnostics.cases(run,p,false,ElementId::toString);
  check(pending.getJSONObject("counts").getInt("passed")==0&&pending.getJSONArray("tests").getJSONObject(0).getString("status").equals("Pending"),"Old evidence must not masquerade as a new pending judgement");
  byte[] large=new byte[70000];Arrays.fill(large,(byte)'x');JSONObject text=RunDiagnostics.preview(new SerializedFile("output.txt",large));
  check(text.getBoolean("truncated")&&text.getString("text").length()==65536&&text.getInt("bytes")==70000,"Bound previews without losing original size");
  check(!RunDiagnostics.preview(null).getBoolean("available"),"Absent output differs from empty output");
  check(RunDiagnostics.preview(new SerializedFile("empty.txt",new byte[0])).getBoolean("available"),"Empty retained output is available");
  ProblemDataFiles data=new ProblemDataFiles(p);data.setJudgesDataFiles(new SerializedFile[]{new SerializedFile("01.in","input".getBytes())});data.setJudgesAnswerFiles(new SerializedFile[]{new SerializedFile("01.ans","answer".getBytes())});
  check(RunDiagnostics.testData(data,1).getJSONObject("expected").getString("text").equals("answer"),"Expected output uses paired reference file");
  System.out.println("RunDiagnostics native evidence checks passed (10 assertions)");
 }
}
