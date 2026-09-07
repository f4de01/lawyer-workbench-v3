#!/usr/bin/env python3
"""【一次性原型，勿入 main】把「推算.py」的区间与 Word 真渲的实测值逐件比对，量出误差带。

样本 = 19 件官方模板各一份甲乙丙占位件（正常件）+ 4 件 fixture + 3 件故障件（撑列 / 空白页 / 多页）。
每件要起一次 Word（约 7 秒），19+ 件约三四分钟。要 Word COM，缺了直接报错。

跑：python prototype/版面推算/对照.py [--json 结果.json] [--limit N]

真值取法与 gate.py 的 pdf_checks 完全一致（直接 import gate 用它的 render_pdf 与同样的
PyMuPDF 调用），保证比的是同一把尺子量出来的数。
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tests" / "loo0ng-to-docx"))
sys.path.insert(0, str(REPO / "skills" / "loo0ng-to-docx" / "scripts"))

import support  # noqa: E402
from support import FIXTURES, all_templates, convert, template  # noqa: E402
import gate  # noqa: E402
import pymupdf  # noqa: E402

sys.path.insert(0, str(HERE.parent))
import 推算  # noqa: E402


def truth(docx):
    """用 Word 真渲一遍，取 (页数, 空白页, 最大行高)。与 gate.pdf_checks 同口径。"""
    pdf, work = gate.render_pdf(docx, None)
    try:
        d = pymupdf.open(str(pdf))
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
        d.close()
        return {"页数": pages, "空白页": blank, "最大行高": round(max_row, 1), "各页最大行高": per_page}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def rewrite(src, dst, edits):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in edits:
                data = edits[item.filename](data)
            zout.writestr(item, data)
    return dst


def build_samples(work):
    """回 [(名字, docx 路径, 期望结论)]。期望结论只用来标注，不参与推算。"""
    out = []
    for tpl in all_templates():
        d = work / ("模板-" + tpl.stem[:6] + ".docx")
        r = convert(support.markdown_mirroring(tpl), tpl, d)
        if r.code != 0:
            print("跳过 %s：转换失败 %r" % (tpl.name, r), file=sys.stderr)
            continue
        out.append(("模板 " + tpl.stem[:6], d, "正常"))

    pairs = [("印章备案.md", "1-2."), ("占位残留.md", "1-2."), ("债权确认.md", "3-1."), ("撑列.md", "1-2.")]
    for name, prefix in pairs:
        tpl = template(prefix)
        d = work / ("fx-" + name.replace(".md", "") + ".docx")
        r = convert((FIXTURES / name).read_text(encoding="utf-8"), tpl, d)
        if r.code != 0:
            print("跳过 fixture %s：%r" % (name, r), file=sys.stderr)
            continue
        out.append(("fixture " + name[:-3], d, "撑列故障" if name == "撑列.md" else "正常几何"))

    good = work / "fx-印章备案.docx"
    if good.is_file():
        def pad(data):
            xml = data.decode("utf-8")
            return xml.replace("<w:sectPr", "<w:p/>" * 45 + "<w:sectPr", 1).encode("utf-8")
        bad = rewrite(good, work / "故障-空白页.docx", {"word/document.xml": pad})
        out.append(("故障 空白页", bad, "空白页故障"))

    md = "# 题\n\n" + "".join("第 %d 段，甲乙丙丁戊己庚辛壬癸，甲乙丙丁戊己庚辛壬癸。\n\n" % i for i in range(1, 60))
    d = work / "故障-多页.docx"
    if convert(md, template("1-2."), d).code == 0:
        out.append(("故障 多页", d, "页数样本"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="把逐件结果写进这个文件")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    work = pathlib.Path(tempfile.mkdtemp(prefix="版面推算-"))
    rows = []
    try:
        samples = build_samples(work)
        if args.limit:
            samples = samples[:args.limit]
        print("样本 %d 件，逐件起 Word……\n" % len(samples), file=sys.stderr)
        for i, (name, docx, kind) in enumerate(samples, 1):
            est = 推算.band(docx)
            try:
                tru = truth(docx)
            except gate.CannotRun as e:
                print("!! %s 渲染失败：%s" % (name, e), file=sys.stderr)
                continue
            rows.append({"名字": name, "类型": kind, "推算": est, "实测": tru})
            print("[%2d/%d] %s" % (i, len(samples), name), file=sys.stderr)
    finally:
        pass

    print("\n===== 逐件对照 =====")
    hdr = "%-16s %-10s | %-10s %-6s | %-14s %-8s %-7s | %s"
    print(hdr % ("件", "类型", "页数推算", "实测", "行高推算(磅)", "实测", "相对误差", "空白页 推算/实测"))
    print("-" * 125)
    page_ok = row_ok = blank_ok = 0
    row_errs = []
    for r in rows:
        e, t = r["推算"], r["实测"]
        p_in = e["页数"][0] <= t["页数"] <= e["页数"][1]
        page_ok += p_in
        rl, rh = e["最大行高"]
        rt = t["最大行高"]
        r_in = (rl - 0.05) <= rt <= (rh + 0.05)
        row_ok += r_in
        if rt > 0:
            mid = (rl + rh) / 2.0
            row_errs.append(((mid - rt) / rt, r["名字"], rl, rh, rt))
        b_in = e["空白页_lo"] == t["空白页"] or e["空白页_hi"] == t["空白页"]
        blank_ok += b_in
        print(hdr % (r["名字"][:16], r["类型"][:10],
                     "%d-%d" % (e["页数"][0], e["页数"][1]), "%d%s" % (t["页数"], "" if p_in else " X"),
                     "%.0f-%.0f" % (rl, rh), "%.0f%s" % (rt, "" if r_in else " X"),
                     ("%+.0f%%" % (((rl + rh) / 2.0 - rt) / rt * 100) if rt else "-"),
                     "%s / %s%s" % (e["空白页_hi"] or "无", t["空白页"] or "无", "" if b_in else " X")))

    n = len(rows) or 1
    print("\n===== 汇总 =====")
    print("样本 %d 件" % len(rows))
    print("页数    实测落在推算区间内：%d/%d" % (page_ok, len(rows)))
    print("最大行高 实测落在推算区间内：%d/%d" % (row_ok, len(rows)))
    print("空白页  推算与实测一致：    %d/%d" % (blank_ok, len(rows)))

    if row_errs:
        row_errs.sort()
        print("\n行高相对误差（区间中点 vs 实测）：最小 %+.1f%%（%s），最大 %+.1f%%（%s）"
              % (row_errs[0][0] * 100, row_errs[0][1], row_errs[-1][0] * 100, row_errs[-1][1]))

    print("\n===== 判定翻转检查（这才是红灯）=====")
    MAXP, MAXR = gate.DEFAULT_MAX_PAGES, gate.DEFAULT_MAX_ROW_HEIGHT
    print("阈值：页数 > %d 不通过；行高 > %.0f 磅不通过" % (MAXP, MAXR))
    flips = []
    for r in rows:
        e, t = r["推算"], r["实测"]
        for key, lo, hi, tv, thr in (("页数", e["页数"][0], e["页数"][1], t["页数"], MAXP),
                                     ("行高", e["最大行高"][0], e["最大行高"][1], t["最大行高"], MAXR)):
            est_v = "不通过" if lo > thr else ("通过" if hi <= thr else "带内")
            tru_v = "不通过" if tv > thr else "通过"
            if est_v != "带内" and est_v != tru_v:
                flips.append((r["名字"], key, est_v, tru_v, lo, hi, tv))
    if flips:
        for f in flips:
            print("  翻转！%s %s：推算判 %s（区间 %.1f-%.1f），实测 %s（%.1f）" % f)
    else:
        print("  无翻转：没有一件「推算给出确定结论、而实测结论相反」。")

    inband = []
    for r in rows:
        e, t = r["推算"], r["实测"]
        if e["页数"][0] <= MAXP < e["页数"][1]:
            inband.append((r["名字"], "页数"))
        if e["最大行高"][0] <= MAXR < e["最大行高"][1]:
            inband.append((r["名字"], "行高"))
    print("\n阈值落在推算区间内（即需要第三值「需人眼」的件）：%d 处 %s" % (len(inband), inband or ""))

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n逐件结果已写 %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
