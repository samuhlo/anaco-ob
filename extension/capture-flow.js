/* Select a single preparation path without losing access to other page resources. */
globalThis.AnacoObCaptureFlow=(()=>{
  function choices(c){
    if(!c)return [];
    if(c.id)return ['note'];
    const types=[];
    if(!c.reader&&!['pdf','video'].includes(c.kind)&&(c.contentReady??(c.text?.trim().length>=100||['quote','image'].includes(c.kind))))types.push('note');
    if(types.length&&['quote','image'].includes(c.kind))return types;
    if(c.reader&&c.kind!=='pdf')types.push('reader');
    if(c.documents?.some(d=>!d.url.startsWith('file:')))types.push('pdf');
    if(c.videos?.some(v=>v.extractable!==false))types.push('video');
    return types;
  }
  function select(c,previous){
    const types=choices(c);
    if(types.includes(previous))return previous;
    if(c?.kind==='video'&&types.includes('video'))return 'video';
    if(c?.kind==='pdf'&&types.includes('pdf'))return 'pdf';
    return types[0]||'';
  }
  return {choices,select};
})();
