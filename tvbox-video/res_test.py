import json, urllib.request, urllib.parse, subprocess
BASE = "http://127.0.0.1:9978/api/v1"
FFPROBE = r"C:\Users\22448\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
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
    return json.load(urllib.request.urlopen(BASE + path, timeout=timeout))

def probe_res(url):
    try:
        p = subprocess.run([FFPROBE, "-hide_banner", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", "-read_intervals", "%+8", url],
                           capture_output=True, text=True, timeout=40)
        for line in p.stdout.splitlines():
            if "," in line and line.split(",")[0].isdigit():
                return line.strip()
        return "?"
    except Exception:
        return "timeout"

for sid, name in SITES:
    try:
        d = api("/film/cms/search?" + urllib.parse.urlencode({"uuid": sid, "wd": "凡人修仙传"}))
        hits = [v for v in (d.get("data") or {}).get("list") or [] if "凡人修仙传" in (v.get("vod_name") or "")]
        if not hits:
            print(name, "no-hit"); continue
        dd = api("/film/cms/detail?" + urllib.parse.urlencode({"uuid": sid, "ids": str(hits[0]["vod_id"])}))
        v = ((dd.get("data") or {}).get("list") or [{}])[0]
        flags = (v.get("vod_play_from") or "").split("$$$")
        urls = (v.get("vod_play_url") or "").split("$$$")
        print("==", name, "flags:", flags)
        for i, f in enumerate(flags):
            if i >= len(urls):
                continue
            eps = urls[i].split("#")
            ep = next((e for e in eps if "195" in e), eps[-1] if eps else "")
            u = ep.split("$")[-1]
            if ".m3u8" in u:
                res = probe_res(u)
                print("   ", f, "->", res, "|", u[:60])
    except Exception as e:
        print(name, "ERR", str(e)[:70])
