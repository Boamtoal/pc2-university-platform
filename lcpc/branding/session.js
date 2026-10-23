/* Keep the tab's session through temporary outages; never retain a password. */
(() => {
 'use strict';
 const key='lcpc.team-session.v1',pattern=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
 let authenticated=false,job=null,generation=0;
 const notify=()=>document.dispatchEvent(new Event('lcpc-auth-change'));
 function banner(message){
  if(!document.body)return;
  let el=document.getElementById('lcpc-session-status');
  if(!el){el=document.createElement('div');el.id='lcpc-session-status';el.setAttribute('role','status');el.setAttribute('aria-live','polite');document.body.prepend(el);}
  el.textContent=message||'';el.hidden=!message;
 }
 function cancel(){generation++;if(job){clearTimeout(job.timer);job.abort?.abort();job=null;}}
 function clear(){cancel();authenticated=false;try{sessionStorage.removeItem(key);}catch(_){}banner('');notify();}
 function save(token,username){if(!pattern.test(token)||!/^team[1-9][0-9]*$/.test(username)){clear();return;}cancel();authenticated=true;try{sessionStorage.setItem(key,JSON.stringify({token,username}));}catch(_){}banner('');notify();}
 function restore(auth){try{const saved=JSON.parse(sessionStorage.getItem(key));if(!saved||!pattern.test(saved.token)||!/^team[1-9][0-9]*$/.test(saved.username))return;auth._token=saved.token;auth._userName=saved.username;auth._lcpcRestored=true;}catch(_){clear();}}
 async function reconnect(current){
  if(job!==current||current.busy)return;current.busy=true;
  const controller=new AbortController();current.abort=controller;const timeout=setTimeout(()=>controller.abort(),6000);
  try{
   const response=await fetch('/api/teams/resources-session',{headers:{team_id:current.auth.token},credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(job!==current)return;
   if(response.status===401||response.status===403){current.socket.stopWebsocket();current.auth.completeLogout();return;}
   if(!response.ok)throw new Error('Temporary session service failure');
   authenticated=true;banner('');current.socket.startWebsocket();
   current.contest.getIsContestRunning().subscribe({next(value){if(generation===current.generation){current.contest.isContestRunning=value;current.contest.contestClock.next();}},error(){if(generation===current.generation)banner('The contest clock is temporarily unavailable. Reconnect before submitting.');}});
   notify();clearTimeout(current.timer);job=null;
  }catch(_){
   if(job!==current)return;
   banner('Connection interrupted. Your session is retained. Reconnecting… Check My submissions before retrying an upload.');
   current.attempt++;current.timer=setTimeout(()=>reconnect(current),Math.min(15000,1000*2**Math.min(current.attempt,4)));
  }finally{clearTimeout(timeout);current.busy=false;}
 }
 async function startup(auth,socket,contest){
  if(!auth._lcpcRestored)return;auth._lcpcRestored=false;cancel();authenticated=false;
  job={auth,socket,contest,generation,attempt:0,busy:false,timer:null};await reconnect(job);
 }
 addEventListener('online',()=>{if(job){clearTimeout(job.timer);reconnect(job);}});
 globalThis.LCPCSession={save,restore,clear,startup,isAuthenticated:()=>authenticated};
})();
