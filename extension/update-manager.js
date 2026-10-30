/* Official stable channels only. Network checks never include captured content. */
globalThis.AnacoObUpdates=(()=>{
  const AMO='https://addons.mozilla.org/api/v5/addons/addon/anaco-ob%40samuhlo/';
  const GITHUB='https://api.github.com/repos/samuhlo/anaco-ob/releases/latest';
  const DAY=24*60*60*1000;
  let checking=null,installing=false;
  function version(value){return typeof value==='string'&&/^\d+\.\d+\.\d+$/.test(value)?value.split('.').map(Number):null;}
  function newer(candidate,current){
    const a=version(candidate),b=version(current);if(!a||!b)return false;
    for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i];}return false;
  }
  async function json(url){
    const response=await fetch(url,{credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000)});
    if(response.status===404&&url===GITHUB)return null;
    if(!response.ok)throw new Error(String(response.status));
    return response.json();
  }
  async function check(force=false){
    if(installing)return (await browser.storage.local.get('updateState')).updateState||{};
    if(checking){const result=await checking;return force?check(true):result;}
    checking=(async()=>{
      const {updateState={},autoUpdateCheck=true}=await browser.storage.local.get(['updateState','autoUpdateCheck']);
      if(!force&&(!autoUpdateCheck||Date.now()-(updateState.checkedAt||0)<DAY))return updateState;
      const result={checkedAt:Date.now(),extension:{current:browser.runtime.getManifest().version},service:{}};
      const replies=await Promise.allSettled([json(AMO),json(GITHUB),native({action:'update_info'},25000)]);
      if(replies[0].status==='fulfilled'){
        const data=replies[0].value,v=data?.current_version;
        if(data?.guid==='anaco-ob@samuhlo'&&version(v?.version)&&v?.file?.status==='public')Object.assign(result.extension,{latest:v.version,available:newer(v.version,result.extension.current)});
        else result.extension.error=true;
      }else result.extension.error=true;
      if(replies[1].status==='fulfilled'){
        const data=replies[1].value,tag=data?.tag_name;
        if(data===null)result.service.unpublished=true;
        else if(!data.draft&&!data.prerelease&&/^v\d+\.\d+\.\d+$/.test(tag))result.service.latest=tag.slice(1);
        else result.service.error=true;
      }else result.service.error=true;
      if(replies[2].status==='fulfilled')Object.assign(result.service,{current:replies[2].value.version,canUpdate:replies[2].value.can_update===true});
      else {
        // Pre-1.3.2 services do not expose update_info. Keep a migration path.
        try{result.service.current=(await native({action:'status'},25000)).version;}catch{}
        result.service.canUpdate=false;
      }
      result.service.available=newer(result.service.latest,result.service.current);
      await browser.storage.local.set({updateState:result});return result;
    })();
    try{return await checking;}finally{checking=null;}
  }
  async function installService(){
    if(installing||checking||workClaim||requests.size||globalThis.AnacoObBatch?.busy())throw new Error(tx('updates_busy'));
    installing=true;
    try{
      const {updateState}=await browser.storage.local.get('updateState'),service=updateState?.service;
      if(!service?.canUpdate||!newer(service.latest,service.current))throw new Error(tx('updates_check_first'));
      await browser.storage.local.set({updateInstalling:true,updateInstallError:''});
      await native({action:'install_update',version:service.latest},1900000);
      // No requests remain: detach the old host before reconnecting.
      if(port){const old=port;port=null;old.disconnect();}
      const info=await native({action:'update_info'},25000);
      if(info.version!==service.latest)throw new Error(tx('updates_reconnect'));
      const state={...updateState,service:{...service,current:info.version,available:false}};
      await browser.storage.local.set({updateState:state});return state;
    }catch(error){await browser.storage.local.set({updateInstallError:error.message});throw error;}
    finally{installing=false;await browser.storage.local.set({updateInstalling:false});}
  }
  async function extension(){
    if(installing||checking||workClaim||requests.size||globalThis.AnacoObBatch?.busy())throw new Error(tx('updates_busy'));
    // Mozilla handles signing, compatibility and the user's installation approval.
    return browser.tabs.create({url:'https://addons.mozilla.org/firefox/addon/anaco/'});
  }
  function start(){
    browser.storage.local.set({updateInstalling:false});
    browser.alarms.create('anaco-update-check',{periodInMinutes:60});
    browser.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='anaco-update-check')check().catch(()=>{});});
    check().catch(()=>{});
  }
  return {check,installService,extension,start,newer,busy:()=>installing};
})();
AnacoObUpdates.start();
