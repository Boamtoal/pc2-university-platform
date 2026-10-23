const test=require('node:test'),assert=require('node:assert/strict');
const view=require('../../admin-ui/run-details.js');
test('Escape code, diagnostic text and private test data as text',()=>{
 const attack='<img src=x onerror=alert(1)>';
 const html=view.render({final:true,counts:{total:1},tests:[{number:1,status:'Failed',verdict:attack,elapsedMS:4}],reports:[{verdict:attack,validatorMessage:attack,outputs:{executionStdout:{available:true,bytes:30,text:attack}}}]});
 assert.ok(!html.includes(attack));assert.ok(html.includes('&lt;img'));assert.ok(!view.renderTestData({number:1,input:{available:true,text:attack,bytes:30}}).includes(attack));
});
test('Missing cases, pending and unvalidated results retain distinct states',()=>{
 const html=view.render({final:false,counts:{total:3,notRecorded:2,notValidated:1},tests:[{number:1,status:'Not validated'},{number:2,status:'Pending'},{number:3,status:'Not recorded'}]});
 for(const text of ['Not validated','Pending','Not recorded','Judging is not complete'])assert.ok(html.includes(text));
 assert.ok(!html.includes('badge accepted">Passed</span>'));
});
test('Missing, empty and truncated output are distinguished',()=>{
 assert.ok(view.preview(null).includes('Not saved'));assert.ok(view.preview({available:true,text:'',bytes:0}).includes('(Empty file)'));assert.ok(view.preview({available:true,text:'abc',bytes:70000,truncated:true}).includes('First 64 KiB only'));
});
test('Compiler failure does not mark execution or validation as complete',()=>{
 const html=view.render({reports:[{compileFailed:true,outputs:{}}]});assert.equal((html.match(/>Not run<\/span>/g)||[]).length,2);
});

test('Provisional evidence is available without presenting it as final acceptance',()=>{
 const html=view.render({final:false,preliminary:true,awaitingApproval:true,counts:{passed:1,total:1},tests:[{number:1,status:'Passed',verdict:'Yes',elapsedMS:12}],reports:[{verdict:'Yes',outputs:{}}]});
 assert.ok(html.includes('Awaiting human approval'));assert.ok(html.includes('provisional'));assert.ok(html.includes('Saved report 1 · Recorded judgement'));assert.ok(html.includes('badge accepted">Accepted'));assert.ok(!html.includes('Judging is not complete'));
});

