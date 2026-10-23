const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('lcpc/admin-ui/app.js','utf8');
const start=source.indexOf('function problems(){'),end=source.indexOf('\n function resources()',start);
function render(problem){
 const context={state:{data:{problems:[{letter:'A',id:'p',name:'Example',timeLimit:2,memoryLimit:256,tests:80,active:true,...problem}]}},owner:()=>false,manage:()=>false,button:()=>'',esc:x=>String(x),balloonCell:()=>'',table:(heads,rows)=>heads.join('|')+'\n'+rows.join('')};
 return vm.runInNewContext('('+source.slice(start,end)+')()',context);
}
test('contest problems display numeric difficulty and identify estimates',()=>{
 const html=render({difficulty:1350,difficultyEstimated:true});assert.match(html,/ID\|Name\|Difficulty\|Balloon/);assert.match(html,/>≈1350<\/td>/);assert.match(html,/Estimated difficulty/);
 assert.match(render({difficulty:1800,difficultyEstimated:false}),/>1800<\/td>/);
});
test('missing values stay unassigned rather than becoming zero or a guessed rating',()=>{
 const html=render({difficulty:null});assert.match(html,/>—<\/td>/);assert.doesNotMatch(html,/>0<\/td>/);
});
