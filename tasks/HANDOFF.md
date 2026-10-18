# 安可三联 · 接手说明

更新日期：2026-10-18 UTC。

## 当前范围

已实现图片＋文字纪念卡的本地源代码 MVP。技术栈是 Python 3.12+、FastAPI、SQLite、Pillow 和静态 HTML/CSS/JavaScript。没有公网部署、支付、钱包、NFT 或真实用户招募；不表示需求或盈利已验证。

## 已交付

- `app.py`：事件创建、私密读取、三人协作上限、个人修改与撤回、主办者整份删除、邀请轮换/撤销、图片处理和本地持久化。
- `static/`：前端源文件，已完成有明确范围的本地桌面实操验收，详见浏览器报告。
- `start.sh` / `start.cmd`：创建虚拟环境、安装依赖、启动本地服务。
- `requirements.txt` / `requirements-dev.txt`：运行和测试依赖。
- `tests/test_backend.py`、`docs/test-results/backend-pytest.txt`：后端测试及本次运行结果。
- `README.md`、`BACKEND.md`、`docs/PRODUCT_SCOPE.md`：用户启动、接口和范围说明。

## 验证状态

后端测试：13 项通过，最新隔离运行输出已保存；一条上游测试工具弃用警告，不是测试失败。测试使用临时目录与合成图片，不改动正在运行应用的 `data/`。

本地桌面浏览器 QA：**所列流程通过**。手机精确尺寸、第三个独立浏览器上下文、Windows 和互联网分享未测，不能写成全平台完整验收。

Windows：`start.cmd` 未在真实 Windows 环境实测。

本地 HTTP：后端在 127.0.0.1:8765 启动并返回健康检查。开发执行环境的跨命令网络连接有限制；同一次命令中启动服务并请求成功，不等于用户可以从另一台设备访问。

## 运行与数据

运行 `sh start.sh` 或 Windows 的 `start.cmd`，访问 http://127.0.0.1:8765，保持进程运行。默认单进程；不要开多个工作进程或把它直接暴露到公网。

`data/` 是运行时私人数据，`.venv/`、缓存、真实管理链接、请求重试 UUID 和测试中临时生成的能力密钥均不应进入交付源码或 Git。测试输出必须保持无密钥、无私人内容。

邀请只能用于同机浏览器/无痕窗口模拟。管理链接是访问凭证；不提供账户恢复。删除不影响已导出的图片或外部备份。邀请轮换不会踢出已有参与者。

## 下一个明确步骤

1. 查看 docs/test-results/browser-qa.md 的已测流程与未验证项；今后修改对应流程后必须重测。
2. 打包/同步仅包含源码和文档的交付，排除运行数据和密钥。
3. 如需 Windows 支持承诺，在 Windows 实际启动并运行最短创建、加入、导出、删除流程。
4. 跨设备试用或公开部署是新范围：先取得明确授权，再处理 HTTPS、托管、访问控制、配额、备份与删除政策、安全审查。当前不应部署。

## 权限请求记录

后端实现及本轮文档接手未发起 `require_escalated` 或其他审批请求。无法将其他工作流的审批编号归因到本后端任务。

## 2026-10-18 final scoped checkpoint
Desktop actual-click QA complete within documented scope; see docs/test-results/browser-qa.md. Four retry defects fixed and covered by tests/frontend_retry_regression.cjs. All synthetic browser records cleaned. Mobile exact widths, Windows and third independent browser context remain unverified. Do not label this public/commercial production readiness. Source checkpoint before evidence: 0a424d2fe354af146b1a83034039ed1e99be3865.
