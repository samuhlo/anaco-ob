/* Page detection is separate from saved captures and in-flight generation. */
const ZenBrainDetection = (() => {
  const origin = value => { try { const u = new URL(value); return /^https?:$/.test(u.protocol) ? `${u.protocol}//${u.hostname}/*` : null; } catch { return null; } };
  const pdfURL = value => { try { const u = new URL(value); return /\.pdf$/i.test(u.pathname) || /application\/pdf/i.test(u.searchParams.get('type') || u.searchParams.get('content_type') || ''); } catch { return false; } };
  const unique = items => [...new Map(items.map(item => [item.url, item])).values()];
  const usable = c => Boolean(c && (c.contentReady ?? (c.text?.trim().length >= 100 || c.kind === 'quote' || c.kind === 'image')));
  function merge(pages, tab, blocked = [], extra = {}) {
    const top = pages.find(p => p.frameId === 0) || pages[0];
    const content = pages.filter(p => usable(p) && !p.loginPage && !["authentication","wrapper"].includes(p.frameRole));
    const nested = content.filter(p => p.frameId !== 0);
    const possible=nested.length?nested:content;
    const parentOf=new Map(pages.map(p=>[p.frameId,p.parentFrameId]));
    const hasAncestor=(child,id)=>{let current=parentOf.get(child.frameId);const seen=new Set();while(current!==undefined&&!seen.has(current)){if(current===id)return true;seen.add(current);current=parentOf.get(current);}return false;};
    const chosen=possible.filter(p=>!possible.some(child=>child!==p&&hasAncestor(child,p.frameId)));
    const readerPages=pages.filter(p=>p.reader&&!['authentication','wrapper'].includes(p.frameRole)).filter(p=>!pages.some(child=>child!==p&&child.reader&&!['authentication','wrapper'].includes(child.frameRole)&&hasAncestor(child,p.frameId)));
    const reader=readerPages.length?{scope:'detected',overflow:readerPages.some(p=>p.reader.overflow),pages:readerPages.flatMap(p=>(p.reader.pages||[]).map(page=>({...page,frameId:p.frameId}))),frames:[...new Set(readerPages.map(p=>p.frameId))]}:null;
    const base = top || {kind:'article',title:tab.title || 'Página actual',text:'',images:[],warnings:[]};
    const result = {...base, reader, url:tab.url, title: chosen[0]?.title || base.title,
      text: chosen.map(p => p.text).filter(Boolean).join('\n\n').slice(0,120000),
      images: reader?[]:unique(chosen.flatMap(p => (p.images || []).map(i => ({...i, frameId:p.frameId})))),
      documents: unique(pages.flatMap(p => p.documents || [])),
      videos: unique(pages.flatMap(p => (p.videos || []).map(v=>({...v,frameId:p.frameId,frameURL:p.url})))),
      frames: unique(blocked), requiredOrigins:[...new Set(blocked.filter(f=>f.needsPermission!==false).map(f => origin(f.url)).filter(Boolean))],
      contentReady: chosen.length > 0||Boolean(reader?.pages.length), warnings: [...new Set(chosen.flatMap(p => p.warnings || []))],
      detection: {framesRead:pages.length, framesBlocked:blocked.length, framesUnreadable:blocked.filter(f=>f.needsPermission===false).length, loginPage:pages.some(p => p.loginPage),
        platforms:[...new Set(pages.map(p => {try{return new URL(p.url).hostname;}catch{return '';}}))],
        ...extra,reader:Boolean(reader),surfaces:pages.reduce((counts,p)=>{for(const key of ['canvas','svg','backgrounds','blocked'])counts[key]+=(p.surfaces?.[key]||0);return counts;},{canvas:0,svg:0,backgrounds:0,blocked:0}),
        frameDetails:pages.map(p=>({id:p.frameId,parent:p.parentFrameId,host:(()=>{try{return new URL(p.url).hostname;}catch{return '';}})(),role:p.frameRole||'content',readable:usable(p),textChars:p.text?.length||0,images:p.images?.length||0,videos:(p.videos||[]).map(v=>({host:(()=>{try{return new URL(v.url).hostname;}catch{return '';}})(),tracks:v.tracks?.length||0,loadedSubtitles:Boolean(v.subtitles),extractable:v.extractable!==false})),documentType:p.documentType||'',surfaces:p.surfaces})),
        blockedDetails:blocked.map(f=>({host:(()=>{try{return new URL(f.url).hostname;}catch{return '';}})(),id:f.frameId,reason:f.reason||(f.needsPermission===false?'unreadable':'permission-required')}))}
    };
    for(const video of result.videos)if(video.extractable===false&&video.unavailableReason)result.warnings.push(video.unavailableReason);
    if (result.documents.length || result.videos.some(v=>v.extractable!==false)) result.warnings = result.warnings.filter(w => !w.includes('no se han transcrito'));
    return result;
  }
  function problem(c) {
    if (c.contentReady || c.documents?.length || c.videos?.some(v => v.extractable !== false)) return '';
    if(c.detection?.surfaces?.blocked)return 'El lector dibuja sus páginas, pero el navegador impide leer su contenido visual. El diagnóstico indica qué superficies no se han podido capturar.';
    if (c.requiredOrigins?.length) return 'El contenido está dentro de un visor de otro dominio. Autoriza su lectura para detectar el PDF o el vídeo.';
    if (c.detection?.loginPage) return 'La página muestra un inicio de sesión. Entra en el curso y vuelve a detectar su contenido.';
    if (c.videos?.length) return c.videos[0].unavailableReason || 'Veo un reproductor, pero no expone audio ni subtítulos accesibles. Inicia el vídeo y vuelve a detectar.';
    if(c.detection?.framesUnreadable)return 'El visor está cargado, pero no expone contenido legible ni un PDF o audio accesible. Abre el recurso original y vuelve a detectar.';
    return 'No se ha encontrado texto, PDF, vídeo ni imágenes que se puedan capturar en esta página.';
  }
  return {origin, pdfURL, unique, usable, merge, problem};
})();
