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
 vm.runInContext(I18N+fs.readFileSync('extension/media-source.js','utf8')+fs.readFileSync('extension/detection.js','utf8')+fs.readFileSync('extension/background.js','utf8'),ctx);
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

test('dismissing a pending capture clears its editor, review and tab cache, preserving unrelated captures',async()=>{
 const {ctx,data}=app(),removed=[],editors=[],calls=[];
 const c={...capture(1),id:'pending-1',source:{tabId:1,url:tab(1).url}};
 ctx.c=c;ctx.other={...capture(2),id:'pending-2',source:{tabId:2,url:tab(2).url}};
 ctx.localStorage={removeItem:key=>editors.push(key)};
 ctx.browser.tabs.get=async id=>({id,url:'moz-extension://test/review.html?capture=pending-1'});
 ctx.browser.tabs.remove=async id=>removed.push(id);
 ctx.native=async m=>{calls.push(m);return {discarded:true,discarded_jobs:['draft-job']};};
 await vm.runInContext('publishCapture(c);publishCapture(other)',ctx);
 Object.assign(data,{currentCapture:c,draftResult:{draft:{}},editorFields:{body:'draft'},sources:{'pending-1':{},'pending-2':{}},reviews:{'pending-1':23,'pending-2':24},workSources:{'draft-job':{},'other-job':{}}});
 await vm.runInContext('discardPending({id:"pending-1"})',ctx);
 assert.equal(calls[0].action,'discard');assert.equal(data.currentCapture,null);assert.equal(data.draftResult,null);assert.equal(data.editorFields,null);
 assert.deepEqual(removed,[23]);assert.deepEqual(editors,['editor:pending-1']);
 assert.deepEqual(Object.keys(data.sources),['pending-2']);assert.deepEqual(Object.keys(data.reviews),['pending-2']);assert.deepEqual(Object.keys(data.workSources),['other-job']);
 assert.equal(vm.runInContext('tabCaptures.has("1:https://course.example/page-1")',ctx),false);
 assert.equal(vm.runInContext('tabCaptures.get("2:https://course.example/page-2").currentCapture.id',ctx),'pending-2');
});

test('dismissing a failed job preserves the current capture and blocks competing work until done',async()=>{
 const {ctx,data}=app();let finish;const calls=[];ctx.owner=capture(1);data.currentCapture=ctx.owner;
 data.workSources={'failed-job':{},'other-job':{}};
 ctx.native=m=>{calls.push(m);return new Promise(resolve=>{finish=resolve;});};
 const dismiss=vm.runInContext('discardPending({job:"failed-job"})',ctx);
 await assert.rejects(vm.runInContext('beginWork(owner,"Preparing")',ctx),/en curso/);
 await assert.rejects(vm.runInContext('discardPending({job:"other-job"})',ctx),/en curso/);
 finish({discarded:true});await dismiss;
 assert.equal(calls[0].action,'discard_job');assert.equal(data.currentCapture,ctx.owner);assert.deepEqual(Object.keys(data.workSources),['other-job']);
 ctx.native=async()=>{throw new Error('native failed');};
 await assert.rejects(vm.runInContext('discardPending({job:"other-job"})',ctx),/native failed/);
 assert.deepEqual(Object.keys(data.workSources),['other-job']);assert.equal(vm.runInContext('pendingDiscard',ctx),false);
});

test('a pending capture cannot be dismissed while generation is active',async()=>{
 const {ctx,data}=app();ctx.owner=capture(1);let calls=0;
 await vm.runInContext('beginWork(owner,"Preparing")',ctx);
 ctx.native=async()=>{calls++;};
 await assert.rejects(vm.runInContext('discardPending({id:"pending-1"})',ctx),/en curso/);
 assert.equal(calls,0);assert.equal(data.operation,'Preparing');
});

