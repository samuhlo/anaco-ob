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
    const count=chosen().length,total=(discovery?.nodes||[]).filter(n=>n.url&&!n.locked).length;
    $('courseCount').textContent=count>100?tx('course_selection_limit',[count,100]):tx('course_selection_count',[count,total]);
    $('courseCount').classList.toggle('danger',count>100);
    $('courseUse').textContent=count?tx('course_use_count',[count]):tx('course_use');$('courseUse').disabled=count===0||count>100;
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
    const contexts={};
    for(const node of chosen()){
      const chain=[node.title],seen=new Set([node.id]);let parent=node.parentId;
      while(parent&&!seen.has(parent)){seen.add(parent);const n=discovery.nodes.find(v=>v.id===parent);if(!n)break;chain.unshift(n.title);parent=n.parentId;}
      contexts[node.url]={page_url:discovery.root,resource_title:node.title,catalog:chain.join(' > '),catalog_position:node.sourcePosition==null?'':String(node.sourcePosition)};
    }
    AnacoObBatchUI.importLinks(urls,discovery.cookieStoreId,contexts);
  });
  async function render(){
    const {courseDiscovery:next}=await browser.storage.local.get('courseDiscovery');
    const changed=next?.id!==discovery?.id;discovery=next;
    if(changed||!pendingWrites)selection=new Set(discovery?.selected||[]);
    const busy=discovery?.status==='running',found=Boolean(discovery?.nodes.some(n=>n.url));$('courseStart').disabled=busy;$('courseStop').hidden=!busy;
    // Once links are listed, adding them is the main action; searching again steps back.
    $('courseStart').className=found?'sm':'primary';$('courseStart').textContent=found?tx('course_start_again'):tx('course_start');
    $('courseResult').hidden=!discovery;
    const stateName=busy?'running':discovery?.status==='paused'?'paused':discovery?.truncated||discovery?.blocked?.length?'partial':'done';
    $('courseState').textContent=discovery?{running:tx('course_state_running'),paused:tx('course_state_paused'),partial:tx('course_state_partial'),done:tx('course_state_done')}[stateName]:'';$('courseState').dataset.tone=stateName==='done'?'ok':'run';
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
        for(const text of [...discovery.warnings,...(discovery.truncated?[tx('course_limit')]:[]),...discovery.blocked.map(t=>new URL(t.url).hostname+': '+t.error)]){const p=document.createElement('p');p.className='hint';p.textContent=text;$('courseWarnings').append(p);}
        const add=(node,parent)=>{
          const children=discovery.nodes.filter(n=>n.parentId===node.id),box=document.createElement(children.length?'details':'div');
          box.className='course-node';box.dataset.courseGroup=node.id;
          if(children.length)box.open=node.id==='root'||opened.has(node.id)||changed;
          const heading=document.createElement(children.length?'summary':'div'),label=document.createElement('label'),check=document.createElement('input'),text=document.createElement('span'),kind=document.createElement('small');
          const links=descendants(node.id).length;
          kind.textContent=node.locked?tx('course_locked'):children.length?tx('course_kind_group',[links]):({module:tx('course_kind_module'),file:tx('course_kind_file'),video:tx('course_kind_video'),link:tx('course_kind_link')})[node.kind]||tx('course_kind_page');
          heading.className='course-row';check.type='checkbox';check.dataset.courseNode=node.id;text.textContent=node.title;text.append(kind);label.append(check,text);heading.append(label);box.append(heading);
          check.onclick=e=>e.stopPropagation();label.onclick=e=>e.stopPropagation();
          check.onchange=()=>{for(const id of descendants(node.id))check.checked?selection.add(id):selection.delete(id);persist();};
          if(node.url){const a=document.createElement('a');a.className='course-go';a.textContent='↗';a.title=tx('course_open_title',[node.title]);a.setAttribute('aria-label',a.title);a.href=node.url;a.target='_blank';a.rel='noopener noreferrer';a.onclick=e=>e.stopPropagation();heading.append(a);}
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
