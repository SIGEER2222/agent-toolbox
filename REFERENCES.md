# REFERENCES —— 面向 AI 的操作合集索引

核验日期：2026-10-11（逐条打开确认存在）。

这些合集与本仓库的关系：awesome 列表/注册表告诉你"有什么可用的轮子"，本仓库记录"本机实际怎么跑通"。造 runbook 前先在对应类别里查一遍，能站轮子就别重造。

## 元索引（找方向先看这里）

| 合集 | 内容 |
|---|---|
| [greasebig/awesome-agent-everything](https://github.com/greasebig/awesome-agent-everything) | 聚合 100+ 个 agent 类 awesome 仓库的元索引，按框架/技能/MCP/安全分类 |
| [michielhdoteth/awesome-ai-agent-tools](https://github.com/michielhdoteth/awesome-ai-agent-tools) | 600+ **可安装**组件目录（SKILL.md、MCP 配置、工作流、子代理），带 catalog.json，兼容 30+ 客户端 |
| [jim-schwoebel/awesome_ai_agents](https://github.com/jim-schwoebel/awesome_ai_agents) | 1500+ agent 资源大全：框架/模型/prompt/工具/课程 |
| [e2b-dev/awesome-ai-sdks](https://github.com/e2b-dev/awesome-ai-sdks) | agent SDK/框架/监控部署工具库 |
| [bradAGI/awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) | 终端编码 agent 及其 harness 目录 |

## Agent 技能/Prompt 库（现成 SKILL.md 可抄）

| 合集 | 内容 |
|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | Agent Skills 规范 + 官方示例（docx/pdf/pptx/xlsx、前端、测试等），附模板 |

## MCP 服务（三方 API 的现成通道，优先查这里）

| 合集 | 内容 |
|---|---|
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 官方参考服务：filesystem/git/github/sqlite/fetch/brave-search/memory 等 |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | 最大社区 MCP 列表（配套 glama.ai 站点） |
| [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) | 精选版 MCP 列表（配套 mcpservers.org） |
| [TensorBlock/awesome-mcp-servers](https://github.com/TensorBlock/awesome-mcp-servers) | 7700+ MCP 条目 + 可机读 registry API（按类目/传输/鉴权过滤） |
| [AlexMili/Awesome-MCP](https://github.com/AlexMili/Awesome-MCP) | 带活跃度标记的 MCP 精选 |

## 桌面 UI 自动化

| 工具 | 内容 |
|---|---|
| [microsoft/UFO](https://github.com/microsoft/UFO) | Windows AgentOS：UIA + Win32 + WinCOM 混合驱动，自然语言跨应用任务 |
| [microsoft/OmniParser](https://github.com/microsoft/OmniParser) | 屏幕截图 → 可交互元素结构化（纯视觉 GUI 感知，可配 UFO） |
| [pywinauto/pywinauto](https://github.com/pywinauto/pywinauto) | Python Windows GUI 自动化（win32/uia 两种后端） |
| [OpenAdaptAI/OpenAdapt](https://github.com/openadaptai/openadapt) | 录屏演示 → 编译成确定性可执行工作流 |
| [oculix-org/Oculix](https://github.com/oculix-org/Oculix) | SikuliX 后继：图像识别驱动任意 GUI（跨平台、无需无障碍接口） |

## 浏览器自动化

| 工具 | 内容 |
|---|---|
| 本仓库 [tabbit-browser-automation/](tabbit-browser-automation/) | Tabbit Browser + tabbit-cli：Playwright JS 注入真实标签页（本机实测） |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | LLM 驱动的浏览器任务 agent（`Saik0s/mcp-browser-use` 是其 MCP 包装） |
| [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern) | 视觉 LLM + Playwright，网页工作流自动化；自带 75+ 工具的 MCP server |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Playwright 官方 MCP server |
| [firecrawl/firecrawl-mcp-server](https://github.com/firecrawl/firecrawl-mcp-server) | 抓取 + 搜索 + 页面交互三合一 MCP |

## 资源获取 / 抓取

| 工具 | 内容 |
|---|---|
| [mendableai/firecrawl](https://github.com/mendableai/firecrawl) | URL → markdown/结构化 JSON，带搜索与浏览器沙箱 |
| Jina Reader（`https://r.jina.ai/<url>`） | 网页 → LLM 友好文本的即取即用服务，无需部署 `[需验证]` |
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | 社区维护的免费公共 API 大目录（含 MCP 条目） |
| yt-dlp | 音视频抓取（见本仓库 tvbox-video 同类工作流） |

## 三方 API 集成平台

| 工具 | 内容 |
|---|---|
| [ComposioHQ/composio](https://github.com/ComposioHQ/composio) | 1000+ 预认证工具集（GitHub/Gmail/Slack…），SDK + CLI + 每会话托管 MCP |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | 可视化工作流引擎，节点即 API 封装，大量现成模板 |

## 可执行 runbook 类（形态最接近本仓库）

| 合集 | 内容 |
|---|---|
| [unskript/Awesome-CloudOps-Automation](https://github.com/unskript/Awesome-CloudOps-Automation) | SRE 可执行 runbook（Jupyter notebook + 拖放 action） |
| [runbear-io/awesome-runbook](https://github.com/runbear-io/awesome-runbook) | runbook 软件/文档/模板索引 |

## 维护约定

- 新增条目按类别进表，标注核验日期；只列打开确认过的链接。
- 条目失效时在行尾标 `[失效 <日期>]`，不静默删行。
