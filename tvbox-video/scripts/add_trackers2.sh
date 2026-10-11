#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
TR=$(curl -s --compressed -m 15 "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt" | head -30)
[ -z "$TR" ] && TR=$(curl -s -m 15 "https://gh-proxy.com/https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt" | head -30)
echo "$TR" | head -5; echo "... ($(echo "$TR" | wc -l) trackers)"
for H in $(curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "import json,sys;print(' '.join(t['hash'] for t in json.load(sys.stdin) if t['progress']<1))"); do
  curl -s -b /tmp/qbc "$B/torrents/addTrackers" --data-urlencode "hash=$H" --data-urlencode "urls=$TR" >/dev/null && echo "ok $H"
done
curl -s -b /tmp/qbc "$B/torrents/reannounce" -d "hashes=" >/dev/null
echo done
