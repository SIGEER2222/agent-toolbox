#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
TR='udp://tracker.opentrackr.org:1337/announce
udp://open.demonii.com:1337/announce
udp://tracker.torrent.eu.org:451/announce
udp://exodus.desync.com:6969/announce
udp://tracker.openbittorrent.com:6969/announce
udp://open.stealth.si:80/announce
udp://tracker.dler.org:6969/announce
http://tracker1.itzmx.com:8080/announce
udp://tracker.moeking.me:6969/announce
https://tracker.lilithraws.org:443/announce'
for H in $(curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "import json,sys;print(' '.join(t['hash'] for t in json.load(sys.stdin) if t['progress']<1))"); do
  curl -s -b /tmp/qbc "$B/torrents/addTrackers" --data-urlencode "hash=$H" --data-urlencode "urls=$TR" && echo " -> $H trackers added"
  curl -s -b /tmp/qbc "$B/torrents/reannounce" -d "hashes=$H"
done
echo done
