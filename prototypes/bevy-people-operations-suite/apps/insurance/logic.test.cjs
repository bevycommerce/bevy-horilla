const test=require('node:test'),assert=require('node:assert/strict'),L=require('./logic.js');
const now=Date.UTC(2026,10,17);
const header=['Claim Tracking Number','Claim Number','Type','Unused','Amount','Received','Settled','Bank','Member ID (last 4 digits)','Start Date','Start Basis','Bank Received Confirmed','Post Status'];
const base=['T-1','C-1','OPD','','1200','02 Nov 2026','03 Nov 2026','04 Nov 2026','****1234-01','01 Nov 2026','HR approval','TRUE','Settled'];
const csv=rows=>[header,...rows].map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');
function claim(changes={}){const r=[...base];for(const [i,v]of Object.entries(changes))r[+i]=v;return L.decode(csv([r]),now)[0];}
test('CSV handles quoted commas, escaped quotes and CRLF',()=>assert.deepEqual(L.parseCSV('"a,b","a""b"\r\n1,2'),[['a,b','a"b'],['1','2']]));
test('invalid and rolled-over dates are rejected',()=>{for(const d of ['2026-02-30','31 Apr 2026','2026-13-01','12 Unknown 2026','29/02/2025'])assert.equal(L.day(d),null,d);assert.equal(L.day('29 Feb 2024'),Date.UTC(2024,1,29));});
test('missing and malformed amounts never silently become zero',()=>{for(const v of ['',null,undefined,'abc','৳','12oops'])assert.equal(L.numeric(v),null);assert.equal(L.numeric('৳1,200.50'),1200.5);assert.equal(L.numeric('0'),0);});
test('working-day durations exclude Friday and Saturday',()=>{assert.equal(L.workingDays(Date.UTC(2026,10,12),Date.UTC(2026,10,15)),1);assert.equal(L.workingDays(now,now),0);});
test('valid confirmed claim qualifies and full member IDs stay hidden',()=>{assert.equal(claim().status,'done');assert.equal(claim()["member"],'****1234-01');assert.equal(claim({8:'987654321'}).member,'Hidden');});
test('explicit insurer rejection stays rejected instead of pending',()=>{const c=claim({12:'Reject',11:'FALSE'});assert.equal(c.status,'rejected');assert.equal(c.conclusion,'Rejected');});
test('pending and date-only bank records never become paid',()=>{assert.equal(claim({11:'FALSE'}).status,'pending');assert.notEqual(claim({7:'',11:'TRUE'}).status,'done');});
test('missing, reversed and future receipt dates cannot publish completed claims',()=>{for(const change of [{5:''},{5:'2026-12-01'},{5:'2026-10-01'},{6:'2026-11-01'},{7:'2026-11-02'}])assert.notEqual(claim(change).status,'done');});
test('older unconfirmed claim auto-rejects after 30 working days',()=>{assert.equal(claim({9:'2026-08-01',11:'FALSE'}).autoRejected,true);});
test('duplicate source tracking references fail closed',()=>assert.throws(()=>L.decode(csv([base,base]),now),/Duplicate/));
