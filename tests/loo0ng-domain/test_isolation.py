"""雏形 CLI 的依赖边界（#29 验收）：import 只含标准库，不 import 图引擎，写入只经引擎子进程。

运行：python -m unittest tests/loo0ng-domain/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "loo0ng-domain" / "scripts" / "sketch.py"


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


if __name__ == "__main__":
    unittest.main()
