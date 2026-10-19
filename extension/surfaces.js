/* Read rendered course pages without navigating the course or changing progress. */
if (!globalThis.AnacoObSurfaces) {
  const visible = node => {
    if (!node?.isConnected || node.closest('[hidden],[aria-hidden="true"],nav,header,footer,aside,[role="navigation"]')) return false;
    const box=node.getBoundingClientRect(), style=getComputedStyle(node);
    if(style.visibility==='hidden'||style.visibility==='collapse'||style.display==='none'||style.opacity==='0')return false;
    for(let p=node.parentElement;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;}
    return true;
  };
  function elements(root) {
    const result=[],queue=[root];
    while(queue.length&&result.length<30000){
      const parent=queue.shift();
      for(const node of parent.querySelectorAll('*')){
        result.push(node);if(node.shadowRoot)queue.push(node.shadowRoot);
        if(result.length>=30000)break;
      }
    }
    return result;
  }
  function raster(node, drawable, label) {
    const box=node.getBoundingClientRect();
    const width=drawable.naturalWidth||drawable.width?.baseVal?.value||drawable.width||box.width;
    const height=drawable.naturalHeight||drawable.height?.baseVal?.value||drawable.height||box.height;
    const scale=Math.min(1,1800/Math.max(width,height));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale));
    const context=canvas.getContext('2d');context.fillStyle='white';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(drawable,0,0,canvas.width,canvas.height);
    const data=canvas.toDataURL('image/jpeg',.88).split(',')[1];
    if(data.length>3900000)throw new Error('oversize');
    const thumb=document.createElement('canvas');thumb.width=160;thumb.height=Math.min(240,Math.max(1,Math.round(160*canvas.height/canvas.width)));
    thumb.getContext('2d').drawImage(canvas,0,0,thumb.width,thumb.height);
    const imageId=crypto.randomUUID();node.dataset.anacoObImage=imageId;
    return {imageId,url:location.href+'#zen-page-'+imageId,data,thumbnail:thumb.toDataURL('image/jpeg',.65),width:canvas.width,height:canvas.height,alt:label,visual_page:true};
  }
  async function svgImage(node){
    const clone=node.cloneNode(true),box=node.getBoundingClientRect();
    clone.removeAttribute('xmlns');clone.setAttributeNS('http://www.w3.org/2000/xmlns/','xmlns','http://www.w3.org/2000/svg');clone.setAttribute('width',Math.round(box.width));clone.setAttribute('height',Math.round(box.height));
    clone.querySelectorAll('script,foreignObject').forEach(n=>n.remove());
    for(const child of [clone,...clone.querySelectorAll('*')]){
      for(const attr of [...child.attributes]){
        if(/^on/i.test(attr.name)||(/href$/.test(attr.name)&&!attr.value.startsWith('#')))child.removeAttribute(attr.name);
      }
    }
    const image=document.createElement('img');image.crossOrigin='anonymous';
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('timeout')),1500);
      image.onload=()=>{clearTimeout(timer);resolve();};image.onerror=()=>{clearTimeout(timer);reject(new Error('svg'));};
      image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(clone));
    });
    return raster(node,image,tx('surfaces_pagina_del_visor'));
  }
  async function collect(root, existing) {
    const images=[],nodes=elements(root),failures=[];let blocked=0,canvasCount=0,svgCount=0,backgroundCount=0,inlineSize=0,limited=false;
    const room=()=>{if(images.length>=8||inlineSize>=3000000){limited=true;return false;}return true;};
    const add=image=>{if(!room())return;if(image.data&&inlineSize+image.data.length>3000000){limited=true;return;}inlineSize+=image.data?.length||0;images.push(image);};
    const seen=new Set(existing.map(i=>i.url));
    for(const node of nodes){
      if(!visible(node))continue;
      const box=node.getBoundingClientRect();if(box.width<160||box.height<90)continue;
      const tag=node.tagName.toLowerCase();
      if(tag==='canvas'){
        canvasCount++;
        try{if(room()&&node.width&&node.height)add(raster(node,node,tx('surfaces_pagina_del_visor')));}catch{blocked++;}
      }else if(tag==='svg'&&!node.parentElement?.closest('svg')){
        svgCount++;try{if(room())add(await svgImage(node));}catch(error){blocked++;failures.push({type:'svg',code:error.name,detail:['svg','timeout','oversize'].includes(error.message)?error.message:''});}
      }else if(tag==='img'&&/\.svg(?:[?#]|$)/i.test(node.currentSrc||node.src)){
        try{if(room()&&node.complete&&node.naturalWidth)add(raster(node,node,node.alt||tx('surfaces_pagina_del_visor')));}catch{blocked++;}
      }else{
        const background=getComputedStyle(node).backgroundImage;
        for(const match of background.matchAll(/url\(["']?([^"')]+)["']?\)/g)){
          let url;try{url=new URL(match[1],location.href).href;}catch{continue;}
          if(!/^https?:/.test(url)||seen.has(url)||/\.svg(?:[?#]|$)/i.test(url))continue;
          seen.add(url);backgroundCount++;if(!room())continue;
          const imageId=crypto.randomUUID();node.dataset.anacoObImage=imageId;
          add({imageId,url,alt:node.getAttribute('aria-label')||node.title||'',width:Math.round(box.width),height:Math.round(box.height)});
        }
      }
    }
    return {images,failures,limited,blocked,canvas:canvasCount,svg:svgCount,backgrounds:backgroundCount};
  }
  let savedScroll=null;
  function inventory(root){
    const all=elements(root), units=[], candidates=[];
    const isLarge=node=>{const r=node.getBoundingClientRect();return r.width>=160&&r.height>=90;};
    for(const node of all){
      if(!visible(node))continue;
      if(node.matches('.page,.pf,[data-page-number]')&&(isLarge(node)||(node.innerText||'').trim().length>=30))units.push(node);
    }
    const unitSet=new Set(units);
    const inUnit=node=>{for(let p=node.parentElement;p&&p!==root;p=p.parentElement)if(unitSet.has(p))return true;return false;};
    for(const node of units)if(!inUnit(node))candidates.push({node,type:'page'});
    for(const node of all){
      if(!visible(node)||!isLarge(node)||unitSet.has(node)||inUnit(node)||/\b(logo|avatar|profile picture)\b/i.test(node.getAttribute('alt')||''))continue;
      const tag=node.tagName.toLowerCase();
      if(tag==='img'||tag==='canvas'||(tag==='svg'&&!node.parentElement?.closest('svg')))candidates.push({node,type:tag});
      else if(/url\(/.test(getComputedStyle(node).backgroundImage))candidates.push({node,type:'background'});
    }
    candidates.sort((a,b)=>a.node===b.node?0:a.node.compareDocumentPosition(b.node)&Node.DOCUMENT_POSITION_FOLLOWING?-1:1);
    const pages=candidates.slice(0,501).map(({node,type},i)=>{
      const id=node.dataset.anacoObPage||(node.dataset.anacoObPage=crypto.randomUUID());
      const image=type==='img'?node:node.querySelector('img');
      const urls=[image?.currentSrc,image?.src,image?.dataset.src,...[...getComputedStyle(node).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(m=>m[1])].filter(u=>/^https?:/.test(u||''));
      return {id,type,index:i+1,label:tx('surfaces_pagina')+(i+1),urls:[...new Set(urls)]};
    });
    return {pages,overflow:candidates.length>500};
  }
  function start(){
    if(!savedScroll)savedScroll={x:window.scrollX,y:window.scrollY,elements:elements(document).filter(e=>e.scrollHeight>e.clientHeight+30).map(e=>({e,x:e.scrollLeft,y:e.scrollTop}))};
    globalThis.AnacoObReaderBusy=true;
  }
  function end(){
    if(savedScroll){for(const {e,x,y} of savedScroll.elements){e.scrollLeft=x;e.scrollTop=y;}window.scrollTo(savedScroll.x,savedScroll.y);savedScroll=null;}
    globalThis.AnacoObReaderBusy=false;
  }
  async function read(id){
    const node=elements(document).find(e=>e.dataset.anacoObPage===id);
    if(!node)throw new Error(tx('surfaces_la_pagina_cambio_mientras_se_extraia_el_'));
    start();node.scrollIntoView({behavior:'instant',block:'center',inline:'nearest'});
    await new Promise(r=>setTimeout(r,180));
    const items=[node,...node.querySelectorAll('canvas,img,svg')].filter(e=>visible(e)&&/^(canvas|img|svg)$/i.test(e.tagName));
    items.sort((a,b)=>{const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return y.width*y.height-x.width*x.height;});
    const primary=items[0];
    const text=(node.innerText||'').trim();
    if(primary?.tagName.toLowerCase()==='img'){
      for(let n=0;n<60&&(!primary.complete||!primary.naturalWidth);n++)await new Promise(r=>setTimeout(r,100));
      if(!primary.complete||!primary.naturalWidth)throw new Error(tx('surfaces_la_imagen_de_esta_pagina_todavia_no_esta'));
      const url=primary.currentSrc||primary.src;
      if(/^https?:/.test(url)&&!/\.(svg|avif)(?:[?#]|$)/i.test(url))return {text,image:{url,alt:tx('surfaces_pagina_del_libro'),visual_page:true}};
      return {text,image:raster(primary,primary,tx('surfaces_pagina_del_libro'))};
    }
    if(primary?.tagName.toLowerCase()==='canvas'){
      // Do not accept an unpainted canvas as a successfully read book page.
      let ready=false;
      for(let attempt=0;attempt<50;attempt++){
        const probe=document.createElement('canvas');probe.width=64;probe.height=64;
        const ctx=probe.getContext('2d');ctx.drawImage(primary,0,0,64,64);
        const pixels=ctx.getImageData(0,0,64,64).data;
        let changed=false;
        for(let at=4;at<pixels.length;at+=4){if(Math.abs(pixels[at]-pixels[0])+Math.abs(pixels[at+1]-pixels[1])+Math.abs(pixels[at+2]-pixels[2])>4){changed=true;break;}}
        const knownLoaded=node.dataset.loaded==='true'||primary.closest('[data-loaded="true"]');
        if(changed||knownLoaded||text.length>=120){ready=true;break;}
        await new Promise(r=>setTimeout(r,120));
      }
      if(!ready)throw new Error(tx('surfaces_el_visor_todavia_no_ha_dibujado_esta_pag'));
      return {text,image:raster(primary,primary,tx('surfaces_pagina_del_libro'))};
    }
    if(primary?.tagName.toLowerCase()==='svg')return {text,image:await svgImage(primary)};
    const url=[...getComputedStyle(node).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)][0]?.[1];
    if(url)return {text,image:{url:new URL(url,location.href).href,alt:tx('surfaces_pagina_del_libro'),visual_page:true}};
    if(text)return {text,image:null};
    throw new Error(tx('surfaces_esta_pagina_no_expone_texto_ni_una_image'));
  }
  globalThis.AnacoObSurfaces={visible,elements,collect,inventory,start,end,read};
}
void 0;
