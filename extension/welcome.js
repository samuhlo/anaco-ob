/* Welcome page: install steps for this system and a live check of each piece. */
const $=id=>document.getElementById(id);
const NAMES={linux:'Linux',mac:'macOS',win:'Windows'};

async function steps(){
  const {os}=await browser.runtime.getPlatformInfo();
  $('platformNote').textContent=tx('welcome_pasos_para_1_copia_cada_comando_en_una_t',[NAMES[os]||os,os==='win'?' (PowerShell)':'']);
  for(const step of AnacoObDiagnosis.installSteps(os)){
    const copy=Object.assign(document.createElement('button'),{type:'button',className:'copy-small',textContent:tx('panel_copiar')});
    copy.onclick=async()=>{try{await navigator.clipboard.writeText(step.command);copy.textContent=tx('panel_copiado');}catch{copy.textContent=tx('welcome_seleccionalo_y_copia');}setTimeout(()=>{copy.textContent=tx('panel_copiar');},2000);};
    const item=document.createElement('li'),text=document.createElement('p'),code=document.createElement('pre');
    text.textContent=step.text;code.textContent=step.command;item.append(text,code,copy);$('steps').append(item);
  }
}

function line(ok,text){const item=document.createElement('li');item.className=ok?'ok':'missing';item.textContent=(ok?'✓ ':'✗ ')+text;$('checks').append(item);}

// Each piece in order: service, version, vault, profile and AI.
async function check(){
  $('checks').replaceChildren();$('check').disabled=true;
  try{
    const status=await browser.runtime.sendMessage({type:'native',message:{action:'status'}});
    line(true,tx('welcome_servicio_local_conectado'));
    const problems=AnacoObDiagnosis.status(status,browser.runtime.getManifest().version);
    for(const problem of problems)line(false,problem.title+': '+problem.text);
    line(!status.profile?.missing,status.profile?.missing?tx('welcome_tu_vault_aun_no_tiene_perfil_confirmalo_'):tx('welcome_perfil_del_vault_confirmado'));
    if(!problems.length&&!status.profile?.missing)line(true,tx('welcome_todo_listo_abre_el_panel_de_anaco_en_cua'));
  }catch(error){
    const problem=AnacoObDiagnosis.connection(error);line(false,problem.title+': '+problem.text);
  }finally{$('check').disabled=false;}
}

$('check').onclick=check;
$('openOptions').onclick=()=>browser.runtime.openOptionsPage();
steps();
