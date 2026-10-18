/* The background owns in-flight requests so closing the sidebar doesn't cancel them. */
const HOST = "org.samuh.anaco_ob";
const SESSION = crypto.randomUUID();
// Keep return targets in this browser session; never reuse tab IDs after restart.
const optionsSources = new Map();
const reviewSessions={};
browser.storage.local.set({reviewSessions:{}});
async function reviewStatus(message,sender){
  const expected=browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(message.id);
  if(!sender.tab||sender.url!==expected)return;
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
  if(!session||session.windowId!==message.windowId)throw new Error('Esa revisión ya no está abierta en esta ventana.');
  const commands=['focus','note','include','read','edit','properties','connections','refreshLinks','split','save'];
  if(!commands.includes(message.command))throw new Error('Acción de revisión no disponible.');
  const tab=await browser.tabs.get(session.tabId);
  if(tab.url!==browser.runtime.getURL('review.html')+'?capture='+encodeURIComponent(message.id)){await clearReviewTab(tab.id);throw new Error('La revisión se cerró.');}
  await browser.tabs.update(tab.id,{active:true});
  if(message.command==='focus')return true;
  const pending=browser.runtime.sendMessage({type:'reviewControl',id:message.id,instance:session.instance,command:message.command,note:message.note,value:message.value});
  if(message.command==='save'){pending.catch(()=>{});return true;}
  return pending;
}
browser.tabs.onRemoved.addListener(id => optionsSources.delete(id));
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
// Close the sidebar Firefox inherits into a new window, keeping explicit opens.
const knownSidebarWindows=new Set(),inheritedSidebarWindows=new Set();
const sidebarInitialization=browser.windows?.getAll?browser.windows.getAll({windowTypes:['normal']}).then(windows=>{for(const w of windows)knownSidebarWindows.add(w.id);}):Promise.resolve();
let sidebarOpening=Promise.resolve();
browser.windows?.onCreated?.addListener(w=>{if(!knownSidebarWindows.has(w.id)){knownSidebarWindows.add(w.id);inheritedSidebarWindows.add(w.id);}});
browser.windows?.onRemoved?.addListener(id=>{knownSidebarWindows.delete(id);inheritedSidebarWindows.delete(id);});
function openSidebar(tab){
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
function checkWork(){if(workClaim&&cancelledWork.has(workClaim))throw new Error('Trabajo cancelado. Puedes reanudarlo desde Trabajos recuperables.');}
const requests = new Map();
browser.storage.local.get(["operation","activeWork"]).then(({operation,activeWork}) => {
  if (operation||activeWork) browser.storage.local.set({activeWork:null,operation:"",operationError:"La preparación anterior se interrumpió. Puedes recuperar la captura en Pendientes y reintentar."});
});
function native(message, timeoutMs=2400000) {
  return new Promise((resolve, reject) => {
    if(['capture','draft','revise','propose_split','refresh_links','upload_begin','upload_chunk','upload_finish','video_url','subtitles'].includes(message.action)||message.action?.startsWith('reader_'))try{checkWork();}catch(error){reject(error);return;}
    if (!port) {
      port = browser.runtime.connectNative(HOST);
      port.onMessage.addListener(response => {
        const pending = requests.get(response.requestId);
        if (!pending) return;
        if(response.progress){if(pending.workId===workClaim){const p=response.progress;browser.storage.local.set({operation:typeof p==='string'?p:p.message,operationProgress:typeof p==='object'?{...p,updatedAt:Date.now()}:null});}return;}
        clearTimeout(pending.timer); requests.delete(response.requestId);
        response.ok ? pending.resolve(response.result) : pending.reject(new Error(response.error));
      });
      port.onDisconnect.addListener(() => {
        const error = port?.error?.message || "No se pudo conectar con el servicio local. Ejecuta scripts/install.py.";
        port = null;
        for (const pending of requests.values()) { clearTimeout(pending.timer); pending.reject(new Error(error)); }
        requests.clear();
      });
    }
    const requestId = crypto.randomUUID();
    const timer = setTimeout(() => {requests.delete(requestId); reject(new Error("El servicio está tardando demasiado. La captura se conserva en Pendientes."));}, timeoutMs);
    requests.set(requestId, {resolve, reject, timer,workId:workClaim});
    try { port.postMessage({...message, requestId,task:workClaim}); } catch (error) { clearTimeout(timer); requests.delete(requestId); reject(error); }
  });
}

async function beginWork(c,operation,showCapture=true){
  if(workClaim)throw new Error('Ya hay un trabajo en curso. Puedes seguir navegando mientras termina.');
  const id=crypto.randomUUID();workClaim=id;++detectionSequence;
  if(typeof AbortController==='function')workAbortControllers.set(id,new AbortController());
  const activeWork={id,title:c.title||'Captura',source:c.source||{url:c.url},captureToken:c.token,captureId:c.id,startedAt:Date.now()};
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
  const id=workClaim;cancelledWork.add(id);await browser.storage.local.set({operation:'Cancelando el trabajo y conservando el avance…'});
  workAbortControllers.get(id)?.abort();
  for(const r of workResources.get(id)||[])browser.tabs.executeScript(r.tabId,{frameId:r.frameId,code:`AnacoObResource.close(${JSON.stringify(r.job)});void 0;`}).catch(()=>{});
  const result=await browser.runtime.sendNativeMessage(HOST,{action:'cancel_job',job:id});if(!result.ok)throw new Error(result.error);
}

const tabCaptures = new Map();
let detectionSequence = 0;
const keyFor = tab => `${tab.id}:${tab.url}`;
const sourceFor = tab => ({tabId:tab.id, windowId:tab.windowId, url:tab.url, session:SESSION});
function pdfCapture(tab) {
  return {kind:"pdf",url:tab.url,title:tab.title||"Documento PDF",text:"",images:[],warnings:[],documents:[{url:tab.url,title:tab.title||"PDF"}],videos:[],frames:[],contentReady:false,requiredOrigins:[]};
}
async function readFrame(tabId, frameId, input = {}) {
  const target = {frameId, matchAboutBlank:true};
  await browser.tabs.executeScript(tabId, {...target, file:"surfaces.js"});
  await browser.tabs.executeScript(tabId, {...target, file:"media-source.js"});
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
async function scanTab(tab, input = {}) {
  if (AnacoObDetection.pdfURL(tab.url)) return pdfCapture(tab);
  const pages = [], blocked = [];
  try { pages.push(await readFrame(tab.id, 0, input)); }
  catch {
    const granted = await browser.permissions.contains({origins:[AnacoObDetection.origin(tab.url)].filter(Boolean)});
    if (granted && await probePDF(tab.url)) return pdfCapture(tab);
    blocked.push({url:tab.url,title:tab.title||'Página actual',needsPermission:!granted});
  }
  if (input.kind === 'quote' || input.kind === 'image') return pages[0];
  const all = await browser.webNavigation.getAllFrames({tabId:tab.id}).catch(() => []);
  // Read each frame independently. One denied domain must not hide other frames.
  const frames = (all || []).filter(f => f.frameId !== 0 && !f.errorOccurred &&
    !/doubleclick|recaptcha|googlesyndication/i.test(f.url)).slice(0,40);
  const results = await Promise.allSettled(frames.map(async frame => {
    if (AnacoObDetection.pdfURL(frame.url)) return {kind:'pdf',url:frame.url,frameId:frame.frameId,documents:[{url:frame.url,title:'PDF del curso'}]};
    try { return {...await readFrame(tab.id, frame.frameId),parentFrameId:frame.parentFrameId}; }
    catch {
      const origin=AnacoObDetection.origin(frame.url);
      const granted=origin&&await browser.permissions.contains({origins:[origin]});
      if(granted&&await probePDF(frame.url))return {kind:'pdf',url:frame.url,frameId:frame.frameId,documents:[{url:frame.url,title:'PDF del visor'}]};
      return {blocked:true,url:frame.url,title:'Contenido incrustado',needsPermission:!granted,frameId:frame.frameId,reason:granted?'script-unreadable':'permission-required'};
    }
  }));
  for (const result of results) if (result.status === 'fulfilled') {
    if (result.value.blocked) { if (AnacoObDetection.origin(result.value.url)) blocked.push(result.value); }
    else pages.push(result.value);
  }
  // The live navigation tree is authoritative. An iframe's src can still be
  // its launch URL after a redirect, so it is not evidence of denied access.
  const unmatched=pages.flatMap(p=>(p.frames||[]).filter(f=>!all?.some(live=>live.url===f.url))).length;

  return AnacoObDetection.merge(pages, tab, blocked, {frameReferencesUnmatched:unmatched});
}
let activeDetection;
function capture(tab,input={},options={}){
  const key=tab?keyFor(tab)+JSON.stringify(input):'';
  if(activeDetection?.key===key)return activeDetection.promise;
  const promise=performCapture(tab,input,options).finally(()=>{if(activeDetection?.promise===promise)activeDetection=null;});
  activeDetection={key,promise};
  return promise;
}
async function performCapture(tab, input = {}, {automatic = false, fresh = true} = {}) {
  if (automatic && tab?.url?.startsWith(browser.runtime.getURL(''))) return null;
  if(workClaim){if(automatic)return (await browser.storage.local.get('currentCapture')).currentCapture;throw new Error('La captura actual sigue procesándose. Puedes cambiar de pestaña mientras termina.');}
  const sequence = ++detectionSequence;
  if (!tab?.id || !/^(https?:|file:)/.test(tab.url || '')) {
    if (automatic && tab?.url?.startsWith(browser.runtime.getURL(''))) return null;
    await browser.storage.local.set({currentCapture:null,draftResult:null,pageContext:{tabId:tab?.id,url:tab?.url,status:'error',error:'Esta pestaña no contiene una página web que se pueda capturar.'}});
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
    const result = await Promise.race([scanTab(tab,input), new Promise((_,reject) => {timer=setTimeout(() => reject(new Error('No se pudo terminar la detección. Espera a que cargue el contenido y vuelve a intentarlo.')),12000);})]).finally(()=>clearTimeout(timer));
    if (!result) throw new Error('No se pudo leer el contenido seleccionado. Vuelve a capturarlo desde la página.');
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
  const tab = Number.isInteger(message.tabId)?await browser.tabs.get(message.tabId).catch(()=>null):(await browser.tabs.query({active:true,...(Number.isInteger(message.windowId)?{windowId:message.windowId}:{currentWindow:true})}))[0];
  if(!tab)return null;
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
    if (Number(response.headers.get("content-length")) > 3000000) throw new Error("supera 3 MB");
    const reader = response.body.getReader();
    const parts = []; let size = 0;
    while (true) { const {value, done} = await reader.read(); if (done) break; size += value.length; if (size > 3000000) {await reader.cancel(); throw new Error("supera 3 MB");} parts.push(value); }
    const bytes = new Uint8Array(size); let offset = 0; for (const part of parts) {bytes.set(part,offset); offset += part.length;}
    let binary = ""; for (let i=0; i<bytes.length; i+=8192) binary += String.fromCharCode(...bytes.subarray(i,i+8192));
    return {...image, data: btoa(binary)};
  } finally { clearTimeout(timer);workSignal?.removeEventListener('abort',abort); }
}

async function prepare(message,ownedCapture=null) {
  const {operation,currentCapture:capture}=await browser.storage.local.get(['operation','currentCapture']);
  if(operation||workClaim)throw new Error('Ya hay una nota preparándose.');
  let c=ownedCapture||capture;
  if(!c)throw new Error('Primero captura una página, frase o imagen.');
  if(message.token&&c.token!==message.token)throw new Error('La pestaña cambió antes de preparar la nota. Revisa la captura actual y reintenta.');
  if(!c.id&&(c.reader||c.kind==='pdf'||!AnacoObDetection.usable(c)))throw new Error('Primero extrae el documento detectado.');
  c={...c,intent:message.intent||'',selected_images:message.images||c.selected_images};
  const work=await beginWork(c,'Preparando la propuesta…');
  try {
    let selected=message.images;
    if (!c.id) {
      const images = [];
      const warnings = [...c.warnings];
      if(c.reader&&(message.images||[]).length<c.images.length)warnings.push(`Lector HTML: se han elegido ${(message.images||[]).length} de ${c.images.length} páginas/figuras detectadas para lectura visual. La selección no representa una lectura visual del libro entero.`);
      for (const index of message.images || []) {
        try { images.push(await imageData(c.images[index])); }
        catch (e) { warnings.push("No se pudo conservar una imagen: " + e.message + ". Vuelve a capturar para reintentar."); }
      }
      if (c.kind === "image" && !images.length) throw new Error("No se pudo descargar la imagen. Esta versión admite PNG, JPEG, GIF y WebP accesibles desde el navegador.");
      const source = c.source, token = c.token;
      c = {...await native({action: "capture", capture: {...c, images, warnings}}), source, token};
      selected=c.images.map((_,index)=>index);
      const {sources={}} = await browser.storage.local.get("sources");
      sources[c.id] = source || {url:c.url};
      await browser.storage.local.set({sources});
      await publishCapture(c);
    }
    const result = await native({action: "draft", id: c.id, intent: message.intent, provider: message.provider,images:selected,note_structure:message.note_structure},c.reader?.job?7200000:2400000);
    localStorage.removeItem("editor:" + c.id);
    result.capture.source = c.source;
    result.capture.token = c.token;
    await publishCapture(result.capture, result);
    await browser.storage.local.set({editorFields:null});
    await openReview(c.id,{automatic:true,source:c.source});
    await endWork(work);
    return result;
  } catch (error) {
    await endWork(work,error); throw error;
  }
}

async function openReview(id,{automatic=false,source}={}) {
  const c = await native({action:"load",id});
  if (!c.draft || c.status !== "draft") throw new Error("Esta captura no tiene una propuesta pendiente de revisión.");
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
  if(!source?.tabId || source.session!==SESSION)throw new Error("Vuelve a capturar el artículo para localizar sus imágenes.");
  const image=c.images[message.index];
  const frameId=image?.frameId||0;
  if(!message.clear&&!image)return {found:false};
  try {
    await browser.tabs.executeScript(source.tabId,{file:"locate.js",frameId,matchAboutBlank:true});
    if(sequence!==locateSequence)return {found:false};
    const input=message.clear?{clear:true}:{imageId:image.imageId,url:image.url,index:message.index};
    const [result]=await browser.tabs.executeScript(source.tabId,{code:`globalThis.AnacoObLocateImage(${JSON.stringify(input)})`,frameId,matchAboutBlank:true});
    return result;
  } catch {throw new Error("No puedo localizar la imagen. Comprueba que el artículo sigue abierto y vuelve a capturarlo si ha cambiado.");}
}

async function reviewData(id) {
  return native({action:'review_data',id});
}

async function finishReview(message,sender) {
  const expected=browser.runtime.getURL("review.html")+"?capture="+encodeURIComponent(message.id);
  if(!sender.tab || sender.url!==expected)throw new Error("Esta acción debe iniciarse en la página de revisión de la captura.");
  const c=await native({action:"load",id:message.id});
  let result;
  if(message.decision==="save")result=await native({action:"save",id:message.id,fields:message.fields});
  else if(message.decision==="discard")result=await native({action:"discard",id:message.id});
  else if(message.decision!=="back")throw new Error("Acción de revisión desconocida.");
  if(message.decision!=="back"){
    localStorage.removeItem("editor:"+message.id);
    for (const [key,value] of tabCaptures) if(value.currentCapture?.id===message.id)tabCaptures.delete(key);
    const {currentCapture:current}=await browser.storage.local.get("currentCapture");
    if(current?.id===message.id)await browser.storage.local.set({currentCapture:null,draftResult:null,operationError:"",lastResult:message.decision==="save"?result:null});
  }
  const {sources={},reviews={}}=await browser.storage.local.get(["sources","reviews"]);
  const source=sources[message.id]||{url:c.url};
  try {
    let target;
    if(source.session===SESSION&&Number.isInteger(source.tabId)){
      try{target=await browser.tabs.get(source.tabId);}catch{}
    }
    if(target){await browser.tabs.update(target.id,{active:true});await browser.windows.update(target.windowId,{focused:true});}
    else{const url=source.url||c.url;await browser.tabs.create({url:/^https?:/.test(url)?url:browser.runtime.getURL("panel.html"),active:true});}
    delete reviews[message.id];await browser.storage.local.set({reviews});
    await browser.tabs.remove(sender.tab.id);
  } catch(error) {return {result,completed:message.decision!=="back",returnError:"La operación terminó, pero no pude volver al artículo: "+error.message};}
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
  const same=diagnostic.attempts.find(v=>v.context===value.context&&v.host===value.host&&v.status===value.status&&v.reason===value.reason);
  if(same)same.count++;else if(diagnostic.attempts.length<16)diagnostic.attempts.push({...value,count:1});
}
async function resourceBytes(url,source,frameId=0,maxBytes=100000000,diagnostic){
  checkWork();const owner=workClaim;const host=resourceHost(url);let frameError;
  if(Number.isInteger(source?.tabId)){
    const target={frameId,matchAboutBlank:true};let job,phase='frame-access';
    try{
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
          size+=bytes.length;if(size>maxBytes)throw new Error('El recurso supera el límite de descarga.');parts.push(bytes);
        }
        return {parts,size,url:opened.url};
      }
    }catch(error){frameError=error;resourceAttempt(diagnostic,{context:'player',host,reason:phase,error:error.name||'Error'});}
    finally{if(job){await browser.tabs.executeScript(source.tabId,{...target,code:`AnacoObResource.close(${JSON.stringify(job)});void 0;`}).catch(()=>{});if(owner)workResources.set(owner,(workResources.get(owner)||[]).filter(v=>v.job!==job));}}
    if(frameError?.message?.includes('límite de descarga'))throw frameError;
  }
  // A CDN may allow the extension but reject page CORS. Try its authorized read.
  let response;
  const workSignal=workAbortControllers.get(workClaim)?.signal;
  try{response=await fetch(url,{credentials:'include',signal:workSignal?AbortSignal.any([workSignal,AbortSignal.timeout(30000)]):AbortSignal.timeout(30000)});}
  catch{
    resourceAttempt(diagnostic,{context:'extension',host,reason:'network-or-cors'});
    throw new Error('No se pudo leer el recurso del reproductor. Vuelve a iniciar el vídeo y a detectar su contenido; el diagnóstico incluye los intentos de descarga.');
  }
  resourceAttempt(diagnostic,{context:'extension',host,status:response.status,reason:''});
  if(!response.ok)throw new Error(`El servidor rechazó el recurso del reproductor (HTTP ${response.status}). Se ha intentado conservar la sesión del vídeo. Inícialo y vuelve a detectar para renovar su enlace.`);
  const type=response.headers.get('content-type')||'';
  if(/text\/html|application\/xhtml/i.test(type))throw new Error('El recurso devolvió una página de acceso en lugar del vídeo o los subtítulos. Abre la lección y vuelve a detectar.');
  if(Number(response.headers.get('content-length'))>maxBytes){await response.body?.cancel();throw new Error('El recurso supera el límite de descarga.');}
  let size=0;const parts=[],reader=response.body.getReader();
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>maxBytes){await reader.cancel();throw new Error('El recurso supera el límite de descarga.');}parts.push(value);}
  return {parts,size,url:response.url||url};
}
async function subtitleText(url, source, frameId=0,diagnostic){
  const result=await resourceBytes(url,source,frameId,5000000,diagnostic);
  return new TextDecoder().decode(await new Blob(result.parts).arrayBuffer());
}
async function importResource(message){
  const {operation,currentCapture}=await browser.storage.local.get(['operation','currentCapture']);
  if(operation)throw new Error('Ya hay un recurso procesándose. Puedes cambiar de pestaña mientras termina.');
  if(message.token&&currentCapture?.token!==message.token)throw new Error('La pestaña cambió antes de extraer el recurso. Revisa el contenido actual y reintenta.');
  const source=currentCapture?.source||await sourceForImport();
  const diagnostic={kind:message.kind,frameId:message.frameId||0,playerHost:resourceHost(message.frameURL||source?.url),resourceHost:resourceHost(message.url),attempts:[]};
  const work=await beginWork(currentCapture||{title:message.title||'Recurso',source},message.kind==='pdf'?'Extrayendo el PDF…':'Recuperando subtítulos o audio…',Boolean(currentCapture));
  try{
    let c;
    if(message.kind==="subtitles"||message.kind==="subtitle-url"){
      try{
        const text=message.kind==='subtitles'?message.text:await subtitleText(message.url,source,message.frameId||0,diagnostic);
        c=await native({action:"subtitles",url:message.pageUrl,title:message.title,text});
      }catch(error){
        if(!message.fallback)throw error;
        await browser.storage.local.set({operation:'Los subtítulos no están disponibles. Recuperando el audio para transcribirlo…'});
        message={...message,...message.fallback};diagnostic.kind=message.kind;diagnostic.resourceHost=resourceHost(message.url);
      }
    }
    if(!c&&message.kind==="video-platform")c=await native({action:"video_url",url:message.url});
    else if(!c){
      await browser.storage.local.set({operation:message.kind==='pdf'?'Descargando el PDF…':'Descargando el recurso del reproductor…',operationProgress:{stage:'download',message:'Descargando el recurso del reproductor…'}});
      let parts=[],size=0;
      if(message.kind==='video-hls'){
        const {config}=await native({action:'settings'});
        ({parts,size}=await AnacoObStream.download(message.url,{load:(url,limit)=>resourceBytes(url,source,message.frameId||0,limit,diagnostic),maxSeconds:config.video_minutes*60,onProgress:(n,total)=>{
          if(n===1||n===total||n%10===0)browser.storage.local.set({operation:`Recuperando vídeo del curso: segmento ${n} de ${total}…`});
        }}));
      }else{
        ({parts,size}=await resourceBytes(message.url,source,message.frameId||0,100000000,diagnostic));
      }
      const begin=await native({action:"upload_begin",name:message.name||(message.kind==="pdf"?"documento.pdf":"video.mp4"),size,url:message.pageUrl||message.url});let offset=0;
      for(const bytes of parts){for(let start=0;start<bytes.length;start+=393216){const piece=bytes.subarray(start,start+393216);let binary="";for(let i=0;i<piece.length;i+=8192)binary+=String.fromCharCode(...piece.subarray(i,i+8192));await native({action:"upload_chunk",upload:begin.upload,offset,data:btoa(binary)});offset+=piece.length;}}
      await browser.storage.local.set({operation:message.kind==='pdf'?'Leyendo las páginas del PDF…':'Preparando el archivo de audio…',operationProgress:null});
      c=await native({action:"upload_finish",upload:begin.upload,pages:message.pages||""});
    }
    const adopted=await adoptMedia(c,source);
    await endWork(work);return adopted;
  }catch(error){await browser.storage.local.set({operationDiagnostic:diagnostic});await endWork(work,error);throw error;}
}

