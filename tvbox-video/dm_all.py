# -*- coding: utf-8 -*-
import urllib.request, re, os, glob, html

DL = "/mnt/c/Users/22448/Downloads"
UA = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate",
      "Referer": "https://www.bilibili.com/"}
EPS = {185:40480868938,186:40698383030,187:40920682135,188:41140749663,
       189:41804826860,190:41805680522,191:41806202889,192:42011328801,
       193:42426632174,194:42360308036,195:42607054789}
import gzip

def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)
    data = r.read()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data

def esc(s):
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

def color_hex(c):
    c = int(c) & 0xFFFFFF
    return "&H%02X%02X%02X" % (c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF)

W, H = 3840, 2160
FS = 64          # 基准字号
SCROLL_S = 13.0  # 滚动穿越秒数
FIX_S = 5.0      # 顶/底部固定秒数
LANES = 18

def convert(xml_bytes, out_path):
    txt = xml_bytes.decode("utf-8", "ignore")
    items = []
    for m in re.finditer(r'<d p="([^"]+)"[^>]*>(.*?)</d>', txt, re.S):
        p = m.group(1).split(",")
        if len(p) < 4:
            continue
        try:
            st, mode, fs, col = float(p[0]), int(p[1]), int(p[2]), int(p[3])
        except ValueError:
            continue
        text = html.unescape(m.group(2)).strip()
        if not text or mode in (7, 8, 9):
            continue
        items.append((st, mode, fs, col, text))
    items.sort()
    lane_end = [0.0] * LANES      # 滚动弹幕每泳道占用结束时间
    top_end = [0.0] * 6
    bot_end = [0.0] * 6
    lines = []
    for st, mode, fs, col, text in items:
        size = max(30, int(FS * fs / 25))
        coltag = "\\c%s" % color_hex(col)
        t1 = st
        if mode in (1, 2, 3, 6):   # 滚动
            dur = SCROLL_S
            t2 = st + dur
            # 找最早空出的泳道
            lane = min(range(LANES), key=lambda i: lane_end[i])
            if lane_end[lane] > st:
                # 挤一挤也要放：选最早结束的道
                pass
            lane_end[lane] = max(lane_end[lane], t2) if lane_end[lane] < t2 else lane_end[lane]
            lane_end[lane] = st + dur * 0.35  # 近似放行间隔
            y = 60 + lane * (size + 10)
            if mode == 6:   # 左到右
                mov = "\\move(%d,%d,%d,%d)" % (-600, y, W + 600, y)
            else:
                mov = "\\move(%d,%d,%d,%d)" % (W + 600, y, -600 - len(text) * size, y)
            eff = "{\\an8\\fs%d\\bord2\\shad0%s%s}" % (size, mov, coltag)
        elif mode == 5:    # 顶部固定
            lane = min(range(6), key=lambda i: top_end[i])
            top_end[lane] = st + FIX_S
            y = 40 + lane * (size + 8)
            eff = "{\\an8\\fs%d\\bord2\\shad0\\pos(%d,%d)%s}" % (size, W // 2, y, coltag)
            t2 = st + FIX_S
        elif mode == 4:    # 底部固定
            lane = min(range(6), key=lambda i: bot_end[i])
            bot_end[lane] = st + FIX_S
            y = H - 80 - lane * (size + 8)
            eff = "{\\an2\\fs%d\\bord2\\shad0\\pos(%d,%d)%s}" % (size, W // 2, y, coltag)
            t2 = st + FIX_S
        else:
            continue
        fmt = lambda s: "%d:%02d:%05.2f" % (int(s // 3600), int(s % 3600 // 60), s % 60)
        lines.append("Dialogue: 0,%s,%s,Dm,,0,0,0,,%s%s" % (fmt(t1), fmt(t2), eff, esc(text)))
    hdr = ("[Script Info]\nTitle: danmaku\nScriptType: v4.00+\n"
           "PlayResX: %d\nPlayResY: %d\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
           "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
           "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           "Style: Dm,Microsoft YaHei,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
           "1,0,0,0,100,100,0,0,1,2,0,7,20,20,20,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
           % (W, H))
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write(hdr + "\n".join(lines) + "\n")
    return len(items)

for ep, cid in EPS.items():
    xp = "/tmp/dm_%d.xml" % ep
    if not os.path.exists(xp):
        print(ep, "xml missing")
        continue
    xml = open(xp, "rb").read()
    mp4s = [p for p in glob.glob(DL + "/*.mp4") if ("第%d话" % ep) in os.path.basename(p)]
    if not mp4s:
        print(ep, "no mp4 yet, xml stashed")
        continue
    out = os.path.splitext(mp4s[0])[0] + ".ass"
    n = convert(xml, out)
    print(ep, "->", os.path.basename(out), n, "danmaku")
