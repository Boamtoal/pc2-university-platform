const test=require('node:test'),assert=require('node:assert/strict');
const {read}=require('../download-feedback.js');
function response(parts,headers={}){return new Response(new ReadableStream({start(c){for(const p of parts)c.enqueue(new Uint8Array(p));c.close();}}),{headers});}
test('known download size reports received byte percentages and preserves exact file contents',async()=>{
 const updates=[],blob=await read(response([[1,2],[3,4]],{'Content-Length':'4','Content-Type':'application/zip'}),v=>updates.push(v));
 assert.deepEqual([...new Uint8Array(await blob.arrayBuffer())],[1,2,3,4]);assert.deepEqual(updates.map(x=>x.percent),[50,99,100]);assert.equal(blob.type,'application/zip');
});
test('unknown or compressed response sizes stay indeterminate until receipt completes',async()=>{
 for(const headers of [{},{'Content-Length':'1','Content-Encoding':'gzip'}]){const updates=[];await read(response([[1,2],[3,4]],headers),v=>updates.push(v));assert.equal(updates[0].percent,null);assert.equal(updates.at(-1).percent,100);}
});
test('an interrupted download fails and is never marked complete',async()=>{
 const updates=[],broken={headers:new Headers({'Content-Length':'100'}),body:{getReader(){return {read:async()=>{throw Error('connection lost');},cancel:async()=>{}};}}};
 await assert.rejects(()=>read(broken,v=>updates.push(v)),/connection lost/);assert.equal(updates.some(v=>v.percent===100),false);
});
