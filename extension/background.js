/* The background owns in-flight requests so closing the sidebar doesn't cancel them. */
const HOST = "org.samuh.anaco_ob";
const SESSION = crypto.randomUUID();
// A sidebar belongs to the page explicitly chosen by the user, not the active tab.
const panelSources = new Map();
function bindPanel(tab) {
  if (!tab || !Number.isInteger(tab.windowId)) return;
  panelSources.set(tab.windowId, {tabId:tab.id, windowId:tab.windowId, url:tab.url});
  browser.storage.local.set({panelBindingRevision:crypto.randomUUID()});
}
async function panelSource(windowId) {
  if (!panelSources.has(windowId)) {
    const [tab] = await browser.tabs.query({active:true, windowId});
    if (tab) bindPanel(tab);
  }
  return panelSources.get(windowId);
}
async function resumeCapture(message) {
  const c=await native({action:"load",id:message.id});
  if(workClaim||pendingDiscard)throw new Error(tx('bg_ya_hay_un_trabajo_en_curso'));
  if(c.status==='discarded'||c.status==='saved')throw new Error(tx('bg_captura_ya_no_pendiente'));
  const {sources={}}=await browser.storage.local.get("sources");c.source=sources[c.id];
  // The panel that resumes a capture shows it, even when its source tab is gone.
  if(Number.isInteger(message.windowId))panelSources.set(message.windowId,{tabId:c.source?.tabId,windowId:message.windowId,url:c.source?.url});
  await browser.storage.local.set({editorFields:null,operationError:"",pageContext:{...c.source,status:"ready"}});
  await publishCapture(c,c.draft?{capture:c,draft:c.draft,folders:(await native({action:"status"})).folders}:null);
  if(c.draft&&c.status==="draft")await openReview(c.id);
  return c;
}
async function panelCapture(windowId) {
  const source=await panelSource(windowId);
  const state=await browser.storage.local.get(['currentCapture','draftResult','pageContext']);
  if(state.pageContext?.tabId===source?.tabId)return {...state,panelSource:source};
  const cached=source&&tabCaptures.get(`${source.tabId}:${source.url}`);
  return {...(cached||{currentCapture:null,draftResult:null}),pageContext:source?{...source,status:'ready'}:null,panelSource:source};
}
function captureForToken(token) {
  if(!token)return null;
  for(const value of tabCaptures.values())if(value.currentCapture?.token===token)return value.currentCapture;
  return null;
}
// Keep return targets in this browser session; never reuse tab IDs after restart.
const optionsSources = new Map();
const reviewSessions={};
browser.storage.local.set({reviewSessions:{}});
async function reviewStatus(message,sender){
  const expected=browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(message.id);
  if(!sender.tab||sender.url!==expected)return;
  // Statuses are sent on a timer: one may arrive after the review closed or left its tab.
  const tab=await browser.tabs.get(sender.tab.id).catch(()=>null);
  if(tab?.url!==expected)return;
  if(sender.tab.active)for(const value of Object.values(reviewSessions))if(value.windowId===sender.tab.windowId)value.tabActive=false;
  reviewSessions[message.id]={...message.status,id:message.id,tabId:sender.tab.id,windowId:sender.tab.windowId,instance:message.instance,tabActive:Boolean(sender.tab.active),updatedAt:Date.now()};
  await browser.storage.local.set({reviewSessions:{...reviewSessions}});
  return true;
}
async function clearReviewTab(tabId){
  let changed=false;
  for(const [id,value] of Object.entries(reviewSessions))if(value.tabId===tabId){delete reviewSessions[id];changed=true;}
  if(changed)await browser.storage.local.set({reviewSessions:{...reviewSessions}});
}
browser.tabs.onUpdated?.addListener((id,change)=>{if(change.url&&!change.url.startsWith(browser.runtime.getURL('review.html')+'?capture='))clearReviewTab(id);});
browser.tabs.onActivated?.addListener(info=>{
  let changed=false;
  for(const value of Object.values(reviewSessions))if(value.windowId===info.windowId){const active=value.tabId===info.tabId;if(value.tabActive!==active){value.tabActive=active;changed=true;}if(active)value.updatedAt=Date.now();}
  if(changed)browser.storage.local.set({reviewSessions:{...reviewSessions}});
});
async function reviewCommand(message){
  const session=reviewSessions[message.id];
  if(!session||session.windowId!==message.windowId)throw new Error(tx('bg_esa_revision_ya_no_esta_abierta_en_esta_'));
  const commands=['focus','note','include','read','edit','properties','connections','refreshLinks','split','save'];
  if(!commands.includes(message.command))throw new Error(tx('bg_accion_de_revision_no_disponible'));
  const tab=await browser.tabs.get(session.tabId);
  if(tab.url!==browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(message.id)){await clearReviewTab(tab.id);throw new Error(tx('bg_la_revision_se_cerro'));}
  await browser.tabs.update(tab.id,{active:true});
  if(message.command==='focus')return true;
  const pending=browser.runtime.sendMessage({type:'reviewControl',id:message.id,instance:session.instance,command:message.command,note:message.note,value:message.value});
  if(message.command==='save'){pending.catch(()=>{});return true;}
  return pending;
}
browser.tabs.onRemoved.addListener(id => optionsSources.delete(id));
// First install: show how to set up the local service, vault and AI.
browser.runtime.onInstalled?.addListener(({reason})=>{if(reason==='install')browser.tabs.create({url:browser.runtime.getURL('welcome.html')});});
async function openOptions(windowId) {
  const [source] = await browser.tabs.query({active: true, windowId});
  const tab = await browser.tabs.create({url: browser.runtime.getURL('options.html'),
    ...(source ? {windowId: source.windowId} : {})});
  if (Number.isInteger(source?.id) && source.id >= 0) optionsSources.set(tab.id, {tabId: source.id, windowId: source.windowId});
}
async function returnFromOptions(sender) {
  if (sender.url !== browser.runtime.getURL('options.html') || !sender.tab) return false;
  const source = optionsSources.get(sender.tab.id);
  if (!source) return false;
  try {
    const tab = await browser.tabs.get(source.tabId);
    if (tab.windowId !== sender.tab.windowId || tab.windowId !== source.windowId) return false;
    await browser.tabs.update(tab.id, {active: true});
    await browser.tabs.remove(sender.tab.id);
    return true;
  } catch { return false; }
}
let locateSequence = 0;
let port;
let workClaim=null;
let pendingDiscard=false;
// Close the sidebar Firefox inherits into a new window, keeping explicit opens.
const knownSidebarWindows=new Set(),inheritedSidebarWindows=new Set();
const sidebarInitialization=browser.windows?.getAll?browser.windows.getAll({windowTypes:['normal']}).then(windows=>{for(const w of windows)knownSidebarWindows.add(w.id);}):Promise.resolve();
let sidebarOpening=Promise.resolve();
browser.windows?.onCreated?.addListener(w=>{if(!knownSidebarWindows.has(w.id)){knownSidebarWindows.add(w.id);inheritedSidebarWindows.add(w.id);}});
browser.windows?.onRemoved?.addListener(id=>{knownSidebarWindows.delete(id);inheritedSidebarWindows.delete(id);});
function openSidebar(tab){
  if(tab&&!workClaim&&!globalThis.AnacoObBatch?.busy())bindPanel(tab);
  if(Number.isInteger(tab?.windowId)){knownSidebarWindows.add(tab.windowId);inheritedSidebarWindows.delete(tab.windowId);}
  else if(browser.windows?.getLastFocused)sidebarOpening=browser.windows.getLastFocused().then(w=>{knownSidebarWindows.add(w.id);inheritedSidebarWindows.delete(w.id);});
  // Keep this call inside the original user gesture.
  return browser.sidebarAction.open();
}
async function allowSidebar(windowId){
  await sidebarInitialization;await sidebarOpening;
  if(!knownSidebarWindows.has(windowId)){knownSidebarWindows.add(windowId);inheritedSidebarWindows.add(windowId);}
  return !inheritedSidebarWindows.delete(windowId);
}
const cancelledWork=new Set(),workResources=new Map(),workAbortControllers=new Map();
function checkWork(){if(workClaim&&cancelledWork.has(workClaim))throw new Error(tx('bg_trabajo_cancelado_puedes_reanudarlo_desd'));}
const requests = new Map();
browser.storage.local.get(["operation","activeWork"]).then(({operation,activeWork}) => {
  if (operation||activeWork) browser.storage.local.set({activeWork:null,operation:"",operationProgress:null,operationError:tx('bg_la_preparacion_anterior_se_interrumpio_p')});
});
function native(message, timeoutMs=2400000) {
  return new Promise((resolve, reject) => {
    if(['capture','draft','revise','propose_split','refresh_links','upload_begin','upload_chunk','upload_finish','finish_asset','video_url','subtitles'].includes(message.action)||message.action?.startsWith('reader_'))try{checkWork();}catch(error){reject(error);return;}
    if (!port) {
      port = browser.runtime.connectNative(HOST);
      port.onMessage.addListener(response => {
        const pending = requests.get(response.requestId);
        if (!pending) return;
        if(response.progress){if(pending.workId&&pending.workId===workClaim&&!cancelledWork.has(workClaim)){const p=response.progress;browser.storage.local.set({operation:typeof p==='string'?p:p.message,operationProgress:typeof p==='object'?{...p,updatedAt:Date.now()}:null});}return;}
        clearTimeout(pending.timer); requests.delete(response.requestId);
        response.ok ? pending.resolve(response.result) : pending.reject(new Error(response.error));
      });
      port.onDisconnect.addListener(() => {
        const error = port?.error?.message || tx('bg_no_se_pudo_conectar_con_el_servicio_loca');
        port = null;
        for (const pending of requests.values()) { clearTimeout(pending.timer); pending.reject(new Error(error)); }
        requests.clear();
      });
    }
    const requestId = crypto.randomUUID();
    const timer = setTimeout(() => {requests.delete(requestId); reject(new Error(tx('bg_el_servicio_esta_tardando_demasiado_la_c')));}, timeoutMs);
    requests.set(requestId, {resolve, reject, timer,workId:workClaim});
    try { port.postMessage({...message, requestId,task:workClaim,lang:AnacoObI18n.language()}); } catch (error) { clearTimeout(timer); requests.delete(requestId); reject(error); }
  });
}

