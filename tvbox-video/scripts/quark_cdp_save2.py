# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, websocket, sys, time

PWD_ID = '182564e99d76'
STOKEN = 'JSopUCkrdoGCNuoRgmCuOtLE1+QA+n5MM134m0k1Ch4='
BASE = "https://drive-pc.quark.cn/1/clouddrive"
Q = "uc_param_str=dsdnfrpfbivesscpgimibtbmnijblauputogpintnwktprchmt&device_model=MAXSUN&pr=ucpro&fr=win&sys=win32&ve=7.3.5.1009"
TARGET_FIDS = {'a7d9543a983646f3bea31ca4eb7d9395', '5aa9241a57494224a6a05514d47f27a4'}

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
def post(path, body):
    url = "%s%s?%s" % (BASE, path, Q)
    ex = "fetch('%s',{credentials:'include',method:'POST',headers:{'Content-Type':'application/json'},body:%s}).then(r=>r.json()).then(j=>JSON.stringify(j))" % (url, json.dumps(json.dumps(body)))
    raw = ev(ex)
    return json.loads(raw) if raw else {}
def getj(url):
    raw = ev("fetch('%s',{credentials:'include'}).then(r=>r.json()).then(j=>JSON.stringify(j))" % url)
    return json.loads(raw) if raw else {}
def sdetail(fid):
    return getj("%s/share/sharepage/detail?%s&pwd_id=%s&stoken=%s&pdir_fid=%s&force=0&_page=1&_size=500&_sort=file_type:asc,updated_at:desc" % (BASE, Q, PWD_ID, urllib.parse.quote(STOKEN), fid))

# gather share_fid_token for target files
tokens = {}
def walk(fid, depth):
    if depth > 5 or len(tokens) == len(TARGET_FIDS):
        return
    items = (sdetail(fid).get('data') or {}).get('list', [])
    for it in items:
        if it.get('dir'):
            if any(k in it['file_name'] for k in ('凡人', '凡', '修仙')) or depth < 2:
                walk(it['fid'], depth + 1)
        elif it['fid'] in TARGET_FIDS:
            tokens[it['fid']] = it.get('share_fid_token')
            print('got token for', it['file_name'][:40], '->', str(it.get('share_fid_token'))[:40])
root = sdetail('0')
for it in root.get('data', {}).get('list', []):
    if it.get('dir'):
        walk(it['fid'], 1)
print('tokens:', len(tokens))

r = post('/share/sharepage/save', {
    'pwd_id': PWD_ID, 'stoken': STOKEN,
    'fid_list': list(tokens.keys()),
    'fid_token_list': list(tokens.values()),
    'to_pdir_fid': '0', 'pdir_fid': '0', 'scene': 'link'
})
print('SAVE:', json.dumps(r, ensure_ascii=False)[:400])
task_id = (r.get('data') or {}).get('task_id')
if not task_id:
    sys.exit('save failed')
saved = []
for i in range(40):
    t = getj("%s/task?task_id=%s&retry_index=%d&%s" % (BASE, task_id, i, Q))
    st = (t.get('data') or {}).get('status')
    if st == 2:
        saved = (t.get('data') or {}).get('save_as', {}).get('save_as_top_fids') or []
        break
    if st in (3, 4):
        sys.exit('task failed ' + json.dumps(t)[:300])
    time.sleep(1)
print('SAVED fids:', saved)
urls = []
for fid in saved:
    d = post('/file/download', {'fids': [fid]})
    dl = (d.get('data') or [])
    for it in dl:
        urls.append({'fid': fid, 'name': it.get('file_name'), 'url': it.get('download_url')})
    if not dl:
        print('download resp:', json.dumps(d, ensure_ascii=False)[:300])
print(json.dumps(urls, ensure_ascii=False))
ws.close()
