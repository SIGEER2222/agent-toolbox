# Qoder CLI 的 ACP 模式与 Agent 分发

## 概述

ACP（Agent Client Protocol）是「编辑器 ↔ 编码代理」的标准化协议（JSON-RPC over stdio，
定位类比 LSP）。Qoder CLI 实现了该标准：`qoder --acp` 即可把 CLI 变成 ACP Agent Server，
被 Zed / JetBrains / Neovim 等任何 ACP 客户端内嵌。本篇覆盖：启动与握手、编辑器接入配置、
以及通过 ACP Registry 分发 agent 的路径。

> 诚实声明：本篇以官方文档整理为主（标 `[docs]`），本机只有 Qoder IDE、无独立 CLI，
> stdio 握手未实测（标 `[需验证]`）；GitHub API 回退技巧为 `[实测]`。

## 协议解剖（速览）

| 层 | 方法 | 说明 |
|---|---|---|
| 初始化 | `initialize` → `authenticate` | 协商协议版本 / 能力；认证方式在 manifest 声明 |
| 会话 | `session/new`、`session/load`、`session/prompt` | 一个 session 一段对话；prompt 发起回合直到 stop reason |
| 流式回传 | `session/update`（通知） | agent_message_chunk / tool_call / plan 推给编辑器渲染 |
| 权限 | `session/request_permission` | 敏感操作阻塞等用户决定，UI 由编辑器画 |
| 反向能力 | `fs/read_text_file`、`fs/write_text_file`、`terminal/*` | 文件走编辑器缓冲区（可见 diff），命令在编辑器终端跑 |

Qoder CLI ACP 模式能力：内置工具集与 CLI 相同、Subagent、MCP（Stdio/SSE/Streamable HTTP）、
完整权限体系、上下文压缩、图像多模态；文件/终端操作走 IDE 侧。运行模式：默认 / Bypass
Permissions（等价 `--yolo`）。斜杠命令：`/init` `/memory` `/about` `/help`。`[docs]`

## 环境前提

- OS：macOS / Linux / Windows（CPU arm64/amd64；**Windows arm64 不支持**）`[docs]`
- 依赖：独立 Qoder CLI（npm 分发，Windows 入口 `%AppData%\Roaming\npm\qoder.cmd`）；
  安装命令以官网 CLI 文档页为准 `[需验证]`
- Zed ≥ 0.216（更旧版本不认 `type` 字段）`[docs]`

## 操作步骤

### 1. 登录（ACP 客户端共享 CLI 登录态）

```bash
qoder login
```

或免交互：在客户端 env 注入 `QODER_PERSONAL_ACCESS_TOKEN`
（生成地址：https://qoder.com/account/integrations ）。`[docs]`

### 2. stdio 握手自检（可选，验证 CLI 的 ACP 可用）

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientCapabilities":{"fs":{"readTextFile":true,"writeTextFile":true},"terminal":{}}}}\n' | qoder --acp
```

预期输出：一行 JSON-RPC response，`result.agentCapabilities` 非空。`[需验证]`

### 3. Zed 接入

`~/.config/zed/settings.json`（Windows：`~\AppData\Roaming\Zed\settings.json`）：

```json
{
  "agent_servers": {
    "Qoder CLI": {
      "type": "custom",
      "command": "qoder",
      "args": ["--acp"],
      "env": { "QODER_PERSONAL_ACCESS_TOKEN": "<可选>" }
    }
  }
}
```

Windows 下 `command` 用完整路径：`"~\\AppData\\Roaming\\npm\\qoder.cmd"`。`[docs]`

### 4. 分发路径

- **单编辑器手动注册**：任何 ACP 客户端都只要 spawn `qoder --acp`（stdio），配置格式各异但本质相同。
- **ACP Registry（正式渠道）**：向专门仓库 PR 一个 JSON manifest（名称/图标/版本/认证方式/
  分发起义），schema 校验后并入聚合 `registry.json`；支持 **npm 包 / 独立二进制 / uvx** 三种分发。
  支持 ACP 的客户端（Zed、JetBrains）在 IDE 内直接发现并一键安装。注册一次，全生态可用。`[docs]`
  - Qoder CLI 已收录：https://zed.dev/acp/agent/qoder-cli

## 验证方法

- Zed 的 Thread 选择器出现 "Qoder CLI" → 新建会话发一句话有流式回复 → `/about` 返回版本。`[需验证]`
- Registry：PR 合并后 `registry.json` 能查到自己的 agent，客户端内可安装。`[需验证]`

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 客户端起会话即报未登录 | ACP 模式不独立登录，共享 CLI 态 | 先 `qoder login` 或注入 token env `[docs]` |
| Zed 配置报错 unrecognized `type` | Zed ≤ 0.215.2 不认该字段 | 删掉 `type` 行 `[docs]` |
| Windows arm64 跑不了 | CLI 未发布该架构 | 用 amd64（模拟）或换机 `[docs]` |
| `raw.githubusercontent.com` 拉文件超时 | 本机网络对 raw 域名不稳 | 改走 `api.github.com/repos/<o>/<r>/contents/<path>` + `Accept: application/vnd.github.raw` `[实测 2026-10-13]` |

## 参考

- Qoder ACP 文档：https://docs.qoder.com/zh/cli/acp
- 协议官网：https://agentclientprotocol.com/ · https://zed.dev/acp
- Registry RFD：https://agentclientprotocol.com/rfds/acp-agent-registry
- Registry 上线公告：https://zed.dev/blog/acp-registry
- JetBrains ACP：https://www.jetbrains.com.cn/acp/

## 文件清单

无（纯协议操作，无附属脚本）。
