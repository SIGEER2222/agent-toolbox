# -*- coding: utf-8 -*-
"""lock_verify.py — 锁屏态后台操作实测（两阶段；第二阶段需要用户解锁一次）。

phase 1  python lock_verify.py lock
         拉起 WADemo(tk) 与新开的 winver(原生对话框) -> 记录基线 -> LockWorkStation()
         -> 轮询直到 LogonUI.exe 出现（证明真的进入锁屏，而不是只调用了 API）
         -> 锁屏中：WM_CHAR 注入 'LCK' 到 tk Entry、PostMessageW BM_CLICK 点 winver 确定、PrintWindow 截图
         -> 状态写入 %TEMP%\\wa_lock_state.json，之后等待用户解锁。
phase 2  python lock_verify.py check
         解锁后运行：核对锁屏期间投递的操作是否在解锁后补执行（winver 是否已销毁、Entry 是否多出 'LCK'），
         然后关闭本次拉起的两个测试窗口。

只操作本脚本自己拉起的测试窗口，不碰用户已有窗口。
"""
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from win_capture import close, list_windows, shot, type_text, user32  # noqa: E402
from bg_verify import entry_dark_px  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TEMP = os.environ.get("TEMP", ".")
STATE = os.path.join(TEMP, "wa_lock_state.json")
BM_CLICK = 0x00F5
PYW = sys.executable.replace("python.exe", "pythonw.exe")


def desktop_name():
    d = user32.OpenInputDesktop(0, False, 0x0001)
    if not d:
        return f"<open failed err={ctypes.GetLastError()}>"
    buf = ctypes.create_unicode_buffer(64)
    user32.GetUserObjectInformationW(d, 2, buf, ctypes.sizeof(buf), None)
    user32.CloseDesktop(d)
    return buf.value


def logonui_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq LogonUI.exe", "/NH"],
                         capture_output=True, text=True, errors="replace").stdout
    return "LogonUI.exe" in out


def dialogs32770():
    out = set()
    for h, _, _t in list_windows():
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, cls, 64)
        if cls.value == "#32770":
            out.add(h)
    return out


def child_of(hwnd, cls_name):
    P = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found = []

    def cb(c, _):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(c, buf, 64)
        if buf.value == cls_name:
            found.append(c)
            return False
        return True

    user32.EnumChildWindows(hwnd, P(cb), 0)
    return found[0] if found else 0


def phase_lock():
    dlg_before = dialogs32770()
    subprocess.Popen(["cmd.exe", "/c", "start", "winver"])
    demo_proc = subprocess.Popen([PYW, os.path.join(HERE, "demo_target.pyw")])
    demo = winver = 0
    for _ in range(40):
        time.sleep(0.3)
        demo = next((h for h, p, t in list_windows() if p == demo_proc.pid and t == "WADemo"), 0)
        new = dialogs32770() - dlg_before
        winver = next(iter(new), 0)
        if demo and winver:
            break
    if not (demo and winver):
        raise SystemExit(f"launch failed demo={demo} winver={winver}")
    time.sleep(1.0)
    ok_btn = child_of(winver, "Button")
    base_png = os.path.join(TEMP, "wa_lock_base.png")
    shot(demo, base_png)
    base = entry_dark_px(base_png)
    print(f"demo={demo} winver={winver} ok_btn={ok_btn} base_dark={base}", flush=True)
    print(f"pre-lock desktop={desktop_name()!r} logonui={logonui_running()}", flush=True)

    ret = user32.LockWorkStation()
    print(f"LockWorkStation() returned {ret}", flush=True)
    locked = False
    for i in range(15):
        time.sleep(1)
        ui = logonui_running()
        print(f"  poll {i+1}s desktop={desktop_name()!r} logonui={ui}", flush=True)
        if ui:
            locked = True
            break
    time.sleep(2)

    type_text(demo, "LCK")
    user32.PostMessageW(ok_btn, BM_CLICK, 0, 0)
    time.sleep(2)
    during_png = os.path.join(TEMP, "wa_lock_during.png")
    try:
        shot(demo, during_png)
        during_delta = entry_dark_px(during_png) - base
    except SystemExit as e:
        during_png, during_delta = None, f"shot failed: {e}"
    during = {
        "locked_seen": locked,
        "desktop": desktop_name(),
        "logonui": logonui_running(),
        "entry_delta": during_delta,
        "winver_alive": bool(user32.IsWindow(winver)),
    }
    print("during-lock:", during, flush=True)
    json.dump({"demo": demo, "winver": winver, "ok_btn": ok_btn, "base": base,
               "during": during}, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"state -> {STATE}\n请解锁屏幕，然后运行: python lock_verify.py check", flush=True)


def phase_check():
    st = json.load(open(STATE, encoding="utf-8"))
    after_png = os.path.join(TEMP, "wa_lock_after.png")
    after = {
        "desktop": desktop_name(),
        "logonui": logonui_running(),
        "winver_alive": bool(user32.IsWindow(st["winver"])),
        "demo_alive": bool(user32.IsWindow(st["demo"])),
    }
    if after["demo_alive"]:
        shot(st["demo"], after_png)
        after["entry_delta_vs_base"] = entry_dark_px(after_png) - st["base"]
    print("during-lock:", st["during"])
    print("after-unlock:", after)
    for h in (st["demo"], st["winver"]):
        if user32.IsWindow(h):
            close(h)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "lock":
        phase_lock()
    elif mode == "check":
        phase_check()
    else:
        raise SystemExit(__doc__)
