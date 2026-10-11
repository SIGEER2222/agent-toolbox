# -*- coding: utf-8 -*-
"""lock_verify.py — Verify background automation WHILE the workstation is locked.

What it does (single run):
  1. Ensures two native test targets exist: WADemo (typing) and winver (click).
  2. Countdown 15 s (Ctrl+C to abort), then LockWorkStation() -> session locks.
  3. While locked (this process keeps running in the user session):
       - injects WM_CHAR 'LCK' into the WADemo entry (background typing)
       - sends BM_CLICK to winver's native OK button (background click)
       - captures WADemo via PrintWindow (offscreen capture attempt)
  4. Writes results to %TEMP%\\wa_lock_result.txt.
  5. Exits. The session stays locked; results are readable after unlock —
     or from any other process/WSL while still locked.

Run:  python.exe lock_verify.py
"""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from win_capture import user32, list_windows, find_window, shot

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

RESULT = os.path.join(os.environ.get("TEMP", "."), "wa_lock_result.txt")
LINES = []

def log(msg):
    print(msg, flush=True)
    LINES.append(msg)

def first_child(hwnd, cls_name):
    found = []
    P = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(c, _):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(c, buf, 64)
        if buf.value == cls_name:
            found.append(c)
            return False
        return True
    user32.EnumChildWindows(hwnd, P(cb), 0)
    return found[0] if found else 0

def find_hwnd(substr):
    try:
        return find_window(substr)[0]
    except SystemExit:
        return 0

def launch_demo():
    pyw = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_target.pyw")
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        exe = exe[:-len("python.exe")] + "pythonw.exe"
    subprocess.Popen([exe, pyw])
    for _ in range(30):
        time.sleep(0.3)
        h = find_hwnd("WADemo")
        if h:
            return h
    return 0

def launch_winver():
    subprocess.Popen(["cmd.exe", "/c", "start", "winver"])
    for _ in range(30):
        time.sleep(0.3)
        for w in list_windows():
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(w[0], cls, 64)
            if cls.value == "#32770" and "windows" in w[2].lower():
                return w[0]
    return 0

def main():
    log(f"start {time.strftime('%H:%M:%S')}")

    demo = find_hwnd("WADemo") or launch_demo()
    log(f"WADemo hwnd={demo}")

    winver = 0
    for w in list_windows():
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(w[0], cls, 64)
        if cls.value == "#32770" and "windows" in w[2].lower():
            winver = w[0]
            break
    if not winver:
        winver = launch_winver()
    ok_btn = first_child(winver, "Button") if winver else 0
    log(f"winver hwnd={winver} OK-button hwnd={ok_btn}")

    for i in range(15, 0, -1):
        print(f"locking in {i}s (Ctrl+C to abort)", flush=True)
        time.sleep(1)
    log("locking workstation ...")
    user32.LockWorkStation()
    time.sleep(8)

    if demo:
        entry = first_child(demo, "TkChild") or demo
        for ch in "LCK":
            user32.PostMessageW(entry, 0x0102, ord(ch), 0)
            time.sleep(0.02)
        time.sleep(0.4)
        png = os.path.join(os.environ.get("TEMP", "."), "wa_lock.png")
        try:
            shot(demo, png)
            log(f"while-locked: WM_CHAR 'LCK' posted; PrintWindow OK -> {png}")
        except SystemExit as e:
            log(f"while-locked: WM_CHAR 'LCK' posted; PrintWindow FAILED: {e}")

    if ok_btn:
        user32.SendMessageW(ok_btn, 0x00F5, 0, 0)  # BM_CLICK
        time.sleep(0.6)
        log(f"while-locked: BM_CLICK sent; winver IsWindow afterwards = {bool(user32.IsWindow(winver))}")

    log(f"done {time.strftime('%H:%M:%S')} (session still locked)")
    with open(RESULT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")

if __name__ == "__main__":
    main()
