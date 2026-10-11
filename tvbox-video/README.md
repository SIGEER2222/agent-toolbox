# 凡人修仙传 观看/下载/弹幕 全流程手册

本目录存放所有脚本。两条观看路线：**在线看**走 zyfun（省事、最高 1080p、有广告段），
**下载看**走 qBittorrent+mpv（4K B站高码率、无广告、可叠弹幕）。

---

## 一、在线看：zyfun（ZyPlayer）

- 安装：`winget install HiramWong.zyfun`
- 详细 API 用法与已配源见 `README.txt`
- 搜索「凡人修仙传」→ 详情 → 线路选 `*m3u8` 结尾的（jsm3u8 最全最快）→ 点播
- 采集站片头烧入广告属正常，几秒后进正片；上限 1080p，无 4K

## 二、4K 下载流程（已验证 2026-10-11）

### 2.1 找磁链

- 聚合页：`https://www.ku0.cc/1214`（凡人修仙传 4K 2160p 全季分集磁链+网盘，每周更新）
- 备选：nyaa.si 搜 `凡人修仙传`（Doomdos 发布组，[4K BILIBILI COM WEB-DL]，
  3840×2160 h264 ~21Mbps ~2.9G/集）——国内直连打不开页面，但磁链照样能下（DHT/PEX）
- 网盘备选：夸克 `pan.quark.cn/s/c737dd5a9484`（更到 188，HEVC 版体积更小）

### 2.2 安装并配置 qBittorrent

```
winget install -e --id qBittorrent.qBittorrent
```

配置 `%APPDATA%\qBittorrent\qBittorrent.ini` 的 `[BitTorrent]` 段（已配好）：

```ini
Session\InterfaceName=以太网        ; 绑定物理网卡，不走 WireGuard/VPN 隧道
Session\InterfaceAddress=192.168.1.3
Session\GlobalUPLimit=300           ; 上传限速 300KB/s，保护流量套餐
```

### 2.3 批量添加磁链（免对话框）

```powershell
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe" `
  -ArgumentList "--skip-dialog", "`"magnet:?xt=urn:btih:<HASH>`""
```

- `--skip-dialog` 静默添加，循环调用即可批量（见 `add10.ps1`）
- 注意磁链最好带 `&tr=` tracker 参数；裸 hash 只能靠 DHT 摸 peer，小种子很慢
- 验证：`%LOCALAPPDATA%\qBittorrent\BT_backup\` 出现 `<hash>.torrent` + `.fastresume`
- 下载目录默认 `~\Downloads`；`du -h <file>` 看真实已下（预分配文件显示全尺寸）

## 三、弹幕下载与转换（已验证）

### 3.1 拿每集的 cid

```bash
# 搜索番剧 → season_id（凡人修仙传 = 28747）
curl "https://api.bilibili.com/x/web-interface/search/type?keyword=凡人修仙传&search_type=media_bangumi" -A "Mozilla/5.0"
# 拉分集列表，每集有 ep_id/aid/cid/title
curl "https://api.bilibili.com/pgc/view/web/season?season_id=28747" -A "Mozilla/5.0"
```

注意：同一 title 可能出现两组 ep（正片 vs 抢先看等），选 `maxlimit` 大（3000）
的那组 cid——danmaku 多的才是主播放源。

### 3.2 拉弹幕 XML

```bash
curl --compressed -A "Mozilla/5.0" -H "Referer: https://www.bilibili.com/" \
  "https://comment.bilibili.com/<CID>.xml" -o dm.xml
