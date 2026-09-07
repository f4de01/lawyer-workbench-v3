#!/usr/bin/env python3
"""【一次性原型，勿入 main】同一批样本，Word 与 WPS 两个真渲染器逐件对照，第三列并排放 #55 的推算区间。

回答 issue #60（地图 #54）：两个真渲染器之间差多少？会不会在阈值上给出相反的结论？

样本与 #55 完全一致，直接复用 prototype/版面推算/对照.py 的 build_samples。
每件出两份 PDF：Word COM 一份、KWPS.Application 走 32 位宿主一份，参数表逐字相同，串行（本机两个
Office 进程同时起会互相关掉）。两份 PDF 各跑一遍 pdf_checks 的三项（页数 / 空白页 / 最大行高）。

跑：python prototype/双引擎对照/对照.py [--json 结果.json] [--limit N]
"""
import argparse
import base64
import importlib.util
import json
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tests" / "loo0ng-to-docx"))
sys.path.insert(0, str(REPO / "skills" / "loo0ng-to-docx" / "scripts"))
sys.path.insert(0, str(REPO / "prototype" / "版面推算"))

import gate  # noqa: E402
import pymupdf  # noqa: E402
import 推算  # noqa: E402

_spec = importlib.util.spec_from_file_location("对照55", REPO / "prototype" / "版面推算" / "对照.py")
对照55 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(对照55)

PS32 = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"

# 与 gate.PS_RENDER 逐字同构，只换 ProgID；多回显引擎身份与 ComputeStatistics 的返回值，
# 这两条顺带验掉 #56 留下的「Wd* 枚举数值在 WPS 里是否相同」与「Application.Path 能不能分辨引擎」。
PS_RENDER = r"""
$ErrorActionPreference = 'Stop'
try { $w = New-Object -ComObject {PROGID} } catch { Write-Output ('NOAPP ' + $_.Exception.Message); exit 3 }
$w.Visible = $false
$w.DisplayAlerts = 0
Write-Output ('ENGINE ' + $w.Name + '|' + $w.Path + '|' + $w.Version + '|' + $w.Build)
try {
  $d = $w.Documents.Open('{IN}', $false, $true, $false)
  $stat = $d.ComputeStatistics(2)
  Write-Output ('STAT ' + $stat)
  $d.ExportAsFixedFormat('{OUT}', 17)
  $d.Close(0)
  Write-Output 'OK'
} catch { Write-Output ('EXPORTFAIL ' + $_.Exception.Message); exit 4 }
finally { $w.Quit() }
"""

ENGINES = [
    ("Word", "Word.Application", None),          # 64 位宿主，与 gate.py 现行通道一致
    ("WPS", "KWPS.Application", PS32),           # KWPS 只注册在 WOW6432Node，必须 32 位宿主
]


def render(docx_path, progid, ps_exe):
    """回 (pdf 路径, 临时目录, 引擎身份串, ComputeStatistics 返回值)。任何一步不成抛 gate.CannotRun。"""
    exe = ps_exe or shutil.which("powershell.exe")
    if not exe or not pathlib.Path(exe).is_file():
        raise gate.CannotRun("找不到宿主 %s" % (ps_exe or "powershell.exe"))
    base = pathlib.Path(tempfile.gettempdir()) / "双引擎对照"
    base.mkdir(parents=True, exist_ok=True)
    while True:
        work = base / secrets.token_hex(4)
        try:
            os.mkdir(work)
            break
        except FileExistsError:
            continue
    pdf = work / (docx_path.stem + ".pdf")
    script = (PS_RENDER.replace("{PROGID}", progid)
              .replace("{IN}", str(docx_path.resolve()).replace("'", "''"))
              .replace("{OUT}", str(pdf).replace("'", "''")))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    first = ""
    for _ in range(2):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180)
        except subprocess.TimeoutExpired:
            raise gate.CannotRun("%s 导出超过 180 秒没有回来" % progid)
        out = (r.stdout or "").strip()
        lines = out.splitlines()
        engine = next((l[7:] for l in lines if l.startswith("ENGINE ")), "?")
        stat = next((l[5:] for l in lines if l.startswith("STAT ")), "?")
        if r.returncode == 0 and pdf.is_file():
            return pdf, work, engine, stat
        first = lines[0] if lines else ((r.stderr or "").strip().splitlines() or ["退出码 %d" % r.returncode])[0]
        if first.startswith("NOAPP"):
            break
    shutil.rmtree(work, ignore_errors=True)
    raise gate.CannotRun("%s 没能出 PDF（%s）" % (progid, first))


