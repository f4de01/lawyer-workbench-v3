#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次真实「出一版」会话的分段计时：Codex 侧。

codex exec --json 的流里 item.started/item.completed 圈出工具时间，其余算模型。
"""
import argparse, collections, json, os, pathlib, shutil, subprocess, sys, tempfile, time

REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
PY = sys.executable
PROMPT_CASE = REPO / "evals/用例/办节点出一版"
STAND_IN = "读 ~/.agents/skills/{skill}/SKILL.md 并照做：{prompt}"
TOOL_ITEMS = {"command_execution", "file_change", "mcp_tool_call", "web_search"}


def materialize(seed):
    out = subprocess.run([PY, "scripts/skill-eval.py", "--materialize", seed],
                         cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return pathlib.Path(out.stdout.strip().splitlines()[-1])


def classify(item):
    c = item.get("command") or ""
    if item.get("type") != "command_execution":
        return "其他 item(%s)" % item.get("type")
    if "graph.py" in c:
        return "段1 图引擎(graph.py)"
    if "md2docx.py" in c:
        return "段3 转换器(md2docx.py)"
    if "gate.py" in c:
        return "段4 门禁推算(--no-render)" if "--no-render" in c else "段5 门禁全量(含渲染)"
    if "uv " in c or "pip " in c or "python -m venv" in c:
        return "自备环境(uv/pip)"
    return "其他命令(读盘/拷贝)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="在办中")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", default="会话codex.json")
    a = ap.parse_args()

    prompt = STAND_IN.format(skill="loo0ng-doit",
                             prompt=(PROMPT_CASE / "提示词.md").read_text(encoding="utf-8").strip())
    ws = materialize(a.seed)
    home = pathlib.Path(tempfile.mkdtemp(prefix="loo0ng-home-"))
    last = pathlib.Path(tempfile.mkdtemp(prefix="codexlast-")) / "last.txt"

    env = dict(os.environ)
    env["LOO0NG_HOME"] = str(home)
    exe = shutil.which("codex") or "codex"
    cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write",
           "-C", str(ws), "--json", "-o", str(last), "-"]

    print("工作区:", ws)
    t0 = time.perf_counter()
    raw = open(a.out + ".raw.jsonl", "w", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=ws, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
    p.stdin.write(prompt); p.stdin.close()
    events = []
    try:
        for line in p.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            t = time.perf_counter() - t0
            events.append((t, ev))
            raw.write(json.dumps({"t": round(t, 3), "ev": ev}, ensure_ascii=False) + chr(10))
            if t > a.timeout:
                p.kill(); break
    finally:
        p.wait(timeout=60); raw.close()
    total = time.perf_counter() - t0
    err = p.stderr.read()

    pend = {}
    tool_time = collections.defaultdict(float)
    tool_calls = collections.Counter()
    intervals = []
    timeline = []
    turns = 0
    for t, ev in events:
        item = ev.get("item") or {}
        if ev.get("type") == "item.started" and item.get("type") in TOOL_ITEMS:
            turns += 1
            pend[item.get("id")] = (t, item)
        elif ev.get("type") == "item.completed":
            got = pend.pop(item.get("id"), None)
            if got:
                st, it0 = got
                seg = classify({**it0, **item})
                tool_time[seg] += t - st
                tool_calls[seg] += 1
                intervals.append((st, t))
                timeline.append((seg, round(t - st, 2), str((item.get("command") or ""))[:110]))
    merged = []
    for x, y in sorted(intervals):
        if merged and x <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], y)
        else:
            merged.append([x, y])
    tool_union = sum(y - x for x, y in merged)
    startup = events[0][0] if events else 0.0
    model_time = total - tool_union - startup

    print()
    print("总墙钟 %.1f 秒，工具类 item %d 个（= 跑器口径的回合数）" % (total, turns))
    print("%-34s %9s %6s %7s" % ("段", "秒", "次", "占比"))
    print("%-34s %9.1f %6s %6.1f%%" % ("段2 模型（写稿+整读+全部推理）", model_time, "-", 100 * model_time / total))
    for seg, s in sorted(tool_time.items(), key=lambda kv: -kv[1]):
        print("%-34s %9.1f %6d %6.1f%%" % (seg, s, tool_calls[seg], 100 * s / total))
    print("%-34s %9.1f %6s %6.1f%%" % ("工具合计（并集）", tool_union, sum(tool_calls.values()), 100 * tool_union / total))
    print("%-34s %9.1f %6s %6.1f%%" % ("CLI 启动（首事件之前）", startup, "-", 100 * startup / total))

    pathlib.Path(a.out).write_text(json.dumps({
        "工作区": str(ws), "总墙钟": round(total, 2), "工具item数": turns,
        "模型秒": round(model_time, 2), "工具并集秒": round(tool_union, 2), "启动秒": round(startup, 2),
        "各段": {k: {"秒": round(v, 2), "次": tool_calls[k]} for k, v in tool_time.items()},
        "时间线": timeline, "退出码": p.returncode, "stderr": err[-2000:],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JSON:", a.out, "退出码", p.returncode)
    if err.strip():
        print("stderr:", err[-400:])


main()
