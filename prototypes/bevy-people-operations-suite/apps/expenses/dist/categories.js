(function(root){
const definitions={
 'Lunch / Meals':{kind:'meal',version:2,note:'Use the specific meal date. Submit a separate claim for another date.'},
 'AI Subscriptions':{kind:'subscription',version:2,note:'Use the specific date you paid for the service. Company-paid subscriptions are not reimbursable.'},
 'Cursor / Developer Tools':{kind:'subscription',version:2,note:'Use the specific date you paid for this subscription.'},
 'Travel':{kind:'travel',version:2,note:'Use the specific travel expense date and destination.'},
 'Equipment / Purchases':{kind:'purchase',version:2,note:'Describe the purchased item and quantity.'},
 'Training / Courses':{kind:'training',version:2,note:'Add the course and provider. Prior approval may be required.'},
 'Other':{kind:'other',version:2,note:'Explain the business purpose. HR must confirm coverage.'}
};
const date=v=>/^\d{4}-\d{2}-\d{2}$/.test(v||'')&&Number.isFinite(Date.parse(v))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
function dates(from,to){if(!date(from)||!date(to)||from>to)return [];const out=[];for(let t=Date.parse(from);t<=Date.parse(to)&&out.length<=92;t+=86400000)out.push(new Date(t).toISOString().slice(0,10));return out;}
function validate(def,c){if(!def)throw Error('Choose a configured expense category.');if(!date(c.date))throw Error('Choose a valid expense date.');switch(def.kind){case 'meal':break;case 'subscription':if(!c.plan?.trim()||!['Monthly','Annual'].includes(c.cycle))throw Error('Add the subscription plan and billing cycle.');break;case 'travel':if(!c.destination?.trim())throw Error('Add the destination or route.');break;case 'purchase':if(!c.item?.trim()||!Number.isInteger(+c.quantity)||+c.quantity<1||+c.quantity>10000)throw Error('Add an item and a positive whole quantity.');break;case 'training':if(!c.course?.trim())throw Error('Add the course or training name.');break;case 'other':break;default:throw Error('Unsupported category form type.');}}
function serviceWindow(c){if(!date(c.date))return null;const d=new Date(c.date+'T00:00:00Z');if(c.cycle==='Annual'){d.setUTCFullYear(d.getUTCFullYear()+1);d.setUTCDate(d.getUTCDate()-1);return [c.date,d.toISOString().slice(0,10)];}const [y,m]=c.date.slice(0,7).split('-').map(Number);return [c.date.slice(0,7)+'-01',new Date(Date.UTC(y,m,0)).toISOString().slice(0,10)];}
function summary(c){switch(c.categorySchema?.kind){case 'meal':return 'Meal expense · '+c.date;case 'subscription':return `${c.plan||''} · ${c.cycle||''} · billed ${c.date}`;case 'travel':return `${c.destination} · ${c.date}`;case 'purchase':return `${c.item} × ${c.quantity}`;case 'training':return c.course;default:return c.purpose;}}
const api={definitions,validate,dates,summary,serviceWindow};if(typeof module!=='undefined')module.exports=api;else root.ExpenseCategories=api;
})(globalThis);
