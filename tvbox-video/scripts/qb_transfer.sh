#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
curl -s -b /tmp/qbc "$B/transfer/info" | python3 -m json.tool
echo "== speeds now =="
curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "
import json,sys
tot=0
for t in json.load(sys.stdin):
    if t['progress']<1:
        tot+=t['dlspeed']
        print('%-4s %5.1f%% dl=%5.0fKB/s seeds=%d peers=%d %s'%(t['hash'][:4],t['progress']*100,t['dlspeed']/1024,t['num_seeds'],t['num_leechs'],t['name'][30:50]))
print('TOTAL DL: %.0f KB/s'%(tot/1024))"
