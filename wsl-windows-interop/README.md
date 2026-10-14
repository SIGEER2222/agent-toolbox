# WSL ↔ Windows interop 实操（进程/路径/凭据/GUI/文件系统）

## 概述

WSL（或 Git Bash 类 POSIX 环境）里驱动 Windows 侧的常用通道：`cmd.exe /c` 调 Windows 命令、`wslpath` 互转路径、Windows Python 跑重依赖脚本、`cmd.exe` 里的 git 走 Windows Credential Manager 推 GitHub、以及本环境特有的 `$变量` 剥离与 9P 文件视图延迟。`scripts/` 内置两座桥：`winnode.sh`（Windows node，stdio 修复）与 `winps.sh`（PowerShell，`$` 预展开修复）。主体为 2026-10-11 实测，2026-10-14 据 90 个历史会话复盘增补坑表与脚本。

## 环境前提

- OS：WSL（`uname -a` 含 `Microsoft`）挂载 `/mnt/c`、`/mnt/e`
- Windows Python313：`/mnt/c/Users/<win用户>/AppData/Local/Programs/Python/Python313/python.exe`（下称 `<PY313>`）
- `powershell.exe` 在 WSL PATH（`System32/WindowsPowerShell/v1.0/`）可直接调；`pwsh.exe` 不在 PATH，需全路径；`sqlite3`/`wmic` 无，进程查询用 `Get-CimInstance` 或 `cmd.exe /c tasklist`

## 操作步骤

### 1. 调 Windows 命令（tasklist/findstr/where）

```bash
cmd.exe /c "tasklist" | grep -i warhammer     # 进程检查（findstr 同理）
cmd.exe /c "echo %LOCALAPPDATA%" | tr -d '\r' # 解析 Windows 环境变量
wslpath "$(cmd.exe /c 'echo %LOCALAPPDATA%' | tr -d '\r')"  # → /mnt/c/Users/.../AppData/Local
```

预期：tasklist 输出进程表（编码是 GBK，中文乱码无碍英文匹配）；env 解析出 `C:\Users\...\AppData\Local`。

### 2. 跑 Windows Python（需要 zstandard/Pillow 等已装依赖）

```bash
<PY313> -c "import sqlite3; c=sqlite3.connect(r'C:\path\to\db.sqlite',timeout=5); print(c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall())"
```

预期：`[(0,0,0)]`——WAL 帧清空；用于收缩 `xxx.db-wal` 且**无需排他锁**（实测回收 1.6G）。

### 3. 磁盘用量/清理

```bash
df -h /mnt/c /mnt/e                        # 盘级用量
du -x -h --max-depth=1 /mnt/c 2>/dev/null | sort -rh | head   # 逐目录（-x 防跨盘）
find /mnt/c/Users/<u>/AppData/Local/Temp -mindepth 1 -mtime +0 -delete   # 清 >24h 临时文件
```

### 4. git 推送（WSL 无凭据时）

```bash
# WSL 侧提交（不改配置，行内身份）：
git -c user.name="<name>" -c user.email="<email>" commit -m "msg"
# 推送走 Windows Credential Manager：
cmd.exe /c "cd /d E:\Code\<repo> && git push origin main"
```

预期：Windows 侧 git 已配 GCM 时静默推送成功 `[实测]`。

### 5. 拉起 Windows GUI 程序

```bash
"$(dirname <PY313>)/pythonw.exe" "E:\path\to\app.pyw" &     # GUI 进程入用户会话
explorer.exe "E:\path\to\dir"                   # 打开资源管理器/关联应用
```

### 6. 跑 Windows node（stdio 修复桥）

```bash
scripts/winnode.sh script.js [args...]        # stdout+stderr+退出码都拿得到
scripts/winnode.sh --keep script.js           # 保留生成的 .cmd 便于排查
```

直接 `node.exe script.js` 会 EISDIR 崩溃（node 把 WSL 管道 fd 当 socket 打开），`node --version` 能显示是假象（走另一输出路径）。本桥生成 `.cmd`→`cmd.exe /c`→脚本内 `> log 2>&1` + `%ERRORLEVEL%` 写 `.rc` 回读。

### 7. 跑 PowerShell（`$` 预展开修复桥）

```bash
scripts/winps.sh script.ps1 [args...]
scripts/winps.sh -c 'Get-Process | Where-Object {\$_.Name -match "x"}'   # -c 里 $ 写 \$
```

内联 `powershell -Command` 里的 `$_`/`$var` 被预展开成 `/bin/bash`/空串，内层引号被转义成 `\"`——一律写 `.ps1` 文件或走 `-c`（代码写 UTF-8 BOM 临时文件）。应急可用 `powershell.exe -EncodedCommand <UTF16LE base64>`（base64 无 `$` 可吞）：

```bash
powershell.exe -EncodedCommand "$(python3 -c 'import base64,sys; print(base64.b64encode(sys.argv[1].encode("utf-16-le")).decode())' 'Get-Date')"
```

### 8. GitHub 不通时走本地代理

