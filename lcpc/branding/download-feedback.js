/* Shared download feedback. Percentages represent received bytes, never a timer. */
(function(root){
 'use strict';
 const busy=new WeakMap();let lastControl=null;
 async function read(response,update){
  const length=Number(response.headers.get('Content-Length')),encoded=response.headers.get('Content-Encoding');
  const total=Number.isFinite(length)&&length>0&&(!encoded||encoded==='identity')?length:null;
  if(!response.body?.getReader){const blob=await response.blob();update({phase:'Receiving',received:blob.size,total,percent:100});return blob;}
  const reader=response.body.getReader(),chunks=[];let received=0;
  try{for(;;){const {done,value}=await reader.read();if(done)break;chunks.push(value);received+=value.byteLength;update({phase:'Receiving',received,total,percent:total?Math.min(99,Math.floor(received/total*100)):null});}}
  catch(error){try{await reader.cancel();}catch(_){}throw error;}
  update({phase:'Ready',received,total,percent:100});return new Blob(chunks,{type:response.headers.get('Content-Type')||'application/octet-stream'});
 }
 function begin(control=lastControl){
  if(!control||!root.document)return {update(){},finish(){}};
  if(busy.has(control))return busy.get(control);
  const original=[...control.childNodes],disabled=control.disabled,oldBusy=control.getAttribute('aria-busy');
  const spinner=document.createElement('span');spinner.className='lcpc-download-spinner';spinner.setAttribute('aria-hidden','true');
  const status=document.createElement('span');status.className='lcpc-download-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  control.replaceChildren(...original,spinner,status);control.classList.add('lcpc-downloading');control.setAttribute('aria-busy','true');if('disabled' in control)control.disabled=true;
  const feedback={update({phase='Preparing',percent=null,received=0}={}){status.textContent=' '+phase+(percent===null?(received?' · '+(received/1048576).toFixed(1)+' MiB':'…'):' · '+percent+'%');},finish(){control.replaceChildren(...original);control.classList.remove('lcpc-downloading');if(oldBusy===null)control.removeAttribute('aria-busy');else control.setAttribute('aria-busy',oldBusy);if('disabled' in control)control.disabled=disabled;busy.delete(control);}};
  busy.set(control,feedback);feedback.update();return feedback;
 }
 function handoff(blob,name,opened){
  const url=URL.createObjectURL(blob);
  if(opened&&!opened.closed){opened.location.replace(url);setTimeout(()=>URL.revokeObjectURL(url),300000);return;}
  const link=document.createElement('a');link.href=url;link.download=String(name||'download').replace(/[\\/\x00-\x1f]/g,'_');link.dataset.downloadFeedbackSkip='true';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
 }
 async function transfer(url,options={},name='download',control=lastControl,opened=null){
  const feedback=begin(control),controller=new AbortController(),timer=setTimeout(()=>controller.abort(),180000);
  try{
   const response=await fetch(url,{...options,signal:controller.signal});
   if(!response.ok){let message='Download failed (HTTP '+response.status+').';try{message=(await response.json()).error||message;}catch(_){}throw new Error(message);}
   if(response.redirected&&/text\/html/i.test(response.headers.get('Content-Type')||''))throw new Error('Sign in again before downloading this file.');
   const disposition=response.headers.get('Content-Disposition')||'',utf=disposition.match(/filename\*=UTF-8''([^;]+)/i),plain=disposition.match(/filename="([^"\r\n]+)"/i);
   if(utf){try{name=decodeURIComponent(utf[1]);}catch(_){}}else if(plain)name=plain[1];
   const blob=await read(response,value=>feedback.update(value));handoff(blob,name,opened);feedback.update({phase:'Ready',percent:100});await new Promise(resolve=>setTimeout(resolve,250));return blob;
  }catch(error){if(opened&&!opened.closed)opened.close();throw error;}
  finally{clearTimeout(timer);feedback.finish();}
 }
 async function save(blob,name,control=lastControl){const feedback=begin(control);try{await new Promise(resolve=>setTimeout(resolve,0));handoff(blob,name);feedback.update({phase:'Ready',percent:100});await new Promise(resolve=>setTimeout(resolve,250));}finally{feedback.finish();}}
 const api={read,begin,transfer,save,get control(){return lastControl;}};
 if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
 root.LCPCDownloads=api;
 document.addEventListener('submit',event=>{lastControl=event.submitter||event.target.querySelector('button[type=submit],button:not([type])')||lastControl;},true);
 document.addEventListener('click',event=>{
  const control=event.target.closest?.('button,a,[role=button]');if(control)lastControl=control;
  const link=event.target.closest?.('a[href]');if(!link||link.dataset.downloadFeedbackSkip||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  if(link.getAttribute('aria-busy')==='true'){event.preventDefault();event.stopImmediatePropagation();return;}
  const url=new URL(link.href,location.href);if(url.origin!==location.origin||!/^https?:$/.test(url.protocol))return;
  const file=link.hasAttribute('download')||/\/api\/resources\/[^/]+\/download$/.test(url.pathname)||/^\/problems\/files\//.test(url.pathname)||/\.(pdf|zip|csv|cpp|java|py|txt|crt)$/i.test(url.pathname);
  if(!file)return;event.preventDefault();event.stopImmediatePropagation();
  if(link.nextElementSibling?.hasAttribute('data-download-error'))link.nextElementSibling.remove();
  let opened=null;if(link.target==='_blank'&&!link.hasAttribute('download')){opened=window.open('about:blank','_blank');if(opened)opened.opener=null;}
  const name=link.getAttribute('download')||decodeURIComponent(url.pathname.split('/').pop())||'download';
  transfer(url.href,{credentials:'same-origin',cache:'no-store'},name,link,opened).catch(error=>{
   let box=document.querySelector('[data-download-error]');if(!box){box=document.createElement('p');box.dataset.downloadError='';box.className='lcpc-download-error';box.setAttribute('role','alert');link.after(box);}box.textContent=error.message;
  });
 },true);
})(typeof globalThis!=='undefined'?globalThis:this);
