import json, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:9978/api/v1"
SITES = [
    ("f6b0662e-3b3d-4c82-8ca1-1c6993204378", "电影天堂"),
    ("510e3292-bdca-43c8-8b94-e43256e02f5c", "量子"),
    ("32f26814-96b2-48c6-9e99-4b220b13ab68", "非凡"),
    ("e62f5480-5d8a-4ffe-9472-d9a744e46302", "尤酷"),
    ("125f3b64-9169-4b6d-b505-1cf455305f86", "极速"),
    ("886d5097-0b56-48c4-bfc6-1711c9df1f9c", "百度"),
    ("d2345c83-f4ce-4027-9d2a-ec1e72442bf3", "暴風"),
    ("de0cc1ab-ca97-4feb-8430-68f22d5444cb", "建安"),
]

def api(path, timeout=60):
    r = urllib.request.urlopen(BASE + path, timeout=timeout)
    return json.load(r)

def check_url(url):
    """返回 (是否直链m3u8, 说明)"""
    u = url.lower()
    if ".m3u8" in u:
        return True, "m3u8"
    if "/share/" in u or "/play/" in u:
        return False, "share-page"
    return None, "other:" + u[-30:]

def test(sid, name):
    try:
        d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": sid, "wd": "凡人修仙传"}))
        hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
        if not hits:
            return name, "no-hit", []
        dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": sid, "ids": str(hits[0]["vod_id"])}))
        v = ((dd.get("data") or {}).get("list") or [{}])[0]
        lines = (v.get("vod_play_from") or "").split("$$$")
        urls = (v.get("vod_play_url") or "").split("$$$")
        rows = []
        for i, ln in enumerate(lines):
            eps = (urls[i] if i < len(urls) else "").split("#")
            eps195 = [e for e in eps if "195" in e]
            ep = (eps195[0] if eps195 else (eps[-1] if eps else ""))
            epurl = ep.split("$", 1)[1] if "$" in ep else ep
            direct, kind = check_url(epurl)
            rows.append(f"{ln.strip()}[{kind}] ep={ep.split('$')[0]} total_eps={len(eps)}")
        return name, v.get("vod_remarks"), rows
    except Exception as e:
        return name, "EXC " + str(e)[:60], []

with ThreadPoolExecutor(8) as ex:
    for name, remark, rows in ex.map(lambda s: test(*s), SITES):
        print(f"== {name} ({remark})")
        for r in rows:
            print("   ", r)
