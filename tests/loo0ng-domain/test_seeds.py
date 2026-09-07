"""种子「回流」（#34 验收）：用跑器自己的种子接口回放，再看工作区状态与 状态.md 说的一致。

运行：python -m unittest tests/loo0ng-domain/test_seeds.py

「在办中」那一层的状态由 tests/loo0ng-setup-case/test_seeds.py 覆盖，这里只看回流这一层加了什么：
两个律师自加节点的状态、可写的领域图副本、案件图指纹，以及 from-case 恰好提出已确认的那一个。
测试工作区跑完即弃（ADR-0015）。
"""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
EVALS = REPO / "evals" / "用例"
RUNNER = REPO / "scripts" / "skill-eval.py"
SKETCH = REPO / "skills" / "loo0ng-domain" / "scripts" / "sketch.py"
DOMAIN_GRAPH = REPO / "skills" / "loo0ng-domain" / "assets" / "破产" / "领域图.json"

spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

模块 = "接管与调查"
已确认 = "乙公司甲年乙月丙日厂区接管现场情况说明"
已生成 = "乙公司食堂承包合同解除请示"


class 回流种子(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        runner.replay_seed(EVALS, "回流", cls.ws)

    @classmethod
    def tearDownClass(cls):
        runner.remove_workspace(cls.ws)  # 只读的律师陈述与被占用的文件都归它处理

    def graph(self):
        return json.loads((self.ws / "案件" / "图.json").read_text(encoding="utf-8"))

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return m, n
        raise AssertionError("案件图里找不到节点「%s」" % title)

    def test_工作区根只有那三样(self):
        self.assertEqual(["基线.json", "案件", "领域图.json"],
                         sorted(p.name for p in self.ws.iterdir()),
                         "开发会话看得见的三样：案件工作区、可写的领域图副本、回流前的基线")

    def test_两个律师自加节点挂在领域图已有的模块下(self):
        for title in (已确认, 已生成):
            module, _ = self.node(title)
            self.assertEqual(模块, module["标题"], "「%s」该挂在「%s」下" % (title, 模块))

    def test_一个已确认一个只生成(self):
        self.assertEqual(["生成", "确认"], [e["动作"] for e in self.node(已确认)[1]["条目"]])
        self.assertEqual(["生成"], [e["动作"] for e in self.node(已生成)[1]["条目"]],
                         "只生成没拍板，判据 (a) 不满足（ADR-0012）")

    def test_标题带着本案的当事人与日期(self):
        for title in (已确认, 已生成):
            self.assertIn("乙公司", title, "标题要带案件事实，去案件化才有得改")
        self.assertIn("甲年乙月丙日", 已确认)

    def test_领域图副本是原件的一份拷贝(self):
        self.assertEqual(DOMAIN_GRAPH.read_bytes(), (self.ws / "领域图.json").read_bytes(),
                         "回流写的是副本，一次 eval 不该动到 skills/ 下的领域图（ADR-0015）")

    def test_基线记下了回流前的样子(self):
        基线 = json.loads((self.ws / "基线.json").read_text(encoding="utf-8"))
        for name, path in (("案件图sha256", self.ws / "案件" / "图.json"),
                           ("领域图sha256", self.ws / "领域图.json")):
            self.assertEqual(基线[name], hashlib.sha256(path.read_bytes()).hexdigest(), name)
        domain = json.loads((self.ws / "领域图.json").read_text(encoding="utf-8"))
        self.assertEqual(基线["领域图模块数"], len(domain["模块"]))
        self.assertEqual(基线["领域图节点数"], sum(len(m["节点"]) for m in domain["模块"]),
                         "断言按这个数判「只多出一个节点」，不硬写 72（下一次回流会改它）")

    def test_from_case恰好提出已确认的那一个(self):
        r = subprocess.run([sys.executable, str(SKETCH), "from-case",
                            "--case", str(self.ws / "案件" / "图.json"),
                            "--domain", str(self.ws / "领域图.json")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(0, r.returncode, r.stderr)
        proposal = json.loads(r.stdout[r.stdout.index("{"):])
        self.assertEqual([模块], [m["标题"] for m in proposal["模块"]], "模块按领域图的标题指认")
        nodes = proposal["模块"][0]["节点"]
        self.assertEqual([已确认], [n["标题"] for n in nodes], "只生成没拍板的那个不是候选")
        self.assertEqual(self.node(已确认)[1]["id"], nodes[0]["id"], "保留案件里的原 id（ADR-0012）")


if __name__ == "__main__":
    unittest.main()
