# Agent 流水线搭建：2026 主流方案调研

## 概述

调研「从零搭一条 agent 流水线该选什么」的层-by-层答案。结论一句话：**编排层已收敛到三种抽象（图/状态机、事件驱动步骤、代码即编排），持久化执行从加分项变成必需项，"harness" 成了 2026 年的新分层**。本文件是选型地图 + 失败模式清单 + 落地蓝图。

> 调研日期：2026-11-01。**全部内容直连厂商官方文档/仓库/论文原文**抓取，未使用搜索引擎。因此**没有任何 star 数、下载量、市场份额等第三方统计**——文中所有量化数字均为厂商自述评测或论文自述。
>
> 可信度标注沿用本仓库规范：`[实测]` 本机跑通；`[原文]` 官方文档/论文原文直接引用；`[需验证]` 未独立核实。

## 环境前提

本文件是**调研笔记**而非可执行 runbook，无环境依赖。若要走可执行部分（第十节的落地蓝图），需要：

- Python 3.13（`%LOCALAPPDATA%\Programs\Python\Python313\python.exe`）
- 若要接 WH3 工作区：`E:\Code\WH3-modding` 的 `tools/build_pack.py`

## 一、四层架构：先分清在选哪一层

```
编排层    LangGraph / CrewAI Flows / ADK Graphs / MAF Workflows / LlamaIndex Workflows
         └ 或"代码即编排"：OpenAI Agents SDK / Claude Agent SDK / Pydantic AI
执行层    持久化 & 状态：Temporal、DBOS、Prefect、Restate、LangGraph checkpointer
能力层    工具与互操作：MCP（agent↔工具）、A2A（agent↔agent）
观测层    LangSmith / Logfire / Langfuse 类 trace + eval
```

**MCP 与 A2A 不竞争** [原文]：MCP 标准化「agent 连工具」，A2A（已捐给 Linux Foundation，TSC 含 AWS/Cisco/Google/IBM/Microsoft/Salesforce/SAP/ServiceNow）标准化「agent 连 agent」。A2A 官方明确：**不是开发框架**，也不替代 MCP。

来源：<https://a2a-protocol.org/latest/>

## 二、方案速览

