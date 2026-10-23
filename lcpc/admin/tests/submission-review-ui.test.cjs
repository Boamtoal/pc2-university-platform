const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('lcpc/admin-ui/app.js','utf8');
function fn(name,next){return source.slice(source.indexOf('function '+name+'('),source.indexOf('\n function '+next+'('));}
function fixture(filters={}){
 const data={teams:[{login:'team1',name:'Official'},{login:'team99999',name:'Diagnostic',testAccount:true}],problems:[],judging:{mode:'review'},runs:[
  {number:1,team:'team1',teamName:'Official',final:false,workflowState:'Awaiting human approval',verdict:'Awaiting human approval'},
  {number:2,team:'team1',teamName:'Official',final:true,workflowState:'Final',verdict:'Accepted'},
  {number:3,team:'team1',teamName:'Official',final:false,workflowState:'Pending',verdict:'Pending'},
  {number:4,team:'team99999',teamName:'Diagnostic',testAccount:true,final:false,workflowState:'Awaiting human approval',verdict:'Awaiting human approval'}]};
 const ctx={state:{data,filters},owner:()=>false,esc:String,option:(v,label)=>'<option>'+label+'</option>',button:(action,label)=>'<button>'+label+'</button>',runTable:rows=>JSON.stringify(rows),panel:(title,body)=>'<section>'+title+body+'</section>',status:v=>v==='Accepted'?['Accepted','accepted']:['Pending','pending'],workflowLabels:{review:'Automatic + human approval'}};
 vm.createContext(ctx);vm.runInContext(fn('reviewHelp','judging')+'\n'+fn('runs','teams')+'\n'+fn('judging','controls'),ctx);return ctx;
}
test('official submissions are the default and test attempts have a separate explicit filter',()=>{
 let c=fixture();let html=c.runs();assert.match(html,/"number":1/);assert.doesNotMatch(html,/"number":4/);
 c=fixture({account:'test'});html=c.runs();assert.match(html,/"number":4/);assert.doesNotMatch(html,/"number":1/);
});
test('review queue excludes final, executing and diagnostic submissions',()=>{
 const html=fixture().judging();assert.match(html,/Pending human review \(1\)/);assert.match(html,/"number":1/);
 for(const n of [2,3,4])assert.doesNotMatch(html,new RegExp('"number":'+n));
});
test('awaiting-human filter retains only submissions ready for a human decision',()=>{
 const html=fixture({verdict:'review'}).runs();assert.match(html,/"number":1/);for(const n of [2,3,4])assert.doesNotMatch(html,new RegExp('"number":'+n));
 assert.match(html,/Confirming an automatic Wrong Answer rejects the solution/);
});
