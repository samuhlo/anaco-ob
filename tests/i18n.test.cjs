const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('extension/i18n-catalog.js','utf8')+fs.readFileSync('extension/i18n.js','utf8');
function load(context){const ctx=vm.createContext(context);vm.runInContext(source,ctx);return ctx.AnacoObI18n;}

test('Spanish is the default and the fallback; English follows an English browser',()=>{
  assert.equal(load({}).tx('options_idioma'),'Idioma');
  assert.equal(load({navigator:{language:'fr-FR'}}).language(),'es');
  const english=load({browser:{i18n:{getUILanguage:()=>'en-GB'}}});
  assert.equal(english.language(),'en');
  assert.equal(english.tx('options_idioma'),'Language');
  assert.equal(english.tx('no_existe'),'no_existe');
});

test('the chosen language wins over the browser and fills placeholders',()=>{
  const i18n=load({AnacoObLang:'en',browser:{i18n:{getUILanguage:()=>'es-ES'}}});
  assert.equal(i18n.tx('panel_1_8_elegidas_2_disponibles',[3,12]),'3 / 8 chosen · 12 available');
  assert.equal(load({AnacoObLang:'es'}).tx('panel_1_8_elegidas_2_disponibles',[3,12]),'3 / 8 elegidas · 12 disponibles');
});

test('both catalogs have the same keys and placeholders',()=>{
  const es=JSON.parse(fs.readFileSync('extension/_locales/es/messages.json','utf8'));
  const en=JSON.parse(fs.readFileSync('extension/_locales/en/messages.json','utf8'));
  assert.deepEqual(Object.keys(en).sort(),Object.keys(es).sort());
  for(const key of Object.keys(es))assert.deepEqual((en[key].message.match(/\$\d/g)||[]).sort(),(es[key].message.match(/\$\d/g)||[]).sort(),key);
});
