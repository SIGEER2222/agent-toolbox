#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
echo "== torrents =="
curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "
import json,sys
for t in json.load(sys.stdin):
    print('%-8s %-12s %5.1f%%  dl=%6.0fKB/s up=%4.0fKB/s seeds=%d peers=%d  %s' % (
        t['hash'][:8], t['state'], t['progress']*100, t['dlspeed']/1024,
        t['upspeed']/1024, t['num_seeds'], t['num_leechs'], t['name'][:40]))
"
echo "== trackers per torrent (first) =="
H=$(curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "import json,sys;print(json.load(sys.stdin)[0]['hash'])")
curl -s -b /tmp/qbc "$B/torrents/trackers?hash=$H" | python3 -c "
import json,sys
for t in json.load(sys.stdin): print(t['status'], t['url'])"
