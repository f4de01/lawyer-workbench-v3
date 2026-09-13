#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次真实「出一版」会话的分段计时：模型时间 vs 各 CLI 段的时间。

claude -p --output-format stream-json，按事件到达时刻切开：
  模型时间 = 上一个事件到本条 assistant 事件之间
  工具时间 = 该 assistant 的 tool_use 到对应 tool_result 之间
工具时间再按命令里调的是哪个脚本归到五段里。
"""
import argparse, collections, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time

REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
PY = sys.executable
PROMPT_CASE = REPO / "evals/用例/办节点出一版"


def materialize(seed):
    out = subprocess.run([PY, "scripts/skill-eval.py", "--materialize", seed],
                         cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return pathlib.Path(out.stdout.strip().splitlines()[-1])


def classify(tool_name, inp):
    if tool_name != "Bash":
        return "读盘/其他工具(%s)" % tool_name
    c = inp.get("command", "")
    if "graph.py" in c:
        return "段1 图引擎(graph.py)"
    if "md2docx.py" in c:
        return "段3 转换器(md2docx.py)"
    if "gate.py" in c:
        return "段5 门禁全量(gate.py 含渲染)" if "--no-render" not in c else "段4 门禁推算(gate.py --no-render)"
    return "其他 Bash(读盘/拷贝)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="在办中")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--max-turns", type=int, default=70)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--out", default="会话.json")
    a = ap.parse_args()

    prompt = a.prompt or (PROMPT_CASE / "提示词.md").read_text(encoding="utf-8").strip()
    prompt = "/loo0ng-doit " + prompt

    ws = materialize(a.seed)
    home = pathlib.Path(tempfile.mkdtemp(prefix="loo0ng-home-"))

    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    env["MSYS_NO_PATHCONV"] = "1"
    env["LOO0NG_HOME"] = str(home)

    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--max-turns", str(a.max_turns), "--permission-mode", "acceptEdits",
           "--no-session-persistence", "--allowedTools", "Bash"]

    print("工作区:", ws)
    print("起跑…")
    t0 = time.perf_counter()
    events = []
    raw = open(a.out + ".raw.jsonl", "w", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace", bufsize=1)
    try:
        for line in p.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            events.append((time.perf_counter() - t0, ev))
            raw.write(json.dumps({"t": round(time.perf_counter() - t0, 3), "ev": ev},
                                 ensure_ascii=False) + chr(10))
            if time.perf_counter() - t0 > a.timeout:
                p.kill(); break
    finally:
        p.wait(timeout=60)
        raw.close()
    total = time.perf_counter() - t0
    err = p.stderr.read()

    # 归段
    types = collections.Counter(ev.get("type") for _, ev in events)
    intervals = []
    model_time = 0.0
    tool_time = collections.defaultdict(float)
    tool_calls = collections.Counter()
    pending = {}   # tool_use_id -> t
    prev_t = 0.0
    timeline = []
    for t, ev in events:
        typ = ev.get("type")
        if typ == "assistant":
            dt = t - prev_t
            model_time += dt
            timeline.append(("模型", round(dt, 2), ""))
            for blk in ev.get("message", {}).get("content", []):
                if blk.get("type") == "tool_use":
                    pending[blk.get("id")] = (t, classify(blk.get("name"), blk.get("input", {})),
                                              str(blk.get("input", {}).get("command", ""))[:110])
        elif typ == "user":
            for blk in ev.get("message", {}).get("content", []):
                if blk.get("type") == "tool_result":
                    got = pending.pop(blk.get("tool_use_id"), None)
                    if got:
                        st, seg, c = got
                        tool_time[seg] += t - st
                        tool_calls[seg] += 1
                        intervals.append((st, t))
                        timeline.append((seg, round(t - st, 2), c))
        prev_t = t

    # 工具区间取并集，其余全部算模型/宿主：按事件类型归段会漏掉未识别的事件类型
    merged = []
    for a_, b_ in sorted(intervals):
        if merged and a_ <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b_)
        else:
            merged.append([a_, b_])
    tool_union = sum(b_ - a_ for a_, b_ in merged)
    startup = events[0][0] if events else 0.0
    model_time = total - tool_union - startup

    res = [e for _, e in events if e.get("type") == "result"]
    print()
    print("总墙钟 %.1f 秒（%d 个事件）" % (total, len(events)))
    if res:
        r = res[-1]
        print("result: subtype=%s duration_ms=%s num_turns=%s is_error=%s" % (
            r.get("subtype"), r.get("duration_ms"), r.get("num_turns"), r.get("is_error")))
    print()
    print("%-34s %9s %6s %7s" % ("段", "秒", "次", "占比"))
    print("事件类型:", dict(types))
    print("%-34s %9.1f %6s %6.1f%%" % ("段2 模型（写稿+整读+全部推理）", model_time, "-", 100 * model_time / total))
    for seg, s in sorted(tool_time.items(), key=lambda kv: -kv[1]):
        print("%-34s %9.1f %6d %6.1f%%" % (seg, s, tool_calls[seg], 100 * s / total))
    print("%-34s %9.1f %6s %6.1f%%" % ("工具合计（并集）", tool_union, sum(tool_calls.values()), 100 * tool_union / total))
    print("%-34s %9.1f %6s %6.1f%%" % ("CLI 启动（首事件之前）", startup, "-", 100 * startup / total))
    rest = 0.0

    pathlib.Path(a.out).write_text(json.dumps({
        "工作区": str(ws), "总墙钟": round(total, 2),
        "模型秒": round(model_time, 2),
        "各段": {k: {"秒": round(v, 2), "次": tool_calls[k]} for k, v in tool_time.items()},
        "工具并集秒": round(tool_union, 2), "启动秒": round(startup, 2),
        "事件类型": dict(types),
        "result": res[-1] if res else None,
        "时间线": timeline,
        "stderr": err[-2000:],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JSON:", a.out)
    if err.strip():
        print("stderr:", err[-600:])


main()
