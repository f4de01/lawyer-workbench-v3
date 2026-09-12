"""记一句用例的断言：恰一条陈述文件、文件名与六字段合规、原话逐字、图没动。签名 (workspace: Path, reply: str)。"""
import json
import re

def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。

    #105 实测 Codex 也会把 uv 的缓存落成不带点的 `uv-cache`，所以 `uv-` 开头的一并忽略：
    它是 harness 自备解释器留下的，不是 skill 的产物。七份同名小函数逐字相同，改一处就一起改。
    """
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")

FILENAME_RE = re.compile(r"^\d{8}-\d{6}-[^\s.]{1,20}\.md$")
FIELDS = ["性质", "转述来源", "录入时间", "节点", "回应", "取代"]
WORDS = "东头那块地去年种的是番茄，今年别再种茄科。"


def _only_file(workspace):
    d = workspace / "材料" / "律师陈述"
    assert d.is_dir(), "没有 材料/律师陈述/"
    files = sorted(d.iterdir())
    assert len(files) == 1, "律师陈述目录里应恰有一个文件，实际：%s" % [p.name for p in files]
    return files[0]


def _split(text):
    assert text.startswith("---\n"), "文件须以 --- 起头"
    head, _, body = text[4:].partition("\n---\n")
    keys, data = [], {}
    for line in head.splitlines():
        k, sep, v = line.partition(":")
        assert sep, "头部行不是 键: 值：%r" % line
        keys.append(k)
        data[k] = v.strip()
    return keys, data, body


def check_文件名格式(workspace, reply):
    name = _only_file(workspace).name
    assert FILENAME_RE.match(name), "文件名不合 YYYYMMDD-HHMMSS-<标题>.md：%s" % name
    title = name[16:-3]
    assert all(c.isalnum() for c in title), "标题含标点或空格：%s" % title


def check_头部六字段(workspace, reply):
    keys, data, _ = _split(_only_file(workspace).read_text(encoding="utf-8"))
    assert keys == FIELDS, "头部字段应恰为 %s，实际 %s" % (FIELDS, keys)
    assert data["性质"] == "直接陈述", "律师本人说的事实应是直接陈述，实际 %r" % data["性质"]
    assert data["转述来源"] == "", "直接陈述不该有转述来源"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", data["录入时间"]), "录入时间不合 ISO 8601"
    assert data["取代"] == "", "首条陈述不该取代谁"


def check_原话逐字(workspace, reply):
    _, _, body = _split(_only_file(workspace).read_text(encoding="utf-8"))
    assert "## 原话" in body, "正文缺 ## 原话"
    assert WORDS in body, "原话没有逐字落下"
    assert "## 问题" not in body, "直接陈述不该有裁定的两段"


def check_图没动_收件箱没建(workspace, reply):
    data = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    assert all(n["条目"] == [] for m in data["模块"] for n in m["节点"]), "落档不该写条目"
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "指南", "收件箱", "文书", "材料", "模板"], "工作区里多出了东西：%s" % names
