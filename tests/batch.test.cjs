const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const I18N=require('./i18n.cjs');
const article=url=>({kind:'article',url,title:url,text:'A complete lesson about permissions, sessions and resources.',contentReady:true,images:[],embeds:[],videos:[],documents:[],warnings:[],requiredOrigins:[]});
function app(initial={}){
  const event=()=>({addListener(){}}),data=structuredClone(initial),created=[],removed=[],calls=[],tabs=new Map(),captures=new Map();let next=10;
  const browser={runtime:{id:'test',getURL:p=>'moz-extension://test/'+p,onMessage:event()},storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,data[k]])),set:async values=>Object.assign(data,structuredClone(values))}},
    permissions:{contains:async()=>true},tabs:{onRemoved:event(),query:async()=>[{id:1,windowId:2,url:'https://course.test/home',cookieStoreId:'firefox-container-3'}],
      create:async props=>{created.push(props);const tab={id:next++,status:'complete',...props};tabs.set(tab.id,tab);return tab;},get:async id=>{if(!tabs.has(id))throw Error('closed');return tabs.get(id);},remove:async id=>{removed.push(id);tabs.delete(id);},executeScript:async()=>[false]},
    webNavigation:{onCompleted:event()},browserAction:{onClicked:event()},commands:{onCommand:event()},menus:{create(){},onClicked:event()}};
  const ctx=vm.createContext({browser,URL,AbortSignal,crypto:require('node:crypto').webcrypto,localStorage:{removeItem(){}},setTimeout:(fn,ms)=>setTimeout(fn,ms===1000?0:ms),clearTimeout});
  vm.runInContext(I18N+['media-source','detection','capture-flow','background','batch-plan','batch'].map(f=>fs.readFileSync(`extension/${f}.js`,'utf8')).join('\n'),ctx);
  const actualScanTab=ctx.scanTab;
  ctx.scanTab=async tab=>article(tab.url);
  ctx.native=async m=>{
    calls.push(m);
    if(m.action==='capture'){const c={...m.capture,id:'capture-'+captures.size};captures.set(c.id,c);return c;}
    if(m.action==='draft'){const c={...captures.get(m.id),draft:{body:'Lesson notes'},status:'draft'};captures.set(c.id,c);return {capture:c,draft:c.draft};}
    if(m.action==='load')return captures.get(m.id);
    return {};
  };
  const invoke=code=>vm.runInContext(code,ctx);
  const settled=async()=>{for(let i=0;i<200;i++){if(!ctx.AnacoObBatch.busy())return;await new Promise(r=>setTimeout(r,2));}throw Error('Queue did not settle');};
  return {ctx,browser,data,created,removed,calls,tabs,captures,invoke,settled,actualScanTab};
}
const start={urls:'https://course.test/one\nhttps://course.test/two',windowId:2,provider:'manual',mode:'auto'};
test('queue uses the login container, runs sequentially without reviews/focus changes and restores the panel',async()=>{
  const a=app({pageContext:{tabId:1,url:'https://course.test/home'},currentCapture:article('https://course.test/home')});
  await a.ctx.AnacoObBatch.start(start);await a.settled();
  assert.equal(a.data.batchQueue.status,'complete');assert.deepEqual(a.data.batchQueue.items.map(i=>i.status),['ready','ready']);
  assert.equal(a.created.length,2);assert.ok(a.created.every(t=>t.active===false&&t.cookieStoreId==='firefox-container-3'));
  assert.equal(a.removed.length,2);assert.equal(a.data.currentCapture.url,'https://course.test/home');
  assert.deepEqual(a.calls.filter(m=>['capture','draft'].includes(m.action)).map(m=>m.action),['capture','draft','capture','draft']);
});
test('a denied player domain records permission needs and does not stop later links',async()=>{
  const a=app();a.ctx.scanTab=async tab=>({...article(tab.url),requiredOrigins:tab.url.endsWith('/one')?['https://player.test/*']:[]});
  await a.ctx.AnacoObBatch.start(start);await a.settled();
  assert.deepEqual(a.data.batchQueue.items.map(i=>i.status),['failed','ready']);
  assert.deepEqual(a.data.batchQueue.items[0].requiredOrigins,['https://player.test/*']);
  a.ctx.scanTab=async tab=>article(tab.url);
  await a.ctx.AnacoObBatch.resume(a.data.batchQueue.items[0].id,4);await a.settled();
  assert.deepEqual(a.data.batchQueue.items.map(i=>i.status),['ready','ready']);assert.equal(a.created.at(-1).windowId,4);
  assert.equal(a.calls.filter(m=>m.action==='draft').length,2);
});
test('a login page never becomes a lesson draft',async()=>{
  const a=app();a.browser.tabs.executeScript=async()=>[true];
  await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/one'});await a.settled();
  assert.equal(a.data.batchQueue.items[0].status,'failed');assert.match(a.data.batchQueue.items[0].error,/iniciar sesión/);
  assert.equal(a.calls.filter(m=>m.action==='draft').length,0);
});
test('pause waits for the current draft and prevents the next link from starting',async()=>{
  const a=app();let release;const native=a.ctx.native;
  a.ctx.native=async m=>{if(m.action==='draft')await new Promise(r=>release=r);return native(m);};
  await a.ctx.AnacoObBatch.start(start);
  while(!release)await new Promise(r=>setTimeout(r,2));
  await a.ctx.AnacoObBatch.pause();assert.equal(a.ctx.AnacoObBatch.busy(),true);
  await assert.rejects(a.ctx.AnacoObBatch.start(start),/trabajo en curso/);
  release();await a.settled();
  assert.equal(a.created.length,1);assert.equal(a.data.batchQueue.status,'paused');
  assert.deepEqual(a.data.batchQueue.items.map(i=>i.status),['ready','pending']);
  a.ctx.native=native;await a.ctx.AnacoObBatch.resume();await a.settled();assert.equal(a.created.length,2);
});
test('retry after a draft error reuses its extracted capture',async()=>{
  const a=app(),native=a.ctx.native;a.ctx.native=async m=>{if(m.action==='draft')throw Error('model unavailable');return native(m);};
  await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/one'});await a.settled();
  assert.equal(a.data.batchQueue.items[0].captureId,'capture-0');
  a.ctx.native=native;await a.ctx.AnacoObBatch.resume(a.data.batchQueue.items[0].id);await a.settled();
  assert.equal(a.created.length,1);assert.equal(a.data.batchQueue.items[0].status,'ready');
});
test('browser restart pauses unfinished entries and forgets previous session tab IDs',async()=>{
  const a=app({batchQueue:{status:'running',items:[{id:'a',url:start.urls.split('\n')[0],tabId:99,status:'running'},{id:'b',status:'ready',captureId:'existing'}]}});
  await new Promise(r=>setImmediate(r));
  assert.equal(a.data.batchQueue.status,'paused');assert.equal(a.data.batchQueue.items[0].status,'pending');
  assert.equal(a.data.batchQueue.items[0].tabId,undefined);assert.equal(a.created.length,0);
});
test('batch URL validation rejects unsafe protocols and credentials, and deduplicates links',()=>{
  const a=app(),plan=a.ctx.AnacoObBatchPlan;
  assert.deepEqual(Array.from(plan.urls('https://course.test/a\nhttps://course.test/a')),['https://course.test/a']);
  for(const url of ['javascript:alert(1)','file:///tmp/a','https://user:pass@course.test/a','no-url'])assert.throws(()=>plan.urls(url),/no válido/);
  assert.throws(()=>plan.urls(''),/100/);
});
test('batch auto chooses lesson media over intro text and rejects ambiguous resources',()=>{
  const a=app(),plan=a.ctx.AnacoObBatchPlan,c={...article('https://course.test/one'),videos:[{url:'https://cdn.test/one.mp4',frameId:12,tracks:[]}]};
  const result=plan.plan(c);assert.equal(result.request.kind,'video');assert.equal(result.request.frameId,12);
  assert.equal(plan.plan({...c,documents:[{url:'https://cdn.test/one.pdf',scope:'navigation'}]}).request.kind,'video');
  assert.throws(()=>plan.plan({...c,videos:[...c.videos,{url:'https://cdn.test/two.mp4'}]}),/varios recursos/);
  assert.equal(plan.plan(c,'note').kind,'note');
});

