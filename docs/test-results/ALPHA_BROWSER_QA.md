# Triptych Alpha actual browser QA

Date: 2026-10-18 UTC. This report applies to the Alpha research workbench, not the historical photo-card app.

## Execution and evidence boundaries
Tests used actual cloud Chromium UI and the native cloud Terminal running the installed Python interpreter against loopback127.0.0.1:8765. No public hosting, accounts, wallets, payments, signing or trades. No network/proxy/security configuration changes. Disabled incognito/developer tools were not bypassed.

The first genuine UI Scan at02:01:05 UTC failed all four public requests with `network_error`. Superteam returned `needs_credentials`. The UI showed zero signals, source failures and no synthetic fallback. This is a verified failure-state test, NOT fresh live-source success. A separate execution environment had successfully collected real provider responses; those results are distinct from native-Terminal networking.

The parent verified and copied four original public-provider cache files byte-for-byte into the app cache, preserving their original fetch times01:55:21–01:56:18 UTC. A subsequent actual UI Scan at02:04:32 UTC again encountered network errors and correctly used those genuine observations as `stale`. All four sources and observations were labelled过期, not fresh. There were60 raw real observations. Superteam stayed需配置. No mock data was substituted for real evidence.

## Actual UI checks completed
- Initial empty state, five source-health cells, readonly/no-wallet wording, scan loading state/button disabled, source-failure recovery feedback.
- Manual Muse malformed JSON rejected with original text retained.
- Muse forbidden field rejected with original text retained.
- Explicitly labelled `SYNTHETIC QA ONLY — inert research lead` accepted only as未验证; zero actions executed; no source URL fetched by import. Synthetic text was used only to exercise import, never represented as live signal.
- Business detail separated source metrics, hypotheses, customer task, willingness-to-pay assumptions, distribution, counterevidence and build gates. Unknown costs/revenue/profit stayed unknown;0% coverage was explicitly not success probability.
- Scenario input100000 addressable daily volume,1% captured share,80bps fee,50% retained share produced gross8 and retained4. Blank costs produced unknown/null profit, not4 profit. Cost2 produced illustrative2 net, with no income prediction claim.
- Markdown and PNG export buttons downloaded files locally. Synthetic PNG1440×1140, RGB stddev24.81/26.26/25.27; visually nonblank. Later genuine-stale Jupiter PNG1440×1140, stddev24.43/26.05/25.03, UTC observation/export times and stale label visible. Latest word-wrap patch preserves English words; deliberate summary ellipsis is visible rather than text clipping.
- Search and Solana chain filter selected genuine cached Jupiter observations. Category filtering was exercised with DEX Aggregator. Final protocol fee/revenue grouping regression is documented below.
- Refresh and normal full app-process stop/restart preserved snapshot/import. This is NOT an OS restart test.
- Synthetic import was removed after verification using its exact QA-only title/ID; genuine raw observations/cache retained. Final product data must not count QA fixtures as market research.

## Responsive checks
Desktop tested at approximately1180px inner width (1165px content with scrollbar). Ordinary native-window resizing reached browser minimum500px. At500px, detail and controls reflowed; document/client widths matched with no horizontal overflow. Narrow heading orphan and canvas English word-wrap issues were reported and fixed; final screenshots reflect fixes.

Exact320/375/1440px browser viewports were NOT RUN: native Chromium minimum width500px and developer tools disabled. No physical mobile device, Windows or cross-browser claim. PNG output1440px width is not a1440px browser test.

## Artifacts (current Alpha only)
- evidence/alpha-empty.jpg
- evidence/alpha-source-failure.jpg
- evidence/alpha-synthetic-unknown-cost.jpg
- evidence/alpha-synthetic-spec.md
- evidence/alpha-synthetic-export.png
- evidence/alpha-narrow-500.jpg (intermediate, before heading refinement)
- evidence/alpha-stale-signals-500.jpg (final narrow source list)
- evidence/alpha-stale-signals-desktop.jpg
- evidence/alpha-stale-jupiter-narrow.jpg
- evidence/alpha-stale-jupiter-desktop.jpg
- evidence/alpha-stale-jupiter-spec.md
- evidence/alpha-stale-jupiter-export.png

All screenshots exclude browser address bars. Synthetic evidence is named synthetic and contains explicit QA-only label. Genuine provider metrics are historical observations, not current investment recommendations or proof of a new product's demand.

## Remaining limits
Native-Terminal fresh-live successful scan remains unverified because of actual network failures; no approved network-environment change was made. Superteam credential-backed success not run. No complete network trace or physical-device test. Commercial demand, revenue, deployability and protocol execution are not established by this QA.

## Final grouped-metric regression — 02:08 UTC
After normal server restart, another actual UI Scan recomputed cards from the genuine stale cache. The60 raw observations remain unchanged;47 grouped research cards are displayed. Search「Jupiter」plus category「DEX Aggregator」returns exactly one card. It shows24h fees$41,667 and24h revenue$41,667 as separate metric types, net profit未知, stale evidence and0% coverage/尚不可评分. Expanding「逐项指标来源与时间」shows fees fetched01:56:15 UTC and revenue01:56:18 UTC, each attributed to its respective DeFiLlama adapter and labelledstale. It explicitly says merging the same provider is not independent corroboration.

Final grouped Markdown and PNG were downloaded through actual UI buttons and visually inspected. PNG1440×1140, RGB stddev24.49/26.12/25.09, no clipping; source URL, historical observation time, stale label, unknown profit and no-transaction disclaimer remain visible. Artifacts:
- evidence/alpha-grouped-jupiter-desktop.jpg
- evidence/alpha-grouped-jupiter-spec.md
- evidence/alpha-grouped-jupiter-export.png

These final grouped artifacts supersede earlier ungrouped Jupiter screenshots/exports for current product presentation. Earlier artifacts remain chronological QA evidence. Fresh networking in the native-Terminal runtime is still NOT claimed successful. No proxy environment or machine setting was changed.

## Authorized fresh-network follow-up — 02:11 UTC (in progress)
The owner explicitly approved temporary use of the execution environment's existing proxy for this test process only. The first one-use helper launch from native Terminal failed before execution: installed Python returned `Errno 2: No such file or directory` for the helper under `/tmp`. The prior server was stopped normally. No proxy values were pasted, no network settings changed, and no helper was executed in this attempt. Awaiting a verified path visible to the native runtime before proceeding; this failure is not evidence that the proxy itself is unreachable.

### Follow-up outcome — 02:14 UTC
Parent moved the same unconsumed helper into the shared workspace. It launched successfully in native Terminal as server PID 109, with temporary existing proxy/CA environment only. Parent independently verified the one-use helper/private files were removed. Actual browser “刷新真实数据” at 02:13:28 UTC returned all four public source reasons `network_error`; source observation timestamps did not advance. The UI honestly displayed four stale sources plus Superteam requiring credentials, 47 research cards and “5 个来源未取得新鲜结果”. No fresh-network success is established even after the approved temporary environment test; the sanitized error does not establish a more specific underlying cause.

Saved `evidence/alpha-authorized-proxy-scan-failure.jpg` without browser chrome or environment values. Selecting Jupiter and downloading its still-stale evidence PNG succeeded: `evidence/alpha-authorized-proxy-stale-export.png`, 1440×1140, RGB standard deviations 24.49/26.12/25.09. These remain stale evidence, not fresh results.

Stopped PID 109 normally with Ctrl+C after testing; Terminal confirmed application shutdown complete and finished server process. No permanent proxy/network configuration or TLS-verification change was made. This follow-up supersedes earlier statements that no temporary proxy test was attempted, while preserving the original chronological failure evidence.
