# wsl-joinguard — 根治 Windows `bash.exe`/`wsl.exe` 命令行拼接吞 `$` 问题

## 概述

Windows 上任何走 `bash.exe -c "CMD"`（System32 WSL stub）或
`wsl.exe <prog> <args...>`（非 `-e` join 模式）的调用，命令都会被外层
shell 以双引号语义预展开一次：`$VAR`、`$(...)`、`$$` 被吃掉，**单引号
也不保护**。典型表现：AI agent（Devin 等）经 bash 执行的命令里 `$`
静默消失。本工具用 `dpkg-divert` 把发行版内 `/bin/bash` 换成一个
dispatcher（真 bash → `/bin/bash.dist`）：认出被包裹形态就剥壳逐字
exec 真 bash，其余调用（脚本/交互/`-l`/正常 `-c`）原样透传。
免 UAC、免注册表，`wsl -u root` 完成，`apt` 升级 bash 也顶不掉。

## 环境前提

- Windows + WSL2 任一发行版（如 Ubuntu）
- 发行版内有 python3（Ubuntu 自带）与 dpkg（dpkg 系发行版自带；
  非 dpkg 系可手工 mv `/bin/bash`→`/bin/bash.dist` 等价实现）
- Windows 侧 cmd（`.cmd` 脚本）

## 操作步骤

### 1. 安装

```cmd
scripts\Install-Joinguard.cmd
```

预期输出：`VERIFY_SQ:$HOME:END`（字面 `$HOME` = 已修复；
`/home/...` = 仍坏）。

原理：`dpkg-divert --divert /bin/bash.dist --rename --add /bin/bash`
把真 bash 挪走，再把 `wsl-joinguard.py` 拷到 `/bin/bash`（chmod 755，
LF 行尾已由脚本保证）。

### 2. 回归验证（可选）

```cmd
scripts\verify.cmd
```

~60 项：$ 家族、单/双引号、控制流、重定向、heredoc、错误码、嵌套
`-c`、聚合 flag（`-lc`）、`wsl.exe` 非-e 各形态、root、长命令。
全绿即覆盖生效。

### 3. 卸载

```cmd
scripts\Uninstall-Joinguard.cmd
```

`dpkg-divert --rename --remove /bin/bash` 还原真 bash。

## 验证方法

```cmd
C:\Windows\System32\bash.exe -c "echo 'SQ:$HOME:END'"
rem 期望 SQ:$HOME:END（字面）；出 SQ:/home/xxx:END 说明守卫没生效
```

```bash
head -1 /bin/bash          # #!/usr/bin/python3
dpkg-divert --list | grep bash   # local diversion ... /bin/bash.dist
tail /tmp/joinguard-$(id -u).log # 守卫命中/透传日志
```

## 注意事项

- **`\$` 恢复标准语义**：修复生效后 `echo "\$x"` 输出字面 `$x`——
  裸写 `$` 才展开（修复前 `\$` 是 workaround，别再写）。
- **急救**：守卫损坏导致 bash 全死时 `wsl.exe -u root -e /bin/sh`
  （`-e` exec 模式不经壳层永远可用）→ `dpkg-divert --rename --remove /bin/bash`。
- **勿走 IFEO 路线**：火绒等 HIPS 会静默拦截 IFEO `Debugger` 值
  （写入不报错但值不存）——本工具即是为绕开该拦截设计。
- **作用域**：只影响 `wsl.exe` 命令行 join 进本发行版的调用；
  Git Bash / MSYS 有自己的 shell 不经 `/bin/bash`，不受影响。
- `scripts/BashFwd.cs` 是配套冗余件（编译成 bash.exe 放 PATH/探测位
  做 `wsl -e` 转发），主方案不需要它，仅在「不想动发行版」的
  环境做备选。

## 常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| 装完 `$` 仍被吃 | 用了别的发行版或守卫被还原 | 确认 `head -1 /bin/bash`，重跑 Install |
| Install 报 "required file not found" | 脚本是 CRLF | 新版 Install 已 `tr -d '\r'` 兜底 |
| 命令里内嵌 `"` 错位 | Windows 命令行层的引号配对（独立问题） | 把复杂命令写成 .sh 文件再执行 |
