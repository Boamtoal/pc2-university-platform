const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const guide=require('../../admin-ui/guide.js'),data=require('../../admin-ui/guide-content.js'),nav=require('../../admin-ui/workspace-nav.js');
test('guide covers full operating lifecycle and honest incomplete work',()=>{const ids=new Set(data.sections.map(s=>s.id));for(const id of ['network','roles','remote','contests','problems','judge-data','resources','identity','teams','clock','submissions','review','details','scoreboards','clarifications','monitoring','exports','learning','security','troubleshooting','advanced','limits','checklist'])assert.ok(ids.has(id),id);assert.equal(ids.size,data.sections.length);assert.equal(data.version,'1.0.0');assert.match(guide.guide(),/guide-search/);assert.ok(guide.matches(data.sections.find(s=>s.id==='network'),'DHCP'));assert.ok(!guide.matches(data.sections[0],'nonexistent-search-492'));});
test('guide escapes rendered content instead of executing documentation HTML',()=>{const html=guide.article({id:'safe',title:'<img onerror="x">',where:'A & B',paragraphs:['<script>alert(1)</script>'],steps:['<svg>'],limit:'<b>'});assert.doesNotMatch(html,/<script|<svg|<img/);assert.match(html,/&lt;script&gt;/);assert.match(html,/A &amp; B/);});
test('About preserves original authors and all four identities',()=>{const html=guide.about();for(const name of ['John Clevenger','Douglas Lane','Samir Ashoo','Troy Boudreau','California State University','Omar Al-Mukhtar University','Boamtoal','EPL-2.0','Project Nayuki'])assert.ok(html.includes(name.replaceAll('&','&amp;')),name);for(const logo of ['pc2-logo.png','icpc-logo.png','omu-logo.png','lcpc-logo.png'])assert.ok(html.includes(logo));assert.match(html,/original About information/);assert.match(html,/does not replace those credits/);});
test('Help sections are accessible without a live native snapshot and preserve guide focus on refresh',()=>{for(const id of ['guide','about'])assert.ok(nav.sections.some(([key])=>key===id));const app=fs.readFileSync(path.join(__dirname,'../../admin-ui/app.js'),'utf8');assert.ok(app.indexOf("state.tab==='guide')body=")<app.indexOf('else if(state.data)'));assert.match(app,/!\$\('platform-guide'\)/);assert.match(app,/!\$\('platform-about'\)/);});
test('guide search hides both table-of-contents entries and articles',()=>{const listeners={},elements={},root={querySelector:key=>elements[key],addEventListener:(name,fn)=>listeners[name]=fn};for(const s of data.sections){elements['#guide-'+s.id]={hidden:false};elements['[data-guide-topic="'+s.id+'"]']={hidden:false};}elements['#guide-search']={value:'zz-no-match-317',addEventListener:(name,fn)=>listeners['search-'+name]=fn};elements['#guide-count']={};elements['#guide-empty']={hidden:true};guide.mount(root);listeners['search-input']();assert.equal(elements['#guide-empty'].hidden,false);for(const s of data.sections)assert.equal(elements['#guide-'+s.id].hidden,true);elements['#guide-search'].value='';listeners['search-input']();assert.equal(elements['#guide-empty'].hidden,true);assert.equal(elements['#guide-count'].textContent,data.sections.length+' of '+data.sections.length+' topics');});

test('guide table of contents and chapter headings share stable numbering',()=>{
 const html=guide.guide();for(const [index,section] of data.sections.entries()){
  assert.ok(html.includes('data-guide-topic="'+section.id+'"><span class="guide-topic-number">'+(index+1)+'.</span>'));
  assert.ok(guide.article(section,index).includes('<span class="guide-chapter-number">'+(index+1)+'.</span>'));
 }
});

test('workspace map is one connected complete tree and stays collapsed until opened',()=>{
 const html=guide.workspaceMap(true);assert.match(html,/<details class="guide-workspace-map panel">/);assert.doesNotMatch(html,/<details[^>]*\bopen\b|guide-map-grid|guide-map-branch/);
 assert.equal((html.match(/<details\b/g)||[]).length,1);assert.equal((html.match(/class="guide-system-root"/g)||[]).length,1);
 for(const [page,,label] of nav.sections){assert.ok(html.includes(label.replaceAll('&','&amp;')));for(const [,name] of nav.views[page]||[])assert.ok(html.includes(name.replaceAll('&','&amp;')),name);}
 const viewer=guide.workspaceMap(false);assert.doesNotMatch(viewer,/data-guide-page="security"|data-guide-page="system"/);assert.doesNotMatch(viewer,/data-guide-view="deliveries"/);
});

test('support information states real limitations and both manuals use protected progress-enabled downloads',()=>{
 const html=guide.guide();
 for(const lang of ['en','ar'])assert.match(html,new RegExp('href="/api/manuals/'+lang+'" download="University_Contest_Platform_User_Guide_'+lang.toUpperCase()+'\\.pdf"'));
 const features=new Map(data.features.map(f=>[f.id,f]));
 for(const [id,status] of [['languages','Partly supported'],['autojudges','Requires external setup'],['balloons','Requires external setup'],['eventfeeds','Read-only'],['inputValidation','Read-only'],['shadow','Read-only'],['plugins','Read-only'],['host-portability','Not yet validated'],['historic-data','Unavailable'],['network-inventory','Unavailable']])assert.equal(features.get(id)?.status,status,id);
 assert.equal(features.size,data.features.length);
 for(const f of data.features){assert.ok(f.works&&f.limits&&f.alternative,f.id);assert.ok(html.includes(f.label.replaceAll('&','&amp;')),f.id);assert.doesNotMatch(f.works,/Managed native controls/);}
 assert.match(html,/not every PC² desktop feature/);assert.match(html,/Available means integrated within the stated limits/);
});
