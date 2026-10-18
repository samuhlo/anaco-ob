const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
function resource(fetch){
 const ctx=vm.createContext({URL,content:{fetch},AbortController,setTimeout,clearTimeout,crypto:require('node:crypto').webcrypto,btoa});
 vm.runInContext(fs.readFileSync('extension/resource.js','utf8'),ctx);return ctx.AnacoObResource;
}
test('page reads use content.fetch with credentials and transfer bounded chunks',async()=>{
 const input=new Uint8Array(950000);input.forEach((_,i)=>input[i]=i%251);let options;
 const r=resource(async(url,o)=>{options=o;return new Response(input);});
 const opened=await r.open('https://player.example/video.mp4',1000000),chunks=[];
 for(;;){const piece=await r.read(opened.id);if(piece.done)break;const bytes=Buffer.from(piece.data,'base64');assert.ok(bytes.length<=393216);chunks.push(bytes);}
 assert.equal(options.credentials,'include');assert.deepEqual(Buffer.concat(chunks),Buffer.from(input));
 await assert.rejects(r.read(opened.id),/interrumpió/);
});
test('page HTTP failures and login pages are never transferred as media',async()=>{
 for(const [response,status,reason] of [[new Response('',{status:403}),403,undefined],[new Response('<html>Login</html>',{headers:{'content-type':'text/html'}}),200,'login-response']]){
  const result=await resource(async()=>response).open('https://player.example/private',1000000);
  assert.equal(result.ok,false);assert.equal(result.status,status);assert.equal(result.reason,reason);assert.equal(result.id,undefined);
 }
});
test('streamed resources exceeding the limit are cancelled and cannot be resumed',async()=>{
 const r=resource(async()=>new Response(new Uint8Array(700000))),opened=await r.open('https://player.example/video.mp4',1000);
 await assert.rejects(r.read(opened.id),/límite/);await assert.rejects(r.read(opened.id),/interrumpió/);
});
