"""skills/loo0ng-setup-case/scripts/setup.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/loo0ng-setup-case/test_setup.py

缝是起手 CLI 加临时工作区里的文件：每个测试在临时目录里调 main(argv)，再看六格、图、视图、
工作区指针块与既有成品的登记条目落成了什么样。领域用合成小领域「菜园」（ADR-0015）。
文件名与内容全是合成的，没有案件内容。
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "loo0ng-setup-case" / "scripts" / "setup.py"
DOMAIN = REPO / "evals" / "领域" / "菜园"

spec = importlib.util.spec_from_file_location("loo0ng_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

CELLS = ["收件箱", "材料", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书"]


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp(prefix="setup-test-"))
        self.addCleanup(shutil.rmtree, self.ws, True)

    def cli(self, *argv, workspace=None):
        args = list(argv) + ["--workspace", str(workspace or self.ws)]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = setup.main(args)
            except SystemExit as e:  # argparse 的用法错
                code = e.code if isinstance(e.code, int) else 2
        return Run(code, out.getvalue(), err.getvalue())

    def graph(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def titles(self):
        return {m["标题"]: [n["标题"] for n in m["节点"]] for m in self.graph()["模块"]}


class InitCase(Base):
    def test_空图起手落下六格与图与两份视图(self):
        r = self.cli("init", "--empty", "--name", "菜园")
        self.assertEqual(r.code, 0, r)
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assertEqual(self.graph()["领域"], "菜园")
        self.assertEqual(self.graph()["模块"], [])
        for name in ("图视图.md", "图视图.json"):
            self.assertTrue((self.ws / name).is_file(), "缺视图 %s" % name)

    def test_整份领域图起手带进全部模块与节点(self):
        r = self.cli("init", "--full", "--domain", str(DOMAIN))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(len(self.graph()["模块"]), 4)
        self.assertEqual(sum(len(m["节点"]) for m in self.graph()["模块"]), 9)
        self.assertEqual(json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))["前方"], [])

    def assert_指针块(self, 领域, 领域目录文本):
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- 领域：%s" % 领域, agents)
        self.assertIn("- 领域目录：%s" % 领域目录文本, agents)
        for expected in ("图.json", "图视图.md", "图视图.json", "loo0ng-doit", "只读"):
            self.assertIn(expected, agents, "指针块里缺 %s" % expected)
        self.assertEqual((self.ws / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_定制图起手(self):
        custom = self.ws.parent / ("定制图-%s.json" % self.ws.name)
        self.addCleanup(custom.unlink, True)
        custom.write_text(json.dumps({"格式版本": 1, "领域": "菜园", "模块": [
            {"id": "m-x", "标题": "只有一个模块", "节点": [
                {"id": "n-x", "标题": "只有一个节点", "空白模板": "无", "条目": []}]}]},
            ensure_ascii=False), encoding="utf-8")
        r = self.cli("init", "--from", str(custom), "--domain", str(DOMAIN))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.titles(), {"只有一个模块": ["只有一个节点"]})
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_指针块四项齐全(self):
        self.cli("init", "--full", "--domain", str(DOMAIN))
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_领域目录给的是领域图文件也记成目录(self):
        self.cli("init", "--full", "--domain", str(DOMAIN / "领域图.json"))
        self.assertIn("- 领域目录：%s" % DOMAIN.as_posix(),
                      (self.ws / "AGENTS.md").read_text(encoding="utf-8"))

    def test_没有领域目录时指针块照样落下(self):
        self.cli("init", "--empty", "--name", "菜园")
        self.assert_指针块("菜园", "（无")
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("空图", agents,
                         "没给领域目录跟起手图选了哪一种是两回事：--from 的定制图也可以没有领域目录")

    def test_空图起手也验六格与指针块(self):
        self.cli("init", "--empty", "--domain", str(DOMAIN))
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_已有图就拒绝且一字不动(self):
        (self.ws / "图.json").write_text("原样", encoding="utf-8")
        r = self.cli("init", "--empty", "--name", "菜园")
        self.assertEqual(r.code, 1, r)
        self.assertIn("图.json", r.err)
        self.assertEqual((self.ws / "图.json").read_text(encoding="utf-8"), "原样")
        self.assertFalse((self.ws / "收件箱").exists(), "拒绝时不该建六格")
        self.assertFalse((self.ws / "AGENTS.md").exists(), "拒绝时不该写指针块")

    def test_三选一必须恰好一个(self):
        r = self.cli("init", "--empty", "--full", "--domain", str(DOMAIN))
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists())
        self.assertFalse((self.ws / "AGENTS.md").exists())
        r = self.cli("init")
        self.assertEqual(r.code, 1, r)

    def test_引擎拒写时不留半个工作区(self):
        r = self.cli("init", "--empty")  # 既没有 --domain 也没有 --name，引擎拒
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists())
        self.assertFalse((self.ws / "AGENTS.md").exists())
        self.assertFalse((self.ws / "收件箱").exists())


class TemplateCase(Base):
    def make_domain(self, files):
        root = pathlib.Path(tempfile.mkdtemp(prefix="setup-domain-"))
        self.addCleanup(shutil.rmtree, root, True)
        shutil.copy2(DOMAIN / "领域图.json", root / "领域图.json")
        if files is not None:
            (root / "模板").mkdir()
            for name in files:
                (root / "模板" / name).write_bytes(b"synthetic")
        return root

    def test_起手图挂到的官方模板拷进模板官方(self):
        root = self.make_domain(["施肥记录.docx", "播种登记.docx", "采摘记录.docx", "没人挂的.docx"])
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        got = sorted(p.name for p in (self.ws / "模板" / "官方").iterdir())
        self.assertEqual(got, sorted(["施肥记录.docx", "播种登记.docx", "采摘记录.docx"]),
                         "只拷起手图上挂到的那几件")

    def test_空图起手不拷模板(self):
        root = self.make_domain(["施肥记录.docx"])
        self.cli("init", "--empty", "--domain", str(root))
        self.assertEqual(list((self.ws / "模板" / "官方").iterdir()), [])

    def test_领域目录里缺模板原件只报不拒(self):
        root = self.make_domain(["施肥记录.docx"])
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        self.assertIn("播种登记.docx", r.out)
        self.assertEqual(sorted(p.name for p in (self.ws / "模板" / "官方").iterdir()), ["施肥记录.docx"])

    def test_领域目录没有模板格也不拒(self):
        root = self.make_domain(None)
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(list((self.ws / "模板" / "官方").iterdir()), [])


class RegisterCase(Base):
    def setUp(self):
        super().setUp()
        self.cli("init", "--full", "--domain", str(DOMAIN))
        self.doc = self.ws / "材料" / "旧的下种记录.md"
        self.doc.write_text("合成的既有成品", encoding="utf-8")

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)

    def test_既有成品登记为已生成来源律师(self):
        r = self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md",
                     "--words", "都按建议登记")
        self.assertEqual(r.code, 0, r)
        entries = self.node("下种")["条目"]
        self.assertEqual(len(entries), 1, entries)
        self.assertEqual(entries[0]["动作"], "生成")
        self.assertEqual(entries[0]["来源"], "律师")
        self.assertEqual(entries[0]["文书"], "材料/旧的下种记录.md")

    def test_登记不确认任何节点(self):
        self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md", "--words", "都按建议登记")
        actions = [e["动作"] for m in self.graph()["模块"] for n in m["节点"] for e in n["条目"]]
        self.assertEqual(actions, ["生成"], "起手登记只该落生成条目")

    def test_审查报告按固定模板落在文书目录下(self):
        self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md", "--words", "都按建议登记")
        review = self.ws / "文书" / "下种" / "下种-v1-审查报告.md"
        self.assertTrue(review.is_file(), "没写审查报告")
        text = review.read_text(encoding="utf-8")
        for heading in ("## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"):
            self.assertIn(heading, text, "审查报告缺固定段 %s" % heading)
        self.assertIn("都按建议登记", text)
        self.assertIn("材料/旧的下种记录.md", text)
        self.assertEqual(self.node("下种")["条目"][0]["审查报告"], "文书/下种/下种-v1-审查报告.md")

    def test_文书不存在就拒(self):
        r = self.cli("register", "--node", "下种", "--doc", "材料/不存在.md", "--words", "都按建议登记")
        self.assertEqual(r.code, 1, r)
        self.assertEqual(self.node("下种")["条目"], [])
        self.assertFalse((self.ws / "文书" / "下种").exists(), "拒绝时不该留审查报告")

    def test_越界路径就拒(self):
        for bad in ("../外面.md", "D:/外面.md", "材料\\反斜杠.md"):
            r = self.cli("register", "--node", "下种", "--doc", bad, "--words", "都按建议登记")
            self.assertEqual(r.code, 1, "%s 应被拒：%r" % (bad, r))

    def test_引擎拒写时回滚审查报告(self):
        r = self.cli("register", "--node", "图里没有的节点", "--doc", "材料/旧的下种记录.md",
                     "--words", "都按建议登记")
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "文书" / "图里没有的节点").exists(), "拒绝时不该留审查报告")

    def test_没有图就拒(self):
        empty = pathlib.Path(tempfile.mkdtemp(prefix="setup-nograph-"))
        self.addCleanup(shutil.rmtree, empty, True)
        r = self.cli("register", "--node", "下种", "--doc", "材料/x.md", "--words", "x", workspace=empty)
        self.assertEqual(r.code, 1, r)


if __name__ == "__main__":
    unittest.main()
