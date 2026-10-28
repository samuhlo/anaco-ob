/* One queue owns the existing extraction/drafting pipeline, even with no panel open. */
globalThis.AnacoObBatch=(()=>{
  let queue=null,running=false,stop=false,abortCurrent=false;
  const persist=()=>browser.storage.local.set({batchQueue:JSON.parse(JSON.stringify(queue))});
  const initialized=browser.storage.local.get('batchQueue').then(async data=>{
    queue=data.batchQueue||null;
    if(queue){
      for(const item of queue.items){delete item.tabId;if(item.status==='running'){item.status='pending';item.error='';}}
      if(['running','pausing'].includes(queue.status))queue.status='paused';
      await persist();
    }
  });
  function permissionError(item,urls){item.requiredOrigins=AnacoObBatchPlan.permissionOrigins(urls);const error=new Error(tx('batch_permissions_domains',[item.requiredOrigins.map(u=>new URL(u).hostname).join(', ')]));error.code='permission';return error;}
  const check=()=>{if(abortCurrent)throw new Error(tx('batch_paused'));};
  const delay=()=>new Promise(resolve=>setTimeout(resolve,1000));
  async function assertVault(){
    if(!queue?.vault)throw new Error(tx('batch_legacy_vault_unknown'));
    const owner=queue;
    const {config}=await native({action:'settings'});
    if(queue!==owner)throw new Error(tx('batch_busy'));
    if(config.vault!==owner.vault)throw new Error(tx('batch_vault_changed',[owner.vault]));
  }
  async function start(message){
    await initialized;
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    if(queue?.items.some(i=>i.status==='pending'))throw new Error(tx('batch_pending_queue'));
    const urls=AnacoObBatchPlan.urls(message.urls);
    const origins=[...new Set(urls.map(AnacoObDetection.origin))];
    if(!await browser.permissions.contains({origins}))throw new Error(tx('batch_permissions'));
    const [source]=await browser.tabs.query({active:true,windowId:message.windowId});
    if(!source)throw new Error(tx('batch_no_content'));
    const cookieStoreId=message.cookieStoreId||source.cookieStoreId;
    if(cookieStoreId&&cookieStoreId!=='firefox-default'&&!await browser.permissions.contains({permissions:['cookies']}))throw new Error(tx('batch_container_permission'));
    const {config}=await native({action:'settings'});
    // Recheck after asynchronous permission/context lookups before claiming the queue.
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    queue={id:crypto.randomUUID(),status:'running',windowId:source.windowId,cookieStoreId,vault:config.vault,
      options:{provider:message.provider,intent:message.intent||'',note_structure:message.note_structure||'single',mode:message.mode||'auto',captureMode:message.captureMode||'auto'},
      items:urls.map(url=>({id:crypto.randomUUID(),url,source_context:message.contexts?.[url]||{},status:'pending',title:'',error:''}))};
    launch();return true;
  }
  async function resume(id,windowId){
    await initialized;
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    if(!queue)return false;
    await assertVault();
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    if(id){const item=queue.items.find(i=>i.id===id);if(!item||item.status!=='failed')return false;item.status='pending';item.error='';}
    if(!queue.items.some(i=>i.status==='pending'))return false;
    if(Number.isInteger(windowId))queue.windowId=windowId;
    launch();return true;
  }
  function launch(){
    running=true;stop=false;abortCurrent=false;queue.status='running';delete queue.error;++detectionSequence;
    run().catch(async error=>{queue.status='paused';queue.error=error.message;await persist();}).finally(()=>{running=false;});
  }
  async function pause(cancel=false){
    if(!running)return false;
    stop=true;abortCurrent=cancel;
    if(queue){queue.status='pausing';await persist();}
    if(cancel&&workClaim)await cancelWork();
    return true;
  }
  async function read(item,tabId){
    let last,lastError,stableKey='',stableCount=0;
    const visited=new Set();let launches=0;
    for(let attempt=0;attempt<30;attempt++){
      check();
      const tab=await browser.tabs.get(tabId);
      if(tab.status!=='complete'||!tab.url||tab.url==='about:blank'){await delay();continue;}
      const origin=AnacoObDetection.origin(tab.url);
      if(!origin)throw new Error(tx('batch_no_content'));
      if(!await browser.permissions.contains({origins:[origin]})){throw permissionError(item,[origin]);}
      if(!AnacoObDetection.pdfURL(tab.url)){
        const [login]=await browser.tabs.executeScript(tab.id,{code:`Boolean(document.querySelector('input[type="password"]'))`});
        if(login||/\/(?:login|signin|sign-in)(?:[/?#]|$)/i.test(tab.url))throw new Error(tx('batch_login'));
      }
      // Lazy iframes otherwise may never load in a background tab.
      await browser.tabs.executeScript(tab.id,{code:`for(const frame of document.querySelectorAll('iframe[loading="lazy"]'))frame.loading='eager';void 0;`}).catch(()=>{});
      last=await scanTab(tab,{},queue.options.captureMode);
      check();
      let candidate;
      try{candidate=last&&AnacoObBatchPlan.plan(last,queue.options.mode);}catch(error){lastError=error;}
      // A playable resource already identified by the readable page does not
      // require access to every other iframe (Drive's account/API helpers, etc.).
      const hasVideo=candidate?.kind==='resource'&&candidate.request.kind!=='pdf';
      if(last?.requiredOrigins?.length&&!hasVideo)throw permissionError(item,last.requiredOrigins);
      if(last?.detection?.loginPage&&!hasVideo)throw new Error(tx('batch_login'));
      if(last?.linkLauncher&&last.launchLinks?.length===1&&!last.videos?.some(v=>v.extractable!==false)){
        const url=last.launchLinks[0],origin=AnacoObDetection.origin(url);
        if(origin&&url!==tab.url&&!visited.has(url)&&launches<3){
          if(!await browser.permissions.contains({origins:[origin]})){throw permissionError(item,[origin]);}
          item.source_context={...last.source_context,...item.source_context};
          visited.add(tab.url);visited.add(url);launches++;stableKey='';stableCount=0;
          await browser.tabs.update(tab.id,{url});await delay();continue;
        }
      }
      if(candidate){
        const key=JSON.stringify([tab.url,candidate]);
        stableCount=key===stableKey?stableCount+1:1;stableKey=key;
        // Count stable detections, not page-load polls. Linked PDFs/text need
        // a longer settling window so a delayed lesson player can supersede them.
        const embeddedOrLinkedPDF=candidate.request?.kind==='pdf'&&last.kind!=='pdf';
        const needed=candidate.kind==='note'||embeddedOrLinkedPDF?5:2;
        if(stableCount>=needed){last.source=sourceFor(tab);last.token=crypto.randomUUID();return last;}
      }else{stableKey='';stableCount=0;}
      await delay();
    }
    throw lastError||new Error(last?.detectionError||tx('batch_no_content'));
  }
  async function process(item){
    let tab,loadedURL;
    try{
      check();
      let c;
      if(item.captureId){
        c=await native({action:'load',id:item.captureId});
        if(c.status==='draft'&&c.draft){item.status='ready';return;}
        if(c.status==='saved'){item.status='saved';return;}
        if(c.status==='discarded'){item.captureId=null;c=null;}
        else {const {sources={}}=await browser.storage.local.get('sources');c.source=sources[c.id]||{url:item.url};}
      }
      if(!c){
        const properties={url:item.url,active:false,windowId:queue.windowId};
        if(queue.cookieStoreId&&queue.cookieStoreId!=='firefox-default')properties.cookieStoreId=queue.cookieStoreId;
        tab=await browser.tabs.create(properties);item.tabId=tab.id;
        c=await read(item,tab.id);c.source_context={...c.source_context,...item.source_context};loadedURL=c.source.url;item.title=c.title;
        await persist();check();
        const plan=AnacoObBatchPlan.plan(c,queue.options.mode);
        item.selectedKind=plan.request?.kind||plan.kind;
        const resourceURLs=plan.kind==='resource'?[plan.request.url,plan.request.fallback?.url]:plan.kind==='reader'?c.reader.pages.flatMap(p=>p.urls||[]):[];
        const origins=AnacoObBatchPlan.permissionOrigins(resourceURLs);
        if(origins.length&&!await browser.permissions.contains({origins})){throw permissionError(item,origins);}
        if(plan.kind==='reader')c=await extractReader({token:c.token},c);
        else if(plan.kind==='resource')c=await importResource({...plan.request,token:c.token},c);
      }
      if(c.id){item.captureId=c.id;await persist();}
      check();
      const result=await prepare({...queue.options,conversation:queue.options.captureMode==='podcast'?'on':'auto',images:c.id?c.images.map((_,i)=>i):[],embeds:[],deferReview:true},c);
      item.captureId=result.capture.id;item.title=result.capture.title;item.status='ready';item.error='';item.requiredOrigins=[];delete item.diagnostic;
    }catch(error){
      // Preserve a native capture created before a failed draft so retry is cheap.
      const {currentCapture:c}=await browser.storage.local.get('currentCapture');
      if(c?.id&&tab&&c.source?.tabId===tab.id)item.captureId=c.id;
      item.status=abortCurrent?'pending':'failed';item.error=error.message;
      if(error.diagnostic)item.diagnostic=error.diagnostic;else delete item.diagnostic;
      if(error.code!=='permission')item.requiredOrigins=[];
    }finally{
      if(tab){
        try{const current=await browser.tabs.get(tab.id);if(!current.active&&current.url===(loadedURL||item.url)){await browser.tabs.remove(tab.id);delete item.tabId;}}catch{}
      }
    }
  }
  async function run(){
    // The panel keeps the capture it was attached to before batch work began.
    const previous=await browser.storage.local.get(['currentCapture','draftResult','pageContext']);
    try{
      await persist();
      for(const item of queue.items){
        if(stop)break;
        if(!queue.items.includes(item)||item.status!=='pending')continue;
        await assertVault();
        item.status='running';await persist();await process(item);await persist();
      }
      queue.status=stop&&queue.items.some(i=>i.status==='pending')?'paused':'complete';
    }finally{
      if(previous.currentCapture?.id){
        try{const c=await native({action:'load',id:previous.currentCapture.id});if(['saved','discarded'].includes(c.status)){previous.currentCapture=null;previous.draftResult=null;}}catch{}
      }
      await browser.storage.local.set({...previous,operationError:'',operationDiagnostic:null});
      await persist();
    }
  }
  async function reviewed(id,status){
    await initialized;
    const item=queue?.items.find(i=>i.captureId===id);
    if(item){item.status=status;if(status==='saved')item.reviewedAt=Date.now();await persist();}
  }
  async function restartVideos(windowId){
    await initialized;
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    if(!queue)return false;
    await assertVault();
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    for(const item of queue.items){
      if(['saved','discarded'].includes(item.status))continue;
      if(item.captureId)item.previousCaptureIds=[...new Set([...(item.previousCaptureIds||[]),item.captureId])];
      delete item.captureId;delete item.selectedKind;
      item.status='pending';item.title='';item.error='';
    }
    queue.options.mode='video';
    return resume(null,windowId);
  }
  async function retryFailed(windowId){
    await initialized;
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    if(!queue)return false;
    await assertVault();
    if(running||workClaim||pendingDiscard)throw new Error(tx('batch_busy'));
    for(const item of queue.items)if(item.status==='failed'){item.status='pending';item.error='';}
    return resume(null,windowId);
  }
  async function remove(id){
    await initialized;if(!queue)return false;
    const item=queue.items.find(i=>i.id===id);if(!item)return false;
    if(item.status==='running')throw new Error(tx('batch_remove_running'));
    queue.items=queue.items.filter(i=>i!==item);
    if(!running&&!queue.items.length)queue=null;
    else if(!running&&!queue.items.some(i=>i.status==='pending'))queue.status='complete';
    await persist();return true;
  }
  async function clear(failedOnly=false){
    await initialized;if(!queue)return false;
    if(running&&!failedOnly)throw new Error(tx('batch_remove_running'));
    queue.items=failedOnly?queue.items.filter(i=>i.status!=='failed'):[];
    if(!running&&!queue.items.length)queue=null;
    else if(!running&&!queue.items.some(i=>i.status==='pending'))queue.status='complete';
    await persist();return true;
  }
  async function reviewContext(id){
    await initialized;
    const index=queue?.items.findIndex(i=>i.captureId===id)??-1;
    if(index<0)return null;
    const remaining=[...queue.items.slice(index+1),...queue.items.slice(0,index)].filter(i=>i.status==='ready'&&i.captureId&&i.captureId!==id);
    const reviewable=queue.items.filter(i=>i.captureId&&(i.captureId===id||['ready','saved'].includes(i.status)));
    return {queueId:queue.id,index:reviewable.findIndex(i=>i.captureId===id)+1,total:reviewable.length,reviewed:queue.items.filter(i=>i.status==='saved').length,next:remaining.map(i=>i.captureId)};
  }
  return {start,resume,pause,reviewed,reviewContext,restartVideos,retryFailed,remove,clear,busy:()=>running,vault:()=>running?queue?.vault:null};
})();
