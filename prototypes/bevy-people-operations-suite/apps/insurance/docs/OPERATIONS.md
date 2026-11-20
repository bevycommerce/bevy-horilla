> Public handoff: no project mapping, live links or backups are included. Create a separate staging project and configure placeholder values. See PUBLIC_HANDOFF.md at the suite root.

# Operations and recovery

## Runtime and access
1. Employee share link redirects to the Apps Script /exec deployment.
2. Deployment executes as the deploying user, and is restricted to the Bevy Commerce Workspace domain.
3. Both doGet() and getDashboardData() call requireBevy_(), which rejects a missing email or an email outside @bevycommerce.com.
4. The backend reads only 'Share View'!A4:S using the advanced Sheets v4 service. No published CSV endpoint is used by the current runtime.
5. Names are absent from the response, member IDs are masked, and rejected claims are returned as count-only records.
6. The frontend refreshes every 60 seconds while open.

The current manifest was copied directly from the editor. Keep executeAs USER_DEPLOYING and access DOMAIN. Do not deploy as ANYONE or ANYONE_ANONYMOUS. A private GitHub repo alone does not authenticate dashboard visitors.

## Deploy an intentional code change
- Edit the files in apps-script/ and review the diff.
- Use Apps Script editor (link in README), preserving the file names Code.gs and Dashboard.html and manifest.
- Enable the Sheets advanced service v4 if recovering into another project; for a standard Cloud project also enable Google Sheets API there.
- Authorize only the scopes in the manifest.
- In Deploy > Manage deployments, edit the existing employee dashboard deployment, choose a new version, and deploy. This preserves its /exec link.
- Confirm domain-only access and execute-as-deployer remain selected.
- Test using a Bevy account. Check initial-stage claims, settled-awaiting-bank claims, completed claims, mobile cards, search, filters and refresh.
- Verify an outside-domain account is denied. Do not change sharing settings merely to make a test pass.

Optional clasp workflow: install the official @google/clasp package, authenticate using your own account, run clasp pull for the current project before editing, inspect diffs, then clasp push only when intentionally updating the editor. clasp push does not promote the existing production version. OAuth token files stay outside version control.

## Data updates
Update Claims inputs in the Sheet. The frontend fetches changes automatically; no code deployment is required. Confirm bank payment only with evidence, using both the checkbox and actual bank-received date. A settlement is not a bank payment.

## Recovery
- Prefer Drive version history or a full native Sheet copy to recover an entire workbook.
- The dated JSON snapshot contains captured cells with userEnteredValue (including formulas), notes, validation and cell formatting. Its ranges and limits are documented in DATA.md.
- To recover source into the existing project, restore the three apps-script files, authorize the read-only scopes, and version the existing deployment.
- If creating a replacement project, update the sheet constant and .clasp.json for that project, reapply domain-only settings, and update redirect destinations only after the new protected deployment works.
- Recreate missing formula-only capacity by filling the row-relative Claims R:Y formulas and Share View reference formulas down to the desired row count; validate relative references. Do not replace formulas with CSV values.

## Troubleshooting
- Access denied: use a Bevy Commerce Google account and check selected Google profile, domain deployment access and server email check.
- Missing data: confirm advanced Sheets service, deploying user's Sheet access, Share View headers and formula results.
- Old code: editor saves and GitHub commits do not update an already versioned deployment; promote a new version deliberately.
- Pending payable on portal: source amount zero is not a confirmed payable amount.
- Dates or totals unexpected: check bank checkbox/date, start basis, Fri/Sat weekends, selected date window and actual activity dates.
