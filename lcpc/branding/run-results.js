/* Present PC2 verdicts without changing API values, filters, or judgements. */
(function(root){
 'use strict';
 function verdict(value){
  const key=String(value??'').trim().replace(/^No\s*[-–—:]\s*/i,'').toLowerCase();
  const names={
   yes:['Accepted','accepted'],ac:['Accepted','accepted'],accepted:['Accepted','accepted'],correct:['Accepted','accepted'],
   wa:['Wrong Answer','rejected'],'wrong answer':['Wrong Answer','rejected'],
   '':['Pending','pending'],pending:['Pending','pending'],queued:['Pending','pending'],judging:['Judging','pending'],
   tle:['Time Limit Exceeded','limit'],'time limit exceeded':['Time Limit Exceeded','limit'],
   mle:['Memory Limit Exceeded','limit'],'memory limit exceeded':['Memory Limit Exceeded','limit'],
   ce:['Compilation Error','error'],'compilation error':['Compilation Error','error'],
   rte:['Runtime Error','rejected'],re:['Runtime Error','rejected'],'run-time error':['Runtime Error','rejected'],'runtime error':['Runtime Error','rejected'],
   eo:['Output Limit Exceeded','limit'],'excessive output':['Output Limit Exceeded','limit'],'output limit exceeded':['Output Limit Exceeded','limit'],
   ofe:['Output Format Error','rejected'],'output format error':['Output Format Error','rejected'],
   'other - contact staff':['Contact Staff','error'],'contact staff':['Contact Staff','error'],no:['Rejected','rejected'],rejected:['Rejected','rejected']
  };
  const found=names[key];return found?{label:found[0],state:found[1]}:null;
 }
 if(typeof module!=='undefined'&&module.exports){module.exports={verdict};return;}
 const originals=new WeakMap();
 function clearDecoration(element){
  for(const node of element.childNodes){
   const previous=originals.get(node);
   if(previous&&node.textContent===previous.output)node.textContent=previous.raw;
   originals.delete(node);
  }
  element.classList.remove('lcpc-verdict','lcpc-verdict-filter');delete element.dataset.verdict;
 }
 function decorate(element,pending=false,prefix='',filter=false){
  const node=Array.from(element.childNodes).find(n=>n.nodeType===3 && (!prefix||n.textContent.trim().startsWith(prefix)) && (!filter||n.textContent.trim()));
  if(!node){if(filter)clearDecoration(element);return;}
  const previous=originals.get(node),current=node.textContent;
  const raw=previous&&previous.output===current?previous.raw:current;
  const value=prefix?raw.trim().slice(prefix.length).trim():raw.trim();
  if(filter&&!value){clearDecoration(element);return;}
  const result=verdict(pending?'pending':value);
  if(!result){clearDecoration(element);return;}
  const output=(prefix?prefix+' ':'')+result.label;
  originals.set(node,{raw,output});
  if(current!==output)node.textContent=output;
  element.classList.add('lcpc-verdict');element.classList.toggle('lcpc-verdict-filter',filter);element.dataset.verdict=result.state;
 }
 const observer=new MutationObserver(update);
 function watch(){observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class']});}
 function update(){
  observer.disconnect();
  try{
   for(const table of document.querySelectorAll('ng-component table')){
    const headers=Array.from(table.querySelectorAll('tr th'));
    const column=headers.findIndex(h=>/^(judgement|judgment|verdict)$/i.test(h.textContent.trim()));
    if(column<0)continue;
    for(const row of table.querySelectorAll('tr')){
     const cell=row.querySelectorAll('td')[column];
     if(cell)decorate(cell,row.classList.contains('pending'));
    }
   }
   for(const alert of document.querySelectorAll('app-new-run-alert')){
    const preliminary=Array.from(alert.querySelectorAll('p')).some(p=>/preliminary judgement/i.test(p.textContent));
    for(const p of alert.querySelectorAll('p'))if(/^Judgement:/.test(p.textContent.trim()))decorate(p,preliminary,'Judgement:');
   }
   for(const option of document.querySelectorAll('app-judgement-selector option')){
    if(option.value)decorate(option,false,'',true);
   }
   for(const select of document.querySelectorAll('app-judgement-selector mat-select')){
    for(const label of select.querySelectorAll('.mat-mdc-select-min-line')){
     if(select.classList.contains('mat-mdc-select-empty')||label.classList.contains('mat-mdc-select-placeholder')||label.querySelector('.mat-mdc-select-placeholder'))clearDecoration(label);
     else decorate(label,false,'',true);
    }
    const panel=document.getElementById(select.getAttribute('aria-controls'));
    if(panel)for(const option of panel.querySelectorAll('.mdc-list-item__primary-text'))decorate(option,false,'',true);
   }
  }finally{watch();}
 }
 document.addEventListener('DOMContentLoaded',update);window.addEventListener('hashchange',update);update();
})(typeof globalThis!=='undefined'?globalThis:this);
