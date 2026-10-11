import glob, os, time
files = {}
for f in glob.glob('/mnt/c/Users/22448/Downloads/*Doomdos*.mp4'):
    ep = ''.join(c for c in os.path.basename(f) if c.isdigit())[:3]
    files[ep] = f
def sizes():
    return {ep: os.path.getsize(f) for ep, f in files.items()}
s1 = sizes(); t1 = time.time()
time.sleep(60)
s2 = sizes(); t2 = time.time()
total = 0
for ep in sorted(s1):
    d = s2[ep] - s1[ep]
    rate = d / (t2 - t1) / 1024
    total += d
    if d > 0:
        print(f'ep{ep}: +{d/1e6:.1f} MB in {t2-t1:.0f}s  = {rate:.0f} KB/s')
    else:
        print(f'ep{ep}: stalled')
print(f'TOTAL: {total/(t2-t1)/1024:.0f} KB/s')
