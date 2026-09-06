"""skills/loo0ng-to-docx/scripts/gate.py 的脚本层单测（unittest）。要 Word COM：缺 Word 时这些测试 fail，不 skip（ADR-0015）。

运行：python -m unittest tests/loo0ng-to-docx/test_gate.py

缝是门禁 CLI：给一件 DOCX（正常件由转换器从 fixtures/ 出，故障件在正常件上做 XML 手术），断言 --json 的结论、不通过项
与披露项、退出码、--deliver 的落盘行为。每件门禁要起一次 Word（约 7 秒）。
"""
import pathlib
import re
import shutil
import tempfile
import unittest

import support
from support import FIXTURES, W, convert, gate, read_xml, rewrite, template, text_of


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def item_names(result, key="不通过项"):
    return [x.split("：", 1)[0] for x in result[key]]


class GateCase(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-gate-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def build(self, markdown, tpl, name="件.docx"):
        out = self.dir / name
        r = convert(markdown, tpl, out)
        self.assertEqual(r.code, 0, r)
        return out

    def assert_pass(self, docx, *extra):
        r = gate(docx, *extra)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.result["结论"], "通过")
        self.assertEqual(r.result["不通过项"], [])
        return r

    def assert_fail(self, docx, item, *extra):
        r = gate(docx, *extra)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.result["结论"], "不通过")
        self.assertIn(item, item_names(r.result), r.result)
        return r


