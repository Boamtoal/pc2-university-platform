import edu.csus.ecs.pc2.core.model.*;
import org.json.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Read-only projections of saved judge evidence. Never runs or rejudges code. */
public final class RunDiagnostics {
  static final int PREVIEW_BYTES=65536,MAX_REPORTS=10;
  static JSONObject preview(SerializedFile file)throws Exception{
    if(file==null||file.getBuffer()==null)return new JSONObject().put("available",false);
    byte[] data=file.getBuffer();int size=Math.min(data.length,PREVIEW_BYTES);
    return new JSONObject().put("available",true).put("bytes",data.length).put("truncated",size<data.length).put("text",new String(data,0,size,StandardCharsets.UTF_8));
  }
  static JSONObject cases(Run run,Problem problem,boolean finalJudged,java.util.function.Function<ElementId,String> judgement)throws Exception{
    Map<Integer,RunTestCase> saved=new TreeMap<>();RunTestCase[] records=run.getRunTestCases();
    // PC2 records a judgement per test, which can differ from the overall verdict.
    if(finalJudged&&records!=null)for(RunTestCase c:records)if(c!=null&&c.isActive()&&c.getTestNumber()>0){RunTestCase old=saved.get(c.getTestNumber());if(old==null||c.getDate().after(old.getDate()))saved.put(c.getTestNumber(),c);}
    int total=Math.max(problem.getNumberTestCases(),saved.keySet().stream().mapToInt(Integer::intValue).max().orElse(0));
    if(total>10000)throw new IllegalArgumentException("Too many recorded test cases");
    JSONArray rows=new JSONArray();int passed=0,failed=0,unvalidated=0,missing=0;
    for(int i=1;i<=total;i++){
      RunTestCase c=saved.get(i);JSONObject row=new JSONObject().put("number",i).put("recorded",c!=null);
      if(c==null){row.put("status",finalJudged?"Not recorded":"Pending").put("elapsedMS",JSONObject.NULL);missing++;}
      else{
        String verdict=judgement.apply(c.getJudgementId());String status=c.isValidated()?(c.isPassed()?"Passed":"Failed"):"Not validated";
        if(status.equals("Passed"))passed++;else if(status.equals("Failed"))failed++;else unvalidated++;
        row.put("status",status).put("verdict",verdict==null?"":verdict).put("validated",c.isValidated()).put("elapsedMS",c.getElapsedMS()).put("recordedAt",c.getDate().toInstant().toString());
      }
      rows.put(row);
    }
    return new JSONObject().put("tests",rows).put("counts",new JSONObject().put("total",total).put("passed",passed).put("failed",failed).put("notValidated",unvalidated).put("notRecorded",missing)).put("stopOnFirstFailure",problem.isStopOnFirstFailedTestCase()).put("memoryAvailable",false);
  }
  static JSONArray reports(RunResultFiles[] files,java.util.function.Function<ElementId,String> judgement)throws Exception{
    JSONArray reports=new JSONArray();if(files==null)return reports;
    for(int i=0;i<Math.min(files.length,MAX_REPORTS);i++){
      RunResultFiles f=files[i];if(f==null||f.getExecutionData()==null)continue;
      JSONObject report=new JSONObject().put("verdict",judgement.apply(f.getJudgementId())).put("compileFailed",f.failedInCompile()).put("executeFailed",f.failedInExecute()).put("validationFailed",f.failedInValidating()).put("compileTimeMS",f.getCompileTimeMS()).put("executeTimeMS",f.getExecuteTimeMS()).put("validateTimeMS",f.getValidateTimeMS()).put("compileExitCode",f.getCompileResultCode()).put("executeExitCode",f.getExecutionResultCode()).put("validationExitCode",f.getValidationResultCode());
      JSONObject outputs=new JSONObject().put("compilerStderr",preview(f.getCompilerStderrFile())).put("compilerStdout",preview(f.getCompilerStdoutFile())).put("executionStderr",preview(f.getExecuteStderrFile())).put("executionStdout",preview(f.getExecuteStdoutFile())).put("validatorStderr",preview(f.getValidatorStderrFile())).put("validatorStdout",preview(f.getValidatorStdoutFile()));
      String message=f.getValidationResults();if(message!=null)report.put("validatorMessage",message.substring(0,Math.min(message.length(),4096)));
      reports.put(report.put("outputs",outputs));
    }
    return reports;
  }
  static JSONObject testData(ProblemDataFiles files,int test)throws Exception{
    SerializedFile[] inputs=files==null?null:files.getJudgesDataFiles(),answers=files==null?null:files.getJudgesAnswerFiles();
    return new JSONObject().put("number",test).put("input",preview(inputs!=null&&test<=inputs.length?inputs[test-1]:null)).put("expected",preview(answers!=null&&test<=answers.length?answers[test-1]:null));
  }
}
