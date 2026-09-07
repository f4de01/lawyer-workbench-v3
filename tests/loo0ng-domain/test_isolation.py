"""雏形 CLI 的依赖边界（#29 验收）：import 只含标准库，不 import 图引擎，写入只经引擎子进程。
外加回流的会话边界（#34 验收，ADR-0012）：律师会话里没有这个动作，路由与两个入口正文不提它。

运行：python -m unittest tests/loo0ng-domain/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "loo0ng-domain" / "scripts" / "sketch.py"
# 律师面对的三个入口：两个编排 skill 加路由（ADR-0005、ADR-0008）。ask-loo0ng 随它那票落地，
# 这里按名字找，还没有就不算；建起来之后这条断言自动开始管它。
入口 = ("loo0ng-setup-case", "loo0ng-doit", "ask-loo0ng")


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").partition(".")[0])
    return names


class IsolationTest(unittest.TestCase):
    def test_only_standard_library(self):
        mods = imported_modules(SCRIPT)
        self.assertTrue(mods, "sketch.py 竟然没有 import")
        for m in mods:
            self.assertIn(m, sys.stdlib_module_names, "sketch.py 引用了非标准库模块 %s" % m)

    def test_does_not_import_engine_or_siblings(self):
        mods = imported_modules(SCRIPT)
        for f in ("graph", "archive", "statement", "md2docx", "gate", "loo0ng"):
            self.assertNotIn(f, mods, "sketch.py import 了 %s" % f)

    def test_no_bom(self):
        self.assertFalse(SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf"))


class RefluxIsDeveloperOnlyTest(unittest.TestCase):
    """回流只在开发会话做（ADR-0012）：律师会话里没有这个动作，入口与路由的正文不该提它。"""

    def test_entry_skills_do_not_mention_reflux(self):
        found = [p for name in 入口
                 for p in (REPO / "skills" / name).rglob("*.md")
                 if "回流" in p.read_text(encoding="utf-8")]
        self.assertEqual([], found, "律师面对的入口正文里不该出现「回流」：%s" % [str(p) for p in found])

    def test_reflux_lives_in_the_domain_skill(self):
        step = (REPO / "skills" / "loo0ng-domain" / "references" / "回流.md").read_text(encoding="utf-8")
        self.assertIn("回流", step, "回流的步骤住在 loo0ng-domain 的 references 里")


if __name__ == "__main__":
    unittest.main()
