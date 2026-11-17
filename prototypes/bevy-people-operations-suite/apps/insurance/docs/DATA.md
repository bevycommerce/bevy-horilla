# Insurance data contract

Schema reference only. No real claim records or workbook snapshots are included.

## Tabs
| Tab | sheetId | Role |
| --- | --- | --- |
| Dashboard | Configure in staging | HR workbook summary |
| Claims | Configure in staging | Authoritative inputs and row calculations |
| Share View | Configure in staging | Masked read-only feed, header row 4 |
| Import | Configure in staging | Existing import/staging tab, not part of runtime feed |
| Guide | Configure in staging | Workbook instructions |

## Claims columns
A tracking; B claim number; C type; D member ID; E claimed BDT; F payable BDT; G HR approval date; H insurer status; I received date; J post status; K settlement date; L portal submission duration; M portal settlement duration; N optional actual submission date; O bank received checkbox; P actual bank date; Q confirmed on; R start date; S start basis; T start-to-received workdays; U received-to-settled workdays; V settled-to-bank workdays; W total-to-bank workdays; X conclusion; Y data check.

Inputs are A:Q. Preserve row-relative formulas R:Y and all Share View formulas. Newest claims remain at the top. When sorting, sort the populated A:Q block by HR approval date descending, preserving complete input records and keeping formula rows fixed.

## Rules
- Prefer actual submission date; otherwise use HR approval as the start.
- Friday and Saturday are excluded. Start day is excluded; same-day steps take zero workdays.
- Bank paid requires checked confirmation and a valid bank date following valid settlement.
- Nonconfirmed claims older than 30 working days are counted as auto-rejected by the current backend. Insurer Reject records are also redacted.
- Paid averages include completed bank-confirmed claims only.
- Portal day counts L/M are recorded separately from calculated workday columns T:W.
- Do not infer missing dates, patient names, bank receipt or final payable from other fields.