def measure(pdf):
    """与 gate.pdf_checks 同口径取三项：页数、空白页、最大行高。"""
    d = pymupdf.open(str(pdf))
    try:
        pages = len(d)
        blank, max_row, per_page = [], 0.0, []
        for i, page in enumerate(d, 1):
            body = gate._page_body_text(page)
            if not body.strip() and not page.get_images():
                blank.append(i)
            hi = 0.0
            for t in page.find_tables().tables:
                for row in t.rows:
                    hi = max(hi, row.bbox[3] - row.bbox[1])
            per_page.append(round(hi, 1))
            max_row = max(max_row, hi)
        return {"页数": pages, "空白页": blank, "最大行高": round(max_row, 1), "各页最大行高": per_page}
    finally:
        d.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="把逐件结果写进这个文件")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    work = pathlib.Path(tempfile.mkdtemp(prefix="双引擎-"))
    samples = 对照55.build_samples(work)
    if args.limit:
        samples = samples[:args.limit]
    print("样本 %d 件 × 2 个引擎，串行……\n" % len(samples), file=sys.stderr)

    rows = []
    ids = {}
    for i, (name, docx, kind) in enumerate(samples, 1):
        row = {"名字": name, "类型": kind, "推算": 推算.band(docx), "引擎": {}}
        for label, progid, ps_exe in ENGINES:
            try:
                pdf, wd, engine, stat = render(docx, progid, ps_exe)
            except gate.CannotRun as e:
                print("!! %s / %s 渲染失败：%s" % (name, label, e), file=sys.stderr)
                row["引擎"][label] = None
                continue
            try:
                m = measure(pdf)
                m["ComputeStatistics(2)"] = stat
                row["引擎"][label] = m
                ids.setdefault(label, engine)
            finally:
                shutil.rmtree(wd, ignore_errors=True)
        rows.append(row)
        w, k = row["引擎"].get("Word"), row["引擎"].get("WPS")
        print("[%2d/%d] %-18s Word %s / WPS %s" % (
            i, len(samples), name,
            "%d页 %.0f磅" % (w["页数"], w["最大行高"]) if w else "失败",
            "%d页 %.0f磅" % (k["页数"], k["最大行高"]) if k else "失败"), file=sys.stderr)

    report(rows, ids)
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps({"引擎身份": ids, "逐件": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n逐件结果已写 %s" % args.json)
    return 0


def report(rows, ids):
    MAXP, MAXR = gate.DEFAULT_MAX_PAGES, gate.DEFAULT_MAX_ROW_HEIGHT
    print("\n===== 引擎身份 =====")
    for k, v in ids.items():
        print("  %-5s %s" % (k, v))
    print("  （字段序：Application.Name | .Path | .Version | .Build）")

    print("\n===== 三列对照：推算区间 / Word 实测 / WPS 实测 =====")
    hdr = "%-17s | %-9s %-5s %-6s | %-13s %-7s %-8s | %s"
    print(hdr % ("件", "页数推算", "Word", "WPS", "行高推算(磅)", "Word", "WPS", "空白页 推算/Word/WPS"))
    print("-" * 125)
    both = [r for r in rows if r["引擎"].get("Word") and r["引擎"].get("WPS")]
    page_same = 0
    blank_same = 0
    deltas = []
    flips = []
    for r in rows:
        e, w, k = r["推算"], r["引擎"].get("Word"), r["引擎"].get("WPS")
        if not (w and k):
            print("%-17s | 渲染失败：Word=%s WPS=%s" % (r["名字"][:17], bool(w), bool(k)))
            continue
        page_same += (w["页数"] == k["页数"])
        blank_same += (w["空白页"] == k["空白页"])
        if w["最大行高"] > 0 and k["最大行高"] > 0:
            deltas.append(((k["最大行高"] - w["最大行高"]) / w["最大行高"], r["名字"], w["最大行高"], k["最大行高"]))
        for 判据, wv, kv, thr in (("页数", w["页数"], k["页数"], MAXP),
                                  ("行高", w["最大行高"], k["最大行高"], MAXR)):
            if (wv > thr) != (kv > thr):
                flips.append((r["名字"], 判据, wv, kv, thr))
        if (len(w["空白页"]) > 0) != (len(k["空白页"]) > 0):
            flips.append((r["名字"], "空白页", w["空白页"], k["空白页"], "有/无"))
        mark = "" if w["页数"] == k["页数"] else " !"
        rmark = "" if abs(w["最大行高"] - k["最大行高"]) < 0.05 else " !"
        print(hdr % (r["名字"][:17],
                     "%d-%d" % (e["页数"][0], e["页数"][1]), str(w["页数"]), str(k["页数"]) + mark,
                     "%.0f-%.0f" % (e["最大行高"][0], e["最大行高"][1]),
                     "%.0f" % w["最大行高"], "%.0f%s" % (k["最大行高"], rmark),
                     "%s / %s / %s" % (e["空白页_hi"] or "无", w["空白页"] or "无", k["空白页"] or "无")))

    print("\n===== 汇总（%d 件两个引擎都出了 PDF）=====" % len(both))
    print("页数    两引擎相同：%d/%d" % (page_same, len(both)))
    print("空白页  两引擎相同：%d/%d" % (blank_same, len(both)))
    if deltas:
        deltas.sort(key=lambda x: abs(x[0]), reverse=True)
        print("最大行高 WPS 相对 Word 的偏差：中位 %+.2f%%，最大 %+.2f%%（%s：Word %.1f → WPS %.1f）" % (
            100 * sorted(d[0] for d in deltas)[len(deltas) // 2],
            100 * deltas[0][0], deltas[0][1], deltas[0][2], deltas[0][3]))
        print("  偏差最大的五件：")
        for d, name, wv, kv in deltas[:5]:
            print("    %-18s Word %7.1f  WPS %7.1f  %+.2f%%" % (name, wv, kv, 100 * d))

    print("\n===== 阈值翻转（本票的红灯：页数>%d / 行高>%.0f 磅 / 空白页有无）=====" % (MAXP, MAXR))
    if flips:
        for name, 判据, wv, kv, thr in flips:
            print("  !! %s %s：Word=%s WPS=%s（阈值 %s）" % (name, 判据, wv, kv, thr))
    else:
        print("  无翻转：没有一件在阈值上被两个引擎判成相反结论。")

    print("\n===== 同一尺度：推算区间宽度 vs 两引擎间距 =====")
    over = 0
    for r in rows:
        e, w, k = r["推算"], r["引擎"].get("Word"), r["引擎"].get("WPS")
        if not (w and k) or w["最大行高"] <= 0:
            continue
        band = e["最大行高"][1] - e["最大行高"][0]
        gap = abs(k["最大行高"] - w["最大行高"])
        if gap > band:
            over += 1
            print("  !! %s：两引擎间距 %.1f 磅 > 推算区间宽度 %.1f 磅" % (r["名字"], gap, band))
    if not over:
        print("  每一件的两引擎间距都窄于推算区间宽度，即推算区间已经把渲染器差异包住。")
    bands = [(r["推算"]["最大行高"][1] - r["推算"]["最大行高"][0]) for r in rows if r["引擎"].get("Word")]
    gaps = [abs(r["引擎"]["WPS"]["最大行高"] - r["引擎"]["Word"]["最大行高"])
            for r in rows if r["引擎"].get("Word") and r["引擎"].get("WPS")]
    if bands and gaps:
        print("  推算区间宽度 中位 %.1f 磅 / 最大 %.1f 磅；两引擎间距 中位 %.1f 磅 / 最大 %.1f 磅"
              % (sorted(bands)[len(bands) // 2], max(bands), sorted(gaps)[len(gaps) // 2], max(gaps)))
    print("\n  对照 #55 量到的「推算 vs Word」：行高误差 不折行 ±2% / 重度折行 ±12%，页数 ±1 页。")


if __name__ == "__main__":
    sys.exit(main())
