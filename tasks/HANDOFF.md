# Triptych Alpha handoff

## Scope and current boundaries
The API is a private localhost research workbench, not a financial execution service. It serves the native three-stage UI, imports the shared radar package from `vendor/`, stores a latest scan and up to 100 displayed unverified imports in `alpha-data/alpha.sqlite3`, and keeps independent per-source caches in `alpha-data/cache/`. No previous event data is deleted or migrated.

## API contract
- `GET /api/state`: `scan` (null until first scan), `cards`, `imports`, `status`.
- `POST /api/scan`: JSON `{ "force": false }`; returns state, 409 if already scanning, 502 on unexpected collector/processing failure. Expected upstream failures are explicit per-source statuses. A processing failure retains the previous snapshot and sets `status.last_error`.
- `GET /api/opportunities/{id}`: analyzed card, including imported cards.
- `POST /api/scenario`: `{volume,fee_bps,conversion,share,costs,period,currency}`; uses explicit independent assumptions. No source fee metric is automatically converted into trading volume.
- `GET /api/opportunities/{id}/spec`: Markdown download.
- `POST /api/muse/ingest`: one strict JSON research lead; returns `{import,status:"unverified",actions_executed:0}`. Repeated identical input is idempotent. External IDs cannot replace live opportunities. Imported content is inert.
- `GET /api/health`: service health, research-only mode.

## Validation priorities
Check first-run empty state, fresh/cache/stale/error badges, original timestamps, null costs, safe rendering of imported HTML/script-like strings, Markdown export, repeated scan and import calls, persistence across restart, cross-origin/Host/body-size guards and narrow/mobile layout. Never use synthetic UI fixtures as evidence of a live collector result.

## Not done by design
No current bounty eligibility guarantee, financial integration, Muse connection, automatic build/deploy, authenticated multi-user hosting or earned-revenue claim. Source licenses and current official SDK/auth/payment contracts must be checked for any separately approved downstream product.

## Backend verification, 2026-10-18
17 contract tests passed against target FastAPI 0.141.1. A separate real API scan returned HTTP 200 and 60 analyzed observations: DeFiLlama fees/revenue and DEXScreener boosts/profiles all succeeded at 01:58:40–50 UTC; Superteam remained `needs_credentials`. The opportunity-detail and Markdown-download endpoints both returned 200. This used temporary isolated storage and did not seed product state. Later collector ranking refinements and browser behavior are validated separately.

Returned state derives freshness on every read: a stored successful/cached source beyond 300 seconds becomes `stale`, while `observation_status` records its historical status and `fetched_at` remains unchanged. Corresponding signal/card freshness follows it; `status.scan_age_seconds` exposes snapshot age. The database history is not rewritten by reads. Credential and error labels are preserved.

## Append-only scan history
Every completed collector bundle is additionally stored in `scan_runs(run_id, attempted_at, status, payload)`, including bundles where every source failed. Unexpected exceptions append a generic failure marker and retain the latest previously stored snapshot. No raw exception text, authorization headers or credentials enter the history. Reused collector IDs never overwrite an earlier run. `GET /api/runs` lists up to 100 recent summaries; `GET /api/runs/{run_id}` returns original evidence without relabeling its historical status. History contains normalized bounded collector output rather than raw upstream responses. The latest snapshot remains a convenience view, not the history store. Backend regression suite now has 18 passing tests, including two distinct runs and an unexpected-failure marker.

## Protocol metric grouping
Opportunity cards join DeFiLlama fees and revenue only when the canonical protocol URL and complete chain set match exactly, with exactly one observation of each type. Raw scan signals and historical evidence stay unchanged. Joined cards use a stable `protocol-` hash ID, `source_id: defillama_combined`, `source_ids`, `metrics_type: protocol_metrics` and per-metric provenance (source ID, original observation time, freshness and URL). Fee/revenue growth values receive distinct typed keys. The worse freshness propagates to the card; no profit is inferred. Two endpoints from one provider are not independent corroboration. DEX promotion/profile records and mismatched identities are not joined. Existing persisted cards are regenerated on the next scan. Regression suite: 19 passing tests; the saved genuine 60-observation source bundle yields 47 distinct cards.

## Final scoped acceptance
2026-10-18: complete private research milestone, not production readiness. Current source has actual4-public-API transport success,62scannerunit+14CLI+7experimentCLI+19APIchecks. Actualdesktop/500px journeys and genuine stale-cache/error paths pass. Native browser runtime fresh networking still failed after a specifically authorized one-process existing-proxy trial; helperfiles and process were removed/stopped, no persistent networkchange. Exact320/375,Windows,paid/authenticatedsources and all financial/publicactions remain unverified. See ALPHA_BROWSER_QA.md; do not reclassify its stale screenshots as fresh results.
