/* Isolated content-script helper. Leaves page styles and layout untouched. */
if (!globalThis.AnacoObLocateImage) {
  let overlay, target, label;
  function clear() {
    overlay?.remove();overlay=null;target=null;
    window.removeEventListener("scroll",position,true);
    window.removeEventListener("resize",position);
  }
  function position() {
    if(!overlay||!target?.isConnected){clear();return;}
    const r=target.getBoundingClientRect();
    Object.assign(overlay.style,{left:(r.left-5)+"px",top:(r.top-5)+"px",width:(r.width+10)+"px",height:(r.height+10)+"px"});
  }
  globalThis.AnacoObLocateImage = function(input) {
    clear();
    if(input.clear)return {found:false};
    target=[...document.querySelectorAll("[data-anaco-ob-image]")].find(img=>img.dataset.anacoObImage===input.imageId)
      ||[...document.images].find(img=>(img.currentSrc||img.src)===input.url);
    if(!target)return {found:false};
    // Immediate placement avoids queued animations when scanning several images.
    target.scrollIntoView({behavior:"instant",block:"center",inline:"nearest"});
    overlay=document.createElement("div");overlay.id="anaco-ob-image-highlight";
    overlay.setAttribute("aria-hidden","true");
    Object.assign(overlay.style,{position:"fixed",pointerEvents:"none",zIndex:"2147483647",border:"4px solid #ffca40",borderRadius:"8px",boxShadow:"0 0 0 5px #1c1b2055",boxSizing:"border-box"});
    label=document.createElement("span");label.textContent="Imagen "+(input.index+1);
    Object.assign(label.style,{position:"absolute",left:"-4px",top:"-29px",background:"#ffca40",color:"#1c1b20",padding:"3px 9px",borderRadius:"5px 5px 0 0",font:"600 12px/20px system-ui,sans-serif"});
    overlay.append(label);document.documentElement.append(overlay);
    window.addEventListener("scroll",position,true);window.addEventListener("resize",position);position();
    return {found:true};
  };
}
void 0;
