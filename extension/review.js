const $=id=>document.getElementById(id);
const captureId=new URL(location.href).searchParams.get('capture');
const send=message=>browser.runtime.sendMessage(message);
const native=message=>send({type:'native',message});
let data,previewTimer,previewSequence=0,finished=false,activeNote='source',drafts={},edits={},selected=new Set(),previewNotes=[];
let mergedInto={},history=[],proposal=null,internalNote=null,revisionBusy=false;
let splitProposal=null;
const saveState={disabled:true,label:'Guardar y volver ✓'};
const reviewInstance=crypto.randomUUID();let reviewStatusTimer,lastReviewStatus='',closingReview=false;
function publishReview(){
  clearTimeout(reviewStatusTimer);
  reviewStatusTimer=setTimeout(()=>{
    if(!data)return;
    const status={title:data.capture.title,activeNote,notes:Object.keys(drafts).map(id=>({id,title:edits[id]?.title||drafts[id].title,selected:selected.has(id),externalLinks:(drafts[id].relations||[]).length,internalLinks:id==='source'?0:(drafts[id].links||[]).filter(r=>r.id!=='source').length})),
      busy:revisionBusy||closingReview||$('splitDialog').open||$('revisionDialog').open,canSave:!saveState.disabled,saveLabel:saveState.label,status:$('previewState').textContent,view:$('editPane').hidden?'read':'edit'};
    const encoded=JSON.stringify(status);if(encoded===lastReviewStatus)return;lastReviewStatus=encoded;
    send({type:'reviewStatus',id:captureId,instance:reviewInstance,status}).catch(()=>{});
  },40);
}
const assets=new Map();
function error(e){$('error').textContent=e.message||String(e);$('error').hidden=false;}
const isCollection=()=>Boolean(data?.bundle?.notes?.length);
function formFields(){return {title:$('title').value,context:$('context').value,folder:$('folder').value,filename:$('filename').value,note_type:$('noteType').value,tags:$('tags').value.split(',').map(v=>v.trim()).filter(Boolean),body:$('body').value,
  relations:[...document.querySelectorAll('.relation input:checked')].map(e=>e.value),images:[...document.querySelectorAll('.asset-check:checked')].map(e=>Number(e.value)),
  captions:Object.fromEntries([...document.querySelectorAll('.asset-caption')].map(e=>[e.dataset.index,e.value])),
  relation_kinds:Object.fromEntries([...document.querySelectorAll('[data-relation-kind]')].map(e=>[e.dataset.relationKind,e.value])),
  excluded_links:internalNote===activeNote?[...document.querySelectorAll('[data-new-link]:not(:checked)')].map(e=>e.dataset.newLink):(edits[activeNote]?.excluded_links||[]),
  save_mode:$('saveMode').value,target_path:$('updateTarget').value,update_approved:$('approveUpdate').checked,update_review_hash:edits[activeNote]?.update_review_hash,revision_model:edits[activeNote]?.revision_model};}