async function beginWork(c,operation,showCapture=true){
  if(workClaim||pendingDiscard)throw new Error(tx('bg_ya_hay_un_trabajo_en_curso_puedes_seguir'));
  const id=crypto.randomUUID();workClaim=id;++detectionSequence;
  if(typeof AbortController==='function')workAbortControllers.set(id,new AbortController());
  const activeWork={id,title:c.title||tx('bg_captura'),source:c.source||{url:c.url},captureToken:c.token,captureId:c.id,startedAt:Date.now()};
  try{
    const {workSources={}}=await browser.storage.local.get('workSources');workSources[id]={source:activeWork.source,title:activeWork.title};await browser.storage.local.set({workSources});
    await browser.storage.local.set({activeWork,operation,operationProgress:null,operationError:'',operationDiagnostic:null,
      pageContext:{...activeWork.source,status:'ready'},...(showCapture?{currentCapture:c}:{currentCapture:null,draftResult:null})});
  }catch(error){workClaim=null;throw error;}
  return id;
}
async function endWork(id,error=null){
  if(id!==workClaim)return false;
  try{await native({action:'finish_job',job:id,status:cancelledWork.has(id)?'cancelled':error?'failed':'complete'});}catch{}
  await browser.storage.local.set({activeWork:null,operation:'',operationProgress:null,operationError:error?.message||''});
  workClaim=null;cancelledWork.delete(id);workResources.delete(id);workAbortControllers.delete(id);return true;
}
async function cancelWork(){
  if(!workClaim)return;
  const id=workClaim;cancelledWork.add(id);await browser.storage.local.set({operation:tx('bg_cancelando_el_trabajo_y_conservando_el_a'),operationProgress:{stage:'cancel'}});
  workAbortControllers.get(id)?.abort();
  for(const r of workResources.get(id)||[])browser.tabs.executeScript(r.tabId,{frameId:r.frameId,code:`AnacoObResource.close(${JSON.stringify(r.job)});void 0;`}).catch(()=>{});
  const result=await browser.runtime.sendNativeMessage(HOST,{action:'cancel_job',job:id,lang:AnacoObI18n.language()});if(!result.ok)throw new Error(result.error);
}

