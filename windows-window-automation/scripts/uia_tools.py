# uia_tools.py — UI Automation (pywinauto backend='uia') 后台窗口操作。
# 不抢焦点、不模拟物理输入：走无障碍树的 ValuePattern / InvokePattern / 文本读取。
# 实测适用：原生 Win32 控件（winver 按钮 Invoke 可关窗）、Explorer 对话框（运行框读值）。
# 实测不适用：tk 自绘控件（Invoke 是 no-op）、UIA 无法枚举的定制渲染控件。
#
# 用法（Windows Python）：
#   python uia_tools.py inspect <标题子串>            # 打印 UIA 树（找 AutomationId/Name/类型）
#   python uia_tools.py read    <标题子串> <名称片段> [控件类型]  # 读控件 ValuePattern 值
#   python uia_tools.py set     <标题子串> <名称片段> <文本> [控件类型]  # 写值（等价 WM_SETTEXT）
#   python uia_tools.py click   <标题子串> <按钮名>   # InvokePattern 点按钮（等价 BM_CLICK）
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from pywinauto import Desktop  # noqa: E402


def find_win(title_sub):
    wins = [w for w in Desktop(backend="uia").windows()
            if title_sub.lower() in (w.window_text() or "").lower()]
    if not wins:
        raise SystemExit(f"no UIA window matching {title_sub!r}")
    if len(wins) > 1:
        print(f"warn: {len(wins)} matches, using first", file=sys.stderr)
    return wins[0]


def find_ctrl(win, name_sub, control_type=None):
    hits = []
    for el in win.descendants():
        info = el.element_info
        if control_type and info.control_type != control_type:
            continue
        text = info.name or ""
        auto_id = info.automation_id or ""
        if name_sub.lower() in text.lower() or name_sub.lower() in auto_id.lower():
            hits.append(el)
    if not hits:
        raise SystemExit(f"no control matching {name_sub!r} under {win.window_text()!r}")
    if len(hits) > 1:
        names = [(h.element_info.control_type, h.element_info.name)
                 for h in hits]
        raise SystemExit(f"ambiguous {name_sub!r}: {names}")
    return hits[0]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "inspect"
    win = find_win(sys.argv[2]) if len(sys.argv) > 2 else None
    if cmd == "inspect":
        win.print_control_identifiers()
    elif cmd == "read":
        el = find_ctrl(win, sys.argv[3],
                       sys.argv[4] if len(sys.argv) > 4 else None)
        try:
            print(repr(el.get_value()))
        except Exception:
            print(repr(el.window_text()))
    elif cmd == "set":
        el = find_ctrl(win, sys.argv[3],
                       sys.argv[5] if len(sys.argv) > 5 else None)
        el.iface_value.SetValue(sys.argv[4])
        print("set ok")
    elif cmd == "click":
        el = find_ctrl(win, sys.argv[3], control_type="Button")
        el.invoke()
        print("invoked")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