test('unavailable subtitle tracks fall back to the already authorized audio resource',async()=>{
 const {ctx,data}=app();ctx.btoa=btoa;
 data.currentCapture={...capture(1),source:{tabId:1,url:tab(1).url,windowId:1}};
 data.pageContext={tabId:1,url:tab(1).url,status:'ready'};
 const calls=[];
 ctx.fetch=async url=>url.endsWith('.vtt')?new Response('Forbidden',{status:403}):new Response(new Uint8Array([1,2,3]));
 ctx.native=async message=>{
  calls.push(message);
  if(message.action==='source_context')return {id:message.id,kind:'video',url:tab(1).url,images:[],warnings:[],text:'Recovered transcript',source_context:message.source_context};
  if(message.action==='upload_begin')return {upload:'test-upload'};
  if(message.action==='upload_finish')return {id:'video-1',kind:'video',url:tab(1).url,images:[],warnings:[],text:'Recovered transcript'};
  return {};
 };
 ctx.request={kind:'subtitle-url',url:'https://media.example/missing.vtt',pageUrl:tab(1).url,fallback:{kind:'video',url:'https://media.example/video.mp4',name:'video.mp4'}};
 await vm.runInContext('importResource(request)',ctx);
 assert.equal(data.currentCapture.id,'video-1');
 assert.equal(data.currentCapture.source.tabId,1);
 assert.ok(calls.some(m=>m.action==='upload_finish'));
 assert.ok(calls.some(m=>m.action==='source_context'&&m.id==='video-1'&&m.source_context.page_url===tab(1).url));
 assert.ok(!calls.some(m=>m.action==='subtitles'));
 assert.equal(data.operation,'');
});

test('resource extraction rejects a click belonging to an older tab',async()=>{
 const {ctx,data}=app();data.currentCapture={token:'new-page'};
 ctx.request={kind:'pdf',url:'https://course.example/old.pdf',token:'old-page'};
 await assert.rejects(vm.runInContext('importResource(request)',ctx),/pestaña cambió/);
 assert.equal(data.operation,undefined);
});

test('an unextracted platform video cannot prepare a note from page metadata',async()=>{
 const {ctx,data}=app();
 data.currentCapture={...capture(1),kind:'video',contentReady:true};
 await assert.rejects(vm.runInContext('prepare({})',ctx),/Primero extrae/);
 assert.equal(data.operation,undefined);
});

test('native progress retains counts, clears legacy phase data and cannot overwrite cancellation',async()=>{
 const {ctx,data}=app();let receive;const sent=[];
 ctx.browser.runtime.connectNative=()=>({onMessage:{addListener(fn){receive=fn;}},onDisconnect:{addListener(){}},postMessage(m){sent.push(m);}});
 ctx.browser.runtime.sendNativeMessage=async()=>({ok:true});
 ctx.owner={...capture(1),source:{tabId:1,url:tab(1).url}};
 await new Promise(resolve=>setImmediate(resolve));
 await vm.runInContext('beginWork(owner,"Preparing")',ctx);
 const pending=vm.runInContext('native({action:"draft"})',ctx);
 const requestId=sent[0].requestId;
 receive({requestId,progress:{stage:'reading',unit:'stretches',completed:1,total:7,message:'Reading 2/7'}});
 assert.equal(data.operationProgress.completed,1);assert.equal(data.operationProgress.total,7);
 receive({requestId,progress:'Legacy synthesis'});
 assert.equal(data.operation,'Legacy synthesis');assert.equal(data.operationProgress,null);
 await vm.runInContext('cancelWork()',ctx);
 const operation=data.operation;
 receive({requestId,progress:{stage:'reading',unit:'stretches',completed:2,total:7,message:'Late reading'}});
 assert.equal(data.operation,operation);assert.equal(data.operationProgress.stage,'cancel');
 const rejected=assert.rejects(pending,/cancelled/);receive({requestId,ok:false,error:'cancelled'});await rejected;
});

