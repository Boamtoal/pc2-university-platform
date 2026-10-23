(() => {
 'use strict';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let job=null,panel=null,button=null,filterTimer=null;
 function stop(){if(job){clearTimeout(job.timer);job=null;}clearTimeout(filterTimer);if(panel){panel.hidden=true;panel.querySelector('[data-notification-list]').replaceChildren();}if(button){button.hidden=true;button.setAttribute('aria-expanded','false');}}
 function showBadge(value){if(!button)return;const badge=button.querySelector('[data-notification-badge]');badge.hidden=!value;badge.textContent=value>999?'999+':String(value);button.setAttribute('aria-label','Notifications, '+value+' unread');}
 function ensure(ctx){
  button=document.getElementById('notification-bell');if(!button)return;
  if(panel)return;
  panel=document.createElement('aside');panel.id='notification-center';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Notifications');
  panel.innerHTML='<header class="notification-heading"><div><h2>Notifications</h2><p>Security, participant warnings and connection history</p></div><button type="button" data-notification-close aria-label="Close notifications">×</button></header><div class="notification-filters"><label>Search notifications<input type="search" name="search" placeholder="Team, IP or message"></label><label>Category<select name="category"><option value="">All categories</option><option value="connection">Connections</option><option value="security">Security</option><option value="participant">Participant warnings</option></select></label><label class="check-field"><input type="checkbox" name="unread">Unread only</label><label class="check-field"><input type="checkbox" name="archived">Include archived diagnostics</label><button type="button" data-notification-read-all>Mark all as read</button></div><p data-notification-status class="hint" role="status"></p><div data-notification-list></div><button type="button" data-notification-older hidden>Older notifications</button><p class="notification-note">Reading a notification keeps it in history. Resolve incidents separately in Security & Logs or Participant activity.</p>';
  document.body.append(panel);
  button.addEventListener('click',()=>{if(!job)return;panel.hidden=!panel.hidden;button.setAttribute('aria-expanded',String(!panel.hidden));if(!panel.hidden){load(job);panel.querySelector('input[type=search]').focus({preventScroll:true});}});
  function close(){panel.hidden=true;button.setAttribute('aria-expanded','false');button.focus({preventScroll:true});}
  panel.querySelector('[data-notification-close]').addEventListener('click',close);
  panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();close();}});
  panel.addEventListener('input',()=>{clearTimeout(filterTimer);filterTimer=setTimeout(()=>job&&load(job),200);});
  panel.addEventListener('change',e=>{if(e.target.matches('select,input[type=checkbox]'))job&&load(job);});
  panel.addEventListener('click',async e=>{
   const s=job;if(!s)return;const control=e.target.closest('[data-notification-id],[data-notification-read-all],[data-notification-older]');if(!control)return;control.disabled=true;
   try{
    if(control.hasAttribute('data-notification-older')){if(s.before)await load(s,s.before);return;}
    if(control.hasAttribute('data-notification-read-all')){if(s.latest)await s.ctx.api('notifications/read',{through:s.latest});await load(s);await poll(s);return;}
    const id=Number(control.dataset.notificationId),row=s.rows?.find(v=>v.id===id);if(!row)return;
    const detail=control.closest('.notification-item').querySelector('[data-notification-details]');detail.hidden=!detail.hidden;control.setAttribute('aria-expanded',String(!detail.hidden));
    if(!detail.hidden&&!row.read_at){await s.ctx.api('notifications/read',{id});row.read_at=new Date().toISOString();control.closest('.notification-item').classList.remove('is-unread');await poll(s);}
   }catch(error){s.ctx.notice(error.message,true);}finally{control.disabled=false;}
  });
 }
 function parameters(before){const q=new URLSearchParams();for(const key of ['search','category']){const v=panel.querySelector('[name='+key+']').value.trim();if(v)q.set(key,v);}if(panel.querySelector('[name=unread]').checked)q.set('unread','1');if(panel.querySelector('[name=archived]').checked)q.set('archived','1');if(before)q.set('before',before);return q.toString();}
 async function load(s,before){
  if(job!==s||!panel)return;const ticket=++s.loadTicket;const status=panel.querySelector('[data-notification-status]');
  try{
   const data=await s.ctx.api('notifications?'+parameters(before));if(job!==s||ticket!==s.loadTicket)return;s.latest=data.latest;s.before=data.before;s.more=data.more;s.rows=data.notifications;showBadge(data.unread);
   panel.querySelector('[data-notification-list]').innerHTML=data.notifications.length?data.notifications.map(row=>'<article class="notification-item '+(!row.read_at?'is-unread':'')+'"><button type="button" class="notification-summary" data-notification-id="'+row.id+'" aria-expanded="false"><span class="badge '+(row.severity==='error'?'rejected':row.severity==='warning'?'pending':row.severity==='success'?'accepted':'neutral')+'">'+esc(row.category)+'</span><strong>'+esc(row.title)+'</strong><span>'+esc(row.message)+(row.occurrences>1?' · '+row.occurrences+' occurrences':'')+(row.archived?' · Archived diagnostic':'')+'</span><small>'+esc(s.ctx.date(row.created))+' · '+esc(row.contest_id||'Dashboard')+'</small></button><div data-notification-details hidden><dl><dt>Source</dt><dd>'+esc(row.category)+'</dd><dt>Contest</dt><dd>'+esc(row.contest_id||'Dashboard')+'</dd><dt>Event</dt><dd>'+esc(row.details.event||'Security alert')+'</dd><dt>Team</dt><dd>'+esc(row.details.team||row.details.reportedTeam||'Not specified')+'</dd><dt>IP</dt><dd>'+esc(row.details.ip||'Not recorded')+'</dd></dl>'+((row.details.event||'')==='connection.signal_missing'?'<p class="hint">The browser signal stopped. A suspended or closed tab can also cause this; it does not by itself prove a network outage.</p>':'')+'<pre class="code">'+esc(JSON.stringify(row.details.details||row.details,null,2))+'</pre></div></article>').join(''):'<p class="empty">No notifications match these filters.</p>';
   panel.querySelector('[data-notification-older]').hidden=!data.more;status.textContent=data.unread+' unread · Updated '+s.ctx.date(data.checkedAt);s.browsingOlder=!!before;
  }catch(error){if(job===s)status.textContent='Notification history unavailable: '+error.message;}
 }
 async function poll(s){
  if(job!==s)return;clearTimeout(s.timer);
  try{
   const data=await s.ctx.api('notifications?after='+s.cursor);if(job!==s)return;showBadge(data.unread);s.latest=data.latest;
   if(s.ready)for(const row of data.notifications){
    if(Date.now()-Date.parse(row.created)>60000)continue;
    s.ctx.notice(row.message,row.severity==='warning'||row.severity==='error');
    if(row.category==='connection'&&row.severity!=='success'&&typeof Notification!=='undefined'&&Notification.permission==='granted'&&localStorage.getItem('lcpc.connection-notifications')==='enabled'){try{new Notification('Team connection alert',{body:row.message,tag:'lcpc-notification-'+row.id});}catch(_){}}
   }
   s.cursor=s.ready?data.cursor:data.latest;s.ready=true;
   button?.removeAttribute('data-unavailable');
   if(panel&&!panel.hidden&&!s.browsingOlder&&s.openedOnce){const focused=panel.contains(document.activeElement),expanded=panel.querySelector('[data-notification-details]:not([hidden])');if(!focused&&!expanded)await load(s);}
   s.openedOnce=true;
  }catch(error){if(job===s&&button){button.setAttribute('data-unavailable','true');button.setAttribute('aria-label','Notifications unavailable');if(panel&&!panel.hidden)panel.querySelector('[data-notification-status]').textContent='Notification updates unavailable: '+error.message;}}
  finally{if(job===s)s.timer=setTimeout(()=>poll(s),5000);}
 }
 function start(ctx){if(ctx.user?.role!=='owner'){stop();return;}if(job){job.ctx=ctx;return;}ensure(ctx);if(button)button.hidden=false;const s=job={ctx,cursor:0,ready:false,timer:null,loadTicket:0,latest:0,before:null,browsingOlder:false,openedOnce:false};poll(s);}
 window.LCPCNotifications={start,stop};
})();
