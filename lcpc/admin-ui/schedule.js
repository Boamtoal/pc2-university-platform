/* Offline, country-aware calendar controls. The server resolves local time/DST. */
(function(root){
 'use strict';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const option=(value,label,selected)=>'<option value="'+esc(value)+'"'+(value===selected?' selected':'')+'>'+esc(label)+'</option>';
 function preferences(catalog,prefs){const country=catalog.countries.find(c=>c.code===prefs?.country)||catalog.countries.find(c=>c.code==='LY')||catalog.countries[0];if(!country)throw new Error('No supported time zones are available');return {country:country.code,timeZone:country.zones.some(z=>z.id===prefs?.timeZone)?prefs.timeZone:country.zones[0].id};}
 function render(catalog,prefs){const current=preferences(catalog,prefs),country=catalog.countries.find(c=>c.code===current.country);return '<label>Country<select name="scheduleCountry">'+catalog.countries.map(c=>option(c.code,c.name,current.country)).join('')+'</select></label><label>Time zone<select name="scheduleTimeZone">'+country.zones.map(z=>option(z.id,z.label,current.timeZone)).join('')+'</select></label><label class="wide">Scheduled start (local time)<input type="datetime-local" name="scheduledLocal" step="1" min="1900-01-01T00:00" max="9999-12-31T23:59:59"></label><label class="wide" id="schedule-occurrence-label" hidden>Repeated local time — choose UTC offset<select name="scheduleOccurrence"></select></label><div class="schedule-summary wide" id="schedule-summary" role="status" aria-live="polite">Loading the scheduled date…</div><p class="hint wide">Changing the country or time zone keeps the same scheduled instant and updates the local date/time shown. Edit the date/time to reschedule it. Clear the field to remove the scheduled start. Saving this date does not start the contest clock.</p>';}
 function selectedCandidate(result,occurrence){if(!result?.valid||result.empty)return null;if(!result.ambiguous)return result.candidates[0];return /^\d+$/.test(String(occurrence))?result.candidates[Number(occurrence)]||null:null;}
 function mount(form,{catalog,prefs,instant,request}){
  const country=form.elements.scheduleCountry,zone=form.elements.scheduleTimeZone,local=form.elements.scheduledLocal,fold=form.elements.scheduleOccurrence,label=form.querySelector('#schedule-occurrence-label'),summary=form.querySelector('#schedule-summary'),submit=form.querySelector('.form-actions button');
  let previous=preferences(catalog,prefs),version=0,timer=null,disposed=false,result=null;
  const connected=()=>!disposed&&form.isConnected;
  function busy(value,lockDate=false){country.disabled=value;zone.disabled=value;local.disabled=value&&lockDate;submit.disabled=value;}
  function showError(error){summary.className='schedule-summary wide error';summary.textContent=error.message||String(error);submit.disabled=true;}
  function show(data,keepOccurrence='',setLocal=false){
   result=data;if(setLocal)local.value=data.empty?'':data.local;label.hidden=!data.ambiguous;fold.replaceChildren();
   if(data.ambiguous){fold.add(new Option('Choose the intended UTC offset',''));data.candidates.forEach((c,i)=>fold.add(new Option(c.offset+' · '+c.utcLabel,String(i))));fold.value=data.selected!==null&&data.selected!==undefined?String(data.selected):String(keepOccurrence||'');}
   summary.className='schedule-summary wide';summary.replaceChildren();
   if(!data.valid){showError(new Error(data.error));return;}
   if(data.empty){summary.textContent='No scheduled start. The current contest clock is unchanged.';submit.disabled=false;return;}
   const chosen=selectedCandidate(data,fold.value);const first=document.createElement('strong');first.textContent=data.display+' · '+zone.value;summary.append(first,document.createElement('br'));
   if(!chosen){summary.append('This local time occurs twice because the clocks move back. Choose the intended UTC offset above.');submit.disabled=true;return;}
   summary.append(chosen.offset+' · '+chosen.utcLabel);submit.disabled=false;
  }
  async function display(payload,{keep='',setLocal=false,lockDate=false}={}){
   const ticket=++version;busy(true,lockDate);summary.className='schedule-summary wide';summary.textContent='Updating the local date and time…';
   try{const value=await request({...payload,country:previous.country,timeZone:previous.timeZone});if(!connected()||ticket!==version)return null;busy(false);show(value,keep,setLocal);return value;}
   catch(error){if(connected()&&ticket===version){busy(false);showError(error);}throw error;}
  }
  async function localPreview(keep=fold.value){return display({local:local.value},{keep});}
  async function changeZone(newCountry,newZone){
   clearTimeout(timer);const old={...previous},oldOccurrence=fold.value;busy(true,true);const ticket=++version;
   try{
    const before=await request({local:local.value,country:old.country,timeZone:old.timeZone});if(!connected()||ticket!==version)return;
    if(!before.valid)throw new Error(before.error);const chosen=selectedCandidate(before,oldOccurrence);if(!before.empty&&!chosen)throw new Error('Choose the intended UTC offset before changing the time zone.');
    const countryRow=catalog.countries.find(c=>c.code===newCountry);if(!countryRow)throw new Error('Choose a country');
    const chosenZone=countryRow.zones.some(z=>z.id===newZone)?newZone:countryRow.zones[0].id;
    zone.replaceChildren(...countryRow.zones.map(z=>new Option(z.label,z.id)));zone.value=chosenZone;country.value=newCountry;previous={country:newCountry,timeZone:chosenZone};
    await display(chosen?{instant:chosen.utc}:{local:''},{setLocal:true,lockDate:true});
   }catch(error){if(connected()){previous=old;country.value=old.country;const row=catalog.countries.find(c=>c.code===old.country);zone.replaceChildren(...row.zones.map(z=>new Option(z.label,z.id)));zone.value=old.timeZone;busy(false);showError(error);}}
  }
  country.addEventListener('change',()=>changeZone(country.value,null));zone.addEventListener('change',()=>changeZone(previous.country,zone.value));
  local.addEventListener('input',()=>{clearTimeout(timer);version++;fold.value='';result=null;submit.disabled=true;summary.textContent='Checking the local date and time…';timer=setTimeout(()=>localPreview('').catch(()=>{}),250);});
  fold.addEventListener('change',()=>{if(result)show({...result,selected:null},fold.value);});
  display(instant?{instant}:{local:''},{setLocal:true}).catch(()=>{});
  return {dispose(){disposed=true;version++;clearTimeout(timer);},async value(){clearTimeout(timer);const keep=fold.value,data=await localPreview(keep);if(!data?.valid)throw new Error(data?.error||'Choose a valid date and time');const chosen=selectedCandidate(data,fold.value);if(!data.empty&&!chosen)throw new Error('Choose the intended UTC offset');return {args:{scheduledLocal:local.value,scheduleCountry:previous.country,scheduleTimeZone:previous.timeZone,...(data.ambiguous?{scheduleOccurrence:Number(fold.value)}:{})},description:data.empty?'No scheduled start':data.display+' '+chosen.offset+' ('+previous.timeZone+') · '+chosen.utcLabel};}};
 }
 const api={render,mount,preferences,selectedCandidate};if(typeof module==='object'&&module.exports)module.exports=api;else root.LCPCSchedule=api;
})(typeof window==='object'?window:this);
