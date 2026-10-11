#!/usr/bin/env bash
# tab_run.sh <task-name> <js-file>
# WSL 下调用 Tabbit Browser 的 tabbit-cli 执行一段 JS 程序。
# 自动解析 launcher 路径（%LOCALAPPDATA% -> wslpath）、生成唯一 request-id。
# stdout 只含结果 JSON（单行）；launcher 的 TABBIT_PLAYWRIGHT_INSTANCE 行走 stderr。
set -euo pipefail

TASK="${1:?usage: tab_run.sh <task-name> <js-file>}"
JS_FILE="${2:?usage: tab_run.sh <task-name> <js-file>}"

CLI="${TABBIT_CLI:-}"
if [ -z "$CLI" ]; then
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    LAP="$(cmd.exe /c 'echo %LOCALAPPDATA%' 2>/dev/null | tr -d '\r')"
    CLI="$(wslpath "$LAP")/Tabbit/LocalAgent/bin/tabbit-cli.exe"
  else
    CLI="$LOCALAPPDATA/Tabbit/LocalAgent/bin/tabbit-cli.exe"
  fi
fi

[ -x "$CLI" ] || { echo "launcher not found: $CLI (set TABBIT_CLI)" >&2; exit 1; }

REQ_ID="run-$(date +%Y%m%d-%H%M%S)-${RANDOM}${RANDOM}"
"$CLI" nodejs --task "$TASK" --request-id "$REQ_ID" < "$JS_FILE"
