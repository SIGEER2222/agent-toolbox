# bg_verify.py — 后台 UI 自动化能力验证矩阵（窗口解锁、非前台状态）。
# 场景 A：目标窗口被 cover.pyw 完全遮住（不置底不最小化）
# 场景 B：目标窗口被最小化
# 场景 C：原生 Win32 控件（winver 确定按钮）BM_CLICK 基线
# 每项验证真实副作用：截图非空 / 文本真正落进 Entry（截图像素验证）/ 窗口被销毁。
# 用法：python bg_verify.py  （自动拉起并清理演示窗口；输出结果矩阵）
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from win_capture import (  # noqa: E402
    RECT, close, find_window, list_windows, shot, type_text, user32,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PY_EXE = sys.executable
PYW_EXE = PY_EXE.replace("python.exe", "pythonw.exe")
MARKER = os.path.join(os.environ["TEMP"], "wademo_clicks.log")
SW_MINIMIZE = 6
SW_SHOWNOACTIVATE = 4
BM_CLICK = 0x00F5
results = {}


def spawn(name, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.Popen([PYW_EXE, os.path.join(HERE, name)], env=env)


def hwnd_by_pid(pid, title_sub, tries=30):
    for _ in range(tries):
        for h, p, t in list_windows():
            if p == pid and title_sub.lower() in t.lower():
                return h
        time.sleep(0.3)
    return 0


def win_rect(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def button_child(hwnd):
    """找 class=Button 的子控件 hwnd。"""
    P = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found = []

    def cb(c, _):
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(c, cls, 64)
        if cls.value == "Button":
            found.append(c)
            return False
        return True

    user32.EnumChildWindows(hwnd, P(cb), 0)
    return found[0] if found else None


def marker_lines():
    try:
        return open(MARKER, encoding="utf-8").read().strip().splitlines()
    except OSError:
        return []


def entry_dark_px(png):
    """WADemo 截图里 Entry 区域的深色像素数（文本落在输入框的像素级证据）。"""
    from PIL import Image
    img = Image.open(png).convert("L")
    w, h = img.size
    # Entry 约占窗口 y 27%~44%、x 2%~98%（demo_target 布局固定，含 ~32px 标题栏）
    box = img.crop((int(w * 0.02), int(h * 0.27), int(w * 0.98), int(h * 0.44)))
    return sum(1 for p in box.tobytes() if p < 100)


def run_case(tag, work):
    try:
        results[tag] = work()
    except Exception as e:  # noqa: BLE001
        results[tag] = {"error": f"{type(e).__name__}: {e}"}


baseline = {"dark": None}  # 首个有效截图的 Entry 区深色像素基线（空文本）


def case_body(hwnd, tag):
    out = {}
    p = os.path.join(os.environ["TEMP"], f"wa_{tag}.png")
    # 1) PrintWindow 截图（最小化时窗口 rect 塌缩，只能截到残片）
    try:
        shot(hwnd, p)
        from PIL import Image
        out["shot"] = Image.open(p).size[1] > 100  # >100px 才算截到内容
        if out["shot"] and baseline["dark"] is None:
            baseline["dark"] = entry_dark_px(p)
    except Exception as e:  # noqa: BLE001
        out["shot"] = f"FAIL {e}"
    # 2) WM_CHAR 注入
    try:
        type_text(hwnd, tag)
        time.sleep(0.6)
        out["type_posted"] = True
    except Exception as e:  # noqa: BLE001
        out["type_posted"] = f"FAIL {e}"
    # 3) 立即再截一张，与基线比深色像素增量验证文本落进 Entry（截不到内容时跳过）
    if out.get("shot") is True and baseline["dark"] is not None:
        try:
            shot(hwnd, p)
            delta = entry_dark_px(p) - baseline["dark"]
            out["type_landed"] = f"{delta > 50} (delta={delta})"
        except Exception as e:  # noqa: BLE001
            out["type_landed"] = f"FAIL {e}"
    # 4) BM_CLICK -> tk 按钮（已知限制：tk 控件不走原生 WM_COMMAND 路由）
    before = len(marker_lines())
    btn = button_child(hwnd)
    if btn:
        user32.PostMessageW(btn, BM_CLICK, 0, 0)
        time.sleep(0.6)
    out["tk_click"] = len(marker_lines()) > before
    return out


def winver_hwnd():
    for h, _, t in list_windows():
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, cls, 64)
        if cls.value == "#32770" and "windows" in t.lower():
            return h
    return 0


def native_click_case():
    """winver（原生 Win32 对话框）BM_CLICK -> 窗口销毁即生效。"""
    subprocess.Popen(["cmd.exe", "/c", "start", "winver"])
    hwnd = 0
    for _ in range(30):
        time.sleep(0.3)
        hwnd = winver_hwnd()
        if hwnd:
            break
    if not hwnd:
        return {"winver": "not found"}
    btn = button_child(hwnd)
    user32.SendMessageW(btn, BM_CLICK, 0, 0)
    time.sleep(0.6)
    return {"bm_click_closed": not user32.IsWindow(hwnd)}


def main():
    if os.path.exists(MARKER):
        os.remove(MARKER)
    proc = spawn("demo_target.pyw")
    demo = hwnd_by_pid(proc.pid, "WADemo")
    if not demo:
        raise SystemExit("WADemo window not found")
    x, y, w, h = win_rect(demo)

    # ---- 场景 A：完全遮挡 ----
    spawn("cover.pyw", {"COVER_X": str(x), "COVER_Y": str(y),
                        "COVER_W": str(w), "COVER_H": str(h)})
    time.sleep(1.2)
    run_case("occluded", lambda: case_body(demo, "occ"))

    # ---- 场景 B：最小化 ----
    close(find_window("WACover")[0])
    user32.ShowWindow(demo, SW_MINIMIZE)
    time.sleep(1.0)
    run_case("minimized", lambda: case_body(demo, "min"))
    user32.ShowWindow(demo, SW_SHOWNOACTIVATE)  # 还原但不抢焦点
    time.sleep(0.8)

    # 最小化期间投的文本，还原后与基线对比看是否落进 Entry
    try:
        p = os.path.join(os.environ["TEMP"], "wa_restored.png")
        shot(demo, p)
        delta = entry_dark_px(p) - (baseline["dark"] or 0)
        results["restored_typing_landed"] = f"{delta > 50} (delta={delta})"
    except Exception as e:  # noqa: BLE001
        results["restored_shot"] = f"FAIL {e}"
    close(demo)

    # ---- 场景 C：原生控件 BM_CLICK ----
    run_case("native_winver", native_click_case)

    for k, v in results.items():
        print(f"[{k}] {v}")


if __name__ == "__main__":
    main()
