/* Welcome page: a short guided first run. It explains why Anaco needs a local
   service, offers one line to install it, notices when it answers, and then
   sets the vault and the AI. welcome.html#install opens a given step. */
const $=id=>document.getElementById(id);
const native=message=>browser.runtime.sendMessage({type:'native',message});
const STEPS=['intro','why','install','vault','ai','done'];
const NAMES={linux:'Linux',mac:'macOS',win:'Windows'};
let os='linux',connected=false,pollTimer=null;

// =============================================================================
// [FLOW] STEPS
// =============================================================================

function show(step){
  if(!STEPS.includes(step))step='intro';
  for(const section of document.querySelectorAll('.onboard-step'))section.hidden=section.dataset.step!==step;
  STEPS.forEach((name,index)=>{const dot=$('dots').children[index];dot.classList.toggle('current',name===step);dot.classList.toggle('past',index<STEPS.indexOf(step));});
  history.replaceState(null,'','#'+step);
  const heading=document.querySelector(`[data-step="${step}"] h1`);if(heading){heading.tabIndex=-1;heading.focus();}
  clearInterval(pollTimer);
  if(step==='install')watchService();
  if(step==='vault')findVaults();
  if(step==='ai')loadAi();
  if(step==='done')check();
}
function dots(){
  for(const name of STEPS){const item=document.createElement('li');item.dataset.step=name;$('dots').append(item);}
}
for(const button of document.querySelectorAll('[data-go]'))button.addEventListener('click',()=>{
  if(button.hasAttribute('data-already'))$('installAsk').hidden=true;
  show(button.dataset.go);
});

// =============================================================================
// [FLOW] INSTALL
// =============================================================================

// The service answers «settings» even before a vault is configured.
async function serviceAnswers(){
  try{await native({action:'settings'});return true;}catch{return false;}
}
function status(ok){
  $('serviceStatus').hidden=false;
  $('serviceStatus').className='onboard-status '+(ok?'ok':'waiting');
  $('serviceStatus').textContent=ok?tx('welcome_pieza_conectada'):tx('welcome_esperando_la_pieza');
  $('installNext').hidden=!ok;
}
async function watchService(){
  connected=await serviceAnswers();
  if(connected){$('installAsk').hidden=true;$('installGuide').hidden=true;status(true);return;}
  if(!$('installGuide').hidden||$('installAsk').hidden)status(false);
  pollTimer=setInterval(async()=>{
    if(!await serviceAnswers())return;
    clearInterval(pollTimer);connected=true;status(true);
    // Give a moment to see the confirmation before moving on.
    setTimeout(()=>{if(location.hash==='#install')show('vault');},1400);
  },3000);
}
$('acceptInstall').onclick=()=>{$('installAsk').hidden=true;$('installGuide').hidden=false;status(false);};
async function copy(button,text){
  const label=button.textContent;
  try{await navigator.clipboard.writeText(text);button.textContent=tx('panel_copiado');}catch{button.textContent=tx('welcome_seleccionalo_y_copia');}
  setTimeout(()=>{button.textContent=label;},2000);
}
function installGuide(){
  const line=AnacoObDiagnosis.oneLine(os);
  $('installCommand').textContent=line.command;$('scriptLink').href=line.script;
  $('copyInstall').onclick=()=>copy($('copyInstall'),line.command);
  $('terminalHint').textContent=os==='win'?tx('welcome_terminal_windows'):os==='mac'?tx('welcome_terminal_mac'):tx('welcome_terminal_linux');
  $('platformNote').textContent=tx('welcome_pasos_para_1_copia_cada_comando_en_una_t',[NAMES[os]||os,os==='win'?' (PowerShell)':'']);
  for(const step of AnacoObDiagnosis.installSteps(os)){
    const item=document.createElement('li'),text=document.createElement('p'),code=document.createElement('pre');
    const button=Object.assign(document.createElement('button'),{type:'button',className:'copy-small',textContent:tx('panel_copiar')});
    button.onclick=()=>copy(button,step.command);
    text.textContent=step.text;code.textContent=step.command;item.append(text,code,button);$('steps').append(item);
  }
}

// =============================================================================
// [FLOW] VAULT
// =============================================================================

function choice(name,value,title,detail,checked){
  const label=document.createElement('label'),input=document.createElement('input'),text=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');
  label.className='onboard-choice';input.type='radio';input.name=name;input.value=value;input.checked=checked;
  strong.textContent=title;small.textContent=detail;text.append(strong,small);label.append(input,text);return label;
}
async function findVaults(){
  $('vaultSearch').textContent=tx('options_buscando_en_el_registro_de_obsidian_y_ca');$('vaultChoices').replaceChildren();$('vaultError').hidden=true;
  try{
    const [{vaults},settings]=await Promise.all([native({action:'discover_vaults'}),native({action:'settings'})]);
    const saved=settings.vault_available?settings.config.vault:null;
    for(const vault of vaults)$('vaultChoices').append(choice('vault',vault.path,vault.name,vault.path+' · '+vault.source,vault.path===saved||(!saved&&vaults.length===1)));
    $('vaultSearch').textContent=vaults.length?'':tx('welcome_no_he_encontrado_vaults');
    if(saved&&!vaults.some(v=>v.path===saved)){$('vaultPath').value=saved;$('vaultOther').querySelector('input').checked=true;}
    if(!vaults.length)$('vaultOther').querySelector('input').checked=true;
  }catch(error){$('vaultSearch').textContent=error.message;}
}
$('vaultPath').addEventListener('focus',()=>{$('vaultOther').querySelector('input').checked=true;});
$('saveVault').onclick=async()=>{
  const picked=document.querySelector('input[name="vault"]:checked');
  const path=picked?.value||$('vaultPath').value.trim();
  $('vaultError').hidden=true;
  if(!path){$('vaultError').textContent=tx('options_selecciona_un_vault_detectado_o_introduc');$('vaultError').hidden=false;return;}
  $('saveVault').disabled=true;
  try{await native({action:'configure',values:{vault:path,vault_mode:picked?.value?'auto':'manual'}});show('ai');}
  catch(error){$('vaultError').textContent=error.message;$('vaultError').hidden=false;}
  finally{$('saveVault').disabled=false;}
};

