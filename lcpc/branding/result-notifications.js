/* Final participant verdicts across the app and standalone pages. No judge evidence. */
(function(root){
 'use strict';
 const validId=id=>/^[1-9][0-9]{0,9}(?:-[1-9][0-9]{0,9})?$/.test(String(id));
 function result(value){
  const raw=String(value||'').trim().replace(/^No\s*[-–—:]\s*/i,''),key=raw.toLowerCase();
  if(!key||/pending|preliminary|awaiting|queued|judging/i.test(key))return null;
  const names={yes:'Accepted',ac:'Accepted',correct:'Accepted',accepted:'Accepted',no:'Wrong Answer',wa:'Wrong Answer','wrong answer':'Wrong Answer',ce:'Compilation Error','compile error':'Compilation Error','compilation error':'Compilation Error',re:'Runtime Error',rte:'Runtime Error','run-time error':'Runtime Error','runtime error':'Runtime Error',tle:'Time Limit Exceeded',mle:'Memory Limit Exceeded',eo:'Output Limit Exceeded','excessive output':'Output Limit Exceeded',ofe:'Output Format Error'};
  const label=names[key]||raw.slice(0,160);return {label,accepted:label==='Accepted'};
 }
 function tracker(storage,scope){
  if(!/^[a-f0-9]{64}$/.test(scope))throw new Error('Invalid result scope');
  const prefix='lcpc.results.v1.'+scope+'.';let ids=[];
  const read=key=>{try{return JSON.parse(storage.getItem(prefix+key));}catch(_){return null;}};
  const write=(key,value)=>storage.setItem(prefix+key,JSON.stringify(value));
  function ingest(rows,hints=new Set()){
   const initial=read('initialized')!==true;ids=[];
   for(const row of rows){
    if(!validId(row.id))continue;const id=String(row.id);ids.push(id);
    const verdict=row.final===true?result(row.verdict):null,signature=verdict?'final:'+verdict.label:'pending',old=read('run.'+id);
    if(old?.signature===signature)continue;
    const revision=(Number.isSafeInteger(old?.revision)?old.revision:0)+1;
    const notice=verdict&&(!initial||old||hints.has(id))?{id,revision,problem:String(row.problem||'').slice(0,200),language:String(row.language||'').slice(0,120),label:verdict.label,accepted:verdict.accepted,updated:!!old&&old.signature!=='pending'}:null;
    write('run.'+id,{signature,revision,notice});
   }
   write('initialized',true);
  }
  function pending(){return ids.map(id=>read('run.'+id)?.notice).filter(Boolean).sort((a,b)=>a.id.localeCompare(b.id,undefined,{numeric:true}));}
  function acknowledge(notice){const key='run.'+notice.id,entry=read(key);if(entry?.notice?.revision===notice.revision){entry.notice=null;write(key,entry);}}
  return {ingest,pending,acknowledge,prefix};
 }
 const api={result,tracker};
 if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
 const memory=new Map(),storage={getItem:k=>{try{return localStorage.getItem(k)??memory.get(k)??null;}catch(_){return memory.get(k)??null;}},setItem:(k,v)=>{memory.set(k,v);try{localStorage.setItem(k,v);}catch(_){}},removeItem:k=>{memory.delete(k);try{localStorage.removeItem(k);}catch(_){}}};
 let scope='',model=null,dialog=null,current=null,busy=false,abort=null,generation=0,timer=null,leaseAt=0,opening=false,hints=new Set();
 const instance=typeof crypto.randomUUID==='function'?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
 function token(){try{const v=JSON.parse(sessionStorage.getItem('lcpc.team-session.v1'));return /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v?.token)?v.token:'';}catch(_){return '';}}
 function allowed(){if(root.LCPCSession)return root.LCPCSession.isAuthenticated();if(root.LCPCActivity)return root.LCPCActivity.authenticated;return !!token();}
 function lease(){try{return JSON.parse(storage.getItem(model.prefix+'presenter'));}catch(_){return null;}}
 function release(){if(model&&lease()?.owner===instance)storage.removeItem(model.prefix+'presenter');leaseAt=0;}
 function hide(){if(dialog?.open)dialog.close();current=null;release();}
 function reset(){generation++;abort?.abort();abort=null;busy=false;hide();model=null;scope='';hints.clear();}
 function acknowledge(){if(current&&model)model.acknowledge(current);hide();setTimeout(present,50);}
 function createDialog(){
  dialog=document.createElement('dialog');dialog.id='lcpc-result-dialog';dialog.setAttribute('aria-labelledby','lcpc-result-title');dialog.setAttribute('aria-describedby','lcpc-result-description');
  dialog.innerHTML='<div class="lcpc-result-heading"><span class="lcpc-result-icon" aria-hidden="true"></span><button type="button" class="lcpc-result-dismiss" aria-label="Close result">×</button></div><p class="lcpc-result-eyebrow">Submission result</p><h2 id="lcpc-result-title"></h2><p id="lcpc-result-description"></p><dl><dt>Submission</dt><dd data-result-id></dd><dt>Problem</dt><dd data-result-problem></dd><dt>Language</dt><dd data-result-language></dd></dl><div class="lcpc-result-actions"><small data-result-queue></small><button type="button" class="lcpc-result-close">Close</button></div>';
  dialog.querySelector('.lcpc-result-dismiss').addEventListener('click',acknowledge);dialog.querySelector('.lcpc-result-close').addEventListener('click',acknowledge);
  dialog.addEventListener('cancel',event=>{event.preventDefault();acknowledge();});document.body.append(dialog);
 }
 async function present(){
  if(!model||!document.body||document.hidden||!allowed()||opening)return;
  if(current){
   const owner=lease();if(owner&&owner.owner!==instance&&owner.until>Date.now()){hide();return;}
   if(!model.pending().some(n=>n.id===current.id&&n.revision===current.revision)){hide();return;}
   if(Date.now()-leaseAt>2000){storage.setItem(model.prefix+'presenter',JSON.stringify({owner:instance,until:Date.now()+6000}));leaseAt=Date.now();}return;
  }
  if(document.querySelector('dialog[open]'))return;
  const notices=model.pending();if(!notices.length)return;
  const active=lease();if(active&&active.owner!==instance&&active.until>Date.now())return;
  opening=true;const original=model;
  storage.setItem(model.prefix+'presenter',JSON.stringify({owner:instance,until:Date.now()+6000}));
  await new Promise(resolve=>setTimeout(resolve,40));opening=false;
  if(model!==original||document.hidden||!allowed()||lease()?.owner!==instance)return;
  const notice=model.pending()[0];if(!notice){release();return;}
  if(!dialog)createDialog();current=notice;leaseAt=Date.now();dialog.dataset.result=notice.accepted?'accepted':'rejected';
  dialog.querySelector('.lcpc-result-icon').textContent=notice.accepted?'✓':'×';dialog.querySelector('h2').textContent=notice.label;
  dialog.querySelector('#lcpc-result-description').textContent=notice.updated?'The final judgement for this submission has been updated.':notice.accepted?'Your solution has been accepted.':'Your solution was not accepted. The final verdict is shown above.';
  dialog.querySelector('[data-result-id]').textContent='#'+notice.id;dialog.querySelector('[data-result-problem]').textContent=notice.problem||'Problem';dialog.querySelector('[data-result-language]').textContent=notice.language||'—';dialog.querySelector('[data-result-queue]').textContent=notices.length>1?notices.length+' results to review':'';
  dialog.showModal();dialog.querySelector('.lcpc-result-close').focus();
 }
 function schedule(delay=2000){clearTimeout(timer);timer=setTimeout(poll,delay);}
 async function poll(){
  if(busy)return;if(!allowed()){schedule(10000);return;}
  busy=true;const epoch=generation,controller=new AbortController();abort=controller;const timeout=setTimeout(()=>controller.abort(),4500);let delay=document.hidden?5000:2000;
  try{
   const t=token(),response=await fetch('/api/teams/result-notifications',{credentials:'same-origin',cache:'no-store',headers:t?{team_id:t}:{},signal:controller.signal});
   if(response.status===401||response.status===403){if(epoch===generation)reset();delay=15000;return;}
   if(!response.ok)throw new Error('Results unavailable');const value=await response.json();
   if(epoch!==generation)return;if(value.schema!==1||!Array.isArray(value.runs)||value.runs.length>10000)throw new Error('Invalid results');
   if(scope!==value.scope){hide();scope=value.scope;model=tracker(storage,scope);}
   model.ingest(value.runs,hints);hints.clear();present();
  }catch(_){delay=5000;}finally{clearTimeout(timeout);if(abort===controller){abort=null;busy=false;}schedule(delay);}
 }
 api.wake=id=>{if(validId(id))hints.add(String(id));clearTimeout(timer);poll();};root.LCPCResultNotifications=api;
 document.addEventListener('lcpc-auth-change',()=>{reset();schedule(0);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)hide();else{present();schedule(0);}});
 window.addEventListener('focus',()=>schedule(0));window.addEventListener('hashchange',()=>{present();schedule(0);});window.addEventListener('storage',()=>present());window.addEventListener('pagehide',hide);
 setInterval(present,500);if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>schedule(0));else schedule(0);
})(typeof globalThis!=='undefined'?globalThis:this);
