/* Both views use native PC² ranks. Only the public exporter feeds the display page. */
(function(root){
 'use strict';
 let current=null;
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function validate(payload,{publicView=false,now=Date.now()}={}){
  if(!payload?.contestStandings?.standingsHeader)throw new Error('Standings are unavailable.');
  const age=now-Date.parse(payload.publishedAt);
  if(!Number.isFinite(age)||age< -5000||age>30000)throw new Error('Standings updates have stopped. Waiting for a fresh PC² snapshot.');
  if(publicView&&(payload.release?.schema!==1||payload.release?.preliminaryResultsCounted!==false))throw new Error('Public standings are unavailable while preliminary scoring is enabled.');
  return payload;
 }
 function frozen(payload){return payload.release?.frozen??/frozen/i.test(payload.contestStandings.standingsHeader.scoreboardMessage||'');}
 function render(mode){
  const publicView=mode==='public';
  return '<section id="organizer-scoreboard" class="organizer-scoreboard" data-mode="'+mode+'"><div class="scoreboard-toolbar"><div><h2>'+ (publicView?'Public Scoreboard':'Live Scoreboard')+'</h2><p>'+(publicView?'Released PC² standings, including the public freeze. This is the view to share with teams.':'Private organizer view · Final results update throughout the public freeze. Pending submissions do not count as accepted.')+'</p></div><div class="scoreboard-actions">'+(publicView?'<a data-display-link class="secondary" target="_blank" rel="noopener noreferrer" hidden>Open public display</a>':'<span class="badge neutral">Internal only</span>')+'</div></div><div class="scoreboard-controls"><label>Find team<input type="search" data-team-search placeholder="Team name" autocomplete="off"></label><span data-scoreboard-state class="badge pending">Connecting</span><time data-scoreboard-updated>Waiting for data</time></div><p data-scoreboard-error class="error-banner" role="alert" hidden></p><div data-scoreboard-table class="lcpc-full-standings"></div><p class="scoreboard-legend"><span class="accepted">+ Accepted · minute shown</span><span class="rejected">− Unsuccessful attempts</span><span class="pending">? Pending / hidden during freeze</span><span>— No attempts</span></p></section>';
 }
 function dispose(){if(current){current.stopped=true;clearTimeout(current.timer);current.abort?.abort();current=null;}}
 function mount(element,context){
  dispose();const job={stopped:false,timer:null,abort:null};current=job;
  const publicView=element.dataset.mode==='public',standalone=element.hasAttribute('data-public-display'),cid=context?.data?.system?.contestId;
  element.classList.toggle('audience-scoreboard',publicView);
  const target=element.querySelector('[data-scoreboard-table]'),error=element.querySelector('[data-scoreboard-error]'),status=element.querySelector('[data-scoreboard-state]'),updated=element.querySelector('[data-scoreboard-updated]'),search=element.querySelector('[data-team-search]');
  const filter=()=>{const needle=search.value.trim().toLowerCase();target.querySelectorAll('tbody tr[data-lcpc-key]').forEach(row=>{row.hidden=!row.querySelector('.lcpc-team')?.textContent.toLowerCase().includes(needle);});};
  search.addEventListener('input',filter);
  element.querySelector('[data-fullscreen]')?.addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(_){error.hidden=false;error.textContent='Use your browser’s full-screen command to expand the display.';}});
  async function refresh(){
   if(job.stopped||!element.isConnected)return;
   try{
    let value;
    if(standalone){job.abort=new AbortController();const timeout=setTimeout(()=>job.abort.abort(),10000);try{const response=await fetch('./data.json',{credentials:'omit',cache:'no-store',signal:job.abort.signal});if(!response.ok)throw new Error('Public standings are unavailable.');value={payload:await response.json(),mode:'public',checkedAt:response.headers.get('Date')};}finally{clearTimeout(timeout);}}
    else value=await context.api('scoreboards/'+(publicView?'public':'live')+'?contestId='+encodeURIComponent(cid));
    if(job.stopped||!element.isConnected)return;
    if(!standalone&&(value.contestId!==cid||context.getData().system.contestId!==cid))throw new Error('The selected contest changed. Refresh this workspace.');
    if(value.mode!==(publicView?'public':'live'))throw new Error('Unexpected scoreboard view.');
    const payload=validate(value.payload,{publicView,now:value.checkedAt?Date.parse(value.checkedAt):Date.now()});
    root.LCPCScoreboard.update(target,payload,{strictStyles:true,audience:publicView,identityName:root.LCPCParticipantIdentity?.value?.name});root.LCPCRowDetails?.decorate(target);filter();
    const isFrozen=publicView&&frozen(payload);status.textContent=isFrozen?'Frozen':publicView?'Public · Released':'Live · No freeze';status.className='badge '+(isFrozen?'pending':'accepted');if(standalone){status.textContent=isFrozen?'Standings frozen':'';status.hidden=!isFrozen;const title=document.querySelector('[data-display-contest-title]');if(title)title.textContent=payload.contestStandings.standingsHeader.title||'Contest standings';}
    const date=new Date(payload.publishedAt);updated.dateTime=payload.publishedAt;updated.textContent='Last updated: '+date.toLocaleString('en-GB',{hour12:false});
    const link=element.querySelector('[data-display-link]');
    if(link){link.hidden=!value.displayUrl;if(value.displayUrl)link.href=value.displayUrl;else link.removeAttribute('href');}
    error.hidden=true;
   }catch(e){
    if(job.stopped||!element.isConnected)return;
    target.replaceChildren();status.hidden=false;status.textContent='Updates unavailable';status.className='badge rejected';error.textContent=e.message||'Standings are unavailable.';error.hidden=false;
   }finally{if(!job.stopped&&element.isConnected)job.timer=setTimeout(refresh,5000);}
  }
  refresh();return dispose;
 }
 const api={render,mount,dispose,validate,frozen};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else{
  root.LCPCOrganizerScoreboards=api;
  const page=document.querySelector('[data-public-display]');if(page)mount(page);
 }
})(typeof globalThis!=='undefined'?globalThis:this);