const lesson=url=>({...article(url),linkLauncher:true,documents:[{url:'https://course.test/handbook.pdf',title:'Student handbook',scope:'navigation',embedded:false}],videos:[{url:'https://cdn.test/lesson.mp4',tracks:[],frameId:17}]});
test('auto never selects the site handbook on a Moodle URL activity, even before a player appears',()=>{
  const a=app(),plan=a.ctx.AnacoObBatchPlan;
  assert.throws(()=>plan.plan({...lesson('https://course.test/mod/url/view.php?id=1'),videos:[]}),/contenido solicitado/);
  assert.equal(plan.plan({...lesson('https://course.test/lesson'),linkLauncher:false,videos:[]}).kind,'note');
  assert.throws(()=>plan.plan({...lesson('https://course.test/lesson'),videos:[{url:'blob:pending',extractable:false}]}),/contenido solicitado/);
  assert.equal(plan.plan(lesson('https://course.test/lesson')).request.kind,'video');
});
test('batch waits for late lesson media instead of extracting the earlier PDF',async()=>{
  const a=app();let scans=0;const extracted=[];
  a.ctx.scanTab=async tab=>{scans++;return {...lesson(tab.url),videos:scans<4?[]:lesson(tab.url).videos};};
  a.ctx.importResource=async (request,c)=>{extracted.push(request);const saved={...c,id:'video',kind:'video',text:'Actual video transcript',images:[]};a.captures.set(saved.id,saved);return saved;};
  await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/mod/url/view.php?id=1'});await a.settled();
  assert.ok(scans>=5);assert.equal(extracted.length,1);assert.equal(extracted[0].kind,'video');assert.equal(extracted[0].frameId,17);
  assert.equal(a.data.batchQueue.items[0].status,'ready');
});
test('explicit video mode waits for video despite readable page text',async()=>{
  const a=app();let scans=0;
  a.ctx.scanTab=async tab=>++scans<4?article(tab.url):lesson(tab.url);
  a.ctx.importResource=async (request,c)=>{const saved={...c,id:'video',images:[]};a.captures.set(saved.id,saved);return saved;};
  await a.ctx.AnacoObBatch.start({...start,mode:'video',urls:'https://course.test/one'});await a.settled();
  assert.ok(scans>=5);assert.equal(a.data.batchQueue.items[0].status,'ready');
});
test('reprocess as video replaces wrong capture references without deleting drafts or saved notes',async()=>{
  const a=app({batchQueue:{status:'paused',windowId:2,options:{mode:'auto',provider:'manual'},items:[{id:'a',url:'https://course.test/one',captureId:'wrong-pdf',status:'ready'},{id:'b',url:'https://course.test/saved',captureId:'saved-note',status:'saved'}]}});
  a.ctx.scanTab=async tab=>lesson(tab.url);
  a.ctx.importResource=async (request,c)=>{const saved={...c,id:'correct-video',images:[]};a.captures.set(saved.id,saved);return saved;};
  await a.ctx.AnacoObBatch.restartVideos(2);await a.settled();
  const [fixed,saved]=a.data.batchQueue.items;
  assert.equal(fixed.captureId,'correct-video');assert.deepEqual(fixed.previousCaptureIds,['wrong-pdf']);
  assert.equal(saved.captureId,'saved-note');assert.equal(saved.status,'saved');assert.equal(a.created.length,1);
  assert.ok(!a.calls.some(m=>m.action==='discard'||m.id==='wrong-pdf'));
});
test('Moodle launch links are followed in the same inactive tab',async()=>{
  const a=app();const navigations=[];
  a.browser.tabs.update=async (id,props)=>{navigations.push(props);Object.assign(a.tabs.get(id),props);return a.tabs.get(id);};
  a.ctx.scanTab=async tab=>tab.url.endsWith('/launch')?{...article(tab.url),linkLauncher:true,launchLinks:['https://course.test/player'],documents:lesson(tab.url).documents}:lesson(tab.url);
  a.ctx.importResource=async (request,c)=>{const saved={...c,id:'video',images:[]};a.captures.set(saved.id,saved);return saved;};
  await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/launch'});await a.settled();
  assert.equal(navigations.length,1);assert.equal(navigations[0].url,'https://course.test/player');assert.equal(navigations[0].active,undefined);
  assert.equal(a.data.batchQueue.items[0].status,'ready');
});