test('cancelling a subtitle request does not start its audio fallback',async()=>{
 const {ctx,data}=app();let fail;const calls=[];
 ctx.browser.runtime.sendNativeMessage=async()=>({ok:true});
 ctx.native=async message=>{calls.push(message.action);return {};};
 ctx.subtitleText=()=>new Promise((resolve,reject)=>{fail=reject;});
 data.currentCapture={...capture(1),source:{tabId:1,url:tab(1).url}};
 ctx.request={kind:'subtitle-url',url:'https://media.example/captions.vtt',fallback:{kind:'video-platform',url:'https://www.youtube.com/watch?v=abcdefghijk'}};
 const pending=vm.runInContext('importResource(request)',ctx);
 const rejected=assert.rejects(pending,/cancelado/i);
 await new Promise(resolve=>setImmediate(resolve));
 await vm.runInContext('cancelWork()',ctx);fail(new Error('request stopped'));
 await rejected;
 assert.ok(!calls.includes('video_url'));assert.equal(data.operation,'');
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

test('panel stays attached to its chosen tab when another tab becomes active',async()=>{
 const {ctx,data}=app();ctx.a=tab(1);ctx.b=tab(2);
 ctx.browser.tabs.get=async id=>tab(id);ctx.browser.tabs.query=async()=>[tab(2)];
 ctx.scanTab=async value=>capture(value.id);
 await vm.runInContext('bindPanel(a);detectActive({windowId:1,tabId:2})',ctx);
 assert.equal(data.currentCapture.source.tabId,1);
 await vm.runInContext('detectActive({windowId:1,useActive:true})',ctx);
 assert.equal(data.currentCapture.source.tabId,2);
});
test('two windows show their own pinned capture, including when the global capture belongs to the other',async()=>{
 const {ctx}=app();ctx.a=tab(1);ctx.b={...tab(2),windowId:2};ctx.scanTab=async value=>capture(value.id);
 await vm.runInContext('bindPanel(a);capture(a)',ctx);await vm.runInContext('bindPanel(b);capture(b)',ctx);
 const one=await vm.runInContext('panelCapture(1)',ctx),two=await vm.runInContext('panelCapture(2)',ctx);
 assert.equal(one.currentCapture.source.tabId,1);assert.equal(two.currentCapture.source.tabId,2);
 assert.equal(vm.runInContext('captureForToken(undefined)',ctx),null);
});

test('Google feedback frames cannot block detection of the actual Drive player',async()=>{
 const {ctx}=app();
 vm.runInContext(fs.readFileSync('extension/media-source.js','utf8'),ctx);
 ctx.AnacoObEmbeds={embedFrame:()=>false};
 const frames=[];
 ctx.browser.webNavigation.getAllFrames=async()=>[{frameId:0,url:tab(1).url},{frameId:4,url:'https://drive.google.com/file/d/lesson/preview'},{frameId:99,url:'https://feedback-pa.clients6.google.com/static/feedback.html'}];
 ctx.readFrame=async(id,frameId)=>{frames.push(frameId);if(frameId===99)throw Error('Missing host permission');return {...capture(1),frameId,videos:frameId===4?[{url:'https://drive.google.com/file/d/lesson/preview',download:'https://drive.google.com/uc?id=lesson',tracks:[]}]:[]};};
 ctx.a=tab(1);const c=await vm.runInContext('scanTab(a)',ctx);
 assert.deepEqual(frames,[0,4]);assert.equal(c.requiredOrigins.length,0);assert.equal(c.videos.length,1);
});

test('a recognized Drive confirmation is followed once and real media is returned',async()=>{
 const {ctx}=app(),requests=[];ctx.requestURL='https://drive.google.com/uc?id=lesson';
 ctx.AnacoObDriveDownload={publicRequest:()=>({url:'https://drive.usercontent.google.com/download?id=lesson&confirm=t',method:'GET'}),confirmation:async(response,url)=>{assert.equal(url,ctx.requestURL);await response.body.cancel();return {url:'https://drive.usercontent.google.com/download?id=lesson&confirm=t',method:'GET'};}};
 ctx.fetch=async(url)=>{requests.push(url);return requests.length===1?new Response('<form>Drive confirmation</form>',{headers:{'content-type':'text/html'}}):new Response('real media',{headers:{'content-type':'video/mp4'}});};
 const result=await vm.runInContext('resourceBytes(requestURL,null,0,1000000000)',ctx);
 assert.equal(result.size,10);assert.equal(requests.length,2);assert.match(requests[1],/drive.usercontent.google.com/);
});
test('Drive confirmation cannot loop or turn a real login page into a download',async()=>{
 const {ctx}=app();let calls=0;
 ctx.AnacoObDriveDownload={publicRequest:()=>({url:'https://drive.usercontent.google.com/download?id=lesson&confirm=t',method:'GET'}),confirmation:async(response)=>{await response.body.cancel();return {url:'https://drive.usercontent.google.com/download?id=lesson&confirm=t',method:'GET'};}};
 ctx.fetch=async()=>{calls++;return new Response('<html>Login</html>',{headers:{'content-type':'text/html'}});};
 await assert.rejects(vm.runInContext('resourceBytes("https://drive.google.com/uc?id=lesson",null)',ctx),/HTML/);assert.equal(calls,4);
});

test('Drive can fall back to its public download when account cookies keep returning HTML',async()=>{
 const {ctx}=app(),calls=[];
 ctx.AnacoObDriveDownload={confirmation:async response=>{await response.body.cancel();return null;},publicRequest:()=>({url:'https://drive.usercontent.google.com/download?id=lesson&confirm=t',method:'GET'})};
 ctx.fetch=async(url,options)=>{calls.push({url,...options});return options.credentials==='include'?new Response('<html>Account page</html>',{headers:{'content-type':'text/html'}}):new Response('public video',{headers:{'content-type':'video/mp4'}});};
 const result=await vm.runInContext('resourceBytes("https://drive.google.com/uc?id=lesson",null)',ctx);
 assert.equal(result.size,12);assert.deepEqual(calls.map(c=>c.credentials),['include','omit']);
});
test('Drive submits POST confirmation fields only to the validated download target',async()=>{
 const {ctx}=app(),calls=[];
 ctx.AnacoObDriveDownload={confirmation:async response=>{await response.body.cancel();return {url:'https://drive.usercontent.google.com/download?id=lesson&export=download&confirm=t',method:'POST',body:'uuid=test-token',headers:{'Content-Type':'application/x-www-form-urlencoded'}};}};
 ctx.fetch=async(url,options)=>{calls.push({url,...options});return calls.length===1?new Response('<form>Confirm</form>',{headers:{'content-type':'text/html'}}):new Response('media',{headers:{'content-type':'video/mp4'}});};
 const result=await vm.runInContext('resourceBytes("https://drive.google.com/uc?id=lesson",null)',ctx);
 assert.equal(result.size,5);assert.equal(calls[1].method,'POST');assert.equal(calls[1].body,'uuid=test-token');
});
test('resuming a pending capture shows it in the panel that asked for it, even without its source tab',async()=>{
 const {ctx,data}=app();ctx.a=tab(1);ctx.scanTab=async value=>capture(value.id);
 const stored={'pending-2':{...capture(2),id:'pending-2',status:'pending'},'imported-3':{...capture(3),id:'imported-3',status:'pending'}};
 ctx.native=async m=>m.action==='load'?structuredClone(stored[m.id]):{folders:[]};
 data.sources={'pending-2':{tabId:2,url:tab(2).url,windowId:1}};
 await vm.runInContext('bindPanel(a);capture(a)',ctx);
 await vm.runInContext('resumeCapture({id:"pending-2",windowId:1})',ctx);
 let own=await vm.runInContext('panelCapture(1)',ctx);
 assert.equal(own.currentCapture.id,'pending-2');assert.equal(own.panelSource.tabId,2);
 await vm.runInContext('resumeCapture({id:"imported-3",windowId:1})',ctx);
 own=await vm.runInContext('panelCapture(1)',ctx);
 assert.equal(own.currentCapture.id,'imported-3');
});
test('a late status from a review that already left its tab cannot bring the assistant back',async()=>{
 const {ctx,data}=app(),review='moz-extension://test/review.html?capture=c1';
 let current=review;ctx.browser.tabs.get=async id=>({id,url:current});
 ctx.sender={tab:{id:5,windowId:1,active:true},url:review};
 await vm.runInContext('reviewStatus({id:"c1",status:{canSave:true},instance:"i"},sender)',ctx);
 assert.ok(data.reviewSessions.c1);
 current='https://course.example/page-1';await vm.runInContext('clearReviewTab(5)',ctx);
 await vm.runInContext('reviewStatus({id:"c1",status:{canSave:true},instance:"i"},sender)',ctx);
 assert.equal(data.reviewSessions.c1,undefined);
 ctx.browser.tabs.get=async()=>{throw new Error('Invalid tab ID');};
 await vm.runInContext('reviewStatus({id:"c1",status:{canSave:true},instance:"i"},sender)',ctx);
 assert.equal(data.reviewSessions.c1,undefined);
});
test('an automatic detection after binding cannot replace a selection capture still in flight',async()=>{
 const {ctx,data}=app();let release;ctx.a=tab(1);
 ctx.delayed=new Promise(resolve=>{release=resolve;});ctx.article=capture(1);
 vm.runInContext('scanTab=(tab,input)=>input.kind==="quote"?delayed:Promise.resolve({...article})',ctx);
 const quote=vm.runInContext('capture(a,{kind:"quote",selection:"Selected words"})',ctx);
 await new Promise(resolve=>setImmediate(resolve));
 const automatic=vm.runInContext('capture(a,{},{automatic:true,fresh:false})',ctx);
 release({...capture(1),kind:'quote',text:'Selected words'});await quote;await automatic;
 assert.equal(data.currentCapture.kind,'quote');assert.equal(data.currentCapture.text,'Selected words');
});
