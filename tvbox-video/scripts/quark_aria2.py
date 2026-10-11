# -*- coding: utf-8 -*-
"""Feed quark direct urls to aria2c with cookie header, multi-connection download."""
import json, os, subprocess, tempfile, sys

ARIA2 = r'C:\Users\22448\AppData\Local\Microsoft\WinGet\Packages\aria2.aria2_Microsoft.Winget.Source_8wekyb3d8bbwe\aria2-1.37.0-win-64bit-build1\aria2c.exe'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/2.5.20 Chrome/100.0.4896.160 Electron/18.3.5.4-b478491100 Safari/537.36 Channel/pckk_other_ch'
CK = open(os.path.join(tempfile.gettempdir(), 'quark_full_cookie.txt'), encoding='ascii').read().strip()
DL = os.path.join(os.environ['USERPROFILE'], 'Downloads')

items = json.load(open(os.path.join(os.path.dirname(__file__), 'quark_urls.json'), encoding='utf-8'))
which = sys.argv[1] if len(sys.argv) > 1 else ''
for it in items:
    if which and which not in it['name']:
        continue
    out = it['name']
    fp = os.path.join(DL, out)
    if os.path.exists(fp) and not os.path.exists(fp + '.aria2'):
        os.remove(fp)   # stale preallocated file, no aria2 control -> restart clean
    cmd = [ARIA2,
           '-x16', '-s16', '-k1M',
           '--file-allocation=none', '--continue=true',
           '--max-tries=0', '--retry-wait=3', '--timeout=60',
           '--console-log-level=warn', '--summary-interval=10',
           '--header=Cookie: ' + CK,
           '--header=User-Agent: ' + UA,
           '--header=Referer: https://pan.quark.cn/',
           '-d', DL, '-o', out, it['url']]
    print('>>>', out, flush=True)
    subprocess.run(cmd)
    print('<<<', out, os.path.getsize(fp) if os.path.exists(fp) else 'MISSING', flush=True)
