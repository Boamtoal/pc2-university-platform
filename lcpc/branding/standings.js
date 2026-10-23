/* Decorate the original scoreboard using its existing, authorized XHR response. */
(()=>{
 'use strict';
 const id='lcpc-standings-branding';
 let snapshot=null,revision=0;
 const originalOpen=XMLHttpRequest.prototype.open;
 XMLHttpRequest.prototype.open=function(method,url,...rest){
  let scoreboard=false;
  try{const endpoint=new URL(url,location.href);scoreboard=endpoint.origin===location.origin && endpoint.pathname.endsWith('/api/contest/scoreboard');}catch(_){}
  if(scoreboard)this.addEventListener('load',()=>{
   try{
    if(this.status!==200){snapshot=null;revision++;update();return;}
    const data=this.responseType==='json'?this.response:JSON.parse(this.responseText);
    if(!data?.contestStandings?.standingsHeader)return;
    snapshot=data;revision++;update();
   }catch(_){snapshot=null;revision++;update();}
  },{once:true});
  return originalOpen.call(this,method,url,...rest);
 };
 const update=()=>{
  const present=document.getElementById(id);
  const route=location.hash.split('?')[0];
  if(route!=='#/scoreboard'){
   if(present)present.remove();document.getElementById('lcpc-full-standings')?.remove();
   document.querySelectorAll('.lcpc-original-standings').forEach(e=>e.classList.remove('lcpc-original-standings'));
   if(route==='#/logout'||route==='#/login')snapshot=null;
   return;
  }
  const table=document.querySelector('ng-component .filter-table-container');
  if(!table)return;
  if(!present){
  const header=document.createElement('section');header.id=id;header.className='lcpc-standings-branding';header.setAttribute('aria-label','LCPC OMU contest organizers');
  for(const [file,alt,cls] of [['lcpc-logo.png','LCPC OMU Programming Contest','lcpc-contest-logo'],['omu-logo.png','Omar Al-Mukhtar University','lcpc-university-logo']]){
   const img=document.createElement('img');img.src='/assets/lcpc-branding/'+file;img.alt=alt;img.className=cls;header.append(img);
  }
  table.before(header);
  }
  let full=document.getElementById('lcpc-full-standings');
  if(!snapshot){if(full)full.remove();table.classList.remove('lcpc-original-standings');return;}
  if(!full){full=document.createElement('section');full.id='lcpc-full-standings';full.className='lcpc-full-standings';table.before(full);}
  if(full.dataset.revision!==String(revision)){
   try{LCPCScoreboard.update(full,snapshot,{audience:true,problemMetadata:globalThis.LCPCContestClock?.problems,identityName:globalThis.LCPCParticipantIdentity?.value?.name});full.dataset.revision=String(revision);table.classList.add('lcpc-original-standings');}
   catch(_){full.remove();table.classList.remove('lcpc-original-standings');}
  }
 };
 new MutationObserver(update).observe(document.documentElement,{childList:true,subtree:true});
 document.addEventListener('lcpc-contest-metadata',()=>{revision++;update();});window.addEventListener('hashchange',update);document.addEventListener('DOMContentLoaded',update);update();
})();
