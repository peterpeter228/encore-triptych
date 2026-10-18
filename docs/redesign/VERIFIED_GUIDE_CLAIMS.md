# Web3 指南独立事实核验与实现修正

核验日期：2026-10-18 UTC。检索时间窗口 01:51:12–01:53:04 UTC。三个原始指南已完整读取（175 / 202 / 151 行，共 66,618 bytes）。仅只读公开官方资料；没有注册、生成凭据、提交悬赏、连接钱包、签名或付款。这里的“可用”区分官方文档承诺与本次实际请求，不把搜索缓存当实时 API 成功。

## 优先纠正矩阵

| 指南断言 | 核验结论及实现要求 | 官方依据 | retrieved_date_utc |
|---|---|---|---|
| Superteam 目前可冲击 $5,000 USDC Open Innovation | **已结束且币种错误**。页面显示 5,000 **USDG**、Winners Announced；预定公布日 2026-03-09。实际提交截止时间 `null`（本次正文未提供），不能把公布日冒充截止日。页面要求原创、未发表、开源及有意义使用 Solana；并非指定叙事扫描器。历史样本 `actionable=false`。 | https://superteam.fun/earn/listing/open-innovation-track-agents | 2026-10-18 |
| Superteam Agent API 免密，没密钥可回填“最新悬赏” | **需 Bearer API key**。canonical host superteam.fun；GET /api/agents/listings/live?take=20；AGENT_ALLOWED/AGENT_ONLY；deadline 是下界，默认当前时间，不支持取过期任务。缺密钥返回 auth_required，items=[]，不得虚构实时快照。代理不做 KYC，奖金需人类认领；指南 80%/20% 比例证据 `null`。 | https://superteam.fun/earn/agents | 2026-10-18 |
| Jupiter /swap/v1 为最新强制 API | **过时**：官方称 Metis v1 不再积极维护，已被 Swap V2 替代。/swap/v2 的 /order+/execute 为 Meta-Aggregator；/build 返回 Router 原始指令。所有 V2 端点需 x-api-key。新实现用版本化适配器，别机械替换路径后继续用 v1 请求体。 | https://developers.jup.ag/docs/swap ; https://developers.jup.ag/docs/swap/v1/add-fees-to-swap | 2026-10-18 |
| Jupiter 填公钥与80bps即可无条件收费 | **有前提**。v1 platformFeeBps/feeAccount 仍有文档，但 feeAccount 必须是已初始化代币账户，不是任意钱包地址；ExactIn mint 可为输入/输出，ExactOut 只能输入。Token2022 收费要 V2 指令。V2 Meta-Aggregator 使用 referralAccount+referralFee，Router 使用 platformFeeBps，不能混用。配置存在≠到账验证。 | 同上两份 Jupiter 官方文档 | 2026-10-18 |
| DeFiLlama fee/revenue = 净利润；成本0=零运营成本 | **错误**。Fees 是用户支付费用，不是成交额；Revenue 扣除供给侧份额；Earnings 还扣代币激励。工资、审计等运营支出另列。缺成本数据应 `net_profit_usd=null`。严禁把 fee×1%×0.8% 算成克隆项目净利润。 | https://docs.llama.fi/analysts/data-definitions | 2026-10-18 |
| vfat Q4 2024 $1.27m 证明零成本纯利润 | DeFiLlama 的确列出该季 Gross Protocol Revenue/Gross Profit/Earnings 约 $1.27m 及 Cost of Revenue $0；这只验证该站特定口径，不证明审计后的企业净利润或运营费用为零。Clanker/o1/Snuggle 等未注明截止日的滚动30天数值本次精确匹配 `null`，不作为当前事实。 | https://investors.defillama.com/protocol/vfat?events=false&revenue=true&tvl=false ; 上述数据定义 | 2026-10-18 |
| DeFiLlama overview/fees 可匿名拉取 | 官方免费 API 确认可匿名；参数 excludeTotalDataChart/excludeTotalDataChartBreakdown；dataType=dailyFees/dailyRevenue/dailyHoldersRevenue。支持 /overview/fees/{chain}。本次 web 工具直接取 JSON 失败，运行时成功状态 `null`，需实现侧真实请求验证。 | https://api-docs.defillama.com/llms-free.txt | 2026-10-18 |
| DEX boosts/orders 可每分钟300次；Boost证明需求和利润 | boosts/profiles/orders 是 **60/min**，部分 pair/search 是300/min，不可混用。实际 orders 路径 /orders/v1/{chainId}/{tokenAddress}，不是 CheckOrdersPaid。Boost 是付费曝光，不是盈利或安全证明；本次 top/v1 返回 JSON。 | https://docs.dexscreener.com/api/reference ; https://docs.dexscreener.com/boosting ; https://api.dexscreener.com/token-boosts/top/v1 | 2026-10-18 |
| 免费 DEX API 可直接包装成收费数据服务 | **不可默认**。条款允许受限商业使用，但禁止直接竞争产品及未授权转售/向第三方提供 API 部分。先做内部研究，付费公开输出须确认数据许可和增值边界。条款页面标示更新于2023-08-18。 | https://docs.dexscreener.com/api/api-terms-and-conditions | 2026-10-18 |
| Mobula Pulse 免密高频 | GET /api/2/pulse 文档为 all plans；正式 API 使用 API key 或短期 token。Pulse WebSocket V2 限 Growth/Enterprise。demo-api 示例不等于生产无凭据。缺 key 显示未配置；具体账户配额 `null`。 | https://docs.mobula.io/rest-api-reference/endpoint/pulse-get ; https://docs.mobula.io/guides/api-key-vs-api-token ; https://docs.mobula.io/indexing-stream/stream/websocket/pulse-stream-v2 | 2026-10-18 |
| x402只需检查请求头便可主网收款 | 必须使用真实验证和结算流程，配置网络、资产、价格及可收款 payTo。CDP facilitator 要 API key；x402.org facilitator 用于免注册测试网。客户端需要兼容签名支付。返回402或看到任意header不等于收款。默认未配置、失败关闭、禁止假paid状态。 | https://docs.cdp.coinbase.com/x402/seller/quickstart ; https://docs.cdp.coinbase.com/x402/quickstart-for-sellers | 2026-10-18 |
| 0x只需recipient+bps；EIP5792保证单签原子批量 | 0x须配置 swapFeeRecipient、swapFeeBps、swapFeeToken（输入/输出币）与 API key/version。EIP5792 的原子能力需要 wallet_getCapabilities 探测及 atomicRequired；不支持时不能宣称原子清仓。 | https://docs.0x.org/docs/introduction/faq ; https://eips.ethereum.org/EIPS/eip-5792 | 2026-10-18 |
| 任何 X 链接可自动渲染交易按钮 | Blinks 要 Action-aware 客户端/钱包；客户端可要求注册/白名单。需要 actions.json、GET/POST/OPTIONS、CORS；并非 X 普遍原生无条件支持。 | https://solana.com/docs/tools/actions | 2026-10-18 |
| Muse拥有云VM/连接器，必然隐匿反爬且每周5亿token | 官方确认隔离云VM及连接器；Meta官方确认 Spark 1.3 于2026-09-02发布。**不能否认这些已证实产品事实**。但40+连接器、5亿周额度、meta_muse标识和反爬穿透承诺本次证据 `null`；不能依赖绕过网站访问限制。Muse平台当前不批准新的金融转账/下单工具。外部情报注入应为可选、鉴权、验证来源，不假装已连接Muse。 | https://muse.ai/privacy ; https://muse.ai/platform/docs ; https://research.meta.ai/blog/introducing-muse-spark-1-3 | 2026-10-18 |
| 克隆后75%–85%变现/获奖概率、6小时必成、零风险 | 证据/样本/估计方法 `null`；不能展示概率或承诺。成熟协议仍有合约、权限、报价、流动性与集成风险；获得奖项不证明产品盈利。 | 指南未提供可复核研究；上列协议文档说明实际前提 | 2026-10-18 |

