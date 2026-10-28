globalThis.AnacoObBatchUI={busy:false};
(()=>{
  // view: which mode the panel shows. source: how the next list is filled.
  let queue=null,signature='',pageQueueId=null,newList=false,previousQueueId=null,importedCookieStoreId=null,view='page',source='paste',structureTouched=false;
  const action=fn=>async()=>{
    $('batchError').hidden=true;
    try{await fn();}catch(error){$('batchError').textContent=error.message;$('batchError').hidden=false;}
  };
  const button=(label,fn,className='sm')=>{const b=document.createElement('button');b.type='button';b.className=className;b.textContent=label;b.onclick=action(fn);return b;};
  const iconButton=(icon,label,fn,className='icon')=>{const b=button(icon,fn,className);b.setAttribute('aria-label',label);b.title=label;return b;};
  const closeMore=()=>{$('batchMore').open=false;};
  // A row without a title names its page, not the raw address.
  function place(url){try{const u=new URL(url),path=u.pathname==='/'?'':u.pathname;return (u.hostname+path).slice(0,80);}catch{return url;}}
  function host(url){try{return new URL(url).hostname;}catch{return '';}}
  async function openSource(item){
    if(item.tabId){try{await browser.tabs.update(item.tabId,{active:true});return;}catch{}}
    await browser.tabs.create({url:item.url,...(queue.cookieStoreId&&queue.cookieStoreId!=='firefox-default'?{cookieStoreId:queue.cookieStoreId}:{})});
  }
  function setView(next){
    view=next;render().catch(showError);
  }
  function setSource(next){
    source=next;
    $('sourcePaste').setAttribute('aria-pressed',String(source==='paste'));$('sourceCourse').setAttribute('aria-pressed',String(source==='course'));
    $('batchPaste').hidden=source!=='paste';$('courseExplorer').hidden=source!=='course';
  }
  $('modePage').onclick=()=>{pageQueueId=queue?.id;newList=false;setView('page');};
  $('modeBatch').onclick=()=>{pageQueueId=null;setView('batch');};
  $('sourcePaste').onclick=()=>setSource('paste');
  $('sourceCourse').onclick=()=>setSource('course');
  $('batchStructure').onchange=()=>{structureTouched=true;};
  $('batchURLs').oninput=()=>{
    let count=0;try{count=AnacoObBatchPlan.urls($('batchURLs').value).length;}catch{}
    $('batchStart').textContent=count>1?tx('batch_start_count',[count]):tx('batch_start');
  };
  $('batchStart').onclick=action(async()=>{
    const urls=AnacoObBatchPlan.urls($('batchURLs').value);
    const origins=AnacoObBatchPlan.permissionOrigins(urls);
    // Request immediately in the click, including optional container permission.
    if(!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'batchStart',urls:urls.join('\n'),windowId:panelWindowId,mode:$('batchMode').value,cookieStoreId:importedCookieStoreId,
      provider:$('provider').value,intent:$('batchIntent').value,note_structure:$('batchStructure').value,captureMode:$('captureMode').value});
    $('batchURLs').value='';$('batchURLs').oninput();newList=false;render().catch(showError);
  });
  AnacoObBatchUI.importLinks=(urls,cookieStoreId)=>{
    newList=true;importedCookieStoreId=cookieStoreId;$('batchURLs').value=urls.join('\n');$('batchURLs').oninput();
    setSource('paste');view='batch';render().then(()=>$('batchURLs').focus()).catch(showError);
  };
  $('batchCancelNew').onclick=()=>{newList=false;render().catch(showError);};
  $('batchNewList').onclick=()=>{newList=true;importedCookieStoreId=null;render().then(()=>$('batchURLs').focus()).catch(showError);};
  $('batchRestartVideos').onclick=action(async()=>{closeMore();await browser.runtime.sendMessage({type:'batchRestartVideos',windowId:panelWindowId});});
  $('batchRetryFailed').onclick=action(async()=>{
    const failed=queue?.items.filter(i=>i.status==='failed')||[];
    const origins=AnacoObBatchPlan.permissionOrigins(failed.flatMap(i=>[i.url,...(i.requiredOrigins||[])]));
    if(origins.length&&!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'batchRetryFailed',windowId:panelWindowId});
  });
  $('batchClearFailed').onclick=action(async()=>{closeMore();await browser.runtime.sendMessage({type:'batchClear',failedOnly:true});});
  $('batchClear').onclick=action(async()=>{
    closeMore();await browser.runtime.sendMessage({type:'batchClear'});await render();
    $('batchURLs').focus();
  });
  $('batchPause').onclick=action(()=>browser.runtime.sendMessage({type:'batchPause'}));
  $('batchResume').onclick=action(()=>browser.runtime.sendMessage({type:'batchResume',windowId:panelWindowId}));
  $('batchReviewNext').onclick=action(async()=>{
    const next=queue?.items.find(i=>i.status==='ready'&&i.captureId);
    if(next)await browser.runtime.sendMessage({type:'openReview',id:next.captureId});
  });
  document.addEventListener('click',event=>{if($('batchMore').open&&!$('batchMore').contains(event.target))closeMore();});
  const statusLabel=value=>({saved:tx('batch_status_saved'),discarded:tx('batch_status_discarded'),pending:tx('batch_status_pending'),running:tx('batch_status_running'),ready:tx('batch_status_ready'),failed:tx('batch_status_failed'),paused:tx('batch_status_paused'),pausing:tx('batch_status_pausing'),complete:tx('batch_status_complete')})[value]||value;
  const tone=value=>({running:'run',pausing:'run',paused:'run',complete:''})[value]||'';
  async function render(){
    const data=await browser.storage.local.get(['batchQueue','activeWork']);queue=data.batchQueue;
    const items=queue?.items||[],busy=['running','pausing'].includes(queue?.status),working=Boolean(data.activeWork);AnacoObBatchUI.busy=busy;
    const count=state=>items.filter(i=>i.status===state).length;
    const pending=count('pending'),failed=count('failed'),ready=count('ready'),saved=count('saved');
    if(queue?.id!==previousQueueId){newList=false;previousQueueId=queue?.id;}
    // A running queue, or one the user has not left yet, keeps the panel on it.
    if(!manualImport&&items.length&&(busy||pageQueueId!==queue.id))view='batch';
    if(manualImport)view='page';
    const batch=view==='batch',composing=!items.length||newList;
    // The panel's organization is only a default until the list chooses its own.
    if(!structureTouched)$('batchStructure').value=$('noteStructure').value||'single';
    document.body.classList.toggle('is-batch',batch);
    $('modeSwitch').hidden=manualImport;
    $('modePage').setAttribute('aria-pressed',String(!batch));$('modeBatch').setAttribute('aria-pressed',String(batch));
    $('modePage').disabled=busy;$('modePage').title=busy?tx('mode_busy_page'):'';
    $('batchSection').hidden=!batch;
    $('batchForm').hidden=!composing;$('batchQueue').hidden=composing;
    $('batchCancelNew').hidden=!(newList&&items.length);$('batchReplaces').hidden=!items.length;
    $('batchStart').disabled=busy||working||pending>0;
    $('useActiveTab').disabled=busy||working;
    // One primary action per state: continue a stopped queue, else review what is ready.
    $('batchResume').hidden=busy||!pending;$('batchResume').disabled=working;
    $('batchReviewNext').hidden=busy||Boolean(pending)||!ready;
    $('batchReviewNext').textContent=tx('batch_review_next',[ready]);
    $('batchPause').hidden=!busy;$('batchPause').disabled=queue?.status==='pausing';
    $('batchRetryFailed').hidden=busy||!failed;$('batchRetryFailed').disabled=working;
    $('batchRetryFailed').className=!pending&&!ready?'primary':'sm';
    $('batchNewList').hidden=busy||Boolean(pending);$('batchNewList').disabled=working;
    $('batchNewList').className=!pending&&!ready&&!failed?'primary':'sm';
    $('batchRestartVideos').hidden=busy||!items.some(i=>!['saved','discarded'].includes(i.status));$('batchRestartVideos').disabled=working;
    $('batchClearFailed').hidden=!failed;
    $('batchClear').disabled=busy;
    $('batchState').textContent=queue?statusLabel(queue.status):'';
    if(tone(queue?.status))$('batchState').dataset.tone=tone(queue.status);else delete $('batchState').dataset.tone;
    $('batchProgress').max=Math.max(1,items.length);$('batchProgress').value=items.filter(i=>['ready','saved','failed','discarded'].includes(i.status)).length;
    // Each fact wraps as a unit in the narrow sidebar.
    $('batchSummary').replaceChildren(...(queue?[tx('batch_summary_ready',[ready+saved,items.length]),tx('batch_summary_saved',[saved]),...(failed?[tx('batch_summary_failed',[failed])]:[])]:[]).map(text=>Object.assign(document.createElement('span'),{textContent:text})));
    const next=JSON.stringify([queue,busy,working]);if(signature===next)return;signature=next;
    $('batchItems').replaceChildren();
    if(!queue)return;
    if(queue.error){$('batchError').textContent=queue.error;$('batchError').hidden=false;}
    for(const item of items){
      const row=document.createElement('li'),dot=document.createElement('span'),title=document.createElement('strong'),meta=document.createElement('p'),state=document.createElement('em'),tools=document.createElement('span');
      row.dataset.state=item.status;dot.className='batch-dot';dot.setAttribute('aria-hidden','true');tools.className='batch-tools';
      title.textContent=item.title||place(item.url);state.className='batch-item-state';state.textContent=statusLabel(item.status);
      meta.className='batch-meta';meta.append(state);if(item.title&&host(item.url))meta.append(' · '+host(item.url));
      const name=item.title||item.url;
      tools.append(iconButton('↗',tx('batch_open_title',[name]),()=>openSource(item)));
      const remove=iconButton('×',tx('batch_remove_title',[name]),()=>browser.runtime.sendMessage({type:'batchRemove',id:item.id}),'icon danger batch-remove');
      remove.disabled=item.status==='running';if(remove.disabled)remove.title=tx('batch_remove_running');
      tools.append(remove);row.append(dot,title,tools,meta);
      if(item.error){const error=document.createElement('p');error.className='batch-error';error.textContent=item.error;row.append(error);}
      if(item.status==='ready'&&item.captureId)row.append(button(tx('batch_review'),()=>browser.runtime.sendMessage({type:'openReview',id:item.captureId}),'sm batch-row-action'));
      if(item.status==='failed'){
        const retry=button(tx('batch_retry'),async()=>{
          const origins=AnacoObBatchPlan.permissionOrigins([item.url,...(item.requiredOrigins||[])]);
          if(!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
          await browser.runtime.sendMessage({type:'batchResume',id:item.id,windowId:panelWindowId});
        },'sm batch-row-action');retry.disabled=busy||working;row.append(retry);
      }
      $('batchItems').append(row);
    }
  }
  browser.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&(changes.batchQueue||changes.activeWork))render().catch(showError);});
  render().catch(showError);
})();
