import json, time, urllib.request, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
API = "http://127.0.0.1:9978/api/v1"

def req(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=timeout)

# get site list, find a fast cms source
sites = json.load(req(API + "/site/list"))
uid = None
for s in sites.get("data", sites if isinstance(sites, list) else []):
    if s.get("name") and "极速" in s.get("name", ""):
        uid = s.get("id"); break
if not uid:
    for s in sites.get("data", []):
        uid = s.get("id"); break
print("site uid:", uid)

# search for the show, get detail, list play lines
det = json.load(req(API + f"/film/cms/search?uuid={uid}&wd=%E5%87%A1%E4%BA%BA%E4%BF%AE%E4%BB%99%E4%BC%A0&pageNum=1&pageSize=5"))
rows = det.get("data", {}).get("list") or det.get("data", [])
target = None
for r in rows:
    if "凡人修仙传" in (r.get("vod_name") or r.get("name") or ""):
        target = r; break
if not target and rows: target = rows[0]
tid = target.get("vod_id") or target.get("id")
print("vod:", target.get("vod_name"), tid)

d = json.load(req(API + f"/film/cms/detail?uuid={uid}&ids={tid}"))
dlist = d.get("data", {}).get("list") or d.get("data", [])
v = dlist[0] if dlist else d.get("data", {})
from_url = v.get("vod_play_from") or ""
play_url = v.get("vod_play_url") or ""
flags = from_url.split("$$$") if isinstance(from_url, str) else []
blocks = play_url.split("$$$") if isinstance(play_url, str) else []
print("lines:", flags)

# for each m3u8 flag, take ep195 url and speed-test first segment
out = {}
for i, f in enumerate(flags):
    if "m3u8" not in f or i >= len(blocks):
        continue
    eps = blocks[i].split("#")
    ep = next((e for e in eps if "195" in e), eps[-1])
    url = ep.split("$")[-1]
    try:
        t0 = time.time()
        pl = req(url, 15).read().decode("utf-8", "ignore")
        t1 = time.time()
        seg = next((l for l in pl.splitlines() if l.strip() and not l.startswith("#")), None)
        if seg and not seg.startswith("http"):
            from urllib.parse import urljoin
            seg = urljoin(url, seg)
        t2 = time.time()
        data = req(seg, 25).read()
        t3 = time.time()
        spd = len(data) / max(t3 - t2, 0.01) / 1024
        out[f] = (round(t1 - t0, 2), len(data) // 1024, round(spd), url)
        print(f, "playlist", round(t1-t0,2), "s; seg", len(data)//1024, "KB;", round(spd), "KB/s")
    except Exception as e:
        print(f, "FAIL", str(e)[:80])
print(json.dumps(out, ensure_ascii=False))
