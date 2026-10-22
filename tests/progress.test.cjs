const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
function progress(lang='es'){
 const context=vm.createContext({AnacoObLang:lang});
 for(const file of ['i18n-catalog','i18n','progress'])vm.runInContext(fs.readFileSync(`extension/${file}.js`,'utf8'),context);
 return context.AnacoObProgress.measure;
}
test('the second of seven stretches has one completed, and finishing reading reaches 100%',()=>{
 const measure=progress(),reading={stage:'reading',unit:'stretches',completed:1,total:7};
 assert.equal(measure(reading).percent,14);
 assert.match(measure(reading).detail,/1 de 7.*14% de esta fase/);
 assert.equal(measure({...reading,completed:2}).percent,28);
 assert.equal(measure({...reading,completed:7}).percent,100);
 assert.equal(measure({stage:'synthesis'}),null);
 // Counts from a previous phase must not turn synthesis/cancellation into 100%.
 assert.equal(measure({...reading,stage:'synthesis'}),null);
 assert.equal(measure({...reading,stage:'cancel'}),null);
});
test('audio progress is bounded and can complete instead of stopping at 99%',()=>{
 const measure=progress(),audio={stage:'transcribe',processed_seconds:300,total_seconds:1200};
 assert.match(measure(audio).detail,/5:00 de 20:00.*25/);
 assert.equal(measure({...audio,processed_seconds:1200}).percent,100);
 assert.equal(measure({...audio,processed_seconds:1300}).fraction,1);
 for(const extra of [{total_seconds:0},{total_seconds:Infinity},{processed_seconds:NaN},{processed_seconds:-1}])assert.equal(measure({...audio,...extra}),null);
});
test('pages, downloads and resources report their own units in both languages',()=>{
 for(const [stage,unit] of [['capture','pages'],['reading','pages'],['download','segments'],['resources','resources'],['frames','frames']]){
  assert.equal(progress()({stage,unit,completed:2,total:8}).percent,25);
  assert.match(progress('en')({stage,unit,completed:2,total:8}).detail,/2 of 8.*25% of this phase/);
 }
 for(const p of [{stage:'model'},{stage:'download'},{stage:'reading',unit:'stretches',completed:0,total:0}])assert.equal(progress()(p),null);
});