class NormalAndFaultPairs(GateCase):
    """五种故障样例各一件必拦，正常件必过；收尾两条规则各一对。"""

    def test_normal_passes_with_disclosures(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        r = self.assert_pass(docx, "--template", template("1-2."))
        notes = r.result["披露项"]
        self.assertIn("空单元格：第 1 张表 第 2 行第 2 格", notes, "印模格本来就空，只披露")
        self.assertIn("页数：1", notes)
        self.assertTrue(any(n.startswith("请求字体不在嵌入字体里：方正小标宋简体") for n in notes), notes)
        self.assertEqual(r.result["页数"], 1)

    def test_long_marker_stretches_a_row(self):
        docx = self.build(fixture("撑列.md"), template("1-2."))
        r = self.assert_fail(docx, "行高超阈值")
        self.assertIn("磅", r.result["不通过项"][0])

    def test_blank_page(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))

        def pad(data):
            xml = data.decode("utf-8")
            return xml.replace("<w:sectPr", "<w:p/>" * 45 + "<w:sectPr", 1).encode("utf-8")

        bad = rewrite(good, self.dir / "空白页.docx", {"word/document.xml": pad})
        r = self.assert_fail(bad, "空白页")
        self.assertIn("第 2 页", r.result["不通过项"][0])

    def test_metadata_leftover(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))

        def leak(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<dc:creator/>|<dc:creator></dc:creator>", "<dc:creator>某人</dc:creator>", xml)
            xml = xml.replace("</cp:coreProperties>", "<cp:lastPrinted>2022-09-08T06:43:00Z</cp:lastPrinted></cp:coreProperties>")
            return xml.encode("utf-8")

        bad = rewrite(good, self.dir / "元数据.docx", {"docProps/core.xml": leak})
        r = self.assert_fail(bad, "元数据残留")
        self.assertIn("作者", r.result["不通过项"][0])
        self.assertIn("上次打印时间", r.result["不通过项"][0])

    def test_table_directly_before_sectpr(self):
        good = self.build("# 题\n\n| 印章名称 | 甲 |\n|---|---|\n", template("1-2."), "表尾.docx")
        self.assert_pass(good)

        def drop_trailing_paragraph(data):
            xml = data.decode("utf-8")
            return re.sub(r"<w:p>(?:(?!<w:p>).)*?</w:p>(?=<w:sectPr)", "", xml, count=1, flags=re.S).encode("utf-8")

        bad = rewrite(good, self.dir / "表接sectPr.docx", {"word/document.xml": drop_trailing_paragraph})
        blocks = support.body_blocks(bad)
        self.assertEqual(blocks[-1].tag, W + "tbl", "手术后最后一块须是表")
        self.assert_fail(bad, "表格直接接 sectPr")

    def test_table_wider_than_the_page(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))

        def widen(data):
            xml = data.decode("utf-8")
            return re.sub(r'<w:gridCol w:w="\d+"/>', '<w:gridCol w:w="6000"/>', xml).encode("utf-8")

        bad = rewrite(good, self.dir / "表宽.docx", {"word/document.xml": widen})
        self.assert_fail(bad, "表宽超页面")

    def test_placeholder_leftover(self):
        docx = self.build(fixture("占位残留.md"), template("1-2."))
        r = self.assert_fail(docx, "模板占位残留")
        line = r.result["不通过项"][0]
        self.assertIn("XX", line)
        self.assertIn("【印模待补】", line)

    def test_template_note_paragraph_leftover_needs_template(self):
        tpl = template("4-2.")
        note = text_of(read_xml(tpl).find(W + "body").find(W + "p")).strip()
        self.assertTrue(note.startswith("（注"), note)
        md = "# 关于提请法院裁定宣告乙公司破产并终结破产程序的报告\n\n" + note + "\n\n:left: 甲法院：\n\n正文一段。\n"
        docx = self.build(md, tpl)
        self.assert_fail(docx, "模板原文残留", "--template", tpl)
        r = gate(docx)
        self.assertEqual(r.code, 0, "不给模板就查不到说明段残留，只披露没比对")
        self.assertTrue(any("未给 --template" in n for n in r.result["披露项"]))

    def test_page_field_hardcoded_and_missing(self):
        tpl = template("3-1.")
        good = self.build(fixture("债权确认.md"), tpl, "债权.docx")
        self.assert_pass(good, "--template", tpl)

        def hardcode(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<w:instrText[^>]*>[^<]*</w:instrText>", "<w:instrText xml:space=\"preserve\"> DUMMY </w:instrText>", xml)
            return xml.encode("utf-8")

        bad = rewrite(good, self.dir / "写死.docx", {"word/footer1.xml": hardcode})
        self.assert_fail(bad, "页脚 PAGE 域写死")

        def remove_all_text(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<w:instrText[^>]*>[^<]*</w:instrText>", "", xml)
            xml = re.sub(r"<w:t(?: [^>]*)?>[^<]*</w:t>", "", xml)
            return xml.encode("utf-8")

        gone = rewrite(good, self.dir / "丢失.docx", {"word/footer1.xml": remove_all_text})
        self.assert_fail(gone, "页脚 PAGE 域丢失", "--template", tpl)
        r = gate(gone)
        self.assertEqual(r.code, 0, "没有模板可比时，页脚没字不算错")

    def test_page_count_threshold(self):
        md = "# 题\n\n" + "".join("第 %d 段，甲乙丙丁戊己庚辛壬癸，甲乙丙丁戊己庚辛壬癸。\n\n" % i for i in range(1, 60))
        docx = self.build(md, template("1-2."))
        r = gate(docx)
        self.assertEqual(r.code, 0, r)
        self.assertGreater(r.result["页数"], 1)
        self.assert_fail(docx, "页数超阈值", "--max-pages", "1")

    def test_row_height_threshold_is_adjustable(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        self.assert_fail(docx, "行高超阈值", "--max-row-height", "50")


class DeliverAndBackend(GateCase):
    def test_deliver_only_on_pass_and_never_overwrites(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))
        target = self.dir / "文书" / "印章备案" / "印章备案-v1.docx"
        r = gate(good, "--deliver", target)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.result["已落盘"], str(target))
        self.assertEqual(target.read_bytes(), good.read_bytes())
        r2 = gate(good, "--deliver", target)
        self.assertEqual(r2.code, 1, r2)
        self.assertEqual(r2.result["结论"], "通过")
        self.assertIn("不覆盖", r2.result["落盘被拒"])
        self.assertEqual(target.read_bytes(), good.read_bytes())

    def test_fail_means_nothing_is_delivered(self):
        bad = self.build(fixture("占位残留.md"), template("1-2."))
        target = self.dir / "文书" / "件-v1.docx"
        r = gate(bad, "--deliver", target)
        self.assertEqual(r.code, 1)
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists(), "不通过连目录都不建")

    def test_lawyer_written_docx_is_checked_the_same_way(self):
        r = gate(template("1-2."))
        self.assertEqual(r.code, 1, "官方模板原件带作者与占位符，照样报出")
        self.assertIn("元数据残留", support.strip_ws(r.out))
        self.assertTrue(r.result["披露项"], "披露项照给，供审查报告只披露不阻断")

    def test_no_backend_is_exit_2_not_a_downgrade(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        r = support.run(support.GATE, docx, "--powershell", self.dir / "没有这个.exe")
        self.assertEqual(r.code, 2, r)
        self.assertIn("无渲染后端", r.err)
        self.assertEqual(r.out, "", "没有后端时不输出任何静态检查结果")
        fake = self.dir / "fakeps.bat"
        fake.write_text("@echo NOWORD fake\r\n@exit /b 3\r\n", encoding="ascii")
        r = support.run(support.GATE, docx, "--powershell", fake)
        self.assertEqual(r.code, 2, r)
        self.assertIn("NOWORD", r.err)

    def test_broken_docx_is_exit_2(self):
        broken = self.dir / "坏.docx"
        broken.write_bytes(b"not a zip")
        r = support.run(support.GATE, broken)
        self.assertEqual(r.code, 2)
        r = support.run(support.GATE, self.dir / "没有.docx")
        self.assertEqual(r.code, 2)


if __name__ == "__main__":
    unittest.main()
