#!/usr/bin/env python
# win_capture.py — Windows 顶层窗口枚举 / PrintWindow 截图 / PostMessageW 注入文本 / WM_CLOSE 关闭。
# 纯 ctypes + Pillow，无第三方自动化框架。Windows Python 运行（WSL 里调 python.exe）。
#
# 用法：
#   python win_capture.py list                       # 列出可见顶层窗口 hwnd/pid/title
#   python win_capture.py shot  <标题子串> <out.png> # PrintWindow 截图（被遮挡/最小化外也能截）
#   python win_capture.py type  <标题子串> <文本>    # 向窗口首个子控件逐字符 PostMessageW(WM_CHAR)
#   python win_capture.py close <标题子串>           # PostMessageW(WM_CLOSE) 优雅关闭
import ctypes
import sys
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
user32.SetProcessDPIAware()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
WM_CHAR = 0x0102
WM_CLOSE = 0x0010
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _win_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def list_windows():
    """[(hwnd, pid, title)] 可见且有标题的顶层窗口。"""
    out = []

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _win_text(hwnd)
        if not title:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((hwnd, pid.value, title))
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return out


def find_window(substr):
    hits = [w for w in list_windows() if substr.lower() in w[2].lower()]
    if not hits:
        raise SystemExit(f"no window matching {substr!r}")
    if len(hits) > 1:
        print(f"warn: {len(hits)} matches, using first", file=sys.stderr)
    return hits[0]


def shot(hwnd, out_path):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        raise SystemExit("window has no size (minimized?)")
    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    gdi32.SelectObject(mem_dc, bmp)
    ok = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    buf = (ctypes.c_char * (w * h * 4))()
    rows = gdi32.GetDIBits(hwnd_dc, bmp, 0, h, buf, ctypes.byref(bmi), DIB_RGB_COLORS)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    if not ok or rows == 0:
        raise SystemExit(f"PrintWindow={ok} GetDIBits rows={rows}")
    from PIL import Image
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(out_path)
    return out_path


def _first_child(hwnd):
    """顶层窗口的第一个可见子控件（没有则返回顶层窗口自身）。"""
    found = []

    def cb(child, _):
        if user32.IsWindowVisible(child):
            found.append(child)
            return False
        return True

    user32.EnumChildWindows(hwnd, EnumWindowsProc(cb), 0)
    return found[0] if found else hwnd


def type_text(hwnd, text):
    target = _first_child(hwnd)
    for ch in text:
        user32.PostMessageW(target, WM_CHAR, ord(ch), 0)
    return target


def close(hwnd):
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for hwnd, pid, title in list_windows():
            print(f"{hwnd:>10}  pid={pid:<6} {title[:70]}")
    elif cmd == "shot":
        hwnd, pid, title = find_window(sys.argv[2])
        print(f"hwnd={hwnd} title={title!r} -> {shot(hwnd, sys.argv[3])}")
    elif cmd == "type":
        hwnd, pid, title = find_window(sys.argv[2])
        print(f"hwnd={hwnd} title={title!r} typed -> child {_first_child(hwnd)}")
        type_text(hwnd, sys.argv[3])
    elif cmd == "close":
        hwnd, pid, title = find_window(sys.argv[2])
        close(hwnd)
        print(f"WM_CLOSE -> hwnd={hwnd} title={title!r}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
