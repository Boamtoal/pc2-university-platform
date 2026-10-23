const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('event rows open details with pointer or keyboard while buttons and text selection stay independent',()=>{
 let selected=false,count=0,prevented=0;const listeners={};const root={addEventListener(type,fn){listeners[type]=fn;}};const row={querySelector(){return {click(){count++;}};}};
 const win={getSelection:()=>({isCollapsed:!selected})};vm.runInNewContext(fs.readFileSync('lcpc/admin-ui/participant-activity.js','utf8'),{window:win});win.LCPCParticipantActivity.bindRows(root);
 const target={closest(selector){return selector==='[data-activity-row]'?row:null;},matches:()=>true,querySelector:row.querySelector};
 listeners.click({target});assert.equal(count,1);
 listeners.keydown({target,key:'Enter',preventDefault(){prevented++;}});listeners.keydown({target,key:' ',preventDefault(){prevented++;}});assert.equal(count,3);assert.equal(prevented,2);
 selected=true;listeners.click({target});assert.equal(count,3);selected=false;
 target.closest=selector=>selector==='[data-activity-row]'?row:{};listeners.click({target});assert.equal(count,3,'Nested actions must not open row details');
});
