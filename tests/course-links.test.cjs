const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const I18N=require('./i18n.cjs');
function model(extra={}){
 const body={querySelectorAll:()=>[]};
 const ctx=vm.createContext({URL,AbortController,location:new URL('https://awsacademy.instructure.com/courses/42/modules'),document:{title:'Course',body,querySelector:()=>null},...extra});
 vm.runInContext(I18N+fs.readFileSync('extension/course-links.js','utf8'),ctx);return ctx;
}
test('Canvas module hierarchy preserves subheaders, indentation and locked content',()=>{
 const ctx=model();const result=ctx.AnacoObCourseLinks.canvasNodes([{id:1,name:'Module 1',state:'unlocked'},{id:2,name:'Locked',state:'locked'}],{1:[{id:10,type:'SubHeader',title:'Topic',indent:0},{id:11,type:'Page',title:'Lesson',page_url:'lesson',indent:1},{id:12,type:'ExternalUrl',title:'Reference',external_url:'https://example.test/reference',indent:2}],2:[{id:20,type:'Page',page_url:'locked',title:'Locked lesson'}]},'https://awsacademy.instructure.com/courses/42');
 assert.equal(result.find(n=>n.id==='item-11').parentId,'item-10');assert.equal(result.find(n=>n.id==='item-12').parentId,'item-11');
 assert.equal(result.find(n=>n.id==='item-20').locked,true);assert.equal(result.find(n=>n.id==='item-11').url,'https://awsacademy.instructure.com/courses/42/pages/lesson');
});
test('Canvas enumeration follows pagination and loads item pages when the inline list is incomplete',async()=>{
 const requests=[];
 const ctx=model({fetch:async(url,options)=>{
  requests.push({url,options});const u=new URL(url);
  const value=u.pathname.endsWith('/modules')?[{id:1,name:'Module',items_count:2,items:[{id:1,type:'Page',title:'Partial'}]}]:u.searchParams.has('page')?[{id:3,type:'Page',title:'Second',page_url:'second'}]:[{id:2,type:'Page',title:'First',page_url:'first'}];
  return new Response(JSON.stringify(value),{headers:{'content-type':'application/json',...(!u.pathname.endsWith('/modules')&&!u.searchParams.has('page')?{Link:'<https://awsacademy.instructure.com/api/v1/courses/42/modules/1/items?page=2>; rel="next"'}:{})}});
 }});
 const result=await ctx.AnacoObCourseLinks.scan();assert.equal(result.platform,'canvas');assert.equal(result.nodes.filter(n=>n.url).length,2);assert.equal(requests.length,3);assert.ok(requests.every(r=>r.options.credentials==='include'&&!r.options.method));
});
test('links outside the course cannot become pagination requests or recursive tasks',async()=>{
 const requests=[];const ctx=model({fetch:async url=>{requests.push(url);return new Response('[]',{headers:{'content-type':'application/json',Link:'<https://other.test/private>; rel="next"'}});}});
 const result=await ctx.AnacoObCourseLinks.scan();assert.equal(requests.length,1);assert.equal(result.platform,'page');assert.equal(result.warnings.length,1);
 assert.equal(ctx.AnacoObCourseLinks.crawlable('https://awsacademy.instructure.com/courses/99/pages/other','https://awsacademy.instructure.com/courses/42/modules'),false);
 assert.equal(ctx.AnacoObCourseLinks.url('javascript:alert(1)'),null);assert.equal(ctx.AnacoObCourseLinks.url('https://school.test/logout.php'),null);assert.equal(ctx.AnacoObCourseLinks.url(undefined,'https://school.test/'),null);
});