const tabCaptures = new Map();
let detectionSequence = 0;
const keyFor = tab => `${tab.id}:${tab.url}`;
const sourceFor = tab => ({tabId:tab.id, windowId:tab.windowId, url:tab.url, cookieStoreId:tab.cookieStoreId, session:SESSION});
function pdfCapture(tab) {
  return {kind:"pdf",url:tab.url,title:tab.title||tx('bg_documento_pdf'),text:"",images:[],warnings:[],documents:[{url:tab.url,title:tab.title||"PDF"}],videos:[],frames:[],contentReady:false,requiredOrigins:[]};
}
// Content scripts cannot read the extension's storage: they get the language from here.
async function injectI18n(tabId,target){
  await browser.tabs.executeScript(tabId,{...target,code:`globalThis.AnacoObLang=${JSON.stringify(AnacoObI18n.language())};void 0;`});
  await browser.tabs.executeScript(tabId,{...target,file:"i18n-catalog.js"});
  await browser.tabs.executeScript(tabId,{...target,file:"i18n.js"});
}
async function readFrame(tabId, frameId, input = {}) {
  const target = {frameId, matchAboutBlank:true};
  await injectI18n(tabId, target);
  await browser.tabs.executeScript(tabId, {...target, file:"surfaces.js"});
  await browser.tabs.executeScript(tabId, {...target, file:"media-source.js"});
  await browser.tabs.executeScript(tabId, {...target, file:"embeds.js"});
  await browser.tabs.executeScript(tabId, {...target, file:"capture.js"});
  const [result] = await browser.tabs.executeScript(tabId, {...target, code:`globalThis.AnacoObCapture(${JSON.stringify(input)})`});
  return {...result, frameId};
}
async function probePDF(url){
  try{
    const response=await fetch(url,{method:'HEAD',credentials:'include',signal:AbortSignal.timeout(6000)});
    return response.ok&&/application\/pdf/i.test(response.headers.get('content-type')||'');
  }catch{return false;}
}
async function scanTab(tab, input = {}, modeOverride) {
  if (AnacoObDetection.pdfURL(tab.url)) return pdfCapture(tab);
  const pages = [], blocked = [];
  // Course mode is the previous detection, kept as an escape hatch for course players.
  const {captureMode:storedMode='auto'}=await browser.storage.local.get('captureMode');
  const captureMode=modeOverride||storedMode;
  const embeds=captureMode!=='course';
  try { pages.push(await readFrame(tab.id, 0, embeds?{...input,embeds:true}:input)); }
  catch {
    const granted = await browser.permissions.contains({origins:[AnacoObDetection.origin(tab.url)].filter(Boolean)});
    if (granted && await probePDF(tab.url)) return pdfCapture(tab);
    blocked.push({url:tab.url,title:tab.title||tx('bg_pagina_actual'),needsPermission:!granted,top:true});
  }
  if (input.kind === 'quote' || input.kind === 'image') return pages[0];
  const all = await browser.webNavigation.getAllFrames({tabId:tab.id}).catch(() => []);
  // Read each frame independently. One denied domain must not hide other frames.
  const frames = (all || []).filter(f => f.frameId !== 0 && !f.errorOccurred &&
    !/doubleclick|recaptcha|googlesyndication/i.test(f.url) && !globalThis.AnacoObMedia?.auxiliaryFrame(f.url) && !(embeds&&AnacoObEmbeds.embedFrame(f.url))).slice(0,40);
  const results = await Promise.allSettled(frames.map(async frame => {
    if (AnacoObDetection.pdfURL(frame.url)) return {kind:'pdf',url:frame.url,frameId:frame.frameId,documents:[{url:frame.url,title:tx('bg_pdf_del_curso')}]};
    try { return {...await readFrame(tab.id, frame.frameId),parentFrameId:frame.parentFrameId}; }
    catch {
      const origin=AnacoObDetection.origin(frame.url);
      const granted=origin&&await browser.permissions.contains({origins:[origin]});
      if(granted&&await probePDF(frame.url))return {kind:'pdf',url:frame.url,frameId:frame.frameId,documents:[{url:frame.url,title:tx('bg_pdf_del_visor')}]};
      return {blocked:true,url:frame.url,title:tx('bg_contenido_incrustado'),needsPermission:!granted,frameId:frame.frameId,reason:granted?'script-unreadable':'permission-required'};
    }
  }));
  for (const result of results) if (result.status === 'fulfilled') {
    if (result.value.blocked) { if (AnacoObDetection.origin(result.value.url)) blocked.push(result.value); }
    else pages.push(result.value);
  }
  // The live navigation tree is authoritative. An iframe's src can still be
  // its launch URL after a redirect, so it is not evidence of denied access.
  const unmatched=pages.flatMap(p=>(p.frames||[]).filter(f=>!all?.some(live=>live.url===f.url))).length;

  return AnacoObDetection.merge(pages, tab, blocked, {frameReferencesUnmatched:unmatched,captureMode}, {preferTop:captureMode==='article'});
}
let activeDetection;
// The capture mode is part of the key, so changing it starts a new detection.
// GUARD -> capture() stays synchronous: an await here would let a later automatic
// detection start first and replace the capture the user asked for.
let captureModeCache='auto';
Promise.resolve(browser.storage.local.get('captureMode')).then(v=>{captureModeCache=v?.captureMode||'auto';},()=>{});
browser.storage.onChanged?.addListener((changes,area)=>{if(area==='local'&&changes.captureMode)captureModeCache=changes.captureMode.newValue||'auto';});
let explicitCapture=null;
function capture(tab,input={},options={}){
  const key=tab?keyFor(tab)+JSON.stringify(input)+captureModeCache:'';
  if(activeDetection?.key===key)return activeDetection.promise;
  // Binding the panel triggers an automatic detection; it must not replace a selection still being read.
  if(options.automatic&&tab&&explicitCapture?.tab===keyFor(tab))return explicitCapture.promise;
  const promise=performCapture(tab,input,options).finally(()=>{if(activeDetection?.promise===promise)activeDetection=null;});
  activeDetection={key,promise};
  if(!options.automatic&&tab){
    const entry={tab:keyFor(tab),promise};explicitCapture=entry;
    promise.then(()=>{},()=>{}).finally(()=>{if(explicitCapture===entry)explicitCapture=null;});
  }
  return promise;
}
async function performCapture(tab, input = {}, {automatic = false, fresh = true} = {}) {
  if(AnacoObBatchBusy()){if(automatic)return null;throw new Error(tx('batch_busy'));}
  if (automatic && tab?.url?.startsWith(browser.runtime.getURL(''))) return null;
  if(workClaim){if(automatic)return (await browser.storage.local.get('currentCapture')).currentCapture;throw new Error(tx('bg_la_captura_actual_sigue_procesandose_pue'));}
  const sequence = ++detectionSequence;
  if (!tab?.id || !/^(https?:|file:)/.test(tab.url || '')) {
    if (automatic && tab?.url?.startsWith(browser.runtime.getURL(''))) return null;
    await browser.storage.local.set({currentCapture:null,draftResult:null,pageContext:{tabId:tab?.id,url:tab?.url,status:'error',error:tx('bg_esta_pestana_no_contiene_una_pagina_web_')}});
    return null;
  }
  const existing=await browser.storage.local.get(['currentCapture','pageContext']);
  if(automatic&&existing.currentCapture?.reader&&existing.pageContext?.tabId===tab.id&&existing.pageContext.url===tab.url)return existing.currentCapture;
  const cached = tabCaptures.get(keyFor(tab));
  if (!fresh && cached && (cached.currentCapture?.id||['quote','image'].includes(cached.currentCapture?.kind))) {
    await browser.storage.local.set({...cached,pageContext:{...sourceFor(tab),status:'ready'}});
    return cached.currentCapture;
  }
  const samePage=existing.pageContext?.tabId===tab.id&&existing.pageContext.url===tab.url;
  if(!samePage||!automatic)await browser.storage.local.set({currentCapture:null,draftResult:null,operationError:'',pageContext:{...sourceFor(tab),status:'loading'}});
  try {
    let timer;
    const result = await Promise.race([scanTab(tab,input), new Promise((_,reject) => {timer=setTimeout(() => reject(new Error(tx('bg_no_se_pudo_terminar_la_deteccion_espera_'))),12000);})]).finally(()=>clearTimeout(timer));
    if (!result) throw new Error(tx('bg_no_se_pudo_leer_el_contenido_seleccionad'));
    result.source = sourceFor(tab); result.token = crypto.randomUUID();
    result.detectionError = AnacoObDetection.problem(result);
    // Empty detections are still shown, with their specific explanation.
    if (tabCaptures.size >= 80) tabCaptures.delete(tabCaptures.keys().next().value);
    if (sequence !== detectionSequence) return result;
    const value = {currentCapture:result,draftResult:null};
    tabCaptures.set(keyFor(tab),value);
    await browser.storage.local.set({...value,editorFields:null,operationError:'',pageContext:{...sourceFor(tab),status:'ready'}});
    return result;
  } catch (error) {
    if (sequence === detectionSequence) await browser.storage.local.set({currentCapture:null,draftResult:null,pageContext:{...sourceFor(tab),status:'error',error:error.message}});
    throw error;
  }
}
async function capturePdf(tab) {
  // Kept for older callers; it no longer turns an arbitrary HTML page into a PDF.
  return capture(tab);
}
async function detectActive(message = {}) {
  if(globalThis.AnacoObBatch?.busy())return null;
  let source;
  if(Number.isInteger(message.windowId)) {
    if(message.useActive&&!workClaim){const [active]=await browser.tabs.query({active:true,windowId:message.windowId});bindPanel(active);}
    source=await panelSource(message.windowId);
  }
  const id=source?.tabId??message.tabId;
  const tab = Number.isInteger(id)?await browser.tabs.get(id).catch(()=>null):(await browser.tabs.query({active:true,currentWindow:true}))[0];
  if(!tab)return null;
  if(source&&source.url!==tab.url)bindPanel(tab);
  return capture(tab, {}, {automatic:true, fresh:message.fresh !== false});
}
async function publishCapture(c, draftResult = null) {
  const value = {currentCapture:c,draftResult};
  if (c.source?.tabId) tabCaptures.set(`${c.source.tabId}:${c.source.url}`,value);
  const {pageContext} = await browser.storage.local.get('pageContext');
  if (!pageContext || pageContext.tabId === c.source?.tabId && pageContext.url === c.source?.url) {
    await browser.storage.local.set(value);
  }
}

async function imageData(image) {
  checkWork();
  if(image.data)return image; // Locally rendered canvas/SVG page, already rasterized.
  const controller = new AbortController();
  const workSignal=workAbortControllers.get(workClaim)?.signal,abort=()=>controller.abort();workSignal?.addEventListener('abort',abort,{once:true});
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(image.url, {credentials: "include", signal: controller.signal});
    if (!response.ok) throw new Error("HTTP " + response.status);
    if (Number(response.headers.get("content-length")) > 3000000) throw new Error(tx('bg_supera_3_mb'));
    const reader = response.body.getReader();
    const parts = []; let size = 0;
    while (true) { const {value, done} = await reader.read(); if (done) break; size += value.length; if (size > 3000000) {await reader.cancel(); throw new Error(tx('bg_supera_3_mb'));} parts.push(value); }
    const bytes = new Uint8Array(size); let offset = 0; for (const part of parts) {bytes.set(part,offset); offset += part.length;}
    let binary = ""; for (let i=0; i<bytes.length; i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
    return {...image, data: btoa(binary)};
  } finally { clearTimeout(timer);workSignal?.removeEventListener('abort',abort); }
}

