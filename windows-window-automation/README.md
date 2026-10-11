# Windows 窗口自动化：遮挡 / 最小化 / 锁屏下的操作实测（UIA · Win32 消息 · PrintWindow）

## 概述

目标：用户在别的窗口里继续工作时，仍能对目标窗口读写、点击、截图——目标被其他窗口遮住、非前台、最小化，甚至**锁屏**时也能完成。每个结论都要有**真实副作用**证据（截图差分、对话框销毁、计算器启动、LogonUI 出现），并记录**实际遮挡者**（`covered_by`），不以脚本退出码为准。

核心结论（2026-10-11，Win11 24H2 本机实测）：

| 目标状态 | 已验证能做 | 未做到 / 不稳定 |
|---|---|---|
| 被其他窗口遮住（非前台） | 原生对话框 winver：`PostMessageW(BM_CLICK)` 与 UIA `Invoke` 均能关窗（遮挡者分别为用户的 Tabbit / Devin 窗口）；运行框：UIA 写值 + `Invoke` 启动 calc（遮挡者 cover.pyw）；tk 输入框：`WM_CHAR` 注入多数成功 | tk 自绘按钮：消息与 UIA 触发均未生效；tk 注入偶发失败（坑 #2） |
| 锁屏（LogonUI 已出现） | 单次实测：`PostMessageW` 的 WM_CHAR 与 BM_CLICK 仍被处理；PrintWindow 截图；解锁后无延后补执行、无重复 | SendInput / 鼠标未测 `[需验证]`；只做过一次锁屏 |
| 最小化 | 注入的文本还原后可见（单次实测） | PrintWindow 截不到内容 |
| 前台 | 不测：测试窗无法靠 API 置前台（`SetForegroundWindow` 返回 0） | 不做"前台 vs 非前台"对照 |

## 环境前提

- Windows 11 用户会话（不要用服务/SYSTEM 运行，否则拿不到用户桌面）；WSL 下通过 `python.exe` interop 调用同一批脚本
- Windows Python 3.13+；依赖：`pip install pillow pywinauto`
  - 坑：清华镜像拉不到 pywinauto，走官方源：`pip install pywinauto -i https://pypi.org/simple` `[实测]`
- 锁屏测试会真正锁定屏幕，**解锁需要你本人输入密码/PIN**，自动化无法代为完成

占位符：`<PY313>` = Windows Python 3.13 的 `python.exe` 路径；`<WORK_DIR>` = 本仓库根目录。

## 操作步骤

### 1. 遮挡 / 最小化 / 原生控件矩阵（一键）

```bash
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\bg_verify.py"
```

自动拉起 `WADemo`（tk）、遮挡窗 `cover.pyw`、`winver`、运行框，并清理自己拉起的测试窗口。一次实测输出：

```text
[occluded_by] cover.pyw
[occluded] {'shot': True, 'type_posted': True, 'type_landed': 'False (delta=0)', 'tk_click': False}
[minimized] {'shot': False, 'type_posted': True, 'tk_click': False}
[restored_typing_landed] False (delta=0)
[native] {'winver_post': {'closed': True, 'covered_by': '凡人修仙传 - Tabbit'}, 'winver_uia': {'closed': True, 'covered_by': 'WH3-modding - Devin - TVBox 本地拉取与配置'}, 'runbox_uia': {'calc_launched': True, 'covered_by': 'cover.pyw'}}
```

读法：
- `occluded_by` / `covered_by`：目标中心点**实际**的顶层窗口（`WindowFromPoint`）。`NOT COVERED` 表示该用例无效，不能计入结论。
- `native` 三项全部 `covered_by` 为其他窗口且结果为真：遮挡下原生控件可操作。
- `occluded.type_landed`：tk 输入注入的截图差分。**同一脚本的另一次运行中，遮挡者为 Devin 窗口时此项为 `True (delta=138)`，但本次为 False。** tk 注入结果有波动，失败时重跑；原因见坑 #2。
- `minimized.shot=False`：最小化时 PrintWindow 截不到内容，截图校验不可用。
- `tk_click=False`：tk 自绘按钮始终未被触发（坑 #1）。

### 2. UIA 工具（原生控件，推荐）

```bash
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\uia_tools.py" inspect 运行
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\uia_tools.py" set 运行 打开 calc Edit
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\uia_tools.py" read 运行 打开 Edit
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\uia_tools.py" click 运行 确定
```

前置：先用 `explorer shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}` 打开"运行"对话框。预期：`set ok` → `'calc'` → `invoked`，随后出现 Calculator 窗口（运行框内容的真实效果）。窗口全程不需要在前台。

### 3. 锁屏测试（两阶段，需要你解锁一次）

