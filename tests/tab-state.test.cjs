const I18N = require('./i18n.cjs');
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function app(){
 const data={};
 const event=()=>({addListener(){}});
 const browser={webNavigation:{onCompleted:event()},runtime:{getURL:p=>'moz-extension://test/'+p,onMessage:event()},permissions:{contains:async()=>true},storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,data[k]])),set:async values=>Object.assign(data,values)}},tabs:{onRemoved:event()},browserAction:{onClicked:event()},commands:{onCommand:event()},menus:{create(){},onClicked:event()}};
 const ctx=vm.createContext({browser,URL,crypto:require('node:crypto').webcrypto,setTimeout,clearTimeout,AbortSignal});
 vm.runInContext(I18N+fs.readFileSync('extension/detection.js','utf8')+fs.readFileSync('extension/background.js','utf8'),ctx);
 return {ctx,data};
}
const tab=id=>({id,url:`https://course.example/page-${id}`,windowId:1,title:`Page ${id}`});
const capture=id=>({kind:'article',url:tab(id).url,title:`Page ${id}`,text:'Readable article body.',contentReady:true,images:[],documents:[],videos:[],warnings:[]});
test('a late detection cannot replace the newly selected tab',async()=>{
 const {ctx,data}=app();let release;
 ctx.delayed=new Promise(resolve=>{release=resolve;});ctx.answer=capture(2);
 vm.runInContext('scanTab=tab=>tab.id===1?delayed:Promise.resolve(answer)',ctx);
 ctx.a=tab(1);ctx.b=tab(2);
 const first=vm.runInContext('capture(a)',ctx);
 await new Promise(resolve=>setImmediate(resolve));
 await vm.runInContext('capture(b)',ctx);
 release(capture(1));await first;
 assert.equal(data.currentCapture.source.tabId,2);assert.equal(data.pageContext.tabId,2);
});
test('generation continues while tab detection changes and its result stays with its source',async()=>{
 const {ctx,data}=app();ctx.a=tab(1);ctx.b=tab(2);ctx.answer=capture(2);
 data.operation='Transcribiendo el curso…';
 vm.runInContext('scanTab=()=>Promise.resolve(answer)',ctx);
 await vm.runInContext('capture(b)',ctx);
 assert.equal(data.operation,'Transcribiendo el curso…');
 ctx.generated={...capture(1),id:'draft-1',source:{tabId:1,url:tab(1).url,windowId:1}};ctx.draft={capture:ctx.generated,draft:{body:'Summary'}};
 await vm.runInContext('publishCapture(generated,draft)',ctx);
 assert.equal(data.currentCapture.source.tabId,2);
 await vm.runInContext('capture(a,{}, {fresh:false})',ctx);
 assert.equal(data.currentCapture.id,'draft-1');assert.equal(data.draftResult.draft.body,'Summary');
});

test('unavailable subtitle tracks fall back to the already authorized audio resource',async()=>{
 const {ctx,data}=app();ctx.btoa=btoa;
 data.currentCapture={...capture(1),source:{tabId:1,url:tab(1).url,windowId:1}};
 data.pageContext={tabId:1,url:tab(1).url,status:'ready'};
 const calls=[];
 ctx.fetch=async url=>url.endsWith('.vtt')?new Response('Forbidden',{status:403}):new Response(new Uint8Array([1,2,3]));
 ctx.native=async message=>{
  calls.push(message);
  if(message.action==='upload_begin')return {upload:'test-upload'};
  if(message.action==='upload_finish')return {id:'video-1',kind:'video',url:tab(1).url,images:[],warnings:[],text:'Recovered transcript'};
  return {};
 };
 ctx.request={kind:'subtitle-url',url:'https://media.example/missing.vtt',pageUrl:tab(1).url,fallback:{kind:'video',url:'https://media.example/video.mp4',name:'video.mp4'}};
 await vm.runInContext('importResource(request)',ctx);
 assert.equal(data.currentCapture.id,'video-1');
 assert.equal(data.currentCapture.source.tabId,1);
 assert.ok(calls.some(m=>m.action==='upload_finish'));
 assert.ok(!calls.some(m=>m.action==='subtitles'));
 assert.equal(data.operation,'');
});

