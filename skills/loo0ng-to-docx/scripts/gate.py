#!/usr/bin/env python3
"""版式门禁：对一件 DOCX 做只读检查，基于真实渲染（Word COM 经 powershell.exe 子进程出 PDF，PyMuPDF 检查）加静态检查。

依据 ADR-0006。只依赖 PyMuPDF 与 powershell.exe；不 import 转换器，可单独对任意 DOCX 跑。不改文书、不评判内容。
没有渲染后端（找不到 powershell.exe、Word COM 起不来、导出失败）时明确报错、退出码 2，不降级为只做静态检查。

不通过项（客观几何与结构，任一命中即不通过）：
  行高超阈值、页数超阈值（长标记撑列）；空白页（只有页码的页也算）；表宽超页面；页脚 PAGE 域写死（有 --template
  时还查丢失）；表格直接接 sectPr；docProps 残留作者 / 最后修改者 / 上次打印时间；正文残留模板占位标记（XX、【】等），
  有 --template 时还查模板里括号说明段整段残留。
披露项（写进审查报告，不判不通过）：空单元格坐标；请求字体不在嵌入字体里；页数；正文有字没渲出来（多半是固定行高裁掉了）。

fail-closed：转换器写在临时位置，本脚本 --deliver <目标> 在通过后才把它一次性拷进工作区；目标已存在则拒绝、不覆盖。

用法：
  python gate.py <文书.docx> [--template <模板.docx>] [--deliver <目标.docx>] [--json]
                 [--max-pages N] [--max-row-height 磅] [--powershell <exe>]

退出码：0 通过（有 --deliver 则已落盘）；1 不通过或落盘被拒；2 无渲染后端、文件打不开或用法错误。
"""
import argparse
import base64
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pymupdf

if hasattr(pymupdf, "no_recommend_layout"):
    pymupdf.no_recommend_layout()  # 否则 find_tables 往 stdout 印一行推荐语，污染 --json

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DEFAULT_PAGE_WIDTH = 11906  # A4，twips；sectPr 缺 pgSz/pgMar 时的兜底
DEFAULT_MARGIN = 1440
DEFAULT_MAX_PAGES = 30
DEFAULT_MAX_ROW_HEIGHT = 200.0  # 磅；1-2 模板的印模行 116 磅，实测事故 250～313 磅
FOOTER_ZONE = 72.0  # 磅；页脚坐在下页边距里，底边 1 英寸内的字当页脚
PAGE_NUMBER_ONLY = re.compile(r"^[\s\d\-–/第页共]*$")
PLACEHOLDER = re.compile(r"X{2,}|×{2,}|＿{2,}|_{3,}|【[^】\n]{0,40}】")
NOTE_PARAGRAPH = re.compile(r"^（.{6,}）$")
TEMP_DIRNAME = "loo0ng-to-docx-gate"
CJK = re.compile(r"[㐀-鿿豈-﫿]")
# 中文字体名与 PDF 里 BaseFont 名的对应，只为披露项做归一，不求全
FONT_ALIASES = {
    "仿宋": "fangsong", "仿宋_gb2312": "fangsonggb2312", "宋体": "simsun", "黑体": "simhei", "楷体": "kaiti",
    "楷体_gb2312": "kaitigb2312", "微软雅黑": "microsoftyahei", "方正小标宋简体": "fzxiaobiaosong",
    "方正小标宋_gbk": "fzxiaobiaosong", "华文仿宋": "stfangsong", "华文中宋": "stzhongsong",
}
FONT_FALLBACK_NAMES = ("microsoftyahei",)  # Word 用它替代缺失的方正字体，披露时点名

# 打开后先 ComputeStatistics(2)（页数）逼 Word 完成分页再导出：不这样做，带页脚 PAGE 域的多页文书导出后 Word 会
# 崩掉（RPC_E_DISCONNECTED），本机对 3-1、4-2 两件模板稳定复现（#28）。
PS_RENDER = r"""
$ErrorActionPreference = 'Stop'
try { $w = New-Object -ComObject Word.Application } catch { Write-Output ('NOWORD ' + $_.Exception.Message); exit 3 }
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open('{IN}', $false, $true, $false)
  $null = $d.ComputeStatistics(2)
  $d.ExportAsFixedFormat('{OUT}', 17)
  $d.Close(0)
  Write-Output 'OK'
} catch { Write-Output ('EXPORTFAIL ' + $_.Exception.Message); exit 4 }
finally { $w.Quit() }
"""


