(() => {
 'use strict';
 const interactive='button,a,input,select,textarea,label,summary,[contenteditable="true"],[role="button"],[role="link"]';
 // Only read operations belong here. Edit, download and state-changing actions stay explicit buttons.
 const detailSelectors=['[data-action="run-details"]','[data-activity="details"]','[data-test-case]','[data-private-test]','[data-native="test-list"]'];
 const candidates='tbody > tr,article.resource-group,article[data-row-card],.progress-row,.access-link,.security-alert';
 const custom='[data-activity-row],[data-connection-team],[data-review-case]';
 let config={},detailDialog,returnFocus;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function detailTrigger(row){for(const selector of detailSelectors){const button=row.querySelector(selector);if(button&&!button.disabled)return button;}return null;}
 function isDataRow(row){return row.matches('tr')?row.cells.length>0&&!row.querySelector('td.empty')&&!row.closest('thead'):true;}
 function blocked(event,row){const selection=window.getSelection?.();return event.defaultPrevented||event.button>0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||(event.target!==row&&!!event.target.closest(interactive))||!!(selection&&!selection.isCollapsed&&String(selection));}
 function readable(element){
  const clone=element.cloneNode(true);
  const originals=element.querySelectorAll('input,select,textarea');
  clone.querySelectorAll('input,select,textarea').forEach((control,i)=>{
   if(control.type==='hidden'||control.closest('[hidden]')){control.remove();return;}
   const original=originals[i];
   const value=control.type==='password'?'Hidden':control.tagName==='SELECT'?Array.from((original||control).selectedOptions).map(o=>o.textContent).join(', '):control.type==='checkbox'||control.type==='radio'?((original||control).checked?'Yes':'No'):(original||control).value;
   control.replaceWith(document.createTextNode(value));
  });
  clone.querySelectorAll('button,script,style,[hidden],.row-detail-label').forEach(n=>n.remove());
  clone.querySelectorAll('br').forEach(n=>n.replaceWith(document.createTextNode('\n')));
  clone.querySelectorAll('.badge,strong,.name').forEach(n=>n.after(document.createTextNode(' ')));
  clone.querySelectorAll('p,h3,small,.panel-heading,.review-note').forEach(n=>n.after(document.createTextNode('\n')));
  return element.title||clone.textContent.trim();
 }
 function rowDetails(row){
  const provided=config.getDetails?.(row);if(provided)return provided;
  if(row.matches('tr')){
   const headings=Array.from(row.closest('table').querySelectorAll('thead tr:last-child th')).map(h=>h.textContent.trim());
   return {title:(readable(row.cells[0])||'Record')+' · Details',fields:Array.from(row.cells).flatMap((cell,i)=>{const value=readable(cell);return value?[{label:headings[i]||'Value',value}]:[];})};
  }
  return {title:row.querySelector('h3')?.textContent||'Record details',fields:[{label:'Details',value:readable(row)}]};
 }
 function showDetails(details,row){
  if(!detailDialog){
   detailDialog=document.createElement('dialog');detailDialog.id='row-details-dialog';detailDialog.setAttribute('aria-labelledby','row-details-title');
   detailDialog.innerHTML='<div class="dialog-header"><h2 id="row-details-title"></h2><button type="button" class="icon-button" aria-label="Close details">×</button></div><div class="row-details-body"></div>';
   detailDialog.querySelector('button').addEventListener('click',()=>detailDialog.close());
   detailDialog.addEventListener('close',()=>{detailDialog.querySelector('.row-details-body').replaceChildren();if(returnFocus?.isConnected)returnFocus.focus({preventScroll:true});});
   document.body.append(detailDialog);
  }
  returnFocus=row;detailDialog.querySelector('h2').textContent=details.title||'Record details';
  detailDialog.querySelector('.row-details-body').innerHTML='<dl class="row-details-fields">'+details.fields.map(f=>'<dt>'+esc(f.label)+'</dt><dd>'+(/^#[0-9a-f]{6}$/i.test(f.color||'')?'<span class="row-detail-color"><input type="color" value="'+esc(f.color)+'" disabled aria-label="Balloon color"><span>'+esc(f.value||f.color)+'</span></span>':esc(f.value||'—'))+'</dd>').join('')+'</dl>'+(typeof details.detailsUrl==='string'&&details.detailsUrl.startsWith('/review.html?')?'<div class="form-actions"><a class="primary detail-page-link" target="_blank" rel="noopener noreferrer" href="'+esc(details.detailsUrl)+'">Details</a></div>':'');
  if(!detailDialog.open)detailDialog.showModal();
 }
 function open(row){const trigger=detailTrigger(row);if(trigger){trigger.click();return;}showDetails(rowDetails(row),row);}
 function decorate(root){
  const rows=[...(root.matches?.(candidates)?[root]:[]),...root.querySelectorAll(candidates)];
  for(const row of rows){
   if(!isDataRow(row))continue;
   row.classList.add('clickable-row');row.tabIndex=0;
   if(!row.matches(custom))row.setAttribute('aria-label','Open record details');
   for(const selector of detailSelectors)row.querySelectorAll(selector).forEach(button=>{
    // Keep the existing handler as the single read path, without a separate Details button.
    if(button.dataset.rowDetailHidden)return;
    if(/^#\d+$/.test(button.textContent.trim())){const label=document.createElement('span');label.className='row-detail-label';label.textContent=button.textContent;button.before(label);}
    button.hidden=true;button.dataset.rowDetailHidden='true';
   });
  }
 }
 function mount(options={}){
  config=options;
  for(const id of ['content','modal-content']){
   const root=document.getElementById(id);if(!root)continue;
   decorate(root);
   new MutationObserver(changes=>{for(const change of changes)for(const node of change.addedNodes)if(node.nodeType===1)decorate(node);}).observe(root,{childList:true,subtree:true});
  }
  document.addEventListener('click',event=>{const row=event.target.closest(candidates);if(!row||!row.closest('#content,#modal-content')||!isDataRow(row)||row.matches(custom)||blocked(event,row))return;open(row);});
  document.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;const row=event.target;if(!row.matches?.(candidates)||!row.closest('#content,#modal-content')||!isDataRow(row)||row.matches(custom)||blocked(event,row))return;event.preventDefault();open(row);});
 }
 window.LCPCRowDetails={mount,detailTrigger,blocked,rowDetails,decorate,showDetails,readable};
})();
