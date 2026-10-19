/* Identify playable platform pages, never arbitrary URLs mentioning YouTube. */
globalThis.AnacoObMedia=(()=>{
  function platformURL(value){
    try{
      const u=new URL(value),host=u.hostname.toLowerCase().replace(/^www\./,'');let id;
      if(host==='youtu.be')id=u.pathname.split('/')[1];
      else if(['youtube.com','m.youtube.com','music.youtube.com','youtube-nocookie.com','youtube.googleapis.com'].includes(host)){
        id=u.pathname==='/watch'?u.searchParams.get('v'):u.pathname.match(/^\/(?:embed|v|shorts|live)\/([^/]+)/)?.[1];
      }
      if(id&&/^[a-zA-Z0-9_-]{11}$/.test(id))return 'https://www.youtube.com/watch?v='+id;
      if((host==='vimeo.com'||host==='player.vimeo.com')&&/\/(?:video\/)?\d+(?:\/|$)/.test(u.pathname))return u.href;
    }catch{}
    return null;
  }
  function apiURL(value){try{const u=new URL(value);return (u.hostname==='youtube.googleapis.com'||/(^|\.)googleapis\.com$/.test(u.hostname)&&/youtube/i.test(u.pathname)||/(^|\.)youtube\.com$/.test(u.hostname)&&/^\/youtubei\//.test(u.pathname))&&!platformURL(value);}catch{return false;}}
  function label(video,index=0){
    const url=platformURL(video.url),origin=url?.includes('youtube.com')?'YouTube':url?.includes('vimeo.com')?'Vimeo':null;
    let title=(video.title||'').trim();
    if(!title||/^https?:\/\//.test(title)||/^[\w.-]+\.(?:com|net|org)(?:\/.*)?$/.test(title))title=tx('media_video_1',[index+1]);
    return (origin?origin+' · ':'')+title;
  }
  return {platformURL,apiURL,label};
})();
