# demo_target.pyw — 演示用 Win32 目标窗口（tkinter）：标题 "WADemo"。
# 一个文本框（接收 WM_CHAR 注入）+ 一个 "stamp" 按钮（点击写 %TEMP%\wademo_clicks.log 副作用）。
# 由验证流程拉起；也可手动：pythonw demo_target.pyw
import os
import time
import tkinter as tk

MARKER = os.path.join(os.environ.get("TEMP", "."), "wademo_clicks.log")

root = tk.Tk()
root.title("WADemo")
root.geometry("360x150")

entry = tk.Entry(root, font=("Consolas", 18), width=20, insertofftime=0)
entry.pack(pady=(16, 6), padx=20, fill="x")
entry.focus_set()

count = {"n": 0}


def stamp():
    count["n"] += 1
    with open(MARKER, "a", encoding="utf-8") as f:
        f.write(f"{count['n']} {time.strftime('%H:%M:%S')}\n")
    btn.config(text=f"stamp ({count['n']})")


btn = tk.Button(root, text="stamp (0)", command=stamp, font=("Consolas", 11))
btn.pack(pady=4)

root.mainloop()
