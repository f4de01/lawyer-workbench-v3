"""对 Codex exec 跑两组：text 块 60,000 个字符（约 1.5 万 token），带 / 不带 structuredContent。
看模型报的开头结尾与总长、以及 turn.completed 的 input_tokens，判断 Codex 交给模型的是什么。"""
import subprocess, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PY = "C:/Users/32892/AppData/Local/Python/pythoncore-3.14-64/python.exe"
SRV = os.path.join(HERE, "probe_server.py").replace("\\", "/")
PROMPT = ("请调用 MCP 工具 probe_view（不要用 shell、不要读文件），然后只回答四项："
          "(1) 工具结果里 text 块开头 20 个字符原样；(2) 结尾 20 个字符原样；(3) text 块里除了大写 X 之外还有没有别的字符，有就原样抄出来；"
          "(4) 你收到的整个工具结果原样是什么形状（是 JSON 对象还是若干内容块，各是什么类型）。")
for tag, extra in [("struct", ""), ("nostruct", ', PROBE_NOSTRUCT="1"')]:
    log = os.path.join(HERE, f"size_{tag}.log").replace("\\", "/")
    if os.path.exists(log): os.remove(log)
    envtoml = f'mcp_servers.probe.env={{PROBE_BIG="60000", PROBE_LOG="{log}"{extra}}}'
    cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-C", HERE,
           "-c", f'mcp_servers.probe.command="{PY}"', "-c", f'mcp_servers.probe.args=["{SRV}"]', "-c", envtoml, PROMPT]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", shell=True, timeout=400)
    print("=====", tag, "exit", r.returncode)
    for line in r.stdout.splitlines():
        try: d = json.loads(line)
        except Exception: continue
        it = d.get("item", {})
        if it.get("type") == "mcp_tool_call" and it.get("result"):
            c = it["result"]["content"][0]["text"]
            print("JSONL text len", len(c), "structured_content" in it["result"], it["result"].get("structured_content"))
        if it.get("type") == "agent_message": print("AGENT:", it["text"][:1200])
        if d.get("type") == "turn.completed": print("USAGE", d["usage"])
    print("STDERR", r.stderr[:300])
