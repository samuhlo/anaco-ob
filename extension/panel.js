const $ = id => document.getElementById(id);
const call = message => browser.runtime.sendMessage({type:"native",message});
const manualImport=typeof location!=='undefined'&&new URL(location.href).searchParams.get('import')==='1';
let state = {}, status, locateTimer, serviceError = '';
let structureInitialized=false;
let captureFormKey='',captureFormSource='',captureFormId=null,captureTarget='';
let activeReview=null,preferredReview=null;
let panelWindowId=null,panelStarted=false,knownJobs=null;
let boundSource=null;
const sidebarView=typeof window!=='undefined'&&Boolean(browser.extension?.getViews?.({type:'sidebar'}).includes(window));
if(sidebarView)document.documentElement.style.visibility='hidden';
function timeLabel(seconds){seconds=Math.max(0,Math.floor(seconds||0));return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');}
function workDisplay(){
  const busy=Boolean(state.operation),p=state.operationProgress||{};
  $('workCard').hidden=!busy;document.body?.classList?.toggle('is-working',busy);
  if(!busy)return;
  const names={model:tx('panel_preparando_el_motor'),transcribe:tx('panel_transcripcion_local'),download:tx('progress_download'),subtitles:tx('panel_buscando_subtitulos'),inspect:tx('panel_comprobando_el_archivo'),frames:tx('panel_extrayendo_fotogramas'),reading:tx('progress_reading'),synthesis:tx('progress_synthesis'),capture:tx('progress_capture'),resources:tx('progress_resources_stage'),cancel:tx('progress_cancel'),'pdf-text':tx('progress_pdf_text'),'pdf-images':tx('progress_pdf_images')};
  $('workStage').textContent=names[p.stage]||tx('panel_trabajo_en_curso_caps');$('workTitle').textContent=state.activeWork?.title||tx('panel_preparando_contenido');
  $('workElapsed').textContent=state.activeWork?.startedAt?timeLabel((Date.now()-state.activeWork.startedAt)/1000):'';
  const progress=$('workProgress');
  const measured=AnacoObProgress.measure(p);
  // Firefox paints an indeterminate <progress> as a full bar with our theme.
  // The spinner already shows activity; only measured phases need the bar.
  progress.hidden=!measured;
  $('cancelJob').disabled=p.stage==='cancel';
  if(measured){progress.max=100;progress.value=measured.fraction*100;}
  else progress.removeAttribute?.('value');
  $('workDetail').textContent=(measured?.detail||tx('progress_waiting'))+(p.engine?' · '+p.engine:'');
  progress.setAttribute('aria-valuetext',$('workDetail').textContent);
  $('workHint').textContent=p.stage==='model'?tx('panel_la_primera_carga_puede_descargar_el_mode'):tx('panel_puedes_seguir_navegando_o_cerrar_este_pa');
}
// [UI] The strip under the logo follows the note: detected, preparing, review, saved.
let brandReady=false;
function brandProgress(){
  if(!brandReady)return;
  const c=state.currentCapture;
  let value=0;
  if(activeReview)value=75;
  else if(state.operation)value=45;
  else if(state.lastResult&&!c)value=100;
  else if(state.draftResult)value=70;
  else if(c)value=25;
  $('brandHead')?.style?.setProperty('--brand-progress',value+'%');
}
// Opening the panel fills and empties the strip once, then shows the current step.
async function brandIntro(){
  const head=$('brandHead')?.style?$('brandHead'):null;
  const still=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(head&&!still){
    const step=(value,ms)=>{head.style.setProperty('--brand-progress',value);return new Promise(r=>setTimeout(r,ms));};
    await step('0%',60);await step('100%',750);await step('0%',750);
  }
  brandReady=true;brandProgress();
}
function imageSelection(){
  const checks=[...document.querySelectorAll('#images input[type=checkbox]')],n=checks.filter(e=>e.checked).length;
  $('imageCount').textContent=tx('panel_1_8_elegidas_2_disponibles',[n,checks.length]);
  for(const check of checks)check.disabled=Boolean(state.operation)||(!check.checked&&n>=8);
  attachmentSummary();
}
function attachmentSummary(){
  const checks=[...document.querySelectorAll('#images input[type=checkbox],#embeds input[type=checkbox]')];
  $('attachmentCount').textContent=tx('panel_flow_attachments_count',[checks.filter(c=>c.checked).length,checks.length]);
}
const showError = error => {$("error").textContent=error.message||String(error);$("error").hidden=false;};
const run = fn => async () => {$("error").hidden=true;try{await fn();}catch(error){showError(error);}};

async function copyReport(button) {
  const parts=[];
  if(!$("error").hidden&&$("error").textContent)parts.push("Error:\n"+$("error").textContent);
  if(!$("diagnostic").hidden&&$("detectionReport").textContent)parts.push(tx('panel_diagnostico_de_deteccion_2')+$("detectionReport").textContent);
  if(!parts.length)return;
  const text="Anaco "+browser.runtime.getManifest().version+"\n\n"+parts.join("\n\n");
  try {
    await navigator.clipboard.writeText(text);
    $("copyFallback").hidden=true;
    button.textContent=tx('panel_copiado');
  } catch {
    // Keep the original error intact; offer a selectable field if clipboard
    // access is unavailable in this browser context.
    const field=$("copyFallback");field.value=text;field.hidden=false;field.focus();field.select();
    button.textContent=tx('panel_pulsa_ctrl_c');
  }
  setTimeout(()=>{button.textContent=tx('panel_copiar');},2000);
}
for(const id of ["copyError","copyDiagnostic"])$(id).onclick=()=>copyReport($(id));

function locate(c,index,clear=false,embed=null) {
  if(c.reader||c.kind==="pdf"||c.kind==="video")return;
  clearTimeout(locateTimer);
  const hint=embed?$('embedHint'):$("imageHint");
  const send=()=>browser.runtime.sendMessage({type:"locateImage",token:c.token,index,clear,embed:Boolean(embed),label:embed}).then(result=>{
    if(!clear&&!result.found)hint.textContent=embed?tx('panel_no_se_encuentra_este_recurso_en_el_artic'):tx('panel_no_se_encuentra_esta_imagen_en_el_articu');
  }).catch(error=>{if(!clear)hint.textContent=error.message;});
  if(clear)send();else locateTimer=setTimeout(send,140);
}
function drawCapture(c) {
  if(manualImport&&c?.source?.url!==location.href)c=null;
  $("empty").hidden=manualImport||Boolean(c)||state.pageContext?.status==="loading";$("captureCard").hidden=!c||Boolean(!c.id&&c.kind==='pdf'&&c.url.startsWith('file:'));
  $("reviewReady").hidden=!state.draftResult||!c;
  $("fileImport").hidden=!manualImport&&!(c?.kind==='pdf'&&c.url.startsWith('file:'));
  if(c?.kind==='pdf'&&c.url.startsWith('file:')&&!c.id)$('fileImport').querySelector('details').open=true;
  $("authorizeDetection").hidden=!c?.requiredOrigins?.length;
  $("authorizeDetection").textContent=c?.requiredOrigins?.length?tx('panel_permitir_lectura_de')+c.requiredOrigins.map(u=>new URL(u).hostname).join(', '):tx('panel_permitir_detectar_el_contenido_del_visor');
  const diagnostics=Boolean(c&&(c.detectionError||c.requiredOrigins?.length||c.videos?.some(v=>v.extractable===false)));
  $("diagnostic").hidden=!diagnostics;
  if(diagnostics)$("detectionReport").textContent=JSON.stringify({version:browser.runtime.getManifest?.().version,
    page:new URL(c.url).hostname,kind:c.kind,readable:Boolean(c.contentReady),pdf:c.documents?.length||0,
    images:c.images?.length||0,reader:c.reader?{scope:c.reader.scope,pages:c.reader.total_pages||c.reader.pages?.length||0,captured:c.reader.captured_pages,analyzed:c.reader.analyzed_pages}:null,
    video:(c.videos||[]).map(v=>({accessible:v.extractable!==false,subtitles:Boolean(v.subtitles||v.tracks?.length),host:(()=>{try{return new URL(v.url).hostname;}catch{return '';}})()})),
    ...c.detection,accessNeeded:(c.requiredOrigins||[]).map(u=>new URL(u).hostname)},null,2);
  if(!c)return;
  const key=c.id||c.url;
  if(key!==captureFormKey){
    const source=c.source?.url||c.url,adopting=Boolean(c.id&&!captureFormId&&source===captureFormSource);
    captureFormKey=key;captureTarget='';
    if(!adopting||c.intent)$('intent').value=c.intent||'';
    if(!adopting||c.note_structure)$('noteStructure').value=c.note_structure||status?.config?.note_structure||'single';
    captureFormSource=source;captureFormId=c.id||null;
    $('attachments').open=c.kind==='image';
    $('capturePreview').open=c.kind==='quote';
  }
  if(state.operation&&c.note_structure)$('noteStructure').value=c.note_structure;
  if(c.detectionError)showError(c.detectionError);
  $("success").hidden=true;
  $("captureTitle").textContent=c.title;$("kind").textContent={article:tx('panel_articulo'),quote:tx('panel_frase'),image:tx('panel_imagen'),pdf:"PDF",video:tx('panel_video_audio')}[c.kind];
  if(c.reader&&c.kind!=="pdf")$("kind").textContent=tx('panel_lector_html');
  if(!c.id&&!c.contentReady)$("kind").textContent=c.documents?.length?'PDF':c.videos?.length?tx('panel_video_audio'):c.requiredOrigins?.length?tx('panel_visor'):tx('panel_sin_contenido');
  $("source").textContent=(()=>{try{return new URL(c.url).hostname+' ↗';}catch{return tx('panel_abrir_fuente');}})();$("source").href=c.url;$("extracted").textContent=c.text||tx('panel_este_recurso_todavia_no_se_ha_extraido');
  const warnings=(c.warnings||[]).filter(w=>!c.reader||w!==tx('capture_libro_detectado_1_paginas_disponibles_us',[c.reader.pages?.length||0]));
  $("warnings").textContent=warnings.join("\n");$("warnings").hidden=!warnings.length;
  $('capturePreview').hidden=!c.text?.trim();
  $("images").replaceChildren();
  $('imageSection').hidden=!c.images.length;
  $("imageHint").hidden=!c.images.length;
  $("imageHint").textContent=c.reader?.job?tx('panel_1_2_paginas_capturadas_estas_imagenes_so',[c.reader.captured_pages,c.reader.total_pages]):c.kind==="pdf"?tx('panel_selecciona_paginas_candidatas_la_ia_prop'):c.kind==="video"?tx('panel_fotogramas_del_video_para_incorporar_dia'):tx('panel_pasa_por_una_imagen_para_localizarla_y_r');
  c.images.forEach((image,index)=>{
    const label=document.createElement("label");label.className="image-option image-pick";
    const check=document.createElement("input");check.type="checkbox";check.value=index;check.checked=c.kind==="image"||(c.selected_images?c.selected_images.includes(index):Boolean(c.id)||Boolean(c.reader&&index<8));check.onchange=imageSelection;
    const thumb=document.createElement("span");thumb.className="image-thumb";
    if(/^data:image\/(jpeg|png|webp);base64,/.test(image.thumbnail||'')){
      const img=document.createElement("img");img.src=image.thumbnail;img.alt="";thumb.append(img);
    }else{thumb.textContent=String(index+1);}
    const info=document.createElement("span");info.className="image-info";
    const title=document.createElement("strong");title.textContent=tx('panel_imagen_1',[index+1]);
    const alt=document.createElement("span");alt.textContent=image.caption||image.figcaption||image.alt||tx('panel_sin_descripcion_localizala_en_el_articul');
    const size=document.createElement("small");size.textContent=image.width&&image.height?image.width+" × "+image.height:"";
    info.append(title,alt,size);label.append(check,thumb,info);
    label.addEventListener("mouseenter",()=>locate(c,index));label.addEventListener("mouseleave",()=>locate(c,index,true));
    label.addEventListener("focusin",()=>locate(c,index));label.addEventListener("focusout",()=>locate(c,index,true));
    $("images").append(label);
  });
  imageSelection();
  drawEmbeds(c);
  const documents=c.documents||[],videos=c.videos||[];
    const rawBook=Boolean(c.reader&&!c.id&&c.kind!=="pdf");
  $("readerCount").textContent=rawBook?tx('panel_flow_pages',[c.reader.pages?.length||0]):'';
  for(const [name,items,label] of [["pdf",documents,"PDF"],["video",videos,tx('panel_video')]]){
    const previous=$(name+'Resource').selectedOptions?.[0]?.dataset.url;
    $(name+"Resource").replaceChildren();
    items.forEach((item,index)=>{const option=document.createElement("option");option.value=index;option.dataset.url=item.url;option.textContent=name==='video'?AnacoObMedia.label(item,index):item.title||label+" "+(index+1);option.disabled=name==='video'?item.extractable===false:item.url.startsWith('file:');$(name+"Resource").append(option);});
    const usable=items.map((v,i)=>({v,i})).filter(({v})=>name==='video'?v.extractable!==false:!v.url.startsWith('file:'));
    $(name+'Resource').value=String((usable.find(({v})=>v.url===previous)||usable[0])?.i??0);
    $(name+'Choice').hidden=usable.length<2;
  }
  const onlyLocalPDF=documents.length>0&&documents.every(d=>d.url.startsWith('file:'));
  $("extractPdf").hidden=onlyLocalPDF;
  const selectedVideo=videos[Number($("videoResource").value)||0];
  $("extractVideo").hidden=selectedVideo?.extractable===false;
  const labels={note:tx('panel_flow_page_text'),reader:tx('panel_lector_html'),pdf:'PDF',video:tx('panel_video_audio')};
  $('captureTarget').replaceChildren();
  for(const type of AnacoObCaptureFlow.choices(c)){const option=document.createElement('option');option.value=type;option.textContent=labels[type];$('captureTarget').append(option);}
  renderCaptureFlow(c);
}
function renderCaptureFlow(c=state.currentCapture){
  if(!c){$('autoReviewLabel').hidden=!manualImport;return;}
  const types=AnacoObCaptureFlow.choices(c);
  $('captureFields').hidden=!types.length;
  captureTarget=AnacoObCaptureFlow.select(c,captureTarget);
  $('captureTarget').value=captureTarget;$('captureTargetGroup').hidden=types.length<2;
  $('noteControls').hidden=captureTarget!=='note';
  $('resources').hidden=!['reader','pdf','video'].includes(captureTarget);
  for(const type of ['reader','pdf','video'])$(type+'Controls').hidden=captureTarget!==type;
  const hasDraft=Boolean(c.id&&(c.draft||state.draftResult?.capture?.id===c.id));
  $('reviewReady').hidden=!hasDraft;$('prepare').classList?.toggle('primary',!hasDraft);
  const create=$('noteStructure').value==='single'?tx('panel_flow_create_one'):tx('panel_flow_create_many');
  $('prepare').textContent=hasDraft?tx('panel_flow_regenerate'):create;
  $('reviewReady').textContent=tx('panel_flow_open_review');
  const extracts=state.autoReview!==false;
  $('extractVideo').textContent=extracts?create:tx('panel_extraer_subtitulos_o_transcribir');
  $('extractPdf').textContent=extracts?create:tx('panel_extraer_pdf_y_paginas');
  $('extractReader').textContent=extracts?create:tx('panel_extraer_libro_completo');
  $('autoReviewLabel').hidden=!(manualImport||captureTarget&&captureTarget!=='note');
  $('attachments').hidden=!(c.images?.length||!c.id&&c.embeds?.length);
  const kinds={article:tx('panel_articulo'),quote:tx('panel_frase'),image:tx('panel_imagen'),pdf:'PDF',video:tx('panel_video_audio')};
  $('kind').textContent=captureTarget==='reader'?tx('panel_lector_html'):captureTarget==='pdf'?'PDF':captureTarget==='video'?tx('panel_video_audio'):kinds[c.kind]||tx('panel_sin_contenido');
  $('captureHint').textContent=hasDraft?tx('panel_flow_ready_review'):captureTarget==='video'?tx('panel_flow_video_hint'):captureTarget==='reader'?tx('panel_flow_reader_hint'):captureTarget==='pdf'?tx('panel_flow_pdf_hint'):captureTarget==='note'?tx('panel_flow_note_hint'):tx('panel_flow_unavailable_hint');
  if(['video','reader','pdf'].includes(captureTarget))$('captureHint').textContent+=' '+(extracts?tx('panel_flow_note_hint'):tx('panel_flow_extracted_hint'));
  captureSettingsSummary();
}
function captureSettingsSummary(){
  const parts=[],modes={article:tx('panel_articulo'),course:tx('panel_flow_mode_course'),podcast:tx('panel_flow_mode_podcast')};
  if(modes[state.captureMode])parts.push(modes[state.captureMode]);
  if($('provider').value==='manual')parts.push(tx('panel_flow_manual'));
  if(state.autoReview===false&&(manualImport||captureTarget&&captureTarget!=='note'))parts.push(tx('panel_flow_extract_only'));
  $('captureSettingsState').textContent=parts.length?' · '+parts.join(' · '):'';
}
// [UI] Embedded resources are chosen like images; heavy clips start unchecked.
function drawEmbeds(c){
  const items=c.id?[]:c.embeds||[];
  $('embedSection').hidden=!items.length;$('embeds').replaceChildren();
  const groups=[['clip',tx('panel_clips_de_video'),'▶'],['pen',tx('panel_demos_de_codepen'),'</>'],['tweet',tx('panel_publicaciones_de_x'),'𝕏']];
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
      const name=document.createElement('strong');name.textContent=item.title||item.author||tx('bg_recurso');
      const detail=document.createElement('span');
      detail.textContent=type==='clip'?[item.duration?Math.round(item.duration)+' s':'',item.size?(item.size/1000000).toFixed(1)+' MB':''].filter(Boolean).join(' · ')||tx('panel_clip_silencioso'):type==='pen'?'CodePen · @'+item.user+tx('panel_copia_ejecutable_sin_conexion'):(item.text||tx('panel_publicacion_incrustada')).slice(0,140);
      info.append(name,detail);
      if(item.warning){const warning=document.createElement('small');warning.className='embed-warning';warning.textContent=item.warning;info.append(warning);}
      // Hover or keyboard focus scrolls the article to the resource and outlines it, as with images.
      const tag={clip:tx('panel_clip'),pen:tx('panel_demo'),tweet:tx('panel_publicacion')}[type]+' '+(list.indexOf(item)+1);
      label.addEventListener('mouseenter',()=>locate(c,item.index,false,tag));label.addEventListener('mouseleave',()=>locate(c,item.index,true,tag));
      label.addEventListener('focusin',()=>locate(c,item.index,false,tag));label.addEventListener('focusout',()=>locate(c,item.index,true,tag));
      label.append(check,thumb,info);$('embeds').append(label);
    }
  }
  embedSelection();
}
function embedSelection(){
  const checks=[...document.querySelectorAll('#embeds input[type=checkbox]')];
  $('embedCount').textContent=tx('panel_flow_attachments_count',[checks.filter(e=>e.checked).length,checks.length]);
  for(const check of checks)check.disabled=Boolean(state.operation);
  attachmentSummary();
}
function pendingControls(){
  for(const button of document.querySelectorAll('.pending-resume,.pending-dismiss'))button.disabled=Boolean(state.operation)||button.dataset.running==='true';
}
function pendingDismiss(target,title){
  const button=document.createElement('button');button.type='button';button.className='pending-dismiss';button.textContent='×';
  button.title=tx('panel_descartar_pendiente',[title]);button.setAttribute('aria-label',button.title);
  button.onclick=run(async()=>{
    const index=[...document.querySelectorAll('.pending-dismiss')].indexOf(button);
    button.disabled=true;
    try{
      await browser.runtime.sendMessage({type:'discardPending',...target});await refresh();
      const remaining=[...document.querySelectorAll('.pending-dismiss')].filter(b=>!b.disabled);
      (remaining[Math.min(index,remaining.length-1)]||$('options')).focus();
    }finally{pendingControls();}
  });
  return button;
}
async function refresh() {
  try {
    status=await call({action:"status"});
    if(!structureInitialized){$('noteStructure').value=state.currentCapture?.note_structure||status.config.note_structure||'single';structureInitialized=true;}$("connection").textContent=tx('panel_flow_connected');
    if($('connection').dataset)$('connection').dataset.state='ready';
    // [UI] The vault profile decides where notes go: missing or outdated, say so before preparing.
    const profile=status.profile||{};$('profileNotice').hidden=!(profile.missing||profile.problems?.length);
    $('profileNoticeText').textContent=profile.missing?(profile.message||tx('panel_este_vault_aun_no_tiene_perfil_escanealo')):profile.problems?.length?profile.problems[0]+(profile.problems.length>1?tx('panel_y_1_mas',[profile.problems.length-1]):''):'';
    if(serviceError && $('error').textContent === serviceError) $('error').hidden=true;
    serviceError='';
    $('recoverSection').hidden=!(status.jobs||[]).length;$('recoverJobs').replaceChildren();
    const {workSources={}}=await browser.storage.local.get('workSources');
    for(const job of status.jobs||[]){
      const row=document.createElement('div');row.className='job-row';row.dataset.job=job.id;
      const title=workSources[job.id]?.title||({upload_finish:tx('panel_extraccion_de_archivo'),draft:tx('panel_preparacion_de_nota'),video_url:tx('panel_video_de_plataforma')})[job.action];
      const label=document.createElement('span');label.textContent=title+' · '+({cancelled:tx('panel_cancelado'),interrupted:tx('panel_interrumpido'),failed:tx('panel_error_recuperable'),pending:tx('panel_pendiente'),running:tx('panel_en_curso_job')}[job.status]||tx('panel_pendiente'));
      const button=document.createElement('button');button.className='pending-resume';button.textContent=tx('panel_reanudar');
      button.onclick=run(async()=>{await browser.runtime.sendMessage({type:'resumeJob',job:job.id});await refresh();});
      const dismiss=pendingDismiss({job:job.id},title);
      button.dataset.running=dismiss.dataset.running=String(job.status==='running');
      row.append(label,button,dismiss);$('recoverJobs').append(row);
    }
    $("provider").value=status.config.provider;$("pending").replaceChildren();
    for(const c of status.pending){
      const row=document.createElement('div');row.className='pending-row';row.dataset.capture=c.id;
      const b=document.createElement('button');b.className='pending-item pending-resume';b.textContent=c.title+' · '+c.kind;
      b.addEventListener('click',run(async()=>browser.runtime.sendMessage({type:'resume',id:c.id,windowId:panelWindowId})));
      row.append(b,pendingDismiss({id:c.id},c.title));$('pending').append(row);
    }
    pendingControls();
    if(!status.pending.length)$("pending").textContent=tx('panel_no_hay_capturas_pendientes');
    $('pendingSection').hidden=!(status.pending.length||(status.jobs||[]).length);
    // A job that becomes recoverable while the panel is open is shown where the notice points.
    const jobIds=(status.jobs||[]).filter(j=>j.status!=='running').map(j=>j.id);
    if(knownJobs&&jobIds.some(id=>!knownJobs.has(id)))$('pendingSection').open=true;
    knownJobs=new Set(jobIds);
    showHealth(AnacoObDiagnosis.status(status,browser.runtime.getManifest().version)[0]);
    captureSettingsSummary();
  }catch(error){
    // The service is missing or broken: explain the fix instead of a raw error.
    serviceError=error.message;$("connection").textContent=tx('panel_flow_disconnected');if($('connection').dataset)$('connection').dataset.state='error';showHealth(AnacoObDiagnosis.connection(error));
  }
}
async function sync(changes) {
  state=await browser.storage.local.get(["currentCapture","draftResult","operation","operationProgress","operationError","operationDiagnostic","lastResult","pageContext","activeWork","autoReview","reviewSessions","captureMode"]);
  if(!manualImport&&Number.isInteger(panelWindowId)){const own=await browser.runtime.sendMessage({type:'panelCapture',windowId:panelWindowId});if(own){boundSource=own.panelSource;Object.assign(state,own);}}
  $('boundPage').textContent=boundSource?tx('panel_bound_page',[state.currentCapture?.title||boundSource.url||'']):'';
  $('useActiveTab').disabled=Boolean(state.operation)||Boolean(globalThis.AnacoObBatchUI?.busy);
  $('captureMode').value=state.captureMode||'auto';$('captureMode').disabled=Boolean(state.operation);
  reviewMenu();
  $('autoReview').checked=state.autoReview!==false;
  $('extractVideo').textContent=$('autoReview').checked?tx('panel_crear_nota_del_video'):tx('panel_extraer_subtitulos_o_transcribir');
  $('extractPdf').textContent=$('autoReview').checked?tx('panel_crear_nota_del_pdf'):tx('panel_extraer_pdf_y_paginas');
  $('extractReader').textContent=$('autoReview').checked?tx('panel_crear_notas_del_libro_completo'):tx('panel_extraer_libro_completo');
  $('importButton').textContent=$('autoReview').checked?tx('panel_extraer_y_preparar_nota'):tx('panel_extraer_archivo');
  if(!changes||changes.currentCapture||changes.draftResult||changes.pageContext||changes.panelBindingRevision)drawCapture(state.currentCapture);
  renderCaptureFlow();
  pendingControls();
  captureSettingsSummary();
  const page=state.pageContext;
  $("pageStatus").textContent=manualImport?tx('panel_importacion_manual_de_un_archivo_local'):page?.status==='loading'?tx('panel_detectando_el_contenido_de_esta_pestana'):page?.url?(host=>state.operation?tx('panel_origen_del_trabajo_1',[host]):tx('panel_pagina_1',[host]))((()=>{try{return new URL(page.url).hostname;}catch{return tx('panel_archivo_local');}})()):'';
  $('pageStatus').hidden=Boolean(state.currentCapture&&!manualImport&&page?.status!=='loading');
  if(activeReview&&!state.operationError)$('error').hidden=true;
  else if(page?.status==='error')showError(page.error);
  else if(page?.status==='ready'&&!state.operationError&&!state.currentCapture?.detectionError)$("error").hidden=true;
  $("operation").textContent=state.operation||'';$("operation").hidden=!state.operation;workDisplay();imageSelection();brandProgress();
  $("prepare").disabled=Boolean(state.operation)||(!state.currentCapture?.id&&state.currentCapture?.kind==="pdf");$("recapture").disabled=Boolean(state.operation);
  for(const id of ["importButton","extractPdf","extractVideo","extractReader"])$(id).disabled=Boolean(state.operation);
  for(const id of ['provider','intent','noteStructure'])$(id).disabled=Boolean(state.operation);
  for(const id of ['captureTarget','autoReview','pdfPages','pdfResource','videoResource'])$(id).disabled=Boolean(state.operation);
  if(state.operationError){
    showError(new Error(state.operationError));
    $("diagnostic").hidden=false;
    const report={error:state.operationError,page:state.currentCapture?.url?new URL(state.currentCapture.url).hostname:'',...state.currentCapture?.detection,...(state.operationDiagnostic?{extraction:state.operationDiagnostic}:{})};
    $("detectionReport").textContent=JSON.stringify(report,null,2);
  }
  if(state.lastResult&&!state.currentCapture&&state.pageContext?.status!=='loading'){
    $("success").replaceChildren(document.createTextNode(tx('panel_nota_guardada')+state.lastResult.relative+" "));
    const link=document.createElement("a");link.href=state.lastResult.obsidian_url;link.textContent=tx('panel_abrir_en_obsidian');$("success").append(link);$("success").hidden=false;
  }
  if(changes?.settingsRevision){structureInitialized=false;refresh().catch(showError);}
  else if(changes?.currentCapture&&!state.operation)refresh().catch(showError);
  else if(changes?.operation&&!state.operation)refresh().catch(showError);
}
let healthAction=null;
function showHealth(problem){
  $('healthNotice').hidden=!problem;if(!problem)return;
  $('healthTitle').textContent=problem.title+'.';$('healthText').textContent=problem.text;
  $('healthAction').textContent=problem.action==='options'?tx('panel_abrir_opciones'):tx('panel_como_instalarlo');healthAction=problem.action;
}
$('healthAction').onclick=run(async()=>healthAction==='options'?browser.runtime.sendMessage({type:'openOptions',windowId:panelWindowId}):browser.tabs.create({url:browser.runtime.getURL('welcome.html#install')}));
function reviewMenu(){
  const previous=activeReview;
  const sessions=Object.values(state.reviewSessions||{}).filter(r=>r.windowId===panelWindowId&&r.tabActive).sort((a,b)=>b.updatedAt-a.updatedAt);
  const focused=sessions.find(r=>r.tabActive);if(focused)preferredReview=focused.id;
  activeReview=focused||sessions.find(r=>r.id===preferredReview)||sessions[0]||null;
  $('reviewWorkspace').hidden=!activeReview;$('captureWorkspace').hidden=Boolean(activeReview);
  if(!activeReview){if(previous&&!manualImport)detectCurrent(true);return;}
  const r=activeReview;
  $('reviewChooser').hidden=$('reviewChooserLabel').hidden=sessions.length<2;
  $('reviewChooser').replaceChildren();
  for(const item of sessions)$('reviewChooser').append(new Option(item.title,item.id));
  $('reviewChooser').value=r.id;$('reviewMenuTitle').textContent=r.title;
  $('reviewMenuStatus').textContent=tx('panel_1_de_2_notas_incluidas_3',[r.notes.filter(n=>n.selected).length,r.notes.length,r.busy?tx('panel_trabajo_en_curso'):r.status||tx('options_revisa_la_propuesta')]);
  $('reviewMenuNotes').replaceChildren();
  for(const note of r.notes){
    const row=document.createElement('div');row.className='review-menu-note';
    const check=document.createElement('input');check.type='checkbox';check.checked=note.selected;check.disabled=r.busy;check.setAttribute('aria-label',tx('panel_incluir_1',[note.title]));
    check.onchange=()=>reviewAction('include',note.id,check.checked).catch(showError);
    const button=document.createElement('button');button.type='button';button.textContent=note.title;button.dataset.reviewNote=note.id;button.setAttribute('aria-current',String(note.id===r.activeNote));button.disabled=r.busy;
    const links=document.createElement('small');links.textContent=tx('panel_1_con_notas_existentes_2_entre_temas',[note.externalLinks||0,note.internalLinks||0]);button.append(links);
    button.onclick=()=>reviewAction('note',note.id).catch(showError);row.append(check,button);$('reviewMenuNotes').append(row);
  }
  for(const id of ['reviewRead','reviewEdit','reviewProperties','reviewConnections','reviewRefreshLinks','reviewSplit'])$(id).disabled=r.busy;
  $('reviewRead').setAttribute('aria-pressed',String(r.view==='read'));
  $('reviewEdit').setAttribute('aria-pressed',String(r.view==='edit'));
  $('reviewSave').disabled=!r.canSave||r.busy;$('reviewSave').textContent=r.saveLabel||tx('panel_guardar_y_volver');
}
function reviewAction(command,note,value){
  if(!activeReview)return Promise.reject(new Error(tx('panel_no_hay_una_revision_abierta_en_esta_vent')));
  return browser.runtime.sendMessage({type:'reviewCommand',id:activeReview.id,windowId:panelWindowId,command,note,value});
}
for(const [id,action] of Object.entries({reviewRead:'read',reviewEdit:'edit',reviewProperties:'properties',reviewConnections:'connections',reviewRefreshLinks:'refreshLinks',reviewSplit:'split',reviewFocus:'focus',reviewSave:'save'}))$(id).onclick=run(()=>reviewAction(action));
$('reviewChooser').onchange=()=>{preferredReview=$('reviewChooser').value;browser.runtime.sendMessage({type:'reviewCommand',id:preferredReview,windowId:panelWindowId,command:'focus'}).catch(showError);};
$("profileReviewButton").onclick=run(async()=>browser.runtime.sendMessage({type:'openOptions',windowId:panelWindowId}));
$("options").onclick=run(async()=>{
  await browser.runtime.sendMessage({type:'openOptions',windowId:panelWindowId});
});
$('cancelJob').onclick=run(async()=>{await browser.runtime.sendMessage({type:'cancelWork'});});
$('useActiveTab').onclick=run(async()=>{await browser.runtime.sendMessage({type:'detectActive',windowId:panelWindowId,useActive:true,fresh:false});await sync();});
$('captureMode').onchange=run(async()=>{
  await browser.storage.local.set({captureMode:$('captureMode').value});
  if(!manualImport)await browser.runtime.sendMessage({type:'detectActive',fresh:true,windowId:panelWindowId});
});
$('autoReview').onchange=()=>browser.storage.local.set({autoReview:$('autoReview').checked});
$('captureTarget').onchange=()=>{captureTarget=$('captureTarget').value;renderCaptureFlow();};
$('noteStructure').onchange=()=>renderCaptureFlow();
$('provider').onchange=()=>captureSettingsSummary();
const preparation=()=>({prepareAfter:state.autoReview!==false,provider:$('provider').value,intent:$('intent').value,note_structure:$('noteStructure').value});
for(const id of ["captureEmpty","recapture"])$(id).onclick=run(async()=>{
  const origins=[state.pageContext?.url,state.currentCapture?.url].filter(Boolean);
  const granted=await requestOrigins(origins);
  if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_a_esta_pagina'));
  await browser.runtime.sendMessage({type:"detectActive",windowId:panelWindowId});
});
$("prepare").onclick=run(async()=>{
  const selected=[...document.querySelectorAll("#images input:checked")].map(i=>Number(i.value));
  if(selected.length>8)throw new Error(tx('panel_selecciona_como_maximo_ocho_imagenes'));
  const c=state.currentCapture;
  const embeds=[...document.querySelectorAll("#embeds input:checked")].map(i=>Number(i.dataset.embed));
  const embedURLs=embeds.map(i=>c.embeds?.[i]).flatMap(e=>e?.type==='clip'?[e.url]:e?.type==='pen'?['https://codepen.io/','https://cdpn.io/']:[]);
  const origins=[...new Set([...selected.map(i=>c.images[i].url),...embedURLs].map(url=>{try{const u=new URL(url);return /^https?:$/.test(u.protocol)?u.protocol+"//"+u.hostname+"/*":null;}catch{return null;}}).filter(Boolean))];
  // Keep this call before any await so Firefox preserves the user gesture.
  if(origins.length&&!c.id){const granted=await browser.permissions.request({origins});if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_a_las_imagenes'));}
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
  if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_a_las_paginas_'));
  await browser.runtime.sendMessage({type:'extractReader',token:c.token,...preparation()});
});
$("extractPdf").onclick=run(async()=>{
  const c=state.currentCapture,resource=c.documents[Number($("pdfResource").value)];
  if(resource.url.startsWith("file:"))throw new Error(tx('panel_para_este_pdf_local_usa_importar_archivo'));
  const granted=await requestOrigins([resource.url]);if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_al_pdf'));
  await browser.runtime.sendMessage({type:"importResource",token:c.token,kind:"pdf",url:resource.url,pageUrl:c.url,name:(resource.title||c.title).replace(/\.pdf$/i,"")+".pdf",pages:$("pdfPages").value,...preparation()});
});
$("extractVideo").onclick=run(async()=>{
  const c=state.currentCapture,video=c.videos[Number($("videoResource").value)];
  if(video.extractable===false)throw new Error(video.unavailableReason||tx('panel_no_hay_audio_o_subtitulos_accesibles_en_'));
  const platform=AnacoObMedia.platformURL(video.url);
  const track=platform?null:[...(video.tracks||[])].sort((a,b)=>(!a.language?.startsWith("es"))-(!b.language?.startsWith("es")))[0];
  const direct=video.download||(/^https?:/.test(video.url)&&!platform&&!AnacoObMedia.apiURL(video.url)&&video.url!==c.url?video.url:null);
  const granted=await requestOrigins([track?.url,direct,...(video.download?['https://drive.usercontent.google.com/','https://*.googleusercontent.com/']:[])]);
  if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_al_recurso_de_'));
  const audio=direct&&!/\.mpd(?:[?#]|$)/i.test(direct)?(/\.m3u8(?:[?#]|$)/i.test(direct)?{kind:'video-hls',url:direct}:{kind:'video',url:direct,name:'video.mp4'}):platform?{kind:'video-platform',url:platform}:null;
  // Browser cues may cover only the part already played. Platform extraction
  // fetches the full transcript and falls back to downloading audio.
  const request=platform?audio:video.subtitles?{kind:'subtitles',text:video.subtitles,fallback:audio}:track?{kind:'subtitle-url',url:track.url,frameId:video.frameId,fallback:audio}:audio;
  if(!request)throw new Error(tx('panel_el_reproductor_no_expone_un_recurso_de_a'));
  await browser.runtime.sendMessage({type:"importResource",token:c.token,...request,frameId:video.frameId,frameURL:video.frameURL,title:video.title||c.title,pageUrl:c.url,...preparation()});
});
$("authorizeDetection").onclick=run(async()=>{
  const c=state.currentCapture;
  const granted=await browser.permissions.request({origins:c.requiredOrigins});
  if(!granted)throw new Error(tx('panel_no_se_ha_concedido_acceso_al_contenido_i'));
  await browser.runtime.sendMessage({type:'inspectFrame',token:c.token});
});
$("videoResource").onchange=()=>{
  const video=state.currentCapture?.videos[Number($("videoResource").value)];
  $("extractVideo").hidden=video?.extractable===false;
  if(video?.extractable===false)showError(video.unavailableReason);
};
$("importButton").onclick=run(async()=>{
  let uploadWork;
  const file=$("importFile").files[0];if(!file)throw new Error(tx('panel_selecciona_primero_un_archivo'));
  const limit=/\.(pdf|vtt|srt)$/i.test(file.name)?100000000:1000000000;
  if(file.size>limit)throw new Error(tx('panel_limite_100_mb_para_pdf_subtitulos_y_1_gb'));
  uploadWork=await browser.runtime.sendMessage({type:'beginUploadWork',name:file.name,manual:manualImport});
  try{
    const begin=await call({action:"upload_begin",name:file.name,size:file.size,url:manualImport?"":state.currentCapture?.url||""});
    for(let offset=0;offset<file.size;offset+=393216){const bytes=new Uint8Array(await file.slice(offset,offset+393216).arrayBuffer());let binary="";for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));await call({action:"upload_chunk",upload:begin.upload,offset,data:btoa(binary)});}
    await browser.storage.local.set({operation:file.name.toLowerCase().endsWith(".pdf")?tx('panel_leyendo_pdf_y_renderizando_paginas'):tx('panel_transcribiendo_o_leyendo_subtitulos_pued'),operationProgress:null});
    const c=await call({action:"upload_finish",upload:begin.upload,pages:$("importPages").value});
    await browser.runtime.sendMessage({type:"adoptUpload",capture:c,work:uploadWork.work,manual:manualImport,...preparation()});
  }catch(error){await browser.runtime.sendMessage({type:'failWork',work:uploadWork.work,error:error.message});throw error;}
});
browser.storage.onChanged.addListener((changes,area)=>{if(area==="local"&&panelStarted){sync(changes).catch(showError);if(changes.panelBindingRevision&&!manualImport)detectCurrent(false);}});
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
    browser.tabs.onActivated.addListener(info=>{if(panelWindowId===null||info.windowId===panelWindowId){const match=Object.values(state.reviewSessions||{}).find(r=>r.tabId===info.tabId);if(match)preferredReview=match.id;sync().catch(showError);}});
    browser.tabs.onUpdated.addListener((id,change)=>{if(id===boundSource?.tabId&&(change.status==='complete'||change.url))detectCurrent(true,id);});

  }
  await sync();brandIntro();refresh().catch(showError);if(!manualImport)detectCurrent(false);
}
startPanel().catch(showError);
if(typeof setInterval==='function')setInterval(()=>{workDisplay();brandProgress();},1000);
