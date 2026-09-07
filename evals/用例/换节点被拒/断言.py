"""换节点被拒用例的断言：三样全无只回缺什么、图一字不动，第二个节点被拒。签名 (workspace: Path, reply: str)。"""
import json


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def check_图一字不动(workspace, reply):
    data = _graph(workspace)
    titles = {m["标题"]: [n["标题"] for n in m["节点"]] for m in data["模块"]}
    assert titles == {"整地": ["松土", "施底肥"], "播种": ["选种", "下种"],
                      "养护": ["浇水", "除草", "搭架"], "收获": ["采摘", "记账"]}, \
        "三样全无与被拒的那次都不该改图的构成，实际：%s" % titles
    动作 = [e["动作"] for m in data["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作 == [], "三样全无不算一次生成，条目一条都不该有，实际 %s" % 动作


def check_文书下一件都没落(workspace, reply):
    docs = workspace / "文书"
    left = sorted(p.relative_to(workspace).as_posix() for p in docs.rglob("*")) if docs.is_dir() else []
    assert left == [], "没出件就不该往 文书/ 下落东西：%s" % left


def check_回复说了缺什么(workspace, reply):
    assert "松土" in reply, "回复里没提第一个节点：\n%s" % reply
    assert any(k in reply for k in ("材料", "空白模板", "模板", "陈述")), \
        "三样全无时要回缺什么，回复里一样都没提：\n%s" % reply


def check_回复拒了第二个节点(workspace, reply):
    assert "除草" in reply, "回复里没提被拒的那个节点：\n%s" % reply
    assert any(k in reply for k in ("新对话", "新开对话", "另开", "再开")), \
        "第二次出一版指向另一节点要拒绝并让律师开新对话：\n%s" % reply


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not (p.name == "__pycache__" or p.name.startswith(".")))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], "工作区根多出了东西：%s" % names
