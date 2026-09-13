#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段 3（转换器）与段 4（门禁推算层）随文书规模怎么长。渲染层不测，避免与别的会话抢 Word。"""
import pathlib, statistics, subprocess, sys, tempfile, time
REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
MD2DOCX = REPO / "skills/loo0ng-to-docx/scripts/md2docx.py"
GATE = REPO / "skills/loo0ng-to-docx/scripts/gate.py"
PY = sys.executable
TPL = pathlib.Path(sys.argv[1])
RUNS = 3

HEAD = """# 关于管理人银行账户备案的报告

:left: 甲法院：

"""
PARA = "甲法院于甲年乙月丙日作出裁定，裁定受理乙公司破产清算一案，并指定本所担任管理人。为便于工作开展，管理人开立了破产费用专用账户，现将账户备案情况报告如下，请予备案。\n\n"
ROW = "| 开户行%d | 甲银行乙支行 |\n"
TAIL = """
特此报告

:right: 乙公司管理人
:right: （盖章）
:right: 甲年乙月丙日
"""

def build(nparas, nrows):
    s = HEAD + PARA * nparas
    if nrows:
        s += "\n| 项目 | 内容 |\n|---|---|\n"
        s += "".join(ROW % i for i in range(nrows))
        s += "\n"
    return s + TAIL

def med(cmd):
    xs = []
    for _ in range(RUNS):
        t = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        xs.append(time.perf_counter() - t)
    return statistics.median(xs), p

tmp = pathlib.Path(tempfile.mkdtemp(prefix="docscale-"))
print("%-10s %-8s %-10s %-12s %-12s %s" % ("段落", "表行", "docx字节", "md2docx中位", "推算层中位", "门禁结论"))
for np_, nr in ((1, 3), (10, 10), (40, 50), (150, 200), (500, 800)):
    md = tmp / ("d%d.md" % np_)
    md.write_text(build(np_, nr), encoding="utf-8")
    out = tmp / ("d%d.docx" % np_)
    t1, p1 = med([PY, str(MD2DOCX), str(md), "--template", str(TPL), "--out", str(out)])
    if not out.exists():
        print(np_, nr, "转换失败", p1.stdout[-200:], p1.stderr[-200:]); continue
    t2, p2 = med([PY, str(GATE), str(out), "--template", str(TPL), "--no-render"])
    concl = [l for l in p2.stdout.splitlines() if l.strip()][:1]
    print("%-10d %-8d %-10d %-12.3f %-12.3f %s" % (np_, nr, out.stat().st_size, t1, t2,
          (concl[0][:40] if concl else "rc=%d" % p2.returncode)))
