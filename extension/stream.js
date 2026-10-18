/* Selected HLS resources are fetched in the browser, retaining its course session.
   No cookies are exported. Encrypted/live streams are rejected explicitly. */
const ZenBrainStream = (() => {
  function playlist(text, base) {
    if (!text.trimStart().startsWith('#EXTM3U')) throw new Error('El recurso no es un manifiesto HLS válido; puede ser una página de acceso.');
    const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const resolve = value => {const u=new URL(value,base);if(!/^https?:$/.test(u.protocol))throw new Error('El vídeo contiene una dirección no compatible.');return u.href;};
    if (lines.some(l => l.startsWith('#EXT-X-KEY:') && !/METHOD=NONE(?:,|$)/.test(l))) throw new Error('Este vídeo usa segmentos cifrados. No se puede transcribir con el capturador actual.');
    if (lines.some(l => l.startsWith('#EXT-X-BYTERANGE:')||l.startsWith('#EXT-X-MAP:')&&/BYTERANGE=/.test(l))) throw new Error('Este vídeo usa rangos de segmentos que todavía no admite el capturador.');
    const variants=[];
    for(let i=0;i<lines.length;i++)if(lines[i].startsWith('#EXT-X-STREAM-INF:')){
      const next=lines[i+1];if(next&&!next.startsWith('#'))variants.push({url:resolve(next),bandwidth:Number(lines[i].match(/(?:^|,)BANDWIDTH=(\d+)/)?.[1]||lines[i].match(/BANDWIDTH=(\d+)/)?.[1]||Infinity)});
    }
    if(variants.length)return {variant:variants.sort((a,b)=>a.bandwidth-b.bandwidth)[0].url};
    if(!lines.includes('#EXT-X-ENDLIST'))throw new Error('El vídeo no expone una lista completa de segmentos. Los directos no se pueden capturar todavía.');
    const segments=[];
    let duration=0;
    for(const line of lines){
      if(line.startsWith('#EXTINF:'))duration+=Number(line.slice(8).split(',')[0])||0;
      if(line.startsWith('#EXT-X-MAP:')){
        const match=line.match(/URI="([^"]+)"/);if(match)segments.push(resolve(match[1]));
      }else if(!line.startsWith('#'))segments.push(resolve(line));
    }
    if(!segments.length||segments.length>4000)throw new Error('No se ha encontrado una lista de segmentos de tamaño compatible.');
    return {segments,duration};
  }
  async function download(url, {maxBytes=100000000,maxSeconds=7200,onProgress=()=>{},load} = {}) {
    const parts=[];let size=0;
    async function resource(address, text=false){
      if(load){
        const result=await load(address,text?2000000:maxBytes-size);
        if(result.size>(text?2000000:maxBytes-size))throw new Error('El vídeo supera el límite de 100 MB de esta captura.');
        if(text)return {text:new TextDecoder().decode(await new Blob(result.parts).arrayBuffer()),url:result.url||address};
        size+=result.size;parts.push(...result.parts);return;
      }
      let response;
      try{response=await fetch(address,{credentials:'include',signal:AbortSignal.timeout(30000)});}
      catch{throw new Error('No se pudo leer un recurso del vídeo en '+new URL(address).hostname+'. Puede requerir permiso para ese dominio.');}
      if(!response.ok)throw new Error(`El servidor del vídeo rechazó el acceso (HTTP ${response.status}).`);
      const reader=response.body.getReader(),chunks=[];let length=0;
      while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;
        if(length>(text?2000000:maxBytes-size)){await reader.cancel();throw new Error('El vídeo supera el límite de 100 MB de esta captura.');}
        chunks.push(value);
      }
      if(text)return {text:new TextDecoder().decode(await new Blob(chunks).arrayBuffer()),url:response.url||address};
      size+=length;parts.push(...chunks);
    }
    let parsed;
    for(let level=0;level<4;level++){
      const manifest=await resource(url,true);
      parsed=playlist(manifest.text,manifest.url);
      if(!parsed.variant)break;
      url=parsed.variant;
    }
    if(parsed.variant)throw new Error('El manifiesto del vídeo contiene demasiados niveles.');
    if(parsed.duration>maxSeconds)throw new Error('El vídeo supera la duración máxima configurada.');
    for(let i=0;i<parsed.segments.length;i++){
      onProgress(i+1,parsed.segments.length);
      await resource(parsed.segments[i]);
    }
    return {parts,size};
  }
  return {playlist,download};
})();
