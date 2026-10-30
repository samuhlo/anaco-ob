const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const I18N=require('./i18n.cjs');
function app(){
 const data={autoUpdateCheck:false},calls=[],opened=[];
 const ctx=vm.createContext({AbortSignal,Date,console,workClaim:null,requests:new Map(),port:null,
 browser:{storage:{local:{get:async()=>data,set:async v=>Object.assign(data,v)}},runtime:{getManifest:()=>({version:'1.3.2'})},alarms:{create(){},onAlarm:{addListener(){}}},tabs:{create:async v=>opened.push(v)}},
 fetch:async(url,opts)=>{calls.push({url,opts});return {ok:true,json:async()=>url.includes('github')?{tag_name:'v1.4.0'}:{guid:'anaco-ob@samuhlo',current_version:{version:'1.3.3',file:{status:'public'}}}};},
 native:async message=>message.action==='install_update'?{version:'1.4.0'}:{version:'1.3.2',can_update:true}});
 vm.runInContext(I18N+fs.readFileSync('extension/update-manager.js','utf8'),ctx);
 return {ctx,api:ctx.AnacoObUpdates,data,calls,opened};
}
test('numeric version comparison rejects prereleases and malformed versions',()=>{
 const {api}=app();assert.equal(api.newer('1.10.0','1.9.9'),true);assert.equal(api.newer('1.3.2','1.3.2'),false);
 for(const v of ['v1.4.0','1.4.0-beta.1','garbage','https://evil.test'])assert.equal(api.newer(v,'1.3.2'),false);
 assert.equal(api.newer('1.2.0','1.3.2'),false);
});
test('manual checks use both official channels without cookies; automatic checks honor opt-out and cache',async()=>{
 const a=app();await a.api.check();assert.equal(a.calls.length,0);
 let result=await a.api.check(true);assert.equal(result.extension.available,true);assert.equal(result.service.available,true);
 assert.ok(a.calls.every(v=>v.opts.credentials==='omit'&&v.opts.redirect==='error'));
 a.data.autoUpdateCheck=true;await a.api.check();assert.equal(a.calls.length,2);
 await a.api.check(true);assert.equal(a.calls.length,4);
});
test('network failure never claims that a component is current',async()=>{
 const a=app();await a.api.check();a.ctx.fetch=async()=>{throw Error('offline');};
 const result=await a.api.check(true);assert.equal(result.extension.error,true);assert.equal(result.service.error,true);assert.equal(result.service.available,false);
});
test('old or absent service preserves extension updates and exposes migration',async()=>{
 const a=app();await a.api.check();a.ctx.native=async m=>{if(m.action==='status')return {version:'1.3.1'};throw Error('unsupported');};
 const result=await a.api.check(true);assert.equal(result.service.current,'1.3.1');assert.equal(result.service.canUpdate,false);assert.equal(result.extension.available,true);
});
test('stable release absence and prereleases do not offer service updates',async()=>{
 const a=app();await a.api.check();a.ctx.fetch=async()=>({status:404,ok:false});
 assert.equal((await a.api.check(true)).service.unpublished,true);
 a.ctx.fetch=async()=>({ok:true,json:async()=>({tag_name:'v1.4.0',prerelease:true})});
 assert.equal((await a.api.check(true)).service.available,false);
});
test('work or pending requests prevent installing either component',async()=>{
 const a=app();await a.api.check(true);a.ctx.workClaim='capture';await assert.rejects(a.api.installService(),/termine/);await assert.rejects(a.api.extension(),/termine/);
 a.ctx.workClaim=null;a.ctx.requests.set('request',{});await assert.rejects(a.api.installService(),/termine/);
});
test('service install reconnects and verifies the version, preserving an actionable error on failure',async()=>{
 const a=app();await a.api.check(true);let installed=false,disconnected=false;
 a.ctx.port={disconnect(){disconnected=true;}};
 a.ctx.native=async m=>{if(m.action==='install_update'){installed=true;return {};}return {version:installed?'1.4.0':'1.3.2'};};
 const result=await a.api.installService();assert.equal(disconnected,true);assert.equal(result.service.current,'1.4.0');assert.equal(result.service.available,false);assert.equal(a.api.busy(),false);
 a.data.updateState.service={current:'1.3.2',latest:'1.4.0',canUpdate:true};a.ctx.native=async()=>{throw Error('download failed');};
 await assert.rejects(a.api.installService(),/download failed/);assert.equal(a.data.updateInstalling,false);assert.equal(a.data.updateInstallError,'download failed');
});
test('extension install always opens Mozilla, ignoring remote URL fields',async()=>{
 const a=app();await a.api.check();a.data.updateState={extension:{url:'https://evil.test'}};await a.api.extension();assert.equal(a.opened[0].url,'https://addons.mozilla.org/firefox/addon/anaco/');
});
