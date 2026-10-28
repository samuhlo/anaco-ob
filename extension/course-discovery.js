/* Background-owned, bounded exploration; it never prepares or saves a note. */
globalThis.AnacoObCourses=(()=>{
  let state=null,running=false,stopped=false,tabId=null;
  const save=()=>browser.storage.local.set({courseDiscovery:JSON.parse(JSON.stringify(state))});
  const ready=browser.storage.local.get('courseDiscovery').then(async data=>{
    state=data.courseDiscovery||null;
    if(state?.status==='running'){
      if(state.activeTask)state.todo.unshift(state.activeTask);
      state.activeTask=null;state.status='paused';await save();
    }
  });
  async function start(message){
    await ready;if(running)throw new Error(tx('course_busy'));
    const url=AnacoObCourseLinks.url(message.url);if(!url)throw new Error(tx('batch_invalid_url',[message.url||'']));
    const origin=AnacoObDetection.origin(url);
    if(!await browser.permissions.contains({origins:[origin]}))throw new Error(tx('batch_permissions'));
    const [active]=await browser.tabs.query({active:true,windowId:message.windowId});
    let source=active;
    if(Number.isInteger(message.sourceTabId)){try{const t=await browser.tabs.get(message.sourceTabId);if(new URL(t.url).origin===new URL(url).origin)source=t;}catch{}}
    if(!source)throw new Error(tx('batch_no_content'));
    if(source.cookieStoreId&&source.cookieStoreId!=='firefox-default'&&!await browser.permissions.contains({permissions:['cookies']}))throw new Error(tx('batch_container_permission'));
    if(running)throw new Error(tx('course_busy'));
    state={id:crypto.randomUUID(),root:url,windowId:source.windowId,cookieStoreId:source.cookieStoreId,maxDepth:Math.max(1,Math.min(5,Number(message.depth)||3)),
      status:'running',nodes:[{id:'root',title:url,kind:'module',parentId:null}],todo:[{url,parentId:'root',depth:0}],visited:[],blocked:[],warnings:[],selected:[],count:0,truncated:false};
    launch();return true;
  }
  async function resume(windowId){
    await ready;if(running)throw new Error(tx('course_busy'));if(!state)return false;
    if(Number.isInteger(windowId))state.windowId=windowId;
    state.todo.push(...state.blocked.map(({url,parentId,depth})=>({url,parentId,depth})));state.blocked=[];
    if(!state.todo.length)return false;launch();return true;
  }
  function launch(){running=true;stopped=false;state.status='running';delete state.error;run().catch(async error=>{state.error=error.message;state.status='paused';await save();}).finally(()=>{running=false;});}
  async function stop(){stopped=true;if(tabId)await browser.tabs.executeScript(tabId,{code:'globalThis.AnacoObCourseLinks?.stop();void 0;'}).catch(()=>{});return true;}
  const delay=()=>new Promise(r=>setTimeout(r,250));
  async function read(task){
    const origin=AnacoObDetection.origin(task.url);
    if(!await browser.permissions.contains({origins:[origin]})){const e=new Error(tx('batch_permissions_domains',[new URL(task.url).hostname]));e.origin=origin;throw e;}
    const tab=await browser.tabs.create({url:task.url,active:false,windowId:state.windowId,...(state.cookieStoreId&&state.cookieStoreId!=='firefox-default'?{cookieStoreId:state.cookieStoreId}:{})});
    tabId=tab.id;let finalURL=task.url;
    try{
      let current;
      for(let i=0;i<80;i++){if(stopped)throw new Error(tx('course_stopped'));current=await browser.tabs.get(tab.id);if(current.status==='complete'&&AnacoObDetection.origin(current.url))break;await delay();}
      if(current.status!=='complete'||!AnacoObDetection.origin(current.url))throw new Error(tx('course_load_timeout'));
      finalURL=current.url;
      const actual=AnacoObDetection.origin(finalURL);
      if(!actual||!await browser.permissions.contains({origins:[actual]})){const e=new Error(tx('batch_permissions_domains',[new URL(finalURL).hostname]));e.origin=actual;throw e;}
      await injectI18n(tab.id,{frameId:0});
      await browser.tabs.executeScript(tab.id,{file:'course-links.js',frameId:0});
      let timeout;
      try{
        const [result]=await Promise.race([browser.tabs.executeScript(tab.id,{code:`AnacoObCourseLinks.scan(${JSON.stringify({root:state.root,catalog:task.depth===0})})`,frameId:0}),new Promise((_,reject)=>{timeout=setTimeout(()=>reject(new Error(tx('course_load_timeout'))),60000);})]);
        return result;
      }finally{clearTimeout(timeout);}
    }finally{
      await browser.tabs.executeScript(tab.id,{code:'globalThis.AnacoObCourseLinks?.stop();void 0;'}).catch(()=>{});
      try{const t=await browser.tabs.get(tab.id);if(!t.active&&(t.url===finalURL||t.url==='about:blank'))await browser.tabs.remove(tab.id);}catch{}
      tabId=null;
    }
  }
  function merge(task,result){
    if(task.depth===0)state.nodes[0].title=result.title||state.root;
    const local=new Map(),byURL=new Map(state.nodes.filter(n=>n.url).map(n=>[n.url,n]));
    for(const entry of result.nodes||[]){
      if((state.nodes.length>=600||state.nodes.filter(n=>n.url).length>=500)){state.truncated=true;break;}
      const url=entry.url?AnacoObCourseLinks.url(entry.url,task.url):null;
      if(entry.url&&!url)continue;
      const existing=url&&byURL.get(url);
      if(existing){local.set(entry.id,existing.id);continue;}
      const id=crypto.randomUUID(),parentId=local.get(entry.parentId)||task.parentId;
      const node={id,parentId,sourcePosition:entry.sourcePosition,title:String(entry.title||url||'').slice(0,180),url,kind:entry.kind||'link',locked:Boolean(entry.locked)};
      state.nodes.push(node);local.set(entry.id,id);if(url)byURL.set(url,node);
      if(url&&entry.explore&&!node.locked){
        if(task.depth<state.maxDepth&&AnacoObCourseLinks.crawlable(url,state.root)&&!state.visited.includes(url)&&!state.todo.some(t=>t.url===url))state.todo.push({url,parentId:id,depth:task.depth+1});
        else if(task.depth>=state.maxDepth)state.truncated=true;
      }
    }
    for(const warning of result.warnings||[])if(!state.warnings.includes(warning))state.warnings.push(warning);
    state.truncated=state.truncated||Boolean(result.truncated);
  }
  async function run(){
    await save();
    try{
      while(state.todo.length&&!stopped){
        if(state.count>=40||(state.nodes.length>=600||state.nodes.filter(n=>n.url).length>=500)){state.truncated=true;break;}
        const task=state.todo.shift();if(state.visited.includes(task.url))continue;
        state.activeTask=task;await save();
        try{const result=await read(task);if(stopped){state.todo.unshift(task);break;}merge(task,result);state.visited.push(task.url);state.count++;}
        catch(error){if(stopped){state.todo.unshift(task);break;}state.blocked.push({...task,error:error.message,origin:error.origin||null});}
        finally{state.activeTask=null;await save();}
      }
      state.status=stopped&&state.todo.length?'paused':'complete';
    }finally{await save();}
  }
  async function select(ids){await ready;if(!state)return;const allowed=new Set(state.nodes.filter(n=>n.url&&!n.locked).map(n=>n.id));state.selected=[...new Set(ids)].filter(id=>allowed.has(id));await save();}
  return {start,resume,stop,select};
})();
