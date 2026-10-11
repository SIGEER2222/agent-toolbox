#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
# hashes of eps 185-189 (from torrents info by name match)
HS=$(curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "
import json,sys
out=[]
for t in json.load(sys.stdin):
    for ep in ('185','186','187','188','189'):
        if ('第%s话'%ep) in t['name'] or ('%d话'%int(ep)) in t['name']:
            out.append(t['hash'])
print('|'.join(out))")
echo "deleting hashes: $HS"
curl -s -b /tmp/qbc "$B/torrents/delete" -d "hashes=$HS&deleteFiles=true"
echo
sleep 2
curl -s -b /tmp/qbc "$B/torrents/info" | python3 -c "
import json,sys
for t in json.load(sys.stdin):
    print('%-4s %5.1f%% %s'%(t['hash'][:4],t['progress']*100,t['name'][:45]))"
