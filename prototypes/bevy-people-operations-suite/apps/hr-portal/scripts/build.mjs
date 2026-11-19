// Embed every public asset behind the same server-side access gate.
import {readFile,mkdir,writeFile,rm,readdir} from 'node:fs/promises';
const root=new URL('../',import.meta.url),types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'};
const assets={};for(const name of ['index.html','app.js','styles.css','seed.mjs','domain.mjs','favicon.svg','bevy-logo.svg','permissions.mjs','profile-schema.mjs']){const ext=name.slice(name.lastIndexOf('.'));assets['/'+name]={body:await readFile(new URL('web/'+name,root),'utf8'),type:types[ext]};}
for(const name of await readdir(new URL('web/expenses/',root))){const ext=name.slice(name.lastIndexOf('.'));assets['/expenses/'+name]={body:await readFile(new URL('web/expenses/'+name,root),'utf8'),type:ext==='.pdf'?'application/pdf':types[ext]};}
const gate=(await readFile(new URL('worker/gate.mjs',root),'utf8')).replaceAll('export ','');
await rm(new URL('dist',root),{recursive:true,force:true});await mkdir(new URL('dist/server',root),{recursive:true});await mkdir(new URL('dist/.openai',root),{recursive:true});
await writeFile(new URL('dist/server/index.js',root),gate+'\nconst assets='+JSON.stringify(assets)+';\nexport default createHandler(assets);\n');
await writeFile(new URL('dist/.openai/hosting.json',root),await readFile(new URL('.openai/hosting.json',root)));
console.log('Built protected Worker. No unguarded static assets.');
