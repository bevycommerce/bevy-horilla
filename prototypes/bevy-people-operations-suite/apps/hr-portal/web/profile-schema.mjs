// Field registry mirrors scope document sections 3 and 4. Shared by display/edit/QA.
export const personalFields=[['name','Full name'],['address','Address'],['email','Company email'],['personalEmail','Personal email'],['phone','WhatsApp phone number'],['emergency','Emergency phone number'],['blood','Blood group'],['gender','Gender'],['dob','Date of birth'],['nid','NID / Passport number']];
export const jobFields=[['joined','Joining date at Bevy'],['position','Position'],['department','Department'],['type','Employee type'],['manager','Reporting manager'],['location','Work location']];
export const educationFields=[['education','University-level education qualification'],['previousMonths','Previous experience (months)']];
export const bankFields=[['bankName','Bank name'],['branch','Branch name'],['holder','Account holder name'],['account','Account number'],['routing','Routing number'],['swift','SWIFT / BIC (if applicable)']];
export const profileGroups=[['Personal information',personalFields],['Employment information',jobFields],['Education & experience',educationFields],['Confidential bank information',bankFields]];
export const bloodGroups=['Not provided','A+','A−','B+','B−','AB+','AB−','O+','O−'];
export function validateProfile(data,employees,id,today){
 for(const key of ['name','email','joined','position','department','type','manager','location'])if(!String(data[key]??'').trim())throw Error('Complete all required employment fields, full name and company email.');
 if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email))throw Error('Enter a valid company email.');
 if(data.personalEmail&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.personalEmail))throw Error('Enter a valid personal email.');
 const validDate=d=>/^\d{4}-\d{2}-\d{2}$/.test(d||'')&&!Number.isNaN(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
 if(!validDate(data.joined)||data.joined>today)throw Error('Enter a valid joining date on or before today.');
 if(data.dob&&(!validDate(data.dob)||data.dob>=today||data.dob>=data.joined))throw Error('Date of birth must be before today and the joining date.');
 if(data.previousMonths===''||!Number.isInteger(Number(data.previousMonths))||Number(data.previousMonths)<0||Number(data.previousMonths)>1200)throw Error('Previous experience must be 0–1200 whole months.');
 if(employees.some(e=>e.id!==id&&e.email.trim().toLowerCase()===data.email.trim().toLowerCase()))throw Error('Company email is already in use.');
 return {...data,email:data.email.trim().toLowerCase(),previousMonths:Number(data.previousMonths)};
}
export function profileCoverage(e){const keys=[...personalFields,...jobFields,...educationFields,...bankFields.filter(([k])=>k!=='swift')].map(([k])=>k);return {total:keys.length,complete:keys.filter(k=>e[k]!==undefined&&e[k]!==null&&String(e[k]).trim()!=='').length,missing:keys.filter(k=>e[k]===undefined||e[k]===null||String(e[k]).trim()==='')};}
