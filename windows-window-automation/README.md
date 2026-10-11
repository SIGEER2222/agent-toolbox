# Windows 窗口自动化：后台/非侵入操作矩阵（PrintWindow / UIA / Win32 消息）

## 概述

目标：**不干扰用户正在做的工作**——目标窗口被其他窗口盖住、不是前台、甚至最小化时，仍能完成读写与点击；全程不抢焦点、不动鼠标、不置顶。三条技术路线按优先级实测：

1. **UIA（pywinauto `backend='uia'`）**：读写控件值（ValuePattern）、触发按钮（InvokePattern）、枚举控件树。对原生/标准控件可靠。
2. **Win32 消息**：`WM_SETTEXT` 写文本、`BM_CLICK` 点原生按钮、`WM_CLOSE` 关窗、`WM_CHAR` 逐字符注入（看控件实现）。
3. **PrintWindow**：窗口被遮挡时截出完整画面做视觉校验（`PW_RENDERFULLCONTENT`=2）。

2026-10-11 本机（Win11 24H2 + Python 3.13 + WSL 调用）逐项实测，结论见能力矩阵——**不是所有"窗口还在"就等于"能操作"，自绘控件和锁屏是两个硬边界**。

## 环境前提

- OS：Windows（本机 Win11 24H2）；WSL 下通过 `python.exe` interop 调用同一批脚本
- 依赖：Windows Python 3.13+ + `pip install pillow pywinauto`
  - 坑：pywinauto 在清华镜像拉不到，走官方源：`pip install pywinauto -i https://pypi.org/simple` `[实测]`
- 演示目标：`scripts/demo_target.pyw`（tkinter `WADemo`，按钮点击写 `%TEMP%\wademo_clicks.log` 做副作用验证）

## 能力矩阵（全部实测，非推断）

| 目标状态 | 操作 | 结果 | 证据 |
|---|---|---|---|
| 被完全遮挡 | `PrintWindow` 截图 | ✅ 完整窗口画面 | `wa_occ.png` |
| 被遮挡 | UIA `SetValue`/`get_value` → 运行对话框 Edit | ✅ 写入 'calc' 并读回 | `set ok` / `'calc'` |
| 被遮挡 | UIA `Invoke` → 原生按钮 | ✅ 触发真实副作用 | 运行框点"确定"→ Calculator 窗口出现 |
| 被遮挡 | `SendMessageW(BM_CLICK)` → 原生按钮 | ✅ | winver"确定"→对话框销毁 `IsWindow=False` |
| 被遮挡 | `PostMessageW(WM_CHAR)` → **tk 自绘控件** | ❌ 3/3 次文本未落入 | 见坑#3 |
| 最小化 | `PrintWindow` | ❌ 只截到标题栏残片 | `wa_min.png` |
| 最小化 | `WM_CHAR` → tk 控件 | ❌ 未落入（tk 内部焦点模型） | restored delta=0 |
| **锁屏** | `BM_CLICK` → winver"确定" | ❌ 窗口存活，解锁后也未补执行 | `lock_verify.py` 实测 |
| **锁屏** | `WM_CHAR` → tk Entry | ❌ 同上 | 同上 |
| **锁屏** | `PrintWindow` | ✅ 能截不能动 | `wa_lock.png` 完整画面 |
| 任意状态 | 跨进程 `GetWindowTextW` 读运行框 Edit | ❌ 恒返回空（写却成功） | 见坑#5 |

**给"即使锁屏也要干活"需求的直接结论**：锁屏切到安全桌面后，消息注入和 UIA 交互实测全部失效——锁屏态的自动化必须走**无头通道**（应用自身 API/CLI/计划任务/服务），UI 自动化只能在桌面未锁的会话里做"隐形操作"。

## 操作步骤

### A. 一键验证矩阵（推荐先跑）

```bash
"<PY313>\python.exe" "<WORK_DIR>\windows-window-automation\scripts\bg_verify.py"
```

自动拉起 WADemo + 遮挡窗 + winver，输出逐项结果。本机输出：

```text
[occluded]   {'shot': True, 'type_posted': True, 'type_landed': 'False (delta=0)', 'tk_click': False}
[minimized]  {'shot': False, 'type_posted': True, 'tk_click': False}
[restored_typing_landed] False (delta=0)
[native_winver] {'bm_click_closed': True}
```

文本落没落入用"Entry 区域深色像素增量（打字符前后截图差分）"判定，阈值 delta>50。

### B. 手动四件套（无框架）

```bash
python.exe win_capture.py list                 # 枚举顶层窗口 hwnd/pid/title
python.exe win_capture.py shot WADemo out.png  # PrintWindow 截图（遮挡可用）
python.exe win_capture.py type WADemo "text"   # WM_CHAR 注入（自绘控件不保证）
python.exe win_capture.py close WADemo         # WM_CLOSE 优雅关窗
```

### C. UIA 工具（原生控件，推荐）

