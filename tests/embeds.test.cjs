const I18N = require('./i18n.cjs');
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({URL,TextEncoder,TextDecoder});
vm.runInContext(I18N+fs.readFileSync('extension/embeds.js','utf8')+';globalThis.embeds=AnacoObEmbeds;',ctx);
const embeds=ctx.embeds;

test('only known post and code demo frames are treated as embeds',()=>{
  for(const url of ['https://platform.twitter.com/embed/Tweet.html?id=1803039502136426656','https://codepen.io/ksenia-k/embed/rNXPZRN?default-tab=result','https://cdpn.io/ksenia-k/fullembedgrid/rNXPZRN?type=embed','https://syndication.twitter.com/settings'])
    assert.equal(embeds.embedFrame(url),true,url);
  // Course players, providers and video platforms keep their current detection.
  for(const url of ['https://emergingtalent.contentcontroller.com/ScormEngineInterface/player.html','https://awsacademy.instructure.com/courses/1/modules/items/2','https://aulavirtual.xunta.gal/mod/scorm/player.php','https://www.youtube.com/embed/NnTvZWp5Q7o','https://player.vimeo.com/video/123','https://evil.example/codepen.io/embed','https://notcodepen.io/a/embed/b','about:blank',''])
    assert.equal(embeds.embedFrame(url),false,url);
});

test('tweet links become canonical status URLs that Obsidian can embed',()=>{
  assert.equal(embeds.tweetURL('https://x.com/uuuuuulala/status/1803039502136426656?ref_src=twsrc%5Etfw'),'https://twitter.com/uuuuuulala/status/1803039502136426656');
  assert.equal(embeds.tweetURL('https://platform.twitter.com/embed/Tweet.html?dnt=true&id=1892286294107013506'),'https://twitter.com/i/status/1892286294107013506');
  assert.equal(embeds.tweetURL('https://example.org/status/1'),null);
});

test('pen identity comes from embed, pen and result URLs',()=>{
  const pen=embeds.penFromURL('https://codepen.io/ksenia-k/embed/rNXPZRN?theme-id=light&default-tab=result');
  assert.equal(pen.user,'ksenia-k');assert.equal(pen.slug,'rNXPZRN');
  assert.equal(pen.url,'https://codepen.io/ksenia-k/pen/rNXPZRN');
  assert.equal(embeds.penFromURL('https://codepen.io/ksenia-k/pen/rNXPZRN').slug,'rNXPZRN');
  assert.equal(embeds.penFromURL('https://codepen.io/trending'),null);
});

test('silent looping article clips are separated from videos to transcribe',()=>{
  const clip={src:'https://tympanus.net/codrops/wp-content/uploads/2026/10/globe1-optimized.mp4',muted:true,loop:true,autoplay:true,controls:false,duration:4.9};
  assert.equal(embeds.isClip(clip),true);
  // A course lesson has controls or sound; a player stream is not a downloadable clip.
  assert.equal(embeds.isClip({...clip,controls:true}),false);
  assert.equal(embeds.isClip({...clip,muted:false}),false);
  assert.equal(embeds.isClip({...clip,loop:false}),false);
  assert.equal(embeds.isClip({...clip,duration:600}),false);
  assert.equal(embeds.isClip({...clip,src:'blob:https://tympanus.net/123'}),false);
  assert.equal(embeds.isClip({...clip,src:'https://cdn.example/master.m3u8'}),false);
  assert.equal(embeds.isClip({...clip,duration:NaN}),true);
});

test('clip weight above the limit or unknown is flagged before selection',()=>{
  assert.equal(embeds.clipWarning(5_633_358),'');
  assert.match(embeds.clipWarning(25_000_000),/25 MB/);
  assert.match(embeds.clipWarning(null),/desconocido/);
});

test('an offline demo copies its module graph and rewrites every import to local files',async()=>{
  const sources={
    'https://unpkg.com/gsap@3/dist/gsap.min.js':'window.gsap={from("a"){}};',
    'https://unpkg.com/three@0.170.0/build/three.module.js':'export * from "./three.core.js";\nexport const REVISION="170";',
    'https://unpkg.com/three@0.170.0/build/three.core.js':'import { REVISION } from "./three.module.js";export const core=1;',
    'https://unpkg.com/three@0.170.0/examples/jsm/controls/OrbitControls.js':'import { core } from "three";export class OrbitControls{}',
    'https://cdn.example/style.css':'body{margin:0}',
  };
  const loads=[];
  const load=async url=>{loads.push(url);if(!(url in sources))throw new Error('404');return new TextEncoder().encode(sources[url]);};
  const page=`<html><head><link rel="stylesheet" href="https://cdn.example/style.css"><script src='https://unpkg.com/gsap@3/dist/gsap.min.js'></script><script src="https://cpwebassets.codepen.io/assets/common/stopExecutionOnTimeout.js"></script>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.170.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.170.0/examples/jsm/"}}</script></head>
<body><script type="module">import * as THREE from "three";import { OrbitControls } from "three/addons/controls/OrbitControls.js";import x from "https://missing.example/x.js";</script></body></html>`;
  const result=await embeds.vendor(page,'https://cdpn.io/u/fullembedgrid/abc',load);
  const files=Object.fromEntries(result.files.map(f=>[f.url,f]));
  assert.equal(Object.keys(files).length,5);
  for(const f of result.files)assert.match(f.name,/^[a-f0-9]{8}-[A-Za-z0-9._@-]+\.(js|css)$/);
  const text=url=>new TextDecoder().decode(files[url].bytes);
  const name=url=>files[url].name;
  assert.ok(result.page.includes(`"./${name('https://unpkg.com/three@0.170.0/build/three.module.js')}"`));
  assert.ok(result.page.includes(`"./${name('https://unpkg.com/three@0.170.0/examples/jsm/controls/OrbitControls.js')}"`));
  assert.ok(result.page.includes(`'./${name('https://unpkg.com/gsap@3/dist/gsap.min.js')}'`));
  assert.ok(result.page.includes(`"./${name('https://cdn.example/style.css')}"`));
  // Relative imports, cycles and bare specifiers inside fetched modules are local too.
  assert.ok(text('https://unpkg.com/three@0.170.0/build/three.module.js').includes(`"./${name('https://unpkg.com/three@0.170.0/build/three.core.js')}"`));
  assert.ok(text('https://unpkg.com/three@0.170.0/build/three.core.js').includes(`"./${name('https://unpkg.com/three@0.170.0/build/three.module.js')}"`));
  assert.ok(text('https://unpkg.com/three@0.170.0/examples/jsm/controls/OrbitControls.js').includes(`"./${name('https://unpkg.com/three@0.170.0/build/three.module.js')}"`));
  assert.equal(text('https://unpkg.com/gsap@3/dist/gsap.min.js'),sources['https://unpkg.com/gsap@3/dist/gsap.min.js']);
  assert.deepEqual([...result.missing],['https://missing.example/x.js']);
  assert.ok(!loads.some(u=>/codepen/.test(u)));
  assert.equal(loads.filter(u=>u.endsWith('three.module.js')).length,1);
});
