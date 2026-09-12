"""scripts/release.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/release -p 'test_*.py'

发布路径上的两道闸门（preflight / postflight）在这里各拆成一条一条的红：
CI 上跑挂就停，靠的是它们的退出码，所以每一条「该停」都要有断言看着。
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "release.py"
LF = chr(10)

默认CHANGELOG = LF.join([
    "# loo0ng-skills",
    "",
    "## 0.2.0",
    "",
    "### Minor Changes",
    "",
    "- 新东西（#96）",
    "",
    "## 0.1.0",
    "",
    "### Minor Changes",
    "",
    "- 老东西（#26）",
    "",
])


def 跑(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, encoding="utf-8")


def git(根, *args):
    return subprocess.run(["git", "-C", str(根), *args], capture_output=True, text=True, encoding="utf-8")


def 写stub(p, 退出码):
    p.write_text("import sys" + LF + "sys.exit(" + str(退出码) + ")" + LF, encoding="utf-8")


def 假仓库(根, *, 版本="0.1.0", changesets=("aaa.md",), gen=0, sync=0, changelog=None, tags=()):
    (根 / "scripts").mkdir(parents=True)
    (根 / "package.json").write_text(
        json.dumps({"name": "loo0ng-skills", "version": 版本}, indent=2) + LF, encoding="utf-8")
    写stub(根 / "scripts" / "gen-openai-yaml.py", gen)
    写stub(根 / "scripts" / "sync-plugin-version.py", sync)
    cs = 根 / ".changeset"
    cs.mkdir()
    (cs / "README.md").write_text("手艺写在这里" + LF, encoding="utf-8")
    (cs / "config.json").write_text("{}" + LF, encoding="utf-8")
    for n in changesets:
        (cs / n).write_text("---" + LF + "'x': patch" + LF + "---" + LF + "一句话（#96）" + LF, encoding="utf-8")
    (根 / "CHANGELOG.md").write_text(默认CHANGELOG if changelog is None else changelog, encoding="utf-8")
    git(根, "init", "-q")
    git(根, "add", "-A")
    git(根, "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "--no-verify", "-m", "x")
    for t in tags:
        git(根, "tag", t)
    return 根


class 结算前(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.根 = pathlib.Path(self.tmp.name) / "repo"

    def preflight(self, **kw):
        假仓库(self.根, **kw)
        return 跑("preflight", "--root", str(self.根))

    def test_全绿(self):
        r = self.preflight()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_openai_yaml_不同步即停(self):
        r = self.preflight(gen=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn("gen-openai-yaml", r.stderr)

    def test_版本三处不齐即停(self):
        r = self.preflight(sync=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn("sync-plugin-version", r.stderr)

    def test_没有待结算的changeset即停(self):
        r = self.preflight(changesets=())
        self.assertEqual(r.returncode, 1)
        self.assertIn("changeset", r.stderr)

    def test_干跑时允许没有待结算的changeset(self):
        # PR 上那次干跑复用同一个 preflight。刚发完版 .changeset 空着的时候，改发布脚本的
        # PR 不该红在「没什么可发的」这个与它无关的理由上（#96 评审）。
        假仓库(self.根, changesets=())
        r = 跑("preflight", "--root", str(self.根), "--allow-no-changeset")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_工作树不干净即停(self):
        假仓库(self.根)
        (self.根 / "脏的.md").write_text("x", encoding="utf-8")
        r = 跑("preflight", "--root", str(self.根))
        self.assertEqual(r.returncode, 1)
        self.assertIn("干净", r.stderr)


class 结算后(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.根 = pathlib.Path(self.tmp.name) / "repo"

    def postflight(self, *, 上一版="0.1.0", **kw):
        kw.setdefault("版本", "0.2.0")
        kw.setdefault("changesets", ())
        假仓库(self.根, **kw)
        return 跑("postflight", "--root", str(self.根), "--previous", 上一版)

    def test_全绿(self):
        r = self.postflight()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_版本没变即停(self):
        r = self.postflight(上一版="0.2.0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("0.2.0", r.stderr)

    def test_版本三处不齐即停(self):
        r = self.postflight(sync=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn("sync-plugin-version", r.stderr)

    def test_还剩下没结算掉的changeset即停(self):
        r = self.postflight(changesets=("bbb.md",))
        self.assertEqual(r.returncode, 1)
        self.assertIn("bbb.md", r.stderr)

    def test_CHANGELOG缺这一节即停(self):
        r = self.postflight(changelog="# loo0ng-skills" + LF + LF + "## 0.1.0" + LF + LF + "- 老东西" + LF)
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGELOG", r.stderr)

    def test_没有CHANGELOG文件也照样报一条不过(self):
        假仓库(self.根, 版本="0.2.0", changesets=())
        (self.根 / "CHANGELOG.md").unlink()
        r = 跑("postflight", "--root", str(self.根), "--previous", "0.1.0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGELOG", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_tag已经在了即停(self):
        r = self.postflight(tags=("v0.2.0",))
        self.assertEqual(r.returncode, 1)
        self.assertIn("v0.2.0", r.stderr)


class 抽发布说明(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.根 = pathlib.Path(self.tmp.name) / "repo"
        self.出 = pathlib.Path(self.tmp.name) / "notes.md"

    def test_只抽这一节(self):
        假仓库(self.根, 版本="0.2.0", changesets=())
        r = 跑("notes", "--root", str(self.根), "--out", str(self.出))
        self.assertEqual(r.returncode, 0, r.stderr)
        文 = self.出.read_text(encoding="utf-8")
        self.assertIn("- 新东西（#96）", 文)
        self.assertNotIn("老东西", 文)
        self.assertNotIn("## 0.2.0", 文)
        self.assertIn("### Minor Changes", 文)

    def test_可以指名版本(self):
        假仓库(self.根, 版本="0.2.0", changesets=())
        r = 跑("notes", "--root", str(self.根), "--version", "0.1.0", "--out", str(self.出))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("老东西", self.出.read_text(encoding="utf-8"))

    def test_没有CHANGELOG文件即停(self):
        假仓库(self.根, 版本="0.2.0", changesets=())
        (self.根 / "CHANGELOG.md").unlink()
        r = 跑("notes", "--root", str(self.根), "--out", str(self.出))
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGELOG", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse(self.出.exists())

    def test_缺这一节即停(self):
        假仓库(self.根, 版本="9.9.9", changesets=())
        r = 跑("notes", "--root", str(self.根), "--out", str(self.出))
        self.assertEqual(r.returncode, 1)
        self.assertIn("9.9.9", r.stderr)
        self.assertFalse(self.出.exists())


class 数待结算的(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.根 = pathlib.Path(self.tmp.name) / "repo"

    def test_一份没有就是0(self):
        假仓库(self.根, changesets=())
        r = 跑("pending", "--root", str(self.根))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "0")

    def test_数的是md不算README(self):
        假仓库(self.根, changesets=("aaa.md", "bbb.md"))
        r = 跑("pending", "--root", str(self.根))
        self.assertEqual(r.stdout.strip(), "2")


class 真仓库(unittest.TestCase):
    def test_抽得出已发那一版(self):
        with tempfile.TemporaryDirectory() as tmp:
            出 = pathlib.Path(tmp) / "notes.md"
            r = 跑("notes", "--version", "0.1.0", "--out", str(出))
            self.assertEqual(r.returncode, 0, r.stderr)
            文 = 出.read_text(encoding="utf-8")
        self.assertIn("新增参考 skill", 文)
        self.assertNotIn("## 0.1.0", 文)


if __name__ == "__main__":
    unittest.main()
