# Independent local browser QA — 2026-10-18

## Scope and limits
All names, captions, PNG/JPEG photos and participants were synthetic. Tests were performed in the existing cloud Chromium UI against loopback-only service. Nothing was publicly deployed, posted, sold or shared externally. This proves same-service local collaboration, not internet sharing or cross-device deployment.

Actual browser testing used two separate localStorage origins, `127.0.0.1:8765` and `localhost:8765`, in one browser profile. These are NOT three independent browser contexts. Incognito was disabled. The third participant/slot concurrency checks were API-only.

The desktop measured `window.innerWidth=1180`, document client/scroll width=1165/1165 (15px scrollbar), no horizontal overflow. Exact 320px, 375px and 1440px viewport tests were NOT RUN. Browser developer tools are explicitly organization-disabled and the supported browser API has no viewport setter; no restriction was bypassed. Windows/mobile devices and full OS restart were NOT RUN. Full app server process restart plus browser refresh WAS RUN successfully.

## Actual click workflow results
- PASS: landing renders styles and original fictional sample illustrations; create dialog opens.
- PASS: create personal card without invitations; enter Chinese title/nickname/caption, choose original synthetic PNG, save, see photo and caption.
- PASS: literal `<script>合成文本不会执行</script>` caption is displayed as text, not executable markup.
- PASS: download personal PNG from button; 1200×1859, RGB pixel standard deviation 99.71/80.85/65.28. Visually inspected image and text. Portrait cover crop is intentional; circular fixture remains circular, not distorted.
- PASS: copy invitation to browser clipboard; fragment contains invite token rather than owner key. Do not mistake the retained event ID for a secret capability.
- PASS: separate localhost storage origin opens invitation without owner controls; clicks join, uploads synthetic JPEG, saves second contribution. Only own edit button available.
- PASS: refresh persists participant state and canonicalizes to event route with current patch.
- PASS: owner clicks invitation rotation; old invitation opens revoked/nonexistent error; new invitation shows available join controls. Existing participant refresh still sees both cards and own edit/download controls.
- PASS: two-person PNG export from owner button; 2400×1817, RGB standard deviation 89.26/79.31/72.18. Clean full-page screenshot saved.
- PASS: oversized PNG selection and Save shows Chinese 8MB error, preserves typed caption and chosen filename. Previously saved photo unchanged.
- PASS: participant clicks withdrawal, confirms once; owner refresh shows 1/3 and guest no longer has edit control.
- PASS: owner clicks deletion, confirms once; returns homepage; old invitation refresh displays revoked/nonexistent. Direct local DB/media observation after completion: zero events, zero contributions, zero media files.
- PASS: create card A, go home, create card B; different event IDs and correct titles. Both cleanup deletions also passed.
- PASS: stop local uvicorn normally, restart same command, refresh card B; title/card/editor controls persist. This is full app process restart, not OS restart.
- PASS: keyboard Enter opens creation, initial focus is Close; Tab moves to title input; Escape closes and returns focus to start button.
- OBSERVED: images briefly show placeholders during fetch, then resolve; saved/autosync and export/invite feedback rendered. No exhaustive screen-reader audit performed.

## Independent API evidence (not browser claims)
26 checks passed through FastAPI TestClient: create, secret-free invitation response, unknown-key403, unauthenticated event/media401, authorized media200, upload, oversized413 and invalid400 preserving previous image, eight concurrent joins yielding exactly two201 and six409, participant cannot delete event/edit owner403, own withdrawal204 and old contribution capability403, old invite404/new200, application reinitialization event/media persistence, no-referrer header, owner deletion and old event/invite/media404, disk media cleanup.
See `independent-api-results.json`. API tests used isolated temporary data and no live capabilities in saved output. Full browser network/referrer capture and trace.zip were unavailable; security header/token separation also checked in source/API by other reviewers.

## Corrections during QA
Initial asset mount mismatch, upload-size text mismatch and CSP-incompatible inline retry handler were reported to owners and fixed. Later fixes supplied by UI/review workers were loaded before repeat-create and rotation-refresh regression. No app source edited by QA worker.

## Evidence
- evidence/landing-desktop.jpg
- evidence/personal-preview.jpg
- evidence/personal-export.png
- evidence/two-person-preview.jpg
- evidence/two-person-export.png

Screenshots are viewport/page-only without browser address bars. No live owner/view/contribution/invite capabilities were saved in these artifacts. All QA events and associated media were deleted at the end; exported synthetic artifacts intentionally retained.

## Environment history
Initial shell launch started uvicorn in an isolated command network namespace; other exec commands and cloud browser could not reach it. Standalone Chromium launch failed sandbox socket setup, and escalation failed environment setup before execution. No retry or denial bypass. The supported cloud native Terminal could see the same workspace and ran the installed Python runtime/app normally; cloud browser then reached it. A second-collaborator CUA call remained pending for approximately13 minutes and later resolved successfully without duplicate action. Native confirm dialogs caused click timeouts, but dialog state was checked before accepting; destructive actions were never blindly repeated.

## Remaining acceptance gaps
Exact mobile/1440 responsive layouts; third independent browser-context join; full browser network trace; live UI simulated response-loss recovery (covered by separate VM regressions, not this browser run); physical devices/Windows; internet deployment/sharing; actual user demand or commercial outcomes. These are not claimed passed.

## Final cosmetic recheck (01:36 UTC)
After the index.html-only SVG arrow fix, a fresh cloud browser tab loaded the landing page. Brand, How and Start arrows render visibly without missing-font boxes. Start still opens the creation dialog; Close returns to landing. Updated evidence/landing-desktop.jpg reflects this final HTML. No test data created during this check.