// =============================================================================
// [FLOW] AI
// =============================================================================

function aiDetails(){
  const value=document.querySelector('input[name="ai"]:checked')?.value;
  for(const detail of document.querySelectorAll('.onboard-detail'))detail.hidden=detail.dataset.for!==value;
}
function keyLink(){
  const service=AnacoObProviders.find($('aiService').value);
  $('aiKeyLink').href=service.keys;$('aiKeyLink').textContent=tx('options_consigue_tu_clave_de_1',[service.name]);
}
async function loadAi(){
  $('aiError').hidden=true;
  try{
    const {config}=await native({action:'settings'});
    const service=AnacoObProviders.find(AnacoObProviders.match(config.api_base));
    const kind=config.provider==='openai'?(service?.local?'local':'service'):config.provider;
    const input=document.querySelector(`input[name="ai"][value="${kind}"]`);if(input)input.checked=true;
    if(service&&!service.local)$('aiService').value=service.id;
    if(service?.local){$('aiLocal').value=service.id;$('aiLocalModel').value=config.api_model;}
    $('aiKey').placeholder=config.api_key_set?tx('options_clave_guardada_escribe_otra_para_cambiar'):'';
  }catch(error){$('aiError').textContent=error.message;$('aiError').hidden=false;}
  keyLink();aiDetails();
}
function aiServices(){
  for(const service of AnacoObProviders.SERVICES)(service.local?$('aiLocal'):$('aiService')).add(new Option(service.name,service.id));
  $('aiLocalModel').value=AnacoObProviders.find('ollama').model;
  $('aiService').onchange=keyLink;
  $('aiLocal').onchange=()=>{$('aiLocalModel').value=AnacoObProviders.find($('aiLocal').value).model;};
  for(const input of document.querySelectorAll('input[name="ai"]'))input.addEventListener('change',aiDetails);
}
$('saveAi').onclick=async()=>{
  const kind=document.querySelector('input[name="ai"]:checked')?.value;
  if(!kind){$('aiError').textContent=tx('welcome_elige_una_opcion');$('aiError').hidden=false;return;}
  let values={provider:kind};
  if(kind==='service'||kind==='local'){
    const service=AnacoObProviders.find(kind==='service'?$('aiService').value:$('aiLocal').value);
    values={provider:'openai',api_base:service.base,api_model:kind==='local'?$('aiLocalModel').value.trim():service.model,api_vision_model:''};
    // An empty key keeps the stored one; local servers need none.
    if(kind==='service')values.api_key=$('aiKey').value.trim();
  }
  $('saveAi').disabled=true;$('aiError').hidden=true;
  try{await native({action:'configure',values});$('aiKey').value='';show('done');}
  catch(error){$('aiError').textContent=error.message;$('aiError').hidden=false;}
  finally{$('saveAi').disabled=false;}
};

// =============================================================================
// [FLOW] DONE
// =============================================================================

function line(ok,text){const item=document.createElement('li');item.className=ok?'ok':'missing';item.textContent=(ok?'✓ ':'✗ ')+text;$('checks').append(item);}
// Each piece in order: service, version, vault, profile and AI.
async function check(){
  $('checks').replaceChildren();
  try{
    const reply=await native({action:'status'});
    line(true,tx('welcome_servicio_local_conectado'));
    const problems=AnacoObDiagnosis.status(reply,browser.runtime.getManifest().version);
    for(const problem of problems)line(false,problem.title+': '+problem.text);
    $('profileNext').hidden=!reply.profile?.missing;
    line(!reply.profile?.missing,reply.profile?.missing?tx('welcome_tu_vault_aun_no_tiene_perfil_confirmalo_'):tx('welcome_perfil_del_vault_confirmado'));
    if(!problems.length&&!reply.profile?.missing)line(true,tx('welcome_todo_listo_abre_el_panel_de_anaco_en_cua'));
  }catch(error){
    const problem=AnacoObDiagnosis.connection(error);line(false,problem.title+': '+problem.text);
  }
}
$('openOptions').onclick=()=>browser.runtime.openOptionsPage();

async function start(){
  dots();aiServices();
  os=(await browser.runtime.getPlatformInfo()).os;
  installGuide();
  show(location.hash.slice(1)||'intro');
}
start();
