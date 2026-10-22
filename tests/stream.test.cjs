const I18N = require('./i18n.cjs');
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx=vm.createContext({URL,TextDecoder,Blob,AbortSignal});
vm.runInContext(I18N+fs.readFileSync('extension/stream.js','utf8')+';globalThis.stream=AnacoObStream;',ctx);
const stream=ctx.stream;

test('HLS resolves master variants, relative segments and initialization data',()=>{
 assert.equal(stream.playlist('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2000000\nhigh.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=300000\nlow.m3u8','https://media.example/master.m3u8').variant,'https://media.example/low.m3u8');
 const parsed=stream.playlist('#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n#EXTINF:4.5,\na.m4s\n#EXTINF:3,\nb.m4s\n#EXT-X-ENDLIST','https://media.example/path/v.m3u8');
 assert.equal(parsed.duration,7.5);assert.deepEqual(Array.from(parsed.segments),['https://media.example/path/init.mp4','https://media.example/path/a.m4s','https://media.example/path/b.m4s']);
});
test('login responses, encrypted, live and ranged manifests fail explicitly',()=>{
 for(const [text,pattern] of [['<html>login</html>',/acceso/],['#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXT-X-ENDLIST',/cifrados/],['#EXTM3U\n#EXTINF:4,\na.ts',/directos/],['#EXTM3U\n#EXT-X-BYTERANGE:10\na.ts\n#EXT-X-ENDLIST',/rangos/]])assert.throws(()=>stream.playlist(text,'https://media.example/master.m3u8'),pattern);
});
test('HLS downloads using browser credentials and enforces duration and size',async()=>{
 const calls=[];
 ctx.fetch=async(url,options)=>{calls.push({url,options});return new Response(url.endsWith('.m3u8')?'#EXTM3U\n#EXTINF:4,\na.ts\n#EXT-X-ENDLIST':new Uint8Array([1,2,3]));};
 const result=await stream.download('https://media.example/m.m3u8');
 assert.equal(result.size,3);assert.ok(calls.every(c=>c.options.credentials==='include'));
 await assert.rejects(stream.download('https://media.example/m.m3u8',{maxSeconds:2}),/duración/);
 await assert.rejects(stream.download('https://media.example/m.m3u8',{maxBytes:2}),/100 MB/);
});
test('HLS uses the same selected transport for manifests and segments with remaining limits',async()=>{
 const calls=[];const load=async(url,limit)=>{calls.push([url,limit]);const bytes=new TextEncoder().encode(url.endsWith('.m3u8')?'#EXTM3U\n#EXTINF:2,\na.ts\n#EXTINF:2,\nb.ts\n#EXT-X-ENDLIST':'abc');return {parts:[bytes],size:bytes.length,url};};
 const result=await stream.download('https://player.example/video.m3u8',{maxBytes:5,load:async(url,limit)=>{
  const r=await load(url,limit);if(!url.endsWith('.m3u8')){r.parts=[new Uint8Array(2)];r.size=2;}return r;
 }});
 assert.equal(result.size,4);assert.deepEqual(calls.map(c=>c[1]),[2000000,5,3]);
 await assert.rejects(stream.download('https://player.example/video.m3u8',{maxBytes:4,load}),/100 MB/);
});

test('HLS counts only downloaded segments and a failed segment never completes the phase',async()=>{
 const updates=[];
 const load=async url=>{
  if(url.endsWith('.m3u8')){const bytes=new TextEncoder().encode('#EXTM3U\n#EXTINF:2,\na.ts\n#EXTINF:2,\nb.ts\n#EXT-X-ENDLIST');return {parts:[bytes],size:bytes.length};}
  assert.equal(updates.at(-1)[0],url.endsWith('a.ts')?0:1);
  if(url.endsWith('b.ts'))throw new Error('interrupted');
  return {parts:[new Uint8Array(2)],size:2};
 };
 await assert.rejects(stream.download('https://player.example/video.m3u8',{load,onProgress:async(done,total)=>{await Promise.resolve();updates.push([done,total]);}}),/interrupted/);
 assert.deepEqual(updates,[[0,2],[1,2]]);
});
