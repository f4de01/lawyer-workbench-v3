"""空图没给领域的断言：律师只说了「图先空着」，没说这案子是哪个领域，起手要先问，不许自己填一个。

签名 (workspace: Path, reply: str)。

来路是律师 0.1.0 现场报的那一次（随 #103 一并修）：agent 问「本案采用哪种起手图？目前发现『破产』领域种子」，
律师答「空图，自己逐步建节点」，agent 就拿本机唯一那个种子当默认起了一张破产领域的空图。
本机有哪些种子是安装的事，案子是哪个领域是律师的事。领域名填错了，整案的前方、惰性带入与
时限都挂在错的领域目录上，而起手一案一次（ADR-0007），改它要换一个空目录从头来。
"""
import re

六格 = ["材料", "指南", "模板", "文书"]
收件箱六件 = 6


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。

    #105 实测 Codex 也会把 uv 的缓存落成不带点的 `uv-cache`，所以 `uv-` 开头的一并忽略：
    它是 harness 自备解释器留下的，不是 skill 的产物。七份同名小函数逐字相同，改一处就一起改。
    """
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_没起图(workspace, reply):
    """起手图三选一里的领域没定，图就不该落盘：定错了改它要换一个空目录从头来。"""
    for name in ("图.json", "图视图.md", "图视图.json"):
        assert not (workspace / name).exists(), "领域还没问就把 %s 落了盘" % name


def check_一格没建(workspace, reply):
    """顺序是死的：六格与起手图是同一条命令，起手图没定，一格也不该建（SKILL.md 第 1–2 步）。"""
    建了 = [rel for rel in 六格 if (workspace / rel).exists()]
    assert not 建了, "领域还没问就建了格：%s" % "、".join(建了)
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == ["收件箱"], "工作区里多出了东西：%s" % names


def check_收件箱原封不动(workspace, reply):
    """归档是第 3 步，在起手图之后：这一问没答之前，收件箱里那六件一件都不该搬。"""
    留着 = [p.name for p in (workspace / "收件箱").iterdir() if not _is_harness_noise(p.name)]
    assert len(留着) == 收件箱六件, "收件箱里本该原封不动的六件现在是 %d 件：%s" % (len(留着), 留着)


def check_问了领域是哪个(workspace, reply):
    assert "领域" in reply, "回复里一个「领域」字都没有，这一问没问出来：\n%s" % reply
    assert re.search(r"[？?]", reply), "回复里没有问号：领域名只能由律师给，得问他，不是报一句就往下走：\n%s" % reply


def check_没报成已经起好了(workspace, reply):
    """报「已建」「已起手」就是把没定的事当定了：这一问没答之前，收尾三段不该出现。"""
    坏 = [x for x in ("六格建齐", "三份都落了盘", "已建空图", "已起手") if x in reply]
    assert not 坏, "领域还没定就报了起手完成：%s\n%s" % ("、".join(坏), reply)