let readingBook=false;
async function extractReader(message){
  const {currentCapture:c,operation}=await browser.storage.local.get(['currentCapture','operation']);
  if(operation||readingBook)throw new Error('Ya hay una extracción o una nota en curso.');
  if(!c?.reader||c.token!==message.token)throw new Error('El lector cambió. Vuelve a detectarlo.');
  if(c.reader.overflow)throw new Error('El libro supera las 500 páginas admitidas en esta versión. No se ha extraído una parte.');
  const frames=[...new Set([0,...c.reader.frames,...(c.detection?.frameDetails||[]).map(f=>f.id).filter(Number.isInteger)])];
  const work=await beginWork(c,'Preparando la extracción del libro completo…');
  let failure=null;
  readingBook=true;
  try{
    const pages=[];
    for(const frameId of c.reader.frames){
      const [inventory]=await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.inventory(globalThis.AnacoObReaderRoot||document.body)'});
      if(inventory.overflow)throw new Error('El libro supera el límite de 500 páginas.');
      pages.push(...inventory.pages.map(p=>({...p,frameId})));
    }
    if(!pages.length)throw new Error('No se localizaron páginas del lector.');
    if(pages.length>500)throw new Error('El libro supera el límite de 500 páginas.');
    for(const frameId of frames)await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.start();void 0;'}).catch(()=>{});
    const identity=c.token+':'+pages.map(p=>p.id).join(',');
    const {readerJobs={}}=await browser.storage.local.get('readerJobs');
    const saved=readerJobs[c.token];
    const begin=await native({action:'reader_begin',count:pages.length,url:c.url,title:c.title,context:c.text,identity,job:saved?.identity===identity?saved.job:undefined});
    readerJobs[c.token]={job:begin.job,identity};await browser.storage.local.set({readerJobs});
    const done=new Set(begin.done);
    for(let i=0;i<pages.length;i++){
      if(done.has(i+1))continue;
      await browser.storage.local.set({operation:`Extrayendo página ${i+1} de ${pages.length}…`});
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
      }catch(error){throw new Error(`No se ha podido leer la página ${i+1}/${pages.length}: ${error.message}. Las páginas recibidas se conservan; vuelve a pulsar Extraer libro completo para continuar.`);}
    }
    await browser.storage.local.set({operation:`${pages.length}/${pages.length} páginas recibidas. Preparando el contenido…`});
    const result=await native({action:'reader_finish',job:begin.job});
    return await adoptMedia(result,c.source);
  }catch(error){failure=error;throw error;}
  finally{
    for(const frameId of [...frames].reverse())await browser.tabs.executeScript(c.source.tabId,{frameId,matchAboutBlank:true,code:'AnacoObSurfaces.end();void 0;'}).catch(()=>{});
    readingBook=false;
    await endWork(work,failure);
  }
}