function worker(initial={}){
 const data=structuredClone(initial),tabs=new Map(),opened=[],closed=[];let next=20;
 const browser={storage:{local:{get:async key=>({[key]:data[key]}),set:async value=>Object.assign(data,structuredClone(value))}},permissions:{contains:async()=>true},tabs:{query:async()=>[{id:9,windowId:1,cookieStoreId:'firefox-container-3'}],get:async id=>tabs.get(id),create:async props=>{const tab={...props,id:next++,status:'complete'};tabs.set(tab.id,tab);opened.push(props);return tab;},remove:async id=>{closed.push(id);tabs.delete(id);},executeScript:async(id,opts)=>opts.code?.startsWith('AnacoObCourseLinks.scan')?[await scan(tabs.get(id).url)]:[]}};
 let scan=async url=>({title:'Course',nodes:[],warnings:[],url});
 const ctx=model({browser,crypto:require('node:crypto').webcrypto,injectI18n:async()=>{},setTimeout:(fn,ms)=>setTimeout(fn,ms===250?0:ms),clearTimeout});
 vm.runInContext(fs.readFileSync('extension/detection.js','utf8')+fs.readFileSync('extension/course-discovery.js','utf8'),ctx);
 const settled=async()=>{for(let i=0;i<300;i++){if(data.courseDiscovery?.status!=='running')return;await new Promise(r=>setTimeout(r,2));}throw Error('Still exploring');};
 return {ctx,browser,data,opened,closed,settled,scan:fn=>scan=fn};
}
test('course exploration keeps its session, traverses nested pages once, and selection excludes locked links',async()=>{
 const a=worker(),root='https://school.test/course/index.html',child='https://school.test/course/module.html';
 a.scan(async url=>({title:'Course',url,nodes:url===root?[{id:'m',kind:'module',title:'Module'},{id:'l',parentId:'m',kind:'page',title:'Lesson',url:child,explore:true},{id:'locked',title:'Locked',url:'https://school.test/course/locked.html',locked:true}]:[{id:'back',url:root,title:'Index',explore:true},{id:'video',url:'https://media.test/video.mp4',title:'Video',kind:'video'}]}));
 await a.ctx.AnacoObCourses.start({url:root,windowId:1,depth:3});await a.settled();
 assert.equal(a.opened.length,2);assert.ok(a.opened.every(t=>t.active===false&&t.cookieStoreId==='firefox-container-3'));assert.equal(a.closed.length,2);
 const nodes=a.data.courseDiscovery.nodes;await a.ctx.AnacoObCourses.select(nodes.map(n=>n.id));assert.ok(a.data.courseDiscovery.selected.length>0);assert.ok(!a.data.courseDiscovery.selected.includes(nodes.find(n=>n.locked).id));
});
test('a denied course domain remains available to resume instead of disappearing',async()=>{
 const a=worker();let allowed=true;a.browser.permissions.contains=async()=>allowed;
 // The initial grant is present, then disappears before the first page read.
 a.browser.tabs.query=async()=>{allowed=false;return [{id:9,windowId:1}];};
 await a.ctx.AnacoObCourses.start({url:'https://school.test/course/',windowId:1});await a.settled();
 assert.equal(a.data.courseDiscovery.blocked[0].origin,'https://school.test/*');
 allowed=true;await a.ctx.AnacoObCourses.resume(1);await a.settled();assert.equal(a.data.courseDiscovery.blocked.length,0);assert.equal(a.data.courseDiscovery.count,1);
});

test('stopping exploration preserves its pending page and can resume it',async()=>{
 const a=worker();let release;
 a.scan(()=>new Promise(r=>release=r));
 await a.ctx.AnacoObCourses.start({url:'https://school.test/course/',windowId:1});
 while(!release)await new Promise(r=>setTimeout(r,2));
 await a.ctx.AnacoObCourses.stop();release({title:'Course',nodes:[]});await a.settled();
 assert.equal(a.data.courseDiscovery.status,'paused');assert.equal(a.data.courseDiscovery.todo.length,1);
 a.scan(async()=>({title:'Course',nodes:[]}));await a.ctx.AnacoObCourses.resume(1);await a.settled();
 assert.equal(a.data.courseDiscovery.status,'complete');assert.equal(a.data.courseDiscovery.count,1);
});
test('browser restart retains results and restores the page that was being explored',async()=>{
 const a=worker({courseDiscovery:{id:'old',status:'running',root:'https://school.test/course/',todo:[],activeTask:{url:'https://school.test/course/lesson',parentId:'root',depth:1},nodes:[{id:'root',kind:'module'}],selected:[],blocked:[],warnings:[],visited:[],count:0}});
 await new Promise(r=>setImmediate(r));assert.equal(a.data.courseDiscovery.status,'paused');assert.equal(a.data.courseDiscovery.todo.length,1);assert.equal(a.opened.length,0);
});

test('exploring a specific Canvas page does not silently enumerate the entire course',async()=>{
 let requests=0;const ctx=model({location:new URL('https://awsacademy.instructure.com/courses/42/pages/specific'),fetch:async()=>{requests++;throw Error('Unexpected catalog read');}});
 const result=await ctx.AnacoObCourseLinks.scan();assert.equal(result.platform,'page');assert.equal(requests,0);
});

test('an initial complete about:blank tab is not mistaken for a denied course domain',async()=>{
 const a=worker(),get=a.browser.tabs.get;let blank=true;
 a.browser.tabs.get=async id=>{const tab=await get(id);if(blank){blank=false;return {...tab,url:'about:blank'};}return tab;};
 await a.ctx.AnacoObCourses.start({url:'https://school.test/course/',windowId:1});await a.settled();
 assert.equal(a.data.courseDiscovery.blocked.length,0);assert.equal(a.data.courseDiscovery.count,1);
});
