/* Recognize posts, code demos and silent clips embedded in a web article.
   Only explicit signals count: course players and providers never match. */
if(!globalThis.AnacoObEmbeds)globalThis.AnacoObEmbeds=(()=>{
  const CLIP_LIMIT=20_000_000;
  const host=url=>{try{const u=new URL(url);return /^https?:$/.test(u.protocol)?u.hostname.toLowerCase():'';}catch{return '';}};
  const within=(name,domain)=>name===domain||name.endsWith('.'+domain);
  function embedFrame(url){
    const name=host(url);
    return ['platform.twitter.com','syndication.twitter.com','codepen.io','cdpn.io'].some(domain=>within(name,domain));
  }
  function tweetURL(value){
    try{
      const u=new URL(value),name=u.hostname.toLowerCase();
      if(within(name,'platform.twitter.com')){const id=u.searchParams.get('id');return /^\d{5,25}$/.test(id||'')?'https://twitter.com/i/status/'+id:null;}
      if(!['x.com','twitter.com','mobile.twitter.com','www.twitter.com','www.x.com'].includes(name))return null;
      const match=u.pathname.match(/^\/([A-Za-z0-9_]{1,15})\/status(?:es)?\/(\d{5,25})/);
      return match?`https://twitter.com/${match[1]}/status/${match[2]}`:null;
    }catch{return null;}
  }
  function penFromURL(value){
    try{
      const u=new URL(value);if(!within(u.hostname.toLowerCase(),'codepen.io')&&!within(u.hostname.toLowerCase(),'cdpn.io'))return null;
      const match=u.pathname.match(/^\/([A-Za-z0-9_-]{1,60})\/(?:embed|pen|full|fullembedgrid|details)\/(?:preview\/)?([A-Za-z0-9]{3,20})(?:\/|$)/);
      if(!match)return null;
      return {user:match[1],slug:match[2],url:`https://codepen.io/${match[1]}/pen/${match[2]}`,embed:`https://codepen.io/${match[1]}/embed/${match[2]}?default-tab=result`};
    }catch{return null;}
  }
  // A clip is decoration-like media: silent, looping and without player controls.
  function isClip(video){
    if(!video?.muted||!video.loop||video.controls)return false;
    if(!/^https?:\/\//i.test(video.src||'')||/\.(m3u8|mpd)(?:[?#]|$)/i.test(video.src))return false;
    return !(Number.isFinite(video.duration)&&video.duration>120);
  }
  function clipWarning(size){
    if(!Number.isFinite(size)||size<=0)return 'Tamaño desconocido: revisa si quieres guardarlo en el vault.';
    return size>CLIP_LIMIT?`Pesa ${Math.round(size/1_000_000)} MB: supera los ${CLIP_LIMIT/1_000_000} MB recomendados.`:'';
  }

  // ===========================================================================
  // [DATA] PAGE SCAN
  // Marks each embed anchor with data-anaco-ob-embed so the Markdown keeps
  // a {{recurso:N}} token at its original position. Callers remove the marks.
  // ===========================================================================
  function collect(root,{visible=()=>true,absolute=v=>v}={}){
    const items=[],seen=new Set();
    const add=(anchor,item,key)=>{
      if(!anchor||seen.has(key)||anchor.closest('[data-anaco-ob-embed]'))return;
      seen.add(key);anchor.dataset.anacoObEmbed=String(items.length);items.push({index:items.length,...item});
    };
    // The X widget keeps the original quote hidden next to its iframe.
    for(const quote of root.querySelectorAll('blockquote.twitter-tweet')){
      const links=[...quote.querySelectorAll('a[href]')].map(a=>tweetURL(a.href)).filter(Boolean);const url=links.at(-1);if(!url)continue;
      const paragraph=quote.querySelector('p');const text=(paragraph?.innerText||paragraph?.textContent||'').trim();
      const byline=(quote.textContent||'').slice((quote.textContent||'').lastIndexOf('—')+1).trim();
      const anchor=visible(quote)?quote:quote.closest('.wp-block-embed__wrapper,figure')||quote.parentElement;
      add(anchor,{type:'tweet',url,text:text.slice(0,2000),author:byline.slice(0,200)},url.split('/').pop());
    }
    for(const frame of root.querySelectorAll('iframe')){
      const src=frame.src||frame.getAttribute('src')||'';
      const url=frame.dataset.tweetId?'https://twitter.com/i/status/'+frame.dataset.tweetId:within(host(src),'platform.twitter.com')&&/\/embed\/Tweet\.html/i.test(src)?tweetURL(src):null;
      if(url){add(frame.closest('.twitter-tweet-rendered')||frame,{type:'tweet',url,text:'',author:''},url.split('/').pop());continue;}
      const pen=penFromURL(src);
      if(pen&&/\/embed\//.test(new URL(src).pathname))add(frame.closest('.cp_embed_wrapper')||frame,{type:'pen',...pen,title:(frame.title||'').trim().slice(0,200)||'Demo de CodePen'},pen.slug);
    }
    // Before CodePen's script runs, the embed is a placeholder paragraph.
    for(const node of root.querySelectorAll('.codepen[data-slug-hash][data-user]')){
      const pen=penFromURL(`https://codepen.io/${node.dataset.user}/embed/${node.dataset.slugHash}`);
      if(pen)add(node,{type:'pen',...pen,title:(node.dataset.penTitle||'').trim().slice(0,200)||'Demo de CodePen'},pen.slug);
    }
    for(const video of root.querySelectorAll('video')){
      const src=absolute(video.currentSrc||video.src||video.querySelector('source')?.src||'');
      if(!isClip({src,muted:video.muted||video.hasAttribute('muted'),loop:video.loop,controls:video.controls,duration:video.duration}))continue;
      const entry=globalThis.performance?.getEntriesByName?.(src)?.[0];const size=entry?.encodedBodySize||entry?.transferSize||null;
      let thumbnail='';
      try{if(video.readyState>=2&&video.videoWidth){const canvas=document.createElement('canvas');canvas.width=160;canvas.height=Math.min(240,Math.max(1,Math.round(160*video.videoHeight/video.videoWidth)));canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);thumbnail=canvas.toDataURL('image/jpeg',.65);}}catch{/* Cross-origin frames cannot be read; the row keeps its number. */}
      const caption=video.closest('figure')?.querySelector('figcaption')?.textContent?.trim()||'';
      const name=decodeURIComponent(new URL(src).pathname.split('/').pop()||'clip.mp4');
      add(video.closest('figure')||video,{type:'clip',url:src,title:(caption||name).slice(0,200),caption:caption.slice(0,500),name:name.slice(0,120),
        duration:Number.isFinite(video.duration)?video.duration:null,size,width:video.videoWidth||null,height:video.videoHeight||null,thumbnail,warning:clipWarning(size)},src);
    }
    return items;
  }
  // ===========================================================================
  // [FLOW] OFFLINE DEMO
  // Copies what a compiled demo loads, following ES module imports and its
  // import map, and points every reference to a flat file next to index.html.
  // ===========================================================================
  const SPECIFIER=/(\bfrom\s*|\bimport\s*\(?\s*)(["'])([^"'\n]+)\2/g;
  const codepen=url=>{try{return /(^|\.)(codepen\.io|cdpn\.io)$/i.test(new URL(url).hostname);}catch{return true;}};
  function localName(url,css){
    let hash=5381;for(const ch of url)hash=((hash*33)^ch.charCodeAt(0))>>>0;
    let base=decodeURIComponent(new URL(url).pathname.split('/').filter(Boolean).pop()||'lib').replace(/[^A-Za-z0-9._@-]/g,'_').slice(0,80)||'lib';
    if(css&&!/\.css$/i.test(base))base+='.css';else if(!css&&!/\.m?js$/i.test(base))base+='.js';
    return hash.toString(16).padStart(8,'0')+'-'+base;
  }
  async function vendor(page,base,load,{maxFiles=40,maxBytes=30_000_000}={}){
    const map={};
    for(const m of page.matchAll(/<script[^>]*type=["']importmap["'][^>]*>([\s\S]*?)<\/script>/gi)){try{Object.assign(map,JSON.parse(m[1]).imports||{});}catch{/* An invalid map loads nothing. */}}
    const prefixes=Object.keys(map).sort((a,b)=>b.length-a.length);
    const resolve=(spec,from)=>{
      try{
        if(/^(https?:)?\/\//.test(spec)||/^\.{0,2}\//.test(spec))return new URL(spec,from).href;
        const key=prefixes.find(k=>k===spec||(k.endsWith('/')&&spec.startsWith(k)));
        return key?new URL(map[key]+spec.slice(key.length),from).href:null;
      }catch{return null;}
    };
    const files=new Map(),missing=new Set();let total=0;
    async function copy(url,css=false){
      if(files.has(url))return files.get(url).name;
      if(missing.has(url)||!/^https:\/\//.test(url)||codepen(url))return null;
      if(files.size>=maxFiles){missing.add(url);return null;}
      // Reserved before loading, so an import cycle resolves to the same file.
      const entry={url,name:localName(url,css),bytes:null};files.set(url,entry);
      try{
        let bytes=await load(url);total+=bytes.length;
        if(total>maxBytes)throw new Error('size');
        if(!css)bytes=new TextEncoder().encode(await rewrite(new TextDecoder().decode(bytes),url));
        entry.bytes=bytes;return entry.name;
      }catch{files.delete(url);missing.add(url);return null;}
    }
    async function rewrite(text,from){
      let out='',last=0;
      for(const m of text.matchAll(SPECIFIER)){
        const url=resolve(m[3],from),name=url&&await copy(url);
        if(!name)continue;
        out+=text.slice(last,m.index)+m[1]+m[2]+'./'+name+m[2];last=m.index+m[0].length;
      }
      return out+text.slice(last);
    }
    let result='',last=0;
    // Tags with src/href, then inline modules; codepen runtime files stay untouched.
    for(const m of page.matchAll(/<script\b[^>]*>[\s\S]*?<\/script>|<link\b[^>]*>/gi)){
      let tag=m[0];
      const css=/^<link/i.test(tag),attr=tag.slice(0,tag.indexOf('>')+1).match(/\b(src|href)=(["'])([^"']+)\2/i);
      if(attr&&(!css||/rel=["']?stylesheet/i.test(tag))){const url=resolve(attr[3],base),name=url&&await copy(url,css);if(name)tag=tag.replace(attr[0],attr[1]+'='+attr[2]+'./'+name+attr[2]);}
      else if(!css&&/type=["']module["']/i.test(tag)){const open=tag.indexOf('>')+1,close=tag.lastIndexOf('</script>');tag=tag.slice(0,open)+await rewrite(tag.slice(open,close),base)+tag.slice(close);}
      result+=page.slice(last,m.index)+tag;last=m.index+m[0].length;
    }
    result+=page.slice(last);
    return {page:result,files:[...files.values()].filter(f=>f.bytes),missing:[...missing]};
  }
  return {embedFrame,tweetURL,penFromURL,isClip,clipWarning,collect,vendor,CLIP_LIMIT};
})();