async function inspectFrame(message){
  const {currentCapture:c}=await browser.storage.local.get('currentCapture');
  if(!c?.source?.tabId)throw new Error('Vuelve a detectar la página del curso.');
  const tab=await browser.tabs.get(c.source.tabId);
  return capture(tab);
}

browser.tabs.onRemoved.addListener(tabId=>{
  clearReviewTab(tabId);
  for(const [key,value] of tabCaptures)if(value.currentCapture?.source?.tabId===tabId)tabCaptures.delete(key);
});
browser.browserAction.onClicked.addListener(tab => {
  openSidebar(tab);
  if(tab.url?.startsWith(browser.runtime.getURL(''))||Object.values(reviewSessions).some(r=>r.windowId===tab.windowId))return;
  capture(tab).catch(error => browser.storage.local.set({operationError: error.message}));
});
browser.commands.onCommand.addListener(async command => {
  if (command !== "capture-page") return;
  openSidebar();
  const [tab] = await browser.tabs.query({active:true,currentWindow:true});
  if(tab.url?.startsWith(browser.runtime.getURL(''))||Object.values(reviewSessions).some(r=>r.windowId===tab.windowId))return;
  capture(tab).catch(error => browser.storage.local.set({operationError:error.message}));
});
browser.menus.create({id: "quote", title: "Guardar frase con Anaco", contexts: ["selection"]});
browser.menus.create({id: "image", title: "Guardar imagen con Anaco", contexts: ["image"]});
browser.menus.onClicked.addListener((info, tab) => {
  openSidebar(tab);
  capture(tab, {kind: info.menuItemId, selection: info.selectionText, src: info.srcUrl})
    .catch(error => browser.storage.local.set({operationError:error.message}));
});
let mediaRefreshTimer;
function queueMediaRefresh(tabId){
  clearTimeout(mediaRefreshTimer);
  mediaRefreshTimer=setTimeout(async()=>{
    try{
      const {pageContext,currentCapture}=await browser.storage.local.get(['pageContext','currentCapture']);
      if(workClaim||readingBook||pageContext?.tabId!==tabId||currentCapture?.id||currentCapture?.reader||pageContext.status==='loading')return;
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
  if (message.type === "native") return native(message.message);
  if (message.type === 'reviewStatus') return reviewStatus(message,sender);
  if (message.type === 'reviewCommand') return reviewCommand(message);
  if (message.type === 'openOptions') return openOptions(message.windowId);
  if (message.type === 'returnFromOptions') return returnFromOptions(sender);
  if (message.type === 'sidebarPolicy') return allowSidebar(message.windowId);
  if (message.type === "extractReader") return extractReader(message).then(c=>message.prepareAfter?prepare({token:c.token,images:c.images.map((_,i)=>i),provider:message.provider,intent:message.intent,note_structure:message.note_structure},c):c);
  if (message.type === "prepare") return prepare(message);
  if (message.type === "importResource") return importResource(message).then(c=>message.prepareAfter?prepare({token:c.token,images:c.images.map((_,i)=>i),provider:message.provider,intent:message.intent,note_structure:message.note_structure},c):c);
  if (message.type === "inspectFrame") return inspectFrame(message);
  if(message.type==='beginUploadWork')return (async()=>{
    const {operation,currentCapture}=await browser.storage.local.get(['operation','currentCapture']);
    if(operation||workClaim)throw new Error('Ya hay un trabajo en curso.');
    const tab=message.manual?(sender.tab||(await browser.tabs.query({url:sender.url}))[0]):null;
    const source=message.manual?{tabId:tab?.id,windowId:tab?.windowId,url:sender.url,session:SESSION}:currentCapture?.source||await sourceForImport();
    const work=await beginWork({...currentCapture,title:message.name,source},'Transfiriendo archivo…',!message.manual&&Boolean(currentCapture));
    return {work,source};
  })();
  if(message.type==='failWork')return endWork(message.work,new Error(message.error));
  if(message.type==='cancelWork')return cancelWork();
  if(message.type==='resumeJob')return (async()=>{
    const request=await native({action:'resume_job',job:message.job});const {workSources={}}=await browser.storage.local.get('workSources');const info=workSources[message.job]||{title:'Trabajo recuperado'};
    const work=await beginWork({...info,source:info.source},'Reanudando el trabajo…',false);
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
    const work=await beginWork({...c,source,token:current?.id===c.id?current.token:undefined},connecting?'Buscando conexiones por tema en tu Second Brain…':splitting?'Estudiando una posible división de la nota…':'Preparando una revisión del apartado…',connecting);
    try{const result=await native({...message,action:connecting?'refresh_links':splitting?'propose_split':'revise'});await endWork(work);return result;}catch(error){await endWork(work,error);throw error;}
  })();
  if(message.type==='splitDecision')return native({...message,action:'split_decision'});
  if (message.type === "adoptUpload") return (async()=>{
    if(message.work!==workClaim)throw new Error('La transferencia ya no pertenece al trabajo actual.');
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
  if (message.type === "resume") return native({action:"load",id:message.id}).then(async c => {
    const {sources={}}=await browser.storage.local.get("sources");c.source=sources[c.id];
    await browser.storage.local.set({editorFields:null,operationError:"",pageContext:{...c.source,status:"ready"}});
    await publishCapture(c,c.draft?{capture:c,draft:c.draft,folders:(await native({action:"status"})).folders}:null);
    if(c.draft&&c.status==="draft")await openReview(c.id);
    return c;
  });
});
