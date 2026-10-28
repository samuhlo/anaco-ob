/* Shared validation and resource selection for the background queue and its UI. */
globalThis.AnacoObBatchPlan=(()=>{
  function urls(text){
    const values=String(text||'').split(/\s+/).filter(Boolean);
    if(!values.length||values.length>100)throw new Error(tx('batch_url_limit'));
    return [...new Set(values.map(value=>{
      let url;try{url=new URL(value);}catch{throw new Error(tx('batch_invalid_url',[value]));}
      if(!/^https?:$/.test(url.protocol)||url.username||url.password)throw new Error(tx('batch_invalid_url',[value]));
      return url.href;
    }))];
  }
  function plan(c,mode='auto'){
    const choices=AnacoObCaptureFlow.choices(c);
    const unavailable=()=>{const error=new Error(tx('batch_no_content'));error.code='not-ready';throw error;};
    const documents=(c.documents||[]).filter(d=>!d.url.startsWith('file:')&&d.scope!=='navigation');
    let kind=mode;
    if(mode==='auto'){
      if(c.kind==='pdf')kind='pdf';
      else if(c.reader)kind='reader';
      else if(c.videos?.length||c.kind==='video')kind='video';
      // A Moodle URL page is a launcher, never its site-wide student handbook.
      else if(c.linkLauncher&&!documents.some(d=>d.embedded))unavailable();
      else if(documents.length)kind='pdf';
      else if(c.frames?.length||c.detection?.frameReferencesUnmatched)unavailable();
      else kind='note';
    }
    if(!choices.includes(kind))unavailable();
    if(kind==='reader'||kind==='note')return {kind};
    if(kind==='pdf'){
      if(!documents.length)unavailable();
      if(documents.length!==1)throw new Error(tx('batch_ambiguous'));
      const doc=documents[0];
      return {kind:'resource',request:{kind:'pdf',url:doc.url,name:(doc.title||c.title||'documento').replace(/\.pdf$/i,'')+'.pdf',frameId:doc.frameId,frameURL:doc.frameURL,pageUrl:c.url}};
    }
    const videos=[...new Map(c.videos.filter(v=>v.extractable!==false).map(v=>[AnacoObMedia.driveFile(v.url)?.id||v.url,v])).values()];
    if(!videos.length)unavailable();
    if(videos.length!==1)throw new Error(tx('batch_ambiguous'));
    const video=videos[0],platform=AnacoObMedia.platformURL(video.url);
    const track=[...(video.tracks||[])].sort((a,b)=>(!a.language?.startsWith('es'))-(!b.language?.startsWith('es')))[0];
    const direct=video.download||(/^https?:/.test(video.url)&&!platform&&!AnacoObMedia.apiURL(video.url)&&video.url!==c.url?video.url:null);
    const audio=direct&&!/\.mpd(?:[?#]|$)/i.test(direct)?{kind:/\.m3u8(?:[?#]|$)/i.test(direct)?'video-hls':'video',url:direct,name:(video.title||c.title||'video').replace(/[\\/:*?"<>|]/g,' ').slice(0,160)+'.mp4'}:platform?{kind:'video-platform',url:platform}:null;
    const request=platform?audio:video.subtitles?{kind:'subtitles',text:video.subtitles,fallback:audio}:track?{kind:'subtitle-url',url:track.url,fallback:audio}:audio;
    if(!request)unavailable();
    return {kind:'resource',request:{...request,frameId:video.frameId,frameURL:video.frameURL,title:video.title||c.title,pageUrl:c.url}};
  }
  function permissionOrigins(urls){
    const origins=new Set();
    for(const value of urls||[]){
      try{const u=new URL(value);if(!/^https?:$/.test(u.protocol)||AnacoObMedia.auxiliaryFrame(value))continue;
        origins.add(u.protocol+'//'+u.hostname+'/*');
        // Drive downloads redirect to these hosts, as in the individual video flow.
        if(u.hostname==='drive.google.com'){origins.add('https://drive.usercontent.google.com/*');origins.add('https://*.googleusercontent.com/*');}
      }catch{}
    }
    return [...origins];
  }
  return {urls,plan,permissionOrigins};
})();
