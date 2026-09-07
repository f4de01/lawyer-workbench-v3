#!/usr/bin/env python3
"""【一次性原型，勿入 main】纯标准库的 CJK 版面推算器：不渲染，只算。

回答 issue #55：能不能不靠 Word / LibreOffice，只读 DOCX 就算出门禁那三项渲染相关的判据
（页数、空白页、表格行高）。

原理：官方模板里页面几何、列宽、字号全是死数，而 CJK 全角字符的 advance 恰好等于字号
（w:sz 是半磅，故 advance = sz/2 磅）。于是「一格几行」是算术，不需要字体度量、不需要字体文件。

输出的是区间 [下界, 上界]，不是点值。区间由两组参数跑两遍得到：
  下界：西文按 0.5 em、行高系数 1.15、不计禁则
  上界：西文按 1.0 em、行高系数 1.35、每个折行段落多算一行（禁则兜底）

只依赖 zipfile + xml.etree（标准库）。写 python 3.9 兼容。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CJK = re.compile("[　-〿㐀-䶿一-鿿豈-﫿＀-￯]")
DEFAULT_PAGE_W, DEFAULT_PAGE_H, DEFAULT_MARGIN = 11906, 16838, 1440
DEFAULT_SZ = 21
DEFAULT_CELL_MAR = 108

# (西文相对字号的宽度, 单倍行距相对字号的倍数, 折行段落是否多算一行)
BOUNDS = {"lo": (0.5, 1.15, False), "hi": (1.0, 1.35, True)}


def tw2pt(v):
    return v / 20.0


def _sz_of(rpr, fallback):
    if rpr is None:
        return fallback
    el = rpr.find(W + "sz")
    if el is None:
        el = rpr.find(W + "szCs")
    if el is None:
        return fallback
    try:
        return int(el.get(W + "val"))
    except (TypeError, ValueError):
        return fallback


def _spacing_of(ppr):
    out = {}
    if ppr is None:
        return out
    sp = ppr.find(W + "spacing")
    if sp is not None:
        for k in ("before", "after", "line"):
            v = sp.get(W + k)
            if v is not None:
                try:
                    out[k] = int(v)
                except ValueError:
                    pass
        rule = sp.get(W + "lineRule")
        if rule:
            out["lineRule"] = rule
    return out


def _ind_of(ppr):
    out = {"left": 0, "right": 0, "firstLine": 0}
    if ppr is None:
        return out
    ind = ppr.find(W + "ind")
    if ind is None:
        return out
    pairs = (("left", ("left", "start")), ("right", ("right", "end")), ("firstLine", ("firstLine",)))
    for key, attrs in pairs:
        for a in attrs:
            v = ind.get(W + a)
            if v is not None:
                try:
                    out[key] = int(v)
                except ValueError:
                    pass
                break
    fc = ind.get(W + "firstLineChars")
    if fc is not None:
        try:
            out["firstLineChars"] = int(fc)
        except ValueError:
            pass
    return out


class Styles:
    """styles.xml 的 sz / spacing 解析，带 basedOn 链与默认段落样式。"""

    def __init__(self, root):
        self.by_id = {}
        self.default_p = None
        self.doc_sz = DEFAULT_SZ
        self.doc_spacing = {}
        if root is None:
            return
        dd = root.find(W + "docDefaults")
        if dd is not None:
            rpr = dd.find(W + "rPrDefault/" + W + "rPr")
            if rpr is not None:
                self.doc_sz = _sz_of(rpr, self.doc_sz)
            ppr = dd.find(W + "pPrDefault/" + W + "pPr")
            if ppr is not None:
                self.doc_spacing = _spacing_of(ppr)
        for st in root.findall(W + "style"):
            sid = st.get(W + "styleId")
            if sid is None:
                continue
            self.by_id[sid] = st
            if st.get(W + "type") == "paragraph" and st.get(W + "default") == "1":
                self.default_p = sid

    def _chain(self, sid):
        seen, out = set(), []
        while sid and sid in self.by_id and sid not in seen:
            seen.add(sid)
            st = self.by_id[sid]
            out.append(st)
            b = st.find(W + "basedOn")
            sid = b.get(W + "val") if b is not None else None
        return out

    def resolve(self, style_id):
        sz, sp = self.doc_sz, dict(self.doc_spacing)
        chain = self._chain(style_id) if style_id else []
        if self.default_p and style_id != self.default_p:
            chain = chain + self._chain(self.default_p)
        for st in reversed(chain):
            rpr = st.find(W + "rPr")
            if rpr is not None:
                sz = _sz_of(rpr, sz)
            ppr = st.find(W + "pPr")
            if ppr is not None:
                sp.update(_spacing_of(ppr))
        return sz, sp


def _para_text(p):
    return "".join((t.text or "") for t in p.iter(W + "t"))


def _has_page_break(p):
    for br in p.iter(W + "br"):
        if br.get(W + "type") == "page":
            return True
    return False


def _style_id(p):
    ppr = p.find(W + "pPr")
    if ppr is None:
        return None
    ps = ppr.find(W + "pStyle")
    return ps.get(W + "val") if ps is not None else None


def _run_sz(p, style_sz):
    ppr = p.find(W + "pPr")
    if ppr is not None:
        v = _sz_of(ppr.find(W + "rPr"), None)
        if v:
            return v
    for r in p.findall(W + "r"):
        v = _sz_of(r.find(W + "rPr"), None)
        if v:
            return v
    return style_sz


def text_width_tw(text, font_tw, latin_ratio):
    """一段文字的总宽（twips）。CJK 全角 = 字号；西文按 latin_ratio 折算。"""
    w = 0.0
    for ch in text:
        if ch == "\t":
            w += font_tw * 2
        elif CJK.match(ch):
            w += font_tw
        else:
            w += font_tw * latin_ratio
    return w


def para_height_pt(p, styles, avail_tw, params):
    """一个段落的 (高磅, 有没有字, 折不折行)。"""
    latin_ratio, line_factor, kinsoku = params
    style_sz, sp = styles.resolve(_style_id(p))
    sz = _run_sz(p, style_sz)
    font_pt = sz / 2.0
    font_tw = sz * 10.0  # 半磅 → twips：sz/2 磅 × 20
    ppr = p.find(W + "pPr")
    sp = dict(sp)
    sp.update(_spacing_of(ppr))
    ind = _ind_of(ppr)
    first_extra = ind.get("firstLine", 0)
    if "firstLineChars" in ind:
        first_extra = max(first_extra, ind["firstLineChars"] / 100.0 * font_tw)
    width = max(avail_tw - ind["left"] - ind["right"], font_tw)
    text = _para_text(p)
    if not text:
        lines, wrapped = 1, False
    else:
        total = text_width_tw(text, font_tw, latin_ratio)
        first_w = max(width - first_extra, font_tw)
        if total <= first_w:
            lines, wrapped = 1, False
        else:
            lines = 1 + int((total - first_w + width - 1e-9) // width)
            wrapped = True
            if kinsoku:
                lines += 1
    rule = sp.get("lineRule", "auto")
    if rule in ("exact", "atLeast"):
        lh = tw2pt(sp.get("line", int(font_pt * line_factor * 20)))
        if rule == "atLeast":
            lh = max(lh, font_pt * line_factor)
    else:
        lh = (sp.get("line", 240) / 240.0) * font_pt * line_factor
    h = lines * lh + tw2pt(sp.get("before", 0)) + tw2pt(sp.get("after", 0))
    return h, bool(text.strip()), wrapped


def _grid_widths(tbl):
    g = tbl.find(W + "tblGrid")
    out = []
    if g is None:
        return out
    for c in g.findall(W + "gridCol"):
        try:
            out.append(int(c.get(W + "w")))
        except (TypeError, ValueError):
            out.append(0)
    return out


def _cell_margins(tbl):
    left = right = DEFAULT_CELL_MAR
    top = bottom = 0
    pr = tbl.find(W + "tblPr")
    cm = pr.find(W + "tblCellMar") if pr is not None else None
    if cm is not None:
        pairs = (("left", "left"), ("start", "left"), ("right", "right"),
                 ("end", "right"), ("top", "top"), ("bottom", "bottom"))
        for tag, name in pairs:
            el = cm.find(W + tag)
            if el is None:
                continue
            try:
                v = int(el.get(W + "w"))
            except (TypeError, ValueError):
                continue
            if name == "left":
                left = v
            elif name == "right":
                right = v
            elif name == "top":
                top = v
            else:
                bottom = v
    return left, right, top, bottom


def _is_vmerge_continuation(tc):
    """纵向合并的续格：<w:vMerge/> 不带 val（带 val="restart" 的是起始格）。"""
    tcpr = tc.find(W + "tcPr")
    if tcpr is None:
        return False
    vm = tcpr.find(W + "vMerge")
    return vm is not None and vm.get(W + "val") is None


def table_rows_pt(tbl, styles, params):
    """回 [(行高磅, 该行有没有字)]，逐行。

    纵向合并的处理：续格所在的行与它上面那行之间没有横线，渲染出来是一条双高的带，
    PyMuPDF 的 find_tables 也就把它们读成一行。所以这里把被 vMerge 连起来的相邻行
    并成一条「带」，带高 = 成员行高之和 —— 与真渲量到的是同一个量。
    """
    grid = _grid_widths(tbl)
    ml, mr, mt, mb = _cell_margins(tbl)
    rows = []
    joins = []  # 第 i 行是否与第 i-1 行连成一带
    for tr in tbl.findall(W + "tr"):
        col = 0
        cell_h, has_text = [], False
        joins.append(any(_is_vmerge_continuation(tc) for tc in tr.findall(W + "tc")))
        for tc in tr.findall(W + "tc"):
            tcpr = tc.find(W + "tcPr")
            span = 1
            if tcpr is not None:
                gs = tcpr.find(W + "gridSpan")
                if gs is not None:
                    try:
                        span = int(gs.get(W + "val"))
                    except (TypeError, ValueError):
                        span = 1
            width = sum(grid[col:col + span]) if grid else 0
            col += span
            avail = max(width - ml - mr, 1)
            h = 0.0
            for p in tc.findall(W + "p"):
                ph, t, _ = para_height_pt(p, styles, avail, params)
                h += ph
                has_text = has_text or t
            cell_h.append(h)
        rh = (max(cell_h) if cell_h else 0.0) + tw2pt(mt + mb)
        trpr = tr.find(W + "trPr")
        if trpr is not None:
            th = trpr.find(W + "trHeight")
            if th is not None:
                try:
                    v = tw2pt(int(th.get(W + "val")))
                except (TypeError, ValueError):
                    v = None
                if v is not None:
                    rh = v if th.get(W + "hRule") == "exact" else max(rh, v)
        rows.append((rh, has_text))

    # 把被 vMerge 连起来的相邻行并成带
    bands = []
    for i, (rh, ht) in enumerate(rows):
        if i and joins[i] and bands:
            ph, pt_ = bands[-1]
            bands[-1] = (ph + rh, pt_ or ht)
        else:
            bands.append((rh, ht))
    return bands


def estimate(docx_path, params):
    with zipfile.ZipFile(docx_path) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        try:
            styles = Styles(ET.fromstring(z.read("word/styles.xml")))
        except KeyError:
            styles = Styles(None)
    body = doc.find(W + "body")
    sect = body.find(W + "sectPr")
    pw, ph = DEFAULT_PAGE_W, DEFAULT_PAGE_H
    mt = mb = ml = mr = DEFAULT_MARGIN
    if sect is not None:
        pg = sect.find(W + "pgSz")
        if pg is not None:
            pw = int(pg.get(W + "w", pw))
            ph = int(pg.get(W + "h", ph))
        mg = sect.find(W + "pgMar")
        if mg is not None:
            mt = int(mg.get(W + "top", mt))
            mb = int(mg.get(W + "bottom", mb))
            ml = int(mg.get(W + "left", ml))
            mr = int(mg.get(W + "right", mr))
    body_tw = pw - ml - mr
    page_h_pt = tw2pt(ph - mt - mb)
    pages = [{"used": 0.0, "text": False, "max_row": 0.0}]

    def newpage():
        pages.append({"used": 0.0, "text": False, "max_row": 0.0})

    def place(h, has_text, is_row):
        cur = pages[-1]
        if cur["used"] + h > page_h_pt + 1e-6 and cur["used"] > 0:
            newpage()
            cur = pages[-1]
        cur["used"] += h
        cur["text"] = cur["text"] or has_text
        if is_row:
            cur["max_row"] = max(cur["max_row"], h)

    for block in body:
        if block.tag == W + "p":
            if _has_page_break(block):
                newpage()
            h, has_text, _ = para_height_pt(block, styles, body_tw, params)
            place(h, has_text, False)
        elif block.tag == W + "tbl":
            for rh, has_text in table_rows_pt(block, styles, params):
                place(rh, has_text, True)

    return {
        "页数": len(pages),
        "空白页": [i for i, p in enumerate(pages, 1) if not p["text"]],
        "最大行高": round(max([p["max_row"] for p in pages] or [0.0]), 1),
        "版心高": round(page_h_pt, 1),
        "各页用量": [round(p["used"], 1) for p in pages],
    }


def band(docx_path):
    lo = estimate(docx_path, BOUNDS["lo"])
    hi = estimate(docx_path, BOUNDS["hi"])
    # 行高再放一点量测容差：PyMuPDF 的 row.bbox 含横线本身，且渲染有取整，实测稳定比推算高约 1 磅
    return {
        "页数": [lo["页数"], hi["页数"]],
        "最大行高": [round(lo["最大行高"] * 0.98, 1), round(hi["最大行高"] * 1.02 + 2.0, 1)],
        "空白页_lo": lo["空白页"],
        "空白页_hi": hi["空白页"],
        "版心高": lo["版心高"],
        "各页用量_lo": lo["各页用量"],
        "各页用量_hi": hi["各页用量"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="推算.py", description="【原型】纯标准库 CJK 版面推算，出区间不出点值")
    ap.add_argument("docx", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = {}
    for d in args.docx:
        out[d] = band(d)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for k, v in out.items():
            print("%s\n  页数 %s  最大行高 %s 磅  空白页 lo=%s hi=%s"
                  % (k, v["页数"], v["最大行高"], v["空白页_lo"], v["空白页_hi"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
