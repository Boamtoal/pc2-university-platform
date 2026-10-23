/* Read-only PC² clock. Use a server timestamp and monotonic time, never the device wall clock. */
(function(root){
 'use strict';
 const maxAge=30000;
 function sample(payload,{serverDate,now=0}={}){
  const c=payload?.clock,published=Date.parse(payload?.publishedAt),server=Date.parse(serverDate);
  if(c?.schema!==1||typeof c.running!=='boolean'||!Number.isSafeInteger(c.lengthSeconds)||c.lengthSeconds<=0||!Number.isSafeInteger(c.remainingSeconds)||c.remainingSeconds<0||c.remainingSeconds>c.lengthSeconds||!Number.isFinite(published)||!Number.isFinite(server))throw new Error('Contest clock unavailable');
  // HTTP Date has whole-second precision. Never use the laptop's date to infer elapsed time.
  const age=Math.max(0,server-published);
  if(server-published< -5000||age>maxAge)throw new Error('Contest clock is stale');
  return {title:String(payload.contestStandings?.standingsHeader?.title||'Contest').slice(0,240),length:c.lengthSeconds,remaining:Math.max(0,c.remainingSeconds-(c.running?age/1000:0)),running:c.running,at:now,validFor:maxAge-age};
 }
 function view(value,now){
  if(!value||now-value.at>value.validFor)return {text:'--:--:--',status:'Reconnecting',low:false,stale:true};
  const remaining=Math.max(0,Math.ceil(value.remaining-(value.running?Math.max(0,now-value.at)/1000:0)));
  return {text:[Math.floor(remaining/3600),Math.floor(remaining/60)%60,remaining%60].map(n=>String(n).padStart(2,'0')).join(':'),status:remaining===0?'Finished':value.running?'Running':'Paused',low:remaining<=value.length*.15,stale:false,remaining};
 }
 function paint(element,value,now){
  const state=view(value,now),set=(e,t)=>{if(e.textContent!==t)e.textContent=t;};
  if(!element.querySelector('[data-clock-value]')){
   const title=document.createElement('bdi');title.dataset.clockTitle='';
   const timer=document.createElement('span');timer.className='lcpc-clock-counter';
   const label=document.createElement('span');label.textContent='Time left';
   const time=document.createElement('time');time.dataset.clockValue='';
   const status=document.createElement('span');status.dataset.clockStatus='';
   timer.append(label,time,status);element.append(title,timer);
  }
  set(element.querySelector('[data-clock-title]'),value?.title||'Contest');
  set(element.querySelector('[data-clock-value]'),state.text);set(element.querySelector('[data-clock-status]'),state.status);
  const mode=state.stale?'stale':state.remaining===0?'finished':state.low?'low':value.running?'running':'paused';
  if(element.dataset.clockState!==mode)element.dataset.clockState=mode;
  element.setAttribute('aria-label',(value?.title||'Contest')+' · Time left '+state.text+' · '+state.status);
 }
 function workspaceView(contest,kind,value,now){
  const labels={inactive:'Offline',archived:'Archived',draft:'Draft',error:'Recovery required',activating:'Starting server'};
  if(!Object.hasOwn(labels,kind))return view(value,now);
  const remaining=contest?.remainingSeconds,valid=Number.isSafeInteger(remaining)&&remaining>=0;
  const text=valid?[Math.floor(remaining/3600),Math.floor(remaining/60)%60,remaining%60].map(n=>String(n).padStart(2,'0')).join(':'):'--:--:--';
  return {text,status:labels[kind],low:false,stale:false,remaining:valid?remaining:null};
 }
 const api={sample,view,paint,workspaceView};
 if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
 root.LCPCContestClock=api;
 let value=null,busy=false,lastPoll=-Infinity,abort=null,epoch=0,metadata=[];
 Object.defineProperty(api,'problems',{get:()=>metadata});
 function hosts(){
  const team=document.querySelector('app-header>header>.teamid-container');
  if(team&&root.LCPCSession?.isAuthenticated()&&!team.querySelector('[data-contest-clock]')){const e=document.createElement('div');e.className='lcpc-contest-clock';e.dataset.contestClock='';team.append(e);}
  if(!root.LCPCSession?.isAuthenticated())document.querySelectorAll('app-header [data-contest-clock]').forEach(e=>e.remove());
  const standalone=document.querySelector('.display-brand,body.lcpc-resource-page>header');
  if(standalone&&!standalone.querySelector('[data-contest-clock]')){const e=document.createElement('div');e.className='lcpc-contest-clock';e.dataset.contestClock='';standalone.append(e);}
  return document.querySelectorAll('[data-contest-clock]');
 }
 async function poll(){
  if(busy||!hosts().length)return;
  busy=true;lastPoll=performance.now();const generation=epoch,controller=new AbortController();abort=controller;const timeout=setTimeout(()=>controller.abort(),4000);
  try{
   const response=await fetch('/standings/data.json',{credentials:'omit',cache:'no-store',signal:controller.signal});
   if(!response.ok)throw new Error('Contest clock unavailable');
   const payload=await response.json(),next=sample(payload,{serverDate:response.headers.get('Date'),now:performance.now()});
   if(generation!==epoch)return;
   value=next;
   const raw=payload.contestStandings.standingsHeader.problem,problems=Array.isArray(raw)?raw:raw?[raw]:[];
   if(JSON.stringify(problems.map(p=>[p.id,p.title,p.letter,p.colorName,p.colorRGB,p.firstToSolveTeams]))!==JSON.stringify(metadata.map(p=>[p.id,p.title,p.letter,p.colorName,p.colorRGB,p.firstToSolveTeams]))){metadata=problems;document.dispatchEvent(new Event('lcpc-contest-metadata'));}
  }catch(_){}finally{clearTimeout(timeout);if(abort===controller){busy=false;abort=null;}}
  tick();
 }
 function tick(){const elements=hosts(),now=performance.now();elements.forEach(e=>paint(e,value,now));if(elements.length&&now-lastPoll>=5000)poll();}
 document.addEventListener('lcpc-auth-change',()=>{epoch++;abort?.abort();abort=null;busy=false;value=null;metadata=[];lastPoll=-Infinity;tick();});
 document.addEventListener('DOMContentLoaded',tick);window.addEventListener('hashchange',tick);window.addEventListener('focus',()=>{lastPoll=-Infinity;tick();});document.addEventListener('visibilitychange',()=>{if(!document.hidden){lastPoll=-Infinity;tick();}});
 setInterval(tick,250);tick();
})(typeof globalThis!=='undefined'?globalThis:this);
