/* Read-only course inventory. Runs inside a granted tab, with its cookie store. */
globalThis.AnacoObCourseLinks=(()=>{
  let controller;
  function url(value,base){
    if(typeof value!=='string'||!value.trim())return null;
    try{const u=new URL(value,base);if(!/^https?:$/.test(u.protocol)||u.username||u.password)return null;
      if(!/^#(?:\/|!)/.test(u.hash))u.hash='';
      if(/\/(?:logout|signout|delete|remove|reset|enroll|unenroll|grades|settings)(?:[/.?]|$)/i.test(u.pathname)||u.searchParams.has('sesskey'))return null;
      return u.href;
    }catch{return null;}
  }
  function scope(value){
    const u=new URL(value),canvas=u.pathname.match(/^\/courses\/(\d+)(?:\/|$)/);
    return {origin:u.origin,canvasId:canvas?.[1]||null,prefix:canvas?'/courses/'+canvas[1]+'/':u.pathname.endsWith('/')?u.pathname:u.pathname.includes('.')?u.pathname.slice(0,u.pathname.lastIndexOf('/')+1):u.pathname+'/'};
  }
  function crawlable(value,root){
    const u=new URL(value),s=scope(root);if(u.origin!==s.origin)return false;
    if(s.canvasId)return u.pathname.startsWith(s.prefix)&&/^\/(?:modules(?:\/items\/\d+)?|pages\/[^/]+)\/?$/.test(u.pathname.slice(s.prefix.length-1));
    if(/\/course\/view\.php$/.test(new URL(root).pathname)&&/\/course\/view\.php$/.test(u.pathname)&&u.searchParams.get('id')!==new URL(root).searchParams.get('id'))return false;
    if(/\/course\/view\.php$/.test(new URL(root).pathname))return /\/(?:course\/(?:view|section)|mod\/(?:page|book|folder))\.php$/.test(u.pathname);
    return u.pathname.startsWith(s.prefix)&&!/[.](?:pdf|mp4|mp3|webm|png|jpg|zip|docx?|pptx?)$/i.test(u.pathname);
  }
  function canvasNodes(modules,itemsByModule,base){
    const nodes=[];
    for(const module of modules){
      const parent='module-'+module.id,locked=module.state==='locked'||module.published===false;
      nodes.push({id:parent,parentId:null,title:module.name||String(module.id),kind:'module',locked});
      const stack=[{id:parent,indent:-1}];
      for(const item of itemsByModule[module.id]||[]){
        const indent=Math.max(0,Math.min(10,Number(item.indent)||0));
        while(stack.length>1&&stack.at(-1).indent>=indent)stack.pop();
        const id='item-'+item.id,header=item.type==='SubHeader';
        const href=header?null:url(item.html_url||(item.type==='Page'&&item.page_url?base+'/pages/'+item.page_url:item.external_url),base);
        if(!header&&!href)continue;
        nodes.push({id,sourcePosition:item.position,parentId:stack.at(-1).id,title:item.title||href,kind:header?'module':item.type==='Page'?'page':item.type==='File'?'file':'link',url:href,
          locked:locked||Boolean(item.content_details?.locked_for_user||item.locked_for_user),explore:!header&&item.type==='Page'});
        stack.push({id,indent});
      }
    }
    return nodes;
  }
  function documentNodes(doc,base,root){
    const main=doc.querySelector('#wiki_page_show .show-content,.user_content,#region-main,main,[role="main"],article')||doc.body;
    const nodes=[],groups=new Map(),seen=new Set();
    for(const link of main.querySelectorAll('a[href]')){
      if(link.closest('nav,header,footer,aside,[role="navigation"],.module-sequence-footer,.navbar,.drawer,.block'))continue;
      const href=url(link.getAttribute('href'),base);if(!href||href===url(base,base)||href===url(root,root)||seen.has(href))continue;
      const target=new URL(href);if(/\/(?:login|signin|users|profile|calendar|inbox|dashboard|assignments|quizzes|discussions)(?:\/|$)/.test(target.pathname))continue;
      if(/\/(?:course|courses)\//.test(target.pathname)&&scope(root).canvasId&&!target.pathname.startsWith(scope(root).prefix))continue;
      seen.add(href);
      const section=link.closest('[data-module-id],.context_module,.section,.course-section,section');let parentId=null;
      if(section&&section!==main){
        if(!groups.has(section)){
          const heading=section.querySelector('h2,h3,h4,.module_name,.sectionname');
          if(heading){const id='group-'+groups.size;groups.set(section,id);nodes.push({id,parentId:null,title:heading.textContent.trim().slice(0,180),kind:'module'});}
        }
        parentId=groups.get(section)||null;
      }
      const title=(link.textContent||link.getAttribute('title')||target.hostname).replace(/\s+/g,' ').trim().slice(0,180);
      if(!title)continue;
      const kind=/\.pdf(?:[?#]|$)/i.test(href)?'file':/\.(?:mp4|webm|mp3|m4a)(?:[?#]|$)|youtu\.be|youtube\.com|drive\.google\.com/i.test(href)?'video':'page';
      nodes.push({id:'link-'+nodes.length,parentId,title,url:href,kind,locked:Boolean(link.closest('[aria-disabled="true"],.locked')),explore:kind==='page'&&crawlable(href,root)});
      if(nodes.length>=500)break;
    }
    return nodes;
  }
  async function scan(options={}){
    controller?.abort();controller=new AbortController();const signal=controller.signal;
    const base=location.href,root=options.root||base,s=scope(base);
    if(document.querySelector('input[type="password"]'))throw new Error(tx('batch_login'));
    const load=typeof content!=='undefined'&&typeof content.fetch==='function'?content.fetch.bind(content):fetch;
    let requests=0,truncated=false;
    async function pages(endpoint){
      let next=endpoint;const results=[],visited=new Set();
      while(next){
        const u=new URL(next,location.origin);
        if(u.origin!==location.origin||!u.pathname.startsWith('/api/v1/courses/'+s.canvasId+'/'))throw new Error(tx('course_api_scope'));
        if(visited.has(u.href)||requests++>=80){truncated=true;break;}visited.add(u.href);
        const response=await load(u.href,{credentials:'include',signal,headers:{Accept:'application/json'}});
        if(!response.ok||!/json/i.test(response.headers.get('content-type')||''))throw new Error(tx('course_api_unavailable'));
        const data=JSON.parse(await response.text());if(!Array.isArray(data))throw new Error(tx('course_api_unavailable'));
        results.push(...data);if(results.length>=500){truncated=true;break;}
        const match=(response.headers.get('link')||'').match(/<([^>]+)>\s*;\s*rel="?next"?/i);next=match?.[1]||null;
      }
      return results.slice(0,500);
    }
    const warnings=[];
    if(s.canvasId&&options.catalog!==false&&/^\/courses\/\d+(?:\/modules)?\/?$/.test(location.pathname)){
      try{
        const api='/api/v1/courses/'+s.canvasId;
        const modules=await pages(api+'/modules?per_page=100&include[]=items&include[]=content_details'),items={};
        let count=0;
        for(const module of modules){
          if(signal.aborted)throw new Error(tx('course_stopped'));
          if(count>=500){truncated=true;break;}
          items[module.id]=Array.isArray(module.items)&&module.items.length===module.items_count?module.items:await pages(api+'/modules/'+module.id+'/items?per_page=100&include[]=content_details');
          count+=items[module.id].length;
        }
        if(modules.length)return {title:document.title,url:base,nodes:canvasNodes(modules,items,location.origin+'/courses/'+s.canvasId).slice(0,600),truncated,platform:'canvas',warnings};
      }catch(error){if(signal.aborted)throw error;warnings.push(tx('course_api_fallback'));}
    }
    return {title:document.title,url:base,nodes:documentNodes(document,base,root),truncated,platform:'page',warnings};
  }
  return {scan,stop:()=>controller?.abort(),url,scope,crawlable,canvasNodes,documentNodes};
})();
