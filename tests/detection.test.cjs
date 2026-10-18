const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({URL});
vm.runInContext(fs.readFileSync('extension/detection.js','utf8')+';globalThis.detect=AnacoObDetection;',ctx);
const detect=ctx.detect;
const page=(url,frameId,other={})=>({url,frameId,kind:'article',title:'Lesson',text:'',images:[],warnings:[],frames:[],documents:[],videos:[],contentReady:false,...other});
const tab={url:'https://course.example/modules/items/123',title:'Course'};

test('web article mode keeps the top article when nested frames also have text',()=>{
 const article=page('https://blog.example/post',0,{text:'A long article about shaders and trails written by the author.',contentReady:true,embeds:[{type:'tweet',url:'https://twitter.com/a/status/1'}]});
 const frame=page('https://widgets.example/post',3,{text:'Text that belongs to an embedded widget, not to the article.',contentReady:true});
 const chosen=detect.merge([article,frame],{url:article.url,title:'Post'},[],{},{preferTop:true});
 assert.equal(chosen.text,article.text);assert.deepEqual(chosen.embeds,article.embeds);
 // Without the option, the established course rule still prefers nested content.
 assert.equal(detect.merge([article,frame],{url:article.url,title:'Post'},[]).text,frame.text);
});

test('nested course content is merged automatically and blocked frames stay separate',()=>{
 const c=detect.merge([page(tab.url,0),page('https://lesson.example/chapter',2,{text:'Useful lesson text',contentReady:true}),page('https://lesson.example/player',4,{videos:[{url:'https://cdn.example/v.mp4',tracks:[],extractable:true}]})],tab,[{url:'https://private.example/embedded'}]);
 assert.equal(c.text,'Useful lesson text');assert.equal(c.videos.length,1);assert.equal(c.frames.length,1);
 assert.equal(c.videos[0].frameId,4);assert.equal(c.videos[0].frameURL,'https://lesson.example/player');
 assert.equal(c.detection.frameDetails[2].videos[0].host,'cdn.example');
 assert.deepEqual(Array.from(c.requiredOrigins),['https://private.example/*']);assert.equal(detect.problem(c),'');
});
test('a frame access error does not replace a readable page with an empty result',()=>{
 const c=detect.merge([page(tab.url,0,{text:'Article body',contentReady:true})],tab,[{url:'https://private.example/embedded'}]);
 assert.equal(c.contentReady,true);assert.equal(c.text,'Article body');assert.equal(detect.problem(c),'');
});
test('empty, login and inaccessible video pages explain why capture is unavailable',()=>{
 for(const [extra,message] of [[{},/No se ha encontrado/],[{detection:{loginPage:true}},/inicio de sesión/],[{videos:[{url:'blob:a',extractable:false,unavailableReason:'Inicia el vídeo'}]},/Inicia el vídeo/],[{requiredOrigins:['https://frame.example/*']},/Autoriza/]]){
  assert.match(detect.problem({contentReady:false,...extra}),message);
 }
});
test('PDF evidence is required, a generic Canvas item URL is not a PDF',()=>{
 assert.equal(detect.pdfURL('https://course.example/modules/items/123'),false);
 assert.equal(detect.pdfURL('https://cdn.example/doc.pdf?token=secret'),true);
 assert.equal(detect.problem({documents:[{url:'https://course.example/files/123/download'}]}),'');
});
test('images retain their actual frame for highlighting',()=>{
 const c=detect.merge([page(tab.url,0),page('https://frame.example',3,{contentReady:true,images:[{url:'https://cdn.example/figure.png'}]})],tab);
 assert.equal(c.images[0].frameId,3);
});

test('an unreadable authorized viewer does not keep asking for the same permission',()=>{
 const c=detect.merge([],tab,[{url:'https://course.example/protected-viewer',needsPermission:false}]);
 assert.equal(c.requiredOrigins.length,0);assert.equal(c.detection.framesUnreadable,1);
 assert.match(detect.problem(c),/visor está cargado/);
});

test('AWS authentication and wrapper text are excluded in favor of loaded reader pages',()=>{
 const aws={url:'https://awsacademy.instructure.com/courses/1/modules/items/2',title:'AWS Academy'};
 const c=detect.merge([
  page(aws.url,0,{frameRole:'wrapper',text:'Course navigation',contentReady:true}),
  page('https://sso.canvaslms.com/redirect',1,{frameRole:'authentication',text:'Authentication service',contentReady:true}),
  page('https://emergingtalent.contentcontroller.com/player',2,{frameRole:'wrapper',contentReady:true,text:'Player navigation'}),
  page('https://emergingtalent.contentcontroller.com/book',3,{parentFrameId:2,contentReady:true,text:'Lesson page',reader:{scope:'loaded'},images:[{url:'https://cdn.example/page.png'}]})
 ],aws,[],{frameReferencesUnmatched:1});
 assert.equal(c.text,'Lesson page');assert.equal(c.requiredOrigins.length,0);assert.equal(c.reader.scope,'detected');
 assert.equal(c.detection.frameDetails.length,4);assert.equal(c.detection.frameReferencesUnmatched,1);
});
test('SSO service text alone cannot be prepared as lesson content',()=>{
 const c=detect.merge([page(tab.url,0,{frameRole:'wrapper',contentReady:false}),page('https://sso.canvaslms.com/',1,{frameRole:'authentication',contentReady:true,text:'Long authentication text'})],tab);
 assert.equal(c.contentReady,false);assert.equal(c.text,'');
});
test('parent and child reader text are not repeated and rendered surfaces are diagnosed',()=>{
 const c=detect.merge([page(tab.url,0,{contentReady:true,text:'Parent'}),page('https://frame.example/book',2,{parentFrameId:0,contentReady:true,text:'Visible page',surfaces:{canvas:1,svg:2,backgrounds:1,blocked:0}})],tab);
 assert.equal(c.text,'Visible page');assert.equal(c.detection.surfaces.svg,2);
});

test('a page Anaco cannot read says so instead of pointing to a viewer',()=>{
 const c=detect.merge([],{url:'https://tympanus.net/codrops/a',title:'Artículo'},[{url:'https://tympanus.net/codrops/a',title:'Página actual',needsPermission:true,top:true}]);
 const message=detect.problem(c);
 assert.match(message,/permiso para leer esta página/);assert.match(message,/tympanus\.net/);assert.doesNotMatch(message,/visor/);
 // A blocked embedded viewer keeps the viewer explanation.
 const nested=detect.merge([page('https://course.example/lesson',0)],{url:'https://course.example/lesson',title:'Curso'},[{url:'https://player.example/v',needsPermission:true}]);
 assert.match(detect.problem(nested),/visor/);
});
