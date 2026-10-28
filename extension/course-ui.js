(()=>{
  let discovery=null,selection=new Set(),signature='',pendingWrites=0,write=Promise.resolve();
  const action=fn=>async()=>{ $('courseError').hidden=true;try{await fn();}catch(error){$('courseError').textContent=error.message;$('courseError').hidden=false;} };
  function chosen(){return (discovery?.nodes||[]).filter(n=>n.url&&!n.locked&&selection.has(n.id));}
  function descendants(id){
    const nodes=discovery?.nodes||[],result=[],todo=[id],seen=new Set();
    while(todo.length){const key=todo.pop();if(seen.has(key))continue;seen.add(key);const node=nodes.find(n=>n.id===key);if(node?.url&&!node.locked)result.push(node.id);todo.push(...nodes.filter(n=>n.parentId===key).map(n=>n.id));}
    return result;
  }
  function counts(){
    const count=chosen().length;$('courseCount').textContent=tx('course_selection_count',[count,100]);$('courseUse').disabled=count===0||count>100;
    for(const check of document.querySelectorAll('#courseTree input[data-course-node]')){
      const ids=descendants(check.dataset.courseNode),total=ids.filter(id=>selection.has(id)).length;
      check.checked=Boolean(ids.length)&&total===ids.length;check.indeterminate=total>0&&total<ids.length;check.disabled=!ids.length;
    }
  }
  function persist(){
    counts();pendingWrites++;const ids=[...selection];
    write=write.catch(()=>{}).then(()=>browser.runtime.sendMessage({type:'courseSelect',ids})).catch(error=>{$('courseError').textContent=error.message;$('courseError').hidden=false;}).finally(()=>pendingWrites--);
  }
  $('courseStart').onclick=action(async()=>{
    const url=AnacoObCourseLinks.url($('courseURL').value);if(!url)throw new Error(tx('batch_invalid_url',[$('courseURL').value]));
    const u=new URL(url);
    if(!await browser.permissions.request({origins:[u.protocol+'//'+u.hostname+'/*'],permissions:['cookies']}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'courseStart',url,depth:$('courseDepth').value,windowId:panelWindowId,sourceTabId:boundSource?.tabId});
  });
  $('courseOpen').onclick=action(async()=>{const url=AnacoObCourseLinks.url($('courseURL').value);if(!url)throw new Error(tx('batch_invalid_url',[$('courseURL').value]));await browser.tabs.create({url,...(discovery?.cookieStoreId&&discovery.cookieStoreId!=='firefox-default'?{cookieStoreId:discovery.cookieStoreId}:{})});});
  $('courseStop').onclick=action(()=>browser.runtime.sendMessage({type:'courseStop'}));
  $('courseResume').onclick=action(async()=>{
    const origins=[...new Set((discovery?.blocked||[]).map(t=>t.origin).filter(Boolean))];
    if(origins.length&&!await browser.permissions.request({origins}))throw new Error(tx('batch_permissions'));
    await browser.runtime.sendMessage({type:'courseResume',windowId:panelWindowId});
  });
  $('courseAll').onclick=()=>{selection=new Set(discovery.nodes.filter(n=>n.url&&!n.locked).map(n=>n.id));persist();};
  $('courseNone').onclick=()=>{selection.clear();persist();};
  $('courseUse').onclick=action(async()=>{
    const urls=[...new Set(chosen().map(n=>n.url))];if(!urls.length||urls.length>100)throw new Error(tx('batch_url_limit'));
    if(discovery.status==='running')await browser.runtime.sendMessage({type:'courseStop'});
    AnacoObBatchUI.importLinks(urls,discovery.cookieStoreId);
    $('courseExplorer').open=false;
  });
  async function render(){
    const {courseDiscovery:next}=await browser.storage.local.get('courseDiscovery');
    const changed=next?.id!==discovery?.id;discovery=next;
    if(changed||!pendingWrites)selection=new Set(discovery?.selected||[]);
    const busy=discovery?.status==='running';$('courseStart').disabled=busy;$('courseStop').hidden=!busy;
    $('courseResume').hidden=busy||!discovery||(discovery.status!=='paused'&&!discovery.blocked.length);
    $('courseURL').disabled=$('courseDepth').disabled=busy;
    if(discovery){
      if(changed||!$('courseURL').value)$('courseURL').value=discovery.root;
      $('courseStatus').textContent=busy?tx('course_scanning',[discovery.count,discovery.nodes.filter(n=>n.url).length]):discovery.status==='paused'?tx('course_paused',[discovery.count,discovery.nodes.filter(n=>n.url).length]):tx('course_found',[discovery.count,discovery.nodes.filter(n=>n.url).length]);
      if(discovery.error){$('courseError').textContent=discovery.error;$('courseError').hidden=false;}
    }else $('courseStatus').textContent='';
    $('courseSelection').hidden=!discovery?.nodes.some(n=>n.url);
    const key=JSON.stringify([discovery?.nodes,discovery?.warnings,discovery?.blocked,discovery?.truncated]);
    if(key!==signature){
      signature=key;const opened=new Set([...document.querySelectorAll('#courseTree details[open]')].map(d=>d.dataset.courseGroup));
      $('courseTree').replaceChildren();$('courseWarnings').replaceChildren();
      if(discovery){
        for(const text of [...discovery.warnings,...(discovery.truncated?[tx('course_limit')]:[]),...discovery.blocked.map(t=>new URL(t.url).hostname+': '+t.error)]){const p=document.createElement('p');p.textContent=text;$('courseWarnings').append(p);}
        const add=(node,parent)=>{
          const children=discovery.nodes.filter(n=>n.parentId===node.id),box=document.createElement(children.length?'details':'div');
          box.className='course-node';box.dataset.courseGroup=node.id;
          if(children.length)box.open=node.id==='root'||opened.has(node.id)||changed;
          const heading=document.createElement(children.length?'summary':'div'),label=document.createElement('label'),check=document.createElement('input'),text=document.createElement('span');
          check.type='checkbox';check.dataset.courseNode=node.id;text.textContent=node.title;label.append(check,text);heading.append(label);box.append(heading);
          check.onclick=e=>e.stopPropagation();label.onclick=e=>e.stopPropagation();
          check.onchange=()=>{for(const id of descendants(node.id))check.checked?selection.add(id):selection.delete(id);persist();};
          if(node.locked){const hint=document.createElement('small');hint.textContent=tx('course_locked');heading.append(hint);}
          if(node.url){const a=document.createElement('a');a.textContent=tx('course_open');a.href=node.url;a.target='_blank';a.rel='noopener noreferrer';a.onclick=e=>e.stopPropagation();heading.append(a);}
          for(const child of children)add(child,box);parent.append(box);
        };
        const root=discovery.nodes.find(n=>n.id==='root');if(root)add(root,$('courseTree'));
      }
    }
    counts();
  }
  browser.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&changes.courseDiscovery)render().catch(showError);});
  render().catch(showError);
})();
