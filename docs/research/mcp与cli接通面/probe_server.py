"""最小 stdio MCP server（零依赖，python 3.9 可跑）：initialize / tools/list / tools/call。
tools/call 回一个 text 块 + 一个 image 块（1x1 PNG）+ 一个 resource_link + 一个内嵌 resource(text/html)。
启动、每次收到请求、stdin 关闭时都往 PROBE_LOG 追一行（含 PID、PPID、相对启动的秒数）。
"""
import sys, json, os, time
t0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get("PROBE_LOG") or os.path.join(HERE, "probe.log")
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
BIG = os.environ.get("PROBE_BIG")  # 若设了，text 块塞这么多个字符
HTML_PATH = os.path.join(HERE, "probe.html")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} +{time.time()-t0:.3f}s pid={os.getpid()} ppid={os.getppid()} {msg}\n")


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


log("start")
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    m = req.get("method")
    rid = req.get("id")
    log(f"recv {m}")
    if m == "initialize":
        send({"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": req["params"].get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "probe", "version": "0"}}})
    elif m == "tools/list":
        send({"jsonrpc": "2.0", "id": rid, "result": {"tools": [{
            "name": "probe_view",
            "description": "返回一段文本、一张 1x1 PNG 图片、一个指向本地 HTML 的 resource_link 与一个内嵌 text/html 资源。",
            "inputSchema": {"type": "object", "properties": {}}}]}})
    elif m == "tools/call":
        text = "PROBE_TEXT_OK 这是 text 块。\n\n| 列A | 列B |\n| --- | --- |\n| 1 | 2 |"
        if BIG:
            text = "X" * int(BIG)
        result = {"content": [
            {"type": "text", "text": text},
            {"type": "image", "data": PNG, "mimeType": "image/png"},
            {"type": "resource_link", "uri": "file:///" + HTML_PATH.replace("\\", "/"), "name": "probe.html", "mimeType": "text/html"},
            {"type": "resource", "resource": {"uri": "probe://inline.html", "mimeType": "text/html", "text": "<b>PROBE_HTML_OK</b>"}},
        ]}
        if not os.environ.get("PROBE_NOSTRUCT"):  # 设了 PROBE_NOSTRUCT 就不带 structuredContent
            result["structuredContent"] = {"probe": "ok"}
        send({"jsonrpc": "2.0", "id": rid, "result": result})
    elif m == "ping":
        send({"jsonrpc": "2.0", "id": rid, "result": {}})
    elif rid is not None:
        send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "not found"}})
log("stdin closed, exiting")
