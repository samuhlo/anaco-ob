/* Selected HLS resources are fetched in the browser, retaining its course session.
   No cookies are exported. Encrypted/live streams are rejected explicitly. */
const AnacoObStream = (() => {
  function playlist(text, base) {
    if (!text.trimStart().startsWith('#EXTM3U')) throw new Error(tx('stream_el_recurso_no_es_un_manifiesto_hls_valid'));
    const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const resolve = value => {const u=new URL(value,base);if(!/^https?:$/.test(u.protocol))throw new Error(tx('stream_el_video_contiene_una_direccion_no_compa'));return u.href;};
    if (lines.some(l => l.startsWith('#EXT-X-KEY:') && !/METHOD=NONE(?:,|$)/.test(l))) throw new Error(tx('stream_este_video_usa_segmentos_cifrados_no_se_'));
    if (lines.some(l => l.startsWith('#EXT-X-BYTERANGE:')||l.startsWith('#EXT-X-MAP:')&&/BYTERANGE=/.test(l))) throw new Error(tx('stream_este_video_usa_rangos_de_segmentos_que_t'));
    const variants=[];
    for(let i=0;i<lines.length;i++)if(lines[i].startsWith('#EXT-X-STREAM-INF:')){
      const next=lines[i+1];if(next&&!next.startsWith('#'))variants.push({url:resolve(next),bandwidth:Number(lines[i].match(/(?:^|,)BANDWIDTH=(\d+)/)?.[1]||lines[i].match(/BANDWIDTH=(\d+)/)?.[1]||Infinity)});
    }
    if(variants.length)return {variant:variants.sort((a,b)=>a.bandwidth-b.bandwidth)[0].url};
    if(!lines.includes('#EXT-X-ENDLIST'))throw new Error(tx('stream_el_video_no_expone_una_lista_completa_de'));
    const segments=[];
    let duration=0;
    for(const line of lines){
      if(line.startsWith('#EXTINF:'))duration+=Number(line.slice(8).split(',')[0])||0;
      if(line.startsWith('#EXT-X-MAP:')){
        const match=line.match(/URI="([^"]+)"/);if(match)segments.push(resolve(match[1]));
      }else if(!line.startsWith('#'))segments.push(resolve(line));
    }
    if(!segments.length||segments.length>4000)throw new Error(tx('stream_no_se_ha_encontrado_una_lista_de_segment'));
    return {segments,duration};
  }
  async function download(url, {maxBytes=100000000,maxSeconds=7200,onProgress=()=>{},load} = {}) {
    const parts=[];let size=0;
    async function resource(address, text=false){
      if(load){
        const result=await load(address,text?2000000:maxBytes-size);
        if(result.size>(text?2000000:maxBytes-size))throw new Error(tx('stream_el_video_supera_el_limite_de_100_mb_de_e'));
        if(text)return {text:new TextDecoder().decode(await new Blob(result.parts).arrayBuffer()),url:result.url||address};
        size+=result.size;parts.push(...result.parts);return;
      }
      let response;
      try{response=await fetch(address,{credentials:'include',signal:AbortSignal.timeout(30000)});}
      catch{throw new Error(tx('stream_no_se_pudo_leer_un_recurso_del_video_en_1',[new URL(address).hostname]));}
      if(!response.ok)throw new Error(tx('stream_el_servidor_del_video_rechazo_el_acceso_',[response.status]));
      const reader=response.body.getReader(),chunks=[];let length=0;
      while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;
        if(length>(text?2000000:maxBytes-size)){await reader.cancel();throw new Error(tx('stream_el_video_supera_el_limite_de_100_mb_de_e'));}
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
    if(parsed.variant)throw new Error(tx('stream_el_manifiesto_del_video_contiene_demasia'));
    if(parsed.duration>maxSeconds)throw new Error(tx('stream_el_video_supera_la_duracion_maxima_confi'));
    for(let i=0;i<parsed.segments.length;i++){
      onProgress(i+1,parsed.segments.length);
      await resource(parsed.segments[i]);
    }
    return {parts,size};
  }
  return {playlist,download};
})();
