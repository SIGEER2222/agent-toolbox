#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
echo "== tracker status per active torrent =="
for H in $(curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "import json,sys;print(' '.join(t['hash'] for t in json.load(sys.stdin) if t['progress']<1))"); do
  echo "--- $H"
  curl -s -b /tmp/qbc "$B/torrents/trackers?hash=$H" | python3 -c "
import json,sys
for t in json.load(sys.stdin):
    s={0:'disabled',1:'idle',2:'working',3:'updating',4:'error',5:'?'}
    print(' ',s.get(t['status'],t['status']), t['num_peers'], t['url'][:55])"
done
