const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync('extension/diagnosis.js','utf8')+';globalThis.diagnosis=AnacoObDiagnosis;',ctx);
const diagnosis=ctx.diagnosis;

test('a missing native host is told apart from a failing service and a missing vault',()=>{
  assert.equal(diagnosis.connection(new Error('No such native application org.samuh.anaco_ob')).kind,'missing');
  assert.equal(diagnosis.connection(new Error('No se pudo conectar con el servicio local. Ejecuta scripts/install.py.')).kind,'missing');
  assert.equal(diagnosis.connection(new Error('No encuentro el vault. Configura una carpeta existente en Opciones.')).kind,'vault');
  const failing=diagnosis.connection(new Error('Traceback: algo falló'));
  assert.equal(failing.kind,'error');assert.equal(failing.action,'welcome');
});

test('a healthy status has no problems; version and AI issues carry their fix',()=>{
  const ok={version:'1.0.0',ai:{provider:'codex',ready:true}};
  assert.deepEqual([...diagnosis.status(ok,'1.0.0')],[]);
  const problems=diagnosis.status({version:'0.11.0',ai:{provider:'codex',ready:false,message:'No encuentro Codex.'}},'1.0.0');
  assert.deepEqual([...problems.map(p=>p.kind)],['version','ai']);
  assert.match(problems[0].text,/pipx upgrade anaco-ob/);
  assert.equal(problems[1].action,'options');
});

test('install steps follow the operating system',()=>{
  const linux=diagnosis.installSteps('linux').map(s=>s.command).join('\n');
  assert.match(linux,/pipx install git\+https:\/\/github.com\/samuhlo\/anaco-ob/);
  assert.match(linux,/anaco-ob install --vault/);
  const windows=diagnosis.installSteps('win').map(s=>s.command).join('\n');
  assert.match(windows,/py -m pip install --user pipx/);
  assert.match(diagnosis.installSteps('mac').map(s=>s.command).join('\n'),/brew install pipx/);
});
