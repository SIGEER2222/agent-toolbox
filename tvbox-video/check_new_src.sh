#!/bin/bash
check() {
  local url="$1"
  local body code
  body=$(curl -sL --connect-timeout 8 --max-time 25 -A "okhttp/3.15" -w '\n__CODE__%{http_code}' "$url" 2>/dev/null)
  code=$(echo "$body" | grep -o '__CODE__[0-9]*' | grep -o '[0-9]*')
  body=$(echo "$body" | sed 's/__CODE__[0-9]*$//')
  local keys size
  size=${#body}
  keys=$(echo "$body" | head -c 6000 | tr '\n' ' ' | grep -o '"\(sites\|lives\|urls\|spider\|parses\)"' | sort -u | tr '\n' ',')
  # 判定：有 sites 或 urls 才算有效 tvbox 配置
  if [ "$code" = "200" ] && [ "$size" -gt 200 ] && echo "$keys" | grep -qE 'sites|urls'; then
    echo "LIVE  $url  size=$size keys=[$keys]"
  else
    echo "dead  $url  code=${code:-0} size=$size keys=[$keys]"
  fi
}
export -f check
cat <<'EOF' | xargs -P8 -I{} bash -c 'check "{}"'
http://www.饭太硬.net/tv
https://gh-proxy.org/https://raw.githubusercontent.com/ggrrttyyiii/CatVodSpider/refs/heads/main/json/demo.json
https://sscq-pay.kingnet.com/static/test.json
http://肥猫.net/tv
https://9280.kstore.vip/newwex.json
http://hb.小虎斑.site:25252/仅供测试
https://g.33445500.xyz/https://raw.githubusercontent.com/qist/tvbox/refs/heads/master/jsm.json
https://ym.wya6.cn/
https://gitee.com/cpu-iy/iy/raw/master/%E5%A4%A9%E7%A5%9EIY.json
http://rihou.cc:88/demo.php
https://欧歌.v.nxog.top/m/
http://fmys.top/fmys.json
https://宝盒接口.top
https://gh-proxy.com/https://raw.githubusercontent.com/yoursmile66/TVBox/main/XC.json
https://www.cttv.vip/ys/json/ctys.json
https://7337.kstore.space/qxys/%E7%A6%81%E6%AD%A2%E4%BC%A0%E6%92%AD.json
http://w.7080.wang/tv/1.json
https://gist.githubusercontent.com/ph7368/20ee6c7b64d77d82f8f4162cdd04ad61/raw/gistfile1.txt
http://影视仓.com/
EOF
