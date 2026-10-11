# TVBox/zyfun 点播 + 4K 下载 + B站弹幕 + mpv 播放（Windows）

## 概述

两条观看路线：**在线看**走 zyfun（省事、最高 1080p、采集源片头有烧入广告）；
**下载看**走 qBittorrent + mpv（4K B站高码率、无广告、可叠弹幕）。
全套链路 2026-10-11 在 Windows 11 + Clash 代理环境实测通过。

## 环境前提

- OS：Windows（步骤里的 shell 以 WSL/Git Bash 为主，ps1 为 PowerShell）
- 依赖安装：
  ```
  winget install HiramWong.zyfun       # TVBox 生态 PC 播放器
  winget install -e --id qBittorrent.qBittorrent
  winget install shinchiro.mpv         # 本地播放（硬解+进度条+自动加载同名 ass）
  winget install Gyan.FFmpeg           # 验证/转码工具链（ffprobe/ffmpeg）
  ```
- 占位约定：`<WORK_DIR>` = 本仓库克隆到本地的目录；`<DL_DIR>` = 下载目录（默认 `%USERPROFILE%\Downloads`）

## 操作步骤

### 1. 在线看：zyfun

1. `winget install HiramWong.zyfun`，启动一次让它初始化数据库
2. 导入 TVBox 接口并设默认源（API 用法见 [README.txt](README.txt)，无鉴权 `http://127.0.0.1:9978/api/v1`）
3. 搜索片名 → 详情 → 线路选 `*m3u8` 结尾的（jsm3u8 实测最全最快）→ 点播

预期：cms 接口返回真实片单；采集源片头烧入广告几秒后进正片；上限 1080p，无 4K。

### 2. 找 4K 磁链

- 聚合页：`https://www.ku0.cc/1214`（凡人修仙传 4K 2160p 全季分集磁链+网盘，周更）`[时效性，2026-10-11 验证]`
- 备选：nyaa.si 搜 `凡人修仙传`（Doomdos 发布组，`[4K BILIBILI COM WEB-DL]`）——页面国内直连可能打不开，但磁链经 DHT/PEX 照样能下
- 网盘备选：夸克 `pan.quark.cn/s/c737dd5a9484`（HEVC 版体积更小）

### 3. 配置 qBittorrent

编辑 `%APPDATA%\qBittorrent\qBittorrent.ini` 的 `[BitTorrent]` 段：

```ini
Session\InterfaceName=<物理网卡名>      ; 绑定物理网卡，不走 VPN 隧道（本机示例：以太网）
Session\InterfaceAddress=<本机网卡IP>   ; 本机示例：192.168.1.3
Session\GlobalUPLimit=300               ; 上传限速 300KB/s，保护流量套餐
```

### 4. 批量添加磁链（免对话框）

```powershell
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe" `
  -ArgumentList "--skip-dialog", "`"magnet:?xt=urn:btih:<HASH>&tr=<TRACKER>`""
```

- `--skip-dialog` 静默添加；批量见 `scripts/add10.ps1`、`scripts/add188.ps1`
- 磁链最好带 `&tr=` tracker 参数；裸 hash 只能靠 DHT 摸 peer，小种子很慢

### 5. 拉 B 站弹幕 XML

```bash
# 搜番剧 → season_id（凡人修仙传 = 28747）
curl "https://api.bilibili.com/x/web-interface/search/type?keyword=<片名>&search_type=media_bangumi" -A "Mozilla/5.0"
# 拉分集列表拿每集 cid（同一 title 可能两组 ep，选 maxlimit=3000 那组——danmaku 多的才是主源）
curl "https://api.bilibili.com/pgc/view/web/season?season_id=<SID>" -A "Mozilla/5.0"
# 拉弹幕（必须 --compressed：接口恒定 brotli，不解是乱码）
curl --compressed -A "Mozilla/5.0" -H "Referer: https://www.bilibili.com/" \
  "https://comment.bilibili.com/<CID>.xml" -o dm.xml
```

预期：单集 ~340KB / ~3600 条；直连可达无需代理。批量脚本 `scripts/dm_fetch.sh`。

### 6. XML 转 ASS：`scripts/dm_all.py`

- `<d p="秒,模式,字号,颜色,...">` → ASS `Dialogue`；模式 1/2/3 右→左、6 左→右、5 顶、4 底，7/8/9 跳过
- PlayResX/Y 按片源分辨率（4K=3840×2160），泳道避让
- 输出与 mp4 同目录同名 `.ass`，mpv `sub-auto=fuzzy` 默认自动加载

### 7. mpv 播放

- 默认装于 `C:\Program Files\MPV Player\mpv.exe`；双击 mp4 即播
- 快捷键：空格暂停，←→ ±5s，↑↓ ±60s，PgUp/PgDn ±10min，F 全屏，`v` 切字幕轨（开关弹幕）

### 8. 出新集怎么续

1. 聚合页抓最新磁链 → `--skip-dialog` 加进 qBittorrent（仿 `scripts/add10.ps1`）
2. 查 season JSON 拿新 cid → `scripts/dm_fetch.sh` + `scripts/dm_all.py` 出 `.ass`
3. mpv 双击直接看，弹幕自动叠

## 验证方法