test('Drive permission recovery excludes feedback and includes the download redirect hosts',()=>{
  const a=app(),origins=a.ctx.AnacoObBatchPlan.permissionOrigins(['https://feedback-pa.clients6.google.com/*','https://drive.google.com/file/d/lesson/view','https://course.test/lesson']);
  assert.deepEqual(Array.from(origins),['https://drive.google.com/*','https://drive.usercontent.google.com/*','https://*.googleusercontent.com/*','https://course.test/*']);
});
test('retry all failed links preserves ready drafts and restarts every failed entry',async()=>{
  const a=app({batchQueue:{id:'retry',status:'complete',windowId:2,options:{mode:'auto',provider:'manual'},items:[{id:'a',url:'https://course.test/one',status:'failed'},{id:'b',url:'https://course.test/two',status:'failed'},{id:'c',url:'https://course.test/ready',status:'ready',captureId:'kept'}]}});
  await a.ctx.AnacoObBatch.retryFailed(2);await a.settled();
  assert.equal(a.created.length,2);assert.ok(a.data.batchQueue.items.every(i=>i.status==='ready'));
  assert.equal(a.data.batchQueue.items[2].captureId,'kept');
});

test('granting Drive access lets the retry finish without requesting Google feedback',async()=>{
  const a=app(),allowed=new Set(['https://course.test/*']);
  a.ctx.scanTab=a.actualScanTab;a.ctx.AnacoObEmbeds={embedFrame:()=>false};
  a.browser.permissions.contains=async ({origins=[]})=>origins.every(v=>allowed.has(v));
  a.browser.webNavigation.getAllFrames=async()=>[{frameId:0,url:'https://course.test/one'},{frameId:4,url:'https://drive.google.com/file/d/lesson/preview'},{frameId:99,url:'https://feedback-pa.clients6.google.com/static/feedback.html'}];
  a.ctx.readFrame=async (id,frameId)=>{
    if(frameId===99)throw Error('Feedback has no permission and must never be read');
    if(frameId===4&&!allowed.has('https://drive.google.com/*'))throw Error('Missing host permission');
    return {...article('https://course.test/one'),frameId,videos:[{url:'https://drive.google.com/file/d/lesson/preview',download:'https://drive.google.com/uc?id=lesson',tracks:[]}]};
  };
  a.ctx.importResource=async (request,c)=>{const saved={...c,id:'video',kind:'video',images:[]};a.captures.set(saved.id,saved);return saved;};
  await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/one'});await a.settled();
  const failure=a.data.batchQueue.items[0];assert.equal(failure.status,'failed');assert.match(failure.error,/drive.google.com/);
  assert.ok(!failure.requiredOrigins.some(v=>v.includes('feedback')));
  for(const origin of failure.requiredOrigins)allowed.add(origin);
  await a.ctx.AnacoObBatch.retryFailed(2);await a.settled();
  assert.equal(a.data.batchQueue.items[0].status,'ready');assert.equal(a.data.batchQueue.items[0].captureId,'video');
});