第一阶段：锁屏并在锁屏中操作。

```bash
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\lock_verify.py" lock
```

脚本会立即锁屏。预期输出（本机单次实测）：

```text
pre-lock desktop='Default' logonui=False
LockWorkStation() returned 1
  poll 1s desktop='Default' logonui=True
during-lock: {'locked_seen': True, 'desktop': '<open failed err=5>', 'logonui': True, 'entry_delta': 151, 'winver_alive': False}
state -> ...\wa_lock_state.json
```

判读：`LogonUI=True` 证明真的进了锁屏；`OpenInputDesktop` 失败（err=5）证明输入桌面已不可访问；截图里可见 `LCK` 证明锁屏中 WM_CHAR 被处理；`winver_alive=False` 证明锁屏中 PostMessage 的 BM_CLICK 被处理。

第二阶段：**你解锁屏幕后**运行：

```bash
"<PY313>" "<WORK_DIR>\windows-window-automation\scripts\lock_verify.py" check
```

预期输出（本机单次实测）：

```text
after-unlock: {'desktop': 'Default', 'logonui': False, 'winver_alive': False, 'demo_alive': True, 'entry_delta_vs_base': 99}
```

判读：解锁后桌面恢复、`winver` 仍已销毁（锁屏期间执行，没有延后）。`entry_delta_vs_base=99` 与第一阶段的 151 不一致，是光标闪烁造成的测量噪声（该次运行尚未关闭闪烁，见坑 #3）；以截图为准：截图里只有一个 `LCK`，没有重复注入。check 结束时会关闭两个测试窗口。

## 验证方法

| 声明 | 证据 | 数据 |
|---|---|---|
| 遮挡者确为所声称的窗口 | `WindowFromPoint(目标中心)` 的根窗口 | `covered_by`，`NOT COVERED` 即无效 |
| tk 输入框接受注入 | 注入前后截图差分（Entry 区深色像素） | 落入：delta 138 / 153 / 182 / 157；失败：delta 0（见坑 #2） |
| 最小化时注入的文本可见 | 还原后截图累计差分 | 例：326 = 138 + 188 |
| 原生按钮在遮挡下生效 | 对话框 `IsWindow` | winver 销毁（Tabbit 与 Devin 两种遮挡者） |
| UIA 写→读→点→真实效果 | `set`/`read`/`invoke` + Calculator 出现 | `'calc'` → Calculator（遮挡者 cover.pyw） |
| 锁屏确实发生 | LogonUI.exe 出现 + 输入桌面打开失败 | `logonui=True`，`err=5` |
| 锁屏中消息送达 | 锁屏中截图看到 `LCK`；winver 销毁 | 截图 + `winver_alive=False` |
| 解锁后无延后执行 | 解锁后截图只有一个 `LCK` | 无重复 |
| tk 按钮未触发 | 标记文件 `%TEMP%\wademo_clicks.log` 行数不变 | 每种方式 0 行（坑 #1） |

## 已知坑

