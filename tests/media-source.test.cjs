const I18N = require('./i18n.cjs');
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx=vm.createContext({URL});vm.runInContext(I18N+fs.readFileSync('extension/media-source.js','utf8'),ctx);const media=ctx.AnacoObMedia;
test('legacy embedded YouTube players become canonical video pages',()=>{
 for(const url of ['https://youtube.googleapis.com/v/abcdefghijk?version=3','https://www.youtube-nocookie.com/embed/abcdefghijk','https://youtu.be/abcdefghijk','https://m.youtube.com/watch?v=abcdefghijk'])assert.equal(media.platformURL(url),'https://www.youtube.com/watch?v=abcdefghijk');
 assert.equal(media.label({url:'https://youtube.googleapis.com/v/abcdefghijk',title:'youtube.googleapis.com'}),'YouTube · Vídeo 1');
});
test('API requests and URLs merely mentioning a platform are not playable platform pages',()=>{
 for(const url of ['https://youtube.googleapis.com/youtube/v3/videos?id=abcdefghijk','https://www.youtube.com/youtubei/v1/player','https://example.org/youtube.mp4','https://cdn.example/video.mp4?ref=https://youtube.com/watch?v=abcdefghijk'])assert.equal(media.platformURL(url),null);
 assert.equal(media.apiURL('https://youtube.googleapis.com/youtube/v3/videos'),true);
 assert.equal(media.apiURL('https://youtube.googleapis.com/v/abcdefghijk'),false);
});

test('Drive identity is independent of view/preview and keeps required sharing parameters',()=>{
 const a=media.driveFile('https://drive.google.com/file/d/lesson_123/preview?usp=sharing&resourcekey=key&authuser=1');
 const b=media.driveFile('https://drive.google.com/file/d/lesson_123/view?resourcekey=key&authuser=1');
 assert.deepEqual(a,b);assert.equal(a.id,'lesson_123');
 assert.equal(new URL(a.download).searchParams.get('resourcekey'),'key');
 assert.equal(new URL(a.download).searchParams.get('authuser'),'1');
 assert.equal(media.driveFile('https://example.test/file/d/lesson_123/view'),null);
});
