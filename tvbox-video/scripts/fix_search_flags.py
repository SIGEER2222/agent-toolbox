import json, urllib.request

BASE = "http://127.0.0.1:9978/api/v1"
GOOD = ["电影天堂", "尤酷", "暴風", "极速", "量子", "非凡", "百度", "茶杯狐", "360"]

sites = []
for p in range(1, 10):
    d = json.load(urllib.request.urlopen(f"{BASE}/film/site/page?pageNum={p}&pageSize=10", timeout=10)).get("data") or {}
    lst = d.get("list") or []
    if not lst:
        break
    sites += lst

for s in sites:
    if any(g in (s.get("name") or "") for g in GOOD):
        print(s["id"], "| t%s" % s["type"], "|", s["name"], "| search=", s.get("search"), "| active=", s.get("isActive"))
        if not s.get("search"):
            body = json.dumps({**s, "search": True}).encode()
            req = urllib.request.Request(f"{BASE}/film/site", data=body, method="PUT", headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=10))
            print("   -> enabled search:", r.get("data"))