## 实现契约（现在就可执行）

- 每条观测保留 source_url、retrieved_at、metric_period、metric_kind、currency、source_status、confidence_reason。不能拿检索时间代替指标期末。
- 上游失败：空数据或有原始时间的明确 stale 缓存；演示夹具只在 demo=true 模式，绝不回填成live。
- fee、revenue、volume、earnings、operating_cost、net_profit 分列。未知 null，零须来自明确观测。7天增长缺比较窗口则null；不以24h增长冒充7d。
- 排序结果是可解释研究优先级，不是投资推荐、可复制利润或确定性获客。映射真实用户痛点、成本/收费假设、原型复杂度、数据许可和验证计划。
- 收费模拟明确 gross_fee = user_assumed_volume × adoption_share × bps / 10000；未计真实基础设施/获客/协议成本时 net_profit=null。
- 导出工单可以覆盖完整后端、数据库、队列和协议适配；不需要退化为静态玩具，也不以减少测试数量作为商业质量证明。
- 安全验收保留：外部输入验证、超时/限流/失败缓存、API密钥服务端保存、交易/支付默认禁用、明确费率/滑点/风险、未签名只读模拟。真实交易、签名、资金操作和对外提交独立授权。
- 不复制“必亏100%”虚假警告、假倒计时或随机奖池承诺。真实数据密度、解释性比较和分享预览可以有强视觉质感，而不诱导高频冲动交易。

## 核验限制

本次查明官方接口契约，不代表用户账号已配置或请求配额已购置。未核验用户仓库现状、钱包/手续费到账、第三方获奖名单金额、零漏洞承诺。没有为数据源直接调用失败推断网站已停运。Superteam和DeFiLlama JSON在web工具读取失败已交实现方进行独立运行时验证。
