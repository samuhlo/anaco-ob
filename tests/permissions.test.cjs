const I18N = require('./i18n.cjs');
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function panel() {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {hidden:true,value:'',textContent:'',addEventListener(){},replaceChildren(){},append(){}});
    return elements.get(id);
  };
  let activation = false, granted = true, requests = [], messages = [];
  const browser = {
    permissions: {
      // A preflight check must never precede request. It consumes activation.
      contains: async () => {activation=false;return false;},
      request(args) {
        assert.equal(activation,true,'permissions.request must run before the click handler yields');
        requests.push(args);
        return Promise.resolve(granted);
      }
    },
    runtime: {sendMessage:async message=>{messages.push(message);if(message.type==='native')return {config:{provider:'manual'},pending:[],folders:[]};return {};},openOptionsPage(){}},
    storage: {local:{get:async()=>({}),set:async()=>{}},onChanged:{addListener(){}}}
  };
  const selected = [];
  const context = vm.createContext({browser,URL,console,setTimeout,clearTimeout,localStorage:{getItem(){return null;}},document:{getElementById:element,querySelectorAll:selector=>selector==='#images input:checked'?selected:[]}});
  vm.runInContext(I18N+fs.readFileSync('extension/media-source.js','utf8')+fs.readFileSync('extension/diagnosis.js','utf8')+fs.readFileSync('extension/panel.js','utf8'),context);
  return {
    async click(capture,indices=[0],allow=true,button='prepare') {
      // Let initialization finish before setting a capture, like opening a panel.
      await new Promise(resolve=>setImmediate(resolve));
      context.captureFixture=capture;
      vm.runInContext('state={currentCapture:captureFixture};',context);
      selected.splice(0,selected.length,...indices.map(value=>({value:String(value)})));
      element('provider').value='manual';element('intent').value='Guardar para estudiar';
      granted=allow;activation=true;
      const pending=element(button).onclick();
      activation=false;
      await pending;
      return {requests,messages,error:element('error')};
    }
  };
}

test('new image host requests permission directly within the original click',async()=>{
  const result=await panel().click({images:[{url:'https://tympanus.net/codrops/uploads/noho.jpg'}]});
  assert.equal(result.requests.length,1);
  assert.deepEqual(Array.from(result.requests[0].origins),['https://tympanus.net/*']);
  assert.ok(result.messages.some(m=>m.type==='prepare'));
  assert.equal(result.error.hidden,true);
});
test('permission rejection preserves the capture and does not start preparation',async()=>{
  const result=await panel().click({images:[{url:'https://images.example.org/test.png'}]},[0],false);
  assert.equal(result.requests.length,1);
  assert.ok(!result.messages.some(m=>m.type==='prepare'));
  assert.match(result.error.textContent,/No se ha concedido/);
});
test('text-only and already staged captures do not request image permissions',async()=>{
  for(const [capture,indices] of [[{images:[]},[]],[{id:'staged',images:[{url:'https://example.org/a.png'}]},[0]]]){
    const result=await panel().click(capture,indices);
    assert.equal(result.requests.length,0);
    assert.ok(result.messages.some(m=>m.type==='prepare'));
  }
});
test('request is limited to distinct selected hosts, with no port in match patterns',async()=>{
  const result=await panel().click({images:[{url:'https://img.example.org:443/a.png'},{url:'https://img.example.org/b.png'},{url:'https://unselected.example.org/c.png'}]},[0,1]);
  assert.deepEqual(Array.from(result.requests[0].origins),['https://img.example.org/*']);
});
test('PDF extraction requests its selected host before yielding',async()=>{
  const result=await panel().click({title:'Curso',url:'https://course.example.org/',images:[],documents:[{url:'https://files.example.org/lesson.pdf',title:'Lección'}]},[],true,'extractPdf');
  assert.deepEqual(Array.from(result.requests[0].origins),['https://files.example.org/*']);
  assert.ok(result.messages.some(m=>m.type==='importResource'&&m.kind==='pdf'));
});
test('iframe exploration requests permission in the originating click',async()=>{
  const result=await panel().click({images:[],requiredOrigins:['https://player.example.org/*']},[],true,'authorizeDetection');
  assert.deepEqual(Array.from(result.requests[0].origins),['https://player.example.org/*']);
  assert.ok(result.messages.some(m=>m.type==='inspectFrame'));
});
test('video subtitles request the subtitle host directly from the click',async()=>{
  const result=await panel().click({title:'Lección',url:'https://course.example.org/',images:[],videos:[{url:'https://media.example.org/video.mp4',frameId:42,frameURL:'https://player.example.org/lesson',tracks:[{url:'https://captions.example.org/sub.vtt',language:'es'}]}]},[],true,'extractVideo');
  assert.deepEqual(Array.from(result.requests[0].origins),['https://captions.example.org/*','https://media.example.org/*']);
  assert.ok(result.messages.some(m=>m.type==='importResource'&&m.kind==='subtitle-url'));
  const request=result.messages.find(m=>m.type==='importResource');assert.equal(request.frameId,42);assert.equal(request.frameURL,'https://player.example.org/lesson');
});
test('direct and HLS video requests retain the actual player frame',async()=>{
  for(const suffix of ['mp4','m3u8']){
    const result=await panel().click({url:'https://course.example.org/',images:[],videos:[{url:'https://media.example.org/video.'+suffix,frameId:99,frameURL:'https://player.example.org/lesson',tracks:[]}]},[],true,'extractVideo');
    const request=result.messages.find(m=>m.type==='importResource');assert.equal(request.frameId,99);assert.equal(request.frameURL,'https://player.example.org/lesson');
    assert.equal(request.kind,suffix==='mp4'?'video':'video-hls');
  }
});
