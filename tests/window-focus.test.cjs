const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function app(){
 const event=()=>({listeners:[],addListener(fn){this.listeners.push(fn);},emit(value){for(const fn of this.listeners)fn(value);}});
 const data={},created=[],opened=[];let focused={id:1,focused:true},active={id:11,url:'https://course.example/lesson'};
 const browser={runtime:{getURL:p=>'moz-extension://test/'+p,onMessage:event()},windows:{getAll:async()=>[{id:1}],get:async id=>({id}),getLastFocused:async()=>focused,onCreated:event(),onRemoved:event()},tabs:{onRemoved:event(),query:async()=>[active],create:async value=>{created.push(value);return {id:created.length+30,...value};},get:async()=>({url:'about:blank'}),update:async()=>{throw new Error('Unexpected focus change');}},sidebarAction:{open:()=>{opened.push(true);return Promise.resolve();}},storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,data[k]])),set:async values=>Object.assign(data,values)}},permissions:{contains:async()=>true},webNavigation:{onCompleted:event()},browserAction:{onClicked:event()},commands:{onCommand:event()},menus:{create(){},onClicked:event()}};
 const ctx=vm.createContext({browser,URL,setTimeout,clearTimeout,AbortSignal,crypto:require('node:crypto').webcrypto});vm.runInContext(fs.readFileSync('extension/detection.js','utf8')+fs.readFileSync('extension/background.js','utf8'),ctx);
 ctx.native=async()=>({status:'draft',draft:{},url:'https://course.example/lesson'});
 return {ctx,browser,data,created,opened,setFocused:value=>focused=value,setActive:value=>active=value};
}
test('new windows reject the inherited sidebar while explicit opens remain allowed',async()=>{
 const a=app();await vm.runInContext('allowSidebar(1)',a.ctx);
 a.browser.windows.onCreated.emit({id:2});assert.equal(await vm.runInContext('allowSidebar(2)',a.ctx),false);assert.equal(a.opened.length,0);
 await vm.runInContext('openSidebar({windowId:2})',a.ctx);assert.equal(await vm.runInContext('allowSidebar(2)',a.ctx),true);assert.equal(a.opened.length,1);
 assert.equal(await vm.runInContext('allowSidebar(1)',a.ctx),true);
});
test('a sidebar loading before its window event is closed only once',async()=>{
 const a=app();assert.equal(await vm.runInContext('allowSidebar(2)',a.ctx),false);a.browser.windows.onCreated.emit({id:2});assert.equal(await vm.runInContext('allowSidebar(2)',a.ctx),true);
});
test('automatic review stays in the source window without stealing a different window or tab',async()=>{
 const a=app();a.setFocused({id:2,focused:true});a.ctx.source={windowId:1,tabId:11};
 await vm.runInContext('openReview("draft",{automatic:true,source})',a.ctx);assert.equal(a.created[0].windowId,1);assert.equal(a.created[0].active,false);
 a.data.reviews={};a.setFocused({id:1,focused:true});a.setActive({id:12,url:'https://other.example/'});
 await vm.runInContext('openReview("draft",{automatic:true,source})',a.ctx);assert.equal(a.created[1].active,false);
});
test('automatic review opens in front only while the user remains on its source',async()=>{
 const a=app();a.ctx.source={windowId:1,tabId:11};await vm.runInContext('openReview("draft",{automatic:true,source})',a.ctx);assert.equal(a.created[0].active,true);
 a.data.reviews={};a.setFocused({id:1,focused:false});await vm.runInContext('openReview("draft",{automatic:true,source})',a.ctx);assert.equal(a.created[1].active,false);
});
test('review menu state is scoped to its real window and disappears when its tab closes',async()=>{
 const a=app();a.ctx.message={id:'capture',instance:'view-one',status:{title:'Review',notes:[]}};a.ctx.sender={url:'moz-extension://test/review.html?capture=capture',tab:{id:91,windowId:1}};
 await vm.runInContext('reviewStatus(message,sender)',a.ctx);assert.equal(a.data.reviewSessions.capture.windowId,1);
 a.ctx.command={id:'capture',windowId:2,command:'read'};
 await assert.rejects(vm.runInContext('reviewCommand(command)',a.ctx),/esta ventana/);
 await vm.runInContext('clearReviewTab(91)',a.ctx);assert.deepEqual(Object.keys(a.data.reviewSessions),[]);
});
test('review menu messages target only the matching review instance',async()=>{
 const a=app(),sent=[],focused=[];
 a.browser.runtime.sendMessage=async value=>{sent.push(value);return {handled:true};};
 a.browser.tabs.get=async id=>({id,windowId:1,url:'moz-extension://test/review.html?capture=capture'});
 a.browser.tabs.update=async (id,value)=>{focused.push(id);return {id,...value};};
 a.ctx.message={id:'capture',instance:'view-two',status:{title:'Review',notes:[]}};a.ctx.sender={url:'moz-extension://test/review.html?capture=capture',tab:{id:92,windowId:1}};
 await vm.runInContext('reviewStatus(message,sender)',a.ctx);
 a.ctx.command={id:'capture',windowId:1,command:'note',note:'tema-cache'};await vm.runInContext('reviewCommand(command)',a.ctx);
 assert.equal(sent[0].instance,'view-two');assert.equal(sent[0].note,'tema-cache');assert.deepEqual(focused,[92]);
});
