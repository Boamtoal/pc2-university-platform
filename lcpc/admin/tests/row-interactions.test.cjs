const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(){
 const listeners={},observers=[],nodes={},root={matches:()=>false,querySelectorAll:()=>[]};let selection='';
 const content={innerHTML:'',replaceChildren(){this.innerHTML='';}},title={},close={addEventListener(){}};
 const dialog={open:false,innerHTML:'',id:'',setAttribute(){},querySelector(s){return s==='h2'?title:s==='button'?close:content;},addEventListener(t,fn){this[t+'-event']=fn;},showModal(){this.open=true;},close(){this.open=false;this['close-event']?.();}};
 // Closing the child must not close or replace a pre-existing editor dialog.
 const parent={open:true,html:'Unsaved parent form'};
 const document={getElementById:()=>root,addEventListener(t,fn){listeners[t]=fn;},createElement:()=>dialog,body:{append(n){nodes[n.id]=n;}}};
 const win={getSelection:()=>({isCollapsed:!selection,toString:()=>selection})};
 vm.runInNewContext(fs.readFileSync('lcpc/admin-ui/row-interactions.js','utf8'),{window:win,document,MutationObserver:class{constructor(fn){observers.push(fn);}observe(){}}});
 const row=(controls={},custom=false)=>{const r={cells:[{}],tabIndex:-1,isConnected:true,dataset:{},classList:{add(){}},setAttribute(k,v){this[k]=v;},focus(){this.focused=true;},matches(s){if(s==='tr')return true;if(s.includes('data-activity-row'))return custom;return true;},closest(s){return s==='thead'?null:s.includes('tbody > tr')?r:root;},querySelector(s){return controls[s]||null;},querySelectorAll(s){return controls[s]?[controls[s]]:[];}};return r;};
 const event=r=>({target:r,key:'Enter',button:0,preventDefault(){this.defaultPrevented=true;}});
 return {api:win.LCPCRowDetails,listeners,observers,dialog,parent,content,title,row,event,setSelection(v){selection=v;}};
}
test('only explicit detail reads are delegated; editing and mutations never become row actions',()=>{
 const f=fixture();let read=0,changed=0;
 const edit={click(){changed++;}},view={click(){read++;}};
 for(const selector of ['[data-native="edit"]','[data-action="team-edit"]','[data-action="contest-open"]','[data-native="delivery"]','[data-action="session-revoke"]','[data-action="resource-delete"]'])assert.equal(f.api.detailTrigger(f.row({[selector]:edit})),null);
 assert.equal(changed,0);assert.equal(f.api.detailTrigger(f.row({'[data-action="run-details"]':view})),view);
 f.api.mount();f.listeners.click(f.event(f.row({'[data-action="run-details"]':view})));assert.equal(read,1);assert.equal(changed,0);
});
test('rows without a detail endpoint open escaped read-only values, preserving the parent form',()=>{
 const f=fixture();f.api.mount({getDetails:()=>({title:'Team details',fields:[{label:'Name',value:'<img onerror="change()">'}]})});
 f.listeners.click(f.event(f.row()));assert.equal(f.dialog.open,true);assert.equal(f.title.textContent,'Team details');assert.match(f.content.innerHTML,/&lt;img/);assert.doesNotMatch(f.content.innerHTML,/<img/);assert.equal(f.parent.open,true);assert.equal(f.parent.html,'Unsaved parent form');f.dialog.close();assert.equal(f.parent.open,true);
});
test('keyboard opens details once and nested controls, modifier clicks and text selection stay independent',()=>{
 const f=fixture();let reads=0;const r=f.row({'[data-test-case]':{click(){reads++;}}});f.api.mount();
 for(const key of ['Enter',' ']){const e=f.event(r);e.key=key;f.listeners.keydown(e);assert.equal(e.defaultPrevented,true);}assert.equal(reads,2);
 const button={closest(s){return s.includes('button')?{}:r;}};f.listeners.click({...f.event(r),target:button});assert.equal(reads,2);
 f.setSelection('copy this');f.listeners.click(f.event(r));assert.equal(reads,2);f.setSelection('');
 f.listeners.click({...f.event(r),ctrlKey:true});f.listeners.click({...f.event(r),defaultPrevented:true});assert.equal(reads,2);
});
test('existing connection/activity row handlers are not dispatched twice',()=>{
 const f=fixture();let reads=0;const r=f.row({'[data-activity="details"]':{click(){reads++;}}},true);f.api.mount();f.listeners.click(f.event(r));f.listeners.keydown(f.event(r));assert.equal(reads,0);
});
test('disabled detail handlers cannot execute and details buttons are hidden while edit remains visible',()=>{
 const f=fixture(),read={disabled:true,textContent:'Details',dataset:{}},edit={textContent:'Edit',dataset:{}};
 const r=f.row({'[data-private-test]':read,'[data-native="edit"]':edit});assert.equal(f.api.detailTrigger(r),null);f.api.decorate(r);assert.equal(read.hidden,true);assert.equal(edit.hidden,undefined);assert.equal(r.tabIndex,0);
});
test('new asynchronous list rows receive the same details-only behavior',()=>{
 const f=fixture();f.api.mount();const r=f.row();r.nodeType=1;f.observers[0]([{addedNodes:[r]}]);assert.equal(r.tabIndex,0);assert.equal(r['aria-label'],'Open record details');
});
test('balloon details show a named color swatch, rejecting unsafe color values',()=>{
 const f=fixture();f.api.mount({getDetails:()=>({title:'Problem A',fields:[{label:'Balloon',value:'Red',color:'#ff0000'},{label:'Unassigned',value:'Not assigned'},{label:'Unsafe',value:'Text',color:'" oninput="change()'}]})});
 f.listeners.click(f.event(f.row()));assert.match(f.content.innerHTML,/type="color" value="#ff0000" disabled/);assert.match(f.content.innerHTML,/>Red</);assert.match(f.content.innerHTML,/Not assigned/);assert.doesNotMatch(f.content.innerHTML,/oninput/);assert.equal((f.content.innerHTML.match(/type="color"/g)||[]).length,1);
});
test('only the local review page can be linked from the summary dialog',()=>{
 const f=fixture();f.api.showDetails({title:'Problem',fields:[],detailsUrl:'/review.html?contestId=fixture&problemId=p1'},f.row());assert.match(f.content.innerHTML,/target="_blank" rel="noopener noreferrer"/);assert.match(f.content.innerHTML,/contestId=fixture&amp;problemId=p1/);
 f.api.showDetails({title:'Unsafe',fields:[],detailsUrl:'https://outside.example/review.html'},f.row());assert.doesNotMatch(f.content.innerHTML,/href=/);
});
