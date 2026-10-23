const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {render}=require('../scoreboard-model.js');
const sample=()=>({contestStandings:{standingsHeader:{title:'LCPC',problem:[{id:1,title:'A problem',attempts:5,numberSolved:1},{id:2,title:'B problem',attempts:2,numberSolved:0}]},teamStanding:[{teamName:'Binary',overallRank:2,solved:1,points:111,totalAttempts:5,problemSummaryInfo:[{index:1,isSolved:true,solutionTime:71,attempts:3},{index:2,isSolved:false,attempts:2}]}]}});
test('uses server rank, penalty, solved time and per-problem attempts',()=>{
 const html=render(sample());
 assert.match(html,/lcpc-rank">2</);assert.match(html,/>111<\/td>/);
 assert.match(html,/accepted[^>]*><strong>\+2<\/strong><span>Accepted<\/span><small>71 min/);
 assert.match(html,/rejected[^>]*><strong>−2<\/strong>/);
 assert.match(html,/Solved \/ attempts/);assert.match(html,/>1 \/ 5<\/td>/);
});
test('pending/frozen result stays pending and untouched stays empty',()=>{
 const data=sample();data.contestStandings.teamStanding[0].problemSummaryInfo=[{index:1,isPending:true,isSolved:false,solutionTime:100,attempts:3}];
 const html=render(data);assert.match(html,/pending[^>]*><strong>\?<\/strong><span>Pending/);assert.match(html,/untouched[^>]*><strong>—/);assert.doesNotMatch(html,/100 min/);
});
test('zero problems stays concise; arbitrary problem counts get columns',()=>{
 const data=sample();data.contestStandings.standingsHeader.problem=[];
 assert.doesNotMatch(render(data),/class="lcpc-problem"|lcpc-empty-problems/);
 data.contestStandings.standingsHeader.problem=Array.from({length:30},(_,i)=>({id:i+1,title:'Problem '+i}));
 const html=render(data);assert.equal((html.match(/class="lcpc-problem"/g)||[]).length,30);assert.match(html,/<text[^>]*>AD<\/text>/);
});
test('problem headers show native balloon color and letter with full titles in tooltips',()=>{
 const data=sample();data.contestStandings.standingsHeader.problem[0].title='The Three Divisors of Acacus';
 data.contestStandings.standingsHeader.problem[0].colorRGB='#FF1234';data.contestStandings.standingsHeader.problem[0].colorName='Red';
 const html=render(data,{strictStyles:true});
 assert.match(html,/title="The Three Divisors of Acacus · Balloon: Red"/);assert.match(html,/<svg class="lcpc-problem-card"[^>]*>[\s\S]*?<text[^>]*>A<\/text><\/svg>/);assert.match(html,/fill="#FF1234"/);assert.doesNotMatch(html,/<span>Th<\/span>|style=/);
 assert.doesNotMatch(html,/<span>The Three Divisors of Acacus<\/span>/);
});
test('formal interface contains no explanatory paragraphs or Arabic UI text',()=>{
 const html=render(sample());assert.doesNotMatch(html,/[\u0600-\u06ff]|lcpc-score-help|lcpc-legend|Official PC²/);
 assert.match(html,/>Attempts<\/th>/);
});
test('team names, contest messages, and problem names cannot insert HTML',()=>{
 const data=sample();data.contestStandings.teamStanding[0].teamName='<img src=x onerror=alert(1)>';data.contestStandings.standingsHeader.scoreboardMessage='<script>bad()</script>';data.contestStandings.standingsHeader.problem[0].title='" onmouseover="bad';
 const html=render(data);assert.doesNotMatch(html,/<img|<script|title="" onmouseover/);assert.match(html,/&lt;img/);assert.match(html,/&quot; onmouseover/);
});
test('actual historical PC2 response renders all teams and both problem columns',()=>{
 const data=JSON.parse(fs.readFileSync(__dirname+'/fixtures/pc2-scoreboard.json'));
 const html=render(data);assert.match(html,/OMU Test Alpha/);assert.match(html,/Technical Test 5/);assert.equal((html.match(/class="lcpc-problem"/g)||[]).length,2);assert.match(html,/9 min/);
});

test('metadata matches native problem IDs and titles; unassigned and invalid colors are never invented',()=>{
 const data=sample(),problemMetadata=[{id:2,title:'B problem',letter:'F',colorName:'Blue',colorRGB:'#0000ff'},{id:1,title:'wrong problem',colorRGB:'#ff0000'}];
 const html=render(data,{problemMetadata,strictStyles:true});assert.match(html,/<text[^>]*>F<\/text>/);assert.match(html,/fill="#0000ff"/);assert.doesNotMatch(html,/fill="#ff0000"/);assert.match(html,/Balloon: Not assigned/);
 data.contestStandings.standingsHeader.problem[0].colorRGB='red" onload="alert(1)';assert.doesNotMatch(render(data),/fill="red|onload=/);
});
test('audience standings contain only rank, team, solved, penalty and compact problem results',()=>{
 const html=render(sample(),{audience:true,strictStyles:true});
 assert.doesNotMatch(html,/lcpc-score-heading|lcpc-score-meta|Last update|<tfoot|>Attempts<|lcpc-attempts-column|<span>Accepted<|<span>Not solved<| tries/);
 assert.match(html,/lcpc-audience-table/);assert.match(html,/accepted[^>]*><strong>\+2<\/strong><small>71<\/small>/);assert.match(html,/rejected[^>]*><strong>−2<\/strong><\/td>/);
 assert.match(html,/Accepted at 71 minutes; 3 attempts/);
 const data=sample();data.contestStandings.standingsHeader.scoreboardMessage='Frozen after 45 minutes';data.contestStandings.teamStanding[0].problemSummaryInfo=[{index:1,isPending:true,isSolved:false,solutionTime:999,attempts:3}];
 const pending=render(data,{audience:true});assert.match(pending,/pending[^>]*><strong>\?<\/strong><\/td>/);assert.doesNotMatch(pending,/999|lcpc-server-notice/);
 data.contestStandings.teamStanding=[];assert.match(render(data,{audience:true}),/colspan="6"/);
});

test('balloon cards retain readable text on dark and light colors in both scoreboard views',()=>{
 const colors=[['#000000','#ffffff'],['#ffffff','#000000'],['#0000ff','#ffffff'],['#ffff00','#000000'],['#ff0000','#000000'],['#ff69b4','#000000'],['#800080','#ffffff'],['#00ff00','#000000'],['#ffa500','#000000']];
 for(const audience of [false,true])for(const [background,foreground]of colors){
  const data=sample();data.contestStandings.standingsHeader.problem=[{id:1,title:'A problem',colorRGB:background,colorName:'Fixture color'}];
  const html=render(data,{audience,strictStyles:true}),header=html.match(/<th scope="col" class="lcpc-problem"[^>]*>([\s\S]*?)<\/th>/)[1];
  assert.match(header,/<svg class="lcpc-problem-card"/);assert.ok(header.includes('rx="7" fill="'+background+'"'));assert.ok(header.includes('fill="'+foreground+'">A</text>'));
  assert.doesNotMatch(header,/<circle|lcpc-problem-color|<strong>|style=/);
 }
});
test('missing balloon color has a neutral letter card and never hides the missing assignment',()=>{
 const html=render(sample(),{strictStyles:true});assert.match(html,/lcpc-problem-card-unassigned/);assert.match(html,/aria-label="A: A problem · Balloon: Not assigned"/);assert.match(html,/<text[^>]*>A<\/text>/);
 const data=sample();data.contestStandings.standingsHeader.problem[0].letter='WWW';
 assert.match(render(data,{strictStyles:true}),/font-size="13"[^>]*>WWW<\/text>/);
});

test('first solve requires authoritative metadata, visible acceptance and exact team identity',()=>{
 const data=sample();data.contestStandings.teamStanding[0].teamKey='1TEAM2';data.contestStandings.standingsHeader.problem[0].firstToSolveTeams=['1TEAM2'];
 for(const audience of [false,true]){const html=render(data,{audience,strictStyles:true});assert.match(html,/lcpc-first-solve-badge/);assert.match(html,/title="First to solve · A problem/);assert.match(html,/>111<\/td>/);}
 data.contestStandings.teamStanding[0].problemSummaryInfo[0]={index:1,isSolved:false,isPending:true,solutionTime:71,attempts:3};assert.doesNotMatch(render(data),/lcpc-first-solve-badge/);
 data.contestStandings.teamStanding[0].problemSummaryInfo[0].isSolved=true;data.contestStandings.standingsHeader.problem[0].firstToSolveTeams=['2TEAM2'];assert.doesNotMatch(render(data),/lcpc-first-solve-badge/);
 delete data.contestStandings.standingsHeader.problem[0].firstToSolveTeams;assert.doesNotMatch(render(data),/lcpc-first-solve-badge/);
});
