"""改标题用例的断言：图只改了那一个标题，两份视图随之重算。签名 (workspace: Path, reply: str)。"""
import json

EXPECTED_TITLES = {
    "整地": ["松土", "施底肥"],
    "播种": ["选种", "播种入土"],
    "养护": ["浇水", "除草", "搭架"],
    "收获": ["采摘", "记账"],
}


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _view(workspace):
    return json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))


def _node(data, title):
    for m in data["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("找不到节点「%s」" % title)


def check_图里标题已改_其余不动(workspace, reply):
    data = _graph(workspace)
    titles = {m["标题"]: [n["标题"] for n in m["节点"]] for m in data["模块"]}
    assert titles == EXPECTED_TITLES, "模块与节点标题应只改一处，实际：%s" % titles
    assert _node(data, "播种入土")["id"] == "n-xiazhong", "改标题不应换 id"
    assert all(n["条目"] == [] for m in data["模块"] for n in m["节点"]), "改标题不该动条目"
    assert set(data) == {"格式版本", "领域", "模块"}, "图顶层多了键：%s" % sorted(data)


def check_视图md已重算(workspace, reply):
    md = (workspace / "图视图.md").read_text(encoding="utf-8")
    assert "播种入土" in md, "图视图.md 里没有新标题"
    assert "下种" not in md, "图视图.md 还留着旧标题"


def check_视图json来源与时限按id查出(workspace, reply):
    view = _view(workspace)
    n = _node(view, "播种入土")
    assert n["来源"] == "领域图", "改了标题的领域图节点来源仍应是 领域图，实际 %r" % n["来源"]
    assert n["时限"] == "选种之后、雨季之前（手册，示例）", "时限应按 id 从领域图查出，实际 %r" % n.get("时限")
    assert view["前方"] == [], "整份起手后前方应为空"
    assert view["格式版本"] == _graph(workspace)["格式版本"], "两份 JSON 的格式版本应一致"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".")


def check_没写别的文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "指南", "收件箱", "文书", "材料", "模板"], "工作区里多出了文件：%s" % names
