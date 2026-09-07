"""归档一件用例的断言：原件按原名到了材料、收件箱空了、图没动。签名 (workspace: Path, reply: str)。"""
import json
import pathlib

def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".")

SEED_FILE = pathlib.Path(__file__).resolve().parents[2] / "种子" / "收件箱" / "收件箱" / "地块记录.txt"


def check_原件按原名到了材料(workspace, reply):
    target = workspace / "材料" / "地块记录.txt"
    assert target.is_file(), "材料/ 下没有 地块记录.txt"
    assert target.read_bytes() == SEED_FILE.read_bytes(), "搬过去的内容变了"


def check_收件箱原件消失(workspace, reply):
    inbox = workspace / "收件箱"
    assert not (inbox / "地块记录.txt").exists(), "收件箱里还留着原件"
    leftovers = sorted(p.as_posix() for p in inbox.rglob("*")) if inbox.exists() else []
    assert leftovers == [], "收件箱里多出了东西：%s" % leftovers


def check_没碰律师陈述与图(workspace, reply):
    statements = workspace / "材料" / "律师陈述"
    assert statements.is_dir(), "起手落下的 材料/律师陈述/ 不见了"
    assert list(statements.iterdir()) == [], "归档不该往 材料/律师陈述/ 里写东西"
    data = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    titles = {m["标题"]: [n["标题"] for n in m["节点"]] for m in data["模块"]}
    assert titles == {"整地": ["松土", "施底肥"], "播种": ["选种", "下种"], "养护": ["浇水", "除草", "搭架"],
                      "收获": ["采摘", "记账"]}, "归档动了图：%s" % titles
    assert all(n["条目"] == [] for m in data["模块"] for n in m["节点"]), "归档不该写条目"


def check_没写别的文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "指南", "收件箱", "文书", "材料", "模板"], "工作区里多出了东西：%s" % names
    assert sorted(p.name for p in (workspace / "材料").iterdir()) == ["地块记录.txt", "律师陈述"], "材料/ 里多出了东西"
