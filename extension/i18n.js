/* Interface language. Spanish is the main language and the fallback; English is
   used when chosen in Options or, in automatic mode, when the browser is English.
   Content scripts receive the language from the background (AnacoObLang). */
if(!globalThis.AnacoObI18n)globalThis.AnacoObI18n=(()=>{
  const catalog=()=>globalThis.AnacoObCatalog||{es:{}};
  const STORAGE='anaco-ob:lang';
  function chosen(){
    if(globalThis.AnacoObLang)return globalThis.AnacoObLang;
    try{if(typeof location!=='undefined'&&location.protocol==='moz-extension:')return localStorage.getItem(STORAGE)||'auto';}catch{/* Private storage can be blocked. */}
    return 'auto';
  }
  function language(){
    const value=chosen();
    if(value&&value!=='auto')return catalog()[value]?value:'es';
    const ui=String(globalThis.browser?.i18n?.getUILanguage?.()||globalThis.navigator?.language||'es').toLowerCase();
    return ui.startsWith('en')?'en':'es';
  }
  function tx(key,values=[]){
    const lang=language();
    let text=catalog()[lang]?.[key]??catalog().es?.[key]??key;
    values.forEach((value,index)=>{text=text.split('$'+(index+1)).join(String(value));});
    return text;
  }
  // Static text in pages: data-i18n for content, data-i18n-<attribute> for attributes.
  function localize(root=document){
    for(const node of root.querySelectorAll('[data-i18n]'))node.textContent=tx(node.dataset.i18n);
    for(const name of ['placeholder','title','aria-label','alt'])
      for(const node of root.querySelectorAll(`[data-i18n-${name}]`))node.setAttribute(name,tx(node.getAttribute(`data-i18n-${name}`)));
    if(root===document&&document.documentElement)document.documentElement.lang=language();
  }
  function set(value){try{localStorage.setItem(STORAGE,value);}catch{/* Falls back to automatic. */}}
  return {tx,localize,language,chosen,set};
})();
var tx=globalThis.AnacoObI18n.tx;
// Extension pages load this at the end of <body>: their markup is already there.
if(typeof document!=='undefined'&&typeof location!=='undefined'&&location.protocol==='moz-extension:'&&document.body?.querySelector('[data-i18n]')){
  globalThis.AnacoObI18n.localize();
  // Other open pages follow a change made in Options; their dynamic text needs a reload.
  addEventListener('storage',event=>{if(event.key==='anaco-ob:lang')location.reload();});
}
