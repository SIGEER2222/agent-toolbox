import json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:9978/api/v1"
SITES = [  # 10 个 search=true 源
    ("f6b0662e-3b3d-4c82-8ca1-1c6993204378", "电影天堂"),
    ("510e3292-bdca-43c8-8b94-e43256e02f5c", "量子"),
    ("32f26814-96b2-48c6-9e99-4b220b13ab68", "非凡"),
    ("e62f5480-5d8a-4ffe-9472-d9a744e46302", "尤酷"),
    ("125f3b64-9169-4b6d-b505-1cf455305f86", "极速"),
    ("886d5097-0b56-48c4-bfc6-1711c9df1f9c", "百度"),
    ("d2345c83-f4ce-4027-9d2a-ec1e72442bf3", "暴風"),
    ("ebaa6bb4-f557-4d66-9565-918e56237957", "茶杯狐"),
    ("33690acf-0b64-40e3-af9e-100c5180de49", "官源360"),
    ("de0cc1ab-ca97-4feb-8430-68f22d5444cb", "建安"),
]

def api(path, timeout=60):
    t0 = time.time()
    r = urllib.request.urlopen(BASE + path, timeout=timeout)
    return time.time() - t0, json.load(r)

def head(url, timeout=20):
    try:
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-64", "User-Agent": "Mozilla/5.0"})
        t0 = time.time()
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read(64)
        return round(time.time() - t0, 1), r.status, body[:40]
    except Exception as e:
        return -1, str(e)[:60], b""

def test_site(sid, name):
    if not sid:
        return (name, "skip", "", 0, "")
    try:
        # 1 search
        t, d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": sid, "wd": "凡人修仙传"}))
        hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
        if not hits:
            return (name, "no-hit", "", round(t, 1), "")
        vod = hits[0]
        # 2 detail
        t2, dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": sid, "ids": str(vod["vod_id"])}))
        vlist = (dd.get("data") or {}).get("list") or []
        if not vlist:
            return (name, "no-detail", "", round(t2, 1), "")
        v = vlist[0]
        lines = (v.get("vod_play_from") or "").split("$$$")
        playurl = (v.get("vod_play_url") or "").split("$$$")
        # 找含195的线
        best = None
        for i, ln in enumerate(lines):
            eps = (playurl[i] if i < len(playurl) else "").split("#")
            for ep in eps:
                if "$" in ep:
                    epname, epurl = ep.split("$", 1)
                    if "195" in epname:
                        best = (ln.strip(), ep.strip())
                        break
            if best:
                break
        if not best:
            # 没195, 取第一线最后一集
            for i, ln in enumerate(lines):
                eps = (playurl[i] if i < len(playurl) else "").split("#")
                if eps and "$" in eps[-1]:
                    best = (ln.strip(), eps[-1].strip())
                    break
        if not best:
            return (name, "no-eps", v.get("vod_remarks"), round(t + t2, 1), "")
        flag, ep = best
        epurl = ep.split("$", 1)[1] if "$" in ep else ep
        # 3 play
        t3, pr = api("/film/cms/play?" + urllib.parse.urlencode({"uuid": sid, "play": epurl, "flag": flag}))
        pd = pr.get("data") or {}
        url = pd.get("url") or ""
        ptype = pd.get("type") or pd.get("mediaType") or ""
        if not url:
            return (name, "play-empty", f"flag={flag} ep={ep[:20]}", round(t3, 1), json.dumps(pd)[:80])
        # 4 校验流地址
        ht, code, body = head(url)
        ok = code == 200 or code == 206
        head_info = f"{code} {body[:20]!r}" if ok else str(code)
        return (name, "OK" if ok else "stream-fail", f"flag={flag} ep={ep.split('$')[0]}", round(t + t2 + t3, 1), f"{url[:80]} -> {head_info} ({ht}s)")
    except Exception as e:
        return (name, "EXC", "", 0, str(e)[:100])

with ThreadPoolExecutor(6) as ex:
    results = list(ex.map(lambda s: test_site(*s), SITES))
for name, st, info, secs, extra in sorted(results, key=lambda r: r[1] != "OK"):
    print(f"{st:11} {name:6} {secs:>6}s {info} {extra}")
