const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('connection alerts establish a baseline, notify new losses and cancel after sign-out',async()=>{
 const timers=[],notices=[],notifications=[],requests=[];let response={contestId:'fixture',alerts:[{id:1,event:'connection.signal_missing',team:'team1',details:{}}],cursor:1,latest:100};let release;
 class Desktop {static permission='granted';constructor(title,options){notifications.push(options.body);}}
 const window={};const sandbox={window,Notification:Desktop,localStorage:{getItem:()=> 'enabled'},URLSearchParams,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){}};vm.runInNewContext(fs.readFileSync('lcpc/admin-ui/team-connections.js','utf8'),sandbox);
 const ctx={user:{role:'owner'},getData:()=>({system:{contestId:'fixture'}}),notice:(...v)=>notices.push(v),api:async path=>{requests.push(path);return typeof response==='function'?response():response;}};
 const turn=()=>new Promise(resolve=>setImmediate(resolve));window.LCPCTeamConnections.start(ctx);await turn();assert.equal(notices.length,0,'Retained history must not replay as a new notification');
 response={contestId:'fixture',alerts:[{id:101,event:'connection.signal_missing',team:'',reported_team:'team7',ip:'192.168.10.7',details:{}}],cursor:101,latest:101};timers.shift()();await turn();assert.ok(requests[1].includes('after=100'));assert.equal(notices.length,1);assert.match(notices[0][0],/team7 \(unverified\)/);assert.equal(notifications.length,1);
 response=()=>new Promise(resolve=>{release=resolve;});timers.shift()();window.LCPCTeamConnections.stop();release({contestId:'fixture',alerts:[{id:102,event:'connection.signal_missing',team:'team1',details:{}}],cursor:102});await turn();assert.equal(notices.length,1,'A signed-out dashboard cannot show a late response');
});
