"""出雏形用例的断言：回显含四样，拍板后图里多了指南提出的、同名的不重复、案件图不存时限、视图重算。签名 (workspace: Path, reply: str)。"""
import json

ORIGINAL = {
    "整地": ["松土", "施底肥"],
    "播种": ["选种", "下种"],
    "养护": ["浇水", "除草", "搭架"],
    "收获": ["采摘", "记账"],
}
ORIGINAL_IDS = {"松土": "n-songtu", "施底肥": "n-difei", "选种": "n-xuanzhong", "下种": "n-xiazhong",
                "浇水": "n-jiaoshui", "除草": "n-chucao", "搭架": "n-dajia", "采摘": "n-caizhai", "记账": "n-jizhang"}


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _titles(data):
    return {m["标题"]: [n["标题"] for n in m["节点"]] for m in data["模块"]}


def _node(data, title):
    for m in data["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("找不到节点「%s」" % title)


def check_回显含模块节点模板与时限(workspace, reply):
    for text in ("越冬", "覆膜", "清园", "施追肥", "覆膜记录"):
        assert text in reply, "回显里没有「%s」" % text
    assert "时限" in reply, "回显里没提时限"
    # 时限句原文在 check 的清单里（脚本层已断言）；Codex 侧只捕获最后一条回复，清单常在中间回复里，这里只要求提到。


def check_图里多了指南提出的(workspace, reply):
    data = _graph(workspace)
    titles = _titles(data)
    assert titles.get("越冬") == ["覆膜", "清园"], "「越冬」模块应有覆膜、清园两个节点，实际：%s" % titles.get("越冬")
    assert titles.get("养护") == ["浇水", "除草", "搭架", "施追肥"], "「养护」应在末尾多一个施追肥、浇水不重复，实际：%s" % titles.get("养护")
    for module, nodes in ORIGINAL.items():
        if module != "养护":
            assert titles.get(module) == nodes, "模块「%s」被动了：%s" % (module, titles.get(module))
    assert set(titles) == set(ORIGINAL) | {"越冬"}, "模块集合不对：%s" % sorted(titles)


def check_空白模板与id(workspace, reply):
    data = _graph(workspace)
    assert _node(data, "覆膜")["空白模板"] == {"来源": "官方", "文件": "覆膜记录.docx"}, "覆膜应挂官方模板 覆膜记录.docx，实际 %r" % _node(data, "覆膜")["空白模板"]
    assert _node(data, "清园")["空白模板"] == "无"
    assert _node(data, "施追肥")["空白模板"] == "无"
    for title, id_ in ORIGINAL_IDS.items():
        assert _node(data, title)["id"] == id_, "原有节点「%s」的 id 变了" % title


def check_案件图不存时限且无条目(workspace, reply):
    data = _graph(workspace)
    for m in data["模块"]:
        for n in m["节点"]:
            assert "时限" not in n, "案件图节点「%s」带了时限（ADR-0016）" % n["标题"]
            assert n["条目"] == [], "雏形不该写条目：%s" % n["标题"]
    assert set(data) == {"格式版本", "领域", "模块"}, "图顶层多了键：%s" % sorted(data)


def check_视图已重算(workspace, reply):
    md = (workspace / "图视图.md").read_text(encoding="utf-8")
    assert "越冬" in md and "施追肥" in md, "图视图.md 没有重算"
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    assert "越冬" in [m["标题"] for m in view["模块"]], "图视图.json 没有重算"
    assert _node(view, "覆膜")["来源"] == "案件"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".")


def check_没写别的文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "指南", "收件箱", "文书", "材料", "模板"], "工作区里多出了文件（雏形文件该写在临时目录）：%s" % names
    assert sorted(p.name for p in (workspace / "指南").iterdir()) == ["种植指南.md"], "指南/ 里多出了东西"
