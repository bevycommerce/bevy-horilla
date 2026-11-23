import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import * as profile from '../apps/hr-portal/web/profile-schema.mjs';
import * as permissions from '../apps/hr-portal/web/permissions.mjs';
import * as fixture from '../apps/hr-portal/web/seed.mjs';
import * as domain from '../apps/hr-portal/web/domain.mjs';
const require=createRequire(import.meta.url),E=require('../apps/expenses/dist/engine.js'),P=require('../apps/expenses/dist/payroll.js');
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
function dom(html,url='https://review.example/hr/'){
 const d=new JSDOM(html,{url,runScripts:'outside-only'}),w=d.window;
 w.structuredClone=structuredClone;w.setInterval=()=>0;
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 return d;
}
function portal(){const d=dom(read('apps/hr-portal/web/index.html')),w=d.window;w.__modules=[profile,permissions,fixture,domain];let i=0;
 const source=read('apps/hr-portal/web/app.js').replace(/^import \{([^}]+)\} from [^;]+;/gm,(_,names)=>`const {${names}}=window.__modules[${i++}];`);
 w.eval(source+`;window.reviewTest={snapshot:()=>structuredClone(db),select:id=>{employeeId=id;loggedIn=true;view='Daily updates';render();},modal:()=>modal('Edit test','<input name="value">',()=>{}),key:KEY};`);return {d,w,t:w.reviewTest};
}
test('cross-tab refresh closes stale editors and keeps the current employee session',()=>{const {d,w,t}=portal();try{
 t.select('EMP-002');t.modal();assert.equal(w.document.querySelector('#modal').open,true);
 const next=t.snapshot(),own=next.sessionsByEmployee['EMP-002'];next.session=next.sessionsByEmployee['EMP-001'];
 w.dispatchEvent(new w.StorageEvent('storage',{key:t.key,newValue:JSON.stringify(next)}));
 assert.equal(w.document.querySelector('#modal').open,false);assert.equal(w.document.querySelector('#modal').innerHTML,'');
 assert.deepEqual(t.snapshot().session,own);
 }finally{d.window.close();}});
test('focused daily draft survives another employee storage update without submitting as that employee',()=>{const {d,w,t}=portal();try{
 t.select('EMP-002');const form=w.document.querySelector('#daily-update-form');assert.ok(form);
 const field=form.querySelector('[name="progress"]');field.value='Unsaved work belongs to employee two';field.focus();
 const next=t.snapshot();next.session=next.sessionsByEmployee['EMP-001'];
 w.dispatchEvent(new w.StorageEvent('storage',{key:t.key,newValue:JSON.stringify(next)}));
 assert.equal(w.document.querySelector('[name="progress"]').value,field.value);
 assert.equal(t.snapshot().session.drafts.mid.progress,field.value);assert.deepEqual(t.snapshot().session,t.snapshot().sessionsByEmployee['EMP-002']);
 }finally{d.window.close();}});
