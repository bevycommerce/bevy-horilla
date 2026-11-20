// Keep the public reference free of production records and deployment configuration.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
for(const name of ['apps/insurance/data','apps/insurance/legacy','apps/insurance/.clasp.json','apps/insurance/live-entry.html','apps/insurance/UPSTREAM_README.md'])assert.equal(fs.existsSync(path.join(root,name)),false,'Private source excluded: '+name);
function scan(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){
 const p=path.join(dir,item.name),rel=path.relative(root,p);
 if(item.name==='node_modules'||item.name==='.git'||rel.startsWith('apps/hr-portal/dist'))continue;
 if(item.isDirectory()){scan(p);continue;}
 assert.ok(!item.isSymbolicLink(),'No symlinks in public snapshot: '+rel);
 const s=fs.readFileSync(p,'utf8');
 for(const pattern of [/https:\/\/(?:docs|script)\.google\.com\//,/\b2PACX-[A-Za-z0-9_-]+/,/\bappgprj_[A-Za-z0-9_]+/,/\bgh[pousr]_[A-Za-z0-9]{20,}/,/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/])assert.ok(!pattern.test(s),'Private configuration or credential pattern in '+rel);
 assert.ok(!/[^\x00-\x7F]/.test(item.name),'Use simple English filenames: '+rel);
}}
scan(root);
console.log('PASS: public code-only handoff excludes business backups, live Google links, hosting IDs, symlinks and credential patterns.');
