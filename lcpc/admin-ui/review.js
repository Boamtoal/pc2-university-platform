(() => {
 'use strict';
 const $=id=>document.getElementById(id),D=LCPCDiagnostics;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const params=new URLSearchParams(location.search),cid=params.get('contestId'),problemId=params.get('problemId');
 const state={kind:problemId?'problem':'submission',tab:'summary',data:null,user:null,loading:false,files:null,fileIndex:0,wrap:false,cases:[],selectedCase:null,caseQuery:'',caseStatus:'',caseVersion:0,report:0};
 const query=new URLSearchParams({contestId:cid||'',site:params.get('site')||'',number:params.get('number')||''});
 async function api(path,data){const options={credentials:'same-origin',cache:'no-store'};if(data!==undefined){options.method='POST';options.headers={'Content-Type':'application/json','X-CSRF-Token':state.user.csrf};options.body=JSON.stringify({...data,contestId:cid});}const response=await fetch('/api/'+path,options),value=await response.json();if(!response.ok){const error=new Error(value.error||'Request failed');error.status=response.status;throw error;}return value;}
 function date(value){return value?new Date(value).toLocaleString('en-GB',{hour12:false,timeZone:state.data?.timeZone||'Africa/Tripoli'}):'Not recorded';}
 function error(message){$('review-error').textContent=message;$('review-error').hidden=false;}
 function fields(rows){return '<dl class="row-details-fields">'+rows.map(([label,value])=>'<dt>'+esc(label)+'</dt><dd>'+esc(value??'Not recorded')+'</dd>').join('')+'</dl>';}
 function problemFields(p){const color=/^#[0-9a-f]{6}$/i.test(p.colorRGB||'')?p.colorRGB:null;return fields([['Problem',p.letter+' · '+p.name],['Short name',p.shortName||'Not assigned'],['Judging workflow',({automatic:'Automatic only',review:'Automatic + human approval',human:'Human only'})[p.judgingMode]||p.judgingMode||'Not recorded'],['Time limit',p.timeLimit+' seconds'],['Memory limit',p.memoryLimit+' MiB'],['Judge tests',p.tests],['Status',p.active?'Active':'Inactive']])+'<dl class="row-details-fields"><dt>Balloon</dt><dd>'+(color?'<span class="row-detail-color"><input type="color" value="'+esc(color)+'" disabled aria-label="Balloon color"><span>'+esc(p.colorName||color)+'</span></span>':esc(p.colorName||'Not assigned'))+'</dd></dl>';}
 function tabs(){const items=state.kind==='problem'?[['summary','Problem'],['tests','Private judge data'],['resources','Resources']]:[['summary','Summary'],['problem','Problem'],['tests','Test cases'],['source','Source code'],['reports','Judge reports']];$('review-tabs').innerHTML=items.map(([id,label])=>'<button type="button" data-review-tab="'+id+'" aria-current="'+(state.tab===id?'page':'false')+'"'+(state.tab===id?' class="active"':'')+'>'+label+'</button>').join('');}
 async function load(){
  if(state.loading)return;state.loading=true;$('review-refresh').disabled=true;
  try{
   if(!state.user)state.user=await api('me');
   if(!cid||cid.length>100)throw new Error('Open a review from a dashboard record.');
   const value=await api(state.kind==='problem'?'problem-review?'+new URLSearchParams({contestId:cid,problemId}):'submission-review?'+query);
   if(value.contest.id!==cid)throw new Error('The selected contest changed. Open a fresh review.');
   state.data=value;$('review-error').hidden=true;$('review-contest').textContent=value.contest.title;
   const r=value.submission,p=value.problem;
   $('review-title').textContent=r?'Submission #'+r.number:p.letter+' · '+p.name;
   $('review-identity').textContent=r?r.teamName+' · '+r.team+' · '+r.problem+' · '+(r.language||'Language not recorded'):'Problem configuration and private reference data';
   $('review-verdict').innerHTML=r?D.verdictBadge(value.evidence.verdict):'';
   $('review-updated').textContent='Last refreshed: '+date(value.checkedAt);
   document.title=(r?'Submission #'+r.number:p.letter+' · '+p.name)+' · Organizer review';
   const scroll=window.scrollY,positions=Array.from(document.querySelectorAll('.review-test-list,.review-case-preview,pre.code')).map(el=>[el.scrollTop,el.scrollLeft]),expanded=Array.from(document.querySelectorAll('#review-body details')).map(el=>el.open);
   tabs();await render();window.scrollTo({top:scroll,behavior:'instant'});document.querySelectorAll('.review-test-list,.review-case-preview,pre.code').forEach((el,i)=>{if(positions[i]){el.scrollTop=positions[i][0];el.scrollLeft=positions[i][1];}});document.querySelectorAll('#review-body details').forEach((el,i)=>{if(expanded[i]!==undefined)el.open=expanded[i];});
  }catch(e){error(e.message);if([401,403,409].includes(e.status)){if([401,403].includes(e.status))state.user=null;state.files=null;state.data=null;$('review-body').innerHTML='<p class="hint">Open the current record from the authenticated dashboard to continue.</p>';}}
  finally{state.loading=false;$('review-refresh').disabled=false;}
 }
 async function render(){
  if(!state.data)return;const box=$('review-body'),data=state.data,p=data.problem,r=data.submission,e=data.evidence;
  if(state.tab==='summary'){
   box.innerHTML=state.kind==='problem'?'<section class="panel">'+problemFields(p)+'</section>':D.summary(e)+'<section class="panel"><h2>Submission</h2>'+fields([['Team',r.teamName+' · '+r.team],['Problem',r.problem],['Language',r.language],['Site',r.site],['Contest time',r.elapsedMinutes==null?'Not recorded':Number(r.elapsedMinutes).toFixed(2)+' minutes'],['Submission state',r.deleted?'Removed':e.final?'Final':e.awaitingApproval?'Awaiting human approval':'Pending']])+'</section><p class="hint">Use Test cases for reference answers and saved output, Source code for retained files, and Judge reports for stage failures and diagnostics. Viewing this page never executes or rejudges code.</p>';return;
  }
  if(state.tab==='problem'){box.innerHTML=p?'<section class="panel"><h2>Problem settings</h2>'+problemFields(p)+'<div class="form-actions"><a class="detail-page-link primary" target="_blank" rel="noopener noreferrer" href="/review.html?'+esc(new URLSearchParams({contestId:cid,problemId:p.id}))+'">Problem resources & private tests</a></div></section>':'<p class="hint">The current problem definition is unavailable.</p>';return;}
  if(state.tab==='resources'){box.innerHTML='<section class="panel"><h2>Linked resources</h2><div class="review-resources">'+(data.resources||[]).map(f=>'<article class="review-resource resource-group"><h3>'+esc(f.label)+'</h3><small>'+esc(f.filename)+' · '+esc(f.language.toUpperCase())+' · '+(f.published?'Published':'Draft')+'</small><div class="form-actions"><a class="detail-page-link secondary" href="/api/resources/'+encodeURIComponent(f.id)+'/download">Download</a></div></article>').join('')+'</div>'+(!(data.resources||[]).length?'<p class="hint">No linked resources.</p>':'')+'</section>';return;}
  if(state.tab==='tests'){await tests();return;}
  if(state.tab==='source'){await source();return;}
  if(state.tab==='reports'){
   const reports=e.reports||[];if(!reports.length){box.innerHTML='<section class="panel"><h2>Judge reports</h2><p class="hint">'+(e.reportsUnavailable?'Saved reports could not be retrieved from PC². Refresh to try again.':'No saved reports are available. This does not establish a successful execution.')+'</p></section>';return;}
   state.report=Math.min(state.report,reports.length-1);box.innerHTML='<section class="panel"><h2>Saved judge reports</h2><p class="hint">Showing '+reports.length+' of '+esc(e.reportCount??reports.length)+' retained reports. Select one report. Saved report order is not a guaranteed judgement timeline; PC² does not provide a matching test-case ID or data revision for these files.</p><label class="review-report-select">Saved report<select id="review-report">'+reports.map((report,i)=>'<option value="'+i+'"'+(state.report===i?' selected':'')+'>Report '+(i+1)+' · '+esc(D.classifyReport(report).label)+' · Saved judgement: '+esc(D.verdictLabel(report.verdict)||'Unspecified')+'</option>').join('')+'</select></label><div id="review-report-body">'+D.report(reports[state.report],state.report,e.verdict)+'</div></section>';box.querySelector('.judge-report').open=true;return;
  }
 }
 async function tests(){
  const box=$('review-body'),data=state.data;let cases;
  if(state.kind==='problem'){
   if(state.user.role!=='owner'){box.innerHTML='<p class="hint">Only an owner can open private judge files here.</p>';return;}
   box.innerHTML='<p class="hint">Loading private judge data…</p>';
   try{const result=await api('native/tests',{id:problemId});if(state.tab!=='tests'||state.data!==data)return;cases=result.rows.map(r=>({...r,number:r.test,status:'Current reference',verdict:''}));}catch(e){if(state.tab==='tests')box.innerHTML='<p class="error">'+esc(e.message)+'</p>';return;}
  }else cases=data.evidence.tests||[];
  state.cases=cases;
  box.innerHTML='<p class="review-stage-note">'+(state.kind==='problem'?'Current private reference inputs and expected answers.':'Per-case results are PC² records. A saved execution report is not automatically linked to the selected case. Missing cases are not passes. No tests are rerun here.')+(data.evidence?.stopOnFirstFailure?' Judging is configured to stop after the first failed case.':'')+'</p><div class="review-test-grid"><section><div class="review-case-controls"><label>Find test<input type="search" id="review-case-search" placeholder="Case number or verdict" value="'+esc(state.caseQuery)+'"></label><label>Recorded state<select id="review-case-status"><option value="">All states</option>'+[...new Set(cases.map(c=>c.status))].map(s=>'<option'+(state.caseStatus===s?' selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label></div><div class="review-test-list"><table><thead><tr><th>Case</th><th>Recorded state</th><th>Recorded judgement</th><th>Time (ms)</th></tr></thead><tbody>'+cases.map(c=>'<tr class="clickable-row" tabindex="0" data-review-case="'+c.number+'" aria-label="Open test case '+c.number+'" aria-selected="false"><td>#'+c.number+'</td><td><span class="badge '+(c.status==='Passed'?'accepted':c.status==='Failed'?'rejected':['Pending','Not validated'].includes(c.status)?'pending':'neutral')+'">'+esc(c.status)+'</span></td><td>'+D.verdictBadge(c.verdict)+'</td><td>'+esc(c.elapsedMS??'—')+'</td></tr>').join('')+'</tbody></table></div><p class="hint" id="review-case-count"></p><p class="hint">Peak memory usage is not recorded by this PC² integration.</p></section><section class="review-case-preview" id="review-case-preview"><p class="hint">Select a test case to view its reference input and expected output.</p></section></div>';
  filterCases();
  if(state.selectedCase&&cases.some(c=>c.number===state.selectedCase))await selectCase(state.selectedCase);
 }
 function filterCases(){let count=0;document.querySelectorAll('[data-review-case]').forEach(row=>{const c=state.cases.find(c=>c.number===Number(row.dataset.reviewCase)),match=(!state.caseStatus||c.status===state.caseStatus)&&(!state.caseQuery||('#'+c.number+' '+c.status+' '+c.verdict).toLowerCase().includes(state.caseQuery.toLowerCase()));row.hidden=!match;if(match)count++;});if($('review-case-count'))$('review-case-count').textContent=count+' of '+state.cases.length+' cases shown.';}
 async function selectCase(number){
  state.selectedCase=number;const version=++state.caseVersion,box=$('review-case-preview');if(!box)return;
  document.querySelectorAll('[data-review-case]').forEach(row=>row.setAttribute('aria-selected',String(Number(row.dataset.reviewCase)===number)));
  box.innerHTML='<p class="hint">Loading private reference data…</p>';
  try{const value=await (state.kind==='problem'?api('native/tests',{id:problemId,test:number}):api('test-data?'+query+'&test='+number));if(version!==state.caseVersion||$('review-case-preview')!==box)return;box.innerHTML=D.renderTestData(value,state.data.evidence);box.scrollTop=0;}catch(e){if($('review-case-preview')===box)box.innerHTML='<p class="error">'+esc(e.message)+'</p>';}
 }
 async function source(){
  const box=$('review-body');box.innerHTML='<p class="hint">Loading retained source files…</p>';
  try{if(!state.files)state.files=(await api('source?'+query)).files;if(state.tab!=='source'||$('review-body')!==box)return;if(!state.files?.length){box.innerHTML='<p class="hint">No source files were retained.</p>';return;}
   const file=state.files[state.fileIndex]||state.files[0],bytes=Uint8Array.from(atob(file.base64),c=>c.charCodeAt(0)),text=new TextDecoder().decode(bytes);
   box.innerHTML='<section class="panel"><div class="review-source-toolbar"><label>Source file<select id="review-source-file">'+state.files.map((f,i)=>'<option value="'+i+'"'+(i===state.fileIndex?' selected':'')+'>'+esc(f.name)+'</option>').join('')+'</select></label><label class="check-field"><input type="checkbox" id="review-source-wrap"'+(state.wrap?' checked':'')+'>Wrap long lines</label><button type="button" id="review-source-download">Download source</button></div><p class="hint">'+bytes.length.toLocaleString('en-GB')+' bytes · '+(text?text.split('\n').length:0)+' lines · UTF-8 preview · Retained source only</p><pre class="code source-code'+(state.wrap?' wrap-code':'')+'" id="review-source-code"></pre></section>';$('review-source-code').textContent=text;
  }catch(e){if(state.tab==='source')box.innerHTML='<p class="error">'+esc(e.message)+'</p>';}
 }
 document.addEventListener('click',async event=>{
  const tab=event.target.closest('[data-review-tab]');if(tab&&state.data){state.tab=tab.dataset.reviewTab;state.caseVersion++;tabs();await render();return;}
  const row=event.target.closest('[data-review-case]');if(row&&!LCPCRowDetails.blocked(event,row)){await selectCase(Number(row.dataset.reviewCase));return;}
  if(event.target.closest('#review-source-download')&&state.files){const f=state.files[state.fileIndex]||state.files[0],bytes=Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0)),blob=new Blob([bytes],{type:'text/plain'});LCPCDownloads.save(blob,f.name,event.target.closest('button'));}
 });
 document.addEventListener('keydown',event=>{const row=event.target.closest('[data-review-case]');if(row&&event.target===row&&(event.key==='Enter'||event.key===' ')&&!LCPCRowDetails.blocked(event,row)){event.preventDefault();selectCase(Number(row.dataset.reviewCase));}});
 document.addEventListener('input',event=>{if(event.target.id==='review-case-search'){state.caseQuery=event.target.value;filterCases();}});
 document.addEventListener('change',async event=>{const el=event.target;if(el.id==='review-case-status'){state.caseStatus=el.value;filterCases();}if(el.id==='review-source-file'){state.fileIndex=Number(el.value);await source();}if(el.id==='review-source-wrap'){state.wrap=el.checked;$('review-source-code').classList.toggle('wrap-code',state.wrap);}if(el.id==='review-report'){state.report=Number(el.value);await render();}});
 $('review-refresh').addEventListener('click',load);
 LCPCRowDetails.mount();LCPCDashboardBranding.load();load();
 setInterval(()=>{if(state.data?.evidence&&!state.data.evidence.final&&!document.hidden&&!document.querySelector('dialog[open]'))load();},10000);
})();
