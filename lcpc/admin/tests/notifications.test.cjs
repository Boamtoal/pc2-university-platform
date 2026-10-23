const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('persistent inbox polling uses a baseline, temporary notices and cancels after sign-out',async()=>{
 const timers=[],notices=[];let response={notifications:[{id:1,created:new Date().toISOString(),message:'Retained history',category:'security',severity:'warning'}],unread:1,latest:100,cursor:1};let release;
 const window={};vm.runInNewContext(fs.readFileSync('lcpc/admin-ui/notifications.js','utf8'),{window,document:{getElementById:()=>null},Date,JSON,Notification:undefined,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){}});
 const ctx={user:{role:'owner'},notice:(...args)=>notices.push(args),api:async()=>typeof response==='function'?response():response};const turn=()=>new Promise(r=>setImmediate(r));window.LCPCNotifications.start(ctx);await turn();assert.equal(notices.length,0);
 response={notifications:[{id:101,created:new Date().toISOString(),message:'team7 returned',category:'connection',severity:'success'}],unread:2,latest:101,cursor:101};timers.shift()();await turn();assert.equal(notices.length,1);assert.equal(notices[0][1],false);
 response=()=>new Promise(resolve=>{release=resolve;});timers.shift()();window.LCPCNotifications.stop();release({notifications:[{id:102,created:new Date().toISOString(),message:'Late alert',category:'security',severity:'error'}],unread:3,latest:102,cursor:102});await turn();assert.equal(notices.length,1);
});
