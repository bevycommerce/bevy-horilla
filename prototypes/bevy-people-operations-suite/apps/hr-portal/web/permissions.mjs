// Demo role policy. Production must enforce the same decisions on the backend.
export const ROLES=['Super Admin','HR Admin','Employee'];
export const MODULES=[
 {key:'expenses',title:'Expense approvals & payroll export',note:'Mandatory HR final review, expense policies, FX-locked reimbursement batches; no salary access'},
 {key:'configuration',title:'Module configuration',note:'Edit approved policy settings, reporting preferences and sample source mapping'},
 {key:'communications',title:'Announcements & templates',note:'Edit Bevy announcements and notification previews'},
 {key:'people',title:'Employee management',note:'Directory, profiles and employment changes'},
 {key:'confidential',title:'Confidential details',note:'Personal identifiers and bank information'},
 {key:'assets',title:'Asset management',note:'Inventory, device assignment and returns'},
 {key:'leave',title:'Leave approvals',note:'Review employee leave requests'},
 {key:'insurance',title:'Insurance tracker',note:'HR-only pending and unconfirmed claim preview'},
 {key:'daily',title:'Daily reports & review',note:'Team records, exports and exception review'},
 {key:'archives',title:'Employee archives',note:'Offboarding retention and deletion decisions'},
 {key:'audit',title:'Activity log',note:'Review administrative changes'}
];
export const defaultGrants=role=>role==='Employee'?[]:MODULES.map(m=>m.key);
export function permitted(account,key){if(!account||account.status!=='Active')return false;if(account.role==='Super Admin')return true;if(account.role!=='HR Admin')return false;return MODULES.some(m=>m.key===key)&&(account.grants??defaultGrants(account.role)).includes(key);}
export function changeAccess(accounts,actorId,targetId,change){const actor=accounts.find(a=>a.employeeId===actorId),target=accounts.find(a=>a.employeeId===targetId);if(actor?.role!=='Super Admin'||actor.status!=='Active')throw Error('Only an active Super Admin can manage access.');if(!target)throw Error('Choose an existing employee account.');if(!ROLES.includes(change.role)||!['Active','Suspended'].includes(change.status))throw Error('Choose a valid role and access status.');if(actorId===targetId&&(change.role!=='Super Admin'||change.status!=='Active'))throw Error('You cannot remove or suspend your own Super Admin access.');const grants=change.role==='Employee'?[]:change.role==='Super Admin'?defaultGrants(change.role):[...new Set(change.grants||[])].filter(k=>MODULES.some(m=>m.key===k));if(grants.includes('confidential')&&!grants.includes('people'))throw Error('Confidential details require Employee management access.');const next={...target,...change,grants};if(!accounts.some(a=>{const v=a.employeeId===targetId?next:a;return v.role==='Super Admin'&&v.status==='Active';}))throw Error('Keep at least one active Super Admin.');return accounts.map(a=>a.employeeId===targetId?next:a);}
export function seedAccounts(employees){return employees.filter(e=>e.status==='Active').map((e,i)=>({employeeId:e.id,role:i===0?'Super Admin':i===2||i===10?'HR Admin':'Employee',status:'Active',grants:defaultGrants(i===0?'Super Admin':i===2||i===10?'HR Admin':'Employee'),updatedAt:null,reason:'Initial demo access'}));}
