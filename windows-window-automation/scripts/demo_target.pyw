# demo_target.pyw — 演示用 Win32 目标窗口（tkinter）：标题 "WADemo"，含一个文本框。
# 由 win_capture.py 的演示流程拉起；也可手动：pythonw demo_target.pyw
import tkinter as tk

root = tk.Tk()
root.title("WADemo")
root.geometry("360x120")

entry = tk.Entry(root, font=("Consolas", 18), width=20)
entry.pack(pady=20, padx=20, fill="x")
entry.focus_set()

root.mainloop()
