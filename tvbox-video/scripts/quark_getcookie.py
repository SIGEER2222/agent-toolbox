# -*- coding: utf-8 -*-
# Extract quark.cn cookies from local Quark browser profile (own machine, own session).
import base64, json, os, shutil, sqlite3, sys, tempfile
import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

LOCAL = os.environ['LOCALAPPDATA']
ud = os.path.join(LOCAL, 'Quark', 'User Data')
ls = json.load(open(os.path.join(ud, 'Local State'), encoding='utf-8'))
key = base64.b64decode(ls['os_crypt']['encrypted_key'])[5:]  # strip 'DPAPI'
key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

src = None
for cand in ('Default', 'Profile 1'):
    p = os.path.join(ud, cand, 'Network', 'Cookies')
    if os.path.exists(p):
        src = p
        break
if not src:
    sys.exit('no cookies db')

# browser holds an exclusive lock; immutable=1 opens read-only without locking
con = sqlite3.connect('file:%s?immutable=1' % src.replace('\\', '/'), uri=True)
rows = con.execute(
    "SELECT host_key,name,encrypted_value FROM cookies WHERE host_key LIKE '%quark%'").fetchall()

out = {}
for host, name, enc in rows:
    if enc[:3] in (b'v10', b'v11', b'v20'):
        nonce, ct = enc[3:15], enc[15:]
        try:
            val = AESGCM(key).decrypt(nonce, ct, None)
        except Exception:
            continue
        out[name] = val.decode('utf-8', 'replace')
    else:
        try:
            out[name] = win32crypt.CryptUnprotectData(enc, None, None, None, 0)[1].decode('utf-8', 'replace')
        except Exception:
            pass

# strip 32-byte prefix used by newer chromium app-bound encryption
for k, v in list(out.items()):
    if len(v) > 0 and ord(v[0]) < 32:
        out[k] = v[32:]

cookie = '; '.join('%s=%s' % (k, v) for k, v in out.items() if v)
open('/tmp/quark_cookie.txt', 'w', encoding='utf-8').write(cookie)
print('cookies:', len(out), '| names:', ','.join(sorted(out)[:30]))
