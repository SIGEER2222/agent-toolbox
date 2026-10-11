import json, urllib.request, urllib.parse
BASE = "http://127.0.0.1:9978/api/v1"

def api(path, timeout=60):
    return json.load(urllib.request.urlopen(BASE + path, timeout=timeout))

sites = []
for p in range(1, 7):
    d = api(f"/film/site/page?pageNum={p}&pageSize=10").get("data") or {}
    lst = d.get("list") or []
    if not lst:
        break
    sites += lst

for s in sites:
    nm = s.get("name") or ""
    if any(k in nm for k in ["茶杯", "360", "官源", "iQIYI", "腾讯", "优酷"]):
        try:
            d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": s["id"], "wd": "凡人修仙传"}))
            hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人" in (v.get("vod_name") or "")]
            print("==", nm, s["id"], "hits:", len(hits))
            if hits:
                dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": s["id"], "ids": str(hits[0]["vod_id"])}))
                v = ((dd.get("data") or {}).get("list") or [{}])[0]
                print("   flags:", (v.get("vod_play_from") or ""))
        except Exception as e:
            print("==", nm, "ERR", str(e)[:60])
