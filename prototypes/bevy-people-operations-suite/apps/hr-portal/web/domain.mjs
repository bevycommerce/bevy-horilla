// Pure domain rules. All date-only calculations use UTC to avoid local DST drift.
export const DAY=86400000;
export const iso=d=>new Date(d).toISOString().slice(0,10);
export const shift=(d,n)=>iso(new Date(d+'T00:00:00Z').getTime()+n*DAY);
export const valid=d=>/^\d{4}-\d{2}-\d{2}$/.test(d||'') && !Number.isNaN(Date.parse(d+'T00:00:00Z')) && iso(d)===d;
export function workingDays(start,end){if(!valid(start)||!valid(end)||end<start)return null;let n=0;for(let t=Date.parse(start)+DAY;t<=Date.parse(end);t+=DAY){if(![5,6].includes(new Date(t).getUTCDay()))n++;}return n;}
export function monthsSince(start,end=iso(Date.now())){if(!valid(start)||!valid(end)||start>end)return 0;const a=new Date(start),b=new Date(end);return Math.max(0,(b.getUTCFullYear()-a.getUTCFullYear())*12+b.getUTCMonth()-a.getUTCMonth()-(b.getUTCDate()<a.getUTCDate()?1:0));}
export const experience=n=>`${Math.floor(n/12)}y ${n%12}m`;
export const archiveEligible=(d,today)=>valid(d)&&valid(today)&&(Date.parse(today)-Date.parse(d))/DAY>=30;
export const completed=c=>c.status==='Completed'&&c.bankConfirmed&&valid(c.bank)&&valid(c.start)&&valid(c.received)&&valid(c.settled)&&c.start<=c.received&&c.received<=c.settled&&c.settled<=c.bank;
export const stages=c=>[workingDays(c.start,c.received),workingDays(c.received,c.settled),workingDays(c.settled,c.bank)];
export const average=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;
export function rangeFor(period,today,month,from,to){const y=today.slice(0,4);if(period==='30')return [shift(today,-29),today];if(period==='month')return [today.slice(0,7)+'-01',today];if(period==='year')return [y+'-01-01',today];if(period==='choose'&&/^\d{4}-\d{2}$/.test(month)){const a=month+'-01';return [a,iso(Date.UTC(+month.slice(0,4),+month.slice(5,7),0))];}if(period==='custom')return [from,to];return ['0000-01-01','9999-12-31'];}
export const inRange=(d,r)=>valid(d)&&d>=r[0]&&d<=r[1];
export function netSeconds(session,now=Date.now()){return Math.max(0,Math.floor(((session.ended||now)-session.started-session.breakMs-(session.pausedAt?(session.ended||now)-session.pausedAt:0))/1000));}
export const hms=s=>[Math.floor(s/3600),Math.floor(s%3600/60),Math.floor(s%60)].map(x=>String(x).padStart(2,'0')).join(':');
export function assignAsset(asset,employee,date){if(!employee||employee.status!=='Active')throw Error('Choose an active employee.');if(!['Available','Returned'].includes(asset.status))throw Error('Only available or returned devices can be assigned.');if(!valid(date))throw Error('Enter a valid assignment date.');return {...asset,employeeId:employee.id,assigned:date,returned:'',status:'Assigned'};}
// Portal entry starts one workday; reloads and same-day re-entry never reset it.
export function portalSession(current,records,employeeId,date,now=Date.now()){
 if(current&&(!current.ended||current.date===date))return current;
 const closed=records.find(r=>r.employeeId===employeeId&&r.date===date);
 if(closed)return {started:now-closed.net*1000-closed.breaks*1000,ended:now,date,breakMs:closed.breaks*1000,pausedAt:0,mid:closed.mid,eod:closed.eod,revisions:closed.revisions||[],events:[],restored:true};
 return {started:now,date,breakMs:0,pausedAt:0,mid:'',eod:'',missReason:'',revisions:[],drafts:{},events:[{at:now,action:'Signed in to the portal',note:'Working time started automatically.'}],automatic:true};
}

