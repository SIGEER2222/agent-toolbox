import hashlib, os, base64, io, re
pw = 'admintv'
salt = os.urandom(16)
dk = hashlib.pbkdf2_hmac('sha512', pw.encode(), salt, 100000, 64)
entry = '@ByteArray(%s:%s)' % (base64.b64encode(salt).decode(), base64.b64encode(dk).decode())
ini = '/mnt/c/Users/22448/AppData/Roaming/qBittorrent/qBittorrent.ini'
s = io.open(ini, encoding='utf-8').read()
# replace/insert credentials inside [Preferences]
s = re.sub(r'WebUI\\Password_PBKDF2=.*\n', '', s)
s = re.sub(r'WebUI\\Username=.*\n', '', s)
s = s.replace('WebUI\\Enabled=true',
              'WebUI\\Enabled=true\nWebUI\\Username=admin\nWebUI\\Password_PBKDF2="%s"' % entry)
io.open(ini, 'w', encoding='utf-8', newline='').write(s)
print('written; login admin / %s' % pw)
