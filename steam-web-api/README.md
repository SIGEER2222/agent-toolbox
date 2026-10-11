# Steam Web API 无 key 端点：工坊条目元数据（GetPublishedFileDetails）

## 概述

不申请 API key 也能拿 Steam 工坊条目元数据：`ISteamRemoteStorage/GetPublishedFileDetails` 是 POST 公开端点，批量返回 title/description/file_size/tags/时间戳等。适合"知道 workshop id、要验证/登记元数据"的资源获取场景。2026-10-11 对 WH3(appid 1142710) 两个真实条目实测通过。

## 环境前提

- 任意能出网的 shell（curl）；本机 WSL 直连 `api.steampowered.com` 可达
- 不需要 API key、不需要登录
- 注意：`steamcommunity.com` 网页在本机直连不通，**但 `api.steampowered.com` 通**——两个域名连通性不同，别一概而论 `[实测]`

## 操作步骤

### 1. 单条/批量查工坊详情

```bash
curl -s -X POST "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/" \
  -d "itemcount=2" \
  -d "publishedfileids[0]=3157105199" \
  -d "publishedfileids[1]=3680306397"
```

预期输出（关键字段）：

```json
{"response":{"result":1,"resultcount":2,"publishedfiledetails":[
  {"publishedfileid":"3157105199","result":1,"title":"Warband UI Framework","file_size":"920567", ...},
  {"publishedfileid":"3680306397","result":1,"title":"MCT菜单界面汉化","file_size":"336518", ...}]}}
```

`result=1` OK，`result=9` 条目不存在或已删除（本机实测乱编 id 返回 9）。

### 2. 提取关键字段（jq 或 python -c）

```bash
curl -s -X POST ".../GetPublishedFileDetails/v1/" -d "itemcount=1" -d "publishedfileids[0]=3157105199" \
| python -c "import sys,json; x=json.load(sys.stdin)['response']['publishedfiledetails'][0]; print(x['title'], x['file_size'])"
```

## 验证方法（2026-10-11 本机实测）

| 检查 | 期望 |
|---|---|
| 真实 wsid 3157105199/3680306397 | `result:1`，title 与工坊页一致 |
| 不存在的 id | `result:9`（k_EResultFileNotFound） |
| 连通性 | `curl --connect-timeout 15` 正常返回（本机直连 ok） |

## 已知坑

| 现象 | 原因 | 解法 |
|---|---|---|
| 需要 key 的接口（GetCollectionDetails 以外的 ISteamRemoteStorage 多数读接口、ResolveVanityURL 等） | 官方多数 API 要 `key=` 参数 | 到 `steamcommunity.com/dev/apikey` 申请后放 `&key=`，别写进代码库；keyless 端点有限，优先用本端点 `[需验证]` |
| 想要"订阅列表/下载"而非元数据 | Web API 不暴露下载（工坊内容走 Steam 客户端/创意工坊协议） | 本机有 `wyccc-warhammer-mod-manager` 的 steamworks 桥（需 Steam 客户端运行）；或 steamcmd `workshop_download_item` |
| 网页打不开但想确认条目 | steamcommunity.com 需代理 | 用本端点查元数据；页面验证走带代理的浏览器（见 tabbit-browser-automation） |
| `file_size` 是字符串 | API 返回全部 string 化 | 用前 `int()` |

## 文件清单

| 文件 | 用途 |
|---|---|
| 无（curl 一行即可复现） | |