| 环节 | 验证命令/方法 | 实测结果（2026-10-11 本机） |
|---|---|---|
| 在线流能播 | ffmpeg 对 m3u8 解码出帧（走完 playlist→AES key→分片解密→h264） | 出凡人正片画面帧 |
| qBittorrent 加成功 | `%LOCALAPPDATA%\qBittorrent\BT_backup\` 出现 `<hash>.torrent`+`.fastresume` | 11 个任务在册 |
| 4K 文件为真 | `ffprobe <file>` 看 width/height/bit_rate | 3840×2160 h264 ~21.7Mbps，2.9GiB/19min |
| 弹幕拉到了 | dm.xml 行数/`<d ` 计数 | 单集 ~3600 条 |
| 弹幕叠上了 | `ffmpeg -ss <t> -copyts -i v.mp4 -vf "ass='<ASS>'" -frames:v 1 out.png` 看帧里有滚动弹幕 | 渲出"念头通达"等弹幕 |
| 下载目录 | `du -h <file>` 看真实已下（预分配文件显示全尺寸） | — |

## 已知坑

### 网络（Clash 环境实测）

| 现象 | 原因 | 解法 |
|---|---|---|
| 浏览器/zyfun 播流烧订阅流量 | 系统代理开着时它们走 Clash | 视频 CDN 域名写 `HKCU\...\Internet Settings\ProxyOverride` 绕过；Clash Verge 的"绕过域名"也要加一份否则被重写 `[实测]` |
| 绕过名单失效 | Clash TUN 模式全流量接管 | 保持 TUN 关闭 `[实测]` |
| 担心走 VPN | WireGuard 隧道不兜全网路由 | `curl ip-api.com/json` 验证出口 `[实测]` |
| curl/ffmpeg/qBittorrent/mpv 流量 | 不读系统代理 | 天然直连，无需处理 `[实测]` |

本机白名单示例（写 ProxyOverride 用）：`*.jisuzyv.com;*.jisuts.com;*.dytt-hot.com;*.lzfile26.com;*.ffzy-plays.com;*.ukubf3.com;*.bdzybf22.com;*.fengbao13.com`

### 执行环境（Windows+WSL 实测）

| 现象 | 原因 | 解法 |
|---|---|---|
| 命令里 `$变量` 消失 | exec 预展开剥离 | 一律写脚本文件再跑 `[实测]` |
| .bat 中文路径报错 | cmd 按 ANSI 读 UTF-8 | .bat 只写 ASCII `[实测]` |
| .ps1 `-like "*中文*"` 匹配失败 | 同上 | 用数字/大小匹配（`*195*`、`-gt 2GB`）`[实测]` |
| ffmpeg 输出路径报错 | Windows ffmpeg 不认 /mnt | 输出写 `C:\...`；image2 单帧加 `-update 1` `[实测]` |
| GUI 程序静默退出 | WSL 直拉无交互会话 | `explorer.exe "path"` 拉起 `[实测]` |
| zyfun 报"无有效搜索数据源" | 后台 API 改库后 UI 内存未刷新 | 重启 zyfun `[实测]` |
| play 接口超时 | 默认 timeout 10s，慢 CDN 首包 5-12s | setting.timeout 调 30000 `[实测]` |
| share 页线路慢/失败 | 要走应用嗅探 | 只用 `*m3u8` 直链线路 `[实测]` |
| ASS 里出现字面 `}` | 花括号嵌套 | 颜色写 `\c&HFFFFFF` 不套 `{}` `[实测]` |
| 弹幕验证渲染时间错位 | `-ss` 在 `-i` 前归零 pts | 加 `-copyts` 保持原时间戳 `[实测]` |
| B站弹幕 XML 是乱码 | 接口恒定 brotli | curl 加 `--compressed` `[实测]` |
| TVBox jar 源导入 0 站点 | zyfun PC 只支持 cms json/xml + drpy js | 换 cms/drpy 接口 `[实测]` |
| WebUI 按文档写 ini 不起作用 | 8080 不监听 | 用 `--skip-dialog` 代替 API `[需复查]` |

## 文件清单

| 文件 | 用途 |
|---|---|
| README.txt | zyfun 内置 API 速查 + 已验证源/线路结论 |
| scripts/dm_fetch.sh | 批量拉 B 站弹幕 XML（brotli 解压） |
| scripts/dm_all.py | XML→ASS 转换，按 mp4 同名落盘 |
| scripts/dm_proof.ps1 | ffmpeg 渲一帧验证弹幕叠加 |
| scripts/add10.ps1 | 批量 `--skip-dialog` 加磁链 |
| scripts/add188.ps1 | 补漏单集（带完整 tracker 参数） |
| scripts/play4k_mpv.ps1 | mpv 打开下载目录里 >2G 的视频 |
| scripts/open195.ps1 / play4k.ps1 / play4k_web.ps1 | 各播放器拉起备选 |
| scripts/shot.ps1 | 截屏存 screen.png（验证 GUI 状态） |
| scripts/confirm.ps1 | AppActivate+回车确认对话框 |
| scripts/zyctl.ps1 / launch.ps1 | zyfun 状态/启动（explorer 会话） |
| scripts/play_test.py / line_test.py / stream_test.py | zyfun 全链路测速 |
| scripts/find4k.py / res_test.py / res2.sh / res3.sh | 线路分辨率探测 |
| scripts/player.html + hls.min.js | 本地 HLS 播放页（无播放器时的备胎） |
| scripts/probe*.bat/ps1、check_*.sh、speedtest.sh 等 | 过程性探测脚本，按需参考 |
