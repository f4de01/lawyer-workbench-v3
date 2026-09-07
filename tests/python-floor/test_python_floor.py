"""随包分发的七件脚本跑得动 python 3.9（#61 验收）：律师那台 mac 的 /usr/bin/python3 是 3.9.6。

两条断言分管两类越界：3.10 才有的**语法**由 ast 的 feature_version 拦；3.10 才有的 **API**
（形状上看得出来的那几个）按名字拦。开发侧脚本与 tests/ 不受这条约束（ADR-0015：它们只在
开发机上跑），所以只扫 skills/*/scripts/*.py。

运行：python -m unittest tests/python-floor/test_python_floor.py
"""
import ast
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SHIPPED = sorted((REPO / "skills").glob("*/scripts/*.py"))

# 3.10 起才有的 API，按调用形状认得出的两类：
# - Path.write_text / Path.read_text 的 newline= 关键字（3.10 加，#61 就栽在这里）
# - sys.stdlib_module_names（3.10 加）
NEWLINE_KWARG_ON = ("write_text", "read_text")
BANNED_ATTRIBUTES = ("stdlib_module_names",)


def parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class PythonFloorTest(unittest.TestCase):
    def test_finds_the_shipped_scripts(self):
        self.assertTrue(SHIPPED, "skills/*/scripts/*.py 一个都没扫到，这条断言就白站着")

    def test_syntax_is_3_9(self):
        for path in SHIPPED:
            with self.subTest(script=path.name):
                try:
                    ast.parse(path.read_text(encoding="utf-8"),
                              filename=str(path), feature_version=(3, 9))
                except SyntaxError as e:
                    self.fail("%s 用了 3.9 读不懂的语法：%s" % (path.name, e))

    def test_no_3_10_only_api(self):
        for path in SHIPPED:
            with self.subTest(script=path.name):
                for node in ast.walk(parse(path)):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                            and node.func.attr in NEWLINE_KWARG_ON:
                        self.assertNotIn(
                            "newline", [kw.arg for kw in node.keywords],
                            "%s:%d %s(newline=) 是 3.10 才有的，改成显式 open(..., newline=) 写"
                            % (path.name, node.lineno, node.func.attr))
                    if isinstance(node, ast.Attribute) and node.attr in BANNED_ATTRIBUTES:
                        self.fail("%s:%d 用了 3.10 才有的 %s" % (path.name, node.lineno, node.attr))


if __name__ == "__main__":
    unittest.main()
