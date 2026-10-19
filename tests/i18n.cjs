// Extension scripts call tx(): load the generated catalog in Spanish, the language the tests assert.
const fs = require('node:fs');
module.exports = 'globalThis.AnacoObLang="es";' + fs.readFileSync('extension/i18n-catalog.js','utf8') + fs.readFileSync('extension/i18n.js','utf8');
