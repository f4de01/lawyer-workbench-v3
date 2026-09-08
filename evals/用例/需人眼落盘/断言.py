"""需人眼落盘用例的断言：退出码 3 不是失败、清单原样进报告第一段、照常落盘、不重试。

签名 (workspace: Path, reply: str)。
断言只断结论类别与项名，不断数值（#59）：196.0 / 206.0 这些数是推算层的实现细节，钉在
tests/loo0ng-to-docx 里；这里钉的是门禁之外那一段，也就是编排 skill 拿到退出码 3 之后做什么。
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[3]
GATE = REPO / "skills" / "loo0ng-to-docx" / "scripts" / "gate.py"
节点 = "管理人银行账户备案报告"
模板 = "1-3.关于管理人银行账户备案的报告.docx"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def _生成条目(workspace):
    return [e for e in _node(workspace, 节点)["条目"] if e["动作"] == "生成"]


def check_需人眼件照常落盘且三件齐全(workspace, reply):
    """退出码 3 不是生成失败：位置与通过件相同、文件名不加装饰、三件齐全。

    模型若把 3 当失败（`if gate.py; then` 那类写法），这里一件都不会有。
    """
    d = workspace / "文书" / 节点
    assert d.is_dir(), "需人眼件该照常落进 文书/%s/，一个目录都没有" % 节点
    docx = sorted(p.name for p in d.glob("*.docx"))
    assert len(docx) == 1, "该只落一版（需人眼不触发重试、不改稿重出），实际 %s" % docx
    stem = docx[0][:-len(".docx")]
    assert stem == "%s-v1" % 节点, "文件名不加任何装饰，也不加「待目验」之类的后缀：%s" % docx[0]
    assert (d / (stem + ".md")).is_file(), "缺 Markdown 源 %s.md" % stem
    assert (d / (stem + "-审查报告.md")).is_file(), "每一版文书必有一份审查报告，缺 %s-审查报告.md" % stem
    stray = [p.name for p in d.iterdir() if p.suffix not in (".docx", ".md")]
    assert stray == [], "文书目录里多出了东西：%s" % stray


def check_落盘件重跑门禁是需人眼且退出码3(workspace, reply):
    """在临时副本上重跑门禁，钉的是结论类别与退出码，不是数值。

    必须带 --no-render：需人眼这一档的存在前提就是没有渲染结果，有渲染时点值取代推算区间、
    这一档当场坍缩（ADR-0017）。开发机上有 Word，不带这个旗跑同一件会得到另一档。
    门禁起的 Word 会多攥一会儿刚检过的件，所以照旧在临时副本上跑（#32）。
    """
    e = _生成条目(workspace)[0]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gate-check-"))
    try:
        copy = tmp / pathlib.Path(e["文书"]).name
        shutil.copy2(workspace / e["文书"], copy)
        r = subprocess.run([sys.executable, str(GATE), str(copy), "--no-render",
                            "--template", str(workspace / "模板" / "官方" / 模板), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode != 2, "门禁没跑起来：%s" % r.stderr.strip()
        result = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode == 3, "落盘件该是需人眼那一档（退出码 3），实际退出码 %d、结论 %s" % (r.returncode, result["结论"])
    assert result["结论"] == "需人眼", "结论该是需人眼，实际 %r" % result["结论"]
    assert result["不通过项"] == [], "这一档不该混进不通过项：%s" % result["不通过项"]
    assert any("最大行高" in n for n in result["需人眼项"]), "需人眼项该指着最大行高：%s" % result["需人眼项"]


def check_审查报告第一段是须目验清单(workspace, reply):
    """清单由门禁生成、不由模型撰写：原样放在第一段，在「生成依据」之前，一个字不改。"""
    e = _生成条目(workspace)[0]
    text = (workspace / e["审查报告"]).read_text(encoding="utf-8")
    # 只跳空行、标题行与围栏行：围栏是排版外壳，清单本身的字不许动。
    body = [l.rstrip() for l in text.splitlines()
            if l.strip() and not l.startswith("#") and not l.strip().startswith("```")]
    assert body, "审查报告是空的"
    assert body[0] == "须目验清单", "标题之后的第一段该是须目验清单，实际是 %r：\n%s" % (body[0], text)
    # 清单块只到门禁那句收尾为止；再往下是「生成依据」那一段，它的 - 行不归这里管。
    尾 = "确认前请在 WPS 或 Word 里打开看这几处。"
    assert 尾 in body, "清单末行被改掉了或整段没搬过来：%s" % text
    项行 = body[1:body.index(尾)]
    assert 项行, "清单一项都没有"
    for l in 项行:  # 每行四样齐全：项名、坐标、推算区间与阈值、最坏越界，缺一即清单被重写过
        assert l.startswith("- "), "清单项该原样保留门禁的行首「- 」：%r" % l
        assert any(k in l for k in ("最大行高", "页数", "空白页")), "清单行缺项名：%r" % l
        for piece in ("阈值", "最坏越界"):
            assert piece in l, "清单行缺 %s：%r" % (piece, l)
    坐标行 = [l for l in 项行 if "最大行高" in l and "张表第" in l]
    assert 坐标行, "该有一行指着最大行高与它的表格坐标：%s" % 项行
    assert text.index("须目验清单") < text.index("生成依据"), "须目验清单该在「生成依据」之前：\n%s" % text
    assert "需人眼" in text, "「版式门禁」段该照实写需人眼这一档：\n%s" % text


def check_成品里有模板那张表(workspace, reply):
    """种子的钉子钉在模板的表格行上：稿子里没有表，转换器就不把表落进成品，钉子不生效。

    落空时门禁给的是通过、不是需人眼，用例会红在别处、看不出原因。这条把那种落空
    单独钉成一句人话，与「模型拿到退出码 3 之后做什么」分开。
    """
    e = _生成条目(workspace)[0]
    with zipfile.ZipFile(workspace / e["文书"]) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "<w:tbl" in xml, "成品里没有表：模型没照模板写那张表，种子钉的行高就没落进成品（钉子落空，不是这一档的事故）"


def check_图上多一条生成条目(workspace, reply):
    entries = _生成条目(workspace)
    assert len(entries) == 1, "该追加一条生成条目，实际 %s" % entries
    e = entries[0]
    assert e["来源"] == "agent", "工作台出的件来源该是 agent，实际 %r" % e["来源"]
    for key in ("文书", "源", "审查报告"):
        rel = e.get(key)
        assert rel, "生成条目缺 %s：%s" % (key, e)
        assert (workspace / rel).is_file(), "条目里的 %s 指着不存在的文件：%s" % (key, rel)
        assert rel.startswith("文书/%s/" % 节点), "%s 该落在 文书/<节点标题>/ 下，实际 %r" % (key, rel)


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，确认永不自动，实际 %s" % 动作
    assert _node(workspace, 节点)["条目"][-1]["动作"] == "生成", "本节点末条该还是生成，等律师拍板"


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not (p.name == "__pycache__" or p.name.startswith(".")))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], \
        "工作区根多出了东西（转换与门禁在临时位置完成，工作区里不建暂存目录）：%s" % names


def check_文书目录只多了这一个(workspace, reply):
    dirs = sorted(p.name for p in (workspace / "文书").iterdir() if p.is_dir())
    assert dirs == ["管理人印章备案报告", "管理人承诺书及团队人员", 节点], "文书/ 下多了目录：%s" % dirs
