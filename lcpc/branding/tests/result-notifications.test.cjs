const test=require('node:test'),assert=require('node:assert/strict');
const {tracker,result}=require('../result-notifications.js');
const scope='a'.repeat(64),row=(id,final=false,verdict='')=>({id,final,verdict,problem:'A · Problem',language:'C++17'});
function memory(){const data=new Map();return {getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};}
test('preliminary and pending judgements never become final result dialogs',()=>{
 const t=tracker(memory(),scope);t.ingest([row('1-1',false,'Accepted')]);assert.equal(t.pending().length,0);
 t.ingest([row('1-1',false,'Wrong Answer')]);assert.equal(t.pending().length,0);
 for(const v of ['Pending','Awaiting human approval','Preliminary Accepted','Judging'])assert.equal(result(v),null);
 t.ingest([row('1-1',true,'Accepted')]);assert.equal(t.pending()[0].label,'Accepted');assert.equal(t.pending()[0].accepted,true);
});
test('acknowledgement survives page changes and refresh; an unseen verdict stays queued',()=>{
 const s=memory(),a=tracker(s,scope);a.ingest([row('1-1')]);a.ingest([row('1-1',true,'Wrong Answer')]);
 const b=tracker(s,scope);b.ingest([row('1-1',true,'Wrong Answer')]);assert.equal(b.pending().length,1);b.acknowledge(b.pending()[0]);
 a.ingest([row('1-1',true,'Wrong Answer')]);assert.equal(a.pending().length,0);
 const c=tracker(s,scope);c.ingest([row('1-1',true,'Wrong Answer')]);assert.equal(c.pending().length,0);
});
test('initial sign-in suppresses old results but a fresh WebSocket event or new final run is announced',()=>{
 const t=tracker(memory(),scope);t.ingest([row('1-1',true,'Accepted'),row('2-1',true,'Wrong Answer')],new Set(['2-1']));
 assert.deepEqual(t.pending().map(n=>n.id),['2-1']);t.acknowledge(t.pending()[0]);
 t.ingest([row('1-1',true,'Accepted'),row('2-1',true,'Wrong Answer'),row('3-1',true,'Runtime Error')]);assert.equal(t.pending()[0].label,'Runtime Error');assert.equal(t.pending()[0].accepted,false);
});
test('rejudging and a changed final verdict produce a new notification, identical repeated events do not',()=>{
 const t=tracker(memory(),scope);t.ingest([row('1-1')]);t.ingest([row('1-1',true,'Accepted')]);const old=t.pending()[0];t.acknowledge(old);
 t.ingest([row('1-1',true,'Yes')],new Set(['1-1']));assert.equal(t.pending().length,0);
 t.ingest([row('1-1',true,'Wrong Answer')]);assert.equal(t.pending()[0].updated,true);assert.ok(t.pending()[0].revision>old.revision);t.acknowledge(old);assert.equal(t.pending().length,1);t.acknowledge(t.pending()[0]);
 t.ingest([row('1-1')]);t.ingest([row('1-1',true,'Wrong Answer')]);assert.equal(t.pending().length,1);
});
test('contest/session scopes keep other team results private and multiple results queue independently',()=>{
 const s=memory(),a=tracker(s,scope),b=tracker(s,'b'.repeat(64));a.ingest([]);a.ingest([row('2-1',true,'CE'),row('1-1',true,'Yes')]);
 assert.deepEqual(a.pending().map(n=>n.label),['Accepted','Compilation Error']);b.ingest([row('1-1',true,'Yes')]);assert.equal(b.pending().length,0);assert.equal(a.pending().length,2);
});
test('malformed identifiers are ignored and labels are normalized with fixed semantic colors',()=>{
 const t=tracker(memory(),scope);t.ingest([]);t.ingest([row('<script>',true,'Yes')]);assert.equal(t.pending().length,0);
 for(const v of ['Wrong Answer','Runtime Error','Compilation Error','Time Limit Exceeded','Memory Limit Exceeded','No - Wrong Answer'])assert.equal(result(v).accepted,false);
 assert.equal(result('No').label,'Wrong Answer');assert.equal(result('Yes').accepted,true);
});
