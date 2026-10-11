# Windows 窗口自动化：枚举 / PrintWindow 截图 / PostMessageW 输入（无框架）

## 概述

不装自动化框架，纯 `ctypes` + Pillow 对 Windows 顶层窗口做四件事：`list` 枚举、`shot` PrintWindow 截图（窗口被遮挡也能截）、`type` 向子控件逐字符 `PostMessageW(WM_CHAR)` 注入文本、`close` 发 `WM_CLOSE` 优雅关闭。2026-10-11 本机（Windows Python + WSL 调用）实测通过。

## 环境前提

- OS：Windows；WSL 下通过 `python.exe` interop 调用同一脚本
- 依赖：Windows Python 3.13+（本机 `C:\Users\<用户>\AppData\Local\Programs\Python\Python313\python.exe`）+ `pip install pillow`
- 演示目标：`scripts/demo_target.pyw`（tkinter 窗口，标题 `WADemo`，含文本框）

## 操作步骤

### 1. 拉起演示窗口

```bash
"<PY313>\pythonw.exe" "<WORK_DIR>\windows-window-automation\scripts\demo_target.pyw" &
```

预期：桌面出现 `WADemo` 窗口（空文本框）。`pythonw` 无控制台，后台运行。

### 2. 枚举窗口

```bash
"<PY313>\python.exe" "<WORK_DIR>\windows-window-automation\scripts\win_capture.py" list
```

预期输出：`     789600  pid=13384  WADemo`（hwnd/pid 行为非固定值）

### 3. 截图（PrintWindow）

```bash
"<PY313>\python.exe" "<WORK_DIR>\...\win_capture.py" shot WADemo "C:\Windows\Temp\wa.png"
```

预期：PNG 落盘，内容是完整窗口画面（不需要窗口在前台/有焦点）。

### 4. 注入文本（PostMessageW WM_CHAR）

```bash
"<PY313>\python.exe" "<WORK_DIR>\...\win_capture.py" type WADemo "hello123"
```

脚本自动取目标窗口第一个可见子控件投递 `WM_CHAR`。再跑一次 shot 验证：文本框里出现 `hello123`——**整个过程不抢焦点、不移动鼠标**。

### 5. 关闭

```bash
"<PY313>\python.exe" "<WORK_DIR>\...\win_capture.py" close WADemo
```

预期：窗口消失（`WM_CLOSE` 等价用户点 X，程序可自行清理）。

## 验证方法（2026-10-11 本机实测）

| 环节 | 方法 | 实测结果 |
|---|---|---|
| 枚举 | `list \| grep -i wademo` | 命中 `hwnd=789600 pid=13384 WADemo` |
| 截图 | `shot` 后用图像查看器看 PNG | 窗口完整画面（标题栏+文本框） |
| 注入 | `type` 后再 `shot` | 文本框内显示 `hello123`，焦点/前台无变化 |
| 关闭 | `close` 后再 `list` | `WADemo` 不再出现（进程正常退出） |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| `UnicodeEncodeError: 'gbk' codec` 打印窗口标题 | 中文 Windows 控制台默认 GBK，部分 CJK/emoji 编码失败 | 脚本里 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` `[实测]` |
| 截图全黑 | DirectX/硬件加速窗口需 `PW_RENDERFULLCONTENT`(=2)；UWP 顶层窗口即便这样也常黑 | 本脚本已用 flag=2；UWP 退而求其次用屏幕 DC 抓 GetWindowRect 区域 `[实测 需随应用复查]` |
| `type` 文本没进 | WM_CHAR 投递到了错误控件/目标只认 WM_KEYDOWN-UP 或 EM_REPLACESEL | 先 `EnumChildWindows` 打印控件树确认目标；不同框架（Qt/Electron/UWP）消息响应差异大，逐案试 `[实测]` |
| 坐标对不上 | 高 DPI 缩放 | 脚本首行 `SetProcessDPIAware()` `[实测]` |
| 想动别人窗口 | **纪律**：只操作自己拉起的或明确授权的目标窗口 | 禁止对其他应用窗口 `SW_HIDE`/`SW_MINIMIZE`/移屏/置顶遮挡；被遮挡要截图就用 PrintWindow 而非把它拉前台 |
| WSL 里调用 | GUI 进程要在用户会话里跑 | `pythonw.exe`/`explorer.exe` 经 interop 拉起即可，截图落 `C:\Windows\Temp` 双方都能读 `[实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| scripts/win_capture.py | 四合一 CLI：list / shot / type / close（EnumWindows + PrintWindow + PostMessageW + EnumChildWindows） |
| scripts/demo_target.pyw | 演示目标：tkinter `WADemo` 窗口（文本框接收注入字符） |