test('a readable Drive video does not require permission to unrelated account and API frames',async()=>{
 const a=app();
 a.ctx.scanTab=async tab=>({...article(tab.url),videos:[{url:'https://drive.google.com/file/d/lesson/view',download:'https://drive.google.com/uc?id=lesson',tracks:[]}],requiredOrigins:['https://accounts.google.com/*','https://clients6.google.com/*','https://youtube.googleapis.com/*'],detection:{loginPage:true}});
 a.ctx.importResource=async(request,c)=>{const saved={...c,id:'drive-video',kind:'video',images:[]};a.captures.set(saved.id,saved);return saved;};
 await a.ctx.AnacoObBatch.start({...start,urls:'https://drive.google.com/file/d/lesson/view',mode:'video'});await a.settled();
 assert.equal(a.data.batchQueue.items[0].status,'ready');assert.equal(a.data.batchQueue.items[0].captureId,'drive-video');
});
test('different Drive view URLs for one file do not count as ambiguous lesson resources',()=>{
 const a=app(),c={...article('https://drive.google.com/file/d/lesson/view'),videos:[{url:'https://drive.google.com/file/d/lesson/preview',download:'https://drive.google.com/uc?id=lesson',tracks:[]},{url:'https://drive.google.com/file/d/lesson/view',download:'https://drive.google.com/uc?id=lesson',tracks:[]}]};
 const result=a.ctx.AnacoObBatchPlan.plan(c,'video');assert.equal(result.request.kind,'video');
});

test('removing failed links and clearing the queue never deletes staged or saved notes',async()=>{
 const a=app({batchQueue:{id:'edit',status:'complete',items:[{id:'saved',status:'saved',captureId:'saved-note'},{id:'bad',status:'failed',captureId:'pending-draft'}]}});
 await a.ctx.AnacoObBatch.remove('bad');assert.equal(a.data.batchQueue.items.length,1);assert.equal(a.data.batchQueue.items[0].id,'saved');
 await a.ctx.AnacoObBatch.clear();assert.equal(a.data.batchQueue,null);assert.equal(a.calls.length,0);
 await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/new'});await a.settled();assert.equal(a.data.batchQueue.items.length,1);assert.equal(a.data.batchQueue.items[0].status,'ready');
});
test('pending items removed during a running draft are not processed by the existing iterator',async()=>{
 const a=app();let release;const native=a.ctx.native;
 a.ctx.native=async m=>{if(m.action==='draft')await new Promise(r=>release=r);return native(m);};
 await a.ctx.AnacoObBatch.start(start);while(!release)await new Promise(r=>setTimeout(r,2));
 const [current,pending]=a.data.batchQueue.items;
 await assert.rejects(a.ctx.AnacoObBatch.remove(current.id),/actual/);
 await assert.rejects(a.ctx.AnacoObBatch.clear(),/actual/);
 await a.ctx.AnacoObBatch.remove(pending.id);release();await a.settled();
 assert.equal(a.created.length,1);assert.equal(a.data.batchQueue.items.length,1);assert.equal(a.data.batchQueue.items[0].status,'ready');
});
test('bulk removal targets failed entries and keeps ready and pending links',async()=>{
 const a=app({batchQueue:{id:'edit',status:'paused',items:[{id:'bad',status:'failed'},{id:'ready',status:'ready',captureId:'keep'},{id:'todo',status:'pending'}]}});
 await a.ctx.AnacoObBatch.clear(true);assert.deepEqual(a.data.batchQueue.items.map(i=>i.id),['ready','todo']);assert.equal(a.data.batchQueue.status,'paused');assert.equal(a.calls.length,0);
});

