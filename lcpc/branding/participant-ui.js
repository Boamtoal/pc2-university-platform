/* Presentation and accessible labels only. No API, auth, form-value or scoring changes. */
(() => {
 'use strict';
 const pages={
  '/runs':['My submissions','Submit your solutions and follow their final judging results.'],
  '/clarifications':['Clarifications','Read announcements and follow your questions to the judges.'],
  '/options':['Preferences','Manage your notification preferences for this contest.']
 };
 function text(element,value){if(element.textContent!==value)element.textContent=value;}
 function node(tag,cls,value){const e=document.createElement(tag);e.className=cls;if(value)e.textContent=value;return e;}
 let queued=false;
 const observer=new MutationObserver(schedule);
 function watch(){observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});}
 function schedule(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;update();});}
 function update(){
  observer.disconnect();
  try{
   const route=location.hash.slice(1).split('?')[0],authenticated=!!globalThis.LCPCSession?.isAuthenticated();
   const host=document.querySelector('app-root .app-content>ng-component');
   const page=authenticated?pages[route]:null;
   document.querySelectorAll('.lcpc-page-intro').forEach(intro=>{if(!page||intro.parentElement!==host)intro.remove();});
   if(page&&host){
    let intro=host.querySelector(':scope>.lcpc-page-intro');
    if(!intro){intro=node('section','lcpc-page-intro');const box=node('div','');box.append(node('h1',''),node('p',''));intro.append(box);host.prepend(intro);}
    text(intro.querySelector('h1'),page[0]);text(intro.querySelector('p'),page[1]);
   }
   const form=document.querySelector('.login-container form');
   if(form){
    const heading=form.querySelector('.header');if(heading)text(heading,'Team sign in');
    if(heading&&!form.querySelector('.lcpc-login-intro'))heading.after(node('p','lcpc-login-intro','Use the team account provided by the organizers. Read Instructions before you begin.'));
    for(const [type,label,complete] of [['text','Team username','username'],['password','Password','current-password']]){
     const input=form.querySelector('input[type="'+type+'"]');if(!input)continue;
     if(!input.id)input.id='lcpc-login-'+type;
     if(!input.parentElement.querySelector('.lcpc-input-label')){const caption=node('label','lcpc-input-label',label);caption.htmlFor=input.id;input.before(caption);}
     input.setAttribute('autocomplete',complete);input.setAttribute('aria-label',label);
     if(type==='text'){input.setAttribute('autocapitalize','none');input.setAttribute('spellcheck','false');}
    }
   }
   document.querySelectorAll('app-header>header>nav>a').forEach(link=>{
    const active=authenticated&&link.classList.contains('active');
    if(active&&link.getAttribute('aria-current')!=='page')link.setAttribute('aria-current','page');
    if(!active&&link.hasAttribute('aria-current'))link.removeAttribute('aria-current');
   });
   // Preserve the existing table, rows, filters, Material controls and Angular listeners.
   document.querySelectorAll('ng-component .table-container>table').forEach(table=>{
    if(!table.hasAttribute('aria-label'))table.setAttribute('aria-label',route==='/runs'?'Your contest submissions':route==='/clarifications'?'Contest clarifications':'Contest results');
    table.querySelectorAll('th').forEach(cell=>{if(!cell.hasAttribute('scope'))cell.setAttribute('scope','col');});
   });
   document.querySelectorAll('ng-component .table-message').forEach(message=>{
    if(!message.hasAttribute('role'))message.setAttribute('role','status');
   });
  }finally{watch();}
 }
 document.addEventListener('DOMContentLoaded',schedule);document.addEventListener('lcpc-auth-change',schedule);window.addEventListener('hashchange',schedule);schedule();
})();
