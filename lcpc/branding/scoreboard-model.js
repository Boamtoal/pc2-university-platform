/* Present only the standings snapshot PC2 has released to this team. */
(function(root){
 'use strict';
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const count=n=>Number.isFinite(Number(n))?Math.max(0,Math.trunc(Number(n))):0;
 const array=v=>v==null?[]:Array.isArray(v)?v:[v];
 const letter=i=>{let s='';for(let n=i+1;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
 // Choose the stronger black/white text contrast against the actual balloon color.
 function cardText(rgb){
  const channels=rgb.slice(1).match(/../g).map(h=>parseInt(h,16)/255).map(c=>c<=.04045?c/12.92:Math.pow((c+.055)/1.055,2.4));
  const luminance=.2126*channels[0]+.7152*channels[1]+.0722*channels[2];
  return (luminance+.05)/.05>=1.05/(luminance+.05)?'#000000':'#ffffff';
 }
 function render(payload,options={}){
  const snapshot=payload?.contestStandings;
  if(!snapshot?.standingsHeader)throw new Error('Invalid PC2 standings snapshot');
  const header=snapshot.standingsHeader,teams=array(snapshot.teamStanding),problems=array(header.problem),audience=options.audience===true,summaryColumns=audience?4:5;
  const columns=problems.map((p,i)=>{
   const metadata=array(options.problemMetadata).find(m=>count(m.id)===count(p.id)&&m.title===p.title)||p;
   return {id:count(p.id)||i+1,label:/^[A-Za-z]{1,3}$/.test(metadata.letter||'')?metadata.letter:letter(i),title:p.title||letter(i),rgb:/^#[0-9a-f]{6}$/i.test(metadata.colorRGB||'')?metadata.colorRGB:null,colorName:String(metadata.colorName||''),firstTeams:array(metadata.firstToSolveTeams).filter(key=>typeof key==='string'),data:p};
  });
  const cell=(team,p)=>{
   const result=array(team.problemSummaryInfo).find(r=>count(r.index)===p.id)||{};
   const attempts=count(result.attempts),time=count(result.solutionTime),solved=result.isSolved===true,pending=result.isPending===true;
   const first=solved&&p.firstTeams.includes(String(team.teamKey||''));
   const state=solved?'accepted':pending?'pending':attempts?'rejected':'untouched';
   const mark=solved?(attempts>1?'+'+(attempts-1):'+'):pending?'?':attempts?'−'+attempts:'—';
   const detail=solved?'Accepted':pending?'Pending':attempts?'Not solved':'No attempts';
   const meta=solved?time+' min':attempts?attempts+(attempts===1?' try':' tries'):'';
   const title=(first?'First to solve · ':'')+p.title+': '+(solved?'Accepted at '+time+' minutes':detail)+'; '+attempts+' attempts';
   return '<td class="lcpc-result '+state+(first?' lcpc-first-solve':'')+'" title="'+escape(title)+'"'+(audience?' aria-label="'+escape(title)+'"':'')+'>'+(first?'<span class="lcpc-first-solve-badge" aria-hidden="true"><svg viewBox="0 0 24 20" focusable="false"><path d="m3 5 4 4 5-7 5 7 4-4-2 11H5Z"/><path d="M6 19h12"/></svg><b>1ST</b></span>':'')+'<strong>'+mark+'</strong>'+(audience?(solved?'<small>'+time+'</small>':''):'<span>'+escape(detail)+'</span><small>'+escape(meta)+'</small>')+'</td>';
  };
  let html=audience?'':'<div class="lcpc-score-heading" data-lcpc-key="heading"><div><p class="lcpc-eyebrow">'+escape(options.identityName||'Contest')+' · STANDINGS</p><h1>'+escape(header.title||'Contest standings')+'</h1></div><div class="lcpc-score-meta">'+teams.length+' teams · '+columns.length+' problems<br><span>Last update: '+escape(header.currentDate||'Live')+'</span></div></div>';
  if(!audience&&header.scoreboardMessage)html+='<p class="lcpc-server-notice" data-lcpc-key="notice" dir="auto">'+escape(header.scoreboardMessage)+'</p>';
  html+='<div class="lcpc-score-scroll" data-lcpc-key="scroll" tabindex="0" role="region" aria-label="Contest standings"><table class="lcpc-score-table'+(audience?' lcpc-audience-table':'')+'"'+(options.strictStyles?'':' style="min-width:'+(audience?Math.max(510,250+48*columns.length):Math.max(680,320+70*columns.length))+'px"')+'><colgroup><col class="lcpc-rank-column"><col class="lcpc-team-column"><col class="lcpc-solved-column"><col class="lcpc-penalty-column">'+(audience?'':'<col class="lcpc-attempts-column">');
  for(const p of columns)html+='<col>';
  html+='</colgroup><thead><tr><th scope="col">Rank</th><th scope="col" class="lcpc-team">Team</th><th scope="col">Solved</th><th scope="col" title="Total penalty in minutes">Penalty</th>'+(audience?'':'<th scope="col">Attempts</th>');
  for(const p of columns){
   const color=p.rgb?(p.colorName||p.rgb):'Not assigned';
   const background=p.rgb||'#edf1f6',foreground=p.rgb?cardText(p.rgb):'#172b46';
   const card='<svg class="lcpc-problem-card'+(p.rgb?'':' lcpc-problem-card-unassigned')+'" viewBox="0 0 44 36" aria-hidden="true" focusable="false"><rect x="1" y="1" width="42" height="34" rx="7" fill="'+background+'" stroke="'+foreground+'" stroke-opacity="0.18"/><text x="22" y="19" text-anchor="middle" dominant-baseline="central" font-size="'+(p.label.length>2?13:17)+'" fill="'+foreground+'">'+escape(p.label)+'</text></svg>';
   html+='<th scope="col" class="lcpc-problem" title="'+escape(p.title+' · Balloon: '+color)+'" aria-label="'+escape(p.label+': '+p.title+' · Balloon: '+color)+'">'+card+'</th>';
  }
  html+='</tr></thead><tbody>';
  for(const [index,t] of teams.entries()){
   html+='<tr data-lcpc-key="team-'+escape(t.teamKey??t.teamId??index)+'"><td class="lcpc-rank">'+escape(t.overallRank??t.rank??'—')+'</td><th scope="row" class="lcpc-team">'+escape(t.teamName)+'</th><td class="lcpc-total-solved">'+count(t.solved)+'</td><td>'+escape(t.points??0)+'</td>'+(audience?'':'<td>'+count(t.totalAttempts)+'</td>');
   for(const p of columns)html+=cell(t,p);
   html+='</tr>';
  }
  if(!teams.length)html+='<tr><td colspan="'+(summaryColumns+columns.length)+'">No teams configured yet.</td></tr>';
  html+='</tbody>';
  if(columns.length&&!audience){
   html+='<tfoot><tr><th colspan="5" scope="row">Solved / attempts</th>';
   for(const p of columns)html+='<td>'+count(p.data.numberSolved)+' / '+count(p.data.attempts)+'</td>';
   html+='</tr></tfoot>';
  }
  html+='</table></div>';
  return html;
 }
 // Keep scroll containers, focused elements and team rows alive between updates.
 const key=node=>node.nodeType===1?node.getAttribute('data-lcpc-key'):null;
 const compatible=(a,b)=>a&&a.nodeType===b.nodeType&&a.nodeName===b.nodeName;
 function reconcile(target,source){
  const wantedKeys=new Set(Array.from(source.childNodes).map(key).filter(Boolean));
  for(const node of Array.from(target.childNodes))if(key(node)&&!wantedKeys.has(key(node)))target.removeChild(node);
  const keyed=new Map(Array.from(target.childNodes).filter(n=>key(n)).map(n=>[key(n),n]));
  let cursor=target.firstChild;
  for(const wanted of Array.from(source.childNodes)){
   const id=key(wanted);
   let node=id?keyed.get(id):cursor;
   if(!compatible(node,wanted)||key(node)!==id)node=wanted.cloneNode(true);
   if(node!==cursor)target.insertBefore(node,cursor);
   if(node.nodeType===1){
    for(const attr of Array.from(node.attributes))if(!wanted.hasAttribute(attr.name))node.removeAttribute(attr.name);
    for(const attr of Array.from(wanted.attributes))if(node.getAttribute(attr.name)!==attr.value)node.setAttribute(attr.name,attr.value);
    reconcile(node,wanted);
   }else if(node.nodeValue!==wanted.nodeValue)node.nodeValue=wanted.nodeValue;
   cursor=node.nextSibling;
  }
  while(cursor){const next=cursor.nextSibling;target.removeChild(cursor);cursor=next;}
 }
 function update(target,payload,options={}){
  const template=target.ownerDocument.createElement('template');template.innerHTML=render(payload,options);
  const focused=target.contains(target.ownerDocument.activeElement)?target.ownerDocument.activeElement:null;
  const positions=[];
  for(let node=target;node;node=node.parentElement)positions.push([node,node.scrollLeft,node.scrollTop]);
  const scroller=target.querySelector('.lcpc-score-scroll');
  if(scroller)positions.push([scroller,scroller.scrollLeft,scroller.scrollTop]);
  reconcile(target,template.content);
  if(focused&&target.contains(focused)&&target.ownerDocument.activeElement!==focused)focused.focus({preventScroll:true});
  for(const [node,left,top] of positions){
   if(node.scrollLeft!==left)node.scrollLeft=left;
   if(node.scrollTop!==top)node.scrollTop=top;
  }
 }
 const api={render,update};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LCPCScoreboard=api;
})(typeof globalThis!=='undefined'?globalThis:this);
