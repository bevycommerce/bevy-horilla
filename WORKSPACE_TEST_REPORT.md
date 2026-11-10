# Smart Employee Workspace - Test Report

Status labels: Implemented / Tested successfully / Partially tested / Not tested (reason).

## Phase 0 baseline (2026-11-10, before any Smart Workspace code)

- Where: inside the running `horilla-hr-web-1` container, temporary test database (real data untouched).
- Command: `python manage.py test <Makefile SMOKE_LABELS> --noinput --verbosity=1`
- Settings at the time: TIME_ZONE=Asia/Kolkata (switched to Asia/Dhaka right after the run).
- Result: **2450 tests, 1 failure, 2 errors, 1 expected failure. Run time 26.5 min.**
- Full log: `D:\HR Portal\migration-tools\baseline-tests.txt` (kept outside the repo).

| Test | Result | Cause | Caused by Smart Workspace? |
|---|---|---|---|
| `base.tests.test_demo_date_windows.DemoDateWindowTests.test_inventory_covers_every_sidebar_app` | FAIL | The owner's custom `expense` app is a sidebar app but is not listed in the demo-date inventory the test checks. | No (pre-existing, owner customization) |
| `recruitment.tests.test_survey_attachment_extension...test_an_ordinary_document_is_still_accepted` | ERROR | Test setUp creates an "applied" stage that recruitment creation already makes, hitting `unique_special_stage_type_per_recruitment`. Recruitment models are unmodified locally (only `recruitment/filters.py` changed). | No (pre-existing, upstream test issue) |
| `recruitment.tests.test_survey_attachment_extension...test_an_uploaded_python_file_is_rejected` | ERROR | Same as above. | No (pre-existing, upstream test issue) |

Rule for later phases: these 3 are the known baseline. Any other failing existing test after a Smart Workspace change is a regression and must be fixed.

## Time zone switch (2026-11-10)

- Local `.env` (git-ignored) now contains only `TIME_ZONE=Asia/Dhaka`.
- Verified in both containers after restart: `settings.TIME_ZONE=Asia/Dhaka`, `timezone.localtime()` = +06:00 and matches the PC clock. Website health check OK.
- Existing test data was not converted (owner decision: test data only).
