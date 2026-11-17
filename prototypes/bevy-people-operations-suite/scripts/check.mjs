import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const canonical=path.join(root,'apps/expenses/dist'),embedded=path.join(root,'apps/hr-portal/web/expenses');
for(const name of fs.readdirSync(canonical))assert.deepEqual(fs.readFileSync(path.join(canonical,name)),fs.readFileSync(path.join(embedded,name)),'Expense module drift: '+name+'. Run npm run sync:expenses.');
for(const entry of ['index.html','apps-script/Dashboard.html']){const html=fs.readFileSync(path.join(root,'apps/insurance',entry),'utf8');for(const [i,m]of [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].entries())if(!/src\s*=/.test(m[1]))new vm.Script(m[2],{filename:'insurance-inline-'+i+'.js'});}
new vm.Script(fs.readFileSync(path.join(root,'apps/insurance/apps-script/Code.gs'),'utf8'),{filename:'insurance-Code.gs'});
for(const app of ['hr-portal','expenses','insurance','daily-updates'])assert.equal(JSON.parse(fs.readFileSync(path.join(root,'apps',app,'package.json'))).private,true);
assert.equal(fs.existsSync(path.join(root,'.github/workflows/pages.yml')),false,'No public Pages deployment in the suite');
console.log('PASS: shared expense assets match, insurance inline JavaScript parses, modules private, no public deployment workflow.');