| 方案 | 语言 | 核心抽象 | 持久化/续跑 | 定位 |
|---|---|---|---|---|
| **LangGraph** | Py/JS | `StateGraph` 节点+边，可混确定性步骤与 LLM 步骤 | checkpointer（线程级）+ store（跨线程），支持 interrupt/HITL | 低层编排运行时，最"可控"，配套 LangSmith |
| **LangChain Deep Agents** | Py | harness：planning + 虚拟文件系统 + subagents + memory，跑在 LangGraph 上 | 继承 LangGraph | 要 model/infra 双灵活 + 内建多租户 |
| **OpenAI Agents SDK** | Py/JS | Agent、Handoffs、Guardrails、Sessions、Tracing；Sandbox Agents | Session + 沙箱快照续跑 | 轻抽象、上手快 |
| **Claude Agent SDK** | Py/TS | 把 Claude Code 当库：内置工具、hooks、subagents、MCP、权限、Skills | Sessions 恢复/分叉；dynamic workflows 可续跑 | 最完整的 coding harness |
| **Google ADK** | Py/TS/Go/Java/Kotlin | Agent + **Graph Workflows（2.0 新增）** | 会话/记忆/工件；可一键上 Cloud Run/GKE | 多语言、企业级、A2A 原生 |
| **Microsoft Agent Framework** | .NET/Py/Go | Agents + Harness Agent + Workflows（函数式/图） | 会话状态、长任务、HITL | **AutoGen 与 Semantic Kernel 的正式继任者** |
| **CrewAI** | Py | **Flows**（`@start`/`@listen` 事件驱动）+ **Crews**（角色团队） | Flow 状态、`usage_metrics` 全量 token 汇总 | 业务自动化，心智模型直观 |
| **Pydantic AI** | Py | 类型化 agent loop + capabilities/harness | **8 种持久化引擎**：Temporal/DBOS/Prefect/Restate/AWS Lambda/Absurd/pgtask/Airflow | Python 类型安全首选 |
| **LlamaIndex Workflows** | Py | 事件即类型，`@step` 按类型注解连边，启动前静态校验事件图 | 可检查点续跑 | 轻量，可独立安装 |
| **Mastra** | TS | Agent/Tool/Workflow + Studio UI | 内建 | TS 生态首选 |
| **Agno AgentOS** | Py | "self-driving agent platform"：API/MCP/鉴权/RBAC/审批/调度/持久化队列 | 内建 durable queue | 要把 agent 做成服务 |
| **AWS Strands** | Py/TS | 进程内运行，无托管控制平面 | — | 要轻、不想要托管层 |
| **Cloudflare Agents** | TS | Durable Object + Lifecycle + 工具（workspace/sandbox/browser/payments） | DO 持久身份、可 recovery | 全球边缘、每 agent 一个持久身份 |
| **eve**（Vercel） | TS | 文件系统优先、Apache-2.0 | durable | TS 栈，要 channel/schedule/approval |
| **Letta** | Py | 有状态 agent + memory 研究 | 内建 | 长期记忆是核心诉求 |
| **Haystack** | Py | Agent + Pipeline + AgentTool/ComponentTool/MCPTool | 自管 | 已有 Haystack RAG 栈 |
| **Temporal** | 多语言 | Workflow/Activity 持久化执行 | 本体就是持久化 | 跨语言生产级底座 |
| **DBOS** | Py/TS | 加注解即可 durably execute，基于 Postgres | 库级 | 不想上 Temporal 的重量 |
| **Restate** | 多语言 | 轻量运行时，含并发限流/durable timer | 运行时级 | 要 flow control |
| **AgentScope**（阿里） | Py | Pipeline/Plan/A2A/Tracing/Eval/Studio | — | 国内部署 |
| **Qwen-Agent**（阿里） | Py | FnCallAgent/ReActChat，Qwen Chat 后端 | — | Qwen 系模型 |
| **Coze Studio**（字节） | Go+React | 可视化 workflow，Apache 2.0，运行时 Eino，画布 FlowGram | 平台托管 | 非工程同学参与 |
| **Dify / n8n** | 平台 | 可视化 agentic workflow / 节点编排（n8n 内含 LangChain 组件、MCP 一键接入） | 平台托管 | 快速验证业务闭环 |

> **AutoGen 状态提醒** [原文]：仓库 README 顶部已标 **archived / 不再维护**，官方要求新项目用 Microsoft Agent Framework，并提供迁移指南。**2026 年新项目不应从 AutoGen 起步。**

> **OpenAI Agent Builder / Evals 下线提醒** [原文]：2026-06-03 公告，**2026-11-30 起不可用**，官方建议改用 Agents SDK（要代码）或 ChatGPT Workspace Agents（要自然语言）。→ 不要押注厂商的可视化 agent 构建器。

## 三、硬数据：多智能体到底值不值

来自 Anthropic《How we built our multi-agent research system》（2025-06，2026-10 更新）[原文]：

| 指标 | 数据 |
|---|---|
| 多智能体 vs 单 agent（内部研究评测） | **+90.2%**（Opus 4 主导 + Sonnet 4 子代理） |
| token 消耗 | 多智能体 ≈ **15×** chat；单 agent ≈ **4×** chat |
| BrowseComp 性能方差解释力 | token 用量 **80%**，工具调用数 + 模型选择合计 **95%** |
| 并行化收益 | 3–5 个子代理并发 + 每个子代理 3+ 并行工具调用，复杂查询耗时**降最多 90%** |
| 工具描述改写收益 | 让 agent 自己重写 MCP 工具描述后，后续任务完成时间**降 40%** |
| 起始评测规模 | 只要 **~20 条**真实查询就能看出显著差异 |

