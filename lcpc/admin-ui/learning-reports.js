(function(root){
 'use strict';
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function render(){return '<section class="panel" id="learning-reports"><div class="panel-heading"><div><h2>Team Learning Reports</h2><p>Post-contest feedback, source code and retained test evidence for participating teams.</p></div></div><p class="hint">Loading report workspace…</p></section>';}
 function content(data){
  const busy=data.job?.status==='running';
  return '<div class="panel-heading"><div><h2>Team Learning Reports</h2><p>'+data.eligibleTeams.length+' participating teams · '+data.ignoredTeams+' teams without retained participation omitted</p></div><button class="primary" type="button" data-learning-generate'+(!data.ready||busy||!data.eligibleTeams.length?' disabled':'')+'>'+(busy&&data.job?.kind==='learning'?'<span class="lcpc-download-spinner" aria-hidden="true"></span> Preparing · '+(data.job.progress?.percent??0)+'%':'Create learning package')+'</button></div>'+
   '<p class="hint">Export after the contest finishes or after its server is stopped. Each team receives its own PDF, original problem PDFs, current reference code and explanation, all its attempts, current input/answer files, isolated per-test replay output, saved judge streams and a structured evidence index. Team code is analysed in the isolated Linux sandbox. Official submissions and judgements are unchanged.</p>'+
   '<div class="review-note">Current test data is not proven to be the historic revision used for an attempt. Each test shows input, actual team replay output and expected output. Historic output without a test association remains separate. Missing evidence is explicitly unavailable. Textual source differences do not establish algorithmic correctness.</div>'+
   (data.job?.kind==='learning'&&busy?'<div class="learning-job-progress" role="status"><span class="lcpc-download-spinner" aria-hidden="true"></span><progress max="100" value="'+(data.job.progress?.percent??0)+'" aria-label="Learning report preparation"></progress><strong>'+(data.job.progress?.percent??0)+'%</strong></div>':'')+
   (data.job?.kind==='learning'?'<p role="status"><strong>Latest report job: '+esc(data.job.status)+'</strong> · '+esc(data.job.message)+'</p>':'')+
   '<h3>Participating teams</h3><div class="table-wrap"><table><thead><tr><th>Account</th><th>Team</th><th>Attempts</th></tr></thead><tbody>'+data.eligibleTeams.map(t=>'<tr><td>'+esc(t.login)+'</td><td>'+esc(t.name)+'</td><td>'+t.attempts+'</td></tr>').join('')+'</tbody></table></div>'+
   '<h3 class="learning-heading">Reference materials</h3><p class="hint">Upload the organizer reference solution and a plain-text or Markdown explanation containing the algorithm and complexity. Files are linked to the selected problem. They are never executed.</p><form data-learning-material><div class="form-grid"><label>Problem<select name="problemId" required>'+data.problems.map(p=>'<option value="'+esc(p.id)+'">'+esc(p.letter+' · '+p.name)+'</option>').join('')+'</select></label><label>Material<select name="kind"><option value="solution">Reference solution</option><option value="editorial">Reasoning and complexity</option></select></label><label>UTF-8 source or text file<input type="file" name="material" accept=".cpp,.cc,.c,.java,.py,.txt,.md" required></label><div class="form-actions"><button type="submit"'+(busy?' disabled':'')+'>Save reference material</button></div></div></form>'+
   '<div class="table-wrap"><table><thead><tr><th>Problem</th><th>Difficulty</th><th>Reference code</th><th>Explanation</th></tr></thead><tbody>'+data.problems.map(p=>'<tr><td>'+esc(p.letter+' · '+p.name)+'</td><td>'+esc(p.difficulty??'Not assigned')+(p.difficultyEstimated?' (estimated)':'')+'</td><td>'+(p.referenceAvailable?'Available':'Not supplied')+'</td><td>'+(p.editorialAvailable?'Available':'Not supplied')+'</td></tr>').join('')+'</tbody></table></div>'+
   '<h3 class="learning-heading">Saved learning packages</h3><p class="hint">The full ZIP is for the organizer. Share an individual team ZIP with that team only.</p>'+
   (data.exports.length?data.exports.map(e=>'<section class="resource-group"><div class="panel-heading"><div><h3>'+esc(e.created)+'</h3><p>'+e.teams.length+' teams · '+(e.bytes/1048576).toFixed(1)+' MiB</p></div><button type="button" data-learning-download="'+esc(e.id)+'" data-team="all">Download all teams</button></div><div class="resource-actions">'+e.teams.map(t=>'<button type="button" data-learning-download="'+esc(e.id)+'" data-team="'+esc(t.login)+'">'+esc(t.login+' · '+t.name)+'</button>').join('')+'</div></section>').join(''):'<p class="hint">No learning package has been created yet.</p>');
 }
 let epoch=0,timer=null;
 function dispose(){epoch++;clearTimeout(timer);timer=null;}
 async function mount(host,ctx){
  dispose();const generation=epoch,cid=ctx.data.system.contestId;
  const active=()=>generation===epoch&&host.isConnected&&ctx.getData().system.contestId===cid;
  async function load(){
   try{const data=await ctx.api('learning-reports?contestId='+encodeURIComponent(cid));if(!active())return;
    // Keep the user's selected file intact while polling a running export.
    if(!host.querySelector('input[type=file]')?.files?.length)host.innerHTML=content(data);
    if(data.job?.status==='running')timer=setTimeout(load,2000);
   }catch(error){if(active())ctx.notice(error.message,true);}
  }
  host.addEventListener('click',async event=>{
   const generate=event.target.closest('[data-learning-generate]'),download=event.target.closest('[data-learning-download]');if(!generate&&!download)return;
   const button=generate||download;button.disabled=true;
   try{
    if(generate){await ctx.api('learning-reports/generate',{});ctx.notice('Preparing participating team reports in the background.');await load();}
    else await ctx.download('learning-reports/download',{exportId:download.dataset.learningDownload,team:download.dataset.team},cid+'-'+download.dataset.team+'-learning.zip');
   }catch(error){ctx.notice(error.message,true);}finally{if(button.isConnected)button.disabled=false;}
  });
  host.addEventListener('submit',async event=>{
   const form=event.target.closest('[data-learning-material]');if(!form)return;event.preventDefault();const button=form.querySelector('button');button.disabled=true;
   try{const file=form.elements.material.files[0];if(!file||file.size>512*1024)throw new Error('Choose a UTF-8 reference file up to 512 KiB.');await ctx.api('learning-reports/material',{problemId:form.elements.problemId.value,kind:form.elements.kind.value,filename:file.name,base64:await ctx.file64(file)});form.reset();ctx.notice('Reference material saved.');await load();}catch(error){ctx.notice(error.message,true);}finally{if(button.isConnected)button.disabled=false;}
  });
  await load();
 }
 const api={render,content,mount,dispose};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LCPCLearningReports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
