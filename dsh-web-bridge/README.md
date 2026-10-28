# dsh-web-bridge — Devin/脚本 ↔ DSH web 会话双向桥（tabbit 驱动真实浏览器）

## 概述

程序化地向一个 **dsh web**（`http://127.0.0.1:3080`）会话发消息、等回复、读转写。
用例：让本地 agent（Devin CLI、脚本、cron）跟 web 宿主里的会话做正式协作对话。

为什么必须走浏览器：`dsh --profile acp` 的 `session/resume` 和 `headless --session-id`
都被宿主持有的**内核命名信号量写锁**拒绝（`session is already owned by an active
write handle`）。读无锁（`session.v4.jsonl.zstd`），写只能过宿主自己的通道——
就是用户浏览器里那条 typert 连接。

## 环境前提

- OS：Windows（已装 Tabbit Browser，已登录 `127.0.0.1:3080` 的 dsh web）
- `tabbit-cli.exe`：`%LOCALAPPDATA%\Tabbit\LocalAgent\bin\tabbit-cli.exe`（`TABBIT_CLI` 可覆盖）
- Windows Python ≥3.10 + `zstandard`（`pip install zstandard`）
- WSL 侧调用：走 `wpy` 封装（Windows python），不要 WSL 内 python（读不到 `%USERPROFILE%`、跑不了 tabbit）

## 操作步骤

### 1. 列出 dsh 相关标签页 / 解析会话引用

```powershell
python scripts/dshpeer.py tabs
python scripts/dshpeer.py resolve 6c2a0508
python scripts/dshpeer.py resolve "http://127.0.0.1:3080/?s=session-<uuid>"
```

预期输出：tabs 打 `tabId/state/title/url`；resolve 打 `{"sid","transcript"}`。

### 2. 读回复（无锁，随时可用）

```powershell
python scripts/dshpeer.py read <ref>
python scripts/dshpeer.py wait <ref> --timeout 300
```

### 3. 发消息 / 一问一答

```powershell
python scripts/dshpeer.py send <ref> -f msg.txt --ws ai-workspace
python scripts/dshpeer.py ask <ref> -f msg.txt --ws ai-workspace --timeout 600
```

- `<ref>` = 完整 URL / `session-<uuid>` / uuid 前 8 位。
- `--ws` = 工作区显示名（会话不在已开标签页时需要，用于工作区下拉点选）。
- **会话必须已挂载**（在首页会话列表里或已有标签页开着）。未挂载的冷会话返回
  `not-on-session`——先让用户/自动化在 UI 里点开一次。
- 发送前等空闲（composer disabled 期间等 `--busy-wait` 秒），发送后双重校验：
  composer 清空 + 转写出现以消息文本开头的 `user/message`。

### 4. 开新会话

```powershell
python scripts/dshpeer.py new --ws ai-workspace -f first_msg.txt --wait 180
```

返回 `{"ok":true,"sid":"session-…"}`；`--wait` 顺带等第一条回复打印。

## 验证方法

| 环节 | 命令 | 期望（2026-10-28 本机实测） |
|---|---|---|
| 会话创建 | `new --wait 180` | `ok:true` + 回显 assistant 回复（实测返回 `OK`） |
| 发送到已挂载空闲会话 | `send <mounted> -f ping.txt` | `sent:true, composerEmpty:true, transcriptConfirmed:true` |
| 等回复 | `wait <ref>` | `{"done":true}` 且 `read` 返回对端应答（实测 `PONG`/`PONG2`） |
| 发送到运行中会话 | `send <running>` | composer 可编辑则入队发送成功；只读挂载则 `busy-timeout` |
| 未挂载会话 | `send <cold-ref>` | `{"sent":false,"error":"not-on-session"}`——不误发 |

实测矩阵（同日）：`new`/`send`/`wait`/`read`/`ask` 五个子命令各自端到端通过；
3 个真实已挂载会话完成「发→转写确认→turn 结束→读到应答」整回合。

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| `?s=<sid>` 导航后进的是只读视图（composer `contenteditable="false"`） | 深链打开的是 viewer 挂载 | **可靠可写路径 = 首页会话列表行点击**（`div.YDXeBa_sessionRow` 逐行 click 比对 URL sid）；工具已内置 `[实测]` |
| 冷会话 `?s=` 直接弹回首页 | 未挂载会话不在 web 注册表 | 列表行点击挂载；未列出则 `not-on-session`，别硬发 `[实测]` |
| 会话列表行没有 href/data-id，搜索框 `fill`/`insertText` 不触发 React 搜索 | 前端实现 | 只能**遍历行点击**再对 `page.url()` 的 sid（工具就是这么做的）`[实测]` |
| Enter 不发送 | 发送靠 `button[aria-label="发送消息"]`（图标键无文本） | 点该按钮；`aria-label` 优先于 has-text `[实测]` |
| composer disabled 未必是"在跑" | 转空闲但自动化/只读挂载同样 disabled | 等待 `--busy-wait`；超时返回 `busy-timeout`（不伪造成功）`[实测]` |
| `?s=` 导航 spawn **新 Playwright page** 而非原地换 URL | SPA 行为 | `pages()` 扫 sid + `usePage()` 换绑 `[实测]` |
| 多次调用累积 spawned page → `N owned Playwright Pages` 超时 | 任务持有量爆炸 | **每次命令开头 `finish --task`（keep:true）清场** `[实测]` |
| `EPERM rename receipt` 偶发失败 | LocalAgent receipt 文件锁竞态 | JS 可能已执行——必须靠转写/composer 副作用自验，勿看 status 就重发 `[实测]` |
| 绑定后标签页被导航到别的会话 | 用户浏览器是活的 | 插字前+点发送前**三重 `page.url()` 断言**；漂移即清草稿中止（实测救过一次误发）`[实测]` |
| 注入 JS 里中文全花 | tabbit-cli 按 cp936 解 stdin | 载荷必须纯 ASCII：`json.dumps` 自带 `\u` 转义；JS 字面量手写**单层** `\uXXXX`（写成 `\\u` 就变字面量，血的教训）`[实测]` |
| 会话列表只显示已挂载子集（~8 行+分组） | 不列 store 全量 | 未挂载会话：让 UI 先打开一次，或 `new` 新建 `[实测]` |
| 列表点击 vs `?s=` 结果不同 | 行点击=交互挂载（可写），`?s=`=viewer（只读） | 发送只走行点击路径 `[实测]` |
| `wpy`/`wtabbit` 封装名必用 | WSL 直跑 exe 报 Exec format error | 固定封装在 `devin-env\bin` `[实测]` |
| 跨窗口标签 `CROSS_WINDOW_CLAIM` | 标签被挪到别的窗口 | 绑候选页循环跳过 `[实测]` |
| `document` 未定义 | 页内 JS 全局只有 `page/context/pages()/usePage` | DOM 查询走 `page.evaluate`/`locator` `[实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/dshpeer.py | 完整 CLI：tabs/resolve/read/wait/send/ask/new；含转写容错读、行点击挂载、三重 URL 断言、转写发送回执校验、nofocus guard、锁文件 |
