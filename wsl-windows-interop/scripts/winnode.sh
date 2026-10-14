#!/usr/bin/env bash
# winnode.sh — WSL -> Windows node.exe bridge。
#
# 为什么需要它（2026-10-14 实测）：
#   * Windows node.exe 在 WSL 下 stdio 是坏的——node 把 WSL 传入的管道
#     fd 当 socket 打开，console.log/console.error 直接抛 EISDIR，
#     进程退出码也丢（exit(3) 变 0）。node --version 能显示是因为走
#     另一条输出路径，别被它骗了。
#   * exec/包装层会转义内层引号、预展开 $，内联 cmd.exe /c "...&& node"
#     不可靠。
#   * cmd.exe /c 经 WSL 互操作层不传进程退出码（批处理 exit /b N -> 0）。
#
# 解法：生成 .cmd 文件，cmd.exe /c 执行（命令行零内层引号），.cmd 内部
# stdout+stderr 重定向到日志文件、%ERRORLEVEL% 写 .rc 文件；本脚本回读
# 后重建输出与退出码。
#
# 用法:
#   winnode.sh script.js [args...]      输出打印到本端 stdout，退出码回传
#   winnode.sh --keep script.js [args]  保留生成的 .cmd 并打印路径
# 环境变量:
#   WINNODE      node.exe 路径（WSL 或 Windows 形式；默认靠 Windows PATH）
#   WINNODE_TMP  生成 .cmd/日志的目录（默认 %TEMP%\winnode）

set -u

NODE="${WINNODE:-node.exe}"
case "$NODE" in
  /mnt/*|/*) NODE="$(wslpath -w "$NODE")" ;;
esac

KEEP=0
if [ "${1:-}" = "--keep" ]; then KEEP=1; shift; fi
if [ $# -lt 1 ]; then
  echo "usage: winnode.sh [--keep] script.js [args...]" >&2
  exit 2
fi

js="$1"; shift
if [ ! -f "$js" ]; then
  echo "winnode: no such script: $js" >&2
  exit 2
fi
win_js="$(wslpath -w "$(readlink -f "$js")")"

# 默认工作目录放 Windows %TEMP%（/tmp 是 UNC 路径，cmd 的 cd 进不去）
work="${WINNODE_TMP:-}"
if [ -z "$work" ]; then
  win_tmp="$(cmd.exe /c 'echo %TEMP%' 2>/dev/null | tr -d '\r')/winnode"
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

# .cmd 正文全部在文件内成形——外层转义/预展开够不着。
# 已是现有文件/目录的 WSL 参数自动转 Windows 路径；其余原样传递。
{
  printf '@echo off\r\n'
  case "$win_cwd" in
    \\\\*) printf 'pushd "%s"\r\n' "$win_cwd" ;;   # UNC：cmd 不能 cd，pushd 自动映射盘符
    *)     printf 'cd /d "%s"\r\n' "$win_cwd" ;;
  esac
  printf '"%s" "%s"' "$NODE" "$win_js"
  for a in "$@"; do
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

# 退出码走 .rc 文件（cmd.exe 的进程退出码过不了 WSL 互操作层）；
# 9P 视图有秒级延迟，rc 文件可能晚到，稍等重读。
for _ in 1 2 3 4 5; do
  [ -s "$rcf" ] && break
  sleep 1
done
if [ -s "$rcf" ]; then
  rc="$(tr -d ' \r\n' < "$rcf")"
fi

if [ $KEEP -eq 1 ]; then
  echo "[winnode] cmd=$win_cmdf log=$win_log rc=$win_rcf" >&2
else
  rm -f "$cmdf" "$rcf"
fi
exit "${rc:-1}"
