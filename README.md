# Triptych Alpha

Private, local full-stack Web3 research workbench. The former static event souvenir product has been replaced in place with three stages: source signals → evidence-aware opportunity decisions → scenario and build-spec export.

## Run locally

Python 3.11+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:8765. Windows users can use `start.cmd`; Unix users can use `./start.sh`. The server binds only to loopback. Do not expose it publicly or through a tunnel. `PORT` changes the local port; `TRIPTYCH_ALPHA_DATA_DIR` optionally changes the private data directory.

Click the scan button to request real public data. An empty first run is intentional. Failed or blocked requests show source errors, not invented opportunities. A source cache is reused for five minutes; stale fallback preserves the original fetched time. Superteam/Mobula credential requirements are shown rather than bypassed. No API keys or paid accounts are required or requested by this build.

## What is implemented

- Fixed-host, bounded read-only source collection via the vendored radar package.
- Local SQLite snapshots, append-only scan-run history and imported research leads in `alpha-data/` (not old `data/`).
- Explainable evidence cards with unknowns, provenance and build gates.
- Explicit revenue-scenario arithmetic. Fees are not revenue; revenue is not net profit; paid boosts are advertising, not organic demand.
- Local Muse JSON import, strictly validated and always unverified. No public webhook or remote fetching of imported links.
- Downloadable Markdown implementation brief. This is a research artifact, not automated project creation or approval to deploy.

No signing, wallet access, trading, payments, token issuance, gambling, paid spending, account creation, public deployment or bounty submission is implemented. No revenue or commercial validation is claimed. DEXScreener-derived data is for private internal research here; review source licenses before any redistribution or product launch.

## API

See [architecture](docs/PRD_AND_ARCHITECTURE.md) and [handoff](tasks/HANDOFF.md). All endpoints require a localhost Host and same-origin browser requests. Scenario inputs are `volume`, `fee_bps`, `conversion` (captured fraction), `share` (retained revenue fraction) and `costs`, plus optional `period` and `currency`. Missing assumptions remain unknown; missing cost data keeps net profit null.

Example inert import:

```json
{"title":"Public research lead","source_refs":["https://example.org/research"],"category":"data analytics","claims":["Unverified claim for independent checking"]}
```

## Test

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/test_backend.py -q
```

Backend tests use explicit injected fixtures, never production fallback data. Browser evidence and live-run limitations are recorded separately when available. The original souvenir implementation remains recoverable from Git commit `8f41529ecb0e7589b4c874518d03587510d9c69e`; this application never deletes its prior data.

## 本轮验收结论（2026-10-18）
真实采集进程成功访问4个公共源，保存60条原始观测；按同一协议及相同链集合合并为47张研究卡，不把费用/收入当两个独立项目。来源证据位于 docs/observations/live-final-20261018.json。62项扫描器单元测试、14项CLI验收、7项实验CLI回归和19项后端测试通过。

浏览器实际点击验证了失败提示、真实历史缓存、筛选、合并指标来源、未知成本模拟、导入校验、持久化和Markdown/PNG导出；桌面及500px窗口已测。浏览器所在运行环境的实时联网仍失败，即使本轮经授权临时沿用现有代理也未成功。缓存模式通过不能替代实时联网通过。临时测试进程已停止，代理配置未打包或长期保存。

未验证：Windows启动、精确320/375px、真实钱包/收费/公开部署、Superteam鉴权接口。参见 docs/test-results/ALPHA_BROWSER_QA.md。该程序是研究工具，不是已经盈利的Web3产品。历史照片卡验收归档在 docs/history，不是当前版本的测试。
