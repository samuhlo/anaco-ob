const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync('extension/providers.js','utf8'),ctx);
const providers=ctx.AnacoObProviders;

test('each service fills a usable OpenAI-compatible address and model',()=>{
  for(const id of ['claude','gemini','minimax','qwen','openrouter','openai','ollama','lmstudio']){
    const service=providers.find(id);
    assert.ok(service,id);
    assert.match(service.base,/^https?:\/\/[^/]+\/.+[^/]$/,id);
    if(!service.local){assert.ok(service.model,id);assert.match(service.keys,/^https:\/\//,id);}
  }
  assert.equal(providers.find('claude').base,'https://api.anthropic.com/v1');
  assert.equal(providers.find('ollama').base,'http://localhost:11434/v1');
});

test('a saved address is recognised as its service, with or without the final slash',()=>{
  assert.equal(providers.match('https://generativelanguage.googleapis.com/v1beta/openai/'),'gemini');
  assert.equal(providers.match('http://localhost:1234/v1'),'lmstudio');
  assert.equal(providers.match('https://mi-servidor.example/v1'),'custom');
});
