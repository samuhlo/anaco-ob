/* Render standard Markdown, then insert only the locally captured image blobs. */
globalThis.AnacoObRender = (root,markdown,assets,onImage,vaultName="") => {
  const body=markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/,"");
  const html=marked.parse(body,{gfm:true,breaks:false});
  root.innerHTML=DOMPurify.sanitize(html,{USE_PROFILES:{html:true},FORBID_TAGS:["img","style","iframe","form","input","button","video","audio","source"],FORBID_ATTR:["style"]});
  for(const a of root.querySelectorAll("a")){
    const href=a.getAttribute("href")||"";
    if(!/^https?:\/\//i.test(href)&&!href.startsWith("#"))a.removeAttribute("href");
    a.target="_blank";a.rel="noopener noreferrer";
  }
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
  for(const node of nodes){
    if(node.parentElement?.closest("pre,code"))continue;
    const pattern=/(!?)\[\[([^\]]+)\]\]/g;
    let match,last=0,found=false;
    const fragment=document.createDocumentFragment();
    while((match=pattern.exec(node.textContent))){
      found=true;fragment.append(document.createTextNode(node.textContent.slice(last,match.index)));
      const [path,alias]=match[2].split("|");
      if(match[1]){
        const asset=assets.get(path);
        if(asset){
          const figure=document.createElement("figure"),image=document.createElement("img"),caption=document.createElement("figcaption");
          image.src=asset.url;image.alt=asset.alt||"Imagen de la fuente";image.tabIndex=0;image.setAttribute("role","button");image.setAttribute("aria-label","Ampliar: "+image.alt);
          image.onclick=()=>onImage(asset);image.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();onImage(asset);}};
          caption.textContent=asset.alt||"Imagen conservada localmente · pulsa para ampliar";figure.append(image,caption);fragment.append(figure);
        }else{const p=document.createElement("span");p.className="muted";p.textContent=(/\.(mp4|webm|mov)$/i.test(path)?"Clip de vídeo · se guardará en el vault: ":"Imagen local: ")+path.split("/").pop();fragment.append(p);}
      }else{
        const a=document.createElement("a");a.className="wiki-link";a.textContent=alias||path.split("/").pop();
        a.href="obsidian://open?vault="+encodeURIComponent(vaultName)+"&file="+encodeURIComponent(path);fragment.append(a);
      }
      last=pattern.lastIndex;
    }
    if(found){fragment.append(document.createTextNode(node.textContent.slice(last)));
      const parent=node.parentElement;
      if(parent?.tagName==="P"&&parent.childNodes.length===1&&fragment.childNodes.length===3&&fragment.childNodes[1]?.nodeName==="FIGURE"&&!fragment.childNodes[0].textContent.trim()&&!fragment.childNodes[2].textContent.trim())parent.replaceWith(fragment.childNodes[1]);
      else node.replaceWith(fragment);
    }
  }
  for(const figure of root.querySelectorAll('figure')){const next=figure.nextElementSibling,caption=figure.querySelector('figcaption');if(next?.tagName==='P'&&caption&&next.textContent.trim()===caption.textContent.trim())next.remove();}
};
