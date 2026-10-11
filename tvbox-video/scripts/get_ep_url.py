import json, urllib.request, urllib.parse

BASE = "http://127.0.0.1:9978/api/v1"
sid = "125f3b64-9169-4b6d-b505-1cf455305f86"  # 极速

d = json.load(urllib.request.urlopen(
    BASE + "/film/cms/search?" + urllib.parse.urlencode({"uuid": sid, "wd": "凡人修仙传"}), timeout=30)).get("data") or {}
hits = [v for v in d.get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
print("hits:", [(h.get("vod_name"), h.get("vod_remarks")) for h in hits])

dd = json.load(urllib.request.urlopen(
    BASE + "/film/cms/detail?" + urllib.parse.urlencode({"uuid": sid, "ids": str(hits[0]["vod_id"])}), timeout=30)).get("data") or {}
v = (dd.get("list") or [{}])[0]
lines = (v.get("vod_play_from") or "").split("$$$")
urls = (v.get("vod_play_url") or "").split("$$$")
for i, ln in enumerate(lines):
    if ln.strip() == "jsm3u8":
        eps = urls[i].split("#")
        print("line:", ln.strip(), "eps:", len(eps))
        for e in eps[:3] + eps[-3:]:
            print("  ", e)
        # 取最新一集
        last = eps[-1]
        epurl = last.split("$", 1)[1] if "$" in last else last
        print("LATEST:", last.split("$")[0], "->", epurl)
