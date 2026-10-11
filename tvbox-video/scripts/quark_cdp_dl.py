# -*- coding: utf-8 -*-
"""End-to-end inside logged-in uccd page: share token -> detail -> save -> download url."""
import json, urllib.request, websocket, time, sys

PWD_ID = '182564e99d76'
WANT = ['EP189', 'EP193']   # match FR.EP189 / FR.EP193 file names

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
            r = m.get('result', {})
            res = r.get('result', {})
            if 'value' in res:
                return res['value']
            return {'exc': r.get('exceptionDetails', {}).get('text'), 'd': res.get('description', '')[:300]}

BASE = "https://drive-pc.quark.cn/1/clouddrive"
Q = "uc_param_str=dsdnfrpfbivesscpgimibtbmnijblauputogpintnwktprchmt&device_model=MAXSUN&pr=ucpro&fr=win&sys=win32&ve=7.3.5.1009"

def api(path, body=None):
    url = "%s%s?%s" % (BASE, path, Q)
    if body is None:
        ex = "fetch('%s',{credentials:'include'}).then(r=>r.json()).then(j=>JSON.stringify(j))" % url
    else:
        ex = "fetch('%s',{credentials:'include',method:'POST',headers:{'Content-Type':'application/json'},body:%s}).then(r=>r.json()).then(j=>JSON.stringify(j))" % (url, json.dumps(json.dumps(body)))
    raw = ev(ex)
    try:
        return json.loads(raw)
    except Exception:
        return {'_raw': str(raw)[:300]}

# step 1: share token
tok = api('/share/sharepage/token', {'pwd_id': PWD_ID, 'passcode': '', 'support_visit_limit_private_share': True})
print('TOKEN:', json.dumps(tok, ensure_ascii=False)[:200])
stoken = tok.get('data', {}).get('stoken')
if not stoken:
    sys.exit('no stoken')

# step 2: list share root then find target folder/files
def sdir(fid, page=1):
    return api('/share/sharepage/detail&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=%d&_size=200&_fetch_banner=0&_fetch_share=0&_fetch_total=1&_sort=file_type:asc,updated_at:desc'
               % (PWD_ID, urllib.parse.quote(stoken), fid, page)) if False else api(
        '/share/sharepage/detail&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=%d&_size=200&_sort=file_type:asc,updated_at:desc'
        % (PWD_ID, urllib.parse.quote(stoken), fid, page))

import urllib.parse
def sdetail(fid, page=1):
    u = '/share/sharepage/detail?x=1'  # placeholder
    url = "%s/share/sharepage/detail?%s&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=%d&_size=200&_sort=file_type:asc,updated_at:desc" % (
        BASE, Q, PWD_ID, urllib.parse.quote(stoken), fid, page)
    raw = ev("fetch('%s',{credentials:'include'}).then(r=>r.json()).then(j=>JSON.stringify(j))" % url)
    return json.loads(raw)

root = sdetail('0')
items = root.get('data', {}).get('list', [])
print('ROOT items:', len(items))
for it in items:
    print(' ', 'DIR' if it.get('dir') else 'file', it['file_name'][:60], it['fid'])
