(function(root){
'use strict';
function parseCSV(text){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';}else cell+=c;}if(quoted)throw Error('Incomplete CSV');if(cell||row.length){row.push(cell);rows.push(row);}return rows;}
const months={jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,oct:9,nov:10,dec:11};
function day(v){
 v=String(v??'').trim();let m,y,mo,d;
 if((m=v.match(/^(\d{4})-(\d{2})-(\d{2})$/))){y=+m[1];mo=+m[2]-1;d=+m[3];}
 else if((m=v.match(/^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$/))){y=+m[3];mo=months[m[2].toLowerCase().slice(0,3)];d=+m[1];}
 else if((m=v.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/))){y=+m[3];mo=+m[2]-1;d=+m[1];}
 else return null;
 if(!Number.isInteger(mo)||y<1900||y>9999||mo<0||mo>11||d<1||d>31)return null;
 const t=Date.UTC(y,mo,d),dt=new Date(t);return dt.getUTCFullYear()===y&&dt.getUTCMonth()===mo&&dt.getUTCDate()===d?t:null;
}
function today(){const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Dhaka',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const v=t=>p.find(x=>x.type===t).value;return Date.UTC(+v('year'),+v('month')-1,+v('day'));}
function numeric(v){if(v==null)return null;const t=String(v).trim().replace(/^[৳$]\s*/, '').replace(/,/g,'');if(!/^-?\d+(?:\.\d+)?$/.test(t))return null;const n=Number(t);return Number.isFinite(n)?n:null;}
function workingDays(a,b){if(a===null||b===null||b<a)return null;let n=0;for(let d=a+86400000;d<=b;d+=86400000){const w=new Date(d).getUTCDay();if(w!==5&&w!==6)n++;}return n;}
function decode(text,now=today()){
 const rows=parseCSV(text),h=rows.findIndex(r=>r[0]?.trim()==='Claim Tracking Number');if(h<0)throw Error('Published Share View headers missing.');
 const heads=rows[h].map(x=>x.trim()),field=n=>{const i=heads.indexOf(n);if(i<0)throw Error('Published tracker is updating. Please refresh shortly. Missing: '+n);return i;};
 const member=field('Member ID (last 4 digits)'),start=field('Start Date'),basis=field('Start Basis'),checked=field('Bank Received Confirmed'),post=field('Post Status');
 const seen=new Set();return rows.slice(h+1).filter(r=>r[0]?.trim()).map(r=>{
 const tracking=r[0].trim();if(seen.has(tracking))throw Error('Duplicate tracking references in source.');seen.add(tracking);
 const received=day(r[5]),settled=day(r[6]),bank=day(r[7]),began=day(r[start]);const confirmed=String(r[checked]).toLowerCase()==='true';
 const validReceived=received!==null&&received<=now&&(began===null||received>=began),validSettled=String(r[post]).trim()==='Settled'&&settled!==null&&settled<=now&&validReceived&&settled>=received;
 const validBank=confirmed&&bank!==null&&bank<=now&&validSettled&&bank>=settled&&(began===null||bank>=began);
 const insurerRejected=String(r[post]).trim()==='Reject';const age=workingDays(began,now),autoRejected=!confirmed&&age!==null&&age>30;
 const times=[workingDays(began,received),validSettled?workingDays(received,settled):null,validBank?workingDays(settled,bank):null,validBank?workingDays(began,bank):null];
 let conclusion=validBank?'Bank confirmed':validSettled?'Settled; bank confirmation pending':String(r[post]).trim()==='Reject'?'Rejected':'Awaiting settlement';
 const issue=confirmed&&!validBank?'Bank confirmation needs a valid receipt date':bank!==null&&!confirmed?'Bank date entered; confirmation not checked':null;
 if(issue)conclusion=issue; if(insurerRejected)conclusion='Rejected'; if(!confirmed&&!autoRejected&&!insurerRejected)conclusion=validSettled?'Pending · bank confirmation awaited':'Pending · insurer processing';
 return {portalStage:String(r[post]||'').trim()||String(r[heads.indexOf('Insurer Status')]||'').trim()||'Processing',tracking,claim:r[1],type:r[2],member:/^\*{4}\d{4}(?:-\d+)?$/.test(r[member])?r[member]:'Hidden',amount:numeric(r[4]),received:validReceived?received:null,settled:validSettled?settled:null,bank:validBank?bank:null,start:began,basis:r[basis]||'HR approval',times,conclusion,status:(autoRejected||insurerRejected)?'rejected':validBank?'done':!confirmed?'pending':'other',issue,age,autoRejected,confirmed,insurerRejected:String(r[post]).trim()==="Reject"};
 });
}


const api={parseCSV,day,today,numeric,workingDays,decode};if(typeof module!=='undefined')module.exports=api;else root.BevyInsurance=api;
})(globalThis);
