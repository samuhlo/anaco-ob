/* What is missing for Anaco to work, and how to fix it. Pure functions shared by
   the panel and the welcome page: no browser APIs here. */
globalThis.AnacoObDiagnosis=(()=>{
  const REPO='git+https://github.com/samuhlo/anaco-ob';
  // A failed connection to the local service.
  function connection(error){
    const text=String(error?.message||error||'');
    if(/no such native application|native application|not found|install\.py|anaco-ob install/i.test(text))
      return {kind:'missing',title:'Falta el servicio local',text:'Anaco necesita su servicio local para preparar y guardar notas. Se instala una vez con dos comandos.',action:'welcome'};
    if(/vault/i.test(text))
      return {kind:'vault',title:'No encuentro tu vault',text,action:'options'};
    return {kind:'error',title:'El servicio local no responde',text:text||'Error desconocido.',action:'welcome'};
  }
  // Problems in a status reply from a running service.
  function status(reply,extensionVersion){
    const out=[];
    if(reply?.version&&extensionVersion&&reply.version!==extensionVersion)
      out.push({kind:'version',title:'Versiones distintas',text:`La extensión es la ${extensionVersion} y el servicio la ${reply.version}. Actualiza el servicio con «pipx upgrade anaco-ob» y vuelve a ejecutar «anaco-ob install».`,action:'welcome'});
    if(reply?.ai&&!reply.ai.ready)
      out.push({kind:'ai',title:'La IA no está lista',text:reply.ai.message||'Revisa el proveedor de IA en Opciones.',action:'options'});
    return out;
  }
  // Commands for runtime.getPlatformInfo().os: linux, mac or win.
  function installSteps(os){
    const pipx=os==='win'?[{text:'Instala pipx (necesitas Python 3.11 o superior)',command:'py -m pip install --user pipx\npy -m pipx ensurepath'}]
      :os==='mac'?[{text:'Instala pipx con Homebrew',command:'brew install pipx\npipx ensurepath'}]
      :[{text:'Instala pipx con el gestor de paquetes de tu sistema (por ejemplo)',command:'sudo apt install pipx   # o: sudo pacman -S python-pipx\npipx ensurepath'}];
    return [...pipx,
      {text:'Instala el servicio local de Anaco',command:'pipx install '+REPO},
      {text:'Regístralo para Firefox y Zen con la ruta de tu vault',command:'anaco-ob install --vault "RUTA/DE/TU/VAULT"'},
      {text:'Comprueba qué falta',command:'anaco-ob doctor'}];
  }
  return {connection,status,installSteps};
})();
