# GitHub REST API 无认证调用（公共仓库信息）

## 概述

公共仓库的只读信息（仓库元数据、README、目录、release）无需 token：`api.github.com` 匿名限额 60 次/小时。够用于"查某个公开仓库是否存在/拿 README/列文件"类资源获取。2026-10-11 实测通过。

## 环境前提

- curl 出网即可；无 token 时 60 req/h，带 token 5000/h
- 认证调用：`Authorization: Bearer <token>` 或 gh CLI / GitHub MCP（本机已有 github MCP 服务可走）

## 操作步骤

### 1. 查自己的剩余限额（不耗 core 限额）

```bash
curl -s https://api.github.com/rate_limit | head -20
```

预期：`"core":{"limit":60,"remaining":60,...}`（匿名）；认证用户 5000。

### 2. 仓库元数据

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com/repos/<owner>/<repo>
# 或拿内容：
curl -s https://api.github.com/repos/<owner>/<repo> | python -c "import sys,json;d=json.load(sys.stdin);print(d['full_name'],d['stargazers_count'],d['default_branch'])"
```

预期：`200`；404=不存在或私有（匿名视角）。

### 3. 列目录/读文件

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/<path>"       # 目录 JSON 数组
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>" # 原始文件（不占 API 限额）
```

预期：contents 返回 name/path/size/download_url 数组；raw 直接给正文。

## 验证方法（2026-10-11 本机实测）

| 调用 | 实测 |
|---|---|
| `/rate_limit` | core limit/remaining = 60/60 |
| `/repos/SIGEER2222/agent-toolbox` | HTTP 200，~0.6s |
| 写操作/issue/搜索 | 匿名 `401/403` 或限额 10 次/分——需 token `[需验证]` |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| `403 rate limit exceeded` | 匿名 60/h 跑完 | 加 `Authorization: Bearer $GITHUB_TOKEN`（token 放环境变量/凭据管理器，不入库）；或等 reset 时间戳 |
| 需要私有仓/写操作 | 匿名只读公开 | PAT（fine-grained 最小 scope）、gh CLI `gh auth login`、或 GitHub MCP（见 REFERENCES） |
| code search API | 匿名不可用（需认证） | 用 `search_code` MCP/带 token；或干脆 clone 后本地 rg |
| raw 大文件 | download_url 走 media CDN | `Accept: application/vnd.github.raw` 或直接用 raw.githubusercontent.com |

## 文件清单

| 文件 | 用途 |
|---|---|
| 无（curl 即复现） | |
