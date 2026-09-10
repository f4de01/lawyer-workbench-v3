"""逐节点回流·改归属的断言：律师改了两个默认值，按他说的写。签名 (workspace: Path, reply: str)。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402

自加, 核心 = 助手.自加, 助手.自加的核心词
默认模块 = 助手.自加所在模块   # 律师明说了别归这里
律师说的模块 = "播种"
律师说的标题 = "补种登记"


def check_确认照常落了(workspace, reply):
    助手.校验确认落了(workspace, 自加)


def check_按律师说的模块与标题写(workspace, reply):
    助手.校验回流进活图的那个节点(workspace, 核心, 律师说的模块, 律师说的标题)


def check_没按默认值写(workspace, reply):
    养护 = [m for m in 助手.活图(workspace)["模块"] if m["标题"] == 默认模块]
    assert 养护, "活图里该还有模块「%s」" % 默认模块
    多出的 = [n["标题"] for n in 养护[0]["节点"] if 核心 in n["标题"]]
    assert not 多出的, "律师说了别归「%s」，那里却多出了节点：%s" % (默认模块, 多出的)


def check_活图只多出那一个节点(workspace, reply):
    助手.校验活图只多出那一个(workspace)


def check_id与案件图一致(workspace, reply):
    节点 = 助手.校验回流进活图的那个节点(workspace, 核心, 律师说的模块, 律师说的标题)[1]
    assert 节点["id"] == 助手.案件节点(workspace, 自加)[1]["id"], \
        "改归属不改 id：换新 id 本案的前方就多出一个与自己重复的节点，实际 %r" % 节点["id"]


def check_没给时限句(workspace, reply):
    节点 = 助手.校验回流进活图的那个节点(workspace, 核心, 律师说的模块, 律师说的标题)[1]
    assert "时限" not in 节点, \
        "律师侧新增的节点不给时限句（ADR-0019），实际带了 %r" % 节点.get("时限")


def check_案件图里那个节点没被改名(workspace, reply):
    模块, _ = 助手.案件节点(workspace, 自加)
    assert 模块["标题"] == 默认模块, \
        "改的是领域图里的归属，案件图里那个节点不动，现在却在「%s」下" % 模块["标题"]
