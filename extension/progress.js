/* Fractions measure the current phase, never elapsed time or the whole job. */
globalThis.AnacoObProgress=(()=>{
  function measure(p={}){
    const audio=p.stage==='transcribe';
    const total=audio?p.total_seconds:p.total,completed=audio?p.processed_seconds:p.completed;
    const units={stretches:v=>tx('progress_stretches',v),pages:v=>tx('progress_pages',v),segments:v=>tx('progress_segments',v),resources:v=>tx('progress_resources',v),frames:v=>tx('progress_frames',v)};
    if(!Number.isFinite(total)||total<=0||!Number.isFinite(completed)||completed<0)return null;
    if(!audio&&(!units[p.unit]||!['reading','capture','resources','download','frames','pdf-text','pdf-images'].includes(p.stage)||!Number.isInteger(total)||!Number.isInteger(completed)))return null;
    const done=Math.min(total,completed),fraction=done/total,percent=Math.floor(fraction*100);
    const time=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');
    return {fraction,percent,detail:audio?tx('panel_1_de_2_de_audio_3',[time(done),time(total),percent]):units[p.unit]([done,total,percent])};
  }
  return {measure};
})();
