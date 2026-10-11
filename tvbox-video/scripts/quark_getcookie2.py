# -*- coding: utf-8 -*-
# Extract REAL cookies: Chromium v10+ plaintext = SHA256(host)(32B) + value
# Covers both Quark browser and uc-cloud-drive client profiles.
import base64, json, os, sqlite3, tempfile, shutil

import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def extract(profile_root, out_name):
    ls = json.load(open(os.path.join(profile_root, 'Local State'), encoding='utf-8'))
    key = win32crypt.CryptUnprotectData(base64.b64decode(ls['os_crypt']['encrypted_key'])[5:], None, None, None, 0)[1]
    ck = os.path.join(profile_root, 'Network', 'Cookies')
    if not os.path.exists(ck):
        ck = os.path.join(profile_root, 'Default', 'Network', 'Cookies')
    tmp = os.path.join(tempfile.gettempdir(), 'qck_%s.db' % out_name)
    shutil.copy(ck, tmp)
    con = sqlite3.connect(tmp)
    rows = con.execute("SELECT host_key,name,encrypted_value,value FROM cookies").fetchall()
    jar = {}
    for host, name, enc, plain in rows:
        val = ''
        if enc and enc[:3] in (b'v10', b'v11', b'v20'):
            try:
                p = AESGCM(key).decrypt(enc[3:15], enc[15:], None)
                val = p[32:].decode('utf-8', 'strict') if len(p) > 32 else ''
            except Exception:
                val = ''
        elif enc:
            try:
                p = win32crypt.CryptUnprotectData(enc, None, None, None, 0)[0]
                val = p[32:].decode('utf-8', 'strict') if len(p) > 32 else p.decode('utf-8', 'strict')
            except Exception:
                val = ''
        elif plain:
            val = plain
        if val and val.isascii() and ('quark' in (host or '') or 'uc.cn' in (host or '')):
            jar[name] = val
    print(out_name, 'clean cookies:', len(jar), sorted(jar))
    return jar

ud1 = os.path.join(os.environ['LOCALAPPDATA'], 'Quark', 'User Data')
ud2 = os.path.join(os.environ['APPDATA'], 'uc-cloud-drive')
jar = {}
jar.update(extract(ud1, 'browser'))   # quark.cn domain cookies
jar.update(extract(ud2, 'client'))    # uc.cn domain auth cookies (__pus/__puus/__uid)

hdr = '; '.join('%s=%s' % (k, v) for k, v in jar.items())
with open(os.path.join(tempfile.gettempdir(), 'quark_full_cookie.txt'), 'w', encoding='ascii') as f:
    f.write(hdr)
print('FULL header saved, len=%d' % len(hdr))
print('has __pus:', '__pus' in jar, '| __puus:', '__puus' in jar, '| __uid:', '__uid' in jar)
