import {copyFile,mkdir} from 'node:fs/promises';
await mkdir(new URL('../extension/vendor/',import.meta.url),{recursive:true});
for(const [source,target] of [['marked/lib/marked.umd.js','marked.js'],['marked/LICENSE','marked-LICENSE'],['dompurify/dist/purify.min.js','purify.js'],['dompurify/LICENSE','DOMPurify-LICENSE']]){
  await copyFile(new URL('../node_modules/'+source,import.meta.url),new URL('../extension/vendor/'+target,import.meta.url));
}
