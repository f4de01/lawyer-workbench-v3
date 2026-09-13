#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出一版五段分段计时（开发机）。一条命令，跑一次就看见慢。

只测，不改任何代码。段 2（模型写 Markdown）不在本脚本里：它是模型自己的时间，
由一次真实会话的 stream 时间戳算出，见 会话计时.py。
"""
import argparse, json, os, pathlib, shutil, statistics, subprocess, sys, tempfile, time

REPO = pathlib.Path(r"D:/Claude/Programs/律师工作台v3.0")
GRAPH = REPO / "skills/loo0ng-graph/scripts/graph.py"
MD2DOCX = REPO / "skills/loo0ng-to-docx/scripts/md2docx.py"
GATE = REPO / "skills/loo0ng-to-docx/scripts/gate.py"
DOMAIN = REPO / "skills/loo0ng-domain/assets/破产"
PY = sys.executable

DRAFT = """# 关于管理人银行账户备案的报告

:left: 甲法院：

甲法院于甲年乙月丙日作出裁定，裁定受理乙公司破产清算一案，并指定本所担任管理人。

为便于工作开展，管理人开立了破产费用专用账户，现将账户备案如下：

| 账户名称 | 乙公司管理人 |
|---|---|
| 开户行 | 甲银行乙支行 |
| 开户日期 | 甲年乙月丙日 |

特此报告

:right: 乙公司管理人
:right: （盖章）
:right: 甲年乙月丙日
"""


def run(cmd, cwd=None):
    t = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return time.perf_counter() - t, p


def materialize():
    out = subprocess.run([PY, "scripts/skill-eval.py", "--materialize", "在办中"],
                         cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return pathlib.Path(out.stdout.strip().splitlines()[-1])


def stats(xs):
    return {"n": len(xs), "min": round(min(xs), 3), "中位": round(statistics.median(xs), 3),
            "max": round(max(xs), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--ws", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    ws = pathlib.Path(a.ws) if a.ws else materialize()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="segtime-"))
    draft = tmp / "稿子.md"
    draft.write_text(DRAFT, encoding="utf-8")
    tpl = ws / "模板/官方/1-3.关于管理人银行账户备案的报告.docx"
    assert tpl.exists(), tpl

    R = {}

    # --- 段 0：地板 ---
    R["0a python 空进程"] = [run([PY, "-c", ""])[0] for _ in range(a.runs)]
    R["0b python -c 'import docx'"] = [run([PY, "-c", "import docx"])[0] for _ in range(a.runs)]

    # --- 段 1：读图与派生视图重算 ---
    R["1a graph.py views（只重算）"] = [
        run([PY, str(GRAPH), "--domain", str(DOMAIN), "views"], cwd=ws)[0] for _ in range(a.runs)]
    R["1b graph.py validate（只校验）"] = [
        run([PY, str(GRAPH), "--domain", str(DOMAIN), "validate"], cwd=ws)[0] for _ in range(a.runs)]
    # 写一次（会改图）：每次在工作区副本上跑
    w = []
    for i in range(a.runs):
        c = tmp / ("ws%d" % i)
        shutil.copytree(ws, c)
        t, p = run([PY, str(GRAPH), "--domain", str(DOMAIN), "add-node",
                    "--module", "一、接管", "--title", "管理人银行账户备案报告"], cwd=c)
        w.append(t)
    R["1c graph.py add-node（写+重算）"] = w

    # --- 段 3：转换器 ---
    conv = []
    docx_out = None
    for i in range(a.runs):
        o = tmp / ("out%d.docx" % i)
        t, p = run([PY, str(MD2DOCX), str(draft), "--template", str(tpl), "--out", str(o)])
        if p.returncode != 0:
            print("md2docx 失败:", p.stdout, p.stderr); sys.exit(1)
        conv.append(t); docx_out = o
    R["3 md2docx.py（起进程+import docx+转换）"] = conv

    # --- 段 4：门禁推算层 ---
    R["4 gate.py --no-render（推算层）"] = [
        run([PY, str(GATE), str(docx_out), "--template", str(tpl), "--no-render", "--json"])[0]
        for _ in range(a.runs)]

    # --- 段 5：门禁含渲染层 ---
    full = []
    for _ in range(a.runs):
        t, p = run([PY, str(GATE), str(docx_out), "--template", str(tpl), "--json"])
        full.append(t)
    R["5 gate.py 全量（推算层+渲染层）"] = full

    print("工作区:", ws)
    print("每段 %d 次。单位秒。" % a.runs)
    print()
    w1 = max(len(k) for k in R)
    print("%-*s  %8s %8s %8s" % (w1, "段", "min", "中位", "max"))
    for k, v in R.items():
        s = stats(v)
        print("%-*s  %8.3f %8.3f %8.3f" % (w1, k, s["min"], s["中位"], s["max"]))
    med = {k: statistics.median(v) for k, v in R.items()}
    print()
    print("推算：渲染层本身 = 全量 - 推算层 = %.3f 秒" % (
        med["5 gate.py 全量（推算层+渲染层）"] - med["4 gate.py --no-render（推算层）"]))
    print("推算：import docx 本身 = %.3f 秒；转换本体 = md2docx - import docx 进程 = %.3f 秒" % (
        med["0b python -c 'import docx'"] - med["0a python 空进程"],
        med["3 md2docx.py（起进程+import docx+转换）"] - med["0b python -c 'import docx'"]))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            {k: {"样本": [round(x, 3) for x in v], **stats(v)} for k, v in R.items()},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("JSON:", a.json)
    shutil.rmtree(tmp, ignore_errors=True)


main()
