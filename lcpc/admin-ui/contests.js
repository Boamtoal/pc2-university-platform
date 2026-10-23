(() => {
 'use strict';
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function render(catalog,{owner,button,table,date,selected}) {
  if(!catalog)return '<div class="panel empty">Loading contest workspaces…</div>';
  const active=catalog.contests.find(c=>c.id===catalog.active),job=catalog.job;
  return '<div class="split-heading"><div><h2>Contest workspaces</h2><p>Create independent contests, keep previous results and prepare the next event.</p></div>'+(owner?button('contest-create','New Contest','','primary'):'')+'</div>'+
   '<div class="review-note"><strong>One active contest at a time.</strong> '+(active?'Active: <strong>'+esc(active.title)+'</strong>. Pause and deactivate it before activating another contest. Pausing the clock alone does not release the server.':'No contest is active. Activate a prepared workspace to open participant access.')+' Opening a workspace only changes the administrator view.</div>'+
   (job?'<div class="panel job-status '+(job.status==='failed'?'error':'')+'"><strong>'+esc(job.kind)+' · '+esc(job.status)+'</strong><p>'+esc(job.message)+'</p><small>'+esc(job.contest)+' · '+date(job.created)+'</small>'+(job.result?.backupId?'<div class="form-actions">'+button('backup-download','Download encrypted backup',job.contest+'|'+job.result.backupId,'primary')+'</div>':'')+'</div>':'')+
   table(['Contest','Status','Teams','Problems','Submissions','Actions'],catalog.contests.map(c=>'<tr><td><strong>'+esc(c.title)+'</strong><br><small>'+esc(c.id)+(selected===c.id?' · Viewing':'')+'</small></td><td><span class="badge '+(c.status==='active'?'accepted':c.status==='archived'?'neutral':'pending')+'">'+esc(c.status)+'</span></td><td>'+c.teams+'</td><td>'+c.problems+'</td><td>'+c.submissions+'</td><td><div class="resource-actions">'+(owner?button('contest-open',selected===c.id?'Open workspace':'Open',c.id)+(c.status==='active'||(['error','activating'].includes(c.status)&&catalog.active===c.id)?button('contest-deactivate','Stop server',c.id,'danger')+((c.unavailable||['error','activating'].includes(c.status))?button('contest-release','Release if stopped',c.id):''):c.status==='archived'?button('contest-unarchive','Unarchive',c.id):button('contest-activate','Start server',c.id,'success'))+(c.id!==catalog.active&&c.status!=='archived'?button('contest-archive','Archive',c.id):''):'')+'</div></td></tr>'))+
   (owner?'<p class="hint">To use a previous contest as a template, open its workspace and choose New Contest. Teams, passwords, submissions and results are never copied. Copied resources start as unpublished drafts.</p>':'<p class="hint">Only an owner can create, open, activate or archive contest workspaces.</p>');
 }
 function runtime(catalog,{owner,button,selected}){
  const current=catalog?.contests.find(c=>c.id===selected),active=catalog?.contests.find(c=>c.id===catalog.active),busy=catalog?.job?.status==='running';
  let description,action='';
  if(busy)description='Server operation in progress: '+esc(catalog.job.kind)+'. '+esc(catalog.job.message);
  else if(active?.id===selected&&['error','activating'].includes(current?.status)){description='Startup did not finish. Resume the saved installation without resetting contest data.';if(owner)action=button('contest-recover','Recover server',selected,'primary');}
  else if(active?.id===selected){description='The server is active for this contest. The contest clock is controlled separately. Pause the clock and finalize pending submissions before stopping the server.';if(owner)action=button('contest-deactivate','Stop server',selected,'danger');}
  else if(active){description='Another contest owns the server: '+esc(active.title)+'. Stop its server before starting this contest.';if(owner)action=button('contest-open','Open active contest',active.id);}
  else if(current?.status==='archived')description='This contest is archived. Unarchive it in Contests before starting its server.';
  else if(current?.status==='error'||current?.status==='activating'){description='The previous startup was interrupted. Recovering resumes an unstarted installation without resetting credentials or results and keeps the clock paused.';if(owner)action=button('contest-recover','Recover server',selected,'primary');}
  else {description='Server stopped. Start the prepared contest server to open participant access. Starting the server leaves the contest clock paused.';if(owner)action=button('contest-activate','Start server',selected,'success');}
  return '<section class="panel server-controls"><div class="panel-heading"><div><h2>Server & participant access</h2><p>'+esc(current?.title||selected)+'</p></div><span class="badge '+(busy?'pending':active?.id===selected?'accepted':'neutral')+'">'+(busy?'Working':active?.id===selected?'Active':active?'Another contest active':'Stopped')+'</span></div><p class="hint">'+description+'</p>'+(action?'<div class="resource-actions">'+action+'</div>':'')+(!owner?'<p class="hint">Only a dashboard owner can start or stop the server.</p>':'')+'</section>';
 }
 function exportsView(catalog,{owner,button,table,date,selected}) {
  const c=catalog?.contests.find(c=>c.id===selected),job=catalog?.job;
  return '<div class="split-heading"><div><h2>Exports & Backups</h2><p>'+esc(c?.title||selected)+' · Keep reports and a separate restorable archive.</p></div></div>'+
   '<div class="export-grid">'+[
    ['CSV data package','A ZIP containing contest settings, teams, problems, submissions, standings, clarifications, resource metadata and audit records. Includes a JSON snapshot for nested details.',button('contest-csv','Export CSV package',selected,'primary')],
    ['Team Learning Reports','An independent PDF and full evidence folder for each participating team: statements, reference code, team attempts, current tests and saved judge output. Inactive teams and diagnostic accounts are omitted.',button('learning-open','Open Team Learning Reports',selected,'primary')],
    ['PDF contest report','A printable report with contest configuration, full administrator standings, submissions, teams, problems, resources and the audit trail.',button('contest-pdf','Export PDF report',selected,'primary')],
    ['Encrypted full backup','Preserves the selected contest state, source files, saved judge evidence, private judge data, resources and administration data. Deactivate the contest first for a consistent backup.',button('contest-backup','Create full backup',selected,'primary')],
    ['Recovery key','Save the recovery key separately on a secure device. It decrypts all backups made with this server key. Download requires your password and authenticator code if enabled.',button('recovery-key','Download recovery key',selected,'danger')]
   ].map(([title,text,action])=>'<section class="panel"><h3>'+title+'</h3><p class="hint">'+text+'</p>'+(owner?action:'<p class="hint">Owner permission required.</p>')+'</section>').join('')+'</div>'+
   '<div class="review-note">CSV and PDF are reports. They do not replace an encrypted full backup. Full backups include secrets: keep the recovery key separate. Native runtimes and the Linux VM must be installed on a replacement server.</div>'+
   (job?.kind==='backup'?'<section class="panel"><h3>Latest backup job · '+esc(job.status)+'</h3><p class="hint">'+esc(job.message)+'</p>'+(job.result?.backupId?button('backup-download','Download encrypted backup',job.contest+'|'+job.result.backupId,'primary'):'')+'</section>':'')+
   (catalog?.backups?.length?'<section class="panel"><h3>Saved backups</h3>'+table(['Contest','Created','Size',''],catalog.backups.map(b=>'<tr><td>'+esc(b.contestId)+'</td><td>'+date(b.created)+'</td><td>'+(b.bytes/1048576).toFixed(1)+' MiB</td><td>'+(owner?button('backup-download','Download',b.contestId+'|'+b.id):'')+'</td></tr>'))+'</section>':'');
 }
 window.LCPCContests={render,exportsView,runtime};
})();
