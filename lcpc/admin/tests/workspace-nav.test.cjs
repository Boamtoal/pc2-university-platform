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
