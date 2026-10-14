#!/usr/bin/env bash
# winps.sh — WSL -> Windows PowerShell bridge。姊妹工具：winnode.sh。
#
# 为什么需要它（2026-10-14 实测）：
#   * exec/包装层会预展开 $——内联 powershell -Command '... $_.X ...'
#     里的 $_ 变成 /bin/bash，$var 变空串，for 循环变量同样失效；
#     'EOF' heredoc 与 $()/反引号也照吃，连 heredoc 写文件都会被污染。
#   * 内层双引号会被转成字面 \" 。
#   * powershell.exe 的 stdout 走 WSL 管道本身没问题，但为复用 .cmd+
#     .rc 的退出码机制（cmd.exe /c 不传进程退出码），仍走同一模式。
#
# 解法：要跑的内容写成 .ps1 文件，再生成 .cmd 由 cmd.exe /c 执行——
# 命令行里没有任何可被破坏的引号。.cmd 内部 stdout+stderr 重定向到
# 日志、%ERRORLEVEL% 写 .rc 回读。
#
# 用法:
#   winps.sh script.ps1 [args...]    跑现有 .ps1
#   winps.sh -c '<powershell 代码>'  代码写入临时 .ps1（UTF-8 BOM）再跑
#   winps.sh --keep ...              保留生成的 .cmd/.ps1 并打印路径
#
# 注意：-c 的代码文本仍经过外层预展开，$ 一律写成 \$（外层吃掉反斜杠
# 后脚本收到字面 $）。例：winps.sh -c 'Get-Process | Where-Object
# {\$_.Name -match "x"}'。代码复杂时直接先写 .ps1 文件更省心。
# 环境变量:
#   WINPS      powershell.exe 路径（默认 Windows PowerShell 5.1，在 PATH）
#   WINPS_TMP  生成文件的目录（默认 %TEMP%\winps）

set -u

PS="${WINPS:-powershell.exe}"

KEEP=0
if [ "${1:-}" = "--keep" ]; then KEEP=1; shift; fi
if [ $# -lt 1 ]; then
  echo "usage: winps.sh [--keep] script.ps1 [args...] | -c '<code>'" >&2
  exit 2
fi

work="${WINPS_TMP:-}"
if [ -z "$work" ]; then
  win_tmp="$(cmd.exe /c 'echo %TEMP%' 2>/dev/null | tr -d '\r')/winps"
  work="$(wslpath "$win_tmp")"
fi
mkdir -p "$work"

ts="$(date +%Y%m%d_%H%M%S)_$$"
log="$work/run_$ts.log"
rcf="$work/run_$ts.rc"
cmdf="$work/run_$ts.cmd"
win_log="$(wslpath -w "$log")"
win_rcf="$(wslpath -w "$rcf")"
win_cmdf="$(wslpath -w "$cmdf")"
win_cwd="$(wslpath -w "$(pwd)")"

ps_args=()
if [ "$1" = "-c" ]; then
  if [ $# -lt 2 ]; then
    echo "winps: -c needs code" >&2
    exit 2
  fi
  psf="$work/run_$ts.ps1"
  # UTF-8 BOM：PS 5.1 对无 BOM 的 .ps1 按 ANSI 读，中文会乱码
  { printf '\xef\xbb\xbf'; printf '%s\n' "$2"; } > "$psf"
  shift 2
  win_psf="$(wslpath -w "$psf")"
else
  psf=""
  if [ ! -f "$1" ]; then
    echo "winps: no such script: $1" >&2
    exit 2
  fi
  win_psf="$(wslpath -w "$(readlink -f "$1")")"
  shift
fi
for a in "$@"; do ps_args+=("$a"); done

{
  printf '@echo off\r\n'
  case "$win_cwd" in
    \\\\*) printf 'pushd "%s"\r\n' "$win_cwd" ;;   # UNC：cmd 不能 cd，pushd 自动映射盘符
    *)     printf 'cd /d "%s"\r\n' "$win_cwd" ;;
  esac
  printf '"%s" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%s"' "$PS" "$win_psf"
  for a in "${ps_args[@]:-}"; do
    [ -n "$a" ] || continue
    if [ -e "$a" ]; then a="$(wslpath -w "$(readlink -f "$a")")"; fi
    printf ' "%s"' "$(printf '%s' "$a" | sed 's/"/""/g')"
  done
  printf ' > "%s" 2>&1\r\n' "$win_log"
  # > file echo 的写法：避开 "echo 3>f" 被解析成 fd 重定向、同时不带尾随空格
  printf '> "%s" echo %%ERRORLEVEL%%\r\n' "$win_rcf"
  case "$win_cwd" in \\\\*) printf 'popd\r\n' ;; esac
} > "$cmdf"

cmd.exe /c "$win_cmdf"
rc=$?

cat "$log" 2>/dev/null

for _ in 1 2 3 4 5; do
  [ -s "$rcf" ] && break
  sleep 1
done
if [ -s "$rcf" ]; then
  rc="$(tr -d ' \r\n' < "$rcf")"
fi

if [ $KEEP -eq 1 ]; then
  echo "[winps] cmd=$win_cmdf log=$win_log rc=$win_rcf ps1=${psf:-<infile>}" >&2
else
  rm -f "$cmdf" "$rcf" ${psf:+"$psf"}
fi
exit "${rc:-1}"
