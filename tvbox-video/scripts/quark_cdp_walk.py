# -*- coding: utf-8 -*-
"""Walk share folders in-page, find EP189/EP193 files."""
import json, urllib.request, urllib.parse, websocket, sys

PWD_ID = '182564e99d76'
STOKEN = 'JSopUCkrdoGCNuoRgmCuOtLE1+QA+n5MM134m0k1Ch4='
BASE = "https://drive-pc.quark.cn/1/clouddrive"
Q = "uc_param_str=dsdnfrpfbivesscpgimibtbmnijblauputogpintnwktprchmt&device_model=MAXSUN&pr=ucpro&fr=win&sys=win32&ve=7.3.5.1009"

tabs = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=10))
t = [x for x in tabs if 'clouddrive/renderer/index.html' in x.get('url', '')][0]
ws = websocket.create_connection(t['webSocketDebuggerUrl'], timeout=60, suppress_origin=True)
mid = [0]
def ev(expr):
    mid[0] += 1
    ws.send(json.dumps({'id': mid[0], 'method': 'Runtime.evaluate',
                        'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == mid[0]:
            return m.get('result', {}).get('result', {}).get('value')

def fetch_json(url):
    raw = ev("fetch('%s',{credentials:'include'}).then(r=>r.json()).then(j=>JSON.stringify(j))" % url)
    return json.loads(raw)

def sdetail(fid):
    url = "%s/share/sharepage/detail?%s&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=1&_size=500&_sort=file_type:asc,updated_at:desc" % (
        BASE, Q, PWD_ID, urllib.parse.quote(STOKEN), fid)
    return fetch_json(url)

def walk(fid, depth, path, hits):
    if depth > 5:
        return
    r = sdetail(fid)
    items = r.get('data', {}).get('list', [])
    for it in items:
        n = it['file_name']
        p = path + '/' + n
        if it.get('dir'):
            # descend only into folders that look relevant OR first level
            if any(k in n for k in ('凡人', '凡', '修仙')) or depth < 2:
                walk(it['fid'], depth + 1, p, hits)
        else:
            for w in ('EP189', 'EP193', 'E189', 'E193', '第189', '第193'):
                if w in n.replace(' ', ''):
                    hits.append((it['fid'], n, it.get('size', 0), p))
                    break

hits = []
root = sdetail('0')
for it in root.get('data', {}).get('list', []):
    if it.get('dir'):
        walk(it['fid'], 1, it['file_name'], hits)
print(json.dumps(hits, ensure_ascii=False))
ws.close()
