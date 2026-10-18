const $ = id => document.getElementById(id);
const call = message => browser.runtime.sendMessage({type:"native",message});
const manualImport=typeof location!=='undefined'&&new URL(location.href).searchParams.get('import')==='1';
let state = {}, status, locateTimer, serviceError = '';
let structureInitialized=false;
let activeReview=null,preferredReview=null;
let panelWindowId=null,panelStarted=false;
const sidebarView=typeof window!=='undefined'&&Boolean(browser.extension?.getViews?.({type:'sidebar'}).includes(window));
if(sidebarView)document.documentElement.style.visibility='hidden';
function timeLabel(seconds){seconds=Math.max(0,Math.floor(seconds||0));return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');}
function workDisplay(){
  const busy=Boolean(state.operation),p=state.operationProgress||{};
  $('workCard').hidden=!busy;document.body?.classList?.toggle('is-working',busy);
  if(!busy)return;
  const names={model:'PREPARANDO EL MOTOR',transcribe:'TRANSCRIPCIÓN LOCAL',download:'DESCARGANDO AUDIO',subtitles:'BUSCANDO SUBTÍTULOS',inspect:'COMPROBANDO EL ARCHIVO',frames:'EXTRAYENDO FOTOGRAMAS'};
  $('workStage').textContent=names[p.stage]||'TRABAJO EN CURSO';$('workTitle').textContent=state.activeWork?.title||'Preparando contenido';
  $('workElapsed').textContent=state.activeWork?.startedAt?timeLabel((Date.now()-state.activeWork.startedAt)/1000):'';
  const progress=$('workProgress');
  if(p.total_seconds>0&&Number.isFinite(p.processed_seconds)){
    const fraction=Math.min(.99,p.processed_seconds/p.total_seconds);progress.max=100;progress.value=fraction*100;
    $('workDetail').textContent=`${timeLabel(p.processed_seconds)} de ${timeLabel(p.total_seconds)} de audio · ${Math.floor(fraction*100)} %`+(p.engine?' · '+p.engine:'');
  }else{progress.removeAttribute?.('value');$('workDetail').textContent=p.engine||'Esta fase no ofrece un porcentaje medible.';}
  $('workHint').textContent=p.stage==='model'?'La primera carga puede descargar el modelo. El audio se procesa en este equipo.':'Puedes seguir navegando o cerrar este panel. El trabajo continúa.';
}
function imageSelection(){
  const checks=[...document.querySelectorAll('#images input[type=checkbox]')],n=checks.filter(e=>e.checked).length;
  $('imageCount').textContent=`${n} / 8 elegidas · ${checks.length} disponibles`;
  for(const check of checks)check.disabled=Boolean(state.operation)||(!check.checked&&n>=8);
}
const showError = error => {$("error").textContent=error.message||String(error);$("error").hidden=false;};
const run = fn => async () => {$("error").hidden=true;try{await fn();}catch(error){showError(error);}};

async function copyReport(button) {
  const parts=[];
  if(!$("error").hidden&&$("error").textContent)parts.push("Error:\n"+$("error").textContent);
  if(!$("diagnostic").hidden&&$("detectionReport").textContent)parts.push("Diagnóstico de detección:\n"+$("detectionReport").textContent);
  if(!parts.length)return;
  const text="Anaco "+browser.runtime.getManifest().version+"\n\n"+parts.join("\n\n");
  try {
    await navigator.clipboard.writeText(text);
    $("copyFallback").hidden=true;
    button.textContent="Copiado ✓";
  } catch {
    // Keep the original error intact; offer a selectable field if clipboard
    // access is unavailable in this browser context.
    const field=$("copyFallback");field.value=text;field.hidden=false;field.focus();field.select();
    button.textContent="Pulsa Ctrl+C";
  }
  setTimeout(()=>{button.textContent="Copiar";},2000);
}
for(const id of ["copyError","copyDiagnostic"])$(id).onclick=()=>copyReport($(id));

function locate(c,index,clear=false) {
  if(c.reader||c.kind==="pdf"||c.kind==="video")return;
  clearTimeout(locateTimer);
  const send=()=>browser.runtime.sendMessage({type:"locateImage",token:c.token,index,clear}).then(result=>{
    if(!clear&&!result.found)$("imageHint").textContent="No se encuentra esta imagen en el artículo. Puede haber cambiado desde la captura.";
  }).catch(error=>{if(!clear)$("imageHint").textContent=error.message;});
  if(clear)send();else locateTimer=setTimeout(send,140);
}
function drawCapture(c) {
  if(manualImport&&c?.source?.url!==location.href)c=null;
  $("empty").hidden=manualImport||Boolean(c)||state.pageContext?.status==="loading";$("captureCard").hidden=!c;
  $("reviewReady").hidden=!state.draftResult||!c;
  $("fileImport").hidden=!manualImport&&!(c?.kind==='pdf'&&c.url.startsWith('file:'));
  $("authorizeDetection").hidden=!c?.requiredOrigins?.length;
  $("authorizeDetection").textContent=c?.requiredOrigins?.length?'Permitir lectura de '+c.requiredOrigins.map(u=>new URL(u).hostname).join(', '):'Permitir detectar el contenido del visor';
  const diagnostics=Boolean(c&&(c.detectionError||c.reader||c.requiredOrigins?.length||c.videos?.some(v=>v.extractable===false)));
  $("diagnostic").hidden=!diagnostics;
  if(diagnostics)$("detectionReport").textContent=JSON.stringify({version:browser.runtime.getManifest?.().version,
    page:new URL(c.url).hostname,kind:c.kind,readable:Boolean(c.contentReady),pdf:c.documents?.length||0,
    images:c.images?.length||0,reader:c.reader?{scope:c.reader.scope,pages:c.reader.total_pages||c.reader.pages?.length||0,captured:c.reader.captured_pages,analyzed:c.reader.analyzed_pages}:null,
    video:(c.videos||[]).map(v=>({accessible:v.extractable!==false,subtitles:Boolean(v.subtitles||v.tracks?.length),host:(()=>{try{return new URL(v.url).hostname;}catch{return '';}})()})),
    ...c.detection,accessNeeded:(c.requiredOrigins||[]).map(u=>new URL(u).hostname)},null,2);
  if(!c)return;
  $("noteControls").hidden=(!c.id&&(c.reader||c.kind==="pdf"))||!(c.id||(c.contentReady??Boolean(c.text?.length>=100||c.kind==='quote'||c.kind==='image')));
  if(c.detectionError)showError(c.detectionError);
  $("success").hidden=true;
  $("captureTitle").textContent=c.title;$("kind").textContent={article:"ARTÍCULO",quote:"FRASE",image:"IMAGEN",pdf:"PDF",video:"VÍDEO / AUDIO"}[c.kind];
  if(c.reader&&c.kind!=="pdf")$("kind").textContent="LECTOR HTML";
  if(!c.id&&!c.contentReady)$("kind").textContent=c.documents?.length?'PDF':c.videos?.length?'VÍDEO / AUDIO':c.requiredOrigins?.length?'VISOR':'SIN CONTENIDO';
  $("source").textContent=(()=>{try{return new URL(c.url).hostname+' ↗';}catch{return 'Abrir fuente ↗';}})();$("source").href=c.url;$("extracted").textContent=c.text||"Este recurso todavía no se ha extraído.";
  $("warnings").textContent=(c.warnings||[]).join("\n");$("warnings").hidden=!c.warnings?.length;$("intent").value=c.intent||"";
  $("images").replaceChildren();
  $('imageSection').hidden=!c.images.length;
  $("imageHint").hidden=!c.images.length;
  $("imageHint").textContent=c.reader?.job?`${c.reader.captured_pages}/${c.reader.total_pages} páginas capturadas. Estas imágenes son figuras candidatas para la nota; la lectura del libro incluye todas las páginas.`:c.kind==="pdf"?"Selecciona páginas candidatas. La IA propondrá cuáles aportan valor; podrás cambiar la selección en la revisión.":c.kind==="video"?"Fotogramas del vídeo para incorporar diagramas o diapositivas a los apuntes.":"Pasa por una imagen para localizarla y resaltarla en el artículo. También puedes usar el teclado.";
  c.images.forEach((image,index)=>{
    const label=document.createElement("label");label.className="image-option image-pick";
    const check=document.createElement("input");check.type="checkbox";check.value=index;check.checked=c.kind==="image"||(c.selected_images?c.selected_images.includes(index):Boolean(c.id)||Boolean(c.reader&&index<8));check.onchange=imageSelection;
    const thumb=document.createElement("span");thumb.className="image-thumb";
    if(/^data:image\/(jpeg|png|webp);base64,/.test(image.thumbnail||'')){
      const img=document.createElement("img");img.src=image.thumbnail;img.alt="";thumb.append(img);
    }else{thumb.textContent=String(index+1);}
    const info=document.createElement("span");info.className="image-info";
    const title=document.createElement("strong");title.textContent="Imagen "+(index+1);
    const alt=document.createElement("span");alt.textContent=image.caption||image.figcaption||image.alt||"Sin descripción · localízala en el artículo";
    const size=document.createElement("small");size.textContent=image.width&&image.height?image.width+" × "+image.height:"";
    info.append(title,alt,size);label.append(check,thumb,info);
    label.addEventListener("mouseenter",()=>locate(c,index));label.addEventListener("mouseleave",()=>locate(c,index,true));
    label.addEventListener("focusin",()=>locate(c,index));label.addEventListener("focusout",()=>locate(c,index,true));
    $("images").append(label);
  });
  imageSelection();
  drawEmbeds(c);
  $("prepare").textContent=c.id?"Regenerar y abrir revisión":"Preparar y abrir revisión ↗";
  const documents=c.documents||[],videos=c.videos||[];
    const rawBook=Boolean(c.reader&&!c.id&&c.kind!=="pdf");
  $("readerControls").hidden=!rawBook;
  $("readerCount").textContent=rawBook?`${c.reader.pages?.length||0} páginas localizadas. Se extraerán todas.`:'';
  $("resources").hidden=!(rawBook||documents.length||videos.some(v=>v.extractable!==false));
  for(const [name,items,label] of [["pdf",documents,"PDF"],["video",videos,"Vídeo"]]){
    $(name+"Controls").hidden=!items.length||(name==='video'&&items.every(v=>v.extractable===false));$(name+"Resource").replaceChildren();
    items.forEach((item,index)=>{const option=document.createElement("option");option.value=index;option.textContent=name==='video'?AnacoObMedia.label(item,index):item.title||label+" "+(index+1);$(name+"Resource").append(option);});
  }
  const onlyLocalPDF=documents.length>0&&documents.every(d=>d.url.startsWith('file:'));
  $("extractPdf").hidden=onlyLocalPDF;
  if(onlyLocalPDF){$("pdfControls").hidden=true;$("resources").hidden=!(rawBook||videos.some(v=>v.extractable!==false));}
  const selectedVideo=videos[Number($("videoResource").value)||0];
  $("extractVideo").hidden=selectedVideo?.extractable===false;
}
// [UI] Embedded resources are chosen like images; heavy clips start unchecked.
function drawEmbeds(c){
  const items=c.id?[]:c.embeds||[];
  $('embedSection').hidden=!items.length;$('embeds').replaceChildren();
  const groups=[['clip','Clips de vídeo','▶'],['pen','Demos de CodePen','</>'],['tweet','Publicaciones de X','𝕏']];
  for(const [type,heading,mark] of groups){
    const list=items.filter(item=>item.type===type);if(!list.length)continue;
    const title=document.createElement('h4');title.className='embed-group';title.textContent=heading+' · '+list.length;$('embeds').append(title);
    for(const item of list){
      const label=document.createElement('label');label.className='image-option image-pick';
      const check=document.createElement('input');check.type='checkbox';check.dataset.embed=item.index;
      check.checked=!(type==='clip'&&Number(item.size)>AnacoObEmbeds.CLIP_LIMIT);check.onchange=embedSelection;
      const thumb=document.createElement('span');thumb.className='image-thumb';
      if(/^data:image\/jpeg;base64,/.test(item.thumbnail||'')){const img=document.createElement('img');img.src=item.thumbnail;img.alt='';thumb.append(img);}else thumb.textContent=mark;
      const info=document.createElement('span');info.className='image-info';
      const name=document.createElement('strong');name.textContent=item.title||item.author||'Recurso';
      const detail=document.createElement('span');
      detail.textContent=type==='clip'?[item.duration?Math.round(item.duration)+' s':'',item.size?(item.size/1000000).toFixed(1)+' MB':''].filter(Boolean).join(' · ')||'Clip silencioso':type==='pen'?'CodePen · @'+item.user+' · copia ejecutable sin conexión':(item.text||'Publicación incrustada').slice(0,140);
      info.append(name,detail);
      if(item.warning){const warning=document.createElement('small');warning.className='embed-warning';warning.textContent=item.warning;info.append(warning);}
      label.append(check,thumb,info);$('embeds').append(label);
    }
  }
  embedSelection();
}
function embedSelection(){
  const checks=[...document.querySelectorAll('#embeds input[type=checkbox]')];
  $('embedCount').textContent=`${checks.filter(e=>e.checked).length} / ${checks.length} elegidos`;
  for(const check of checks)check.disabled=Boolean(state.operation);
}
async function refresh() {
  try {
    status=await call({action:"status"});
    if(!structureInitialized){$('noteStructure').value=status.config.note_structure||'single';structureInitialized=true;}$("connection").textContent="SERVICIO LOCAL CONECTADO";
    // [UI] The vault profile decides where notes go: missing or outdated, say so before preparing.
    const profile=status.profile||{};$('profileNotice').hidden=!(profile.missing||profile.problems?.length);
    $('profileNoticeText').textContent=profile.missing?(profile.message||'Este vault aún no tiene perfil: escanéalo en Opciones antes de guardar notas.'):profile.problems?.length?profile.problems[0]+(profile.problems.length>1?` (y ${profile.problems.length-1} más)`:''):'';
    if(serviceError && $('error').textContent === serviceError) $('error').hidden=true;
    serviceError='';
    $('recoverSection').hidden=!(status.jobs||[]).length;$('recoverJobs').replaceChildren();
    const {workSources={}}=await browser.storage.local.get('workSources');
    for(const job of status.jobs||[]){const row=document.createElement('div');row.className='job-row';const label=document.createElement('span');label.textContent=(workSources[job.id]?.title||({upload_finish:'Extracción de archivo',draft:'Preparación de nota',video_url:'Vídeo de plataforma'})[job.action])+' · '+({cancelled:'Cancelado',interrupted:'Interrumpido',failed:'Error recuperable',pending:'Pendiente',running:'En curso'}[job.status]||'Pendiente');const button=document.createElement('button');button.textContent='Reanudar';button.disabled=Boolean(state.operation);button.onclick=run(async()=>{await browser.runtime.sendMessage({type:'resumeJob',job:job.id});await refresh();});row.append(label,button);$('recoverJobs').append(row);}
    $("provider").value=status.config.provider;$("pending").replaceChildren();
    for(const c of status.pending){const b=document.createElement("button");b.className="pending-item";b.textContent=c.title+" · "+c.kind;b.addEventListener("click",run(async()=>browser.runtime.sendMessage({type:"resume",id:c.id})));$("pending").append(b);}
    if(!status.pending.length)$("pending").textContent="No hay capturas pendientes.";
  }catch(error){serviceError=error.message;$("connection").textContent="SERVICIO SIN CONECTAR";throw error;}
}
async function sync(changes) {
  state=await browser.storage.local.get(["currentCapture","draftResult","operation","operationProgress","operationError","operationDiagnostic","lastResult","pageContext","activeWork","autoReview","reviewSessions","captureMode"]);
  $('captureMode').value=state.captureMode||'auto';$('captureMode').disabled=Boolean(state.operation);
  reviewMenu();
  $('autoReview').checked=state.autoReview!==false;
  $('extractVideo').textContent=$('autoReview').checked?'Crear nota del vídeo':'Extraer subtítulos o transcribir';
  $('extractPdf').textContent=$('autoReview').checked?'Crear nota del PDF':'Extraer PDF y páginas';
  $('extractReader').textContent=$('autoReview').checked?'Crear notas del libro completo':'Extraer libro completo';
  $('importButton').textContent=$('autoReview').checked?'Extraer y preparar nota':'Extraer archivo';
  if(!changes||changes.currentCapture||changes.draftResult||changes.pageContext)drawCapture(state.currentCapture);
  const page=state.pageContext;
  $("pageStatus").textContent=manualImport?'Importación manual de un archivo local':page?.status==='loading'?'Detectando el contenido de esta pestaña…':page?.url?`${state.operation?'Origen del trabajo':'Página'}: ${(()=>{try{return new URL(page.url).hostname;}catch{return 'archivo local';}})()}`:'';
  if(activeReview&&!state.operationError)$('error').hidden=true;
  else if(page?.status==='error')showError(page.error);
  else if(page?.status==='ready'&&!state.operationError&&!state.currentCapture?.detectionError)$("error").hidden=true;
  $("operation").textContent=state.operation||'';$("operation").hidden=!state.operation;workDisplay();imageSelection();
  $("prepare").disabled=Boolean(state.operation)||(!state.currentCapture?.id&&state.currentCapture?.kind==="pdf");$("recapture").disabled=Boolean(state.operation);
  for(const id of ["importButton","extractPdf","extractVideo","extractReader"])$(id).disabled=Boolean(state.operation);
  for(const id of ['provider','intent','noteStructure'])$(id).disabled=Boolean(state.operation);
  if(state.operationError){
    showError(new Error(state.operationError));
    $("diagnostic").hidden=false;
    const report={error:state.operationError,page:state.currentCapture?.url?new URL(state.currentCapture.url).hostname:'',...state.currentCapture?.detection,...(state.operationDiagnostic?{extraction:state.operationDiagnostic}:{})};
    $("detectionReport").textContent=JSON.stringify(report,null,2);
  }
  if(state.lastResult&&!state.currentCapture&&state.pageContext?.status!=='loading'){
    $("success").replaceChildren(document.createTextNode("Nota guardada: "+state.lastResult.relative+" "));
    const link=document.createElement("a");link.href=state.lastResult.obsidian_url;link.textContent="Abrir en Obsidian ↗";$("success").append(link);$("success").hidden=false;
  }
  if(changes?.settingsRevision){structureInitialized=false;refresh().catch(showError);}
  else if(changes?.currentCapture&&!state.operation)refresh().catch(showError);
  else if(changes?.operation&&!state.operation)refresh().catch(showError);
}
function reviewMenu(){
  const previous=activeReview;
  const sessions=Object.values(state.reviewSessions||{}).filter(r=>r.windowId===panelWindowId).sort((a,b)=>b.updatedAt-a.updatedAt);
  const focused=sessions.find(r=>r.tabActive);if(focused)preferredReview=focused.id;
  activeReview=focused||sessions.find(r=>r.id===preferredReview)||sessions[0]||null;
  $('reviewWorkspace').hidden=!activeReview;$('captureWorkspace').hidden=Boolean(activeReview);
  if(!activeReview){if(previous&&!manualImport)detectCurrent(true);return;}
  const r=activeReview;
  $('reviewChooser').hidden=$('reviewChooserLabel').hidden=sessions.length<2;
  $('reviewChooser').replaceChildren();
  for(const item of sessions)$('reviewChooser').append(new Option(item.title,item.id));
  $('reviewChooser').value=r.id;$('reviewMenuTitle').textContent=r.title;
  $('reviewMenuStatus').textContent=`${r.notes.filter(n=>n.selected).length} de ${r.notes.length} notas incluidas · ${r.busy?'Trabajo en curso':r.status||'Revisa la propuesta'}`;
  $('reviewMenuNotes').replaceChildren();
  for(const note of r.notes){
    const row=document.createElement('div');row.className='review-menu-note';
    const check=document.createElement('input');check.type='checkbox';check.checked=note.selected;check.disabled=r.busy;check.setAttribute('aria-label','Incluir '+note.title);
    check.onchange=()=>reviewAction('include',note.id,check.checked).catch(showError);
    const button=document.createElement('button');button.type='button';button.textContent=note.title;button.dataset.reviewNote=note.id;button.setAttribute('aria-current',String(note.id===r.activeNote));button.disabled=r.busy;
    const links=document.createElement('small');links.textContent=`${note.externalLinks||0} con notas existentes · ${note.internalLinks||0} entre temas`;button.append(links);
    button.onclick=()=>reviewAction('note',note.id).catch(showError);row.append(check,button);$('reviewMenuNotes').append(row);
  }
  for(const id of ['reviewRead','reviewEdit','reviewProperties','reviewConnections','reviewRefreshLinks','reviewSplit'])$(id).disabled=r.busy;
  $('reviewRead').setAttribute('aria-pressed',String(r.view==='read'));
  $('reviewEdit').setAttribute('aria-pressed',String(r.view==='edit'));
  $('reviewSave').disabled=!r.canSave||r.busy;$('reviewSave').textContent=r.saveLabel||'Guardar y volver';
}
function reviewAction(command,note,value){
  if(!activeReview)return Promise.reject(new Error('No hay una revisión abierta en esta ventana.'));
  return browser.runtime.sendMessage({type:'reviewCommand',id:activeReview.id,windowId:panelWindowId,command,note,value});
}
for(const [id,action] of Object.entries({reviewRead:'read',reviewEdit:'edit',reviewProperties:'properties',reviewConnections:'connections',reviewRefreshLinks:'refreshLinks',reviewSplit:'split',reviewFocus:'focus',reviewSave:'save'}))$(id).onclick=run(()=>reviewAction(action));
$('reviewChooser').onchange=()=>{preferredReview=$('reviewChooser').value;browser.runtime.sendMessage({type:'reviewCommand',id:preferredReview,windowId:panelWindowId,command:'focus'}).catch(showError);};
$("profileReviewButton").onclick=run(async()=>browser.runtime.sendMessage({type:'openOptions',windowId:panelWindowId}));
$("options").onclick=run(async()=>{
  await browser.runtime.sendMessage({type:'openOptions',windowId:panelWindowId});
});
$('cancelJob').onclick=run(async()=>{await browser.runtime.sendMessage({type:'cancelWork'});});
$('captureMode').onchange=run(async()=>{
  await browser.storage.local.set({captureMode:$('captureMode').value});
  await browser.runtime.sendMessage({type:'detectActive',fresh:true,windowId:panelWindowId});
});
$('autoReview').onchange=()=>browser.storage.local.set({autoReview:$('autoReview').checked});
const preparation=()=>({prepareAfter:state.autoReview!==false,provider:$('provider').value,intent:$('intent').value,note_structure:$('noteStructure').value});
for(const id of ["captureEmpty","recapture"])$(id).onclick=run(async()=>{
  const origins=[state.pageContext?.url,state.currentCapture?.url].filter(Boolean);
  const granted=await requestOrigins(origins);
  if(!granted)throw new Error('No se ha concedido acceso a esta página.');
  await browser.runtime.sendMessage({type:"detectActive"});
});
$("prepare").onclick=run(async()=>{
  const selected=[...document.querySelectorAll("#images input:checked")].map(i=>Number(i.value));
  if(selected.length>8)throw new Error("Selecciona como máximo ocho imágenes.");
  const c=state.currentCapture;
  const embeds=[...document.querySelectorAll("#embeds input:checked")].map(i=>Number(i.dataset.embed));
  const embedURLs=embeds.map(i=>c.embeds?.[i]).flatMap(e=>e?.type==='clip'?[e.url]:e?.type==='pen'?['https://codepen.io/','https://cdpn.io/']:[]);
  const origins=[...new Set([...selected.map(i=>c.images[i].url),...embedURLs].map(url=>{try{const u=new URL(url);return /^https?:$/.test(u.protocol)?u.protocol+"//"+u.hostname+"/*":null;}catch{return null;}}).filter(Boolean))];
  // Keep this call before any await so Firefox preserves the user gesture.
  if(origins.length&&!c.id){const granted=await browser.permissions.request({origins});if(!granted)throw new Error("No se ha concedido acceso a las imágenes o recursos elegidos. Desmárcalos para capturar solo el texto.");}
  locate(c,0,true);
  await browser.runtime.sendMessage({type:"prepare",token:c.token,images:selected,embeds,intent:$("intent").value,provider:$("provider").value,note_structure:$("noteStructure").value});
  await refresh();
});
$("reviewReady").onclick=run(async()=>browser.runtime.sendMessage({type:"openReview",id:state.currentCapture.id}));
$("refresh").onclick=run(refresh);
function requestOrigins(urls){
  const origins=[...new Set(urls.filter(Boolean).map(value=>{const u=new URL(value);return /^https?:$/.test(u.protocol)?u.protocol+"//"+u.hostname+"/*":null;}).filter(Boolean))];
  return origins.length?browser.permissions.request({origins}):Promise.resolve(true);
}
$("extractReader").onclick=run(async()=>{
  const c=state.currentCapture;
  const urls=(c.reader?.pages||[]).flatMap(p=>p.urls||[]);
  const granted=await requestOrigins([c.url,...urls]);
  if(!granted)throw new Error('No se ha concedido acceso a las páginas del libro.');
  await browser.runtime.sendMessage({type:'extractReader',token:c.token,...preparation()});
});
$("extractPdf").onclick=run(async()=>{
  const c=state.currentCapture,resource=c.documents[Number($("pdfResource").value)];
  if(resource.url.startsWith("file:"))throw new Error("Para este PDF local usa Importar archivo, en la parte superior del panel.");
  const granted=await requestOrigins([resource.url]);if(!granted)throw new Error("No se ha concedido acceso al PDF.");
  await browser.runtime.sendMessage({type:"importResource",token:c.token,kind:"pdf",url:resource.url,pageUrl:c.url,name:(resource.title||c.title).replace(/\.pdf$/i,"")+".pdf",pages:$("pdfPages").value,...preparation()});
});
$("extractVideo").onclick=run(async()=>{
  const c=state.currentCapture,video=c.videos[Number($("videoResource").value)];
  if(video.extractable===false)throw new Error(video.unavailableReason||'No hay audio o subtítulos accesibles en este reproductor.');
  const track=[...(video.tracks||[])].sort((a,b)=>(!a.language?.startsWith("es"))-(!b.language?.startsWith("es")))[0];
  const platform=AnacoObMedia.platformURL(video.url);
  const direct=video.download||(/^https?:/.test(video.url)&&!platform&&!AnacoObMedia.apiURL(video.url)&&video.url!==c.url?video.url:null);
  const granted=await requestOrigins([track?.url,direct,...(video.download?['https://drive.usercontent.google.com/','https://*.googleusercontent.com/']:[])]);
  if(!granted)throw new Error("No se ha concedido acceso al recurso de vídeo.");
  const audio=direct&&!/\.mpd(?:[?#]|$)/i.test(direct)?(/\.m3u8(?:[?#]|$)/i.test(direct)?{kind:'video-hls',url:direct}:{kind:'video',url:direct,name:'video.mp4'}):platform?{kind:'video-platform',url:platform}:null;
  const request=video.subtitles?{kind:'subtitles',text:video.subtitles,fallback:audio}:track?{kind:'subtitle-url',url:track.url,frameId:video.frameId,fallback:audio}:audio;
  if(!request)throw new Error('El reproductor no expone un recurso de audio ni subtítulos accesibles.');
  await browser.runtime.sendMessage({type:"importResource",token:c.token,...request,frameId:video.frameId,frameURL:video.frameURL,title:video.title||c.title,pageUrl:c.url,...preparation()});
});
$("authorizeDetection").onclick=run(async()=>{
  const c=state.currentCapture;
  const granted=await browser.permissions.request({origins:c.requiredOrigins});
  if(!granted)throw new Error('No se ha concedido acceso al contenido incrustado.');
  await browser.runtime.sendMessage({type:'inspectFrame'});
});
$("videoResource").onchange=()=>{
  const video=state.currentCapture?.videos[Number($("videoResource").value)];
  $("extractVideo").hidden=video?.extractable===false;
  if(video?.extractable===false)showError(video.unavailableReason);
};
$("importButton").onclick=run(async()=>{
  let uploadWork;
  const file=$("importFile").files[0];if(!file)throw new Error("Selecciona primero un archivo.");
  const limit=/\.(pdf|vtt|srt)$/i.test(file.name)?100000000:1000000000;
  if(file.size>limit)throw new Error("Límite: 100 MB para PDF/subtítulos y 1 GB para archivos locales de audio/vídeo.");
  uploadWork=await browser.runtime.sendMessage({type:'beginUploadWork',name:file.name,manual:manualImport});
  try{
    const begin=await call({action:"upload_begin",name:file.name,size:file.size,url:manualImport?"":state.currentCapture?.url||""});
    for(let offset=0;offset<file.size;offset+=393216){const bytes=new Uint8Array(await file.slice(offset,offset+393216).arrayBuffer());let binary="";for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));await call({action:"upload_chunk",upload:begin.upload,offset,data:btoa(binary)});}
    await browser.storage.local.set({operation:file.name.toLowerCase().endsWith(".pdf")?"Leyendo PDF y renderizando páginas…":"Transcribiendo o leyendo subtítulos. Puedes seguir navegando…"});
    const c=await call({action:"upload_finish",upload:begin.upload,pages:$("importPages").value});
    await browser.runtime.sendMessage({type:"adoptUpload",capture:c,work:uploadWork.work,manual:manualImport,...preparation()});
  }catch(error){await browser.runtime.sendMessage({type:'failWork',work:uploadWork.work,error:error.message});throw error;}
});
browser.storage.onChanged.addListener((changes,area)=>{if(area==="local"&&panelStarted)sync(changes).catch(showError);});
let tabRefreshTimer;
function detectCurrent(fresh=false,tabId){
  clearTimeout(tabRefreshTimer);
  if(activeReview)return;
  tabRefreshTimer=setTimeout(()=>browser.runtime.sendMessage({type:'detectActive',fresh,tabId,windowId:panelWindowId}).catch(showError),100);
}
async function startPanel(){
  if(browser.windows?.getCurrent)panelWindowId=(await browser.windows.getCurrent()).id;
  if(sidebarView){
    const allowed=await browser.runtime.sendMessage({type:'sidebarPolicy',windowId:panelWindowId});
    if(!allowed){window.close();return;}
    document.documentElement.style.visibility='';
  }
  panelStarted=true;
  if(browser.tabs&&!manualImport){
    browser.tabs.onActivated.addListener(info=>{if(panelWindowId===null||info.windowId===panelWindowId){const match=Object.values(state.reviewSessions||{}).find(r=>r.tabId===info.tabId);if(match){preferredReview=match.id;reviewMenu();}detectCurrent(false,info.tabId);}});
    browser.tabs.onUpdated.addListener((id,change,tab)=>{if((panelWindowId===null||tab.windowId===panelWindowId)&&tab.active&&(change.status==='complete'||change.url))detectCurrent(true,id);});
    browser.windows?.onFocusChanged?.addListener(id=>{if(id===panelWindowId)detectCurrent(false);});
  }
  await sync();refresh().catch(showError);if(!manualImport)detectCurrent(false);
}
startPanel().catch(showError);
if(typeof setInterval==='function')setInterval(workDisplay,1000);
