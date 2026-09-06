"""19 件官方模板回归：每件各出一份甲乙丙占位件，全部通过门禁；4 件含合并单元格的模板与模板同形。

运行：python -m unittest tests/loo0ng-to-docx/test_templates.py

只在开发侧跑（ADR-0006）：每件要起一次 Word，19 件约两三分钟；Codex 的 30 秒 shell 超时装不下。要 Word，缺了 fail 不 skip。
"""
import pathlib
import shutil
import tempfile
import unittest

import support
from support import W, all_templates, body_blocks, convert, gate, read_xml, table_signature, template

MERGED = ("1-1.", "3-1.", "3-2.", "8-2.")


class TemplatesRegression(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-tpl-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_there_are_nineteen_templates(self):
        self.assertEqual(len(all_templates()), 19)

    def test_every_template_yields_a_placeholder_docx_that_passes_the_gate(self):
        failures = []
        for tpl in all_templates():
            out = self.dir / (tpl.stem[:6] + ".docx")
            r = convert(support.markdown_mirroring(tpl), tpl, out)
            if r.code != 0:
                failures.append("%s：转换 %r" % (tpl.name, r))
                continue
            g = gate(out, "--template", tpl)
            if g.code != 0:
                failures.append("%s：门禁退出码 %d %s %s" % (tpl.name, g.code, g.result and g.result["不通过项"], g.err.strip()))
        self.assertEqual(failures, [], "\n".join(failures))

    def test_merged_cell_templates_keep_their_shape(self):
        for prefix in MERGED:
            tpl = template(prefix)
            out = self.dir / (prefix + "docx")
            r = convert(support.markdown_mirroring(tpl), tpl, out)
            self.assertEqual(r.code, 0, r)
            tpl_tables = read_xml(tpl).find(W + "body").findall(W + "tbl")
            out_tables = [b for b in body_blocks(out) if b.tag == W + "tbl"]
            merged = any(cell[0] != "1" or cell[1] is not None
                         for t in tpl_tables for _, cells in table_signature(t)[1] for cell in cells)
            self.assertTrue(merged, "%s 应含合并单元格" % prefix)
            self.assertEqual([table_signature(t) for t in out_tables], [table_signature(t) for t in tpl_tables], prefix)


if __name__ == "__main__":
    unittest.main()
