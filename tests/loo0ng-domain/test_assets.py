"""领域目录三样（AGENTS.md 结构不变量 5，ADR-0004）：assets 下只有领域图、官方模板原件、指引手册原文。

运行：python -m unittest tests/loo0ng-domain/test_assets.py

领域图「破产」本票只是空壳（合法但无模块）；19 件官方模板与 2 份指引手册按隐私检查器拆 zip 扫描通过；
既有案件的 .doc 不进（硬边界 1）。
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
ASSETS = REPO / "skills" / "loo0ng-domain" / "assets"
DOMAIN = ASSETS / "破产"
ENGINE = REPO / "skills" / "loo0ng-graph" / "scripts" / "graph.py"
PRIVACY = REPO / "scripts" / "privacy-check.py"

spec = importlib.util.spec_from_file_location("privacy_check", PRIVACY)
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class AssetsTest(unittest.TestCase):
    def test_exactly_three_kinds_and_nothing_else(self):
        self.assertEqual(sorted(p.name for p in ASSETS.iterdir()), ["破产"], "一个领域一个目录")
        self.assertEqual(sorted(p.name for p in DOMAIN.iterdir()), ["指引手册", "模板", "领域图.json"])
        for sub in ("模板", "指引手册"):
            for p in (DOMAIN / sub).iterdir():
                self.assertTrue(p.is_file() and p.suffix == ".docx", "%s 下只放 docx 原件：%s" % (sub, p.name))

    def test_nineteen_templates_and_two_handbooks(self):
        self.assertEqual(len(list((DOMAIN / "模板").glob("*.docx"))), 19)
        self.assertEqual(len(list((DOMAIN / "指引手册").glob("*.docx"))), 2)

    def test_no_legacy_doc_files(self):
        self.assertEqual(list(ASSETS.rglob("*.doc")), [], "既有案件的 .doc 不进领域目录")

    def test_domain_graph_is_a_valid_empty_domain_graph(self):
        data = json.loads((DOMAIN / "领域图.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"格式版本": 1, "领域": "破产", "模块": []})
        r = subprocess.run([sys.executable, str(ENGINE), "--graph", str(DOMAIN / "领域图.json"), "--kind", "domain", "validate"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_originals_pass_the_privacy_scan(self):
        for p in sorted(DOMAIN.rglob("*.docx")):
            rel = p.relative_to(REPO).as_posix()
            self.assertEqual(privacy.find_hits_in_line(rel), [], "文件名命中：%s" % rel)
            hits, disclosed = privacy.scan_blob(rel, p.read_bytes())
            self.assertFalse(disclosed, "%s 不是能拆的 Office 文件" % rel)
            self.assertEqual(hits, [], "%s 命中：%s" % (rel, [(h.line, h.category, h.where) for h in hits]))


if __name__ == "__main__":
    unittest.main()
