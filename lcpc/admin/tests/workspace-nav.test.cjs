const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const nav=require('../../admin-ui/workspace-nav.js');
test('every administrator capability has one contextual destination',()=>{
 const script=fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8');
 const names=script.match(/const names=(\{[^\n]+\});/)[1];
 const capabilities=Object.keys(vm.runInNewContext('('+names+')'));
 assert.deepEqual(Object.keys(nav.home).sort(),capabilities.sort());
 const destinations=new Set();
 for(const [page,items]of Object.entries(nav.views))for(const [view,,kind]of items){
  if(view==='main'||kind==='local')continue;
  assert.ok(!destinations.has(view),'Duplicate home for '+view);destinations.add(view);
  assert.equal(nav.home[view],page);
 }
 assert.equal(nav.home.problems,'problems');
 assert.ok(!nav.sections.some(([id])=>id==='native'));
});
test('colors and private tests belong to problems, judging and results stay distinct',()=>{
 assert.equal(nav.home.tests,'problems');assert.equal(nav.home.languages,'problems');
 assert.equal(nav.home.autojudges,'judging');assert.equal(nav.home.judgements,'judging');
 assert.equal(nav.home.balloons,'scoreboard');assert.equal(nav.home.deliveries,'scoreboard');
 assert.equal(nav.home.reports,'exports');assert.equal(nav.home.reset,'contests');
});
test('non-owner navigation never selects an owner-only subview',()=>{
 for(const [page,items]of Object.entries(nav.views))for(const [view]of items){
  assert.ok(nav.available(page,false).every(([id])=>id==='main'));
  assert.equal(nav.current(page,view,false),'main');
 }
});
test('remembered tools remain scoped to their own section',()=>{
 assert.equal(nav.current('problems','tests',true),'tests');
 assert.equal(nav.current('problems','accounts',true),'main');
 assert.equal(nav.current('system','missing',true),'participant-test');
 const ids=nav.sections.map(([id])=>id);assert.equal(new Set(ids).size,ids.length);
 for(const page of Object.keys(nav.views))assert.ok(ids.includes(page));
});
test('each sidebar section uses a consistent, self-contained semantic SVG icon',()=>{
 const seen=new Set();for(const [id,icon] of nav.sections){assert.equal(icon,id);const svg=nav.icon(icon);assert.match(svg,/viewBox="0 0 24 24"/);assert.match(svg,/stroke="currentColor"/);assert.match(svg,/aria-hidden="true"/);assert.doesNotMatch(svg,/<script|href=|onload=/);assert.ok(!seen.has(svg));seen.add(svg);}
});

test('a browser refresh restores the account section, nested tab and scroll position',()=>{
 const data=new Map(),storage={setItem:(k,v)=>data.set(k,v),getItem:k=>data.get(k)};
 nav.remember(storage,'owner','scoreboard','deliveries',[0,420]);
 assert.deepEqual(nav.restore(storage,'owner',true),{tab:'scoreboard',views:{scoreboard:'deliveries'},scroll:[0,420]});
 assert.deepEqual(nav.restore(storage,'another-owner',true),{tab:'overview',views:{},scroll:null});
});
test('restoring a workspace never revives a tab forbidden by current permissions',()=>{
 const data=new Map(),storage={setItem:(k,v)=>data.set(k,v),getItem:k=>data.get(k)};
 nav.remember(storage,'changed-role','scoreboard','deliveries',[0,0]);assert.equal(nav.restore(storage,'changed-role',false).views.scoreboard,'main');
 nav.remember(storage,'changed-role','security','main',[0,0]);assert.equal(nav.restore(storage,'changed-role',false).tab,'overview');
 nav.remember(storage,'changed-role','missing-page','main',[0,0]);assert.equal(nav.restore(storage,'changed-role',true).tab,'overview');
});
test('missing, corrupt or blocked browser storage cannot prevent dashboard sign-in',()=>{
 for(const storage of [null,{getItem:()=>'{invalid'},{getItem(){throw Error('Blocked');},setItem(){throw Error('Blocked');}}]){
  assert.equal(nav.restore(storage,'owner',true).tab,'overview');assert.doesNotThrow(()=>nav.remember(storage,'owner','guide','main',[0,0]));
 }
});