test('compile and runtime failures are visible in report and stream headers',()=>{
 for(const [key,label,stream] of [['compileFailed','Compile Error','compilerStderr'],['executeFailed','Runtime Error','executionStderr']]){
  const html=view.render({reports:[{[key]:true,verdict:label,outputs:{[stream]:{available:true,bytes:5,text:'error'}}}]});
  assert.ok(html.includes('badge rejected">'+label));assert.ok(html.includes('output-file report-failure" open'));assert.ok(html.includes('badge rejected">Failed'));
 }
});
test('reference answer and actual saved output are clearly distinct without invented test association',()=>{
 const html=view.renderTestData({number:1,input:{available:true,text:'4',bytes:1},expected:{available:true,text:'YES',bytes:3}},{reports:[{verdict:'Wrong Answer',outputs:{executionStdout:{available:true,bytes:2,text:'NO'}}}]});
 for(const label of ['Expected output · Reference answer','Actual output · Saved program output','>YES<','>NO<','must not be assumed to belong to the selected test'])assert.ok(html.includes(label));
 const failed=view.renderTestData({number:1},{reports:[{compileFailed:true,outputs:{}}]});assert.ok(failed.includes('program did not run'));assert.ok(!failed.includes('>YES<'));
});
test('wrapper runtime errors remain visible when PC2 stage flags are false',()=>{
 const report={verdict:'Run-time Error',compileFailed:false,executeFailed:false,compileExitCode:0,executeExitCode:139,outputs:{executionStdout:{available:true,bytes:3,text:'YES'}}};
 const html=view.render({verdict:'Wrong Answer',reports:[report]});
 assert.ok(html.includes('badge rejected">Runtime Error'));
 assert.ok(html.includes('Execution stdout <span class="badge rejected">Failed'));
 assert.ok(html.includes('output-file report-failure" open'));
 assert.ok(view.renderTestData({number:1},{reports:[report]}).includes('saved output may be partial'));
 report.outputs.executionStdout.text="Note: program exited with non-zero exit code '139'\n";
 assert.ok(view.renderTestData({number:1},{reports:[report]}).includes('Actual program output is unavailable. PC² retained an execution diagnostic note instead'));
 const compile=view.render({reports:[{verdict:'Compilation Error',compileFailed:false,compileExitCode:1,executeExitCode:0}]});
 assert.equal((compile.match(/>Not run<\/span>/g)||[]).length,2);
});
test('a stale report judgement cannot turn a saved zero execution exit into runtime failure',()=>{
 const report={verdict:'Run-time Error',validatorMessage:'Wrong Answer',compileExitCode:0,executeExitCode:0,validationExitCode:43,outputs:{executionStdout:{available:true,bytes:2,text:'NO'}}};
 const html=view.render({verdict:'Wrong Answer',reports:[report]});
 assert.ok(html.includes('Official verdict: Wrong Answer'));
 assert.ok(html.includes('does not replace the official verdict'));
 assert.ok(!html.includes('Execution stdout <span class="badge rejected">Failed'));
 assert.ok(html.includes('Validator stdout <span class="badge rejected">Failed'));
 assert.ok(!view.renderTestData({number:1},{reports:[report]}).includes('Runtime failure.'));
});
test('runtime evidence is surfaced separately from an official wrong answer without mutating it',()=>{
 const data={final:true,verdict:'Wrong Answer',reports:[{verdict:'Wrong Answer',compileExitCode:0,executeExitCode:139,validationExitCode:43,outputs:{}}]};const before=JSON.stringify(data),html=view.summary(data);
 assert.ok(html.includes('Official PC² verdict'));assert.ok(html.includes('Runtime Error'));assert.ok(html.includes('exit 139'));assert.ok(html.includes('Review required'));assert.equal(JSON.stringify(data),before);
 const report=view.report(data.reports[0],0,data.verdict);assert.match(report,/Validation<\/td><td><span class="badge neutral">Not applicable/);
});
test('compiler failure and recorded time/memory/output limits are not collapsed into wrong answer or runtime',()=>{
 assert.equal(view.classifyReport({verdict:'Wrong Answer',compileExitCode:1,executeExitCode:139}).label,'Compile Error');
 for(const verdict of ['Time Limit Exceeded','Memory Limit Exceeded','Output Limit Exceeded']){const report={verdict,compileExitCode:0,executeExitCode:137};assert.equal(view.classifyReport(report).label,verdict);const html=view.renderTestData({number:1},{reports:[report]});assert.ok(html.includes(verdict));assert.ok(!html.includes('Runtime Error'));}
});
test('ICPC validator acceptance 42 is a completed validation, 43 is a wrong answer',()=>{
 const accepted={verdict:'Yes',compileExitCode:0,executeExitCode:0,validationExitCode:42};assert.equal(view.classifyReport(accepted).label,'Accepted');assert.equal(view.failures(accepted).validate,false);
 const wrong={...accepted,verdict:'No',validationExitCode:43};assert.equal(view.classifyReport(wrong).label,'Wrong Answer');
 assert.equal(view.classifyReport({...accepted,verdict:'Unspecified',validationExitCode:125}).label,'Validation failure');assert.equal(view.classifyReport({...accepted,verdict:'Wrong Answer',validationExitCode:125}).label,'Validation failure');
});
test('missing exit codes remain unknown and arbitrary stderr does not establish a runtime failure',()=>{
 const report={verdict:'Run-time Error',compileExitCode:0,executeExitCode:0,outputs:{executionStderr:{available:true,text:'Segmentation fault'}}};assert.equal(view.classifyReport(report).label,'Inconclusive');
 assert.ok(view.report({verdict:'Yes'},0,'Yes').includes('Not recorded'));
 assert.ok(!view.summary({final:true,verdict:'Wrong Answer',reports:[]}).includes('Saved execution evidence</h3><div class="evidence-badges"><span class="badge accepted"'));
});
test('summary escapes untrusted labels and retains pending human approval',()=>{
 const html=view.summary({verdict:'<svg onload=alert(1)>',awaitingApproval:true,final:false,reports:[]});assert.ok(!html.includes('<svg'));assert.ok(html.includes('provisional'));assert.ok(!html.includes('Review required'));
});
test('a stale runtime report tag is flagged without overriding zero-exit wrong-answer evidence',()=>{
 const html=view.summary({final:true,verdict:'Wrong Answer',reports:[{verdict:'Run-time Error',compileExitCode:0,executeExitCode:0,validationExitCode:43,validatorMessage:'Wrong Answer'}]});
 assert.match(html,/Saved report label discrepancy/);assert.match(html,/Saved execution evidence<\/h3><div class="evidence-badges"><span class="badge rejected">Wrong Answer/);assert.ok(!html.includes('badge rejected">Runtime Error'));
});
