globalThis.AnacoObBatchUI={busy:false};
(()=>{
  let queue=null,signature='',pageQueueId=null,newList=false,previousQueueId=null,importedCookieStoreId=null;
  const action=fn=>async()=>{
    $('batchError').hidden=true;
    try{await fn();}catch(error){$('batchError').textContent=error.message;$('batchError').hidden=false;}
  };
  const button=(label,fn)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=action(fn);return b;};
  $('batchStart').onclick=action(async()=>{
    const urls=AnacoObBatchPlan.urls($('batchURLs').value);
    const origins=AnacoObBatchPlan.permissionOrigins(urls);
    // Request immediately in the click, including optional container permission.
    if(!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'batchStart',urls:urls.join('\n'),windowId:panelWindowId,mode:$('batchMode').value,cookieStoreId:importedCookieStoreId,
      provider:$('provider').value,intent:$('intent').value,note_structure:$('noteStructure').value,captureMode:$('captureMode').value});
    $('batchURLs').value='';newList=false;render().catch(showError);
  });
  AnacoObBatchUI.importLinks=(urls,cookieStoreId)=>{newList=true;importedCookieStoreId=cookieStoreId;$('batchURLs').value=urls.join('\n');$('batchSection').open=true;render().then(()=>$('batchURLs').focus()).catch(showError);};
  $('batchRestartVideos').onclick=action(()=>browser.runtime.sendMessage({type:'batchRestartVideos',windowId:panelWindowId}));
  $('batchBack').onclick=()=>{pageQueueId=queue?.id;newList=false;$('batchSection').open=false;render().catch(showError);};
  $('batchNewList').onclick=()=>{newList=true;importedCookieStoreId=null;render().then(()=>$('batchURLs').focus()).catch(showError);};
  $('batchSection').addEventListener('toggle',()=>{
    if($('batchSection').open&&queue&&pageQueueId===queue.id){pageQueueId=null;render().catch(showError);}
  });
  $('batchRetryFailed').onclick=action(async()=>{
    const failed=queue?.items.filter(i=>i.status==='failed')||[];
    const origins=AnacoObBatchPlan.permissionOrigins(failed.flatMap(i=>[i.url,...(i.requiredOrigins||[])]));
    if(origins.length&&!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'batchRetryFailed',windowId:panelWindowId});
  });
  $('batchClearFailed').onclick=action(()=>browser.runtime.sendMessage({type:'batchClear',failedOnly:true}));
  $('batchClear').onclick=action(async()=>{
    await browser.runtime.sendMessage({type:'batchClear'});await render();
    $('batchSection').open=true;$('batchURLs').focus();
  });
  $('batchPause').onclick=action(()=>browser.runtime.sendMessage({type:'batchPause'}));
  $('batchResume').onclick=action(()=>browser.runtime.sendMessage({type:'batchResume',windowId:panelWindowId}));
  const statusLabel=value=>({saved:tx('batch_status_saved'),discarded:tx('batch_status_discarded'),pending:tx('batch_status_pending'),running:tx('batch_status_running'),ready:tx('batch_status_ready'),failed:tx('batch_status_failed'),paused:tx('batch_status_paused'),pausing:tx('batch_status_pausing'),complete:tx('batch_status_complete')})[value]||value;
  async function render(){
    const data=await browser.storage.local.get(['batchQueue','activeWork']);queue=data.batchQueue;
    const busy=['running','pausing'].includes(queue?.status);AnacoObBatchUI.busy=busy;
    if(queue?.id!==previousQueueId){newList=false;previousQueueId=queue?.id;}
    const focused=!manualImport&&Boolean(queue?.items.length)&&(busy||pageQueueId!==queue.id);
    document.body.classList.toggle('is-batch',focused);
    if(focused)$('batchSection').open=true;
    $('batchForm').hidden=focused&&!newList;
    $('batchBack').hidden=!focused||busy;$('batchBack').disabled=busy;
    $('batchNewList').hidden=!focused||newList||busy||Boolean(queue?.items.some(i=>i.status==='pending'));
    $('batchNewList').disabled=busy||Boolean(data.activeWork)||Boolean(queue?.items.some(i=>i.status==='pending'));
    $('batchRetryFailed').hidden=busy||!queue?.items.some(i=>i.status==='failed');
    $('batchRetryFailed').disabled=busy||Boolean(data.activeWork);
    $('batchClearFailed').hidden=!queue?.items.some(i=>i.status==='failed');
    $('batchClear').hidden=!queue?.items.length;$('batchClear').disabled=busy;
    $('batchStart').disabled=busy||Boolean(data.activeWork)||Boolean(queue?.items.some(i=>i.status==='pending'));
    $('batchPause').hidden=!busy;$('batchPause').disabled=queue?.status==='pausing';
    $('batchResume').hidden=busy||!queue?.items.some(i=>i.status==='pending');
    $('batchResume').disabled=Boolean(data.activeWork);
    $('batchRestartVideos').hidden=busy||!queue||!queue.items.some(i=>!['saved','discarded'].includes(i.status));
    $('batchRestartVideos').disabled=busy||Boolean(data.activeWork);
    $('useActiveTab').disabled=busy||Boolean(data.activeWork);
    $('batchSummary').textContent=queue?tx('batch_summary',[statusLabel(queue.status),queue.items.filter(i=>['ready','saved'].includes(i.status)).length,queue.items.length,queue.items.filter(i=>i.status==='saved').length]):'';
    const next=JSON.stringify([queue,busy,Boolean(data.activeWork)]);if(signature===next)return;signature=next;
    $('batchItems').replaceChildren();
    if(!queue)return;
    if(queue.error){$('batchError').textContent=queue.error;$('batchError').hidden=false;}
    for(const item of queue.items){
      const row=document.createElement('li'),title=document.createElement('strong'),status=document.createElement('p');
      row.dataset.state=item.status;status.className='batch-item-state';
      title.textContent=item.title||item.url;status.textContent=statusLabel(item.status);row.append(title,status);
      if(item.error){const error=document.createElement('p');error.className='muted';error.textContent=item.error;row.append(error);}
      if(item.status==='ready'&&item.captureId)row.append(button(tx('batch_review'),()=>browser.runtime.sendMessage({type:'openReview',id:item.captureId})));
      if(item.status==='failed'){
        const retry=button(tx('batch_retry'),async()=>{
          const origins=AnacoObBatchPlan.permissionOrigins([item.url,...(item.requiredOrigins||[])]);
          if(!await browser.permissions.request({origins,permissions:['cookies']}))throw new Error(tx('batch_permissions'));
          await browser.runtime.sendMessage({type:'batchResume',id:item.id,windowId:panelWindowId});
        });retry.disabled=busy||Boolean(data.activeWork);row.append(retry);
      }
      row.append(button(tx('batch_open'),async()=>{
        if(item.tabId){try{await browser.tabs.update(item.tabId,{active:true});return;}catch{}}
        await browser.tabs.create({url:item.url,...(queue.cookieStoreId&&queue.cookieStoreId!=='firefox-default'?{cookieStoreId:queue.cookieStoreId}:{})});
      }));
      const remove=button(tx('batch_remove'),()=>browser.runtime.sendMessage({type:'batchRemove',id:item.id}));
      remove.className='batch-remove';remove.disabled=item.status==='running';
      remove.setAttribute('aria-label',tx('batch_remove_title',[item.title||item.url]));
      if(remove.disabled)remove.title=tx('batch_remove_running');
      row.append(remove);$('batchItems').append(row);
    }
  }
  browser.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&(changes.batchQueue||changes.activeWork))render().catch(showError);});
  render().catch(showError);
})();
