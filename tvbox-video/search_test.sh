#!/bin/bash
python3 - <<'PY' > /tmp/zy_sites.txt
import json, urllib.request, sys
seen={}
for p in range(1,10):
    try:
        r=urllib.request.urlopen("http://127.0.0.1:9978/api/v1/film/site/page?pageNum=%d&pageSize=10"%p, timeout=10)
        d=json.load(r).get('data') or {}
        lst=d.get('list') or []
        if not lst: break
        for s in lst:
            seen[s['id']]="%s\t%s\t%s"%(s['id'],s['type'],s['name'])
    except Exception as e:
        print("page%d err %s"%(p,e), file=sys.stderr); break
print("\n".join(seen.values()))
PY
wc -l /tmp/zy_sites.txt

test_one() {
  IFS=$'\t' read -r id typ name <<< "$1"
  res=$(curl -s --connect-timeout 8 --max-time 45 -G "http://127.0.0.1:9978/api/v1/film/cms/search" \
        --data-urlencode "uuid=$id" --data-urlencode "wd=凡人修仙传" 2>/dev/null)
  echo "$res" | python3 -c "
import json,sys
name='$name'; typ='$typ'
try:
    d=json.load(sys.stdin).get('data') or {}
    lst=d.get('list') or []
    hits=[v for v in lst if '凡人' in (v.get('vod_name') or '')]
    if hits:
        remarks=' / '.join(sorted({(v.get('vod_remarks') or '') for v in hits})[:4])
        print('HIT\tt%s\t%s\t%d hits\t%s' % (typ,name,len(hits),remarks))
    else:
        print('miss\tt%s\t%s\t%d results' % (typ,name,len(lst)))
except Exception as e:
    print('ERR\tt%s\t%s\t%s' % (typ,name,str(e)[:60]))
"
}
export -f test_one
grep -v '^$' /tmp/zy_sites.txt | xargs -P8 -I{} bash -c 'test_one "$@"' _ {}
