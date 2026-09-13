"""在 Codex 终端 TUI（winpty 假 pty）里跑一条提示词，收下所有输出并剥掉 ANSI，看 Markdown 表格与 Mermaid 围栏块被渲成什么。
照 #132 的测法：指 codex.exe 真身、开在已信任目录、stdin 用 PIPE。"""
import subprocess, sys, os, re, time
EXE = r"C:\Users\32892\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe"
CWD = r"C:\Users\32892\Documents\Codex\2026-09-06\new-chat"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tui_table.raw")
PROMPT = ("不要调用任何工具、不要读文件。把下面两样原样输出在回复里，别的什么都不写："
          "第一，一张两列两行的 Markdown 表格，表头是 列A 与 列B，一行数据是 1 与 2；"
          "第二，一个 mermaid 围栏代码块，内容是 graph TD; A-->B。")
env = dict(os.environ, COLUMNS="120", LINES="40", TERM="xterm-256color")
t0 = time.time()
p = subprocess.Popen(["winpty", "-Xallow-non-tty", "--", EXE, "--sandbox", "read-only", PROMPT],
                     cwd=CWD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
buf = b""
deadline = time.time() + 150
import threading
def reader():
    global buf
    while True:
        ch = p.stdout.read(1)
        if not ch: break
        buf += ch
th = threading.Thread(target=reader, daemon=True); th.start()
sent_quit = False
while time.time() < deadline and p.poll() is None:
    time.sleep(2)
    txt = buf.decode("utf-8", "replace")
    # 回复出来之后（看见 mermaid 或 表格），发 /quit 退出
    if not sent_quit and ("A-->B" in txt or "graph TD" in txt) and time.time() - t0 > 20:
        time.sleep(4)
        try:
            p.stdin.write(b"/quit\r"); p.stdin.flush()
        except Exception:
            pass
        sent_quit = True
        time.sleep(4)
        break
if p.poll() is None:
    p.kill()
open(OUT, "wb").write(buf)
ansi = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[=>]|\x1b\([B0]|\r")
clean = ansi.sub(b"", buf).decode("utf-8", "replace")
print("elapsed", round(time.time() - t0, 1), "bytes", len(buf))
print(clean[-3500:])
