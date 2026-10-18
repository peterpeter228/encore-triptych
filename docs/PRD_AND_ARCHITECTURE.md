# Triptych Alpha · Product and architecture

## Decision
Upgrade the existing Python + native browser three-stage product into an evidence-led Web3 opportunity workbench, not a static souvenir generator. Preserve the original in Git (`8f41529ecb0e7589b4c874518d03587510d9c69e`). Use the existing FastAPI stack plus SQLite rather than introducing paid accounts or deploying a public service. Full-stack means UI, business rules, persistence and real read-only integrations; it does not require a particular cloud vendor.

## Three stages
1. Signal: live public-source collection, original observation timestamps, source health and cached/stale distinctions. Fees, revenue, volume and paid promotion are different metrics. Missing data stays missing.
2. Decision: explainable opportunity scoring, useful behavioral motivations, evidence gaps and explicit revenue-scenario assumptions. Scenarios are not earnings, profit or proof of demand.
3. Build: downloadable implementation specification, verification gates and read-only integration boundaries. A plan is not a deployed product or successful bounty submission.

## Architecture and interfaces
Browser (same origin) → FastAPI → vendored radar collector / business rules → SQLite + five-minute source cache. No request can supply an outbound fetch destination. External Muse material enters only through a local JSON import: validation, unverified labeling, no execution.

- `GET /api/health`: availability and mode.
- `GET /api/runs` and `GET /api/runs/{run_id}`: recent run summaries and original append-only evidence, including failed attempts.
- `GET /api/state`: `{scan, cards, imports, status}`. Empty installation has no synthetic opportunities.
- `POST /api/scan`: `{force: false}`; return state with collector source diagnostics. A failed refresh cannot silently become mock data.
- `GET /api/opportunities/{id}`: one analyzed opportunity.
- `POST /api/scenario`: explicit numeric assumptions, validated by the business helper.
- `GET /api/opportunities/{id}/spec`: Markdown download; no automated build, deployment or trading.
- `POST /api/muse/ingest`: bounded untrusted JSON; no public webhook, remote fetching or automatic execution.

## Operational and security constraints
Loopback listener, local Host and same-origin checks, 256 KiB request limit, no inline script/style under CSP, parameterized SQLite, isolated `alpha-data` directory. No writes or cleanup to the old `data` directory. A local service is not a multi-user authentication product; do not expose it through a tunnel or reverse proxy.

Zero paid budget. No account creation, credential issuance, wallet connection, signing, payment, token issuance, automatic trading, custom custody contract, gambling mechanic, external submission or public deployment. Mature protocols still have execution, liquidity, security and regulatory risks. Candidate plans may discuss standard protocol integration only as an explicitly future, separately reviewed phase.

## Acceptance
Test real API shapes with deterministic test doubles, not silent production fixtures; preserve source failure and stale metadata; persist and reload observations; reject malformed imports, cross-origin requests and oversized bodies; browser-check empty, live/partial/error, analysis, scenario and export flows. Commercial validation remains unproven until actual users and measured demand establish it.

## Guide adoption and corrections
Adopt guide 1's in-place FastAPI/native-JS rebuild, the three-stage decision flow, real public data and local external-research import. Adopt guide 3's full-stack business and persistence scope and future versioned protocol-adapter design; do not equate that scope with an immediate Next.js/Supabase migration. Keep concise tests that protect evidence integrity and user controls. Reject fake-data fallback, unsupported income probabilities, hidden fees, fabricated urgency and instructions to remove security boundaries. Do not transplant guide text into assistant rules.

Official-source verification corrects several proposed assumptions: the cited Superteam $5,000 track is closed and denominated in USDG; it is not an available USDC payout. Current Jupiter documentation includes V2 and key requirements, so the guide's V1 snippet is not asserted as the current integration contract. x402 requires actual verification and settlement, not merely a payment-looking HTTP header. No such financial integration is activated here. See the separately supplied verified-claims report for dated source findings.