// =============================================================================
// [FLOW] EMBEDDED RESOURCES
// Clips and CodePen demos are copied when the note is prepared, never during
// detection. Each failure becomes a warning; the rest of the capture continues.
// =============================================================================
// Native messages are bounded: bytes travel as ordered base64 chunks.
async function uploadParts(upload,parts){
  let offset=0;
  for(const bytes of parts){for(let start=0;start<bytes.length;start+=393216){const piece=bytes.subarray(start,start+393216);let binary='';for(let i=0;i<piece.length;i+=8192)binary+=String.fromCharCode(...piece.subarray(i,i+8192));await native({action:'upload_chunk',upload,offset,data:btoa(binary)});offset+=piece.length;}}
}
async function uploadAsset(name,parts,size){
  const begin=await native({action:'upload_begin',purpose:'asset',name,size});
  await uploadParts(begin.upload,parts);
  return native({action:'finish_asset',upload:begin.upload});
}
async function clipAsset(item,source){
  const {parts,size}=await resourceBytes(item.url,source,0,100000000);
  const ext=(item.url.match(/\.(mp4|webm|mov)(?:[?#]|$)/i)?.[1]||'mp4').toLowerCase();
  return uploadAsset('clip.'+ext,parts,size);
}
async function fetchBytes(url,limit,credentials='include'){
  const response=await fetch(url,{credentials,signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const raw=new Uint8Array(await response.arrayBuffer());
  if(raw.length>limit)throw new Error(tx('bg_supera_el_limite_de_tamano'));
  return raw;
}
// Runs inside the CodePen embed frame: its tabs hold the original source.
function readPenSource(){
  const box=key=>document.querySelector('#'+key+'-box pre')?.textContent||'';
  const code={html:box('html'),css:box('css'),js:box('js')};
  return Object.values(code).some(Boolean)?code:null;
}
function compiledPenCode(doc){
  const scripts=[...doc.querySelectorAll('script:not([src])')].filter(s=>!s.type||/javascript|module/i.test(s.type));
  // CodePen's own boilerplate is short and mentions its runtime; the pen code is not.
  const js=scripts.map(s=>s.textContent.trim()).filter(t=>t&&!(t.length<400&&/CP\.|codepen/i.test(t))).join('\n\n')
    // Loop guards inserted by CodePen are not part of the author's code.
    .replace(/\s*if \(window\.CP\.shouldStopExecution\(\d+\)\) break;/g,'').replace(/\s*window\.CP\.exitedLoop\(\d+\);/g,'');
  const body=doc.body.cloneNode(true);for(const s of body.querySelectorAll('script:not([type]),script[type*=javascript],script[type=module]'))s.remove();
  return {html:body.innerHTML.trim(),css:[...doc.querySelectorAll('style')].map(s=>s.textContent.trim()).join('\n\n'),js};
}
async function penPackage(item,source,warnings){
  let code=null,code_source='source';
  const frames=await browser.webNavigation.getAllFrames({tabId:source?.tabId}).catch(()=>[]);
  const frame=(frames||[]).find(f=>/\/embed\//.test(f.url)&&AnacoObEmbeds.penFromURL(f.url)?.slug===item.slug);
  if(frame){try{[code]=await browser.tabs.executeScript(source.tabId,{frameId:frame.frameId,code:`(${readPenSource})()`});}catch{/* Not loaded yet: use the compiled page below. */}}
  let demo;
  try{
    const fetched=new TextDecoder().decode(await fetchBytes(`https://cdpn.io/${item.user}/fullembedgrid/${item.slug}?animations=run&type=embed`,5000000));
    // Without a codepen.io referer the demo arrives escaped inside a warning page.
    const shell=new DOMParser().parseFromString(fetched,'text/html');
    const page=shell.querySelector('iframe[srcdoc]')?.getAttribute('srcdoc')||fetched,doc=page===fetched?shell:new DOMParser().parseFromString(page,'text/html');
    if(!code){code=compiledPenCode(doc);code_source='compiled';}
    // Public CDNs answer with a wildcard CORS header, which rejects cookies.
    const offline=await AnacoObEmbeds.vendor(page,`https://cdpn.io/${item.user}/fullembedgrid/${item.slug}`,url=>{checkWork();return fetchBytes(url,10000000,'omit');});
    if(offline.missing.length)warnings.push(tx('bg_demo_1_2_archivos_externos_no_se_pudiero',[item.title,offline.missing.length]));
    const libs=[];
    for(const file of offline.files)libs.push({url:file.url,name:file.name,...await uploadAsset(/\.css$/.test(file.name)?'lib.css':'lib.js',[file.bytes],file.bytes.length)});
    const raw=new TextEncoder().encode(offline.page);
    const html=await uploadAsset('index.html',[raw],raw.length);
    demo={page:html.asset,libs:libs.map(l=>({url:l.url,name:l.name,asset:l.asset}))};
  }catch(error){warnings.push(tx('bg_demo_1_no_se_pudo_guardar_una_copia_sin_',[item.title,error.message,code?tx('bg_y_el_codigo'):'']));}
  return {...item,code:code||{},code_source,...(demo?{demo}:{})};
}
async function embedResources(c,selection,warnings){
  const out=[],chosen=new Set(selection||[]);let done=0;const total=(c.embeds||[]).filter((e,i)=>chosen.has(i)&&e.type!=='tweet').length;
  for(const [index,value] of (c.embeds||[]).entries()){
    const {thumbnail,warning,index:_,...item}=value;const selected=chosen.has(index);
    if(!selected||item.type==='tweet'){out.push({...item,selected});continue;}
    checkWork();await browser.storage.local.set({operation:tx('bg_guardando_recursos_incrustados_1_de_2',[done+1,total]),operationProgress:{stage:'resources',unit:'resources',completed:done,total}});
    if(item.type==='pen')out.push({...await penPackage(item,c.source,warnings),selected});
    else try{out.push({...item,selected,...await clipAsset(item,c.source)});}
    catch(error){checkWork();warnings.push(tx('bg_clip_1_no_se_pudo_guardar_2',[item.title,error.message]));out.push({...item,selected:false});}
    checkWork();
    done++;
    await browser.storage.local.set({operationProgress:{stage:'resources',unit:'resources',completed:done,total}});
  }
  return out;
}

async function prepare(message,ownedCapture=null) {
  const {operation,currentCapture:capture}=await browser.storage.local.get(['operation','currentCapture']);
  if(operation||workClaim)throw new Error(tx('bg_ya_hay_una_nota_preparandose'));
  let c=ownedCapture||capture;
  if(!c)throw new Error(tx('bg_primero_captura_una_pagina_frase_o_image'));
  if(message.token&&c.token!==message.token)throw new Error(tx('bg_la_pestana_cambio_antes_de_preparar_la_n'));
  if(!c.id&&(c.reader||c.kind==='pdf'||c.kind==='video'||!AnacoObDetection.usable(c)))throw new Error(tx('bg_primero_extrae_el_documento_detectado'));
  c={...c,intent:message.intent||'',selected_images:message.images||c.selected_images};
  const work=await beginWork(c,tx('bg_preparando_la_propuesta'));
  try {
    let selected=message.images;
    if (!c.id) {
      const images = [];
      const warnings = [...c.warnings];
      if(c.reader&&(message.images||[]).length<c.images.length)warnings.push(tx('bg_lector_html_se_han_elegido_1_de_2_pagina',[(message.images||[]).length,c.images.length]));
      for (const index of message.images || []) {
        try { images.push(await imageData(c.images[index])); }
        catch (e) { warnings.push(tx('bg_no_se_pudo_conservar_una_imagen_1',[e.message])); }
      }
      if (c.kind === "image" && !images.length) throw new Error(tx('bg_no_se_pudo_descargar_la_imagen_esta_vers'));
      const embeds = c.embeds?.length ? await embedResources(c, message.embeds, warnings) : undefined;
      const source = c.source, token = c.token;
      c = {...await native({action: "capture", capture: {...c, images, warnings, embeds}}), source, token};
      selected=c.images.map((_,index)=>index);
      const {sources={}} = await browser.storage.local.get("sources");
      sources[c.id] = source || {url:c.url};
      await browser.storage.local.set({sources});
      await publishCapture(c);
    }
    const conversation=message.conversation||(captureModeCache==='podcast'?'on':'auto');
    checkWork();
    await browser.storage.local.set({operation:tx('bg_preparando_la_propuesta'),operationProgress:null});
    const result = await native({action: "draft", id: c.id, intent: message.intent, provider: message.provider,images:selected,note_structure:message.note_structure,conversation},c.reader?.job||c.kind==='video'?7200000:2400000);
    localStorage.removeItem("editor:" + c.id);
    result.capture.source = c.source;
    result.capture.token = c.token;
    await publishCapture(result.capture, result);
    await browser.storage.local.set({editorFields:null});
    if(!message.deferReview)await openReview(c.id,{automatic:true,source:c.source});
    await endWork(work);
    return result;
  } catch (error) {
    await endWork(work,error); throw error;
  }
}

async function openReview(id,{automatic=false,source}={}) {
  const c = await native({action:"load",id});
  if (!c.draft || c.status !== "draft") throw new Error(tx('bg_esta_captura_no_tiene_una_propuesta_pend'));
  const url = browser.runtime.getURL("review.html") + "?capture=" + encodeURIComponent(id);
  const {reviews={},sources={}} = await browser.storage.local.get(["reviews","sources"]);
  source=source||sources[id];let windowId,active=!automatic;
  if(automatic&&source?.windowId&&browser.windows?.get){try{await browser.windows.get(source.windowId);windowId=source.windowId;}catch{}}
  if(automatic&&windowId){
    const focused=await browser.windows.getLastFocused();const [tab]=await browser.tabs.query({active:true,windowId});
    active=focused.focused!==false&&focused.id===windowId&&(tab?.id===source.tabId||tab?.url?.startsWith(browser.runtime.getURL('panel.html')));
  }
  if (reviews[id]) {
    try {
      const tab=await browser.tabs.get(reviews[id]);
      if(tab.url===url){if(active)await browser.tabs.update(tab.id,{active:true});return {tabId:tab.id};}
    } catch { /* Its previous review tab was closed. */ }
  }
  const tab = await browser.tabs.create({url,active,...(windowId?{windowId}:{})});
  reviews[id]=tab.id;await browser.storage.local.set({reviews});
  return {tabId:tab.id};
}

async function locateImage(message) {
  const sequence=++locateSequence;
  const {currentCapture:c}=await browser.storage.local.get("currentCapture");
  if(!c || c.token!==message.token)return {found:false};
  const source=c.source;
  if(!source?.tabId || source.session!==SESSION)throw new Error(tx('bg_vuelve_a_capturar_el_articulo_para_local'));
  // Embedded resources live in the top frame and carry their own locator.
  const embed=message.embed?c.embeds?.[message.index]:null;
  const image=message.embed?null:c.images[message.index];
  const frameId=image?.frameId||0;
  if(!message.clear&&!image&&!embed?.locator)return {found:false};
  try {
    await injectI18n(source.tabId,{frameId,matchAboutBlank:true});
    await browser.tabs.executeScript(source.tabId,{file:"locate.js",frameId,matchAboutBlank:true});
    if(sequence!==locateSequence)return {found:false};
    const input=message.clear?{clear:true}:embed?{locator:embed.locator,label:message.label}:{imageId:image.imageId,url:image.url,index:message.index};
    const [result]=await browser.tabs.executeScript(source.tabId,{code:`globalThis.AnacoObLocateImage(${JSON.stringify(input)})`,frameId,matchAboutBlank:true});
    return result;
  } catch {
    const origin=AnacoObDetection.origin(c.url);
    if(origin&&!await browser.permissions.contains({origins:[origin]}))throw new Error(tx('bg_anaco_ya_no_tiene_permiso_para_marcar_en'));
    throw new Error(tx('bg_no_puedo_localizar_este_elemento_comprue'));
  }
}

async function reviewData(id) {
  const data=await native({action:'review_data',id});
  return {...data,queueReview:await globalThis.AnacoObBatch?.reviewContext(id)||null};
}

async function discardPending(message){
  if(workClaim||pendingDiscard)throw new Error(tx('bg_ya_hay_un_trabajo_en_curso'));
  pendingDiscard=true;
  try{
    const result=await native(message.job?{action:'discard_job',job:message.job}:{action:'discard',id:message.id});
    const {workSources={},sources={},reviews={},currentCapture}=await browser.storage.local.get(['workSources','sources','reviews','currentCapture']);
    for(const id of message.job?[message.job]:(result.discarded_jobs||[]))delete workSources[id];
    const update={workSources};
    if(!message.job){
      localStorage.removeItem('editor:'+message.id);
      for(const [key,value] of tabCaptures)if(value.currentCapture?.id===message.id)tabCaptures.delete(key);
      if(currentCapture?.id===message.id)Object.assign(update,{currentCapture:null,draftResult:null,editorFields:null,operationError:'',operationDiagnostic:null});
      const reviewTab=reviews[message.id]||reviewSessions[message.id]?.tabId;
      delete sources[message.id];delete reviews[message.id];delete reviewSessions[message.id];
      Object.assign(update,{sources,reviews,reviewSessions:{...reviewSessions}});
      if(reviewTab)try{
        const tab=await browser.tabs.get(reviewTab);
        if(tab.url===browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(message.id))await browser.tabs.remove(tab.id);
      }catch{} // A closed review does not prevent discarding the capture.
    }
    await browser.storage.local.set(update);
    return result;
  }finally{pendingDiscard=false;}
}

async function finishQueueReview(message,sender){
  const context=await globalThis.AnacoObBatch?.reviewContext(message.id);
  let nextId;
  if(message.decision!=='back')for(const id of context?.next||[]){
    const candidate=await native({action:'load',id});
    if(candidate.status==='draft'&&candidate.draft){nextId=id;break;}
    if(['saved','discarded'].includes(candidate.status))await AnacoObBatch.reviewed(id,candidate.status);
  }
  const {reviews={}}=await browser.storage.local.get('reviews');
  delete reviews[message.id];
  const url=nextId?browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(nextId):browser.runtime.getURL('panel.html');
  let existing;
  if(nextId&&reviews[nextId]&&reviews[nextId]!==sender.tab.id){
    try{const tab=await browser.tabs.get(reviews[nextId]);if(tab.url===url)existing=tab;}catch{}
  }
  if(nextId)reviews[nextId]=existing?.id||sender.tab.id;
  await browser.storage.local.set({reviews});
  await clearReviewTab(sender.tab.id);
  if(existing){
    await browser.tabs.update(existing.id,{active:true});
    if(existing.windowId!==sender.tab.windowId)await browser.windows.update(existing.windowId,{focused:true});
    await browser.tabs.remove(sender.tab.id);
  }else await browser.tabs.update(sender.tab.id,{url,active:true});
}

async function finishReview(message,sender) {
  const expected=browser.runtime.getURL("review.html")+"?capture="+encodeURIComponent(message.id);
  if(!sender.tab || sender.url!==expected)throw new Error(tx('bg_esta_accion_debe_iniciarse_en_la_pagina_'));
  const c=await native({action:"load",id:message.id});
  const fromQueue=message.fromQueue||Boolean(await globalThis.AnacoObBatch?.reviewContext(message.id));
  let result;
  if(message.decision==="save")result=await native({action:"save",id:message.id,fields:message.fields});
  else if(message.decision==="discard")result=await native({action:"discard",id:message.id});
  else if(message.decision!=="back")throw new Error(tx('bg_accion_de_revision_desconocida'));
  if(message.decision!=="back"){
    await globalThis.AnacoObBatch?.reviewed(message.id,message.decision==='save'?'saved':'discarded');
    localStorage.removeItem("editor:"+message.id);
    for (const [key,value] of tabCaptures) if(value.currentCapture?.id===message.id)tabCaptures.delete(key);
    const {currentCapture:current}=await browser.storage.local.get("currentCapture");
    if(current?.id===message.id)await browser.storage.local.set({currentCapture:null,draftResult:null,operationError:"",lastResult:message.decision==="save"?result:null});
  }
  if(fromQueue){
    try{await finishQueueReview(message,sender);}catch(error){return {result,completed:message.decision!=='back',returnError:tx('bg_la_operacion_termino_pero_no_pude_volver')+error.message};}
    return {result,completed:true};
  }
  const {sources={},reviews={}}=await browser.storage.local.get(["sources","reviews"]);
  const source=sources[message.id]||{url:c.url};
  try {
    let target;
    if(source.session===SESSION&&Number.isInteger(source.tabId)){
      try{target=await browser.tabs.get(source.tabId);if(target.url!==source.url)target=null;}catch{}
    }
    if(target){await browser.tabs.update(target.id,{active:true});await browser.windows.update(target.windowId,{focused:true});}
    else{const url=source.url||c.url;await browser.tabs.create({url:/^https?:/.test(url)?url:browser.runtime.getURL("panel.html"),active:true,...(source.cookieStoreId&&source.cookieStoreId!=='firefox-default'?{cookieStoreId:source.cookieStoreId}:{})});}
    delete reviews[message.id];await browser.storage.local.set({reviews});
    await browser.tabs.remove(sender.tab.id);
  } catch(error) {return {result,completed:message.decision!=="back",returnError:tx('bg_la_operacion_termino_pero_no_pude_volver')+error.message};}
  return {result,completed:true};
}

async function adoptMedia(c,source){
  c.source=source;c.token=crypto.randomUUID();
  const {sources={}}=await browser.storage.local.get("sources");sources[c.id]=source||{url:c.url};
  for(let index=0;index<c.images.length;index++){
    try{const chunk=await native({action:"image_chunk",id:c.id,index,offset:0});
      if(chunk.total<=262144)c.images[index].thumbnail="data:"+chunk.mime+";base64,"+chunk.data;
    }catch{}
  }
  await browser.storage.local.set({sources});
  await publishCapture(c);return c;
}

async function sourceForImport(){
  const {currentCapture:c}=await browser.storage.local.get("currentCapture");
  if(c?.source)return c.source;
  const [tab]=await browser.tabs.query({active:true,currentWindow:true});
  return tab?{tabId:tab.id,windowId:tab.windowId,url:tab.url,session:SESSION}:null;
}

const resourceHost=url=>{try{return new URL(url).hostname;}catch{return '';}};
function resourceAttempt(diagnostic,value){
  if(!diagnostic)return;
  const same=diagnostic.attempts.find(v=>v.context===value.context&&v.host===value.host&&v.status===value.status&&v.reason===value.reason&&v.method===value.method&&v.credentials===value.credentials);
  if(same)same.count++;else if(diagnostic.attempts.length<16)diagnostic.attempts.push({...value,count:1});
}
async function resourceBytes(url,source,frameId=0,maxBytes=100000000,diagnostic){
  checkWork();const owner=workClaim;const host=resourceHost(url);let frameError;
  if(Number.isInteger(source?.tabId)){
    const target={frameId,matchAboutBlank:true};let job,phase='frame-access';
    try{
      await injectI18n(source.tabId,target);
      await browser.tabs.executeScript(source.tabId,{...target,file:'resource.js'});
      phase='page-fetch';
      const [opened]=await browser.tabs.executeScript(source.tabId,{...target,code:`AnacoObResource.open(${JSON.stringify(url)},${maxBytes})`});
      resourceAttempt(diagnostic,{context:'player',host,status:opened.status,reason:opened.reason||''});
      if(opened.ok){
        phase='page-transfer';
        job=opened.id;let size=0;const parts=[];
        if(workClaim){const list=workResources.get(workClaim)||[];list.push({tabId:source.tabId,frameId,job});workResources.set(workClaim,list);}
        while(true){
          checkWork();
          const [chunk]=await browser.tabs.executeScript(source.tabId,{...target,code:`AnacoObResource.read(${JSON.stringify(job)})`});
          if(chunk.done)break;
          const binary=atob(chunk.data),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
          size+=bytes.length;if(size>maxBytes)throw new Error(tx('bg_el_recurso_supera_el_limite_de_descarga'));parts.push(bytes);
        }
        return {parts,size,url:opened.url};
      }
    }catch(error){frameError=error;resourceAttempt(diagnostic,{context:'player',host,reason:phase,error:error.name||'Error'});}
    finally{if(job){await browser.tabs.executeScript(source.tabId,{...target,code:`AnacoObResource.close(${JSON.stringify(job)});void 0;`}).catch(()=>{});if(owner)workResources.set(owner,(workResources.get(owner)||[]).filter(v=>v.job!==job));}}
    if(frameError?.message===tx('bg_el_recurso_supera_el_limite_de_descarga'))throw frameError;
  }
  // A CDN may allow the extension but reject page CORS. Try its authorized read.
  const workSignal=workAbortControllers.get(workClaim)?.signal;
  const timeout=AbortSignal.timeout(maxBytes>100000000?600000:30000);
  const signal=workSignal?AbortSignal.any([workSignal,timeout]):timeout;
  let response,request={url,method:'GET'},credentials='include',confirmed=false,readable=false;
  const drive=globalThis.AnacoObDriveDownload&&globalThis.AnacoObMedia?.driveFile(url);
  for(let attempt=0;attempt<(drive?4:1);attempt++){
    checkWork();
    const {url:requestURL,...options}=request;
    try{response=await fetch(requestURL,{...options,credentials,signal,cache:drive?'no-store':'default'});}
    catch{
      resourceAttempt(diagnostic,{context:'extension',host:resourceHost(requestURL),reason:'network-or-cors'});
      throw new Error(tx('bg_no_se_pudo_leer_el_recurso_del_reproduct'));
    }
    resourceAttempt(diagnostic,{context:'extension',host:resourceHost(requestURL),status:response.status,
      reason:confirmed?'drive-confirmation':credentials==='omit'?'drive-public-download':'',method:request.method,credentials});
    if(!response.ok){await response.body?.cancel();throw new Error(tx('bg_el_servidor_rechazo_el_recurso_del_repro',[response.status]));}
    const type=response.headers.get('content-type')||'';
    if(!/text\/html|application\/xhtml/i.test(type)){readable=true;break;}
    const next=drive&&!confirmed?await AnacoObDriveDownload.confirmation(response,url,diagnostic):null;
    if(next){request=next;confirmed=true;continue;}
    await response.body?.cancel().catch(()=>{});
    // Public shares may work without the account cookies that caused an HTML
    // redirect. Private shares still need their normal authenticated download.
    if(drive&&credentials==='include'){
      request=AnacoObDriveDownload.publicRequest(url);credentials='omit';confirmed=false;continue;
    }
    break;
  }
  if(!readable)throw new Error(drive?tx('bg_drive_download_html'):tx('bg_el_recurso_devolvio_una_pagina_de_acceso'));
  if(Number(response.headers.get('content-length'))>maxBytes){await response.body?.cancel();throw new Error(tx('bg_el_recurso_supera_el_limite_de_descarga'));}
  let size=0;const parts=[],reader=response.body.getReader();
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>maxBytes){await reader.cancel();throw new Error(tx('bg_el_recurso_supera_el_limite_de_descarga'));}parts.push(value);}
  return {parts,size,url:response.url||url};
}
async function subtitleText(url, source, frameId=0,diagnostic){
  const result=await resourceBytes(url,source,frameId,5000000,diagnostic);
  return new TextDecoder().decode(await new Blob(result.parts).arrayBuffer());
}
async function importResource(message,ownedCapture=null){
  const {operation,currentCapture:storedCapture}=await browser.storage.local.get(['operation','currentCapture']);
  const currentCapture=ownedCapture||storedCapture;
  if(operation)throw new Error(tx('bg_ya_hay_un_recurso_procesandose_puedes_ca'));
  if(message.token&&currentCapture?.token!==message.token)throw new Error(tx('bg_la_pestana_cambio_antes_de_extraer_el_re'));
  const source=currentCapture?.source||await sourceForImport();
  const diagnostic={transport:'drive-confirmation-v2',kind:message.kind,frameId:message.frameId||0,playerHost:resourceHost(message.frameURL||source?.url),resourceHost:resourceHost(message.url),attempts:[]};
  const work=await beginWork(currentCapture||{title:message.title||tx('bg_recurso'),source},message.kind==='pdf'?tx('bg_extrayendo_el_pdf'):tx('bg_recuperando_subtitulos_o_audio'),Boolean(currentCapture));
  try{
    let c;
    if(message.kind==="subtitles"||message.kind==="subtitle-url"){
      try{
        const text=message.kind==='subtitles'?message.text:await subtitleText(message.url,source,message.frameId||0,diagnostic);
        c=await native({action:"subtitles",url:message.pageUrl,title:message.title,text});
      }catch(error){
        checkWork();
        if(!message.fallback)throw error;
        await browser.storage.local.set({operation:tx('bg_los_subtitulos_no_estan_disponibles_recu'),operationProgress:null});
        message={...message,...message.fallback};diagnostic.kind=message.kind;diagnostic.resourceHost=resourceHost(message.url);
      }
    }
    if(!c&&message.kind==="video-platform")c=await native({action:"video_url",url:message.url});
    else if(!c){
      await browser.storage.local.set({operation:message.kind==='pdf'?tx('bg_descargando_el_pdf'):tx('bg_descargando_el_recurso_del_reproductor'),operationProgress:{stage:'download',message:tx('bg_descargando_el_recurso_del_reproductor')}});
      let parts=[],size=0;
      if(message.kind==='video-hls'){
        const {config}=await native({action:'settings'});
        ({parts,size}=await AnacoObStream.download(message.url,{load:(url,limit)=>resourceBytes(url,source,message.frameId||0,limit,diagnostic),maxSeconds:config.video_minutes*60,onProgress:async(completed,total)=>{
          checkWork();
          await browser.storage.local.set({operation:tx('bg_recuperando_video_del_curso_segmento_1_d',[Math.min(completed+1,total),total]),operationProgress:{stage:'download',unit:'segments',completed,total}});
        }}));
      }else{
        ({parts,size}=await resourceBytes(message.url,source,message.frameId||0,message.kind==='pdf'?100000000:1000000000,diagnostic));
      }
      const begin=await native({action:"upload_begin",name:message.name||(message.kind==="pdf"?"documento.pdf":"video.mp4"),size,url:message.pageUrl||message.url});
      await browser.storage.local.set({operation:tx('bg_transfiriendo_archivo'),operationProgress:null});
      await uploadParts(begin.upload,parts);
      await browser.storage.local.set({operation:message.kind==='pdf'?tx('bg_leyendo_las_paginas_del_pdf'):tx('bg_preparando_el_archivo_de_audio'),operationProgress:null});
      c=await native({action:"upload_finish",upload:begin.upload,pages:message.pages||""});
    }
    checkWork();
    c=await native({action:'source_context',id:c.id,source_context:{...currentCapture?.source_context,
      resource_title:currentCapture?.source_context?.resource_title||message.title||c.title,
      page_url:currentCapture?.source_context?.page_url||currentCapture?.url||source?.url||''}});
    const adopted=await adoptMedia(c,source);
    await endWork(work);return adopted;
  }catch(error){error.diagnostic=diagnostic;await browser.storage.local.set({operationDiagnostic:diagnostic});await endWork(work,error);throw error;}
}

let readingBook=false;
async function extractReader(message,ownedCapture=null){
  const {currentCapture:storedCapture,operation}=await browser.storage.local.get(['currentCapture','operation']);
  const c=ownedCapture||storedCapture;
  if(operation||readingBook)throw new Error(tx('bg_ya_hay_una_extraccion_o_una_nota_en_curs'));
  if(!c?.reader||c.token!==message.token)throw new Error(tx('bg_el_lector_cambio_vuelve_a_detectarlo'));
  if(c.reader.overflow)throw new Error(tx('bg_el_libro_supera_las_500_paginas_admitida'));
  const frames=[...new Set([0,...c.reader.frames,...(c.detection?.frameDetails||[]).map(f=>f.id).filter(Number.isInteger)])];
  const work=await beginWork(c,tx('bg_preparando_la_extraccion_del_libro_compl'));
  let failure=null;
  readingBook=true;
  try{
    const pages=[];
    for(const frameId of c.reader.frames){
      const [inventory]=await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.inventory(globalThis.AnacoObReaderRoot||document.body)'});
      if(inventory.overflow)throw new Error(tx('bg_el_libro_supera_el_limite_de_500_paginas'));
      pages.push(...inventory.pages.map(p=>({...p,frameId})));
    }
    if(!pages.length)throw new Error(tx('bg_no_se_localizaron_paginas_del_lector'));
    if(pages.length>500)throw new Error(tx('bg_el_libro_supera_el_limite_de_500_paginas'));
    for(const frameId of frames)await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.start();void 0;'}).catch(()=>{});
    const identity=c.token+':'+pages.map(p=>p.id).join(',');
    const {readerJobs={}}=await browser.storage.local.get('readerJobs');
    const saved=readerJobs[c.token];
    const begin=await native({action:'reader_begin',count:pages.length,url:c.url,title:c.title,context:c.text,identity,job:saved?.identity===identity?saved.job:undefined});
    readerJobs[c.token]={job:begin.job,identity};await browser.storage.local.set({readerJobs});
    const done=new Set(begin.done);
    for(let i=0;i<pages.length;i++){
      if(done.has(i+1))continue;
      await browser.storage.local.set({operation:tx('bg_extrayendo_pagina_1_de_2',[i+1,pages.length]),operationProgress:{stage:'capture',unit:'pages',completed:done.size,total:pages.length}});
      const page=pages[i];
      try{
        const [value]=await browser.tabs.executeScript(c.source.tabId,{frameId:page.frameId,matchAboutBlank:true,code:`AnacoObSurfaces.read(${JSON.stringify(page.id)})`});
        const image=value.image?await imageData(value.image):null;
        const data=image?.data||'';
        const size=data?atob(data).length:0;
        const state=await native({action:'reader_page_begin',job:begin.job,index:i+1,size,text:value.text,label:page.label});
        if(!state.complete){
          let offset=0;
          for(let at=0;at<data.length;at+=524288){const chunk=data.slice(at,at+524288);await native({action:'reader_chunk',job:begin.job,index:i+1,offset,data:chunk});offset+=atob(chunk).length;}
          await native({action:'reader_page_finish',job:begin.job,index:i+1});
        }
        checkWork();done.add(i+1);
        await browser.storage.local.set({operationProgress:{stage:'capture',unit:'pages',completed:done.size,total:pages.length}});
      }catch(error){throw new Error(tx('bg_no_se_ha_podido_leer_la_pagina_1_2_3_las',[i+1,pages.length,error.message]));}
    }
    await browser.storage.local.set({operation:tx('bg_1_2_paginas_recibidas_preparando_el_cont',[pages.length,pages.length]),operationProgress:null});
    let result=await native({action:'reader_finish',job:begin.job});
    result=await native({action:'source_context',id:result.id,source_context:c.source_context});
    return await adoptMedia(result,c.source);
  }catch(error){failure=error;throw error;}
  finally{
    for(const frameId of [...frames].reverse())await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.end();void 0;'}).catch(()=>{});
    readingBook=false;
    await endWork(work,failure);
  }
}

async function inspectFrame(message){
  const {currentCapture}=await browser.storage.local.get('currentCapture');
  const c=captureForToken(message.token)||currentCapture;
  if(!c?.source?.tabId)throw new Error(tx('bg_vuelve_a_detectar_la_pagina_del_curso'));
  const tab=await browser.tabs.get(c.source.tabId);
  return capture(tab);
}

browser.tabs.onRemoved.addListener(tabId=>{
  clearReviewTab(tabId);
  for(const [key,value] of tabCaptures)if(value.currentCapture?.source?.tabId===tabId)tabCaptures.delete(key);
});
browser.browserAction.onClicked.addListener(tab => {
  openSidebar(tab);
  if(workClaim||globalThis.AnacoObBatch?.busy()||tab.url?.startsWith(browser.runtime.getURL('')))return;
  capture(tab).catch(error => browser.storage.local.set({operationError: error.message}));
});
browser.commands.onCommand.addListener(async command => {
  if (command !== "capture-page") return;
  openSidebar();
  const [tab] = await browser.tabs.query({active:true,currentWindow:true});
  if(workClaim||globalThis.AnacoObBatch?.busy()||tab.url?.startsWith(browser.runtime.getURL('')))return;
  bindPanel(tab);
  capture(tab).catch(error => browser.storage.local.set({operationError:error.message}));
});
browser.menus.create({id: "quote", title: tx('bg_guardar_frase_con_anaco'), contexts: ["selection"]});
browser.menus.create({id: "image", title: tx('bg_guardar_imagen_con_anaco'), contexts: ["image"]});
globalThis.addEventListener?.('storage',event=>{
  if(event.key!=='anaco-ob:lang')return;
  browser.menus.update("quote",{title:tx('bg_guardar_frase_con_anaco')});
  browser.menus.update("image",{title:tx('bg_guardar_imagen_con_anaco')});
});
browser.menus.onClicked.addListener((info, tab) => {
  openSidebar(tab);
  if(workClaim||globalThis.AnacoObBatch?.busy())return;
  capture(tab, {kind: info.menuItemId, selection: info.selectionText, src: info.srcUrl})
    .catch(error => browser.storage.local.set({operationError:error.message}));
});
let mediaRefreshTimer;
function queueMediaRefresh(tabId){
  clearTimeout(mediaRefreshTimer);
  mediaRefreshTimer=setTimeout(async()=>{
    try{
      const {pageContext,currentCapture}=await browser.storage.local.get(['pageContext','currentCapture']);
      if(workClaim||globalThis.AnacoObBatch?.busy()||readingBook||pageContext?.tabId!==tabId||currentCapture?.id||currentCapture?.reader||pageContext.status==='loading')return;
      const tab=await browser.tabs.get(tabId);
      if(tab.active)await capture(tab,{}, {automatic:true});
    }catch{ /* The user may have closed or navigated away from this page. */ }
  },700);
}
browser.webNavigation.onCompleted.addListener(details=>{if(details.frameId!==0)queueMediaRefresh(details.tabId);});
browser.runtime.onMessage.addListener((message, sender) => {
  if(sender.id===browser.runtime.id&&sender.tab&&message.type==='pageMediaChanged'){
    queueMediaRefresh(sender.tab.id);
    return;
  }
  if (sender.id !== browser.runtime.id || !sender.url?.startsWith(browser.runtime.getURL(""))) return;
  if(message.type==='panelCapture')return panelCapture(message.windowId);
  if(message.type==='batchStart')return AnacoObBatch.start(message);
  if(message.type==='courseStart')return AnacoObCourses.start(message);
  if(message.type==='courseStop')return AnacoObCourses.stop();
  if(message.type==='courseResume')return AnacoObCourses.resume(message.windowId);
  if(message.type==='courseSelect')return AnacoObCourses.select(message.ids||[]);
  if(message.type==='batchReviewContext')return AnacoObBatch.reviewContext(message.id);
  if(message.type==='batchRemove')return AnacoObBatch.remove(message.id);
  if(message.type==='batchClear')return AnacoObBatch.clear(message.failedOnly);
  if(message.type==='batchRetryFailed')return AnacoObBatch.retryFailed(message.windowId);
  if(message.type==='batchRestartVideos')return AnacoObBatch.restartVideos(message.windowId);
  if(message.type==='batchPause')return AnacoObBatch.pause();
  if(message.type==='batchResume')return AnacoObBatch.resume(message.id,message.windowId);
  if(AnacoObBatchBusy() && ['prepare','importResource','extractReader','inspectFrame','beginUploadWork','resumeJob','resume','redraft','revise','proposeSplit','refreshConnections','discardPending','captureActive','capturePdfActive'].includes(message.type))return Promise.reject(new Error(tx('batch_busy')));
  if(message.type==='cancelWork'&&AnacoObBatchBusy())return AnacoObBatch.pause(true);
  if (message.type === "native") return native(message.message);
  if (message.type === 'reviewStatus') return reviewStatus(message,sender);
  if (message.type === 'reviewCommand') return reviewCommand(message);
  if (message.type === 'openOptions') return openOptions(message.windowId);
  if (message.type === 'returnFromOptions') return returnFromOptions(sender);
  if (message.type === 'sidebarPolicy') return allowSidebar(message.windowId);
  if (message.type === "extractReader") return extractReader(message,captureForToken(message.token)).then(c=>message.prepareAfter?prepare({token:c.token,images:c.images.map((_,i)=>i),provider:message.provider,intent:message.intent,note_structure:message.note_structure},c):c);
  if (message.type === "prepare") return prepare(message,captureForToken(message.token));
  if (message.type === "importResource") return importResource(message,captureForToken(message.token)).then(c=>message.prepareAfter?prepare({token:c.token,images:c.images.map((_,i)=>i),provider:message.provider,intent:message.intent,note_structure:message.note_structure},c):c);
  if (message.type === "inspectFrame") return inspectFrame(message);
  if(message.type==='beginUploadWork')return (async()=>{
    const {operation,currentCapture}=await browser.storage.local.get(['operation','currentCapture']);
    if(operation||workClaim)throw new Error(tx('bg_ya_hay_un_trabajo_en_curso'));
    const tab=message.manual?(sender.tab||(await browser.tabs.query({url:sender.url}))[0]):null;
    const source=message.manual?{tabId:tab?.id,windowId:tab?.windowId,url:sender.url,session:SESSION}:currentCapture?.source||await sourceForImport();
    const work=await beginWork({...currentCapture,title:message.name,source},tx('bg_transfiriendo_archivo'),!message.manual&&Boolean(currentCapture));
    return {work,source};
  })();
  if(message.type==='failWork')return endWork(message.work,new Error(message.error));
  if(message.type==='cancelWork')return cancelWork();
  if(message.type==='discardPending')return discardPending(message);
  if(message.type==='resumeJob')return (async()=>{
    if(workClaim||pendingDiscard)throw new Error(tx('bg_ya_hay_un_trabajo_en_curso'));
    const request=await native({action:'resume_job',job:message.job});const {workSources={}}=await browser.storage.local.get('workSources');const info=workSources[message.job]||{title:tx('bg_trabajo_recuperado')};
    const work=await beginWork({...info,source:info.source},tx('bg_reanudando_el_trabajo'),false);
    try{
      const result=await native(request,7200000);
      if(request.action==='draft'){result.capture.source=info.source;await publishCapture(result.capture,result);await openReview(result.capture.id,{automatic:true,source:info.source});}
      else await adoptMedia(result,info.source||{url:result.url});
      await native({action:'finish_job',job:message.job,status:'complete'});await endWork(work);return result;
    }catch(error){await endWork(work,error);throw error;}
  })();
  if(message.type==='revise'||message.type==='proposeSplit'||message.type==='refreshConnections')return (async()=>{
    const splitting=message.type==='proposeSplit';
    const connecting=message.type==='refreshConnections';
    if(connecting){for(let i=0;workClaim&&i<100;i++)await new Promise(resolve=>setTimeout(resolve,50));}
    const c=await native({action:'load',id:message.id});
    const {sources={},currentCapture:current}=await browser.storage.local.get(['sources','currentCapture']);
    const source=sources[c.id]||(current?.id===c.id?current.source:null)||{url:c.url};
    const work=await beginWork({...c,source,token:current?.id===c.id?current.token:undefined},connecting?tx('bg_buscando_conexiones_por_tema_en_tu_secon'):splitting?tx('bg_estudiando_una_posible_division_de_la_no'):tx('bg_preparando_una_revision_del_apartado'),connecting);
    try{const result=await native({...message,action:connecting?'refresh_links':splitting?'propose_split':'revise'});await endWork(work);return result;}catch(error){await endWork(work,error);throw error;}
  })();
  // Prepare a reviewed video again, as a conversation or as a plain video.
  if(message.type==='redraft')return (async()=>{
    const c=await native({action:'load',id:message.id});
    const {sources={},currentCapture:current}=await browser.storage.local.get(['sources','currentCapture']);
    const source=sources[c.id]||(current?.id===c.id?current.source:null)||{url:c.url};
    return prepare({intent:c.intent,provider:message.provider,images:c.selected_images,note_structure:c.note_structure,conversation:message.conversation},{...c,source,token:current?.id===c.id?current.token:undefined});
  })();
  if(message.type==='splitDecision')return native({...message,action:'split_decision'});
  if (message.type === "adoptUpload") return (async()=>{
    if(message.work!==workClaim)throw new Error(tx('bg_la_transferencia_ya_no_pertenece_al_trab'));
    const {activeWork}=await browser.storage.local.get('activeWork');
    try{const result=await adoptMedia(message.capture,activeWork.source);await endWork(message.work);return message.prepareAfter?prepare({token:result.token,images:result.images.map((_,i)=>i),provider:message.provider,intent:message.intent,note_structure:message.note_structure},result):result;}
    catch(error){await endWork(message.work,error);throw error;}
  })();
  if (message.type === "locateImage") return locateImage(message);
  if (message.type === "openReview") return openReview(message.id);
  if (message.type === "reviewData") return reviewData(message.id);
  if (message.type === "finishReview") return finishReview(message,sender);
  if (message.type === "detectActive") return detectActive(message);
  if (message.type === "captureActive") return browser.tabs.query({active:true,currentWindow:true}).then(([tab]) => capture(tab, message.input));
  if (message.type === "capturePdfActive") return browser.tabs.query({active:true,currentWindow:true}).then(([tab]) => capturePdf(tab));
  if (message.type === "resume") return resumeCapture(message);
});

function AnacoObBatchBusy(){return Boolean(globalThis.AnacoObBatch?.busy());}