test('reused name with a new employee ID cannot inherit an old approved claim',()=>{const s=E.seed();s.employees.find(e=>e.id==='DEMO-2').id='REPLACEMENT';const before=JSON.stringify(s.claims);assert.throws(()=>E.batch(s,'Arif Ahmed','2026-11-11','2026-12-08'),/ownership/);assert.equal(JSON.stringify(s.claims),before);});
test('legacy claim ownership requires explicit HR verification and reapproval',()=>{const s=E.seed(),c=s.claims[1];delete c.employeeId;E.migrate(s);assert.equal(c.employeeId,undefined);assert.throws(()=>E.batch(s,c.employee,'2026-11-11','2026-12-08'),/ownership/);assert.throws(()=>E.bindOwner(s,c.id,'DEMO-2','Employee','Arif Ahmed','Checked bill'),/requires HR/);E.bindOwner(s,c.id,'DEMO-2','HR','HR reviewer','Compared original bill with employee record');assert.equal(c.status,'Submitted');assert.equal(c.approvals.hr.status,'Pending');assert.throws(()=>E.bindOwner(s,c.id,'DEMO-1','HR','HR reviewer','Reassignment forbidden'),/requires HR/);E.review(s,c.id,'HR','HR reviewer','Approved','Original owner and evidence checked',850);assert.equal(E.batch(s,c.employee,'2026-11-11','2026-12-08').employeeId,'DEMO-2');});
test('frozen payroll rows retain claim ownership even when a directory name is reused',()=>{const s=E.seed(),b=E.batch(s,'Arif Ahmed','2026-11-11','2026-12-08');s.employees.find(e=>e.id==='DEMO-2').id='NEW';assert.equal(E.exportRows(s,b.id)[0].employeeId,'DEMO-2');s.claims[1].employeeId='NEW';assert.throws(()=>E.exportRows(s,b.id),/invalid/);});
test('ownership change invalidates an already displayed payroll preview',()=>{const s=E.seed(),o={from:'2026-11-01',to:'2026-11-11',paymentDate:'2026-12-08'},p=P.preview(s,o),fingerprint=P.fingerprint(p);s.claims[1].employeeId='UNKNOWN';assert.throws(()=>P.createRun(s,o,p.ids,fingerprint),/changed since preview/);assert.equal(s.payrollRuns,undefined);});
function expenses(){const d=dom(read('apps/expenses/dist/index.html'),'https://review.example/expenses/'),w=d.window;
 // Browsers expose named controls on forms; jsdom needs that compatibility shim.
 for(const name of ['category','currency','amount','date','receiptFile','sample'])Object.defineProperty(w.HTMLFormElement.prototype,name,{configurable:true,get(){return this.elements.namedItem(name);}});
 for(const file of ['categories.js','engine.js','payroll.js','payroll-lab.js','receipts.js'])w.eval(read('apps/expenses/dist/'+file));
 w.eval(read('apps/expenses/dist/app.js')+';window.expenseTest={snapshot:()=>structuredClone(s),setState:value=>{s=value;},open:c=>newClaim(c),upload:()=>submitForm(false,\'EXP-1001\'),rates:fetchRates};');return {d,w,t:w.expenseTest};}
test('incomplete FX response does not partly overwrite a valid quote',async()=>{const {d,w,t}=expenses();try{const before=t.snapshot();w.fetch=async()=>({ok:true,json:async()=>({result:'success',rates:{CAD:1,USD:2},time_last_update_unix:Date.now()/1000})});await t.rates();assert.deepEqual(t.snapshot().rates,before.rates);assert.equal(t.snapshot().rateTime,before.rateTime);assert.match(w.document.querySelector('#toast').textContent,/Existing rates retained/);}finally{d.window.close();}});
test('receipt upload cannot overwrite a claim reserved in another tab',async()=>{const {d,w,t}=expenses();try{t.open(t.snapshot().claims[0]);let resolve;w.ExpenseReceipts.sample=async()=>({});w.ExpenseReceipts.put=()=>new Promise(r=>{resolve=r;});w.document.querySelector('[name="sample"]').checked=true;const upload=t.upload();await new Promise(r=>setImmediate(r));assert.ok(resolve,w.document.querySelector('#toast').textContent);const next=t.snapshot();next.claims[0].status='Reserved';next.claims[0].batch='CONCURRENT-BATCH';t.setState(next);resolve({receipt:'new.pdf',receiptKey:'new-key',receiptHash:'new-proof'});await upload;assert.equal(t.snapshot().claims[0].batch,'CONCURRENT-BATCH');assert.equal(t.snapshot().claims[0].status,'Reserved');assert.match(w.document.querySelector('#toast').textContent,/changed during upload/);}finally{d.window.close();}});
test('Windows verification launches the npm JavaScript CLI without a shell',async()=>{const vm=await import('node:vm'),source=read('scripts/verify.mjs'),calls=[];const run=source.slice(source.indexOf('function run('),source.indexOf("const npm='npm';"));const node='C:\\Program Files\\nodejs\\node.exe',cli='C:\\Program Files\\nodejs\\node_modules\\npm\\bin\\npm-cli.js';vm.runInNewContext(run+";run('npm',['--prefix','apps/hr-portal','test']);",{process:{platform:'win32',env:{npm_execpath:cli},execPath:node,exit:()=>assert.fail('Unexpected failure')},root:'C:\\review checkout',spawnSync:(command,args,options)=>{calls.push({command,args,options});return {status:0};}});assert.equal(calls[0].command,node);assert.equal(calls[0].args[0],cli);assert.equal(calls[0].options.shell,undefined);});
