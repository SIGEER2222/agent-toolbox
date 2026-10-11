# -*- coding: utf-8 -*-
"""Quark pan: save shared files to own drive -> get download urls -> fetch fast.
Reads decrypted cookie file written by quark_getcookie.py."""
import json, os, sys, urllib.request, urllib.parse, re

_raw = open(r'E:\tmp\quark_cookie.txt', encoding='utf-8').read().strip()
CK = '; '.join(p for p in _raw.split('; ') if p.split('=', 1)[-1].isascii())
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/2.5.20 Chrome/100.0.4896.160 Electron/18.3.5.4-b478491100 Safari/537.36 Channel/pckk_other_ch'
PWD_ID = '182564e99d76'
WANT = ['189', '193']

def req(url, data=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method or ('POST' if body else 'GET'))
    r.add_header('Cookie', CK)
    r.add_header('User-Agent', UA)
    r.add_header('Content-Type', 'application/json;charset=UTF-8')
    r.add_header('Referer', 'https://pan.quark.cn/')
    return json.load(urllib.request.urlopen(r, timeout=30))

# 1) login check
acc = req('https://pan.quark.cn/account/info?fr=pc&platform=pc')
print('account:', json.dumps(acc.get('data', {}), ensure_ascii=False)[:200])

# 2) share token
tok = req('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token?pr=ucpro&fr=pc',
          {'pwd_id': PWD_ID, 'passcode': ''})
stoken = tok['data']['stoken']
print('stoken ok')

# 3) list share root
def sdir(fid):
    return req('https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail?pr=ucpro&fr=pc&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=1&_size=200&_fetch_banner=0&_fetch_share=0&_fetch_total=1&_sort=file_type:asc,updated_at:desc'
               % (PWD_ID, urllib.parse.quote(stoken), fid))

root = sdir('0')
items = root['data']['list']
print('root items:', len(items))
top = items[0]
sub = sdir(top['fid'])['data']['list']
print('folder has', len(sub))
found = []
for it in sub:
    n = it['file_name']
    tag = 'DIR' if it.get('dir') else 'file'
    if any(w in n for w in WANT):
        found.append(it)
        print('HIT', tag, n, it.get('size', 0), it['fid'])
    else:
        print(' ', tag, n[:70])
open(r'E:\tmp\quark_hits.json', 'w').write(json.dumps(found))
