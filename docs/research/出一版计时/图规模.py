#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段 1（读图与派生视图重算）随图规模怎么长。"""
import json, pathlib, shutil, statistics, subprocess, sys, tempfile, time
REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
GRAPH = REPO / "skills/loo0ng-graph/scripts/graph.py"
DOMAIN = REPO / "skills/loo0ng-domain/assets/破产"
PY = sys.executable
BASE = pathlib.Path(sys.argv[1])
RUNS = 5

def blow(src, dst, mult, entries_per_node):
    g = json.loads((src / "图.json").read_text(encoding="utf-8"))
    mods = g["模块"]
    orig = [json.loads(json.dumps(m)) for m in mods]
    for k in range(1, mult):
        for m in orig:
            m2 = json.loads(json.dumps(m))
            m2["id"] = m2["id"] + "-x%d" % k
            m2["标题"] = m2["标题"] + "·副%d" % k
            for n in m2.get("节点", []):
                n["id"] = n["id"] + "-x%d" % k
                n["标题"] = n["标题"] + "·副%d" % k
            mods.append(m2)
    n_nodes = 0
    for m in mods:
        for n in m.get("节点", []):
            n_nodes += 1
            ent = n.setdefault("条目", [])
            for j in range(entries_per_node):
                ent.append({"动作": "生成", "时间": "2026-09-12T22:05:14-07:00", "来源": "agent",
                            "文书": "文书/x/x-v%d.docx" % (j + 1),
                            "源": "文书/x/x-v%d.md" % (j + 1),
                            "审查报告": "文书/x/x-v%d-审查报告.md" % (j + 1)})
    shutil.copytree(src, dst)
    (dst / "图.json").write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(mods), n_nodes, len((dst / "图.json").read_text(encoding="utf-8").encode("utf-8"))

def t_views(ws):
    xs = []
    for _ in range(RUNS):
        t = time.perf_counter()
        p = subprocess.run([PY, str(GRAPH), "--domain", str(DOMAIN), "views"], cwd=ws,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        xs.append(time.perf_counter() - t)
        if p.returncode != 0:
            return None, p.stderr[-300:]
    return statistics.median(xs), None

tmp = pathlib.Path(tempfile.mkdtemp(prefix="graphscale-"))
print("%-8s %-8s %-10s %-10s %-10s %s" % ("模块", "节点", "图.json字节", "视图md字节", "views中位秒", "备注"))
for mult, ent in ((1, 0), (2, 1), (4, 2), (8, 3), (16, 5)):
    d = tmp / ("m%d" % mult)
    nm, nn, nb = blow(BASE, d, mult, ent)
    s, err = t_views(d)
    vmd = (d / "图视图.md")
    print("%-8d %-8d %-10d %-10s %-10s %s" % (nm, nn, nb,
          vmd.stat().st_size if vmd.exists() else "-",
          ("%.3f" % s) if s else "-", err or ""))
shutil.rmtree(tmp, ignore_errors=True)
