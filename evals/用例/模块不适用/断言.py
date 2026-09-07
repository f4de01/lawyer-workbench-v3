"""模块不适用用例的断言：该模块每个节点各一条不适用条目，别处不动。签名 (workspace: Path, reply: str)。"""
import json

模块 = "自行和解"
节点 = ["和解协议", "裁定认可和解协议并终结破产程序的申请"]
已办过的 = {"管理人承诺书及团队人员": ["生成", "确认"], "管理人印章备案报告": ["生成"]}


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _module(workspace, title):
    for m in _graph(workspace)["模块"]:
        if m["标题"] == title:
            return m
    raise AssertionError("图里没有模块「%s」" % title)


def check_模块下每个节点各一条不适用(workspace, reply):
    m = _module(workspace, 模块)
    assert [n["标题"] for n in m["节点"]] == 节点, "模块「%s」的节点变了：%s" % (模块, [n["标题"] for n in m["节点"]])
    for n in m["节点"]:
        assert len(n["条目"]) == 1, "节点「%s」该恰有一条条目，实际 %s" % (n["标题"], n["条目"])
        e = n["条目"][0]
        assert e["动作"] == "不适用", "该是不适用条目，实际 %r" % e["动作"]
        assert e["来源"] == "律师", "不适用的来源恒为律师，实际 %r" % e["来源"]
        assert e.get("原话"), "不适用条目没有原话（留痕规则 a）"
        assert "和解" in e["原话"], "原话该是律师那句话，实际 %r" % e["原话"]


def check_别的模块没被动过(workspace, reply):
    for m in _graph(workspace)["模块"]:
        if m["标题"] == 模块:
            continue
        for n in m["节点"]:
            期望 = 已办过的.get(n["标题"], [])
            assert [e["动作"] for e in n["条目"]] == 期望, \
                "节点「%s」的条目该是 %s，实际 %s" % (n["标题"], 期望, [e["动作"] for e in n["条目"]])


def check_视图重算了(workspace, reply):
    md = (workspace / "图视图.md").read_text(encoding="utf-8")
    assert "不适用" in md, "图视图.md 该显示不适用的状态"


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not (p.name == "__pycache__" or p.name.startswith(".")))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], "工作区根多出了东西：%s" % names
