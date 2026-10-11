# Wyccc Mod Manager 后端 API 进程内调用（WH3 MOD 状态/冲突扫描）

## 概述

`wyccc-warhammer-mod-manager` 的 `backend.api.API` 是**显式 RPC 白名单**服务（pywebview JS 桥背后同一入口 `api.call(method, args, kwargs)`）。脚本可在本机进程内实例化并调用全部允许方法：列 playset、扫描 MOD、生成冲突报告（含 `deep=True` 深度校验，含 `db_missing_reference`/`prefs_dangling_unit` 等高危项）。2026-10-11 实测通过。

## 环境前提

- 仓库：`E:\Code\wyccc-warhammer-mod-manager`（下称 `<WMM>`），state 在 `%APPDATA%\WycccModManager\state.db`
- Python：Windows Python313（依赖 zstandard/Pillow），WSL 下 `python.exe` interop
- 只读类方法无状态副作用；**写方法（reorder/delete/launch 等）会改 state.db——调用前备份**

## 操作步骤

### 1. 实例化 + 列 playset

```python
import sys, json
sys.path.insert(0, r"<WMM>")
from backend.api import API
api = API()
print(json.dumps(api.call("list_playsets"), ensure_ascii=False)[:500])
```

预期：`{"ok": true, "data": [{"id": "...", "name": "...", "mod_ids": [...]}]}`。`ok:false` 时 `error.code/message` 带原因（白名单外方法返回 `METHOD_NOT_ALLOWED`）。

### 2. 扫描 MOD（调依赖 _assets 的方法前必须做）

```python
r = api.call("scan_mods")
# ok → data: {"mods": 28, "warnings": 1, "scanned_roots": 2, "enabled_order": 20, "missing_enabled_ids": 44}
```

预期：`~1s` 返回；扫描填充 `api._assets`，之后的冲突报告/图鉴类方法才不报"尚未扫描 MOD"。

### 3. 冲突报告（深度）

```python
r = api.call("get_conflict_report", kwargs={"deep": True})
# data: {"generated_at", "elapsed_ms", "deep", "game_id", "items": [...], "stats", "warnings"}
```

预期：本机实测 `31.8s`、items=35。播放集每次变更后、启动游戏前跑这个，重点看 `severity="high"`。

### 4. 常用只读方法速查（均在白名单）

`get_bootstrap` / `detect_paths` / `list_playsets` / `list_mod_types` / `get_runtime_status` / `get_last_launch_mods` / `get_save_mods` / `list_save_games` / `list_launch_history` / `get_workshop_publish_copy`。写类：`reorder_mod_folders`/`launch_game`/`delete_mod_files` 等——见 `backend/api.py` `self._rpc` 字典全表。

## 验证方法（2026-10-11 本机实测）

| 调用 | 期望 |
|---|---|
| `list_playsets` | `ok:true`，data 为 playset 数组（本机含 `20261001` 等，mod_ids 为 `steam:<wsid>:<file>`/`local:data:<hash>` 形式） |
| `scan_mods` | `ok:true` ~0.9s，`mods:28`、`enabled_order:20` |
| `get_conflict_report deep=True` | `ok:true` ~31.8s，items 35 条，含 severity 字段 |
| 不存在的方法 | `ok:false, code=METHOD_NOT_ALLOWED` |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| `get_conflict_report` 立刻 `ok:false` | `_assets` 空，未先扫描 | 先 `scan_mods`（约 1s）`[实测]` |
| 打印 `Current Steam Workshop subscriptions are unavailable: ConnectToGlobalUser failed` | Steam 客户端未运行，`steam_runtime` 桥（node steamworks）连不上 | 仅影响工坊订阅元数据；扫描/冲突报告照常，需要时先启动 Steam `[实测]` |
| 直接 import `backend.api` 报缺包 | zstandard/Pillow 缺失 | 用 Windows Python313；WSL `python3` 不行 `[实测]` |
| `API()` 构造有启动副作用 | `__init__` 内 `_sync_save_games()` 等启动同步 | 脚本里复用同一实例，不要循环 new |
| 想要单位合并面板而非 MOD 状态 | 本 API 不管 DB 合并 | 用 `<WH3工作区>/tools/wh3catalogue.py`（load_catalogue 无头消费） |

## 文件清单

| 文件 | 用途 |
|---|---|
| 无（调用示例全部在 README 内嵌，≤10 行） | |
