# WSL ↔ Windows interop 实操（进程/路径/凭据/GUI/文件系统）

## 概述

WSL（或 Git Bash 类 POSIX 环境）里驱动 Windows 侧的常用通道：`cmd.exe /c` 调 Windows 命令、`wslpath` 互转路径、Windows Python 跑重依赖脚本、`cmd.exe` 里的 git 走 Windows Credential Manager 推 GitHub、以及本环境特有的 `$变量` 剥离与 9P 文件视图延迟。全部为 2026-10-11 本机（WSL on Windows 11）实测。

## 环境前提

- OS：WSL（`uname -a` 含 `Microsoft`）挂载 `/mnt/c`、`/mnt/e`
- Windows Python313：`/mnt/c/Users/<win用户>/AppData/Local/Programs/Python/Python313/python.exe`（下称 `<PY313>`）
- 无 `powershell`/`sqlite3`/`tasklist` 命令——全部走 `cmd.exe /c`

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

## 验证方法（2026-10-11 本机实测）

| 项 | 命令 | 实测 |
|---|---|---|
| 进程检查 | `cmd.exe /c "tasklist" \| grep -i warhammer` | 无匹配=游戏未运行；Steam/Tabbit 在列 |
| sqlite 收缩 | 步骤 2 | `wal_checkpoint` 返回 `(0,0,0)`，`-wal` 文件归零 |
| 推送 | 步骤 4 | `main -> main` 成功，前提是先 `fetch+rebase` |
| 变量陷阱 | `x=hi; echo "x=$x"` | 输出 `x=`（变量被剥离）→ 见坑表 |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 命令里 `$变量`/`$()`/`for` 循环变量变空 | **exec 层预展开剥离**（本会话实测：连 for 循环变量都是空） | 不用变量：管道 `ls -t x* \| tail -n +N \| xargs -d '\n' rm -f`、`find -delete`；shell 逻辑写成 `.sh` 文件再 `bash file`（文件内 `$` 正常）`[实测]` |
| `.sh` 报 `set: pipefail: invalid option name` | 工具写出的文件是 CRLF 行尾 | `sed -i 's/\r$//' file.sh` `[实测]` |
| 批量 rm 后 `ls`/`du` 结果矛盾、`du` 显示 `Infinity` | WSL↔Win 9P 文件视图秒级延迟 | 等 10-30s 再确认；以 `df` 为准 `[实测]` |
| `python3` 跑依赖脚本缺包 | WSL 自带 python 无 zstandard/PIL/numpy | 一律 `<PY313>`（或项目 `tools/winpy` 约定）`[实测]` |
| 中文输出乱码/`UnicodeEncodeError` | cmd/管道是 GBK；Windows 控制台 codepage | 脚本 `sys.stdout.reconfigure(encoding='utf-8',errors='replace')`；`.bat/.ps1` 避免含 CJK `[实测]` |
| 清了 npm-cache 后 MCP 服务报 ENOENT | **memory MCP 把 `memory.jsonl` 存在 `npm-cache\_npx\<hash>\node_modules\...\dist\`** | 清用户级缓存前先查各服务数据文件路径；把缓存目录加入"慎删"名单 `[实测 教训]` |
| 想要 powershell | WSL 里没装 | `cmd.exe /c powershell -Command "..."` 走 Windows 侧 `[需验证]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| 无（命令行即复现） | |
