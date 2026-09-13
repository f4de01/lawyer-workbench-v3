#!/usr/bin/env python3
"""把 Codex 的 rollout 日志切成阶段计时与 token 账。

Codex 桌面客户端与 CLI 都把每个会话写成一份 JSONL，落在 ~/.codex/sessions/<年>/<月>/<日>/ 下。
每行带毫秒时间戳；custom_tool_call 与 custom_tool_call_output 按 call_id 配对，
token_usage_record 逐次响应给出 input / cached_input / output / reasoning。
本脚本只读不写，零第三方依赖。

用法：
    python rollout分析.py --list 10              列最近 10 个会话，挑出要分析的那个
    python rollout分析.py <rollout.jsonl>        分析一个会话
    python rollout分析.py --compare a.jsonl b.jsonl c.jsonl   三条腿并排
    python rollout分析.py <rollout.jsonl> --json 机器可读

切法与 #123 一致：把每次工具调用的 [发起, 回来] 取区间并集算作工具时间，其余全部算模型。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path(os.path.expanduser("~")) / ".codex" / "sessions"

# 产品 CLI 的分段归属：段号与 #123 的五段对齐。
SEGMENTS = [
    ("段1/8 图引擎", re.compile(r"graph\.py")),
    ("段3 转换器", re.compile(r"md2docx\.py")),
    ("段4/5 门禁", re.compile(r"gate\.py")),
    ("归档", re.compile(r"archive\.py")),
    ("陈述", re.compile(r"statement\.py")),
    ("雏形/领域", re.compile(r"draft_node\.py|domain\.py|home\.py|intake\.py")),
]
READ_RE = re.compile(r"Get-Content|\bcat\b|\bsed\b|\bhead\b|\btype\b|Read-|Get-ChildItem|\bls\b|\bfind\b")
EXIT_RE = re.compile(r'"exit_code"\s*:\s*(-?\d+)')
TRUNC_RE = re.compile(r"truncated output")


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def payload_type(payload):
    return payload.get("type") if isinstance(payload, dict) else None


def load(path):
    """读一份 rollout，返回 (meta, events)。坏行跳过并计数。"""
    meta, events, bad = {}, [], 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if not isinstance(obj, dict):
                bad += 1
                continue
            kind = obj.get("type")
            payload = obj.get("payload")
            ts = parse_ts(obj.get("timestamp"))
            if kind == "session_meta" and isinstance(payload, dict):
                meta = payload
            events.append((ts, kind, payload_type(payload), payload))
    meta["_bad_lines"] = bad
    return meta, events


def classify(cmd):
    for name, pattern in SEGMENTS:
        if pattern.search(cmd):
            return name
    if READ_RE.search(cmd):
        return "读取"
    return "其他"


def command_text(payload):
    """tool call 的命令文本。桌面客户端把命令包在 exec_command({cmd:"..."}) 里。"""
    raw = payload.get("input")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return json.dumps(raw, ensure_ascii=False)
    return ""


def output_text(payload):
    out = payload.get("output")
    if isinstance(out, str):
        return out
    if isinstance(out, list):
        parts = []
        for chunk in out:
            if isinstance(chunk, dict):
                parts.append(str(chunk.get("text", "")))
            else:
                parts.append(str(chunk))
        return "\n".join(parts)
    return ""


def union_seconds(intervals):
    """区间并集的总长，单位秒。重叠的工具调用只算一次。"""
    spans = sorted(i for i in intervals if i[0] is not None and i[1] is not None)
    total, cur_lo, cur_hi = 0.0, None, None
    for lo, hi in spans:
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None:
                total += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
        else:
            cur_hi = max(cur_hi, hi)
    if cur_hi is not None:
        total += cur_hi - cur_lo
    return total


def analyse(path):
    meta, events = load(path)
    calls = {}          # call_id -> dict
    order = []
    tokens = []
    first_ts = last_ts = None
    task_started = task_complete = None
    user_msgs = []
    models = []         # 每个 turn_context 报一次；六轮要核对是不是同一个模型同一档强度
    efforts = []

    for ts, kind, ptype, payload in events:
        if ts is not None:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        if kind == "turn_context" and isinstance(payload, dict):
            if payload.get("model"):
                models.append(payload["model"])
            if payload.get("effort"):
                efforts.append(payload["effort"])
        if ptype == "task_started" and task_started is None:
            task_started = ts
        elif ptype == "task_complete":
            task_complete = ts
        elif ptype in ("custom_tool_call", "function_call", "local_shell_call"):
            cid = payload.get("call_id") or payload.get("id")
            cmd = command_text(payload)
            rec = {"call_id": cid, "start": ts, "end": None, "cmd": cmd,
                   "seg": classify(cmd), "exit": None, "truncated": 0}
            calls[cid] = rec
            order.append(rec)
        elif ptype in ("custom_tool_call_output", "function_call_output", "local_shell_call_output"):
            cid = payload.get("call_id") or payload.get("id")
            rec = calls.get(cid)
            if rec is None:
                continue
            rec["end"] = ts
            text = output_text(payload)
            codes = [int(c) for c in EXIT_RE.findall(text)]
            rec["exit"] = codes[-1] if codes else None
            rec["truncated"] = len(TRUNC_RE.findall(text))
        elif kind == "token_usage_record" and isinstance(payload, dict):
            usage = payload.get("usage") or {}
            tokens.append({"ts": ts, **usage})
        elif ptype == "message" and payload.get("role") == "user":
            content = payload.get("content")
            if isinstance(content, list):
                for chunk in content:
                    if isinstance(chunk, dict) and chunk.get("text"):
                        user_msgs.append(chunk["text"])
            elif isinstance(content, str):
                user_msgs.append(content)

    start = task_started or first_ts
    end = task_complete or last_ts
    wall = (end - start) if (start and end) else 0.0
    tool_time = union_seconds([(c["start"], c["end"]) for c in order])
    model_time = max(wall - tool_time, 0.0)

    # 开场：从起跑到第一次调用产品 CLI，即 #123 的「开场探查加整读」。
    opening_end, opening_calls = None, 0
    for rec in order:
        if rec["seg"] in ("段1/8 图引擎", "段3 转换器", "段4/5 门禁", "归档", "陈述", "雏形/领域"):
            opening_end = rec["start"]
            break
        opening_calls += 1
    opening = (opening_end - start) if (opening_end and start) else None

    by_seg = {}
    for rec in order:
        s = by_seg.setdefault(rec["seg"], {"n": 0, "sec": 0.0, "fail": 0, "trunc": 0})
        s["n"] += 1
        if rec["start"] and rec["end"]:
            s["sec"] += rec["end"] - rec["start"]
        if rec["exit"] not in (None, 0):
            s["fail"] += 1
        s["trunc"] += rec["truncated"]

    total = {k: sum(t.get(k, 0) or 0 for t in tokens) for k in
             ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
              "output_tokens", "reasoning_output_tokens")}
    uncached = total["input_tokens"] - total["cached_input_tokens"]

    return {
        "文件": str(path),
        "宿主": meta.get("originator"),
        "版本": meta.get("cli_version"),
        "模型": "/".join(sorted(set(models))) or None,
        "强度": "/".join(sorted(set(efforts))) or None,
        "工作区": meta.get("cwd"),
        "起": datetime.fromtimestamp(start, timezone.utc).isoformat() if start else None,
        "总墙钟": round(wall, 1),
        "模型时间": round(model_time, 1),
        "工具时间": round(tool_time, 1),
        "模型占比": round(100.0 * model_time / wall, 1) if wall else None,
        "往返次数": len(tokens),
        "工具调用次数": len(order),
        "开场秒": round(opening, 1) if opening is not None else None,
        "开场往返": opening_calls,
        "分段": by_seg,
        "非零退出": sum(1 for r in order if r["exit"] not in (None, 0)),
        "被截断的输出": sum(r["truncated"] for r in order),
        "token": total,
        "未命中缓存的输入": uncached,
        "缓存命中率": round(100.0 * total["cached_input_tokens"] / total["input_tokens"], 1)
                     if total["input_tokens"] else None,
        "每次往返未命中输入": round(uncached / len(tokens), 0) if tokens else None,
        "坏行": meta.get("_bad_lines", 0),
        "首句": (user_msgs[0][:120].replace("\n", " ") if user_msgs else ""),
        "_calls": order,
    }


def report(r, verbose=False):
    print("=" * 72)
    print("文件 {}".format(r["文件"]))
    print("宿主 {}  版本 {}".format(r["宿主"], r["版本"]))
    print("模型 {}  强度 {}".format(r["模型"], r["强度"]))
    print("工作区 {}".format(r["工作区"]))
    print("首句 {}".format(r["首句"]))
    print("-" * 72)
    print("总墙钟        {:>8.1f} 秒".format(r["总墙钟"]))
    print("  模型时间    {:>8.1f} 秒   ({}%)".format(r["模型时间"], r["模型占比"]))
    print("  工具时间    {:>8.1f} 秒".format(r["工具时间"]))
    print("往返次数      {:>8}".format(r["往返次数"]))
    print("工具调用次数  {:>8}".format(r["工具调用次数"]))
    if r["开场秒"] is not None:
        print("开场到首个CLI {:>8.1f} 秒   ({} 次工具调用)".format(r["开场秒"], r["开场往返"]))
    print("-" * 72)
    print("{:<16}{:>5}{:>10}{:>8}{:>8}".format("分段", "次数", "工具秒", "非零", "截断"))
    for name, s in sorted(r["分段"].items(), key=lambda kv: -kv[1]["sec"]):
        print("{:<16}{:>5}{:>10.2f}{:>8}{:>8}".format(name, s["n"], s["sec"], s["fail"], s["trunc"]))
    print("-" * 72)
    t = r["token"]
    print("输入 token          {:>12,}".format(t["input_tokens"]))
    print("  其中命中缓存      {:>12,}   缓存命中率 {}%".format(t["cached_input_tokens"], r["缓存命中率"]))
    print("  未命中（真付）    {:>12,}   平均每次往返 {:,.0f}".format(
        r["未命中缓存的输入"], r["每次往返未命中输入"] or 0))
    print("缓存写入            {:>12,}".format(t["cache_write_input_tokens"]))
    print("输出 token          {:>12,}".format(t["output_tokens"]))
    print("  其中思考          {:>12,}".format(t["reasoning_output_tokens"]))
    print("非零退出的调用      {:>12}   被截断的输出 {}".format(r["非零退出"], r["被截断的输出"]))
    if r["坏行"]:
        print("（跳过了 {} 个读不动的行）".format(r["坏行"]))
    if verbose:
        print("-" * 72)
        for i, c in enumerate(r["_calls"], 1):
            dur = (c["end"] - c["start"]) if (c["start"] and c["end"]) else 0.0
            print("{:>3} {:<14}{:>7.2f}s exit={:<5} {}".format(
                i, c["seg"], dur, str(c["exit"]), c["cmd"][:90].replace("\n", " ")))


def compare(results):
    keys = [("总墙钟", "秒"), ("模型时间", "秒"), ("工具时间", "秒"), ("模型占比", "%"),
            ("往返次数", ""), ("工具调用次数", ""), ("开场秒", "秒"), ("非零退出", ""),
            ("被截断的输出", ""), ("未命中缓存的输入", "tok"), ("缓存命中率", "%")]
    names = [Path(r["文件"]).name[:22] for r in results]
    print("{:<20}".format("") + "".join("{:>24}".format(n) for n in names))
    for key in ("模型", "强度"):
        print("{:<20}".format(key) + "".join("{:>24}".format(str(r.get(key))) for r in results))
    mods = set(str(r.get("模型")) for r in results)
    effs = set(str(r.get("强度")) for r in results)
    if len(mods) > 1 or len(effs) > 1:
        print(">>> 警告：这几轮不是同一个模型或同一档强度，不能直接比。")
    print()
    for key, unit in keys:
        row = "{:<20}".format(key + ("(" + unit + ")" if unit else ""))
        for r in results:
            v = r.get(key)
            row += "{:>24}".format("-" if v is None else ("{:,}".format(v) if isinstance(v, int) else v))
        print(row)
    print()
    for key in ("output_tokens", "reasoning_output_tokens", "input_tokens"):
        row = "{:<20}".format(key)
        for r in results:
            row += "{:>24,}".format(r["token"][key])
        print(row)


def list_sessions(n):
    files = sorted(SESSIONS_DIR.glob("**/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                meta = (json.loads(fh.readline()).get("payload") or {})
        except Exception:
            meta = {}
        print("{:<19} {:<16} {}".format(
            datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            str(meta.get("originator"))[:16], p))


def main():
    ap = argparse.ArgumentParser(description="切 Codex rollout 的阶段计时与 token 账")
    ap.add_argument("paths", nargs="*", help="rollout jsonl 路径")
    ap.add_argument("--list", type=int, metavar="N", help="列最近 N 个会话")
    ap.add_argument("--compare", action="store_true", help="并排比较多份")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("-v", "--verbose", action="store_true", help="逐条列出工具调用")
    args = ap.parse_args()

    if args.list:
        list_sessions(args.list)
        return 0
    if not args.paths:
        ap.print_help()
        return 2

    results = [analyse(Path(p)) for p in args.paths]
    if args.json:
        for r in results:
            r.pop("_calls", None)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.compare or len(results) > 1:
        compare(results)
    else:
        report(results[0], verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
