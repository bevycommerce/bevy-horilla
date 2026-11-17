# One administrator validation step

Employee submits → HR / Super Admin validates → Approved & unpaid → Reserved → Synced → Paid.

Rejected and Needs Information remain separate. Either authorized administrator can decide; a second click cannot decide the same submitted version again. Employees and legacy Manager roles cannot validate or read unrelated claims. Self-approval is blocked even for Super Admin. No colleague delegation.

Version 5 migrates pending legacy colleague reviews to HR directly, retaining old decisions only as historical evidence. It preserves paid values, reservations and HR-approved records. Missing HR approval holds an unpaid record out of payout. Production must enforce these rules with server authorization, immutable identity and transactional version checks.