```

- **必须 `--compressed`**：该接口恒定返回 brotli 压缩，不解是乱码
- 直连可达，无需代理；单集 ~340KB / ~3600 条

### 3.3 转 ASS：`dm_all.py`

- XML `<d p="秒,模式,字号,颜色,...">` → ASS `Dialogue`：
  - 模式 1/2/3 右→左滚动，6 左→右，5 顶固定，4 底固定，7/8/9 跳过
  - PlayResX/Y 按片源分辨率（4K=3840×2160），泳道避让
- **坑**：ASS 花括号不能嵌套——颜色写 `\c&HFFFFFF` 不要再套 `{}`，否则 `}` 变成可见字符
- 输出与 mp4 同目录同名 `.ass`，mpv 自动加载（sub-auto=fuzzy 默认开）
- 验证渲染：`ffmpeg -ss <秒> -copyts -i video.mp4 -vf "ass='C:/path/x.ass'" -frames:v 1 out.png`
  - **坑**：`-ss` 放在 `-i` 前会把时间戳归零，弹幕错位；加 `-copyts` 保持原 pts

## 四、播放

- mpv（推荐，硬解+进度条）：`winget install shinchiro.mpv` → `C:\Program Files\MPV Player\mpv.exe`
- 双击 mp4 即播；快捷键：空格暂停，←→ ±5s，↑↓ ±60s，PgUp/PgDn ±10min，F 全屏，v 切字幕轨（开关弹幕）
- ffplay 备用（winget `Gyan.FFmpeg`）：只能键盘 seek，无鼠标进度条

## 五、网络避坑（Clash 环境实测）

- 系统代理开着（`127.0.0.1:7897`）时：**浏览器、zyfun(Electron) 走代理烧 Clash 流量**；
  curl/ffmpeg/qBittorrent/mpv/Devin 会话都不读系统代理，天然直连
- 视频 CDN 域名已写入 `HKCU\...\Internet Settings\ProxyOverride` 绕过：
  `*.jisuzyv.com;*.jisuts.com;*.dytt-hot.com;*.lzfile26.com;*.ffzy-plays.com;*.ukubf3.com;*.bdzybf22.com;*.fengbao13.com`
  —— Clash Verge 切换系统代理时可能重写该名单，永久生效要在 Verge「系统代理→绕过域名」里也加一份
- Clash TUN 模式一开全流量接管（绕过名单无效），确认关着
- WireGuard 隧道 zzq1(10.66.66.9) 不兜全网路由；验证出口：`curl ip-api.com/json`

## 六、WSL/cmd 操作坑（本机实测）

- exec 会**剥离 `$变量`**——所有含变量的循环一律写成脚本文件再跑
- .bat 只写 ASCII：UTF-8 中文被 cmd 按 ANSI 读 → 路径报错
- .ps1 里中文 `-like "*第195话*"` 同样会被 ANSI 读坏 → 用数字/大小匹配替代（如 `*195*`、`-gt 2GB`）
- Windows ffmpeg/ffprobe **不认 /mnt 路径**，输出要写 `C:\...`；image2 单帧输出要 `-update 1`
- 拉 GUI 程序（播放器/应用）必须 `explorer.exe "path"` 进交互会话；`Start-Process`/`cmd /c` 直拉可能静默退出或窗口不现身
- 确认 GUI 对话框：ps1 里 `wscript.shell AppActivate + SendKeys("{ENTER}")`

## 七、出新集怎么续

1. ku0.cc/1214 抓最新磁链 → `add10.ps1` 模式 `--skip-dialog` 加进 qBittorrent
2. `python3 -c` 查 season JSON 拿新 cid → `dm_fetch.sh`/`dm_all.py` 跑一遍出 .ass
3. mpv 双击直接看（弹幕自动叠）

## 脚本清单

| 文件 | 用途 |
|---|---|
| dm_fetch.sh | 批量拉 B 站弹幕 XML（brotli 解压） |
| dm_all.py | XML→ASS 转换，按 mp4 同名落盘 |
| dm_proof.ps1 | ffmpeg 渲一帧验证弹幕叠加 |
| add10.ps1 | 批量 `--skip-dialog` 加磁链 |
| add188.ps1 | 补漏单集（带完整 tracker 参数） |
| play4k_mpv.ps1 | mpv 打开 Downloads 里 >2G 的视频 |
| open195.ps1 / play4k.ps1 / play4k_web.ps1 | 各播放器拉起备选 |
| shot.ps1 | 截屏存 screen.png（验证 GUI 状态） |
| confirm.ps1 | AppActivate+回车确认对话框 |
| zyctl.ps1 / launch.ps1 | zyfun 状态/启动（explorer 会话） |
| play_test.py / line_test.py / stream_test.py | zyfun 全链路测速 |
| find4k.py / res_test.py / res2.sh / res3.sh | 线路分辨率探测 |
