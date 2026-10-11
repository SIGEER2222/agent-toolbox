#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
curl -s -b /tmp/qbc "$B/app/preferences" -o /tmp/prefs.json
python3 -c "
import json
d=json.load(open('/tmp/prefs.json'))
for k in sorted(d):
    if any(x in k.lower() for x in ['limit','speed','schedul','queue','connect','alt','rate']):
        print(k,'=',d[k])"
