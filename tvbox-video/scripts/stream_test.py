import json, urllib.request, urllib.parse, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:9978/api/v1"
CASES = [
    ("d2345c83-f4ce-4027-9d2a-ec1e72442bf3", "暴風", "bfzym3u8"),
    ("886d5097-0b56-48c4-bfc6-1711c9df1f9c", "百度", "dbm3u8"),
    ("125f3b64-9169-4b6d-b505-1cf455305f86", "极速", "jsm3u8"),
    ("e62f5480-5d8a-4ffe-9472-d9a744e46302", "尤酷", "ukm3u8"),
    ("f6b0662e-3b3d-4c82-8ca1-1c6993204378", "电影天堂", "dyttm3u8"),
    ("32f26814-96b2-48c6-9e99-4b220b13ab68", "非凡", "ffm3u8"),
]

def api(path, timeout=60):
    r = urllib.request.urlopen(BASE + path, timeout=timeout)
    return json.load(r)

def fetch(url, timeout=20, rng=200000):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes=0-{rng}"})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=timeout)
    data = r.read()
    return time.time() - t0, r.status, data

def test(sid, name, flag):
    try:
        d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": sid, "wd": "凡人修仙传"}))
        hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
        if not hits:
            return name, flag, "no-hit"
        dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": sid, "ids": str(hits[0]["vod_id"])}))
        v = ((dd.get("data") or {}).get("list") or [{}])[0]
        lines = (v.get("vod_play_from") or "").split("$$$")
        urls = (v.get("vod_play_url") or "").split("$$$")
        epurl = None
        for i, ln in enumerate(lines):
            if ln.strip() == flag:
                eps = (urls[i] if i < len(urls) else "").split("#")
                pick = [e for e in eps if "195" in e] or eps[-1:]
                epurl = pick[0].split("$", 1)[1] if "$" in pick[0] else pick[0]
                break
        if not epurl:
            return name, flag, "no-line"
        # m3u8 playlist
        t1, code, pl = fetch(epurl)
        if b"#EXTM3U" not in pl[:200]:
            return name, flag, f"playlist bad: {pl[:60]!r}"
        segs = [l.strip() for l in pl.decode("utf-8", "ignore").splitlines() if l and not l.startswith("#")]
        if not segs:
            return name, flag, "playlist empty"
        seg0 = urllib.parse.urljoin(epurl, segs[0])
        t2, code2, dat = fetch(seg0)
        speed = len(dat) / max(t2, 0.1) / 1024
        return name, flag, f"OK playlist({t1:.1f}s {len(segs)}segs) seg0({t2:.1f}s {len(dat)//1024}KB {speed:.0f}KB/s {code2})"
    except Exception as e:
        return name, flag, "EXC " + str(e)[:80]

with ThreadPoolExecutor(6) as ex:
    for name, flag, res in ex.map(lambda s: test(*s), CASES):
        print(f"{name:6} {flag:10} {res}")
