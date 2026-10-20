/* What is missing for Anaco to work, and how to fix it. Pure functions shared by
   the panel and the welcome page: no browser APIs here. */
globalThis.AnacoObDiagnosis=(()=>{
  const REPO='git+https://github.com/samuhlo/anaco-ob';
  // A failed connection to the local service.
  function connection(error){
    const text=String(error?.message||error||'');
    if(/no such native application|native application|not found|install\.py|anaco-ob install/i.test(text))
      return {kind:'missing',title:tx('diag_falta_el_servicio_local'),text:tx('diag_anaco_necesita_su_servicio_local_para_pr'),action:'welcome'};
    if(/vault/i.test(text))
      return {kind:'vault',title:tx('diag_no_encuentro_tu_vault'),text,action:'options'};
    return {kind:'error',title:tx('diag_el_servicio_local_no_responde'),text:text||tx('diag_error_desconocido'),action:'welcome'};
  }
  // Problems in a status reply from a running service.
  function status(reply,extensionVersion){
    const out=[];
    if(reply?.version&&extensionVersion&&reply.version!==extensionVersion)
      out.push({kind:'version',title:tx('diag_versiones_distintas'),text:tx('diag_la_extension_es_la_1_y_el_servicio_la_2_',[extensionVersion,reply.version]),action:'welcome'});
    if(reply?.ai&&!reply.ai.ready)
      out.push({kind:'ai',title:tx('diag_la_ia_no_esta_lista'),text:reply.ai.message||tx('diag_revisa_el_proveedor_de_ia_en_opciones'),action:'options'});
    return out;
  }
  // The one line the welcome page offers: it installs uv, Python if missing, and the service.
  function oneLine(os){
    const raw='https://raw.githubusercontent.com/samuhlo/anaco-ob/main/scripts/',page='https://github.com/samuhlo/anaco-ob/blob/main/scripts/';
    return os==='win'?{command:`powershell -ExecutionPolicy ByPass -c "irm ${raw}install.ps1 | iex"`,script:page+'install.ps1'}
      :{command:`curl -fsSL ${raw}install.sh | sh`,script:page+'install.sh'};
  }
  // Commands for runtime.getPlatformInfo().os: linux, mac or win.
  function installSteps(os){
    const pipx=os==='win'?[{text:tx('diag_instala_pipx_necesitas_python_3_11_o_sup'),command:'py -m pip install --user pipx\npy -m pipx ensurepath'}]
      :os==='mac'?[{text:tx('diag_instala_pipx_con_homebrew'),command:'brew install pipx\npipx ensurepath'}]
      :[{text:tx('diag_instala_pipx_con_el_gestor_de_paquetes_d'),command:'sudo apt install pipx   # '+tx('diag_o')+' sudo pacman -S python-pipx\npipx ensurepath'}];
    return [...pipx,
      {text:tx('diag_instala_el_servicio_local_de_anaco'),command:'pipx install '+REPO},
      {text:tx('diag_registralo_para_firefox_y_zen_con_la_rut'),command:`anaco-ob install --vault "${tx('diag_ruta_de_tu_vault')}"`},
      {text:tx('diag_comprueba_que_falta'),command:'anaco-ob doctor'}];
  }
  return {connection,status,oneLine,installSteps};
})();
