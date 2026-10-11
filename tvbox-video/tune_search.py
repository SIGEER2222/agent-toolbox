import json, urllib.request

BASE = "http://127.0.0.1:9978/api/v1"
# 本次搜索验证过的活源（能出结果）：9个命中凡人修仙传 + 建安(有返回无命中)
KEEP = ["电影天堂", "量子", "非凡", "尤酷", "极速", "百度", "暴風", "茶杯狐", "360", "建安"]

def req(method, path, body=None):
    r = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(r, timeout=15))

sites = []
for p in range(1, 10):
    d = req("GET", f"/film/site/page?pageNum={p}&pageSize=10").get("data") or {}
    lst = d.get("list") or []
    if not lst:
        break
    sites += lst

to_off, keep_names = [], []
for s in sites:
    name = s.get("name") or ""
    if any(k in name for k in KEEP):
        keep_names.append(name)
        if not s.get("search"):
            req("PUT", "/film/site", {"id": [s["id"]], "doc": {"search": True}})
            print("enable search:", name)
    else:
        if s.get("search"):
            to_off.append(s["id"])
            print("disable search:", name)

# 批量关掉死源搜索
for i in range(0, len(to_off), 10):
    r = req("PUT", "/film/site", {"id": to_off[i:i+10], "doc": {"search": False}})
    print("batch off ->", r.get("data") if isinstance(r.get("data"), bool) else "ok")

print("\nkept search-enabled:", len(keep_names))
for n in keep_names:
    print("  *", n)
