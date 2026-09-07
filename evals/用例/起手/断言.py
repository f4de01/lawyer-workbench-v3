"""起手用例的断言：六格、图与两份视图、工作区指针块、归档去向、雏形、既有成品登记、没有自动确认。

签名 (workspace: Path, reply: str)。
"""
import json
import pathlib
import re

CELLS = ["收件箱", "材料", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书"]
DOMAIN_ASSETS = "skills/loo0ng-domain/assets/破产"
成品 = "管理人承诺书（已交法院）.md"
成品节点 = "管理人承诺书及团队人员"
新节点 = "联络人备案表"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".")


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _nodes(data):
    for m in data["模块"]:
        for n in m["节点"]:
            yield m, n


def _node(workspace, title):
    for _, n in _nodes(_graph(workspace)):
        if n["标题"] == title:
            return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_六格齐全(workspace, reply):
    for rel in CELLS:
        assert (workspace / rel).is_dir(), "缺格 %s" % rel
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], "工作区根多出了东西：%s" % names


def check_图与两份视图都在(workspace, reply):
    data = _graph(workspace)
    assert set(data) == {"格式版本", "领域", "模块"}, "图顶层多了键：%s" % sorted(data)
    assert data["领域"] == "破产", "领域应是 破产，实际 %r" % data["领域"]
    for name in ("图视图.md", "图视图.json"):
        assert (workspace / name).is_file(), "缺视图 %s" % name
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    assert view["格式版本"] == data["格式版本"], "两份 JSON 的格式版本应一致"


def check_工作区指针块四项齐全(workspace, reply):
    agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert re.search(r"^- 领域：破产\s*$", agents, re.M), "指针块缺领域名：\n%s" % agents
    m = re.search(r"^- 领域目录：(\S+)\s*$", agents, re.M)
    assert m, "指针块缺领域目录：\n%s" % agents
    assert m.group(1).replace("\\", "/").endswith(DOMAIN_ASSETS), \
        "领域目录应是 %s 的绝对路径，实际 %r" % (DOMAIN_ASSETS, m.group(1))
    assert pathlib.Path(m.group(1)).is_absolute(), "领域目录要写绝对路径，实际 %r" % m.group(1)
    for expected in ("图.json", "图视图.md", "图视图.json", "loo0ng-doit", "只读"):
        assert expected in agents, "指针块里缺 %s：\n%s" % (expected, agents)
    assert (workspace / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md", \
        "CLAUDE.md 只该有一行 @AGENTS.md"


def check_收件箱各归其格(workspace, reply):
    去向 = {
        "材料/债务人移交物品清单.txt": "本案事实来源原件",
        "指南/甲法院破产案件管理人工作提示.md": "本案适用的官方要求文件",
        "模板/官方/（格式）债权申报登记表.md": "官方发布的空白件",
        "模板/生成/本所自用-接管物品交接单空表.md": "自己做的空白件",
        "材料/%s" % 成品: "既有成品，归材料",
    }
    for rel, why in 去向.items():
        assert (workspace / rel).is_file(), "%s 没到 %s" % (why, rel)


def check_拿不准的留在收件箱(workspace, reply):
    left = sorted(p.name for p in (workspace / "收件箱").rglob("*"))
    assert left == ["未命名.txt"], "收件箱里该只剩那件没有正向证据的，实际 %s" % left


def check_雏形写进了图(workspace, reply):
    data = _graph(workspace)
    titles = [n["标题"] for _, n in _nodes(data)]
    assert 成品节点 in titles, "指南里提到的「%s」没进图：%s" % (成品节点, titles)
    assert 新节点 in titles, "指南里提到的「%s」没进图：%s" % (新节点, titles)
    assert _node(workspace, 成品节点)["id"] == "n-chengnuoshu", "同名节点应按领域图带入、沿用领域图的 id"
    assert len(titles) == len(set(titles)), "图里有重名节点：%s" % titles
    assert len(titles) <= 6, "空图起手加一份指南不该长出这么多节点（惰性只约束 agent）：%s" % titles


def check_既有成品登记为已生成来源律师(workspace, reply):
    entries = _node(workspace, 成品节点)["条目"]
    assert len(entries) == 1, "该节点应恰有一条条目，实际 %s" % entries
    e = entries[0]
    assert e["动作"] == "生成", "起手登记该是生成条目，实际 %r" % e["动作"]
    assert e["来源"] == "律师", "既有成品的来源该记律师，实际 %r" % e["来源"]
    assert e["文书"] == "材料/%s" % 成品, "文书该指向归档后的既有成品，实际 %r" % e["文书"]
    review = workspace / e["审查报告"]
    assert review.is_file(), "每一版文书必有一份审查报告，缺 %s" % e["审查报告"]
    text = review.read_text(encoding="utf-8")
    for heading in ("## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"):
        assert heading in text, "审查报告缺固定段 %s" % heading


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for _, n in _nodes(_graph(workspace)) for e in n["条目"]]
    assert 动作 == ["生成"], "起手只该落那一条生成条目，确认永不自动，实际 %s" % 动作


def check_收尾三段(workspace, reply):
    assert re.search(r"六格|图\.json|图视图", reply), "收尾第一段没说落了什么（六格、图与视图一件都没提）：\n%s" % reply
    assert re.search(r"确认|拍板", reply), "收尾第二段没说该拍板什么：\n%s" % reply
    assert re.search(r"loo0ng-doit", reply), "收尾第三段没给下一句该打什么：\n%s" % reply


def check_回显里出现过雏形与既有成品(workspace, reply):
    """AC「指南非空时回显含雏形」：起手清单是回显给律师的，从指南提出的那条与那件既有成品要在回复里看得见。"""
    assert 新节点 in reply, "回显里没有从指南提出的「%s」：\n%s" % (新节点, reply)
    assert 成品节点 in reply or 成品 in reply, "回显里没有既有成品的建议登记：\n%s" % reply
