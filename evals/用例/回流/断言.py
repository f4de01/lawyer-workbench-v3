"""回流用例的断言：领域图恰好多出去案件化后的那一个节点，案件图一字未动。签名 (workspace: Path, reply: str)。"""
import hashlib
import json

案件里的标题 = "乙公司甲年乙月丙日厂区接管现场情况说明"
去案件化的核心 = "接管现场情况说明"  # 「乙公司」「甲年乙月丙日」必去，「厂区」去不去归模型判
只生成的 = "食堂承包合同解除请示"
模块 = "接管与调查"
领域图原有节点数 = 72


def _domain(workspace):
    return json.loads((workspace / "领域图.json").read_text(encoding="utf-8"))


def _case(workspace):
    return json.loads((workspace / "案件" / "图.json").read_text(encoding="utf-8"))


def _nodes(data):
    return [(m["标题"], n) for m in data["模块"] for n in m["节点"]]


def _case_node(workspace, title):
    for _, n in _nodes(_case(workspace)):
        if n["标题"] == title:
            return n
    raise AssertionError("案件图里找不到节点「%s」" % title)


def check_回显里有去案件化后的标题(workspace, reply):
    assert 去案件化的核心 in reply, "回复里没提那个候选：\n%s" % reply[:400]
    # 去案件化后的标题多半是案件里那个标题的真子串，所以先把原标题的所有出现抠掉，剩下的文字里还得有它，
    # 才算清单真的标出了去案件化后的标题，而不是只把案件里的原标题读了一遍。
    title = _回流的节点(workspace)[1]["标题"]
    assert title in reply.replace(案件里的标题, ""), \
        "清单里没标出去案件化后的标题「%s」：\n%s" % (title, reply[:400])


def _回流的节点(workspace):
    """领域图里那条回流进来的节点：(所在模块标题, 节点)。去案件化后的标题由模型定，只按核心词认。"""
    hit = [(mod, n) for mod, n in _nodes(_domain(workspace)) if 去案件化的核心 in n["标题"]]
    assert len(hit) == 1, "去案件化后的那个节点该恰好有一条，实际 %s" % [n["标题"] for _, n in hit]
    return hit[0]


def check_领域图恰好多出那一个节点(workspace, reply):
    nodes = _nodes(_domain(workspace))
    assert len(nodes) == 领域图原有节点数 + 1, "领域图该只多出一个节点，实际 %d 个" % len(nodes)
    mod, node = _回流的节点(workspace)
    assert mod == 模块, "该落在领域图已有的模块「%s」下，实际「%s」" % (模块, mod)
    assert "乙公司" not in node["标题"] and "甲年" not in node["标题"], \
        "标题没去案件化，当事人或日期还在：%r" % node["标题"]


def check_id与案件图一致且无条目(workspace, reply):
    node = _回流的节点(workspace)[1]
    assert node["id"] == _case_node(workspace, 案件里的标题)["id"], \
        "回流保留案件里的原 id（ADR-0012），实际领域图里是 %r" % node["id"]
    assert node["条目"] == [], "领域图没有条目（ADR-0012），实际 %s" % node["条目"]
    assert node["空白模板"] == "无", "案件里那个节点没有空白模板，实际 %r" % node["空白模板"]


def check_只生成没拍板的那个没回流(workspace, reply):
    titles = [n["标题"] for _, n in _nodes(_domain(workspace))]
    assert not any(只生成的 in t for t in titles), \
        "只生成没拍板的节点不是候选（判据 a，ADR-0012），却进了领域图：%s" % [t for t in titles if 只生成的 in t]


def check_领域图仍是一张合法的领域图(workspace, reply):
    data = _domain(workspace)
    assert set(data) == {"格式版本", "领域", "模块"}, "领域图顶层多了键：%s" % sorted(data)
    assert data["领域"] == "破产", "领域名被动了：%r" % data["领域"]
    ids = [n["id"] for _, n in _nodes(data)] + [m["id"] for m in data["模块"]]
    assert len(ids) == len(set(ids)), "领域图里 id 重复了"


def check_案件图字节不变(workspace, reply):
    digest = hashlib.sha256((workspace / "案件" / "图.json").read_bytes()).hexdigest()
    assert digest == (workspace / "案件图指纹.txt").read_text(encoding="utf-8").strip(), \
        "回流只读案件图，案件图不该有任何改动（ADR-0012）"
    entries = [e["动作"] for _, n in _nodes(_case(workspace)) for e in n["条目"]]
    assert entries.count("确认") == 2, "案件图的条目该是种子那几条，实际确认 %d 条" % entries.count("确认")


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".")


def check_雏形文件没落进工作区(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["案件", "案件图指纹.txt", "领域图.json"], \
        "工作区里多出了文件（雏形文件该写在临时目录）：%s" % names
