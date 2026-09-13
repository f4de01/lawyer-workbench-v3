#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段 5（门禁渲染层）随文书页数怎么长。全量减 --no-render。"""
import pathlib, statistics, subprocess, sys, tempfile, time
REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
MD2DOCX = REPO / "skills/loo0ng-to-docx/scripts/md2docx.py"
GATE = REPO / "skills/loo0ng-to-docx/scripts/gate.py"
PY = sys.executable
TPL = pathlib.Path(sys.argv[1])
RUNS = 3
HEAD = "# 关于管理人银行账户备案的报告\n\n:left: 甲法院：\n\n"
PARA = "甲法院于甲年乙月丙日作出裁定，裁定受理乙公司破产清算一案，并指定本所担任管理人。为便于工作开展，管理人开立了破产费用专用账户，现将账户备案情况报告如下，请予备案。\n\n"
TAIL = "\n特此报告\n\n:right: 乙公司管理人\n:right: （盖章）\n:right: 甲年乙月丙日\n"

def med(cmd):
    xs = []
    for _ in range(RUNS):
        t = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        xs.append(time.perf_counter() - t)
    return statistics.median(xs), p

tmp = pathlib.Path(tempfile.mkdtemp(prefix="rscale-"))
print("%-8s %-10s %-12s %-12s %-10s %s" % ("段落", "docx字节", "全量中位", "推算层中位", "渲染层", "页数"))
for np_ in (1, 20, 80, 200):
    md = tmp / ("d%d.md" % np_); md.write_text(HEAD + PARA * np_ + TAIL, encoding="utf-8")
    out = tmp / ("d%d.docx" % np_)
    subprocess.run([PY, str(MD2DOCX), str(md), "--template", str(TPL), "--out", str(out)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not out.exists():
        print(np_, "转换失败"); continue
    t_full, p_full = med([PY, str(GATE), str(out), "--template", str(TPL)])
    t_est, _ = med([PY, str(GATE), str(out), "--template", str(TPL), "--no-render"])
    pg = [l for l in p_full.stdout.splitlines() if "页数" in l]
    print("%-8d %-10d %-12.3f %-12.3f %-10.3f %s" % (np_, out.stat().st_size, t_full, t_est,
          t_full - t_est, (pg[0].strip()[:40] if pg else "-")))
