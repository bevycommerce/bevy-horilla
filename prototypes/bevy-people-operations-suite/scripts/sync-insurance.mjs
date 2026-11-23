import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../apps/insurance/',import.meta.url));
const prefix=fs.readFileSync(root+'server/adapter.gs','utf8');
const local=fs.readFileSync(root+'logic.js','utf8');
let core=local.slice(local.indexOf('function parseCSV('),local.indexOf('const api='));
for(const n of ['parseCSV','day','today','numeric','workingDays','decode'])core=core.replace(new RegExp('\\b'+n+'(?=\\s*\\()','g'),n+'_');
fs.writeFileSync(root+'apps-script/Code.gs',(prefix+'// Generated validation core. Edit logic.js, then npm run sync:insurance.\n'+core).trimEnd()+'\n');
console.log('Insurance Apps Script validation synchronized.');
