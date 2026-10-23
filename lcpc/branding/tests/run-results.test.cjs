const {test}=require('node:test');
const assert=require('node:assert/strict');
const {verdict}=require('../run-results.js');
test('PC2 verdicts retain their distinct meaning and color state',()=>{
 for(const [raw,label,state] of [
  ['Yes','Accepted','accepted'],['No - Wrong Answer','Wrong Answer','rejected'],
  ['Wrong Answer','Wrong Answer','rejected'],['','Pending','pending'],['Pending','Pending','pending'],
  ['No - Time Limit Exceeded','Time Limit Exceeded','limit'],['No - Memory Limit Exceeded','Memory Limit Exceeded','limit'],
  ['No - Compilation Error','Compilation Error','error'],['No - Run-time Error','Runtime Error','rejected'],
  ['No - Excessive Output','Output Limit Exceeded','limit'],['No - Output Format Error','Output Format Error','rejected'],
  ['No - Other - Contact Staff','Contact Staff','error'],['No','Rejected','rejected']
 ])assert.deepEqual(verdict(raw),{label,state});
 assert.equal(verdict('unrecognized judgement'),null);
});
