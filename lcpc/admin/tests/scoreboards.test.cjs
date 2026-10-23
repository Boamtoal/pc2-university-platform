const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const views=require('../../public-standings/scoreboards.js');
const renderer=require('../../branding/scoreboard-model.js');
const fixture=()=>({...JSON.parse(fs.readFileSync(path.join(__dirname,'../../branding/tests/fixtures/pc2-scoreboard.json'),'utf8')),publishedAt:new Date().toISOString(),release:{schema:1,frozen:true,preliminaryResultsCounted:false}});
test('public snapshot freshness rejects missing, stale and future updates',()=>{
 const p=fixture(),now=Date.parse(p.publishedAt);assert.equal(views.validate(p,{now,publicView:true}),p);
 for(const date of [undefined,'bad',new Date(now-31000).toISOString(),new Date(now+6000).toISOString()])assert.throws(()=>views.validate({...p,publishedAt:date},{now,publicView:true}));
 assert.throws(()=>views.validate({...p,release:{preliminaryResultsCounted:true}},{now,publicView:true}));
});
test('native release metadata controls frozen status including certified final release',()=>{
 const p=fixture();assert.equal(views.frozen(p),true);p.release.frozen=false;p.contestStandings.standingsHeader.scoreboardMessage='Final Scoreboard';assert.equal(views.frozen(p),false);
});
test('organizer and public display renderer work with strict CSP without inline styles',()=>{
 const html=renderer.render(fixture(),{strictStyles:true});assert.doesNotMatch(html,/style=|<script|onclick=/);assert.match(html,/title=/);assert.match(html,/lcpc-score-scroll/);
});
test('two dashboard views are explicit and only public view offers the display link',()=>{
 assert.match(views.render('live'),/Live Scoreboard/);assert.match(views.render('live'),/Internal only/);assert.doesNotMatch(views.render('live'),/data-display-link/);
 assert.match(views.render('public'),/Public Scoreboard/);assert.match(views.render('public'),/data-display-link/);
});
test('standalone page has no admin bundle, navigation, login, or private data endpoint',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../../public-standings/index.html'),'utf8');assert.doesNotMatch(html,/<nav|app\.js|\/api\/|8091|review\.html|#\/login/);assert.match(html,/data-public-display/);assert.match(html,/connect-src 'self'/);
 const script=fs.readFileSync(path.join(__dirname,'../../public-standings/scoreboards.js'),'utf8');assert.match(script,/credentials:'omit'/);assert.match(script,/fetch\('\.\/data\.json'/);
});
test('public display has one contest title and a deliberate timer slot beside it',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../../public-standings/index.html'),'utf8');
 assert.equal((html.match(/data-display-contest-title/g)||[]).length,1);assert.equal((html.match(/data-contest-clock/g)||[]).length,1);
 assert.match(html,/<header[\s\S]*class="lcpc-contest-clock display-clock" data-contest-clock[\s\S]*<\/header>/);
 assert.doesNotMatch(html,/Official released standings|resource-ui\.css|scoreboard-controls|Results submitted after/);
});
