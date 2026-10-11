# bg_verify.py — 后台 UI 自动化能力验证矩阵（窗口未前台、被遮挡 / 最小化）。
# 场景 A：tk 演示窗被 cover.pyw 完全遮住：PrintWindow 截图 + WM_CHAR 注入输入框 + tk 按钮消息
# 场景 B：tk 演示窗最小化：截图（预期失败）+ 注入（还原后验证）
# 场景 C：原生控件被遮住：winver 的 PostMessageW(BM_CLICK) 与 UIA Invoke、运行框 UIA 写值 + Invoke
# 每项验证真实副作用：截图差分（文本落入）/ 对话框销毁 / Calculator 启动。
# 用法：python bg_verify.py  （自动拉起并清理测试窗口；输出结果矩阵）
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pywinauto import Desktop  # noqa: E402
from win_capture import (  # noqa: E402
    RECT, close, list_windows, shot, type_text, user32,
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


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def top_at_centre(h):
    x, y, w, hh = win_rect(h)
    return user32.GetAncestor(user32.WindowFromPoint(POINT(x + w // 2, y + hh // 2)), 2)


def window_title(h):
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    return buf.value


def cover_target(target):
    """用 cover.pyw 盖住 target，并把遮挡窗（仅它自己）提到 Z 序顶层。
    返回 (遮挡窗 hwnd, target 中心点实际的顶层窗口)；调用方用 covered_by() 判定真实遮挡者。"""
    x, y, w, h = win_rect(target)
    spawn("cover.pyw", {"COVER_X": str(x), "COVER_Y": str(y),
                        "COVER_W": str(w), "COVER_H": str(h)})
    cov = dialog_hwnd(lambda hw, t: t == "WACover", tries=25)
    time.sleep(0.5)
    user32.SetWindowPos(cov, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_TOP, NOMOVE|NOSIZE|NOACTIVATE
    time.sleep(0.6)
    return cov, top_at_centre(target)


def covered_by(cov, top, target):
    if top == target:
        return "NOT COVERED"
    return "cover.pyw" if top == cov else window_title(top)


def dialog_hwnd(pred, tries=30):
    """等待第一个满足 pred(hwnd, title) 的窗口出现，返回 hwnd（找不到返回 0）。"""
    for _ in range(tries):
        time.sleep(0.3)
        for h, _, t in list_windows():
            if pred(h, t):
                return h
    return 0


def is_winver(h, t):
    cls = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(h, cls, 64)
    return cls.value == "#32770" and t.startswith("关于")


def close_covers():
    for h, _, t in list_windows():
        if t == "WACover":
            close(h)
    time.sleep(0.8)


def covered_winver(mode):
    """winver 被 cover 完全遮住后，用 mode 关窗：post=PostMessageW(BM_CLICK)，uia=UIA Invoke。"""
    subprocess.Popen(["cmd.exe", "/c", "start", "winver"])
    hwnd = dialog_hwnd(is_winver)
    if not hwnd:
        return "winver not found"
    time.sleep(0.8)
    cov, top = cover_target(hwnd)
    covered = covered_by(cov, top, hwnd)
    if mode == "post":
        user32.PostMessageW(button_child(hwnd), BM_CLICK, 0, 0)
    else:
        Desktop(backend="uia").window(handle=hwnd).child_window(title="确定", control_type="Button").invoke()
    time.sleep(1.0)
    closed = not user32.IsWindow(hwnd)
    if not closed:
        close(hwnd)
    close_covers()
    return {"closed": closed, "covered_by": covered}


def covered_runbox():
    """运行框被 cover 遮住：UIA ValuePattern 写 calc + Invoke 确定 -> Calculator 启动。
    只关闭本次新启动的计算器，不碰用户已打开的窗口。"""
    calc_before = {h for h, _, t in list_windows() if t in ("Calculator", "计算器")}
    subprocess.Popen(["cmd.exe", "/c", "explorer", "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}"])
    hwnd = dialog_hwnd(lambda h, t: t == "运行")
    if not hwnd:
        return "run dialog not found"
    time.sleep(0.8)
    cov, top = cover_target(hwnd)
    covered = covered_by(cov, top, hwnd)
    dlg = Desktop(backend="uia").window(handle=hwnd)
    dlg.child_window(control_type="Edit").iface_value.SetValue("calc")
    dlg.child_window(title="确定", control_type="Button").invoke()
    time.sleep(2.5)
    calc_new = [h for h, _, t in list_windows()
                if t in ("Calculator", "计算器") and h not in calc_before]
    for h in calc_new:
        close(h)
    close_covers()
    return {"calc_launched": bool(calc_new), "covered_by": covered}


def native_case():
    """原生控件（winver / 运行框）在遮挡下的后台操作。"""
    return {"winver_post": covered_winver("post"),
            "winver_uia": covered_winver("uia"),
            "runbox_uia": covered_runbox()}


def main():
    if os.path.exists(MARKER):
        os.remove(MARKER)
    proc = spawn("demo_target.pyw")
    demo = hwnd_by_pid(proc.pid, "WADemo")
    if not demo:
        raise SystemExit("WADemo window not found")

    # ---- 场景 A：完全遮挡 ----
    cov, top = cover_target(demo)
    results["occluded_by"] = covered_by(cov, top, demo)
    run_case("occluded", lambda: case_body(demo, "occ"))

    # ---- 场景 B：最小化 ----
    close_covers()
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

    # ---- 场景 C：原生控件在遮挡下 ----
    run_case("native", native_case)

    for k, v in results.items():
        print(f"[{k}] {v}")


if __name__ == "__main__":
    main()
