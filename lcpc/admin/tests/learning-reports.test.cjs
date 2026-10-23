const test=require('node:test'),assert=require('node:assert/strict');
const {content}=require('../../admin-ui/learning-reports.js');
test('learning workspace provides explicit post-contest generation, per-team downloads and safe labels',()=>{
 const data={ready:true,eligibleTeams:[{login:'team1',name:'<script>bad</script>',attempts:2}],ignoredTeams:1,problems:[{id:'p1',letter:'A',name:'<img src=x>',difficulty:1350,difficultyEstimated:true,referenceAvailable:true,editorialAvailable:false}],exports:[{id:'a'.repeat(32),created:'now',bytes:1024,teams:[{login:'team1',name:'Team one'}]}]};
 const html=content(data);assert.match(html,/Create learning package/);assert.match(html,/data-team="team1"/);assert.match(html,/data-team="all"/);assert.match(html,/1350 \(estimated\)/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>|<img src=x>/);assert.match(html,/Official submissions and judgements are unchanged/);assert.match(html,/test association/);
});
test('a running or active contest cannot start learning generation from the interface',()=>{
 const data={ready:false,eligibleTeams:[],ignoredTeams:1,problems:[],exports:[],job:{kind:'learning',status:'running',message:'Preparing team 1'}};
 assert.match(content(data),/data-learning-generate disabled/);assert.match(content(data),/Latest report job: running/);
});
