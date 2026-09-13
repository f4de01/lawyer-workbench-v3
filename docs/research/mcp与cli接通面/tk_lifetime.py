"""起一个 tkinter 窗口（pythonw，DETACHED_PROCESS），父进程立刻退出；由外层再查窗口进程还在不在。
窗口 20 秒后自毁，看进程是否随窗口一起退。"""
import subprocess, sys, os
pyw = sys.executable.replace("python.exe", "pythonw.exe")
code = "import tkinter as t;r=t.Tk();r.title('probe-tk');r.geometry('200x100');r.after(20000,r.destroy);r.mainloop()"
p = subprocess.Popen([pyw, "-c", code], creationflags=0x8 | 0x200)  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tk_pid.txt"), "w").write(str(p.pid))
print("spawned", p.pid, "parent exiting now")
