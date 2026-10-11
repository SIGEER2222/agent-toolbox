# cover.pyw — 遮挡层窗口（纯黑 + COVER 字样），位置/尺寸由环境变量指定：
#   COVER_X / COVER_Y / COVER_W / COVER_H
# 用于验证「目标窗口被完全遮住」时 PrintWindow / PostMessageW / UIA 是否照常工作。
import os
import tkinter as tk

x = int(os.environ.get("COVER_X", "0"))
y = int(os.environ.get("COVER_Y", "0"))
w = int(os.environ.get("COVER_W", "800"))
h = int(os.environ.get("COVER_H", "600"))

root = tk.Tk()
root.title("WACover")
root.geometry(f"{w}x{h}+{x}+{y}")
root.configure(bg="black")
tk.Label(root, text="COVER", fg="gray", bg="black",
         font=("Consolas", 48, "bold")).pack(expand=True)
root.mainloop()