class CannotRun(Exception):
    """门禁无法运行（无渲染后端、文书或模板不存在或打不开）：退出码 2，不是不通过，也不降级。"""


class Refused(Exception):
    """落盘被拒（目标已存在等）：退出码 1。"""


# ---------------------------------------------------------------- 静态检查（zip + XML）

def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(W + "t"))


class Docx:
    """只读打开一件 DOCX，取正文、页脚、元数据与页面尺寸。"""

    def __init__(self, path: pathlib.Path):
        self.path = path
        try:
            self.zip = zipfile.ZipFile(str(path))
            self.document = ET.fromstring(self.zip.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
            raise CannotRun("不是能打开的 DOCX：%s（%s）" % (path, e))
        self.body = self.document.find(W + "body")
        if self.body is None:
            raise CannotRun("DOCX 没有 body：%s" % path)
        self.sect_pr = self.body.find(W + "sectPr")

    def blocks(self) -> List[ET.Element]:
        return [c for c in self.body if c.tag in (W + "p", W + "tbl")]

    def paragraph_texts(self) -> List[str]:
        return [_text(p) for p in self.body.findall(W + "p")]

    def tables(self) -> List[ET.Element]:
        return self.body.findall(W + "tbl")

    def body_text(self) -> str:
        return "\n".join(_text(b) for b in self.blocks())

    def text_chunks(self) -> List[str]:
        """正文的每个段落与每个单元格的文字（去空白），供与 PDF 渲出的字比对。"""
        chunks = []
        for p in self.body.iter(W + "p"):
            t = re.sub(r"\s+", "", _text(p))
            if t:
                chunks.append(t)
        return chunks

    def page_metrics(self) -> Tuple[int, int, int]:
        pg = self.sect_pr.find(W + "pgSz") if self.sect_pr is not None else None
        mar = self.sect_pr.find(W + "pgMar") if self.sect_pr is not None else None
        width = int(pg.get(W + "w")) if pg is not None and pg.get(W + "w") else DEFAULT_PAGE_WIDTH
        left = int(mar.get(W + "left")) if mar is not None and mar.get(W + "left") else DEFAULT_MARGIN
        right = int(mar.get(W + "right")) if mar is not None and mar.get(W + "right") else DEFAULT_MARGIN
        return width, left, right

    def core(self) -> Dict[str, Optional[str]]:
        try:
            core = ET.fromstring(self.zip.read("docProps/core.xml"))
        except (KeyError, ET.ParseError):
            return {}
        out = {}
        for key, tag in (("作者", DC + "creator"), ("最后修改者", CP + "lastModifiedBy"), ("上次打印时间", CP + "lastPrinted")):
            el = core.find(tag)
            out[key] = None if el is None else (el.text or "")
        return out

    def footers(self) -> List[str]:
        """sectPr 引用的页脚部件的 XML 原文。"""
        if self.sect_pr is None:
            return []
        try:
            rels = ET.fromstring(self.zip.read("word/_rels/document.xml.rels"))
        except (KeyError, ET.ParseError):
            return []
        targets = {rel.get("Id"): rel.get("Target") for rel in rels.findall(REL + "Relationship")}
        out = []
        for ref in self.sect_pr.findall(W + "footerReference"):
            target = targets.get(ref.get(R + "id"))
            if not target:
                continue
            name = "word/" + target if not target.startswith("/") else target[1:]
            try:
                out.append(self.zip.read(name).decode("utf-8", "replace"))
            except KeyError:
                continue
        return out

    def requested_fonts(self) -> List[str]:
        """有字的 run 请求的字体：含中文的看 eastAsia，否则看 ascii。"""
        fonts = set()
        for r in self.body.iter(W + "r"):
            text = _text(r)
            if not text.strip():
                continue
            rpr = r.find(W + "rPr")
            rf = rpr.find(W + "rFonts") if rpr is not None else None
            if rf is None:
                continue
            attr = "eastAsia" if CJK.search(text) else "ascii"
            name = rf.get(W + attr) or rf.get(W + "eastAsia") or rf.get(W + "ascii")
            if name:
                fonts.add(name)
        return sorted(fonts)


def _footer_has_page_field(xml: str) -> bool:
    return bool(re.search(r"<w:instrText[^>]*>[^<]*\bPAGE\b", xml)) or bool(re.search(r'w:instr="[^"]*\bPAGE\b', xml))


def _footer_visible_text(xml: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def static_checks(doc: Docx, template: Optional[Docx]) -> Tuple[List[str], List[str]]:
    fails: List[str] = []
    notes: List[str] = []

    core = doc.core()
    leftovers = [k for k, v in core.items() if v is not None and (k == "上次打印时间" or v.strip())]
    if leftovers:
        fails.append("元数据残留：%s" % "、".join(leftovers))

    blocks = doc.blocks()
    if blocks and blocks[-1].tag == W + "tbl":
        fails.append("表格直接接 sectPr：正文最后一个块是表格，之后没有空段")

    width, left, right = doc.page_metrics()
    for i, tbl in enumerate(doc.tables(), 1):
        tblpr = tbl.find(W + "tblPr")
        ind = tblpr.find(W + "tblInd") if tblpr is not None else None
        ind_w = int(ind.get(W + "w")) if ind is not None and ind.get(W + "w") and (ind.get(W + "type") or "dxa") == "dxa" else 0
        grid = tbl.find(W + "tblGrid")
        cols = [int(g.get(W + "w")) for g in grid.findall(W + "gridCol")] if grid is not None else []
        table_w = sum(c for c in cols if c)
        tblw = tblpr.find(W + "tblW") if tblpr is not None else None
        if tblw is not None and (tblw.get(W + "type") or "") == "dxa" and tblw.get(W + "w"):
            table_w = max(table_w, int(tblw.get(W + "w")))
        if left + ind_w + table_w > width:
            fails.append("表宽超页面：第 %d 张表右边到 %d twips，纸边在 %d" % (i, left + ind_w + table_w, width))

    for i, tbl in enumerate(doc.tables(), 1):
        empties = []
        for r, tr in enumerate(tbl.findall(W + "tr"), 1):
            for c, tc in enumerate(tr.findall(W + "tc"), 1):
                tcpr = tc.find(W + "tcPr")
                vm = tcpr.find(W + "vMerge") if tcpr is not None else None
                if vm is not None and vm.get(W + "val") is None:
                    continue  # 纵向合并的续格本来就没字
                if not _text(tc).strip():
                    empties.append("第 %d 行第 %d 格" % (r, c))
        if empties:
            notes.append("空单元格：第 %d 张表 %s" % (i, "、".join(empties)))

    body_text = doc.body_text()
    hits = sorted(set(m.group(0) for m in PLACEHOLDER.finditer(body_text)))
    if hits:
        fails.append("模板占位残留：%s" % "、".join(h[:20] for h in hits[:8]))
    if template is not None:
        compact = re.sub(r"\s+", "", body_text)
        leftover_notes = []
        for t in template.paragraph_texts():
            t = t.strip()
            if NOTE_PARAGRAPH.match(t) and re.sub(r"\s+", "", t) in compact:
                leftover_notes.append(t[:20])
        if leftover_notes:
            fails.append("模板原文残留：%s" % "、".join(leftover_notes))

    footers = doc.footers()
    has_field = any(_footer_has_page_field(f) for f in footers)
    if not has_field:
        digits = [f for f in footers if re.search(r"\d", _footer_visible_text(f))]
        if digits:
            fails.append("页脚 PAGE 域写死：页脚里有数字却没有 PAGE 域")
        elif template is not None and any(_footer_has_page_field(f) for f in template.footers()):
            fails.append("页脚 PAGE 域丢失：模板页脚有 PAGE 域，成品没有")
    return fails, notes


# ---------------------------------------------------------------- 真实渲染

def render_pdf(docx_path: pathlib.Path, powershell: Optional[str]) -> Tuple[pathlib.Path, pathlib.Path]:
    """Word COM 经 powershell.exe 子进程导出 PDF；返回 (pdf 路径, 临时目录)。任何一步不成都是 CannotRun。"""
    exe = shutil.which(powershell or "powershell.exe")
    if not exe:
        raise CannotRun("无渲染后端：找不到 %s，门禁不降级" % (powershell or "powershell.exe"))
    base = pathlib.Path(tempfile.gettempdir()) / TEMP_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    while True:
        work = base / secrets.token_hex(4)
        try:
            os.mkdir(work)  # 不用 mkdtemp：它建的目录 ACL 只有三条，别的账户写不了
            break
        except FileExistsError:
            continue
    pdf = work / (docx_path.stem + ".pdf")
    script = PS_RENDER.replace("{IN}", str(docx_path.resolve()).replace("'", "''")).replace("{OUT}", str(pdf).replace("'", "''"))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    first = ""
    for attempt in range(2):  # Word 偶发瞬时失败（导出报错、实例被别的会话关掉），整个再起一次
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        except subprocess.TimeoutExpired:
            raise CannotRun("无渲染后端：Word 导出超过 120 秒没有回来")
        out = (r.stdout or "").strip()
        if r.returncode == 0 and pdf.is_file():
            return pdf, work
        first = out.splitlines()[0] if out else ((r.stderr or "").strip().splitlines() or ["退出码 %d" % r.returncode])[0]
        if first.startswith("NOWORD"):
            break  # 起不来 Word 不是瞬时故障
    shutil.rmtree(work, ignore_errors=True)
    raise CannotRun("无渲染后端：Word COM 没能出 PDF（%s）" % first)


def _page_body_text(page) -> str:
    """页面正文的字：底边一英寸内、只像页码的字块当页脚去掉（正文最后一行可能贴着页脚，不能只按位置切）。"""
    height = page.rect.height
    parts = []
    for block in page.get_text("blocks", sort=True):
        y0, text = block[1], block[4]
        if y0 >= height - FOOTER_ZONE and PAGE_NUMBER_ONLY.match(text.strip() or ""):
            continue
        parts.append(text)
    return "".join(parts)


def pdf_checks(pdf: pathlib.Path, doc: Docx, max_pages: int, max_row_height: float) -> Tuple[List[str], List[str], int]:
    fails: List[str] = []
    notes: List[str] = []
    try:
        pdfdoc = pymupdf.open(str(pdf))
    except Exception as e:
        raise CannotRun("无渲染后端：PDF 打不开（%s）" % e)
    pages = len(pdfdoc)
    notes.append("页数：%d" % pages)
    if pages > max_pages:
        fails.append("页数超阈值：%d 页，阈值 %d" % (pages, max_pages))
    blank = []
    tall = []
    fonts = set()
    rendered = []
    for i, page in enumerate(pdfdoc, 1):
        body = _page_body_text(page)
        rendered.append(re.sub(r"\s+", "", body))
        if not body.strip() and not page.get_images():
            blank.append(i)
        for f in page.get_fonts():
            fonts.add(f[3].split("+")[-1])
        for t in page.find_tables().tables:
            for row in t.rows:
                h = row.bbox[3] - row.bbox[1]
                if h > max_row_height:
                    tall.append("第 %d 页 %.0f 磅" % (i, h))
    if blank:
        fails.append("空白页：第 %s 页" % "、".join(str(b) for b in blank))
    if tall:
        fails.append("行高超阈值：%s（阈值 %.0f 磅）" % ("、".join(tall), max_row_height))
    embedded = sorted(fonts)
    requested = doc.requested_fonts()
    missing = [f for f in requested if not _font_embedded(f, embedded)]
    if missing:
        notes.append("请求字体不在嵌入字体里：%s（嵌入：%s）" % ("、".join(missing), "、".join(embedded) or "无"))
    # PDF 里的字块顺序与段落不一一对应（表格里并排的格会交错），所以只比字的多重集：
    # 一个段落或单元格的字在渲出的字里凑不齐，就是有字没渲出来。
    pool = Counter("".join(rendered))
    lost = []
    for chunk in doc.text_chunks():
        need = Counter(chunk)
        if all(pool[ch] >= n for ch, n in need.items()):
            pool.subtract(need)
        else:
            lost.append(chunk)
    if lost:
        notes.append("有字没渲出来（多半是固定行高裁掉了）：%s" % "、".join(c[:12] for c in lost[:6]))
    return fails, notes, pages


def _norm_font(name: str) -> str:
    key = re.sub(r"[\s\-_]", "", name).lower()
    key2 = re.sub(r"[\s\-]", "", name).lower()
    return FONT_ALIASES.get(key2, FONT_ALIASES.get(key, key))


def _font_embedded(requested: str, embedded: List[str]) -> bool:
    want = _norm_font(requested)
    for e in embedded:
        have = re.sub(r"[\s\-_,]", "", e).lower()
        if have.startswith(want) or want.startswith(have):
            return True
    return False


# ---------------------------------------------------------------- 门禁与落盘

def run_gate(docx_path: pathlib.Path, template_path: Optional[pathlib.Path], max_pages: int, max_row_height: float,
             powershell: Optional[str]) -> Dict[str, object]:
    doc = Docx(docx_path)
    template = Docx(template_path) if template_path else None
    fails, notes = static_checks(doc, template)
    pdf, work = render_pdf(docx_path, powershell)
    try:
        f2, n2, pages = pdf_checks(pdf, doc, max_pages, max_row_height)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    fails += f2
    notes += n2
    if template is None:
        notes.append("未给 --template：没查页脚 PAGE 域丢失与模板说明段残留")
    return {"文件": str(docx_path), "结论": "通过" if not fails else "不通过", "不通过项": fails, "披露项": notes, "页数": pages}


def deliver(src: pathlib.Path, target: pathlib.Path) -> None:
    if target.exists():
        raise Refused("目标已存在，不覆盖：%s（成品仍在 %s）" % (target, src))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(target))


def format_report(result: Dict[str, object]) -> str:
    lines = ["版式门禁：%s" % result["结论"]]
    lines.append("不通过项：" + ("无" if not result["不通过项"] else ""))
    for f in result["不通过项"]:
        lines.append("- " + f)
    lines.append("披露项：")
    for n in result["披露项"]:
        lines.append("- " + n)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="gate.py", description="版式门禁：真实渲染加静态检查，只读，不过不落盘。")
    ap.add_argument("docx", help="要检查的文书（.docx）")
    ap.add_argument("--template", help="该节点的官方模板，给了才查页脚 PAGE 域丢失与模板说明段残留")
    ap.add_argument("--deliver", help="通过后把文书一次性拷到这个路径（已存在则拒绝）")
    ap.add_argument("--json", action="store_true", help="结果按 JSON 打印")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="页数阈值，默认 %(default)s")
    ap.add_argument("--max-row-height", type=float, default=DEFAULT_MAX_ROW_HEIGHT, help="表格行高阈值（磅），默认 %(default)s")
    ap.add_argument("--powershell", help="powershell.exe 的路径，默认从 PATH 找")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    docx_path = pathlib.Path(args.docx)
    template = pathlib.Path(args.template) if args.template else None
    try:
        if not docx_path.is_file():
            raise CannotRun("文书不存在：%s" % docx_path)
        if template is not None and not template.is_file():
            raise CannotRun("模板不存在：%s" % template)
        result = run_gate(docx_path, template, args.max_pages, args.max_row_height, args.powershell)
    except CannotRun as e:
        sys.stderr.write("门禁无法运行：%s\n" % e)
        return 2
    delivered = None
    refused = None
    if result["结论"] == "通过" and args.deliver:
        try:
            deliver(docx_path, pathlib.Path(args.deliver))
            delivered = str(pathlib.Path(args.deliver))
        except Refused as e:
            refused = str(e)
    if args.json:
        result = dict(result, 已落盘=delivered, 落盘被拒=refused)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
        if delivered:
            print("已落盘 %s" % delivered)
        if refused:
            print("落盘被拒：%s" % refused)
        if result["结论"] != "通过" and args.deliver:
            print("未落盘：门禁不通过")
    if result["结论"] != "通过" or refused:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