function collect(){if(data&&drafts[activeNote])edits[activeNote]=formFields();}
function fields(){collect();return {notes:edits,selected_notes:[...selected],active_note:activeNote,merged_into:mergedInto};}
function persist(){if(data&&!finished)localStorage.setItem('editor:'+captureId,JSON.stringify({id:captureId,fields:fields(),history}));publishReview();}
function enlarge(asset){$('largeImage').src=asset.url;$('largeImage').alt=asset.alt;$('largeCaption').textContent=asset.alt||'Imagen de la fuente';$('imageDialog').showModal();}
function typeOptions(folder,value){
  $('noteType').replaceChildren();
  for(const type of data.types_by_folder[folder]||[]){const option=document.createElement('option');option.value=type;option.textContent=data.note_types[type]||type;$('noteType').append(option);}
  const allowed=data.types_by_folder[folder]||[];
  $('noteType').value=allowed.includes(value)?value:folder.startsWith('07_Clases/')?(activeNote==='source'?'resumen':'apunte'):(activeNote==='source'?'fuente_externa':'nota_atomica');
}
function relations(){
  $('relations').replaceChildren();
  for(const relation of drafts[activeNote].relations||[]){
    const box=document.createElement('div');box.className='relation';
    const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.value=relation.path;check.checked=(edits[activeNote].relations||[]).includes(relation.path);label.append(check,document.createTextNode(' '+relation.path));
    const kind=document.createElement('select');kind.className='relation-kind';kind.dataset.relationKind=relation.path;
    for(const value of data.relation_kinds){const option=document.createElement('option');option.value=value;option.textContent=value;kind.append(option);}kind.value=edits[activeNote].relation_kinds?.[relation.path]||relation.kind||'relaciona';
    const p=document.createElement('p');p.textContent=relation.reason;
    const details=document.createElement('details'),summary=document.createElement('summary'),evidence=document.createElement('p');summary.textContent='Ver evidencia';evidence.className='evidence';evidence.textContent=(relation.evidence_origin==='note'?'En esta nota:\n':'En la captura:\n')+relation.source_evidence+'\n\nEn la nota existente:\n'+relation.note_evidence;details.append(summary,evidence);box.append(label,kind,p,details);$('relations').append(box);
  }
  if(!drafts[activeNote].relations?.length)$('relations').textContent=isCollection()?'Sin conexiones propuestas con notas existentes. Los enlaces entre las notas nuevas se muestran en la vista de lectura.':'Sin conexiones con evidencia suficiente. Puedes relacionarla más adelante.';
}
function applyAssets(){
  const value=edits[activeNote];
  $('model').textContent=value.revision_model?'Revisado con '+value.revision_model:drafts[activeNote].assisted?'Asistido por '+drafts[activeNote].model:'Captura manual · sin resumen generado';
  for(const check of document.querySelectorAll('.asset-check'))check.checked=(value.images||[]).includes(Number(check.value));
  for(const caption of document.querySelectorAll('.asset-caption'))caption.value=value.captions?.[caption.dataset.index]??data.capture.images[Number(caption.dataset.index)].caption??data.capture.images[Number(caption.dataset.index)].alt??'';
  for(const asset of assets.values()){const caption=document.querySelector('.asset-caption[data-index="'+asset.index+'"]');if(caption)asset.alt=caption.value;}
}
function showNote(){
  const value=edits[activeNote];
  for(const key of ['title','context','body','filename'])$(key).value=value[key]||'';
  $('folder').value=value.folder;typeOptions(value.folder,value.note_type);$('tags').value=(value.tags||[]).join(', ');
  $('saveMode').value=value.save_mode||'create';$('updateControls').hidden=$('saveMode').value!=='append';$('updateTarget').value=value.target_path||'';$('approveUpdate').checked=Boolean(value.update_approved);$('updateDiff').replaceChildren();
  internalNote=null;$('newRelations').replaceChildren();revisionScopes();
  relations();applyAssets();
  $('activeNoteLabel').textContent=isCollection()?(selected.has(activeNote)?'':'Excluida del guardado · ')+value.title:'';
}
function switchNote(id){collect();activeNote=id;showNote();persist();clearTimeout(previewTimer);preview();}
async function preview(){
  const sequence=++previewSequence;$('previewState').textContent='Actualizando…';saveState.disabled=true;
  publishReview();
  try{
    const result=await native({action:'preview',id:captureId,fields:fields()});
    if(sequence!==previewSequence)return;
    previewNotes=result.notes||[];
    internalLinks(result.internal_links||[]);updatePreview(result.update);
    $('markdown').textContent=result.markdown;AnacoObRender($('reading'),result.markdown,assets,enlarge,data.capture.vault.split('/').pop());
    const collision=result.collisions?.length?'Ya existe: '+result.collisions.join(', '):'';
    $('duplicate').hidden=!result.duplicate&&!collision;$('duplicate').textContent=collision||(result.duplicate?'Esta captura ya existe: '+result.duplicate:'');
    $('error').hidden=true;$('previewState').textContent='Vista actualizada';
    saveState.label=result.update_count?'Guardar propuesta y volver ✓':isCollection()?`Guardar ${result.selected_count} notas y volver ✓`:'Guardar y volver ✓';
    const unapproved=result.updates_pending?.length; if(unapproved)$('previewState').textContent='Revisa y acepta las ampliaciones pendientes';
    saveState.disabled=Boolean(result.duplicate||collision||finished||closingReview||unapproved||revisionBusy);
  }catch(e){if(sequence===previewSequence){$('previewState').textContent='Revisa los campos';error(e);}}
  finally{publishReview();}
}
function changed(event){
  if(event?.target?.id!=='approveUpdate'){$('approveUpdate').checked=false;if(edits[activeNote])edits[activeNote].update_approved=false;}
  collect();for(const asset of assets.values()){const caption=document.querySelector('.asset-caption[data-index="'+asset.index+'"]');if(caption)asset.alt=caption.value;}
  if(isCollection())$('activeNoteLabel').textContent=(selected.has(activeNote)?'':'Excluida del guardado · ')+edits[activeNote].title;
  persist();++previewSequence;saveState.disabled=true;$('error').hidden=true;clearTimeout(previewTimer);previewTimer=setTimeout(preview,180);
}
async function loadImage(index){
  let offset=0,parts=[],part;
  do{part=await native({action:'image_chunk',id:captureId,index,offset});parts.push(part.data);offset+=part.data.length;if(!part.data&&offset<part.total)throw new Error('La imagen está incompleta.');}while(offset<part.total);
  const binary=atob(parts.join('')),bytes=new Uint8Array(binary.length);for(let i=0;i<bytes.length;i++)bytes[i]=binary.charCodeAt(i);
  const image=data.capture.images[index],asset={url:URL.createObjectURL(new Blob([bytes],{type:part.mime})),alt:image.caption||image.alt||'',index};assets.set(part.relative,asset);
  const button=document.createElement('button');button.className='asset-mini';button.type='button';const img=document.createElement('img');img.src=asset.url;img.alt='';const text=document.createElement('span');text.textContent='Ampliar imagen '+(index+1);button.append(img,text);button.onclick=()=>enlarge(asset);
  const box=document.createElement('div'),label=document.createElement('label'),check=document.createElement('input'),caption=document.createElement('textarea');check.type='checkbox';check.className='asset-check';check.value=index;label.append(check,document.createTextNode(' Incluir en esta nota'));
  caption.className='asset-caption';caption.dataset.index=index;caption.setAttribute('aria-label','Descripción de la imagen '+(index+1));
  const origin=document.createElement('small');origin.className='muted';origin.textContent=({figcaption:'Pie original del HTML',aria_description:'Descripción accesible del HTML',alt:'Texto alternativo del HTML',aria_label:'Etiqueta accesible del HTML',title:'Título de la imagen',filename:'Nombre del archivo · pista sin verificación visual',vision:'Descripción por análisis visual',vision_cache:'Descripción visual reutilizada · sin nuevo análisis'})[image.caption_source]||'Descripción existente';
  box.append(label,button,origin,caption);$('assetList').append(box);
}
function setView(edit){$('editPane').hidden=!edit;$('reading').hidden=edit;if(!edit)preview();else publishReview();}
async function finish(decision){
  if(closingReview||finished&&decision!=='back')return;
  if(decision==='save'&&saveState.disabled)return;
  $('error').hidden=true;persist();clearTimeout(previewTimer);for(const id of ['discard','back'])$(id).disabled=true;
  $('operation').textContent=decision==='save'?'Guardando la propuesta revisada…':'Volviendo al origen…';$('operation').hidden=false;
  closingReview=true;saveState.disabled=true;publishReview();
  try{
    const result=await send({type:'finishReview',id:captureId,decision,fields:fields()});
    if(result?.returnError){finished=Boolean(result.completed);$('success').textContent=decision==='save'?'Propuesta guardada. '+result.returnError:result.returnError;$('success').hidden=false;$('back').disabled=false;$('operation').hidden=true;closingReview=false;publishReview();}
  }catch(e){error(e);$('operation').hidden=true;for(const id of ['discard','back'])$(id).disabled=false;closingReview=false;await preview();error(e);}
}
function updateFilename(){
  const old=$('filename').value,date=old.match(/\d{4}-\d{2}-\d{2}/)?.[0]||new Date().toISOString().slice(0,10),folder=$('folder').value,type=$('noteType').value;
  const sep=folder.startsWith('07_Clases/')?'-':'_',slug=$('title').value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,sep).replace(/^[-_]+|[-_]+$/g,'').slice(0,100)||'captura';
  const suffix=type==='fuente_externa'&&['quote','image'].includes(data.capture.kind)?'_'+(data.capture.kind==='quote'?'frase':'imagen')+'_'+(data.capture.source_fingerprint||data.capture.fingerprint).slice(0,6):'';
  $('filename').value=folder.startsWith('07_Clases/')?`${type}_${date}_${slug}.md`:type==='fuente_externa'?`fuente_${date}_${slug}${suffix}.md`:`nota_${type==='indice'?'indice_':''}${slug}.md`;
}
function internalLinks(values){
  $('newRelations').replaceChildren();internalNote=activeNote;
  for(const value of values){const box=document.createElement('div');box.className='internal-link';const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.dataset.newLink=value.id;check.checked=value.accepted;label.append(check,document.createTextNode(' '+value.title));const reason=document.createElement('small');reason.textContent=value.kind+' · '+value.reason;box.append(label,reason);$('newRelations').append(box);
    if(value.source_evidence){const details=document.createElement('details'),summary=document.createElement('summary'),text=document.createElement('p');summary.textContent=value.stale?'La evidencia cambió · buscar conexiones':'Ver qué conecta las dos notas';text.className='evidence';text.textContent='En esta nota:\n'+value.source_evidence+'\n\nEn «'+value.title+'»:\n'+value.target_evidence;details.append(summary,text);box.append(details);}
    check.onchange=()=>{if(check.checked&&edits[value.id])edits[value.id].excluded_links=(edits[value.id].excluded_links||[]).filter(v=>v!==activeNote);changed();};
  }
  if(!values.length)$('newRelations').textContent='Sin conexiones internas para esta selección.';
}
function updatePreview(update){
  $('updateDiff').replaceChildren();
  if(!update)return;
  if(!update.approved&&$('approveUpdate').checked){$('approveUpdate').checked=false;edits[activeNote].update_approved=false;}
  edits[activeNote].update_review_hash=update.review_hash;
  const details=document.createElement('details'),summary=document.createElement('summary'),before=document.createElement('pre');summary.textContent='Ver contenido actual';before.textContent=update.before;details.append(summary,before);
  const title=document.createElement('h3'),addition=document.createElement('pre');title.textContent='Se añadirá al final';addition.className='update-addition';addition.textContent=update.addition;$('updateDiff').append(details,title,addition);
}
function revisionScopes(){
  const previous=$('revisionScope').value;$('revisionScope').replaceChildren(new Option('Toda esta nota','all'));
  for(const [index,match] of [...$('body').value.matchAll(/^##\s+(.+)$/gm)].entries())$('revisionScope').append(new Option(match[1],String(index)));
  if([...$('revisionScope').options].some(v=>v.value===previous))$('revisionScope').value=previous;
  $('mergeNote').replaceChildren();for(const id of selected)if(id!==activeNote&&id!=='source')$('mergeNote').append(new Option(edits[id].title,id));
  $('mergeControls').hidden=!isCollection()||!$('mergeNote').options.length;
}
async function proposeRevision(mode){
  if(revisionBusy)return;persist();revisionBusy=true;$('cancelRevision').hidden=false;$('revisionStatus').textContent='Preparando un cambio revisable…';saveState.disabled=true;
  try{
    const result=await send({type:'revise',id:captureId,note:activeNote,fields:fields(),mode,section:mode==='merge'?'all':$('revisionScope').value,other:$('mergeNote').value,instruction:$('revisionInstruction').value});
    proposal=result;$('revisionBefore').textContent=result.before;$('revisionAfter').textContent=result.after;$('revisionDialog').showModal();$('revisionStatus').textContent='Revisa la propuesta antes de aplicarla.';
  }catch(e){error(e);$('revisionStatus').textContent='El borrador conserva tus ediciones.';}
  finally{revisionBusy=false;$('cancelRevision').hidden=true;preview();}
}
async function proposeSplit(){
  if(revisionBusy)return;
  persist();revisionBusy=true;$('cancelRevision').hidden=false;
  $('revisionStatus').textContent='Estudiando temas para sugerir una división…';saveState.disabled=true;
  try{
    const result=await send({type:'proposeSplit',id:captureId,note:activeNote,fields:fields()});
    $('splitReason').textContent=result.rationale;
    if(!result.recommended){$('revisionStatus').textContent=result.rationale;return;}
    splitProposal=result;
    AnacoObRender($('splitSummary'),result.summary,assets,enlarge,data.capture.vault.split('/').pop());
    $('splitNotes').replaceChildren();
    for(const note of result.notes){
      const section=document.createElement('section');section.className='card';
      const title=document.createElement('h3'),purpose=document.createElement('p');title.textContent=note.title;purpose.textContent=note.purpose;
      const details=document.createElement('details'),summary=document.createElement('summary'),body=document.createElement('div');
      summary.textContent='Ver contenido propuesto';body.className='markdown-body';AnacoObRender(body,note.body,assets,enlarge,data.capture.vault.split('/').pop());
      details.append(summary,body);section.append(title,purpose,details);$('splitNotes').append(section);
    }
    $('splitDialog').showModal();$('revisionStatus').textContent='Sugerencia preparada. La nota todavía no se ha dividido.';
  }catch(e){error(e);$('revisionStatus').textContent='La nota conserva su contenido y tus ediciones.';}
  finally{revisionBusy=false;$('cancelRevision').hidden=true;preview();}
}
async function refreshConnections(){
  if(revisionBusy)return;
  persist();revisionBusy=true;saveState.disabled=true;
  $('connectionStatus').textContent='Buscando relaciones para cada tema y entre las notas…';
  try{
    const result=await send({type:'refreshConnections',id:captureId,fields:fields()});
    collect();
    for(const [id,metadata] of Object.entries(result.notes))if(drafts[id]){
      Object.assign(drafts[id],metadata);
      edits[id].relations=(edits[id].relations||[]).filter(path=>metadata.relations.some(r=>r.path===path));
    }
    data.capture.connections=result.stats;
    const targets=new Set([...$('updateTarget').options].map(o=>o.value));
    for(const candidate of result.candidates)if(!targets.has(candidate.path)){$('updateTarget').append(new Option(candidate.title+' · '+candidate.path,candidate.path));targets.add(candidate.path);}
    relations();
    $('connectionStatus').textContent=`${result.stats.external} conexiones propuestas con notas existentes · ${result.stats.internal} entre temas · ${result.stats.candidates} candidatas revisadas`;
    persist();
  }catch(e){error(e);$('connectionStatus').textContent='No se completó la búsqueda. Puedes reintentarlo sin regenerar la nota.';}
  finally{revisionBusy=false;await preview();}
}
async function splitDecision(decision){
  if(!splitProposal||$('acceptSplit').disabled)return;
  const pending=splitProposal;$('acceptSplit').disabled=$('rejectSplit').disabled=true;
  try{
    const result=await send({type:'splitDecision',id:captureId,proposal:pending.id,decision,fields:fields()});
    if(decision==='accept'){
      localStorage.setItem('editor:'+captureId,JSON.stringify({id:captureId,fields:result.fields,history:[]}));
      location.reload();return;
    }
    splitProposal=null;$('splitDialog').close();$('revisionStatus').textContent='Sugerencia descartada. Conservas la nota actual.';
  }catch(e){error(e);$('splitDialog').close();$('revisionStatus').textContent=e.message;}
  finally{$('acceptSplit').disabled=$('rejectSplit').disabled=false;}
}
function acceptRevision(){
  collect();if(!proposal||edits[proposal.note].body!==proposal.before){error(new Error('El texto cambió mientras se preparaba la propuesta. Solicita el ajuste de nuevo.'));return;}
  if(proposal.merged&&proposal.merged_before!==edits[proposal.merged].body){error(new Error('La otra nota cambió. Solicita de nuevo la integración.'));return;}
  history.push(JSON.parse(JSON.stringify(fields())));history=history.slice(-5);
  const value=edits[proposal.note];value.body=proposal.after;value.revision_model=proposal.model;value.update_approved=false;
  if(proposal.merged){const other=edits[proposal.merged];selected.delete(proposal.merged);mergedInto[proposal.merged]=proposal.note;for(const [id,target] of Object.entries(mergedInto))if(target===proposal.merged)mergedInto[id]=proposal.note;value.images=[...new Set([...value.images,...other.images])];value.relations=[...new Set([...value.relations,...other.relations])];value.relation_kinds={...other.relation_kinds,...value.relation_kinds};value.captions={...other.captions,...value.captions};}
  activeNote=proposal.note;proposal=null;$('revisionDialog').close();$('undoRevision').disabled=false;showNote();persist();preview();
}
function undoRevision(){const snapshot=history.pop();if(!snapshot)return;edits=snapshot.notes;selected=new Set(snapshot.selected_notes);activeNote=snapshot.active_note;mergedInto=snapshot.merged_into||{};showNote();$('undoRevision').disabled=!history.length;persist();preview();}
async function init(){
  if(!/^[a-f0-9]{32}$/.test(captureId||''))throw new Error('No se ha indicado una captura válida.');
  data=await send({type:'reviewData',id:captureId});document.title=data.draft.title+' · Anaco';
  drafts={source:data.draft,...Object.fromEntries((data.bundle?.notes||[]).map(note=>[note.id,note]))};selected=new Set(Object.keys(drafts));
  for(const [id,draft] of Object.entries(drafts))edits[id]={title:draft.title,context:draft.context,body:draft.body,folder:draft.folder,filename:draft.filename,note_type:draft.note_type||(draft.folder.startsWith('07_Clases/')?'resumen':'fuente_externa'),tags:draft.tags,images:draft.selected_images||[],captions:{},relations:[]};
  for(const folder of data.folders){const option=document.createElement('option');option.value=folder;option.textContent=folder;$('folder').append(option);}
  let edited;try{edited=JSON.parse(localStorage.getItem('editor:'+captureId)||'null');}catch{}
  if(edited?.id===captureId){
    if(edited.fields.notes){for(const [id,value] of Object.entries(edited.fields.notes))if(edits[id])edits[id]={...edits[id],...value};selected=new Set((edited.fields.selected_notes||[]).filter(id=>drafts[id]));activeNote=drafts[edited.fields.active_note]?edited.fields.active_note:'source';mergedInto=edited.fields.merged_into||{};history=edited.history||[];}
    else if(!isCollection()&&!edited.fields.notes)edits.source={...edits.source,...edited.fields};
  }
  $('updateTarget').append(new Option('Selecciona una nota existente',''));
  for(const candidate of data.candidates)$('updateTarget').append(new Option(candidate.title+' · '+candidate.path,candidate.path));
  $('undoRevision').disabled=!history.length;
  $('source').textContent=data.capture.title;if(/^https?:/.test(data.capture.url))$('source').href=data.capture.url;
  $('model').textContent=data.draft.assisted?'Asistido por '+data.draft.model:'Captura manual · sin resumen generado';
  const rationale=data.bundle?.rationale||data.draft.rationale;
  $('editorialReason').hidden=!rationale;$('editorialReason').textContent=rationale||'';
  showNote();$('workspace').hidden=false;$('assetCard').hidden=!data.capture.images.length;
  publishReview();
  await Promise.all(data.capture.images.map((_,i)=>loadImage(i).catch(e=>{const p=document.createElement('p');p.textContent='No se pudo mostrar la imagen '+(i+1)+': '+e.message;$('assetList').append(p);})));
  applyAssets();
  if(data.capture.connections){const stats=data.capture.connections;$('connectionStatus').textContent=`${stats.external} conexiones con notas existentes · ${stats.internal} entre temas · ${stats.candidates} candidatas revisadas`;}
  if(!data.capture.connections&&(data.draft.provider==='codex'||!data.draft.provider&&data.draft.assisted||isCollection()))await refreshConnections();
  await preview();$('operation').hidden=true;publishReview();
}
// Cache the background and window before the click so opening the sidebar
// stays inside the user gesture and reuses the explicit-window policy.
Promise.all([browser.runtime.getBackgroundPage(),browser.windows.getCurrent()]).then(([background,win])=>{
  $('openReviewPanel').onclick=()=>background.openSidebar({windowId:win.id}).catch(error);
  $('openReviewPanel').disabled=false;
}).catch(error);
browser.runtime.onMessage.addListener((message,sender)=>{
  if(message.type!=='reviewControl'||message.id!==captureId||message.instance!==reviewInstance||sender.id!==browser.runtime.id)return;
  return (async()=>{
    if(revisionBusy||closingReview||$('splitDialog').open||$('revisionDialog').open)throw new Error('Termina la operación o resuelve la propuesta abierta antes de continuar.');
    const command=message.command;
    if(command==='note'){if(!drafts[message.note])throw new Error('La nota ya no está en la propuesta.');switchNote(message.note);}
    else if(command==='include'){
      if(!drafts[message.note])throw new Error('La nota ya no está en la propuesta.');
      if(message.value){selected.add(message.note);delete mergedInto[message.note];}else selected.delete(message.note);
      changed();
    }else if(command==='read'||command==='edit'){
      $('workspace').classList.remove('properties-open');setView(command==='edit');
      $(command==='edit'?'body':'reading').scrollIntoView({block:'start'});
    }else if(command==='properties'||command==='connections'){
      $('workspace').classList.add('properties-open');
      $(command==='properties'?'title':'relations').scrollIntoView({block:'start'});
    }else if(command==='refreshLinks')await refreshConnections();
    else if(command==='split')await proposeSplit();
    else if(command==='save'){
      if(saveState.disabled)throw new Error('Revisa los campos y conexiones antes de guardar.');
      finish('save');
    }
    publishReview();return {handled:true};
  })();
});
$('splitDialog').addEventListener('close',publishReview);$('revisionDialog').addEventListener('close',publishReview);
$('acceptSplit').onclick=()=>splitDecision('accept');$('rejectSplit').onclick=()=>splitDecision('discard');
$('splitDialog').addEventListener('cancel',event=>{event.preventDefault();splitDecision('discard');});
// input already covers text, selects and checkboxes. Repeating it on a text
// field's blur disables Save between pointerdown and click and loses that click.
$('workspace').addEventListener('input',changed);
$('folder').addEventListener('change',()=>{typeOptions($('folder').value,$('noteType').value);updateFilename();changed();});
$('noteType').addEventListener('change',()=>{updateFilename();changed();});
$('saveMode').onchange=()=>{collect();$('updateControls').hidden=$('saveMode').value!=='append';changed();};
$('updateTarget').onchange=async()=>{if(!$('updateTarget').value)return;try{await native({action:'prepare_update',id:captureId,path:$('updateTarget').value});changed();}catch(e){error(e);}};
$('body').addEventListener('change',revisionScopes);
for(const button of document.querySelectorAll('[data-revise]'))button.onclick=()=>proposeRevision(button.dataset.revise);
$('mergeButton').onclick=()=>proposeRevision('merge');$('acceptRevision').onclick=acceptRevision;$('rejectRevision').onclick=()=>{proposal=null;$('revisionDialog').close();};$('undoRevision').onclick=undoRevision;
$('cancelRevision').onclick=()=>send({type:'cancelWork'}).catch(error);
$('reading').onclick=event=>{const link=event.target.closest('a.wiki-link');if(!link||!isCollection())return;const path=new URL(link.href).searchParams.get('file');const note=previewNotes.find(n=>n.relative.replace(/\.md$/,'')===path);if(note){event.preventDefault();switchNote(note.id);}};
$('discard').onclick=()=>finish('discard');$('back').onclick=()=>finish('back');$('closeImage').onclick=()=>$('imageDialog').close();
window.addEventListener('unload',()=>{for(const asset of assets.values())URL.revokeObjectURL(asset.url);});
init().catch(e=>{$('operation').hidden=true;error(e);});
const reviewBar=document.querySelector('.review-bar');if(typeof ResizeObserver==='function')new ResizeObserver(()=>document.documentElement.style.setProperty('--review-bar-height',reviewBar.getBoundingClientRect().height+'px')).observe(reviewBar);