test('resource extraction rejects a click belonging to an older tab',async()=>{
 const {ctx,data}=app();data.currentCapture={token:'new-page'};
 ctx.request={kind:'pdf',url:'https://course.example/old.pdf',token:'old-page'};
 await assert.rejects(vm.runInContext('importResource(request)',ctx),/pestaña cambió/);
 assert.equal(data.operation,undefined);
});

test('automatic reader mutations do not clear or rebuild the current capture',async()=>{
 const {ctx,data}=app();ctx.a=tab(1);
 data.currentCapture={...capture(1),token:'stable-reader',reader:{pages:Array.from({length:55},(_,i)=>({id:String(i)}))}};
 data.pageContext={tabId:1,url:tab(1).url,status:'ready'};
 vm.runInContext('scanTab=()=>{throw new Error("automatic rescan of a reader");}',ctx);
 await vm.runInContext('capture(a,{}, {automatic:true})',ctx);
 assert.equal(data.currentCapture.token,'stable-reader');
 assert.equal(data.currentCapture.reader.pages.length,55);
});

test('a long job pins title, source and progress when another tab is activated',async()=>{
 const {ctx,data}=app();ctx.a=tab(1);ctx.b=tab(2);ctx.owner={...capture(1),token:'book',source:{tabId:1,url:tab(1).url,session:'test'}};
 ctx.work=await vm.runInContext('beginWork(owner,"Extrayendo página 23 de 55…")',ctx);
 vm.runInContext('scanTab=()=>{throw new Error("should not scan the other tab during work");}',ctx);
 await vm.runInContext('capture(b,{}, {automatic:true})',ctx);
 assert.equal(data.currentCapture.token,'book');assert.equal(data.activeWork.source.tabId,1);assert.equal(data.pageContext.url,tab(1).url);
 assert.match(data.operation,/23 de 55/);
 await vm.runInContext('endWork(work)',ctx);
 assert.equal(data.activeWork,null);assert.equal(data.operation,'');
});
test('a detection already in flight cannot overwrite a newly pinned job',async()=>{
 const {ctx,data}=app();ctx.b=tab(2);let release;ctx.pending=new Promise(resolve=>release=resolve);
 vm.runInContext('scanTab=()=>pending',ctx);
 const detecting=vm.runInContext('capture(b)',ctx);await new Promise(resolve=>setImmediate(resolve));
 ctx.owner={...capture(1),source:{tabId:1,url:tab(1).url},token:'source-book'};
 await vm.runInContext('beginWork(owner,"Reading the book")',ctx);
 release(capture(2));await detecting;
 assert.equal(data.currentCapture.token,'source-book');assert.equal(data.activeWork.title,'Page 1');
});

test('resource downloads use the selected iframe and avoid an unnecessary background request',async()=>{
 const {ctx}=app();ctx.atob=atob;let reads=0;const frames=[];
 ctx.browser.tabs.executeScript=async(id,target)=>{
  frames.push(target.frameId);
  if(target.file)return [];
  if(target.code.startsWith('AnacoObResource.open'))return [{ok:true,id:'job',status:200,url:'https://player.example/video.mp4'}];
  if(target.code.startsWith('AnacoObResource.read'))return [reads++?{done:true}:{done:false,data:btoa('abc')}];
  return [];
 };
 ctx.fetch=async()=>{throw new Error('background fetch loses the player session');};
 const result=await vm.runInContext('resourceBytes("https://player.example/video.mp4",{tabId:1},37)',ctx);
 assert.equal(result.size,3);assert.ok(frames.length>=4&&frames.every(v=>v===37));
});
test('page CORS failures can fall back to extension permissions and record safe contexts',async()=>{
 const {ctx}=app();ctx.diagnostic={attempts:[]};
 ctx.browser.tabs.executeScript=async(id,target)=>{if(target.file||target.code.startsWith('globalThis.AnacoObLang'))return [];throw new TypeError('CORS denied for secret signed URL');};
 ctx.fetch=async()=>new Response('abc');
 const result=await vm.runInContext('resourceBytes("https://cdn.example/video.mp4?signature=secret",{tabId:1},37,100,diagnostic)',ctx);
 assert.equal(result.size,3);assert.equal(ctx.diagnostic.attempts[0].reason,'page-fetch');
 assert.ok(ctx.diagnostic.attempts.some(v=>v.context==='extension'&&v.status===200));
 assert.ok(!JSON.stringify(ctx.diagnostic).includes('secret'));
});
