# Agent 流水线搭建：2026 主流方案调研

## 概述

调研「从零搭一条 agent 流水线该选什么」的逐层答案。一句话结论：**市面上的方案可以归成三类编排抽象（图/状态机、事件驱动步骤、代码即编排），三者并不互斥；持久化执行从加分项变成常见必需项；"harness"（循环 + 工具 + 上下文 + 沙箱的脚手架）成了 2026 年的新分层。** 本文件是选型地图 + 失败模式清单 + 落地骨架。

> 调研日期：2026-11-01。内容通过**直接抓取厂商官方文档、GitHub 仓库与论文原文**获得；搜索引擎不可用（见「已知坑」），故**未采用搜索结果作为依据**。这不等于"没有第三方统计"：文中所有量化数字均为**厂商自述评测或论文作者自述**，未做独立复现，也不是第三方基准排名。
>
> 可信度标注沿用本仓库规范：`[实测]` 本机跑通；`[原文]` 官方文档/论文原文直接引用；`[需验证]` 未独立核实。

## 环境前提

本文件是**调研笔记**而非可执行 runbook，无环境依赖。若要按第十二节的蓝图自己搭，最小环境是：

- Python 3.13（或你选定框架要求的版本）；TypeScript 栈用 Node 22+
- 一个能跑 agent 的开发环境（Claude Code / Codex CLI / 任一支持工具调用的客户端）
- 若要走持久化执行：本地 Docker（Temporal/DBOS/Restate 都能单机起）

## 一、四个关注点：先分清在选哪一层

这不是严格的软件分层，而是**四个该分别回答的问题**。实际产品常常跨越多个格子——LangGraph 同时涉及编排与执行，harness 同时涉及工具/上下文/权限/沙箱，eval 也不只是观测。

```
编排      谁决定下一步：图/状态机，事件驱动步骤，还是代码
          LangGraph / CrewAI Flows / ADK Graphs / MAF Workflows / LlamaIndex Workflows
          └ 代码即编排：OpenAI Agents SDK / Claude Agent SDK / Pydantic AI
执行      崩溃/重启/长等待时怎么继续：Temporal、DBOS、Prefect、Restate、图检查点
能力      如何接工具与别的 agent：MCP（agent↔工具）、A2A（agent↔agent）
观测      怎么知道它做对了：trace、eval、语义约定（LangSmith / Logfire / Langfuse / OTel）
```

**MCP 与 A2A 不竞争** [原文]：MCP 标准化「agent 连工具」，A2A（已捐给 Linux Foundation）标准化「agent 连 agent」。A2A 官方明确：**不是开发框架**，也不替代 MCP。

来源：<https://a2a-protocol.org/latest/>

## 二、方案速览

