const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
async function review(colorName,workflow){
 const sandbox={window:{},URLSearchParams,LCPCNavigation:require('../../admin-ui/workspace-nav.js')};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8'),sandbox);
 const fields={DisplayName:'Fixture problem',Letter:'A',ShortName:'alpha',Active:true,ColorName:'',ColorRGB:'',ComputerJudged:true,ManualReview:false,PrelimaryNotification:false};
 const schema=Object.keys(fields).map(key=>({key,label:key,type:typeof fields[key]==='boolean'?'boolean':'text'}));
 const row={id:'fixture-problem',fingerprint:'fixture-version',fields,groups:[],password:'fixture-do-not-show'};let dialog;const writes=[];
 const ctx={user:{totpEnabled:false},getData:()=>({system:{contestId:'fixture-contest'}}),dialog:(title,html,submit)=>{dialog={title,html,submit};},close(){},notice(){},refresh:async()=>{},api:async(path,data)=>{
  if(path==='native/catalog')return {groups:[]};if(path.startsWith('native/section'))return {schema,rows:[row]};if(path==='native/execute'){writes.push(JSON.parse(JSON.stringify(data)));return {ok:true};}throw new Error(path);
 }};
 await sandbox.window.LCPCAdministrator.openEditor(ctx,'problems',row.id);
 assert.match(dialog.html,/<legend>Balloon color<\/legend>/);
 assert.equal(writes.length,0);
 const details=sandbox.window.LCPCAdministrator.readRowDetails({closest:()=>({}),querySelector:()=>({dataset:{id:row.id}})});
 assert.ok(details.fields.some(f=>f.label==='Display Name'&&f.value==='Fixture problem'));
 assert.ok(!JSON.stringify(details).includes('fixture-do-not-show'));assert.ok(!JSON.stringify(details).includes('fixture-version'));
 const values={problemWorkflow:workflow,f_ColorName:colorName};
 const elements=Object.fromEntries(Object.entries(fields).map(([key,value])=>['f_'+key,{value:key==='ColorRGB'?'#ff0000':key==='ColorName'?colorName:String(value),checked:value===true}]));
 delete elements.f_ComputerJudged;delete elements.f_ManualReview;
 const form={querySelector(selector){if(selector==='[name="groups"]')return {selectedOptions:[]};return elements[selector.match(/name="([^"]+)"/)[1]]||null;}};
 await dialog.submit(values,form);assert.equal(writes.length,0,'Reviewing a form cannot apply it');
 await dialog.submit({confirm:'CONFIRM',reason:'Isolated editor fixture'});
 return writes[0].args;
}
test('reviewing another problem setting preserves an unassigned balloon color',async()=>{
 const args=await review('','human');assert.ok(!('ColorName'in args.fields));assert.ok(!('ColorRGB'in args.fields));
 assert.equal(args.fields.ComputerJudged,false);assert.equal(args.fields.ManualReview,false);assert.equal(args.expectedFingerprint,'fixture-version');
});
test('an explicit problem color and human-approval workflow reach one reviewed operation',async()=>{
 const args=await review('Red','review');assert.equal(args.domain,'problems');assert.equal(args.fields.ColorName,'Red');assert.equal(args.fields.ColorRGB,'#ff0000');
 assert.equal(args.fields.ComputerJudged,true);assert.equal(args.fields.ManualReview,true);assert.equal(args.fields.PrelimaryNotification,false);
});

test('native account permission checkboxes preserve exactly the reviewed selection including no permissions',async()=>{
 for(const checked of [[],['LOGIN','VIEW_RUNS']]){
  const form={querySelector(selector){if(selector==='.permission-picker')return null;if(selector==='[name="groups"]')return {selectedOptions:[]};return null;},querySelectorAll(selector){assert.equal(selector,'input[name="permissions"]:checked');return checked.map(value=>({value}));}};
  const sandbox={window:{},document:{querySelector(){return form;}},LCPCNavigation:require('../../admin-ui/workspace-nav.js')};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8'),sandbox);
  const row={id:'fixture-team',type:'TEAM',fields:{},permissions:['LOGIN'],groups:[],members:[],fingerprint:'fixture'};let dialog;const writes=[];
  const ctx={user:{totpEnabled:false},getData:()=>({system:{contestId:'fixture'}}),dialog:(title,html,submit)=>{dialog={title,html,submit};},close(){},notice(){},refresh:async()=>{},api:async(path,data)=>{if(path==='native/catalog')return {groups:[],permissions:['LOGIN','VIEW_RUNS'],permissionDefaults:{TEAM:['LOGIN']}};if(path.startsWith('native/section'))return {schema:[],rows:[row]};if(path==='native/execute'){writes.push(JSON.parse(JSON.stringify(data)));return {};}throw Error(path);}};
  await sandbox.window.LCPCAdministrator.openEditor(ctx,'accounts',row.id);assert.match(dialog.html,/type="checkbox" name="permissions" value="LOGIN" checked/);assert.ok(!dialog.html.includes('<select name="permissions"'));
  await dialog.submit({newPassword:'',primaryGroup:'',members:''},form);assert.equal(writes.length,0);await dialog.submit({confirm:'CONFIRM',reason:'Fixture account permissions',password:'Fixture-owner-password'});assert.deepEqual(writes[0].args.permissions,checked);
 }
});

test('balloon deliveries render and sort real records without native ids or schema fields',async()=>{
 const sandbox={window:{},LCPCNavigation:require('../../admin-ui/workspace-nav.js')};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8'),sandbox);
 const view={innerHTML:'',textContent:''},calls=[],root={dataset:{section:'deliveries'},isConnected:true,addEventListener(){},querySelector:()=>view};
 const rows=[{team:'team10',teamName:'Team 10',letter:'C',name:'Third',problem:'p3',color:'Blue',elapsedMinutes:35,delivered:false},{team:'team2',teamName:'Team 2',letter:'B',name:'Second',problem:'p2',color:'Red',elapsedMinutes:20,delivered:true},{team:'team2',teamName:'Team 2',letter:'A',name:'First',problem:'p1',color:'Gold',elapsedMinutes:10,delivered:false}];
 await sandbox.window.LCPCAdministrator.mount(root,{getData:()=>({}),api:async name=>{calls.push(name);return name==='native/catalog'?{}:{rows};}});
 assert.equal(view.textContent,'');assert.match(view.innerHTML,/Mark delivered/);assert.match(view.innerHTML,/Mark pending/);assert.ok(view.innerHTML.indexOf('A · First')<view.innerHTML.indexOf('B · Second'));assert.ok(view.innerHTML.indexOf('B · Second')<view.innerHTML.indexOf('C · Third'));assert.deepEqual(calls,['native/catalog','native/section?section=deliveries']);
});

test('balloon delivery uses one confirmation without typing and records an audit reason',async()=>{
 const sandbox={window:{},LCPCNavigation:require('../../admin-ui/workspace-nav.js')};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8'),sandbox);
 const view={innerHTML:'',textContent:''},handlers={},calls=[],row={team:'team2',teamName:'Fixture team',letter:'A',name:'Fixture problem',problem:'p1',color:'Blue',elapsedMinutes:10,delivered:false};let modal;
 const root={dataset:{section:'deliveries'},isConnected:true,addEventListener:(name,fn)=>handlers[name]=fn,querySelector:()=>view,contains:()=>true};
 const ctx={getData:()=>({}),dialog:(title,html,submit)=>modal={title,html,submit},close(){},notice(){},refresh:async()=>{},api:async(name,data)=>{if(name==='native/catalog')return {};if(name.startsWith('native/section'))return {rows:[row]};calls.push({name,data});return {};}};
 await sandbox.window.LCPCAdministrator.mount(root,ctx);await handlers.click({target:{closest:()=>({disabled:false,dataset:{native:'delivery',id:'team2|p1'}})}});
 assert.equal(calls.length,0);assert.match(modal.html,/Confirm delivery/);assert.match(modal.html,/Fixture team/);assert.match(modal.html,/Blue/);assert.doesNotMatch(modal.html,/<input|<textarea|Type CONFIRM/);
 await modal.submit({});assert.equal(calls.length,1);assert.equal(calls[0].data.args.delivered,true);assert.equal(calls[0].data.confirm,'CONFIRM');assert.match(calls[0].data.reason,/confirmed balloon delivery/);
});

test('native feature coverage identifies read-only and external tools without offering writes',async()=>{
 const sandbox={window:{LCPCGuideContent:require('../../admin-ui/guide-content.js')},LCPCNavigation:require('../../admin-ui/workspace-nav.js')};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../admin-ui/administrator.js'),'utf8'),sandbox);
 const view={innerHTML:'',textContent:''},calls=[],root={dataset:{section:'coverage'},isConnected:true,addEventListener(){},querySelector:()=>view};
 await sandbox.window.LCPCAdministrator.mount(root,{getData:()=>({}),api:async name=>{calls.push(name);if(name!=='native/catalog')throw Error('unexpected call');return {};}});
 assert.equal(view.textContent,'');for(const text of ['Read-only','Requires external setup','Partly supported','unimplemented','compiler/runtime'])assert.ok(view.innerHTML.includes(text),text);
 assert.deepEqual(calls,['native/catalog']);assert.doesNotMatch(view.innerHTML,/data-native="(?:save|execute|create|delete)"/);
});