```bash
python.exe uia_tools.py inspect 运行           # 打印 UIA 树（找 Name/AutomationId/类型）
python.exe uia_tools.py set 运行 打开 calc Edit    # ValuePattern 写文本框
python.exe uia_tools.py read 运行 打开 Edit        # 读回 → 'calc'
python.exe uia_tools.py click 运行 确定            # InvokePattern 点按钮 → calc 真启动
```

以上对"运行"对话框（`explorer shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}` 拉起）实测全通，窗口无需在前台。

### D. 锁屏验证（会真的锁屏）

```bash
python.exe lock_verify.py
```

15s 倒计时（Ctrl+C 中止）→ `LockWorkStation()` → 锁屏态执行 WM_CHAR/BM_CLICK/PrintWindow → 结果写 `%TEMP%\wa_lock_result.txt`。本机实测：只有 PrintWindow 成功，两项注入均未生效。

## 验证方法（证据链）

| 声明 | 验证 | 实测输出 |
|---|---|---|
| 遮挡截全图 | 遮挡下 shot→看图 | `wa_occ.png` 完整窗口 |
| UIA 写/读/点全链路 | set→read→click→查新窗口 | `'calc'`→Calculator hwnd 出现→用 WM_CLOSE 清掉 |
| 原生按钮 BM_CLICK | winver 确定→查 IsWindow | `bm_click_closed: True` |
| tk 按钮不可点 | BM_CLICK/鼠标消息/UIA invoke→查 marker 文件 | `%TEMP%\wademo_clicks.log` 始终 NONE |
| 锁屏注入失效 | 锁屏中执行→解锁后查窗口/文本 | winver 存活、Entry 空 |

## 已知坑

| 现象 | 原因 | 解法/结论 |
|---|---|---|
| **`SendMessageW` 挂死** `[实测]` | 同步调用等目标处理完：点"运行-确定"时其 handler 做 ShellExecute，SendMessage 卡 >60s 不返回 | 后台点击一律 `PostMessageW`（发完即走），需要等结果才用 SendMessage 并加超时 |
| **tk/自绘控件吃消息不吃动作** `[实测]` | tk 的 Entry 只在持有 tk 内部焦点时处理 WM_CHAR（被遮挡窗夺前台后丢弃）；tk 按钮不走原生 WM_COMMAND 路由，BM_CLICK/鼠标消息/UIA invoke 全是 no-op | 自绘控件（tk/Qt/Flutter/DirectX 渲染）别试消息注入，走应用 API/CLI 或接受前台模拟输入 |
| **WM_CHAR 遮挡下不稳定** `[实测]` | 同一 tk 演示：激活态注入成功、被 foreground 窗口完全盖住后 3/3 次未落入 | 对非原生控件，注入成功≠下次成功，必须验证副作用（截图差分/标记文件），不能只信"投递成功" |
| **最小化截不到内容** `[实测]` | 最小化窗口 rect 塌缩，PrintWindow 只得标题栏残片 | 最小化场景别用截图做校验；用标记文件/UIA 读值等带外证据 |
| **跨进程 `GetWindowTextW` 恒空** `[实测]` | 运行框 ComboBox-Edit 被子类化：WM_SETTEXT 写成功，WM_GETTEXT 读回恒 '' | 读值用 UIA `get_value()`，别用 WM_GETTEXT 判成败 |
| **UIA `control_type='Button'` 歧义** `[实测]` | 一个窗口有 4 个 Button（含标题栏三键），泛型选择器报 `ElementAmbiguousError` | 按 Name/AutomationId/父节点过滤；`uia_tools.py` 名称匹配多项时直接报错列候选 |
| **pywinauto `set_value` 不存在** `[实测]` | `descendants()` 返回的 wrapper 无 `set_value` | 写值用 `el.iface_value.SetValue(...)`，读值 `el.get_value()` |
| 截图全黑 | DirectX/硬加速窗口即便 flag=2 也常黑 | 退而求其次截屏幕 DC 的窗口区域 `[需随应用复查]` |
| GBK 控制台打印炸 | 中文 Win 控制台默认 GBK | 脚本开头 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` |
| 锁屏注入全失效 | Win+L 切安全桌面，用户桌面窗口消息泵不再处理外来输入 | 锁屏需求改走计划任务/无头 API；UI 自动化只覆盖"解锁但非前台" |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/win_capture.py | 四合一 CLI：list / shot / type / close（EnumWindows + PrintWindow + PostMessageW + WM_CLOSE） |
| scripts/uia_tools.py | UIA CLI：inspect / read / set / click（pywinauto backend='uia'，原生控件推荐路径） |
| scripts/bg_verify.py | 能力矩阵一键验证：遮挡+最小化×{截图,注入,点击} + winver 原生按钮基线 |
| scripts/lock_verify.py | 锁屏态验证：LockWorkStation 后在锁屏中尝试注入/点击/截图，结果落 %TEMP% |
| scripts/demo_target.pyw | 演示目标：tk `WADemo`，Entry + stamp 按钮（点击写 %TEMP%\wademo_clicks.log） |
| scripts/cover.pyw | 遮挡窗：按 COVER_X/Y/W/H 环境变量盖在目标上模拟"被完全遮住" |
