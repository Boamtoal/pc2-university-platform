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
