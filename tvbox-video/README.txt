zyfun（ZyPlayer 现名）3.4.7 — TVBox 生态 PC 播放器

安装：winget install HiramWong.zyfun（装于 %LOCALAPPDATA%\Programs\zyfun）

内置 API：http://127.0.0.1:9978/api/v1/  （无鉴权，CORS *）
- 导入 TVBox 接口：POST /data/db/import/simple  {"api":"<接口url>","putType":"overwrite|additional","remoteType":"tvbox"}
- 站点分页：GET /film/site/page?page=1&size=50 ；设默认源：PUT /film/site/default/{id}
- 直播分页：GET /live/iptv/page ；设默认：PUT /live/iptv/default/{id}
- 探测源是否活：GET /film/cms/home?uuid={siteId} （class>0 即活）；/film/cms/homeVod 拉片单
- 导出：POST /data/db/export {"type":["site","iptv","analyze","setting"]}

已导入（2026-10-10 验证可用）：
- 点播+直播+解析： https://qist.wyfc.qzz.io/jsm.json
- 追加：           https://tvbox-public.gaoops.top/
默认点播源：影视•极速[直连]（197集凡人，144KB/s实测）；默认直播：epg.pw m3u（9 个直播源含虎牙/斗鱼/B站）
超时已调：setting.timeout=30000（原 10000 对慢 CDN 不够）

播放线路规则（2026-10-10 实测）：
- 详情页线路选项卡里选 "*m3u8" 结尾的（bfzym3u8/dbm3u8/jsm3u8/ukm3u8/dyttm3u8/ffm3u8）= 直链，秒开
- dytt/feifan/ukyun/liangzi/jsyun 等 share 页线路要走应用嗅探，慢且可能失败
- 测速结果：暴風/百度/极速 最佳（playlist<1.5s、分片120-160KB/s）；尤酷/电影天堂/非凡较慢但可播
- 播放接口：GET /film/cms/play?uuid=&play=<$后的url>&flag=<线路名>
- play_test.py / line_test.py / stream_test.py 可随时重测全链路

启动注意：从 WSL 里 Start-Process 直拉会静默退出；
必须用 explorer.exe 拉进交互会话：powershell -File launch.ps1
zyctl.ps1：status/start/kill。