// Annual allowances are derived by calendar year; never roll balances forward.
export const LEAVE_TYPES=['Vacation','Floater Day','Sick Leave'];
export function leaveDays(from,to){if(!valid(from)||!valid(to)||to<from)return 0;return workingDays(shift(from,-1),to);}
export function leaveBalance(records,employeeId,type,year,excludeId=''){
 const allowance=type==='Vacation'?11:type==='Floater Day'?3:Infinity;
 const used=status=>records.filter(l=>l.id!==excludeId&&l.employeeId===employeeId&&l.type===type&&l.status===status).reduce((n,l)=>{const a=l.from>year+'-01-01'?l.from:year+'-01-01',b=l.to<year+'-12-31'?l.to:year+'-12-31';return n+leaveDays(a,b);},0);
 const approved=used('Approved'),pending=used('Pending');return {allowance,approved,pending,available:allowance-approved-pending};
}
export function validateLeave(request,records,threshold=2,excludeId=''){
 if(!LEAVE_TYPES.includes(request.type))throw Error('Choose a supported leave type.');
 if(!valid(request.from)||!valid(request.to)||request.to<request.from)throw Error('Enter a valid date range.');
 if(request.from.slice(0,4)!==request.to.slice(0,4))throw Error('Submit separate requests for each calendar year.');
 const days=leaveDays(request.from,request.to);if(!days)throw Error('Choose at least one working day (Sunday–Thursday).');
 if(records.some(l=>l.id!==excludeId&&l.employeeId===request.employeeId&&['Pending','Approved'].includes(l.status)&&l.from<=request.to&&l.to>=request.from))throw Error('This employee already has an overlapping request.');
 if(request.type==='Sick Leave'&&days>threshold&&!request.medicalDoc)throw Error('A medical document is required for more than '+threshold+' working days.');
 if(days>leaveBalance(records,request.employeeId,request.type,request.from.slice(0,4),excludeId).available)throw Error('Insufficient available leave after approved and pending requests.');
 return days;
}

export function maskMemberId(value){const match=String(value||'').match(/^(.*?)(-\d{2})?$/);return '•••• '+(match?.[1]||'').slice(-4)+(match?.[2]||'');}
export function reminderEligibility(employeeId,date,leaves){
 if(!valid(date)||[5,6].includes(new Date(date).getUTCDay()))return {required:false,reason:'Non-working day'};
 const leave=leaves.find(l=>l.employeeId===employeeId&&l.status==='Approved'&&l.from<=date&&l.to>=date);
 return leave?{required:false,reason:'Approved '+leave.type}:{required:true,reason:'Working day'};
}
export function dueReminders(session,employeeId,date,leaves,now=Date.now()){
 const eligibility=reminderEligibility(employeeId,date,leaves);if(!eligibility.required)return {eligibility,items:[]};
 if(!session||session.date!==date||session.ended)return {eligibility,items:[]};
 const n=netSeconds(session,now),items=[];
 if(n>=14400&&!session.mid&&!session.missReason)items.push({kind:'Mid-Day',text:'You have reached 4 net working hours. Please share your progress or record a missed-update reason.'});
 if(n>=26100&&!session.eod)items.push({kind:'EOD',text:'Please share your EOD update and allow 30–45 minutes for feedback before signing out.'});
 return {eligibility,items};
}

export function editAssetDetails(asset,data,assets,today=iso(Date.now())){
 const next={...asset,...data,serial:String(data.serial||'').trim()};
 if(!['MacBook','iPhone','iPad','Other'].includes(next.type)||!String(next.name||'').trim()||!String(next.model||'').trim()||!next.serial)throw Error('Complete device type, name, model and serial.');
 if(next.assigned&&(!valid(next.assigned)||next.assigned>today))throw Error('Assignment date must be valid and on or before today.');
 if(next.returned&&(!valid(next.returned)||next.returned>today||(next.assigned&&next.returned<next.assigned)))throw Error('Return date must be valid, after assignment and on or before today.');
 if(next.status==='Assigned'&&(!next.assigned||next.returned))throw Error('Assigned devices need an assignment date and no return date.');
 if(assets.some(a=>a.id!==asset.id&&a.serial.toLowerCase()===next.serial.toLowerCase()))throw Error('Serial number is already recorded.');
 return next;
}
export function validateClaimFixture(c){
 if(!String(c.tracking||'').trim()||!/^\d+(?:-\d{2})?$/.test(c.member||''))throw Error('Enter a tracking reference and numeric member ID with optional -01/-02 suffix.');
 if(!['OPD','IPD','Maternity'].includes(c.type)||!['Completed','Pending','Unconfirmed','Rejected','Overdue'].includes(c.status))throw Error('Select a supported claim type and status.');
 if(!valid(c.start)||!Number.isFinite(c.paid)||c.paid<0)throw Error('Enter a valid start date and non-negative amount.');
 const dates=[c.start,c.received,c.settled,c.bank].filter(Boolean);if(dates.some(d=>!valid(d))||dates.some((d,i)=>i&&d<dates[i-1]))throw Error('Claim dates must be valid and chronological.');
 if(c.status==='Completed'&&!completed(c))throw Error('Completed requires insurer receipt, settlement, confirmed bank receipt and all valid dates.');
 return c;
}
export function correctDailyTime(record,netMinutes,breakMinutes,reason,now=new Date().toISOString()){
 if(!String(reason||'').trim())throw Error('A correction reason is required.');
 if(![netMinutes,breakMinutes].every(n=>Number.isFinite(n)&&n>=0&&n<=1440)||netMinutes+breakMinutes>1440)throw Error('Work and breaks must be non-negative and total no more than 24 hours.');
 return {...record,net:Math.round(netMinutes*60),breaks:Math.round(breakMinutes*60),reason,status:'Pending review',revisions:[...(record.revisions||[]),{at:now,field:'Time correction',text:JSON.stringify({previousNet:record.net,previousBreaks:record.breaks,previousStatus:record.status,reason})}]};
}
