import json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
BASE = "http://127.0.0.1:9978/api/v1"

def api(path, timeout=45):
    return json.load(urllib.request.urlopen(BASE + path, timeout=timeout))

sites = []
for p in range(1, 8):
    d = api(f"/film/site/page?pageNum={p}&pageSize=10").get("data") or {}
    lst = d.get("list") or []
    if not lst:
        break
    sites += lst
print("total sites:", len(sites))

def probe(s):
    nm = s.get("name") or ""
    try:
        d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": s["id"], "wd": "凡人修仙传"}), 30)
        hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
        if not hits:
            return None
        dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": s["id"], "ids": str(hits[0]["vod_id"])}), 30)
        v = ((dd.get("data") or {}).get("list") or [{}])[0]
        flags = (v.get("vod_play_from") or "")
        remarks = v.get("vod_remarks") or ""
        pic_note = ""
        return f"{nm} [{s['id'][:8]}] hits={len(hits)} remarks={remarks} flags={flags}"
    except Exception:
        return None

with ThreadPoolExecutor(12) as ex:
    for r in ex.map(probe, sites):
        if r:
            print(r)
