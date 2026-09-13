"""量 python stdio MCP server 的冷启动：从 Popen 到收到 initialize 应答。"""
import subprocess, sys, time, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
py = sys.argv[1] if len(sys.argv) > 1 else sys.executable
srv = os.path.join(HERE, "probe_server.py")
init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}) + "\n"
for i in range(5):
    t = time.time()
    p = subprocess.Popen([py, srv], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                         env={**os.environ, "PROBE_LOG": os.path.join(HERE, "coldstart.log")})
    p.stdin.write(init); p.stdin.flush()
    line = p.stdout.readline(); dt = time.time() - t
    p.stdin.close(); p.wait()
    print(f"{py} run{i}: initialize 应答耗时 {dt*1000:.0f} ms ok={'result' in line}")