| 方案 | 语言 | 核心抽象 | 状态与恢复（**注意：这些是不同层级的保证，不能互相替代**） | 定位 |
|---|---|---|---|---|
| **LangGraph** | Py/JS | `StateGraph` 节点+边，可混确定性步骤与 LLM 步骤 | 图检查点（checkpointer，线程级）+ 跨线程 store；支持 interrupt/HITL。恢复的是**图状态**，不自动保证外部副作用幂等 | 低层编排运行时，控制粒度细，配套 LangSmith |
| **LangChain Deep Agents** | Py | harness：planning + 虚拟文件系统 + subagents + memory，跑在 LangGraph 上 | 继承 LangGraph；多租户能力来自部署层（Agent Server / Managed），不是 harness 本身 | 要 model/infra 双灵活 |
| **OpenAI Agents SDK** | Py/JS | Agent、Handoffs、Guardrails、Sessions、Tracing；Sandbox Agents | Session + 沙箱快照续跑 | 轻抽象、上手快 |
| **Claude Agent SDK** | Py/TS | 把 Claude Code 当库：内置工具、hooks、subagents、MCP、权限、Skills | Sessions 历史可恢复/分叉；dynamic workflows 可续跑。沙箱与多租户需自建 | 代码/文件类任务最省事的一体化 harness |
| **Google ADK** | Py/TS/Go/Java/Kotlin | Agent + **Graph Workflows（2.0 新增）** | 会话/记忆/工件；可一键上 Cloud Run/GKE | 多语言、企业级、A2A 原生 |
| **Microsoft Agent Framework** | .NET/Py/Go | Agents + Harness Agent + Workflows（函数式/图） | 会话状态、长任务、HITL | **AutoGen 与 Semantic Kernel 的正式继任者** |
| **CrewAI** | Py | **Flows**（`@start`/`@listen` 事件驱动）+ **Crews**（角色团队） | Flow 状态可持久化；`usage_metrics` 是 **token 成本汇总**，不是恢复能力 | 业务自动化，角色协同心智模型直观 |
| **Pydantic AI** | Py | 类型化 agent loop + capabilities/harness | **8 种持久化引擎**：Temporal/DBOS/Prefect/Restate/AWS Lambda/Absurd/pgtask/Airflow | Python 类型安全首选 |
| **LlamaIndex Workflows** | Py | 事件即类型，`@step` 按类型注解连边，启动前静态校验事件图 | 可检查点续跑 | 轻量，可独立安装 |
| **Mastra** | TS | Agent/Tool/Workflow + Studio UI | 内建 | TypeScript 栈 |
| **Agno AgentOS** | Py | "self-driving agent platform"：API/MCP/鉴权/RBAC/审批/调度/持久化队列 | 内建 durable queue（**队列持久化 ≠ 工作流续跑**） | 要把 agent 做成对外服务 |
| **AWS Strands** | Py/TS | 进程内运行，无托管控制平面 | — | 要轻、不想要托管层 |
| **Cloudflare Agents** | TS | Durable Object + Lifecycle + 工具（workspace/sandbox/browser/payments） | DO 提供持久身份与对象级恢复；跨步骤工作流语义需自行设计 | 全球边缘、每 agent 一个持久身份 |
| **eve**（Vercel） | TS | 文件系统优先、Apache-2.0 | durable（作者声明） | TS 栈，要 channel/schedule/approval |
| **Letta** | Py | 有状态 agent + memory 研究 | 内建（agent 状态持久化） | 长期记忆是核心诉求 |
| **Haystack** | Py | Agent + Pipeline + AgentTool/ComponentTool/MCPTool | 自管（管道可序列化，恢复需自行编排） | 已有 Haystack RAG 栈 |
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
| 多智能体 vs 单 agent（Anthropic 内部研究评测，Opus 4 主导 + Sonnet 4 子代理） | **+90.2%**（相对该评测上单 agent 的成绩；非"提升 90.2 个百分点"，不跨任务外推） |
| token 消耗（**基线均为普通 chat**） | 多智能体 ≈ **15×** chat；单 agent ≈ **4×** chat。换算成"多智能体/单 agent"约为 **3.75×**，但这不是作者给出的常数 |
| BrowseComp 性能方差解释力（回归分析，非因果） | token 用量 **80%**，加上工具调用数与模型选择合计 **95%** |
| 并行化收益 | 3–5 个子代理并发 + 每个子代理 3+ 并行工具调用，**该评测中**复杂查询耗时降最多 90% |
| 工具描述改写收益 | 让 agent 自己重写 MCP 工具描述后，后续任务完成时间降 40%（作者内部工具，未给样本量） |
| 起始评测规模 | **约 20 条**真实查询即可看出"可观测的差异"——这不是统计显著性的保证 |

另一篇（2026-01-23）口径更保守 [原文]：**多智能体通常比单 agent 多烧 3–10 倍 token**，很多团队搭完发现"改好 prompt 的单 agent"效果一样；只有三种情形稳定正收益——**上下文污染、可并行、需要专门化（工具/提示词/领域）**。

> **结论**：把"是否并行 / 是否上下文隔离"作为准入条件，而不是把"多智能体"当默认架构。

## 四、MAST 失败分类（可直接当 checklist）

