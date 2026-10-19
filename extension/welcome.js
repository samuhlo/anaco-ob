/* Welcome page: install steps for this system and a live check of each piece. */
const $=id=>document.getElementById(id);
const NAMES={linux:'Linux',mac:'macOS',win:'Windows'};

async function steps(){
  const {os}=await browser.runtime.getPlatformInfo();
  $('platformNote').textContent=`Pasos para ${NAMES[os]||os}. Copia cada comando en una terminal${os==='win'?' (PowerShell)':''}.`;
  for(const step of AnacoObDiagnosis.installSteps(os)){
    const copy=Object.assign(document.createElement('button'),{type:'button',className:'copy-small',textContent:'Copiar'});
    copy.onclick=async()=>{try{await navigator.clipboard.writeText(step.command);copy.textContent='Copiado ✓';}catch{copy.textContent='Selecciónalo y copia';}setTimeout(()=>{copy.textContent='Copiar';},2000);};
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
    line(true,'Servicio local conectado');
    const problems=AnacoObDiagnosis.status(status,browser.runtime.getManifest().version);
    for(const problem of problems)line(false,problem.title+': '+problem.text);
    line(!status.profile?.missing,status.profile?.missing?'Tu vault aún no tiene perfil: confírmalo en Opciones.':'Perfil del vault confirmado');
    if(!problems.length&&!status.profile?.missing)line(true,'Todo listo. Abre el panel de Anaco en cualquier artículo.');
  }catch(error){
    const problem=AnacoObDiagnosis.connection(error);line(false,problem.title+': '+problem.text);
  }finally{$('check').disabled=false;}
}

$('check').onclick=check;
$('openOptions').onclick=()=>browser.runtime.openOptionsPage();
steps();
