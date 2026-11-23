const INSURANCE_SHEET_ID = 'CONFIGURE_STAGING_SHEET_ID';
function requireBevy_() {
 const email = String(Session.getActiveUser().getEmail() || '').trim().toLowerCase();
 if (!/^[^@]+@bevycommerce\.com$/.test(email)) throw new Error('Access restricted. Please sign in with your Bevy Commerce Google account.');
}
function doGet() {
 try { requireBevy_(); return HtmlService.createHtmlOutputFromFile('Dashboard').setTitle('Bevy Commerce | Insurance Claims').addMetaTag('viewport','width=device-width, initial-scale=1'); }
 catch(e) { return HtmlService.createHtmlOutput('<h2>Bevy employees only</h2><p>Please open this link using your Bevy Commerce Google account.</p>').setTitle('Bevy account required'); }
}
function getDashboardData() {
 requireBevy_();
 const rows = Sheets.Spreadsheets.Values.get(INSURANCE_SHEET_ID, "'Share View'!A4:S", {valueRenderOption:'FORMATTED_VALUE'}).values || [];
 if (!rows.length) throw new Error('Dashboard source unavailable.');
 const csv=rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n');
 return decode_(csv).map(c=>{
  if(!c.autoRejected&&!c.insurerRejected)return c;
  return {start:c.start,status:'rejected',autoRejected:c.autoRejected,insurerRejected:c.insurerRejected,times:[null,null,null,null]};
 });
}
