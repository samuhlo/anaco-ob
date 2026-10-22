const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx=vm.createContext({});vm.runInContext(fs.readFileSync('extension/capture-flow.js','utf8'),ctx);
const flow=ctx.AnacoObCaptureFlow;
const article={kind:'article',contentReady:true,documents:[],videos:[],images:[]};
test('a raw platform video must extract, while an extracted video only prepares its note',()=>{
 const c={...article,kind:'video',videos:[{url:'https://youtube.com/watch?v=abcdefghijk',extractable:true}]};
 assert.deepEqual(Array.from(flow.choices(c)),['video']);assert.equal(flow.select(c),'video');
 assert.deepEqual(Array.from(flow.choices({...c,id:'capture'})),['note']);
});
test('mixed course resources offer explicit alternatives and preserve a still-valid choice',()=>{
 const c={...article,documents:[{url:'https://course.example/book.pdf'}],videos:[{extractable:true}]};
 assert.deepEqual(Array.from(flow.choices(c)),['note','pdf','video']);
 assert.equal(flow.select(c),'note');assert.equal(flow.select(c,'video'),'video');
 assert.equal(flow.select({...c,videos:[]},'video'),'note');
});
test('book pages, local PDFs and unavailable players never expose an invalid action',()=>{
 assert.deepEqual(Array.from(flow.choices({...article,reader:{pages:[1,2]}})),['reader']);
 assert.deepEqual(Array.from(flow.choices({...article,kind:'pdf',documents:[{url:'file:///book.pdf'}]})),[]);
 assert.deepEqual(Array.from(flow.choices({...article,contentReady:false,videos:[{extractable:false}]})),[]);
 assert.deepEqual(Array.from(flow.choices({...article,kind:'quote',videos:[{extractable:true}]})),['note']);
});