| # | 现象 | 原因 / 结论 | 处理 |
|---|---|---|---|
| 1 | tk 按钮（stamp）的消息/UIA 触发全部无效 `[实测 原因未查明 需验证]` | 已试 6 种：对 `Button` 子窗 BM_CLICK（同步与异步）、WM_COMMAND、UIA `invoke()`、完整鼠标序列 WM_MOUSEMOVE→LBUTTONDOWN→LBUTTONUP（坐标对准按钮中心，投给覆盖按钮的 `TkChild`）。标记文件始终不增加 | 自绘按钮不要依赖消息触发，需要点击时改用应用自身 API / CLI |
| 2 | tk 输入框注入偶发失败 `[实测 原因未查明 需验证]` | 同一设置下多数成功，但也出现过：① probe9 六次中五次落入，唯一失败的一次目标被系统"任务切换"界面覆盖（`covered_by` 能识别）；② bg_verify 一次运行中遮挡者为 cover.pyw，注入和最小化后注入都是 delta=0，同一演示实例内全部失败 | 不要只看返回值：用截图差分验证；失败就重启演示窗再投递。目前无法保证 100% 成功 |
| 3 | 截图差分忽大忽小（±50 像素） `[实测]` | tk 输入框光标闪烁，光标亮/灭改变差分；基线取在"亮"的时刻，文本增量会被抵消，曾误判为注入失败 | 演示窗 Entry 设 `insertofftime=0` 关闭闪烁（`demo_target.pyw` 已设）；以文本量级（每字符约 40–70 像素）判断，并以截图为准 |
| 4 | 遮挡 Z 序会被抢回，早先"遮挡"结论不成立 `[实测 已修正→见2026-10-11]` | 测试从 Devin 终端发起，创建窗口时终端会重新激活并压到遮挡窗上面。早先的 cover 结论没有校验遮挡者，属于未验证的假设 | 每次遮挡都用 `WindowFromPoint` 记录 `covered_by`；`cover_target()` 会把自己的遮挡窗提到顶层（`SetWindowPos(HWND_TOP)`，只动遮挡窗自身）。结论只采用 `covered_by` 为预期窗口的样本 |
| 5 | 系统"任务切换"界面会覆盖目标 `[实测]` | Alt+Tab 类系统界面出现在最顶层时会遮住目标，此时注入结果无效 | 看 `covered_by`，为 `任务切换` 的样本作废 |
| 6 | 早先版本断言"锁屏下注入全部失效、解锁后也不补执行" `[已修正→见2026-10-11]` | 当时没有检查 `LockWorkStation()` 返回值，也没有确认锁屏状态与输入桌面，属于未验证的推断。实测推翻：锁屏中 PostMessage 送达并生效 | 以本文第 3 节为准（单次实测） |
| 7 | 早先版本断言"tk Entry 只在持 tk 内部焦点时吃 WM_CHAR，遮挡下 3/3 未落入" `[已修正→见2026-10-11]` | 该数字是光标闪烁造成的测量伪影（坑 #3）。但注入确有偶发失败（坑 #2），不能说"稳定可用"也不能说"不行" | 以本文矩阵与坑 #2 为准 |
| 8 | `SendMessageW` 同步调用挂死 `[实测]` | 点"运行"对话框"确定"时其 handler 执行 ShellExecute，同步 SendMessage 卡 >60s 不返回 | 后台点击一律 `PostMessageW`（投递即返回）；需要结果时用 UIA 或副作用证据 |
| 9 | 跨进程 `WM_GETTEXT` 读"运行"框 Edit 恒为空 `[实测]` | 该控件写入（WM_SETTEXT 返回 1）后 WM_GETTEXT 读回仍为空 | 读值用 UIA `get_value()`，不要用 `GetWindowTextW` 判断成败 |
| 10 | UIA `control_type='Button'` 命中多个按钮报 `ElementAmbiguousError` `[实测]` | 标题栏的最小化/最大化/关闭按钮也是 Button | 按 Name 过滤（`uia_tools.py` 在多匹配时直接列出候选） |
| 11 | pywinauto 的 `descendants()` 元素没有 `set_value` `[实测]` | 写值需要底层 ValuePattern | 写 `el.iface_value.SetValue(...)`，读 `el.get_value()` |
| 12 | 最小化后 PrintWindow 截不到内容 `[实测]` | 最小化时窗口矩形塌缩 | 最小化场景用还原后的截图或 UIA 读值做校验 |
| 13 | 测试窗无法置前台 `[实测]` | `SetForegroundWindow` 返回 0（前台锁）。强行置前台需要 AttachThreadInput 或模拟输入，会抢焦点，不符合本 runbook 目标 | 不做"前台 vs 非前台"对照；需要前台时须用户同意后单独处理 |
| 14 | 锁屏测试需要人工解锁 `[实测]` | LogonUI 需要密码/PIN，自动化无法代为输入 | 先告知用户，再运行第一阶段；第二阶段在用户解锁后执行 |
| 15 | GBK 控制台打印窗口标题报 `UnicodeEncodeError` `[实测]` | 中文 Windows 控制台默认 GBK | 脚本首行 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` |
| 16 | 锁屏是否与 Win+L 手动锁屏等价 `[需验证]` | 本次锁屏由 `LockWorkStation()` 触发，未测 Win+L | 第 3 节结论适用于 `LockWorkStation()` 触发的锁屏 |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/win_capture.py | 枚举 / PrintWindow 截图 / WM_CHAR 注入 / WM_CLOSE 关窗（ctypes，无框架） |
| scripts/uia_tools.py | UIA 命令行：inspect / read / set / click（pywinauto `backend='uia'`） |
| scripts/bg_verify.py | 遮挡 / 最小化 / 原生控件矩阵一键验证；每项记录 `covered_by`，截图差分判定注入是否落入 |
| scripts/lock_verify.py | 锁屏两阶段验证：`lock` 锁屏并在锁屏中操作，`check` 解锁后核对 |
| scripts/demo_target.pyw | 演示目标：tk `WADemo`，Entry（已关闭光标闪烁）+ stamp 按钮（点击写 `%TEMP%\wademo_clicks.log`） |
| scripts/cover.pyw | 遮挡窗：按 `COVER_X/Y/W/H` 环境变量盖住目标，模拟"被完全遮住" |
