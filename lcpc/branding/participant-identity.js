/* Public identity only: no team/session data, external URLs, private endpoints or HTML injection. */
(function(root){
 'use strict';
 let value=null,busy=false,queued=false;
 const locations=['header','resources','scoreboard'];
 function validate(data){
  if(data?.schema!==1||typeof data.version!=='string'||!Array.isArray(data.logos)||data.logos.length!==4)throw new Error('Invalid participant identity');
  for(const key of ['name','universityName','universityNameAr','contestLabel','instructionsTitle','instructionsTitleAr','instructionsSubtitle','instructionsSubtitleAr','footerText','footerTextAr'])if(typeof data[key]!=='string'||data[key].length>200)throw new Error('Invalid identity text');
  const ids=new Set();for(const logo of data.logos){if(!['pc2','icpc','university','contest'].includes(logo.id)||ids.has(logo.id)||typeof logo.label!=='string'||!/^\/assets\/lcpc-branding\/identity\/[a-f0-9]{64}\.(png|jpg)$/.test(logo.url)||locations.some(key=>typeof logo[key]!=='boolean'))throw new Error('Invalid identity logo');ids.add(logo.id);}
  if(data.colors&&root.LCPCParticipantTheme)root.LCPCParticipantTheme.validate(data.colors);
  return data;
 }
 function logos(data,location){return data.logos.filter(logo=>logo[location]);}
 if(typeof module!=='undefined'&&module.exports){module.exports={validate,logos};return;}
 function text(element,content){if(element&&element.textContent!==content)element.textContent=content;}
 function renderLogos(container,location){
  if(!container||!value)return;
  const signature=value.version+':'+location;if(container.dataset.participantIdentity===signature)return;
  container.replaceChildren();
  for(const logo of logos(value,location)){const image=document.createElement('img');image.src=logo.url;image.alt=logo.label;image.dataset.identitySlot=logo.id;image.dataset.custom=String(logo.custom===true);container.append(image);}
  container.dataset.participantIdentity=signature;
 }
 function renderHeader(container){
  if(!container||!value)return false;
  let managed=container.querySelector('.lcpc-managed-identity');
  for(const image of container.querySelectorAll('img'))if(!image.closest('.lcpc-managed-identity')){if(!image.hasAttribute('data-lcpc-native-logo'))image.setAttribute('data-lcpc-native-logo','');}
  if(!managed){managed=document.createElement('div');managed.className='lcpc-managed-identity';const images=document.createElement('div');images.className='lcpc-managed-logos';const caption=document.createElement('p');caption.className='lcpc-identity-caption';managed.append(images,caption);container.append(managed);}
  renderLogos(managed.querySelector('.lcpc-managed-logos'),'header');text(managed.querySelector('p'),value.name+' · '+value.universityName);
  return true;
 }
 function footer(ar){return ar?(value.footerTextAr||[value.universityNameAr||value.universityName,value.name].join(' · ')):(value.footerText||[value.universityName,value.name].join(' · '));}
 function apply(){
  if(!value)return;
  if(value.colors&&root.LCPCParticipantTheme)root.LCPCParticipantTheme.apply(value.colors);
  renderHeader(document.querySelector('app-header>header .logo-container'));
  const resources=document.body.classList.contains('lcpc-resource-page'),instructions=document.body.classList.contains('lcpc-instructions-page'),ar=instructions&&document.documentElement.lang==='ar';
  if(resources){
   renderLogos(document.querySelector('body>header .logos'),'resources');
   if(instructions){text(document.getElementById('page-heading'),ar?(value.instructionsTitleAr||value.instructionsTitle):value.instructionsTitle);text(document.getElementById('page-subtitle'),ar?(value.instructionsSubtitleAr||value.instructionsSubtitle):value.instructionsSubtitle);}
   else{text(document.querySelector('body>header .brand h1'),value.name);text(document.querySelector('body>header .sub'),value.contestLabel+' · '+value.universityName);}
   document.querySelectorAll('footer').forEach(element=>text(element,footer(element.closest('[lang=ar]')!==null)));
  }
  const display=document.querySelector('.display-brand');if(display){text(display.querySelector('p'),value.name);renderLogos(display.querySelector('.display-logos'),'scoreboard');let institution=display.querySelector('.lcpc-public-institution');if(!institution){institution=document.createElement('span');institution.className='lcpc-public-institution';display.querySelector('h1').after(institution);}text(institution,value.universityName+' · '+value.contestLabel);}
  const board=document.getElementById('lcpc-standings-branding');if(board){renderLogos(board,'scoreboard');board.setAttribute('aria-label',value.name+' organizers');}
  document.querySelectorAll('.lcpc-eyebrow').forEach(e=>text(e,value.name+' · STANDINGS'));
  const nativeFooter=document.querySelector('app-footer footer');if(nativeFooter){let caption=nativeFooter.querySelector('.lcpc-organizer-credit');if(!caption){caption=document.createElement('div');caption.className='lcpc-organizer-credit';nativeFooter.prepend(caption);}text(caption,footer(false));}
  let title;
  if(resources)title=(instructions?(ar?(value.instructionsTitleAr||value.instructionsTitle):value.instructionsTitle):'Problem PDFs')+' · '+value.name;
  else if(display)title='Public Scoreboard · '+value.name;
  else if(document.querySelector('app-root')){const labels={runs:'My submissions',clarifications:'Clarifications',options:'Preferences',scoreboard:'Scoreboard',login:'Team sign in',logout:'Sign out'};const route=location.hash.slice(2).split('?')[0];title=(labels[route]||'Participant workspace')+' · '+value.name;}
  if(title&&document.title!==title)document.title=title;
 }
 function schedule(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;apply();});}
 async function refresh(){
  if(busy)return;busy=true;
  try{const response=await fetch('/assets/lcpc-branding/participant-identity.json',{credentials:'omit',cache:'no-store'});if(!response.ok)return;const next=validate(await response.json());if(next.version!==value?.version){value=next;apply();document.dispatchEvent(new Event('lcpc-participant-identity'));}}catch(_){}finally{busy=false;}
 }
 const api={get value(){return value;},renderHeader,renderLogos,refresh};root.LCPCParticipantIdentity=api;
 new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['lang']});
 document.addEventListener('DOMContentLoaded',schedule);window.addEventListener('hashchange',schedule);window.addEventListener('focus',refresh);refresh();setInterval(refresh,30000);
})(typeof globalThis!=='undefined'?globalThis:this);
