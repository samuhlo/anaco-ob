/* Firefox MV2 page-context reads preserve the player's cookie partition and
   referrer. Transfer bounded chunks, never a whole video in one IPC message. */
if(!globalThis.AnacoObResource)globalThis.AnacoObResource=(()=>{
  const jobs=new Map();
  function close(id){const job=jobs.get(id);if(!job)return;jobs.delete(id);clearTimeout(job.timer);job.controller.abort();job.reader?.cancel().catch(()=>{});}
  async function open(url,maxBytes){
    if(!/^https?:$/.test(new URL(url).protocol))throw new Error('Dirección de recurso no admitida.');
    if(!Number.isInteger(maxBytes)||maxBytes<1||maxBytes>100000000)throw new Error('Límite de descarga no válido.');
    if(typeof content==='undefined'||typeof content.fetch!=='function')throw new Error('La lectura con el contexto del reproductor no está disponible.');
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
    let response;
    try{response=await content.fetch(url,{credentials:'include',signal:controller.signal});}
    catch(error){clearTimeout(timer);throw error;}
    clearTimeout(timer);
    if(!response.ok){controller.abort();return {ok:false,status:response.status};}
    const type=response.headers.get('content-type')||'';
    if(/text\/html|application\/xhtml/i.test(type)){controller.abort();return {ok:false,status:response.status,reason:'login-response'};}
    if(Number(response.headers.get('content-length'))>maxBytes){controller.abort();throw new Error('El recurso supera el límite de descarga.');}
    const id=crypto.randomUUID();
    const job={controller,reader:response.body.getReader(),size:0,maxBytes,pending:null,timer:null};
    job.timer=setTimeout(()=>close(id),60000);jobs.set(id,job);
    return {ok:true,id,status:response.status,url:response.url||url,type};
  }
  async function read(id){
    const job=jobs.get(id);if(!job)throw new Error('La descarga del reproductor se interrumpió.');
    clearTimeout(job.timer);job.timer=setTimeout(()=>close(id),60000);
    try{
      let value=job.pending;job.pending=null;
      if(!value){const next=await job.reader.read();if(next.done){close(id);return {done:true};}value=next.value;job.size+=value.length;}
      if(job.size>job.maxBytes)throw new Error('El recurso supera el límite de descarga.');
      if(value.length>393216){job.pending=value.subarray(393216);value=value.subarray(0,393216);}
      let binary='';for(let i=0;i<value.length;i+=8192)binary+=String.fromCharCode(...value.subarray(i,i+8192));
      return {done:false,data:btoa(binary)};
    }catch(error){close(id);throw error;}
  }
  return {open,read,close};
})();
