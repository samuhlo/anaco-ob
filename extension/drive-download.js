/* Only confirm the requested Drive file on Google's own download endpoint.
   Logged-in and public downloads can return different GET/POST forms. */
globalThis.AnacoObDriveDownload=(()=>{
  const HOSTS=new Set(['drive.google.com','drive.usercontent.google.com']);
  const FIELDS=new Set(['id','export','confirm','uuid','resourcekey','authuser','at']);
  function confirmationRequest(html,responseURL,originalURL,diagnostic){
    const file=AnacoObMedia.driveFile(originalURL);if(!file)return null;
    let origin;try{origin=new URL(responseURL);}catch{return null;}
    if(origin.protocol!=='https:'||!HOSTS.has(origin.hostname))return null;
    const doc=new DOMParser().parseFromString(html,'text/html');
    const form=doc.querySelector('form#download-form');
    if(diagnostic){
      let action;try{action=new URL(form?.getAttribute('action')||'',responseURL);}catch{}
      (diagnostic.driveForms??=[]).push({responseHost:origin.hostname,found:Boolean(form),
        method:(form?.getAttribute('method')||'get').toUpperCase().slice(0,16),
        actionHost:action?.hostname||'',actionPath:action?.pathname==='/download'?'/download':'other',
        fields:[...doc.querySelectorAll('form#download-form input[type="hidden"][name]')].slice(0,20).map(i=>(i.getAttribute('name')||'').slice(0,64))});
    }
    if(!form||form.querySelector('input[type="password"]'))return null;
    const method=(form.getAttribute('method')||'get').toUpperCase();
    if(!['GET','POST'].includes(method))return null;
    let next;try{next=new URL(form.getAttribute('action'),responseURL);}catch{return null;}
    if(next.protocol!=='https:'||next.hostname!=='drive.usercontent.google.com'||next.pathname!=='/download'||next.username||next.password)return null;
    const fields=new Map(),hidden=new URLSearchParams();
    for(const [name,value] of next.searchParams){
      if(!FIELDS.has(name)||fields.has(name)||value.length>8192)return null;
      fields.set(name,value);
    }
    for(const input of form.querySelectorAll('input[type="hidden"][name]')){
      const name=input.getAttribute('name'),value=input.getAttribute('value')||'';
      if(!FIELDS.has(name)||hidden.has(name)||value.length>8192||fields.has(name)&&fields.get(name)!==value)return null;
      fields.set(name,value);hidden.set(name,value);
    }
    if(fields.get('id')!==file.id||fields.get('export')!=='download'||!fields.get('confirm'))return null;
    const original=new URL(file.download);
    for(const key of ['resourcekey','authuser'])if(original.searchParams.has(key)&&!fields.has(key)){
      fields.set(key,original.searchParams.get(key));hidden.set(key,original.searchParams.get(key));
    }
    if(method==='GET'){
      next.search='';for(const [name,value] of fields)next.searchParams.set(name,value);
      return {url:next.href,method};
    }
    return {url:next.href,method,body:hidden.toString(),headers:{'Content-Type':'application/x-www-form-urlencoded'}};
  }
  // Retained for callers that only need the GET target.
  function confirmationURL(html,responseURL,originalURL){
    const request=confirmationRequest(html,responseURL,originalURL);
    return request?.method==='GET'?request.url:null;
  }
  async function confirmation(response,originalURL,diagnostic){
    if(!AnacoObMedia.driveFile(originalURL)){await response.body?.cancel();return null;}
    const reader=response.body?.getReader();if(!reader)return null;
    const chunks=[];let size=0;
    try{
      for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>131072)return null;chunks.push(value);}
    }finally{await reader.cancel().catch(()=>{});}
    const bytes=new Uint8Array(size);let offset=0;
    for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    return confirmationRequest(new TextDecoder().decode(bytes),response.url,originalURL,diagnostic);
  }
  function publicRequest(originalURL){
    const file=AnacoObMedia.driveFile(originalURL);if(!file)return null;
    const url=new URL('https://drive.usercontent.google.com/download');
    url.searchParams.set('id',file.id);url.searchParams.set('export','download');url.searchParams.set('confirm','t');
    const source=new URL(file.url);if(source.searchParams.has('resourcekey'))url.searchParams.set('resourcekey',source.searchParams.get('resourcekey'));
    return {url:url.href,method:'GET'};
  }
  return {confirmationURL,confirmationRequest,confirmation,publicRequest};
})();