test('saving queue notes advances in the same review tab and returns to the queue after the last',async()=>{
 const a=app({batchQueue:{id:'review-list',status:'complete',items:[{id:'a',status:'ready',captureId:'first'},{id:'b',status:'failed'},{id:'c',status:'ready',captureId:'second'}]}}),updates=[],native=a.ctx.native;
 for(const id of ['first','second'])a.captures.set(id,{id,status:'draft',draft:{},url:'https://course.test/'+id});
 a.browser.tabs.update=async(id,value)=>{updates.push({id,...value});return {id,...value};};
 a.ctx.native=async m=>{if(m.action==='save'){a.captures.get(m.id).status='saved';return {relative:m.id+'.md'};}return native(m);};
 a.ctx.request={id:'first',decision:'save',fields:{}};a.ctx.sender={url:'moz-extension://test/review.html?capture=first',tab:{id:41,windowId:2}};
 await a.invoke('finishReview(request,sender)');
 assert.equal(updates[0].id,41);assert.equal(updates[0].url,'moz-extension://test/review.html?capture=second');
 assert.equal(a.data.batchQueue.items[0].status,'saved');assert.ok(a.data.batchQueue.items[0].reviewedAt);
 a.ctx.request.id='second';a.ctx.sender.url='moz-extension://test/review.html?capture=second';
 await a.invoke('finishReview(request,sender)');
 assert.equal(updates[1].url,'moz-extension://test/panel.html');assert.equal(a.created.length,0);
 assert.equal(a.data.batchQueue.items[2].status,'saved');assert.equal(Object.keys(a.data.reviews).length,0);
});
test('a failed save never advances or marks a queued note as reviewed',async()=>{
 const a=app({batchQueue:{id:'queue',status:'complete',items:[{id:'a',status:'ready',captureId:'first'}]}}),updates=[],native=a.ctx.native;
 a.captures.set('first',{id:'first',status:'draft',draft:{},url:'https://course.test/one'});
 a.ctx.native=async m=>{if(m.action==='save')throw Error('write failed');return native(m);};
 a.browser.tabs.update=async(...args)=>updates.push(args);
 a.ctx.request={id:'first',decision:'save',fields:{}};a.ctx.sender={url:'moz-extension://test/review.html?capture=first',tab:{id:41,windowId:2}};
 await assert.rejects(a.invoke('finishReview(request,sender)'),/write failed/);
 assert.equal(a.data.batchQueue.items[0].status,'ready');assert.equal(updates.length,0);
});
test('returning from a queue review keeps the draft pending and opens the queue, never the video',async()=>{
 const a=app({batchQueue:{id:'queue',status:'complete',items:[{id:'a',status:'ready',captureId:'first'}]}}),updates=[];
 a.captures.set('first',{id:'first',status:'draft',draft:{},url:'https://course.test/one'});
 a.browser.tabs.update=async(id,value)=>{updates.push(value);return {id,...value};};
 a.ctx.request={id:'first',decision:'back',fields:{}};a.ctx.sender={url:'moz-extension://test/review.html?capture=first',tab:{id:41,windowId:2}};
 await a.invoke('finishReview(request,sender)');assert.equal(a.data.batchQueue.items[0].status,'ready');
 assert.equal(updates[0].url,'moz-extension://test/panel.html');assert.ok(!a.calls.some(m=>m.action==='save'));
});

test('links imported from a course keep that course container when another tab is active',async()=>{
 const a=app();await a.ctx.AnacoObBatch.start({...start,urls:'https://course.test/one',cookieStoreId:'firefox-container-9'});await a.settled();
 assert.equal(a.created[0].cookieStoreId,'firefox-container-9');assert.equal(a.data.batchQueue.cookieStoreId,'firefox-container-9');
});
