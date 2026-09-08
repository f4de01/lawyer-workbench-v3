"""不通过收尾用例的断言：生成失败，且什么都没留下。

签名 (workspace: Path, reply: str)。
断的全是终态（#74）：「至多 2 次」那个数从工作区里看不出来：转换器写在 %TEMP%，
重转的中间件不进工作区。所以这里钉的是收尾（失败且不落盘、不追加条目、不写审查报告、
不走歪门），不是次数；次数仍只有两处正文与人工触发看着。别为了断那个数去改转换器的落点。
"""
import json
import pathlib

节点 = "管理人银行账户备案报告"
种子里的文书目录 = ["管理人印章备案报告", "管理人承诺书及团队人员"]


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_一件都没落盘(workspace, reply):
    """不通过什么都不落：连 文书/<节点标题>/ 这个目录都不该建。

    skill 正文那四条明令（不调阈值、不跳门禁、不把临时件手拷进 文书/、不改成品 DOCX）
    全都收在这一条里：任何一条走了歪门，这一件就会落盘，这里当场红。扫回复里有没有
    --max-row-height 反而不行：阈值由律师定，把这个杠杆讲给律师听是 skill 正文允许的
    （「律师说本案文书就是长，落成一条陈述再带参数」），实测模型正是这么收尾的。
    """
    d = workspace / "文书" / 节点
    assert not d.exists(), "生成失败不落盘，文书/%s/ 里却有：%s" % (节点, sorted(p.name for p in d.iterdir()))
    dirs = sorted(p.name for p in (workspace / "文书").iterdir() if p.is_dir())
    assert dirs == 种子里的文书目录, "文书/ 下只该剩种子里那两个目录，实际 %s" % dirs


def check_没有审查报告落盘(workspace, reply):
    """三件缺一即生成失败，失败时一件都不写：整个工作区里只该有种子那两份报告。

    不按节点名过滤：模型把报告写在别处、名字里不带节点标题时，按名过滤这条会空转。
    """
    报告 = sorted(str(p.relative_to(workspace)).replace("\\", "/")
                for p in workspace.rglob("*审查报告*.md"))
    种子的 = ["文书/%s/%s-v1-审查报告.md" % (t, t) for t in 种子里的文书目录]
    assert 报告 == sorted(种子的), "生成失败不写审查报告，工作区里的报告是：%s" % 报告


def check_图上没有新条目(workspace, reply):
    """条目只有出件那一条来路（ADR-0008）：件没落，条目就无从追加。"""
    n = _node(workspace, 节点)
    assert n["条目"] == [], "生成失败不追加条目，实际 %s" % n["条目"]


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，确认永不自动，实际 %s" % 动作
    assert 动作.count("生成") == 2, "只该有种子里那两条生成，本节点这一次失败了，实际 %s" % 动作


def check_回复带着门禁的原话与兜底那条路(workspace, reply):
    """失败时把门禁输出原文交给律师，并提兜底自写这条路（skill 正文）。

    「行高超阈值」是门禁自己那条不通过项的项名（gate.py 的 judge），不是模型能替它写出来的话：
    这一条同时兜住「压根没跑门禁、直接报生成失败」那种走法：那种走法别的断言全都绿。
    按 #59 只断项名与结论类别，不断 250.1 / 245.0 这些数。
    """
    assert "行高超阈值" in reply, "回复里没有门禁那条不通过项的原话（项名都没有，多半没真跑门禁）：\n%s" % reply
    assert "阈值" in reply, "门禁原话里的阈值那半句没交给律师：\n%s" % reply
    assert "不通过" in reply, "回复里没说门禁的结论：\n%s" % reply
    assert any(k in reply for k in ("兜底", "自己写", "自写")), "没告诉律师可以兜底自写：\n%s" % reply


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not (p.name == "__pycache__" or p.name.startswith(".")))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], \
        "工作区根多出了东西（转换与门禁在临时位置完成，工作区里不建暂存目录）：%s" % names


def check_没往模板与材料里塞东西(workspace, reply):
    """改成品或另存一份「改好的」件时最容易掉在这两处。"""
    生成模板 = sorted(p.name for p in (workspace / "模板" / "生成").iterdir())
    assert 生成模板 == [], "模板/生成/ 该还是空的，实际 %s" % 生成模板
    docx = [str(p.relative_to(workspace)) for p in (workspace / "材料").rglob("*.docx")]
    assert docx == [], "材料/ 里多出了 docx：%s" % docx
