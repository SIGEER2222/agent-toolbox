# Tabbit Browser tabbit-cli 浏览器自动化（WSL → Windows）

## 概述

`tabbit-cli` 把 Playwright 程序注入正在运行的 Tabbit Browser 标签页执行：新开页/接管用户已有页、DOM 操作、截图、带登录态抓页面资源。适合需要**真实浏览器环境**（登录态、JS 渲染、反爬页面）的 UI 自动化与页面数据获取。全链路 2026-10-11 在 WSL → Windows interop 环境实测通过。

## 环境前提

- OS：Windows（已装 Tabbit Browser）+ WSL 或 Git Bash；Windows 侧 PowerShell/CMD 同理
- 依赖：launcher 位于 `%LOCALAPPDATA%\Tabbit\LocalAgent\bin\tabbit-cli.exe`（浏览器未启动时会自动拉起）
  - WSL 侧等价：`/mnt/c/Users/<win用户名>/AppData/Local/Tabbit/LocalAgent/bin/tabbit-cli.exe`
  - 不确定路径就跑 `scripts/tab_run.sh`，它会用 `cmd.exe` 解析 `%LOCALAPPDATA%` 再转 wslpath
- **只调 launcher**。不要直接调浏览器安装目录下 bundle 里的 `tabbit-playwright-cli.exe`，也不要读 `endpoint.json`

## 操作步骤

设 `CLI` = launcher 路径（WSL 示例见上；以下命令块中 `$CLI` 指该路径）。

### 1. 健康检查

```bash
"$CLI" diagnose
```

预期输出：`{"activeTaskCount":0,"capabilities":{"capabilityVersion":18,...}`（本机实测 capabilityVersion 18）

### 2. 建任务、看标签页清单

```bash
"$CLI" create --task "<任务名>"
```

预期输出：JSON 含 `groups`（标签组）与 `tabs[]`（`tabId/state/title/url`）；`state=available` 表示可接管。任务名会成为标签组可见标题，用短小可读名。

### 3. 新开页执行 JS

```bash
"$CLI" nodejs --task "<任务名>" --request-id "<每次唯一的id>" <<'JS'
await page.goto("https://example.com", {waitUntil: "domcontentloaded"});
const text = (await page.locator("body").innerText({timeout: 15000})).slice(0, 200);
return {title: await page.title(), text};
JS
```

预期输出：`{"result":{"requestId":"...","value":{"title":"Example Domain","text":"..."}},"status":"succeeded",...}`

- 程序内全局对象：`page / context / browser / pages() / usePage(p) / assert / expect / artifactPath(name) / reportIssue(code) / tabbit.*`；顶层支持 `await` 与 `return`
- `return` 只收 JSON 安全值，别返回 Page/Locator；词法变量跨调用不保留，跨调用存 `globalThis`
- 结果 ≤16KiB 在 `result.value` 内联；超限给 `result.resourceId`，用 `resource --resource <id> --offset --max-bytes` 按 `nextOffset` 分页读（上限 64MB）

### 4. 接管用户已有标签页

第 2 步清单里挑 `tabId`（`currentTabId` 为 null 时按 title/url 匹配），然后：

```bash
"$CLI" nodejs --task "<任务名>" --request-id "<id>" --tab <tabId> <<'JS'
return {url: page.url(), title: await page.title()};
JS
```

`--group <groupId>` 整组接管，与 `--tab` 互斥。`available`=空闲，`owned`=本任务已占，`claimed`=别的任务占用。

### 5. 无障碍快照（先看再动手）

```bash
"$CLI" nodejs --task "<任务名>" --request-id "<id>" <<'JS'
const snap = await tabbit.observe({frames: "none", maxChars: 4000});
return snap;
JS
```

跨 iframe 用 `frames:"all"`。拿到语义结构后再用 `getByRole/getByLabel/fill/click` 原生 Playwright 操作。

### 6. 收尾释放

```bash
"$CLI" finish --task "<任务名>"
```

预期输出：`{"finished":true,"keep":true,...}`。默认 `keep:true` 保留标签页为可恢复组；`--discard` 会连标签页一起关（含已接管的用户页），只在明确要求时用。**每个任务做完必须 finish**。

## 验证方法

| 环节 | 验证命令 | 期望（2026-10-11 本机实测） |
|---|---|---|
| launcher 可用 | 步骤 1 | `capabilityVersion` 字段存在，`cliCommands` 含 create/nodejs/finish |
| 新页导航+取内容 | `scripts/tab_run.sh verify scripts/get_title.js` | `value.title="Example Domain"`，text 含 `This domain is for use in documentation` |
| 收尾 | 步骤 6 | `"finished":true`，浏览器里出现以任务名命名的标签组 |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 输出里混进 `TABBIT_PLAYWRIGHT_INSTANCE=<id>` | launcher 把实例标记打到 **stderr**；stdout 只有单行结果 JSON | 解析只用 stdout（天然干净）；若 `2>&1` 合并流则该标记占首行，需 `tail -n +2` 跳过。**注意**单行 JSON 场景下对 stdout 用 `tail -n +2` 会吞掉整个结果 `[实测 2026-10-11]` |
| `locator.xxx` 在 goto 后超时但页面其实到了 | `domcontentloaded` 后页面仍在渲染/选择器竞态 | 元素操作带显式 `timeout`，或先 `waitForSelector` `[实测]` |
| 重复 `--request-id` 不重跑 | 幂等回执 | 每次调用换新 id；脚本内 `date +%s + $RANDOM` 生成 `[实测]` |
| 退出码 75 | 请求在排队/运行中 | `receipt --wait-ms` 等原请求，别重投 `[摘自全局契约]` |
| 结果里拿不到大文本 | >16KiB 走 resourceId | `resource` 命令按 `nextOffset` 分页读 `[实测]` |
| 登录墙/CAPTCHA | 站点防护 | `reportIssue("AUTHENTICATION_REQUIRED"/"SITE_ACCESS_BLOCKED")` 并交还用户，不要硬闯 |
| 发布/支付/删除类操作 | 有现实副作用 | 停下来问用户确认再执行 |
| WSL 行内命令里 `$变量`/`$()` 消失 | 执行层预展开剥离 | JS 走 heredoc 或脚本文件；shell 逻辑一律写 `.sh` 文件再跑（见 `scripts/tab_run.sh`）`[实测]` |

## 能力速查（capabilityVersion 18）

| 需求 | 用法 |
|---|---|
| 合成粘贴 TSV/大文本 | `tabbit.pasteText(text,{format:"tsv"})`，不动系统剪贴板 |
| 等弹窗/新页 | `tabbit.triggerAndWait("popup", () => locator.click())` → `usePage(popup)` |
| 不确定跳转的导航 | `tabbit.triggerAndObserve(trigger, {timeoutMs, settleMs})` |
| 页面内带 cookie 抓资源 | `page.fetch(url,{as:"json"|"text"|"file", savePath:artifactPath(name)})` |
| 截图（仅 PNG） | `page.screenshot({fullPage:false})`，路径见 `result.nextAction.path` |
| 上传文件 | `locator.setInputFiles("/abs/path")` |
| 交互诊断 | `tabbit.actionability(locator)` / `tabbit.hitTest(...)` / `tabbit.focusInfo()` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/tab_run.sh | WSL 下自动解析 launcher 路径并执行 JS 文件：`tab_run.sh <task> <file.js>`（自动生成唯一 request-id、剥实例行） |
| scripts/get_title.js | 示例程序：新开页访问 example.com 并回传 title+正文片段 |
