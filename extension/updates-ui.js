/* Shared by Options and the sidebar; all work lives in the background page. */
(()=>{
  const el=id=>document.getElementById(id),options=Boolean(el('updatesCard'));
  let checking=false;
  async function render(){
    const {updateState={},updateInstalling=false,updateInstallError='',autoUpdateCheck=true}=await browser.storage.local.get(['updateState','updateInstalling','updateInstallError','autoUpdateCheck']);
    const ext=updateState.extension||{},service=updateState.service||{};
    if(!options){
      el('updateNotice').hidden=!(ext.available||service.available||updateInstalling);
      el('updateNoticeText').textContent=updateInstalling?tx('updates_installing'):tx('updates_available');return;
    }
    el('autoUpdateCheck').checked=autoUpdateCheck;
    const line=(label,data)=>label+' · '+(data.current||tx('updates_unknown'))+(data.error?' · '+tx('updates_check_error'):data.available?' → '+data.latest:data.latest?' · '+tx('updates_current'):data.unpublished?' · '+tx('updates_unpublished'):'');
    el('extensionVersion').textContent=line(tx('updates_extension'),{...ext,current:browser.runtime.getManifest().version});
    el('serviceVersion').textContent=line(tx('updates_service'),service);
    el('updateExtension').hidden=!ext.available;
    el('updateService').hidden=!(service.available&&service.canUpdate);
    el('updateMigration').hidden=service.canUpdate!==false;
    for(const id of ['checkUpdates','updateExtension','updateService'])el(id).disabled=checking||updateInstalling;
    el('updateStatus').textContent=updateInstalling?tx('updates_installing'):checking?tx('updates_checking'):updateInstallError|| (updateState.checkedAt?tx('updates_checked',[new Date(updateState.checkedAt).toLocaleString()]):tx('updates_not_checked'));
  }
  async function action(type){
    checking=true;await render();
    try{await browser.runtime.sendMessage({type,force:true});}
    catch(error){el('updateStatus').textContent=error.message;checking=false;for(const id of ['checkUpdates','updateExtension','updateService'])el(id).disabled=false;return;}
    checking=false;await render();
  }
  if(options){
    el('checkUpdates').onclick=()=>action('checkUpdates');
    el('updateService').onclick=()=>action('installServiceUpdate');
    el('updateExtension').onclick=()=>action('installExtensionUpdate');
    el('autoUpdateCheck').onchange=async()=>{await browser.storage.local.set({autoUpdateCheck:el('autoUpdateCheck').checked});if(el('autoUpdateCheck').checked)await browser.runtime.sendMessage({type:'checkUpdates'});};
  }else el('showUpdates').onclick=()=>browser.runtime.openOptionsPage();
  browser.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&['updateState','updateInstalling','updateInstallError','autoUpdateCheck'].some(k=>k in changes))render();});
  render();
})();
