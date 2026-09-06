"""scripts/gen-openai-yaml.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/gen-openai-yaml -p 'test_*.py'
缝是 CLI 加 skills/<name>/agents/openai.yaml 文件：在临时 skills 根里放 SKILL.md，跑 main()，读产物。
"""
import contextlib
import importlib.util
import io
import pathlib
import shutil
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "gen-openai-yaml.py"

spec = importlib.util.spec_from_file_location("gen_openai_yaml", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

REFERENCE_SKILL = '''---
name: loo0ng-demo
description: "参考 skill 的四要素描述，含 #号 与 \\"引号\\"。"
metadata:
  display-name: "loo0ng-demo"
  short-description: "改构成、追加条目"
---

# 正文
'''

ROUTER_SKILL = '''---
name: ask-demo
description: "路由：一句人话。"
disable-model-invocation: true
metadata:
  display-name: "ask-demo"
  short-description: "找到该打哪个入口"
---
'''


class GenTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="gen-openai-yaml-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def put(self, name, text):
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
        return d

    def run_cli(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen.main(["--skills", str(self.root), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_reference_skill_gets_interface_only(self):
        d = self.put("loo0ng-demo", REFERENCE_SKILL)
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0, out)
        text = (d / "agents" / "openai.yaml").read_bytes()
        self.assertEqual(text.decode("utf-8"),
                         'interface:\n  display_name: "loo0ng-demo"\n  short_description: "改构成、追加条目"\n')
        self.assertFalse(text.startswith(b"\xef\xbb\xbf"), "不带 BOM")
        self.assertNotIn(b"\r\n", text, "LF")

    def test_user_invoked_skill_gets_policy_flag(self):
        d = self.put("ask-demo", ROUTER_SKILL)
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual((d / "agents" / "openai.yaml").read_text(encoding="utf-8"),
                         'interface:\n  display_name: "ask-demo"\n  short_description: "找到该打哪个入口"\n'
                         'policy:\n  allow_implicit_invocation: false\n')

    def test_check_reports_stale_and_writes_nothing(self):
        d = self.put("loo0ng-demo", REFERENCE_SKILL)
        code, out, _ = self.run_cli("--check")
        self.assertEqual(code, 1)
        self.assertIn("不同步", out)
        self.assertFalse((d / "agents" / "openai.yaml").exists())
        self.run_cli()
        code, out, _ = self.run_cli("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("已同步", out)

    def test_display_name_must_equal_directory_name(self):
        self.put("loo0ng-demo", REFERENCE_SKILL.replace('display-name: "loo0ng-demo"', 'display-name: "示例引擎"'))
        code, out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("display-name", err)
        self.assertIn("目录名", err)

    def test_missing_display_name_is_an_error(self):
        self.put("loo0ng-bad", REFERENCE_SKILL.replace('  display-name: "loo0ng-demo"\n', ""))
        code, _, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("display-name", err)

    def test_repo_skills_are_in_sync(self):
        """仓库里每件 skill 的 openai.yaml 都与其 SKILL.md 同步（登记不变量）。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen.main(["--skills", str(REPO / "skills"), "--check"])
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