伯克利《Why Do Multi-Agent LLM Systems Fail?》（arXiv [2503.13657](https://arxiv.org/abs/2503.13657)，v1 2025-03）[原文]：用 Grounded Theory 分析 **7 个主流 MAS 框架、200+ 条 trace**（每条平均 15,000 行），经 3 轮标注者一致性研究收敛出失败分类 MAST。

- **14 种失败模式**，3 大类。人工标注 **Cohen's κ = 0.88**（3 名标注者 × 15 条 trace，第 3 轮）；LLM-as-judge（o1 + few-shot）**准确率 0.94 / κ = 0.77**；在未参与分类构建的 MAS 上 κ = 0.79。
- **SOTA 开源 MAS 也大面积失败**：ChatDev 在 ProgramDev 上正确率仅 **33.33%**。

**完整 14 项**（括号内为论文报告的出现频率；三项合计 100.01%）：

| 类别 | 失败模式 | 频率 |
|---|---|---|
| **FC1 规格问题**（41.77%） | FM-1.1 未遵循任务要求 | 10.98% |
| | FM-1.2 未遵循角色规格 | 0.50% |
| | FM-1.3 步骤重复（回合配置僵化） | 17.14% |
| | FM-1.4 上下文丢失 | 3.33% |
| | FM-1.5 未识别任务已完成 | 9.82% |
| **FC2 智能体间失配**（36.94%） | FM-2.1 意外重置对话 | 2.33% |
| | FM-2.2 带着错误假设继续而不澄清 | 11.65% |
| | FM-2.3 任务脱轨 | 7.15% |
| | FM-2.4 隐瞒关键信息 | 1.66% |
| | FM-2.5 忽略其他 agent 的输入 | 0.17% |
| | FM-2.6 推理与行动不一致 | 13.98% |
| **FC3 任务验证**（21.30%） | FM-3.1 过早终止 | 7.82% |
| | FM-3.2 未验证或验证不完整 | 6.82% |
| | FM-3.3 验证错误 | 6.66% |

**两个反直觉结论** [原文]：

1. **"不遵循规格"不只是 instruction-following 问题**。把同一提示词写得更明确后，ChatDev 仍产出固定词表——失败来自 MAS 的**设计**而非模型理解力。仅改善角色规格 **+9.4%**，架构改造 **+15.6%**（同为 GPT-4o 与同一 user prompt）。
2. **验证器不是万能药**。ChatDev 生成的国际象棋程序通过了所有"编译/注释"检查，却存在运行时 bug（接受非法走子），因为验证器只做表面检查。

> **用法**：把上面 14 项做成 review checklist，问"这个新 agent 防住了哪一项"。注意 MAST 是**失败分类**，不是架构价值分类——它回答"会怎么坏"，不回答"该不该加"。


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

同一句 prompt、同一个模型（Opus 4.5）、同一台机器上的**三次账单对照**（原作者单案例，非对照实验）[原文]：

| 方案 | 时长 | 成本 |
|---|---|---|
| Solo（单 agent） | 20 分钟 | **$9** |
| 完整 harness v1 | 6 小时 | **$200**（约 20×） |
| 简化 harness v2（去掉 sprint，改结束时单次 QA） | 3 小时 50 分 | **$124.70** |

v2 明细：planner 4.7min/$0.46 → build 2h7/$71.08 → QA 8.8min/$3.24 → build 1h2/$36.89 → QA 6.8min/$3.09 → build 10.9min/$5.88 → QA 9.6min/$4.06。

> **口径提醒**：这是**单次案例的账单**，不是"harness 是否值得"的对照实验。没有控制输出质量、验收范围、缓存命中率与人工介入；solo 的产物更差但没有统一打分。要判断值不值，应看**每个合格交付物的成本**与成功率，而不是总花费。

**关键判断（可直接套用）** [原文]：
> "Evaluator 不是一个固定的 yes/no 决策。**当任务超出当前模型能可靠独做的边界时，它才值得成本。**"

Opus 4.6 变强后，sprint 拆分与 context reset 都成了 dead weight，被移除。

来源：<https://www.anthropic.com/engineering/harness-design-long-running-apps>

以下是 Anthropic 在同一篇里给出的四组测量，**各自独立的 A/B**，不是同一实验的四个维度 [原文]：

| 模式 | 做法 | 报告的数据（附条件） |
|---|---|---|
| **用模型已知的** | bash + text editor 两个通用工具就够 | Claude 3.5 Sonnet 靠这两个工具在 SWE-bench Verified 上达 49%（2024 年末，当时 SOTA）。技能/记忆/编程式工具调用都是这两个的组合 |
| **让模型自己编排** | 给代码执行工具，让模型写代码串联工具调用、过滤/管道，只把最终结果送进上下文 | BrowseComp 上 **45.3% → 61.6%**（Opus 4.6，开启自过滤工具输出） |
| **让模型管自己的上下文** | Skills 渐进披露、context editing、subagents 隔离 | subagents：Opus 4.6 上比最佳单 agent **+2.8%**（BrowseComp）；memory folder：Sonnet 4.5 在 BrowseComp-Plus 上 **60.4% → 67.2%**；compaction：同一预算下 Sonnet 4.5 停在 **43%**，Opus 4.5 **68%**，Opus 4.6 **84%**（BrowseComp） |
| **谨慎设边界** | 把需要安全/UX/可观测性的动作**提升为声明式工具**——bash 只暴露一个命令字符串，harness 拿不到结构化参数 | 无量化数据；属设计建议 |

> **口径提醒**：这四组数字分别来自不同的模型、不同的 benchmark 变体（BrowseComp / BrowseComp-Plus）和不同的预算设置，**不能相加或互相印证**。它们共同说明的是"这些机制在各自条件下有效"，不是"都该上"。

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

## 八、标准与治理：哪些已经定了，哪些还要自己判断

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

**结论**：这些标准值得**优先采用**，避免自造不兼容的协议；但"优先采用"不等于"必须采用"：

- 已有 HTTP API / 消息队列 / 内部函数 / 作业系统能满足需求时，引入 MCP 或 A2A 只增加鉴权、适配与版本兼容成本。收益来自**真实的互操作需求**，不是协议本身。
- AGENTS.md 是**指令约定**，不是完整 agent 配置标准；Skills 给的是**渐进披露的内容组织**，不提供流程执行、事务或恢复语义；用 OTel 也不自动消除评测平台与数据模型的绑定。
- 嵌套指令如何覆盖，取决于具体客户端的实现，不是规范保证。
- 自建的也不止业务编排——业务特有的数据边界与控制边界同样需要自己设计。

## 九、评测：三个必须知道的量化事实

1. **可靠性比单次准确率重要**。τ-bench（arXiv [2406.12045](https://arxiv.org/abs/2406.12045)）提出 **pass^k**（同一任务连续 k 次全部成功）：SOTA function-calling agent（如 gpt-4o）在**其设计的三个域上**任务成功率 **<50%**，零售域 **pass^8 < 25%** [原文]。→ 流水线要跑重复试验，不是"跑通一次就上线"。
2. **验收优先看端状态**。τ-bench 的判定方式是**比对会话结束时的数据库状态与标注目标状态**——这不是"所有系统都可以忽略过程"的论据。应区分两件事：**不要机械匹配唯一轨迹**（合理），与**不检查过程约束**（会漏掉越权、违规中间动作、成本超限、数据泄露）。Anthropic 的建议也是"端状态 + 关键检查点"。
3. **LLM-as-judge 的配置要看任务**。Anthropic 报告在其评测中，"单次调用 + 单 prompt 输出 0–1 分并给 pass/fail"比多 judge 更一致；这是**特定 rubric 与任务下的结论**，不是通用最优。MAST 的 few-shot judge（κ=0.77）也只在它自己的失败分类任务上验证过。

工具位 [原文]：

- **Inspect AI**（UK AISI）：200+ 预置 eval，支持任意外部 agent（Claude Code / Gemini CLI）、Docker/K8s/Modal 沙箱、VS Code 扩展。`pip install inspect-ai`
- **Harbor**：「任何 agent × 任何模型 × 任何任务 × 任何沙箱」。task = `instruction.md` + `task.toml` + `environment/` + `solution/` + `tests/`，`tests/test.sh` 输出 reward 到 `/logs/verifier/reward.txt`
- **promptfoo**：本地跑、可进 CI、带红队
- **Langfuse**：OTel 原生、可自托管、trace/数据集/在线评分
- **Terminal-Bench 4.0**：终端任务公开基准 [需验证 具体分数，榜单动态渲染未取到]

## 十、安全：可量化的两条防线

| 威胁 | 量化结论 | 对策 |
|---|---|---|
| **提示注入** | **CaMeL**（arXiv [2503.18813](https://arxiv.org/abs/2503.18813)）：从可信查询中显式抽出控制流与数据流，使**不可信数据无法改变程序流**；并用 capability 在调用工具时强制策略，阻止私有数据经未授权路径外泄。AgentDojo 上 **能带可证明安全性解决 77% 的任务**，无防护基线为 **84%**（后者是**任务完成率**，不是安全率） | 读不可信内容的 agent 不给写权限；gh-aw 的 `safe-outputs`、Anthropic 的"隔离读/可信写"是同一模式 |
| **过度代理 / 无界消耗** | OWASP LLM06 / LLM10（2025 Top 10） | 工具粒度最小权限、不可逆动作需确认、硬 token 预算 + 最大步数 + 超时 |
| **MCP 特有** | **Confused Deputy**（静态 client_id + 动态注册 + consent cookie → 跳过同意）、**Token Passthrough**（规范**明确禁止**） | per-client consent、`redirect_uri` 精确匹配、`state` 单次短时效、consent 之后再设 cookie |
| **沙箱隔离** | OpenAI 文档明确：`UnixLocalSandboxClient` 在 Linux **无 OS 级隔离**，在 macOS 有文件系统限制但**无网络隔离** | 隔离方案须按威胁模型选，不能凭产品名。Docker 也依赖挂载、权限、网络、宿主机暴露的具体配置；E2B 这类托管沙箱可暂停并保留文件系统与内存，但仍需自行确认租户边界 |

**AgentDojo** 提供 **97 个真实任务 + 629 个安全测试用例**（邮件、银行、旅行），可直接作为红队基线（arXiv [2406.13352](https://arxiv.org/abs/2406.13352)）。
## 十一、常见误判（不是"反模式"清单）

以下十条是**容易做错的方向**，但每条都有成立的反例。判断时看依赖关系、超时、工作区冲突和集成成本，不要当规则套。

1. **一上来选框架做绿地重写**。常见于"框架能省事"的假设；12-Factor 作者的访谈显示多数团队做到 70–80% 就撞墙。反例：确实需要持久化、多租户、审计时，自建成本更高。
2. **把确定性步骤交给 LLM 决定路径**。可复现性差、成本高。反例：路径本身随输入变化，写死反而覆盖不全。
3. **子代理任务描述含糊**（→ 重复劳动、漏项）。这一条几乎没有反例，投入产出比最高。
4. **同步等待所有子代理**。会阻塞信息流。反例：**任务本身需要全部结果才能继续时，等待就是正确的汇合条件**，问题在超时与失败处理，不在等待。
5. **大输出在对话历史里传递**（→ 丢信息 + 烧 token）。改用文件/引用传递。
6. **没有 trace 就调 prompt**。大型系统上接近必然踩坑。反例：小型本地一次性试验，加 trace 的成本高于收益。
7. **一开始就建大评测集**。会拖慢上线。反例：**有发布门槛、且改动风险高时，先建评测集是对的**。真正的错误是"永不开始"，不是"建得多"。
8. **用多智能体做紧耦合任务**。Anthropic 明确指出编码类任务的并行度低于研究类。反例：**互不重叠的批量改动确实可并行**——要验证的是依赖关系，不是任务类型名称。
9. **读不可信输入的 agent 持有写权限**。这一条建议无条件遵守。
10. **无预算上限的循环**。`while not done` 必须有最大步数、超时与全局成本上限。

## 十二、落地蓝图

### 场景 A：本地批处理流水线（最通用的一种）

适用于「一批同构任务，每个独立、可并行、结果可机器判定」的场景——批量改代码、批量迁移、批量校验、批量生成文档、批量处理数据。

```
Stage 0  initializer：把任务拆成清单（每项含验收断言）+ 一条冒烟命令
Stage 1  fan-out：每项一个 agent，独立上下文，按 schema 输出结构化结果
Stage 2  确定性验收：先跑机器可判定的检查（测试/编译/schema/比对）← 主要判据
Stage 3  执行副作用：真正落盘/部署/写库（只在此步做不可逆动作，需幂等键）
Stage 4  端状态断言：读真实系统状态确认结果（不覆盖过程约束与越权）
Stage 5  （可选）adversarial verify：仅当 Stage 2 的断言不足以判定质量时，
         才加一个独立上下文的校验 agent 对照 MAST FC1/FC2/FC3
```

> Stage 2 与 Stage 5 的边界要划清：**机器能判定的，交给确定性检查**。对可判定任务再加一个 agent 做验收，既增加成本，也可能产生与主 agent 相关的同类错误。Stage 5 只在"质量本身需要判断"时才有价值。

要点：

- **默认不引入 agent 框架**——多数本地批处理用「宿主运行时的 pipeline 原语 + 一份任务清单」就够。但如果开始需要下一节列的**执行保证**，缺的就不是 agent 框架，而是**执行基础设施**。
- 任务清单可用 JSON（模型较少改写），但它只是**验收清单**，不是运行时状态机。运行状态需要额外字段：`pending / claimed / running / awaiting_approval / failed_retryable / unknown / done / cancelled`，以及尝试次数、产物版本、验收证据、工作区归属。
- **Stage 4 不接受 agent 自述成功**，但"回读真实状态"要看断言强度：哈希需有可信预期值、接口 200 可能只代表"已接收"、测试退出码只覆盖已有测试。**还要防止被测 agent 改动验收规则本身**。
- **副作用必须幂等**。典型故障是 Stage 3 已写成功、进程在记录完成前退出；恢复时重做会重复执行，跳过会漏做。需要：操作幂等键 / 去重记录 / 可查询的执行结果 / 必要的事务或补偿。**检查点解决"从哪继续"，不解决"这件事到底做过没有"。**
- 并发写同一清单需处理覆盖与半写：文件锁、单写者、或改用数据库做原子更新。JSON 本身不提供原子性、锁或访问控制。
- 任务独立性要验证：可能改同一文件、公共依赖、生成物或数据结构；每项本地通过 ≠ 合并后通过。需要工作区隔离与集成验收。
- 预算要全局：单次 token 上限管不住并发子代理、重试、长时间工具调用与外部服务费用。还需并发上限、速率限制、截止时间，以及取消后如何阻止继续产生副作用。
- 中断可恢复：每个 Stage 的产物落盘，恢复时从最后一个**已确认完成**的 Stage 继续。

### 什么时候"不引入框架"会失效

出现以下任一需求时，「宿主原语 + 一个 JSON」通常不够（缺的是执行基础设施，未必是 agent 框架）：

- 多进程或多机领取任务，需处理重复领取与执行者失联
- 外部副作用要求去重、审计、恢复或补偿
- 等待审批、定时事件或外部回调跨越进程生命周期
- 工作流升级时，旧任务仍需按原版本继续执行
- 多租户需要配额、公平调度、隔离与统一取消
- 运维要查询运行状态、批量恢复失败任务、满足服务承诺

### 场景 B：要做成产品/服务

```
Pydantic AI（类型化 agent + capabilities）
  ├ TemporalDurability / DBOS（崩溃续跑）
  ├ Langfuse（OTel trace，静态在前动态在后保缓存命中）
  ├ promptfoo + AgentDojo（回归 + 红队）
  ├ E2B / Docker（不可信代码隔离，凭证永不入沙箱）
  └ 协议：工具走 MCP（含 Tasks 扩展处理长任务），跨组织走 A2A
```

### 选型：五个正交维度（不是一条单选路线）

这几件事**互不排斥**：图可以用代码描述，事件可以驱动状态机，探索型 agent 也可以作为图里的一个节点。分别回答，再组合：

```
D1 流程有多确定？
   高度确定 → 普通代码 / 状态机即可，不必上图框架
   部分确定 → 图/状态机（ADK Graphs / LangGraph），把确定的部分写死
   基本不确定 → harness + 动态工作流（Claude Code workflows / 宿主 pipeline 原语）

D2 控制流由谁决定？
   代码决定 → OpenAI Agents SDK / Pydantic AI / Strands
   模型决定 → harness 自己编排；用代码执行工具让模型串联工具调用

D3 需要什么执行保证？
   可重算、失败重跑即可 → 宿主原语 + 落盘产物
   有外部副作用要防重复 → 幂等键 + 去重记录（可能只需 DB）
   要跨进程等待/审批/升级时继续跑 → Temporal / DBOS / Restate
   （判断依据是可接受的丢失量、重算成本、副作用不可逆性，
     不是"运行超过几分钟"）

D4 谁来改流程？
   只有工程师 → 代码
   有非工程同学 → Dify / Coze Studio / n8n 做外壳，复杂环节回调服务

D5 需要跨边界互操作？
   已有 HTTP/队列/内部函数够用 → 不必上协议
   真的要跨团队/跨供应商 → 工具走 MCP，agent 之间走 A2A
```

### 三条建议（不是铁律）

1. **先证明需要多智能体**：上下文隔离、可并行、需专门化是三个常见正收益来源；但独立复核、不同信任边界、组织责任分离也可能构成理由。判断标准是**收益覆盖成本与新增失败面**，不是套用清单。
2. **每加一个 agent 要能说出它的理由**：MAST 的 14 项失败模式能帮你问"会怎么坏"，但它是**失败分类**，不是"该不该加"的价值分类。
3. **交付判定不要只信 agent 自述**：优先用机器可核验的断言。但端状态不是唯一标准——越权使用、违规中间动作、成本上限、数据暴露都可能看不出来，仍需过程约束与审计。

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

本文为**文档调研**，不是本机实测的 runbook。可信度分三级：

| 级别 | 含义 | 覆盖范围 |
|---|---|---|
| 已读到原文 | 抓到了包含该说法的官方页面/论文正文 | 框架能力描述、方法论、规范内容、论文数字 |
| 仅读到摘要/二手 | 只看到摘要、公告标题或第三方转述 | 少数产品状态（见下方风险项） |
| 未核实 | 明确标注 `[需验证]` | 具体基准分数、市占率类统计 |

**原文核对方式**（可复现）：

```bash
# 论文数字要查 PDF/HTML 正文，摘要页不含表格
curl -sL https://arxiv.org/pdf/2503.13657 | pdftotext - - | grep -n "41.77"
# 框架能力要看版本化文档，不是 latest 首页
curl -sL https://docs.langchain.com/oss/python/langgraph/persistence.md | head -40
```

读取过的页面清单（2026-11-01）：

- 论文：MAST 2503.13657（PDF 正文）、τ-bench 2406.12045（摘要）、CaMeL 2503.18813（摘要）、AgentDojo 2406.13352（摘要）
- Anthropic：multi-agent-research-system、building-effective-agents、effective-context-engineering、writing-tools-for-agents、effective-harnesses-for-long-running-agents、harness-design-long-running-apps、managed-agents、harnessing-claudes-intelligence、dynamic-workflows 博客
- 框架文档：LangGraph（overview/persistence）、OpenAI Agents SDK（首页/multi_agent/sandbox_agents）、Claude Agent SDK（overview/skills）、ADK（首页/graphs）、MAF overview、CrewAI（introduction/Flows）、Pydantic AI（首页/durable execution）、LlamaIndex Workflows、Mastra、Deep Agents（overview/与 Claude Agent SDK 对比）、Agno、Strands、Cloudflare Agents、eve、Letta、Haystack、DSPy（含 GEPA）、LiteLLM
- 持久化：Temporal、DBOS、Restate
- 协议：MCP 规范 2026-07-28 + Tasks 扩展、MCP 安全最佳实践、A2A、AGENTS.md、AAIF、Agent Skills、ACP、OTel GenAI 仓库
- 评测/观测：Inspect AI、Harbor、promptfoo、Langfuse、LangSmith Engine、Terminal-Bench 4.0
- 安全：OWASP LLM Top 10 2025、E2B
- 中文生态：AgentScope、Qwen-Agent、Coze Studio、Dify、n8n
- 平台公告：OpenAI AgentKit（含下线公告）、gh-aw README
- 方法论：12-Factor Agents

## 已知坑与风险项

### 方法层面

- **搜索引擎全部不可用**：xai/startpage/duckduckgo 连接失败，google/mojeek 被拦（脚本化查询墙）。所以**没有采用搜索结果作为依据**；这不等于"没有第三方统计"——本文确实只引用了厂商自述与论文自述，未做独立复现，也不是第三方基准排名。[实测 2026-11-01]
- **`huggingface.co` 不可达**：`smolagents` 文档站抓取失败，故未对其做任何能力断言。[实测]
- **Terminal-Bench 榜单是动态渲染**：抓到的排行榜表格为空，未获得具体分数。[实测]
- **`platform.claude.com` 本地区返回 "App unavailable in region"**：Managed Agents 内容全部来自其工程博客原文，未含 API 细节。[实测]
- **GitHub 首次连接常超时**：`git ls-remote` 第一次报 `Recv failure: Connection was reset` / 32s 超时，重试第 2 次即成功。推送前先探活，失败就重试而非改配置。[实测 2026-11-01]

### 内容层面（高影响断言，使用前请自行确认）

以下几条**影响面大但本文只读到单一来源**，属于最需要复核的部分：

- **AutoGen 状态**：说"已 archived"来自其 GitHub README 的归档横幅；但"停止维护"与"仓库归档"在时间点与范围上仍需以具体仓库为准。
- **OpenAI Agent Builder / Evals 下线**：来自 2025-10-06 公告页顶部的 2026-06-03 更新；**Evals 指的是平台产品界面还是其他入口没说清**，且未找到独立的下线公告页。
- **MCP 规范版本 2026-07-28**：版本存在（页面可访问），但"stateless / per-request 协商"等描述需绑定该版本，不能概括所有 MCP 实现。
- **AGENTS.md 捐赠给 AAIF**：来自 OpenAI 2025-12-09 公告；捐赠范围（格式、治理、商标）应分开看。
- **MCP Tasks 扩展**：读到的是扩展文档；其"实验性/稳定"状态与各客户端支持度需另行确认。任务状态对象不自动等于持久存储或断点续跑保证。
- **CrewAI `usage_metrics`**：是 token 统计，不是持久化能力。原方案表把它放在"持久化/续跑"列是错的，已改为"可观测/成本"语义。

### 概念层面（本文件已修正，读者勿沿用旧版）

- **保存 ≠ 恢复**：会话历史、DB 存储、沙箱快照、队列持久化、图检查点、工作流恢复解决的是**不同问题**。存了对话不代表能恢复正在执行的工具调用；存了文件系统不代表能安全重放外部写操作。
- **不是所有"多租户"都一样**：namespace / store 隔离 ≠ 租户鉴权、配额、审计。
- **"端状态是唯一标准"过强**：见第九节第 2 条。

## 外部审稿记录

2026-11-02，本文经 **gpt-6-astra**（经 kakou 线路，`/v1/responses`）独立审查一轮，返回 8812 字、49 条带严重度标注的意见。据此修订了以下内容：

| 审查意见 | 处理 |
|---|---|
| 开头"未使用搜索引擎，因此没有第三方统计"因果混淆 | 改为区分"检索方式"与"证据来源"，并说明缺失的是独立复现而非第三方统计 |
| MAST 只列 11 项却称"14 条 checklist"；FC1/FC2 明细合计 41.27%/34.44% ≠ 41.77%/36.94% | **属实**，已补齐完整 14 项（FM-1.1~3.3），合计 41.77/36.94/21.30 = 100.01% |
| CaMeL 的 77% vs 84% 把任务完成率与安全率混写 | **属实**，已改为"带可证明安全性解决 77% 任务，无防护基线 84% 是完成率" |
| 15× token 在"铁律"里丢了比较对象（基线是 chat，不是单 agent） | **属实**，已标注基线并给出 3.75× 换算，且不再作为铁律 |
| "单次 >5 分钟就必须外挂 Temporal"无依据 | **属实**，决策树改为按"丢失量/重算成本/副作用不可逆性"判断 |
| 决策树把正交维度串成单选 | **属实**，改为 D1–D5 五维检查 |
| "协议层不要自建→工具都走 MCP"结论过强 | **属实**，已改为"优先采用但非必须"，并说明引入成本 |
| "端状态是唯一标准"与"端状态+检查点"自相矛盾 | **属实**，已区分"不机械匹配轨迹"与"不检查过程约束" |
| 场景 A 的 `passes` 布尔值不足以做运行时真相源 | **属实**，已补状态机字段、幂等键、并发写、集成验收、全局预算 |
| "每个 Stage 产物落盘即可恢复"忽略副作用已发生但未记录 | **属实**，已写明"检查点解决从哪继续，不解决是否做过" |
| "多智能体只在三种情形下用"过度约束 | **属实**，已改为"三个常见正收益来源，但非充分条件" |
| 用注意力 n² 直接解释 context rot 因果过简 | **属实**，已在第六节改为"多因素"表述 |
| "$9/$200/$124.70"被当作架构效益对照 | **属实**，已标注为单案例账单，需看每合格交付物成本 |
| 20 条查询"看出显著差异"被写成统计保证 | **属实**，已改为"可观测差异，非统计显著" |

**未采纳的审查意见及理由**：

- 审稿人称"无法确认 2026 年产品状态"，建议全部降为 `[需验证]`——这些页面是**直接抓取并读到原文**的（含归档横幅、公告更新行），不是凭记忆；因此保留为已读原文，但另设"高影响断言"清单提示复核范围。
- 审稿人称"四层架构不能作为严格边界"——本文从未主张它是严格边界，仅作导航用途，未改。

审稿人说明：**未联网原文核验**，其判断基于自身知识，因此它标"存疑"的项目不等于本文有错；反向亦然。它的价值在于**指出哪里的表述会误导实施**，而非替代事实核查。

## 文件清单

| 文件 | 说明 |
|---|---|
| `README.md` | 本文件，完整调研（架构分层 / 方案表 / MAST 完整 14 项 / harness 演进 / 上下文工程 / 标准 / 评测 / 安全 / 蓝图 / 方法论 / 审稿记录） |
