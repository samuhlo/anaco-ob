const I18N = require('./i18n.cjs');
const {test}=require('node:test'),assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');

// Exercise the capture entry point with player internals and reader candidates.
async function capture({url='https://www.youtube.com/watch?v=abcdefghijk',book=false,media=true,article=false,frames=[]}={}){
  const calls={inventory:0,collect:0};
  const player={currentSrc:'blob:https://www.youtube.com/internal',src:'',title:'',textTracks:[],duration:120,
    closest:()=>null,querySelector:()=>null,querySelectorAll:()=>[]};
  const players=media?[{...player,currentSrc:''},player,{...player,currentSrc:'blob:https://www.youtube.com/ad'}]:[];
  const clone={nodeType:1,tagName:'MAIN',dataset:{},childNodes:[{nodeType:3,textContent:'Video description, comments and recommendations. '.repeat(30)}],querySelectorAll:()=>[]};
  const root={querySelector:selector=>selector==='canvas'?{}:selector==='video,audio'&&media?player:null,
    querySelectorAll:()=>[],cloneNode:()=>clone,matches:()=>false};
  const document={body:root,title:'Video title',contentType:'text/html',
    querySelector:selector=>selector.startsWith('.pdfViewer,')?(book?root:null):selector==='article'?(article?root:null):selector==='main,[role=main]'?root:null,
    querySelectorAll:selector=>selector==='video,audio'?players:selector==='embed,object,iframe'?frames:[],images:[]};
  const context=vm.createContext({URL,document,location:new URL(url),
    window:{getSelection:()=>null},crypto:{randomUUID:()=> 'id'},Node:{ELEMENT_NODE:1,TEXT_NODE:3},
    performance:{getEntriesByType:()=>[]},AnacoObMediaWatcher:true,
    AnacoObEmbeds:{collect:()=>[]},AnacoObSurfaces:{visible:()=>true,
      inventory:()=>{calls.inventory++;return {pages:[{id:'a',type:'canvas'},{id:'b',type:'canvas'}],overflow:false};},
      collect:async()=>{calls.collect++;return {images:[],canvas:2,svg:0,backgrounds:0,blocked:0};}}});
  for(const file of ['media-source','capture'])vm.runInContext((file==='media-source'?I18N:'')+fs.readFileSync(`extension/${file}.js`,'utf8'),context);
  return {result:await context.AnacoObCapture({embeds:true}),calls};
}

test('YouTube ambient canvases are not a book and internal players collapse to the page URL',async()=>{
  const {result,calls}=await capture();
  assert.equal(result.reader,null);
  assert.equal(result.kind,'video');assert.equal(result.contentReady,false);
  assert.equal(result.text,'');assert.equal(result.images.length,0);
  assert.equal(calls.inventory,0);assert.equal(calls.collect,0);
  assert.equal(result.videos.length,1);
  assert.equal(result.videos[0].url,'https://www.youtube.com/watch?v=abcdefghijk');
  assert.equal(result.videos[0].extractable,true);
  assert.deepEqual(Array.from(result.warnings).filter(w=>/Libro detectado|Inicia el vídeo/.test(w)),[]);
});

test('shorts, live and embedded YouTube pages use the same platform extraction',async()=>{
  for(const path of ['/shorts/abcdefghijk','/live/abcdefghijk','/embed/abcdefghijk']){
    const {result}=await capture({url:'https://www.youtube.com'+path,media:false});
    assert.equal(result.reader,null);assert.equal(result.videos.length,1);
    assert.equal(result.videos[0].url,'https://www.youtube.com/watch?v=abcdefghijk');
    assert.equal(result.videos[0].extractable,true);
  }
});

test('a course player with canvases is not inferred to be a book',async()=>{
  const {result}=await capture({url:'https://course.example/lesson'});
  assert.equal(result.reader,null);
  assert.equal(result.kind,'article');assert.equal(result.contentReady,true);
});

test('explicit books still work with embedded video, and canvas-only readers remain supported',async()=>{
  for(const options of [{book:true,media:true},{book:false,media:false}]){
    const {result,calls}=await capture({url:'https://course.example/book',...options});
    assert.equal(result.reader.pages.length,2);assert.equal(calls.inventory,1);
    assert.match(result.warnings[0],/Libro detectado/);
  }
});

test('Drive view and preview identify one file and retain its resource key',async()=>{
 const frame={tagName:'IFRAME',src:'https://drive.google.com/file/d/lesson_id/preview',title:'Embedded video',getAttribute:()=>null};
 const {result}=await capture({url:'https://drive.google.com/file/d/lesson_id/view?resourcekey=required-key',article:true,media:false,frames:[frame]});
 assert.equal(result.videos.length,1);assert.equal(result.videos[0].title,'Video title');
 const download=new URL(result.videos[0].download);assert.equal(download.searchParams.get('id'),'lesson_id');assert.equal(download.searchParams.get('resourcekey'),'required-key');
});