```bash
# 直连 443 超时/reset 时，找本地代理端口（常见 7890/7897/10809）后用一次性 -c（不改配置）：
git -c http.proxy=http://127.0.0.1:7897 push origin main
```

## 验证方法（2026-10-11 本机实测）

| 项 | 命令 | 实测 |
|---|---|---|
| 进程检查 | `cmd.exe /c "tasklist" \| grep -i warhammer` | 无匹配=游戏未运行；Steam/Tabbit 在列 |
| sqlite 收缩 | 步骤 2 | `wal_checkpoint` 返回 `(0,0,0)`，`-wal` 文件归零 |
| 推送 | 步骤 4 | `main -> main` 成功，前提是先 `fetch+rebase` |
| 变量陷阱 | `x=hi; echo "x=$x"` | 输出 `x=`（变量被剥离）→ 见坑表 |
| winnode 桥 | `winnode.sh probe.js`（脚本 exit 4、stdout+stderr 混合中文） | 双流输出齐全、UTF-8 完好、退出码 4 正确回传 `[2026-10-14 实测]` |
| winps 桥 | `winps.sh -c 'Write-Output x; exit 6'` | 输出正常、退出码 6 正确回传 `[2026-10-14 实测]` |
| GitHub 代理推送 | `git -c http.proxy=http://127.0.0.1:7897 push` | 直连 reset/超时后代理推送 `main -> main` 成功 `[2026-10-14 实测]` |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 命令里 `$变量`/`$()`/`for` 循环变量变空 | **exec 层预展开剥离**（本会话实测：连 for 循环变量都是空） | 不用变量：管道 `ls -t x* \| tail -n +N \| xargs -d '\n' rm -f`、`find -delete`；shell 逻辑写成 `.sh` 文件再 `bash file`（文件内 `$` 正常）`[实测]` |
| `.sh` 报 `set: pipefail: invalid option name` | 工具写出的文件是 CRLF 行尾 | `sed -i 's/\r$//' file.sh` `[实测]` |
| 批量 rm 后 `ls`/`du` 结果矛盾、`du` 显示 `Infinity` | WSL↔Win 9P 文件视图秒级延迟 | 等 10-30s 再确认；以 `df` 为准 `[实测]` |
| `python3` 跑依赖脚本缺包 | WSL 自带 python 无 zstandard/PIL/numpy | 一律 `<PY313>`（或项目 `tools/winpy` 约定）`[实测]` |
| 中文输出乱码/`UnicodeEncodeError` | cmd/管道是 GBK；Windows 控制台 codepage | 脚本 `sys.stdout.reconfigure(encoding='utf-8',errors='replace')`；`.bat/.ps1` 避免含 CJK `[实测]` |
| 清了 npm-cache 后 MCP 服务报 ENOENT | **memory MCP 把 `memory.jsonl` 存在 `npm-cache\_npx\<hash>\node_modules\...\dist\`** | 清用户级缓存前先查各服务数据文件路径；把缓存目录加入"慎删"名单 `[实测 教训]` |
| heredoc/`$()`/反引号内容被吃或被执行 | **exec/包装层在 shell 启动前预展开**，连 `'EOF'` 引用式 heredoc、`python -c` 字符串内的也吃（7+ 个历史会话重复踩） | 含 `$`/反引号/代码的文件内容一律用编辑器/write 工具落盘，禁止 heredoc 喂内容 `[实测]` |
| `powershell -Command` 里 `$_`→`/bin/bash`、`$?`→`0` | 同上，变量被外层先展开 | `.ps1` 文件 `-File` 跑或 `scripts/winps.sh -c`（`$`→`\$`）`[实测]` |
| `tasklist /FI` 参数失效/报路径错 | MSYS 把 `/FI` 当 POSIX 路径转换 | 写 `//FI` `//NH`，或命令进 `.cmd` 文件 `[实测]` |
| `.cmd` 在 bash 里直接执行被当 shell 脚本 | bash 只按后缀不识 | `cmd.exe /c file.cmd` `[实测]` |
| `cmd.exe /c` 后 `$?` 恒 0 | 批处理退出码过不了互操作层 | `.cmd` 内 `> f echo %ERRORLEVEL%` 写文件回读（`winnode/winps` 已封装）`[实测]` |
| Windows node `console.log` 抛 EISDIR | node 把 WSL 管道 fd 当 socket 打开 | `scripts/winnode.sh`（生成 .cmd+文件重定向）`[实测]` |
| `echo $?` 显示 0 但命令实际失败 | exec 层把 `$?` 预展开成字面 0 | 看工具返回的 Exit code 字段，勿 inline echo `[实测]` |
| 想要 powershell | ~~WSL 里没装~~（已更正 2026-10-14：`powershell.exe` 在 PATH） | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File x.ps1` `[实测]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| `scripts/winnode.sh` | WSL→Windows node 桥：生成 .cmd→cmd.exe /c→日志+.rc 回读，修 EISDIR/退出码丢失 |
| `scripts/winps.sh` | WSL→PowerShell 桥：.ps1/-c 代码写文件→.cmd 包装，修 `$_` 预展开/引号转义 |
