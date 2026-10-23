const test=require('node:test'),assert=require('node:assert/strict');
const {sample,view,workspaceView}=require('../contest-clock.js');
const publishedAt='2026-10-20T10:00:00.000Z';
const fixture=(remainingSeconds=1800,running=true,lengthSeconds=7200)=>({publishedAt,clock:{schema:1,remainingSeconds,running,lengthSeconds},contestStandings:{standingsHeader:{title:'Fixture contest'}}});
const read=p=>sample(p,{serverDate:publishedAt,now:1000});
test('running countdown moves each second and becomes red at precisely 15% of total duration',()=>{
 const c=read(fixture(1081));assert.equal(view(c,1000).text,'00:18:01');assert.equal(view(c,1000).low,false);assert.equal(view(c,2000).text,'00:18:00');assert.equal(view(c,2000).low,true);assert.equal(view(c,3000).text,'00:17:59');
});
test('pause, resume, reset and extension rebase to the native clock instead of the previous countdown',()=>{
 assert.equal(view(read(fixture(900,false)),20000).text,'00:15:00');assert.equal(view(read(fixture(900,false)),20000).status,'Paused');
 assert.equal(view(read(fixture(900,true)),6000).text,'00:14:55');
 assert.equal(view(read(fixture(1200,true,7500)),1000).low,false);
 assert.equal(view(read(fixture(7200,false)),1000).text,'02:00:00');
 assert.equal(view(read(fixture(0,false)),1000).status,'Finished');assert.equal(view(read(fixture(1)),3000).text,'00:00:00');
});
test('server Date accounts for snapshot delay without trusting the laptop date; stale data expires',()=>{
 const c=sample(fixture(),{serverDate:'2026-10-20T10:00:05Z',now:50});assert.equal(view(c,50).text,'00:29:55');assert.equal(view(c,25051).stale,true);
 assert.equal(view(null,5).status,'Reconnecting');assert.equal(view(read(fixture()),32000).stale,true);
 assert.throws(()=>sample(fixture(),{serverDate:'2026-10-20T10:00:31Z'}));assert.throws(()=>sample(fixture(),{serverDate:'2026-10-20T09:59:54Z'}));
});
test('invalid, missing or impossible native clock data is never shown as an active countdown',()=>{
 for(const change of [{clock:null},{clock:{schema:1,running:'true',remainingSeconds:30,lengthSeconds:60}},{clock:{schema:1,running:true,remainingSeconds:-1,lengthSeconds:60}},{clock:{schema:1,running:true,remainingSeconds:61,lengthSeconds:60}},{publishedAt:'bad'}])assert.throws(()=>read({...fixture(),...change}));
});
test('stopped server shows its retained time without claiming to reconnect or counting down',()=>{
 const retained={remainingSeconds:900,running:true};
 assert.equal(workspaceView(retained,'inactive',null,500000).status,'Offline');
 assert.equal(workspaceView(retained,'inactive',null,900000).text,'00:15:00');
 assert.equal(workspaceView(retained,'archived',null,900000).status,'Archived');
 assert.equal(workspaceView(retained,'active',null,900000).status,'Reconnecting');
 assert.equal(workspaceView(retained,'active',read(fixture()),2000).text,'00:29:59');
});