另一篇（2026-01-23）口径更保守 [原文]：**多智能体通常比单 agent 多烧 3–10 倍 token**，很多团队搭完发现"改好 prompt 的单 agent"效果一样；只有三种情形稳定正收益——**上下文污染、可并行、需要专门化（工具/提示词/领域）**。

> **结论**：把"是否并行 / 是否上下文隔离"作为准入条件，而不是把"多智能体"当默认架构。

## 四、MAST 失败分类（可直接当 checklist）

伯克利《Why Do Multi-Agent LLM Systems Fail?》（arXiv [2503.13657](https://arxiv.org/abs/2503.13657)）[原文]：分析 **7 个主流 MAS 框架、200+ 条 trace**（每条平均 15,000 行），得出首个实证失败分类 MAST。

- **14 种失败模式**，3 大类，人工标注 **Cohen's κ = 0.88**，LLM-as-judge（o1 few-shot）**准确率 0.94 / κ = 0.77**，未见过的系统上仍达 κ=0.79。
- **SOTA 开源 MAS 也大面积失败**：ChatDev 在 ProgramDev 上正确率仅 **33.33%**。

| 类别 | 占比 | 高频模式（频率） |
|---|---|---|
| **FC1 规格问题**（系统设计/提示词缺陷） | **41.77%** | 未遵循任务要求 **10.98%**、步骤重复 **17.14%**、未识别任务完成 **9.82%**、上下文丢失 3.33% |
| **FC2 智能体间失配**（协调失败） | **36.94%** | 推理与行动不一致 **13.98%**、带着错误假设继续而不澄清 **11.65%**、任务脱轨 7.15%、隐瞒关键信息 1.66% |
| **FC3 任务验证**（质量把关失败） | **21.30%** | 过早终止 7.82%、未验证/验证不全 6.82%、验证错误 6.66% |

**两个反直觉结论** [原文]：

1. **"不遵循规格"不只是 instruction-following 问题**。把同一提示词写得更明确后，ChatDev 仍产出固定词表——失败来自 MAS 的**设计**而非模型理解力。仅改善角色规格 **+9.4%**，架构改造 **+15.6%**。
2. **验证器不是万能药**。ChatDev 生成的国际象棋程序通过了所有"编译/注释"检查，却存在运行时 bug（接受非法走子），因为验证器只做表面检查。

> **用法**：把这 14 条做成 review checklist。每加一个 agent，就问："它防住了 14 种失败模式里的哪一种？"

## 五、Harness 演进：从"加脚手架"到"减脚手架"

这是 2025→2026 最重要的范式转移，Anthropic 连续三篇工程博客讲透 [原文]。

### 5.1 长任务 harness 的四个失败模式与对策（2025-11）

| 问题 | 对策 |
|---|---|
| 想一次做完 → 上下文中途耗尽，留下半成品 | **Initializer agent**：首次会话生成 `feature_list.json`（200+ 条功能，全部 `passes: false`） |
| 后续会话看到"已有进展"就宣布完成 | 每次会话**只做一个 feature**，挑最高优先级未完成项 |
| 留下带 bug/无文档的环境 | `claude-progress.txt` + git commit + 会话开始时先跑 `init.sh` 做端到端冒烟 |
| 没测就标记完成 | 明确要求用浏览器自动化**像用户一样**验证；仅单测/curl 不够 |

细节值得抄 [原文]：**用 JSON 而不是 Markdown 存功能清单**（模型更不容易改写 JSON），并强措辞禁止删除测试。

来源：<https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>

### 5.2 三智能体架构与真实成本（2026-03）

GAN 启发的 **planner → generator → evaluator**：

- **Planner**：1–4 句 prompt 扩成完整产品规格（16 个 feature / 10 个 sprint），只定交付物不定实现细节。
- **Generator**：按 sprint 实现，每 sprint 结束自评后交 QA。
- **Evaluator**：用 Playwright MCP **像用户一样点**应用，按硬阈值逐项打分，任一项不达标该 sprint 失败并给具体反馈。
- **Sprint contract**：写代码前 generator 与 evaluator 先就"什么算 done"达成一致，用文件通信。

**成本对照（同一句 prompt）** [原文]：

| 方案 | 时长 | 成本 |
|---|---|---|
| Solo（单 agent） | 20 分钟 | **$9** |
| 完整 harness v1 | 6 小时 | **$200**（约 20×） |
| 简化 harness v2（去掉 sprint，改结束时单次 QA） | 3 小时 50 分 | **$124.70** |

v2 明细：planner 4.7min/$0.46 → build 2h7/$71.08 → QA 8.8min/$3.24 → build 1h2/$36.89 → QA 6.8min/$3.09 → build 10.9min/$5.88 → QA 9.6min/$4.06。

**关键判断（可直接套用）** [原文]：
> "Evaluator 不是一个固定的 yes/no 决策。**当任务超出当前模型能可靠独做的边界时，它才值得成本。**"

Opus 4.6 变强后，sprint 拆分与 context reset 都成了 dead weight，被移除。

来源：<https://www.anthropic.com/engineering/harness-design-long-running-apps>

### 5.3 三种 harness 设计模式（2026-04）

| 模式 | 做法 | 实测收益 |
|---|---|---|
| **用模型已知的** | bash + text editor 两个通用工具就够（Claude 3.5 Sonnet 靠它拿 49% SWE-bench Verified） | 技能/记忆/编程式工具调用都是这两个的组合 |
| **让模型自己编排** | 给代码执行工具，让模型写代码串联工具调用、过滤/管道，**只有最终输出进上下文** | BrowseComp **45.3% → 61.6%** |
| **让模型管自己的上下文** | Skills 渐进披露（只预载 YAML description）、context editing 删陈旧内容、subagents 隔离 | subagents 在 Opus 4.6 上 **+2.8%**；memory folder **60.4% → 67.2%**；compaction 预算：Sonnet 4.5 卡在 43%，Opus 4.5 68%，Opus 4.6 **84%** |
| **谨慎设边界** | 把需要安全/UX/可观测性的动作**提升为声明式工具**（bash 只给一个命令字符串，harness 无法拦截） | 不可逆动作（外部 API 调用）走用户确认 |

**缓存命中五原则**（省钱最直接的手段，缓存 token 只花 10%）[原文]：

1. 静态在前，动态在后（system prompt、tools 放前面）
2. 更新走 messages 里的 `<system-reminder>`，而不是改 prompt
3. **会话中不要换模型**（缓存按模型隔离；要便宜模型就用 subagent）
4. 工具列表变动会失效整个前缀；动态发现用 tool search（追加而不破坏缓存）
5. 多轮时把 breakpoint 移到最新消息，用 auto-caching

来源：<https://claude.com/resources/articles/harnessing-claudes-intelligence>

## 六、上下文工程：把 context 当稀缺资源

Anthropic《Effective context engineering for AI agents》（2025-09）[原文]：

- **Context rot**：token 越多，模型准确召回能力越差——**所有模型都有**，只是衰减速度不同。原因是 transformer 的 n² 注意力关系 + 训练数据里长序列本就少。
- 目标是**"能最大化期望行为的最小高信号 token 集"**，不是"尽量多给信息"。
- 三种长任务手段，各有适用面：

| 手段 | 适用 | 代价 |
|---|---|---|
| **Compaction**（摘要后就地继续） | 需要大量来回对话 | 摘要不可逆，细节会丢 |
| **结构化笔记**（`NOTES.md` / 记忆文件夹） | 有明确里程碑的迭代开发 | 需要模型自己会挑重点 |
| **子代理架构** | 并行探索收益大的研究/分析 | 每个子代理返回 1,000–2,000 token 摘要，信息压缩有损 |

- **"Just in time" 检索**：不预加载全部数据，只保留轻量标识（文件路径、查询、链接），运行时按需拉取。Claude Code 就是这个模式（`CLAUDE.md` 预载 + glob/grep 即时导航）。
- **压缩顺序**：先最大化 recall（别丢关键信息），再迭代提升 precision（删冗余）。最安全的第一步是**清理工具结果**。

来源：<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>

## 七、Managed Agents：把 agent 拆成三个可替换接口

Anthropic 2026-04 工程文章 [原文]，是"平台化"的架构答案：

```
session（append-only 事件日志，持久化）
   ↕ getEvents() / emitEvent()
harness（循环 + 工具路由，无状态，可随时重启）
   ↕ execute(name, input) → string
sandbox（容器/手机/模拟器，是 cattle 不是 pet）
```

**踩过的坑与解法** [原文]：

1. **"养宠物"陷阱**：session/harness/sandbox 塞一个容器 → 容器挂了 session 就丢；且无法调试（唯一窗口是 WebSocket 流，harness bug / 丢包 / 容器离线长得一样）。解法：**brain 与 hands 解耦**。
2. **凭证边界**：耦合时模型生成的不可信代码与凭证同容器，**一次提示注入就能读到自己的环境变量**，进而开新会话提权。解法：凭证永不进入 sandbox——Git 用初始化时注入的 remote，MCP 走代理从 vault 取 token，**harness 从不知道凭证**。
3. **性能**：brain 不在容器里后，容器按需通过 `execute()` 才创建 → **p50 TTFT 降约 60%，p95 降超 90%**。
4. **session ≠ context window**：session 是 context 的持久存储，harness 通过 `getEvents()` 取位置切片、回退几步、重读——把"不可逆的保留/丢弃决策"变成"可回查"。

> 这解释了为什么 `12-Factor Agents` 的 Factor 5（统一执行状态与业务状态）+ Factor 6（Launch/Pause/Resume）+ Factor 12（无状态 reducer）是对的：**harness 应该无状态，状态放外面。**

来源：<https://www.anthropic.com/engineering/managed-agents>

## 八、标准与治理已收敛（决定你要不要自建）

| 标准 | 状态 | 意义 |
|---|---|---|
| **MCP** | 规范版本 **2026-07-28**；已捐给 **AAIF（Linux Foundation）** | agent↔工具；JSON-RPC、stateless 请求、per-request 能力协商 |
| **MCP Tasks 扩展** | 新 | 长任务返回**持久 handle**：`working` / `input_required` / `completed` / `failed` / `cancelled`，支持断线重连、中途要输入、进度可见 |
| **AGENTS.md** | **60,000+** 开源项目；2025-12 捐给 AAIF | "给 agent 的 README"；嵌套文件就近优先 |
| **Agent Skills**（agentskills.io） | Anthropic 开源、开放标准 | `SKILL.md` + scripts/references/assets；**渐进披露**三阶段（发现→激活→执行） |
| **A2A** | 已捐给 Linux Foundation | agent↔agent，明确**不替代 MCP**、不是开发框架 |
| **ACP**（Agent Client Protocol） | 编辑器↔agent，复用 MCP 的 JSON 表示 | 类似 LSP 之于语言服务器 |
| **OTel GenAI 语义约定** | 已迁到独立仓库 `semantic-conventions-genai`（含 agent spans、MCP、provider 专属约定） | 可观测性不再厂商绑定 |
| **AAIF 工作组** | Accuracy & Reliability、Identity & Trust、Observability & Traceability、Security & Privacy、Workflows & Process Integration 等 | 未来 12 个月规范方向 |

**结论**：**协议层不要自建**。工具走 MCP，跨组织 agent 走 A2A，agent 配置走 AGENTS.md，可复用流程走 Skills，trace 走 OTel。自建的只应是**业务编排**。

## 九、评测：三个必须知道的量化事实

1. **可靠性比单次准确率重要**。τ-bench（arXiv [2406.12045](https://arxiv.org/abs/2406.12045)）提出 **pass^k**（k 次全成功）：即使 gpt-4o 这类 SOTA function-calling agent，任务成功率 **<50%**，零售域 **pass^8 < 25%** [原文]。→ 流水线要跑重复试验，不是"跑通一次就上线"。
2. **评测看端状态，不看过程**。τ-bench 直接**比对会话结束时的数据库状态与标注目标状态**；Anthropic 也说改状态的 agent 应做"端状态评测 + 关键检查点"，而不是逐轮打分。
3. **LLM-as-judge 用单次调用 + 0–1 分 + pass/fail 最稳定**（Anthropic 实测多 judge 反而一致性更差）；MAST 的 few-shot 版 judge 达 κ=0.77，可直接复用其 prompt 结构。

工具位 [原文]：

- **Inspect AI**（UK AISI）：200+ 预置 eval，支持任意外部 agent（Claude Code / Gemini CLI）、Docker/K8s/Modal 沙箱、VS Code 扩展。`pip install inspect-ai`
- **Harbor**：「任何 agent × 任何模型 × 任何任务 × 任何沙箱」。task = `instruction.md` + `task.toml` + `environment/` + `solution/` + `tests/`，`tests/test.sh` 输出 reward 到 `/logs/verifier/reward.txt`
- **promptfoo**：本地跑、可进 CI、带红队
- **Langfuse**：OTel 原生、可自托管、trace/数据集/在线评分
- **Terminal-Bench 4.0**：终端任务公开基准 [需验证 具体分数，榜单动态渲染未取到]

## 十、安全：可量化的两条防线

| 威胁 | 量化结论 | 对策 |
|---|---|---|
| **提示注入** | **CaMeL**（arXiv [2503.18813](https://arxiv.org/abs/2503.18813)）：显式分离控制流与数据流（不可信数据**永远不能影响程序流**）+ capability 限制外泄，AgentDojo 上 **77% 任务可证明安全**（无防护 84%） | 读不可信内容的 agent 不给写权限；gh-aw 的 `safe-outputs`、Anthropic 的"隔离读/可信写"是同一模式 |
| **过度代理 / 无界消耗** | OWASP LLM06 / LLM10（2025 Top 10） | 工具粒度最小权限、不可逆动作需确认、硬 token 预算 + 最大步数 + 超时 |
| **MCP 特有** | **Confused Deputy**（静态 client_id + 动态注册 + consent cookie → 跳过同意）、**Token Passthrough**（规范**明确禁止**） | per-client consent、`redirect_uri` 精确匹配、`state` 单次短时效、consent 之后再设 cookie |
| **沙箱隔离** | OpenAI 明确：Unix-local 在 Linux **无 OS 级隔离**、macOS **无网络隔离** | 不可信代码必须 Docker/托管沙箱（E2B 可暂停并保留文件系统+内存） |

**AgentDojo** 提供 **97 个真实任务 + 629 个安全测试用例**（邮件、银行、旅行），可直接作为红队基线（arXiv [2406.13352](https://arxiv.org/abs/2406.13352)）。

## 十一、反模式清单（按踩坑频率）

1. 一上来选框架做绿地重写（→ 撞 80% 质量墙后重写）。
2. 把 DAG 扔掉、全交给 LLM 决定路径（确定性步骤应写死）。
3. 子代理任务描述含糊（→ 重复劳动、漏项）。
4. 同步等待所有子代理（→ 单点阻塞）。
5. 大输出在对话历史里传递（→ 丢信息 + 烧 token）。
6. 没有 trace 就调 prompt。
7. 一开始就要建 100+ 用例的评测集（→ 永远不上线）。
8. 用多智能体做紧耦合任务（编码并行度低，Anthropic 明确说这不是好场景）。
9. 读不可信输入的 agent 持有写权限。
10. 无预算上限的循环（`while not done`）。

## 十二、落地蓝图

### 场景 A：本地批处理（例：WH3 MOD 流水线）

```
Stage 0  initializer：生成 feature_list.json（改动项清单，全 false）+ 冒烟脚本
Stage 1  fan-out：每个改动项一个 agent（独立上下文，schema 结构化输出）
Stage 2  adversarial verify：每项配对抗校验 agent（对照 MAST FC1/FC2/FC3）
Stage 3  打包：tools/build_pack.py <mod> --deploy
Stage 4  端状态断言：读 state.db 确认新 mod_id 在 playset 中 ← pass/fail 的唯一标准
Stage 5  （可选）evaluator：只在"超出模型可靠边界"的改动上启用
```

要点：不引入框架（用现成 agent 运行时原语）；`feature_list.json` 是唯一真相源，agent 只能改 `passes` 字段；单次运行设 token 上限 + 最大步数。

### 场景 B：要做成产品/服务

```
Pydantic AI（类型化 agent + capabilities）
  ├ TemporalDurability / DBOS（崩溃续跑）
  ├ Langfuse（OTel trace，静态在前动态在后保缓存命中）
  ├ promptfoo + AgentDojo（回归 + 红队）
  ├ E2B / Docker（不可信代码隔离，凭证永不入沙箱）
  └ 协议：工具走 MCP（含 Tasks 扩展处理长任务），跨组织走 A2A
```

### 选型决策树

```
Q1 流程是否高度确定？
 ├ 是 → 图/状态机（ADK Graphs / LangGraph / 手写 12-factor 状态机）
 └ 否 → Q2
Q2 是否需要"模型自己写编排"（探索型、批量未知）？
 ├ 是 → harness + 动态工作流（Claude Code workflows / 自带 pipeline 原语）
 └ 否 → 代码即编排（OpenAI Agents SDK / Pydantic AI / Strands）
Q3 单次运行 > 5 分钟或需要人等待？
 └ 是 → 必须外挂 Temporal/DBOS（不要自己写重试）
Q4 有非工程同学要改流程？
 └ 是 → Dify / Coze Studio / n8n 做外壳，复杂环节回调服务
Q5 要跨团队/跨供应商互操作？
 └ 是 → 工具走 MCP，agent 之间走 A2A
```

### 三条铁律

1. **先证明需要多智能体**：只在"上下文污染 / 可并行 / 需专门化"三种情形下用。多智能体烧 15× token，单 agent 4×。
2. **每加一个 agent，就要能说出它防住了 MAST 14 种失败模式里的哪一种**，否则删掉。
3. **交付判定用端状态断言，不用 agent 的自述**。

## 十三、方法论参考

### 12-Factor Agents（工程规范）

1. 自然语言 → 工具调用　2. **自己拥有 prompt**　3. **自己拥有上下文窗口**　4. 工具就是结构化输出　5. **统一执行状态与业务状态**　6. Launch/Pause/Resume 用简单 API　7. **用工具调用来联系人**（HITL 不要外挂）　8. **自己拥有控制流**　9. 把错误压缩进上下文　10. **小而专注的 agent**　11. 从任何地方触发　12. **把 agent 做成无状态 reducer**

作者的核心论点 [原文]：访谈 100+ 团队，路径几乎都是"选框架 → 做到 70–80% → 发现不够 → 逆向框架 → 重写"。
> "最快拿到好结果的方式，是把 agent 的模块化概念嵌进你已有的产品，而不是绿地重写。"

来源：<https://github.com/humanlayer/12-factor-agents>

### Anthropic 六种可复现编排模式

classify-and-act、fan-out-and-synthesize、adversarial verification、generate-and-filter、tournament、loop-until-done。

来源：<https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code>

### 工具设计（写工具的 40% 杠杆在这里）

Anthropic《Writing effective tools for agents》（2025-09）[原文]：

- **别包 API，要包工作流**：`schedule_event` 而不是 `list_users` + `list_events` + `create_event`；`search_logs` 而不是 `read_logs`。
- **命名空间**：`asana_projects_search` / `asana_users_search`，前缀 vs 后缀对评测有非平凡影响。
- **返回高信号**：把 UUID 解析成有语义的名字能显著降幻觉；提供 `response_format` enum（detailed 206 token vs concise 72 token，约 1/3）。
- **token 效率**：分页/范围/过滤/截断 + 明确默认值；Claude Code 默认把工具响应限制在 **25,000 token**。
- **错误响应要可行动**：不要给 traceback 或错误码，给"该怎么改"的示例。
- **Poka-yoke**：SWE-bench agent 在相对路径上出错，改成强制绝对路径后模型零失误。

来源：<https://www.anthropic.com/engineering/writing-tools-for-agents>

## 验证方法

本轮为**文档调研**，验证方式是原文对照而非本机运行：

```bash
# 抽查任一条结论是否为原文所述（示例：MAST 分类占比）
# 打开 https://arxiv.org/abs/2503.13657 搜索 "41.77" 应命中 FC1 占比
```

已核实原文（2026-11-01 直连抓取）：

- 论文：MAST 2503.13657、τ-bench 2406.12045、CaMeL 2503.18813、AgentDojo 2406.13352
- Anthropic：multi-agent-research-system、building-effective-agents、effective-context-engineering、writing-tools-for-agents、effective-harnesses-for-long-running-agents、harness-design-long-running-apps、managed-agents、harnessing-claudes-intelligence、dynamic-workflows 博客
- 框架文档：LangGraph（overview/persistence）、OpenAI Agents SDK（首页/multi_agent/sandbox_agents）、Claude Agent SDK（overview/skills）、ADK（首页/graphs）、MAF overview、CrewAI（introduction/Flows）、Pydantic AI（首页/durable execution）、LlamaIndex Workflows、Mastra、Deep Agents（overview/与 Claude Agent SDK 对比）、Agno、Strands、Cloudflare Agents、eve、Letta、Haystack、DSPy（含 GEPA）、LiteLLM
- 持久化：Temporal、DBOS、Restate
- 协议：MCP 规范 2026-07-28 + Tasks 扩展、MCP 安全最佳实践、A2A、AGENTS.md、AAIF、Agent Skills、ACP、OTel GenAI 仓库
- 评测/观测：Inspect AI、Harbor、promptfoo、Langfuse、LangSmith Engine、Terminal-Bench 4.0
- 安全：OWASP LLM Top 10 2025、E2B
- 中文生态：AgentScope、Qwen-Agent、Coze Studio、Dify、n8n
- 平台公告：OpenAI AgentKit（含下线公告）、gh-aw README
- 方法论：12-Factor Agents

## 已知坑

- **`web_search` 全部 provider 失败**：xai/startpage/duckduckgo 连接失败，google/mojeek 被拦（脚本化查询墙）。因此本文件**没有任何 star 数、下载量、市场份额、第三方采用率统计**；所有量化数字均为厂商自述或论文自述，不是独立第三方基准。[实测 2026-11-01]
- **`huggingface.co` 不可达**：`smolagents` 文档站抓取失败，故本文件未对其做任何能力断言。[实测]
- **Terminal-Bench 榜单是动态渲染**：抓到的排行榜表格为空，未获得具体分数。[实测]
- **`platform.claude.com` 本地区返回 "App unavailable in region"**：Managed Agents 内容全部来自其工程博客原文，未含 API 细节。[实测]
- **GitHub 首次连接常超时**：`git ls-remote` 第一次报 `Recv failure: Connection was reset` / 32s 超时，**重试第 2 次即成功**。推送前先 `git ls-remote --heads origin` 探活，失败就重试而非改配置。[实测 2026-11-01]
- **区分"文档能力"与"生产采用"**：本文件描述的是各框架文档声明的能力，不代表它们在生产环境的稳定性。Anthropic 的数据也明确说"多智能体通常用在单 agent 会更好的场景"。

## 文件清单

| 文件 | 说明 |
|---|---|
| `README.md` | 本文件，完整调研（架构分层 / 方案表 / MAST 失败分类 / harness 演进 / 上下文工程 / 标准 / 评测 / 安全 / 蓝图 / 方法论） |
