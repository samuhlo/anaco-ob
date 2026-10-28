/* Reads only the page selected in the capture panel, with its granted access. */
globalThis.AnacoObCapture = async (input = {}) => {
  const absolute = value => { try { const u = new URL(value, location.href); return /^(https?:|data:|blob:)$/.test(u.protocol) ? u.href : ""; } catch { return ""; } };
  const ignored = 'script,style,noscript,nav,header,footer,aside,form,button,[role="navigation"],[role="banner"],[aria-hidden="true"],.advertisement,.ads,.cookie-banner';
  const selection = window.getSelection();
  const quote = input.selection || selection?.toString() || "";
  const contextNode = selection?.anchorNode?.parentElement?.closest("p,li,blockquote,section,div");
  const bookRoot=document.querySelector('.pdfViewer,.pdf2htmlEX,.book-content,.flipbook,[data-reader],.reveal .slides,#page-container');
  const courseRoot = document.querySelector('#wiki_page_show .show-content,.user_content,#region-main .no-overflow,#region-main .content');
  const providerHost=/(^|\.)contentcontroller\.com$/.test(location.hostname);
  const platformPage=AnacoObMedia.platformURL(location.href);
  const root = bookRoot || courseRoot || document.querySelector("article") || document.querySelector("main,[role=main]") || document.body;
  // Player canvases (ambient light, previews, overlays) are not book pages.
  const readerHint=!platformPage&&Boolean(bookRoot||providerHost||(!document.querySelector('article')&&!root.querySelector('video,audio')&&root.querySelector('canvas')));
  // Course mode and nested frames never receive input.embeds; their capture is unchanged.
  const embeds=input.embeds===true&&!readerHint&&!platformPage&&!input.kind?AnacoObEmbeds.collect(root,{visible:AnacoObSurfaces.visible,absolute}):[];
  const clone = root.cloneNode(true);
  // Remove hidden course pages before converting the clone to Markdown.
  const originals=[...root.querySelectorAll('*')], copies=[...clone.querySelectorAll('*')];
  originals.forEach((node,index)=>{if(!AnacoObSurfaces.visible(node))copies[index]?.remove();});
  clone.querySelectorAll(ignored).forEach(node => node.remove());
  const escape = s => s.replace(/([\\`*_\[\]])/g, "\\$1");
  const codeBlocks=[];
  const codeToken=crypto.randomUUID();
  const fenceFor = value => '`'.repeat(Math.max(3,...[...value.matchAll(/`+/g)].map(m=>m[0].length+1)));
  function md(node) {
    if (node.nodeType === Node.TEXT_NODE) return escape(node.textContent.replace(/\s+/g, " "));
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const tag = node.tagName.toLowerCase();
    if (node.dataset?.anacoObEmbed !== undefined) return '\n\n{{recurso:'+node.dataset.anacoObEmbed+'}}\n\n';
    if (tag === 'pre') {
      const code=node.querySelector('code')||node;
      const language=(code.className+' '+node.className).match(/(?:language|lang)-([a-z0-9_+-]+)/i)?.[1]||node.getAttribute('data-language')||'';
      const value=node.textContent, fence=fenceFor(value);
      codeBlocks.push(fence+language.replace(/[^a-z0-9_+-]/gi,'')+'\n'+value+(value.endsWith('\n')?'':'\n')+fence);
      return '\n\n'+codeToken+':'+(codeBlocks.length-1)+'\n\n';
    }
    if (tag === "img") return "";
    const inner = [...node.childNodes].map(md).join("").trim();
    if (/^h[1-6]$/.test(tag)) return "\n\n" + "#".repeat(Number(tag[1])) + " " + inner + "\n\n";
    if (tag === "a") { const href = absolute(node.getAttribute("href")); return href && inner ? `[${inner}](<${href.replace(/>/g, "%3E")}>)` : inner; }
    if (tag === "strong" || tag === "b") return `**${inner}**`;
    if (tag === "em" || tag === "i") return `*${inner}*`;
    if (tag === 'code') {
      const value=node.textContent.replace(/\r?\n/g,' '),fence='`'.repeat(Math.max(1,...[...value.matchAll(/`+/g)].map(m=>m[0].length+1)));
      return fence+' '+value+' '+fence;
    }
    if (tag === "li") return "\n- " + inner + "\n";
    if (tag === "br") return "\n";
    if (tag === "blockquote") return "\n\n" + inner.split("\n").map(x => "> " + x).join("\n") + "\n\n";
    if (tag === "table") {
      const rows = [...node.querySelectorAll("tr")].map(tr => [...tr.querySelectorAll("th,td")].map(td => td.textContent.trim().replace(/\|/g, "\\|").replace(/\s+/g, " ")));
      if (!rows.length) return "";
      const width = Math.max(...rows.map(r => r.length));
      const line = row => "| " + Array.from({length: width}, (_, i) => row[i] || "").join(" | ") + " |";
      return "\n\n" + [line(rows[0]), line(Array(width).fill("---")), ...rows.slice(1).map(line)].join("\n") + "\n\n";
    }
    return /^(p|div|section|article|main|ul|ol|figure|figcaption|dl|dt|dd)$/.test(tag) ? "\n\n" + inner + "\n\n" : inner;
  }
  const seen = new Set();
  function describeImage(img) {
    const imageId = crypto.randomUUID();
    img.dataset.anacoObImage = imageId;
    let thumbnail = "";
    try {
      if (img.complete && img.naturalWidth) {
        const canvas = document.createElement("canvas");
        canvas.width = 160; canvas.height = Math.max(1,Math.round(160*img.naturalHeight/img.naturalWidth));
        canvas.height = Math.min(canvas.height,240);
        canvas.getContext("2d").drawImage(img,0,0,canvas.width,canvas.height);
        thumbnail = canvas.toDataURL("image/jpeg",0.65);
      }
    } catch { /* Cross-origin images still have a numbered locator in the article. */ }
    const figcaption=img.closest("figure")?.querySelector("figcaption")?.textContent?.trim()||"";
    const aria_description=(img.getAttribute('aria-describedby')||'').split(/\s+/).map(id=>document.getElementById(id)?.textContent?.trim()||'').filter(Boolean).join(' ');
    return {imageId,thumbnail,url:absolute(img.currentSrc || img.src),alt:img.alt||"",figcaption,aria_description,aria_label:img.getAttribute('aria-label')||'',title:img.title||'',width:img.naturalWidth,height:img.naturalHeight};
  }
  const images = readerHint||platformPage?[]:[...root.querySelectorAll("img")].filter(img=>AnacoObSurfaces.visible(img)&&!img.closest(ignored)&&!/\b(logo|avatar|profile picture)\b/i.test(img.alt||'')).map(describeImage)
    .filter(img => img.url && !seen.has(img.url) && seen.add(img.url) && (img.width >= 100 || img.height >= 100));
  const inventory=readerHint?AnacoObSurfaces.inventory(root):{pages:[],overflow:false};
  if(readerHint)globalThis.AnacoObReaderRoot=root;
  const rendered=readerHint||platformPage?{images:[],canvas:inventory.pages.filter(p=>p.type==='canvas').length,svg:inventory.pages.filter(p=>p.type==='svg').length,backgrounds:inventory.pages.filter(p=>p.type==='background').length,blocked:0,limited:false,failures:[]}:await AnacoObSurfaces.collect(root,images);
  const rasterizedSVG=new Set(rendered.images.filter(i=>i.data).map(i=>i.imageId));
  // Converted SVG <img> replaces its original unsupported SVG resource.
  const convertedNodes=[...root.querySelectorAll('img')].filter(n=>rasterizedSVG.has(n.dataset.anacoObImage));
  for(const node of convertedNodes){const index=images.findIndex(i=>i.url===(node.currentSrc||node.src));if(index>=0)images.splice(index,1);}
  images.push(...rendered.images);
  let kind = input.kind || (platformPage?"video":"article");
  let text = md(clone).replace(/\n{3,}/g, "\n\n").trim();
  codeBlocks.forEach((block,index)=>{text=text.replace(codeToken+':'+index,()=>block);});
  let context = "";
  let selectedImages = images;
  // Titles, comments and recommendations are not the video's transcript.
  // Only extraction may make a platform video ready for note preparation.
  if(platformPage&&!input.kind)text="";
  if (kind === "quote") { text = quote; context = (contextNode?.textContent || "").trim().slice(0,5000); selectedImages = []; }
  if (kind === "image") {
    const target = [...document.images].find(img => (img.currentSrc || img.src) === input.src);
    selectedImages = [target ? describeImage(target) : {url: absolute(input.src), alt: ""}];
    text = selectedImages[0].figcaption||selectedImages[0].aria_description||selectedImages[0].alt||selectedImages[0].aria_label||selectedImages[0].title||"";
    context = (target?.closest("figure,p")?.textContent || "").trim().slice(0,3000);
  }
  const warnings = [];
  const resourceRoot=document.querySelector('#region-main')||root;
  const resourceScope=node=>node?.closest('nav,header,footer,aside,[role="navigation"],[role="banner"],.navbar,.drawer,.block')||resourceRoot.contains&&!resourceRoot.contains(node)?'navigation':'content';
  const linkLauncher=/\/mod\/url\/view\.php$/.test(location.pathname);
  const launchLinks=linkLauncher?[...document.querySelectorAll('#region-main .urlworkaround a[href],#region-main .resourceworkaround a[href]')].map(a=>absolute(a.href)).filter(u=>/^https?:/.test(u)):[];
  const documents=[],videos=[],frames=[];
  const seenDocs=new Set(),seenVideos=new Set();
  function addDocument(url,title,details={}){url=absolute(url);if(!url)return;
    const existing=documents.find(d=>d.url===url);
    if(existing){if(details.scope==='content')existing.scope='content';if(details.embedded)existing.embedded=true;return;}
    seenDocs.add(url);documents.push({url,title:title||tx('bg_documento_pdf'),...details});
  }
  function addVideo(video){
    if(AnacoObMedia.apiURL(video.url))return;
    const drive=AnacoObMedia.driveFile(video.url);
    video.url=drive?.url||AnacoObMedia.platformURL(video.url)||video.url;
    if(drive){
      video.download=drive.download;
      const existing=videos.find(v=>AnacoObMedia.driveFile(v.url)?.id===drive.id);
      if(existing){
        if(drive.url===AnacoObMedia.driveFile(location.href)?.url)existing.title=document.title;
        if(new URL(drive.url).searchParams.has('resourcekey')){existing.url=drive.url;existing.download=drive.download;}
        return;
      }
    }
    if(video.url&&!seenVideos.has(video.url)){seenVideos.add(video.url);videos.push(video);}
  }
  for(const node of document.querySelectorAll('embed,object,iframe')){
    const src=absolute(node.src||node.data||node.getAttribute('src'));
    if(!src)continue;
    if(node.type==='application/pdf'||/\.pdf(?:[?#]|$)/i.test(src))addDocument(src,node.title,{scope:resourceScope(node),embedded:true});
    else if(node.tagName==='IFRAME'){
      frames.push({url:src,title:node.title||new URL(src).hostname});
      const u=new URL(src);const nested=u.searchParams.get('file')||u.searchParams.get('url');
      if(nested&&/\.pdf(?:[?#]|$)/i.test(nested))addDocument(new URL(nested,src).href,node.title,{scope:resourceScope(node),embedded:true});
      if(AnacoObMedia.platformURL(src)||/drive\.google\.com\/file\/d\//i.test(src)){const id=src.match(/drive\.google\.com\/file\/d\/([^/?#]+)/)?.[1];addVideo({url:src,title:node.title||tx('capture_video_incrustado'),tracks:[],download:id?'https://drive.google.com/uc?export=download&id='+encodeURIComponent(id):undefined});}
    }
  }
  for(const link of document.querySelectorAll('a[href]')){
    const href=absolute(link.href),label=(link.textContent||'').trim();
    // Moodle URL activities may expose a link to the lesson instead of an iframe.
    if(linkLauncher&&resourceScope(link)==='content'&&(AnacoObMedia.platformURL(href)||/\.(?:mp4|webm|mp3|m4a|m3u8)(?:[?#]|$)/i.test(href)))addVideo({url:href,title:label||document.title,tracks:[],extractable:true});
    if(/\.pdf(?:[?#]|$)/i.test(href)||(/\.pdf\b/i.test(label)&&/\/files\//.test(href))||/application\/pdf/i.test(link.getAttribute('type')||link.dataset.mimetype||'')){
      let url=href;if(/\.instructure\.com$/.test(location.hostname)&&/\/files\/\d+(?:\/preview)?(?:[?#]|$)/.test(url))url=url.replace(/(\/files\/\d+)(?:\/preview)?(?=[?#]|$)/,'$1/download');
      addDocument(url,label,{scope:resourceScope(link),embedded:false});
    }
  }
  // A paginated/scrolling HTML viewer can fetch its PDF without exposing a link.
  for(const resource of performance.getEntriesByType('resource')){
    try{if(/\.pdf$/i.test(new URL(resource.name).pathname))addDocument(resource.name,tx('capture_pdf_cargado_por_el_visor'),{scope:'content',embedded:true});}catch{}
  }
  if(bookRoot?.matches('.pdfViewer')){
    const file=new URL(location.href).searchParams.get('file');
    if(file)addDocument(file,document.title||tx('capture_documento_del_visor'),{scope:'content',embedded:true});
  }
  for(const video of document.querySelectorAll('video,audio')){
    if(video.closest('[data-anaco-ob-embed]'))continue;
    // Platform extraction uses the public page URL, not internal blob/ad players.
    if(platformPage&&videos.some(v=>v.url===platformPage))continue;
    let src=platformPage||absolute(video.currentSrc||video.src||video.querySelector('source')?.src);
    const tracks=[...video.querySelectorAll('track')].map(track=>({url:absolute(track.src),language:track.srclang,label:track.label})).filter(track=>track.url);
    let cues='';for(const track of video.textTracks||[]){try{if(track.cues?.length)cues+=[...track.cues].map(c=>`${new Date(c.startTime*1000).toISOString().slice(11,23)} --> ${new Date(c.endTime*1000).toISOString().slice(11,23)}\n${c.text}\n`).join('\n');}catch{}}
    // MediaSource players often expose blob: while the actual source was loaded
    // by the player. Resource Timing reveals only resources this frame loaded.
    const loaded=performance.getEntriesByType('resource').map(r=>r.name);
    if(!src||src.startsWith('blob:'))src=loaded.filter(u=>/\.(mp4|webm|m4a|mp3|m3u8)(?:[?#]|$)/i.test(u)).at(-1)||src;
    for(const url of loaded.filter(u=>/\.(vtt|srt)(?:[?#]|$)/i.test(u)).slice(-8))if(!tracks.some(t=>t.url===url))tracks.push({url,language:'',label:tx('capture_subtitulos_del_reproductor')});
    const dash=/\.mpd(?:[?#]|$)/i.test(src);
    const extractable=Boolean(cues||tracks.length||(/^https?:/.test(src)&&!dash));
    addVideo({url:src||location.href,title:video.title||document.title,tracks,subtitles:cues,extractable,
      unavailableReason:extractable?'':dash?tx('capture_este_reproductor_usa_dash_todavia_no_se_'):tx('capture_el_reproductor_esta_presente_pero_todavi'),
      duration:Number.isFinite(video.duration)?video.duration:null,poster:absolute(video.poster)});
  }
  if(platformPage)addVideo({url:platformPage,title:document.title,tracks:[],extractable:true});
  const drive=AnacoObMedia.driveFile(location.href);
  if(drive){addVideo({url:drive.url,download:drive.download,title:document.title,tracks:[]});const index=videos.findIndex(v=>AnacoObMedia.driveFile(v.url)?.id===drive.id);if(index>0)videos.unshift(...videos.splice(index,1));}
  if(document.contentType==='application/pdf')addDocument(location.href,document.title,{scope:'content',embedded:true});
  if(!input.kind&&bookRoot?.matches('.pdfViewer')&&documents.length)kind='pdf';
  // A viewer is not an article; do not summarize platform navigation or login UI.
  const loginPage=Boolean(document.querySelector('input[type="password"]')) && !documents.length && !videos.length;
  const authenticationFrame=location.hostname==='sso.canvaslms.com';
  const providerFrame=/(^|\.)contentcontroller\.com$/.test(location.hostname);
  const canvasHost=/\.instructure\.com$/.test(location.hostname);
  const courseShell=authenticationFrame||(canvasHost&&!courseRoot)||
    ((canvasHost||providerFrame)&&frames.length>0&&!bookRoot&&!inventory.pages.length&&!images.length&&!documents.length&&!videos.length);
  const reader=Boolean(readerHint&&!courseShell&&inventory.pages.length);
  if(reader)warnings.push(tx('capture_libro_detectado_1_paginas_disponibles_us',[inventory.pages.length]));
  if(rendered.limited)warnings.push(tx('capture_la_captura_visual_del_lector_ha_alcanzad'));
  if(rendered.blocked)warnings.push(tx('capture_el_navegador_impide_leer_1_superficies',[rendered.blocked]));
  const contentReady=!loginPage && (kind==='quote'?Boolean(text.trim()):kind==='image'?Boolean(selectedImages[0]?.url):
    (!platformPage&&!courseShell && text.replace(/https?:\/\/\S+/g,'').length>=120 && text.split(/\s+/).length>=18) || (!platformPage&&!courseShell&&selectedImages.length>0));
  if (root === document.body && kind === "article") warnings.push(tx('capture_no_se_detecto_un_articulo_principal_revi'));
  const untouchedMedia=[...document.querySelectorAll('video,iframe')].filter(n=>!embeds.length||!(n.closest('[data-anaco-ob-embed]')||AnacoObEmbeds.embedFrame(n.src)||!AnacoObSurfaces.visible(n)));
  for(const node of root.querySelectorAll('[data-anaco-ob-embed]'))delete node.dataset.anacoObEmbed;
  if (untouchedMedia.length && kind === "article") warnings.push(tx('capture_se_ha_capturado_el_texto_de_la_pagina_el'));
  if (text.length > 120000) warnings.push(tx('capture_la_pagina_supera_el_limite_de_esta_versi'));
  return {reader:reader?{scope:"detected",pages:inventory.pages,overflow:inventory.overflow,visual_limited:false,pageElements:root.querySelectorAll(".page,.pf,[data-page-number]").length,canvas:rendered.canvas,svg:rendered.svg,backgrounds:rendered.backgrounds}:null,documentType:document.contentType,frameRole:authenticationFrame?"authentication":courseShell?"wrapper":"content",surfaces:{canvas:rendered.canvas,svg:rendered.svg,backgrounds:rendered.backgrounds,blocked:rendered.blocked,limited:rendered.limited,failures:rendered.failures},kind, url: location.href, title: document.querySelector('meta[property="og:title"]')?.content || document.title,
    author: document.querySelector('meta[name="author"]')?.content || "", text: text.slice(0,120000), context,
    images: selectedImages, warnings,documents,videos,frames,embeds,contentReady,loginPage,linkLauncher,launchLinks:[...new Set(launchLinks)]};
};
// Notify only about changes to media/frames, not every DOM mutation. The
// background verifies that this is still the selected page before rescanning.
if(!globalThis.AnacoObMediaWatcher){
  let timer;
  const changed=()=>{if(globalThis.AnacoObReaderBusy)return;clearTimeout(timer);timer=setTimeout(()=>browser.runtime.sendMessage({type:'pageMediaChanged'}).catch(()=>{}),700);};
  const observer=new MutationObserver(records=>{
    if(records.some(r=>(r.type==='attributes'&&r.target.matches('iframe,video,audio,source,track,embed,object,canvas,.page,.pf,.slide,.book-content,.flipbook'))||[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('iframe,video,audio,source,track,embed,object,canvas,svg,.page,.pf,.slide')||n.querySelector?.('iframe,video,audio,source,track,embed,object,canvas,svg,.page,.pf,.slide')))))changed();
  });
  observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src','data','class','style','aria-hidden']});
  document.addEventListener('loadedmetadata',changed,true);
  if(typeof PerformanceObserver!=='undefined'){
    const resources=new PerformanceObserver(list=>{
      if(document.querySelector('canvas,.pdfViewer,.book-content,.flipbook,[data-reader]')&&list.getEntries().some(e=>/^https?:/.test(e.name)&&/\.(png|jpe?g|webp|svg)(?:[?#]|$)/i.test(e.name)))changed();
    });resources.observe({type:'resource',buffered:false});
  }
  globalThis.AnacoObMediaWatcher=observer;
}
// executeScript serializes the last expression: never return the function itself.
void 0;
