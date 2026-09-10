"""逐节点回流·未拍板的断言：回显了归属提案，律师没拍板，活图一个字节不变。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402

自加, 核心, 默认模块 = 助手.自加, 助手.自加的核心词, 助手.自加所在模块


def check_确认照常落了(workspace, reply):
    """归属那一问是确认之后的事，问归问，这一句确认本身照落（ADR-0010 一句话即落）。"""
    助手.校验确认落了(workspace, 自加)


def check_律师一句话之前活图逐字不变(workspace, reply):
    助手.校验活图逐字不变(workspace, "律师还没就归属说过一句话，未拍板不写（ADR-0019）")


def check_回复里问了归属(workspace, reply):
    assert re.search(r"领域图|活图", reply), \
        "确认的是领域图里没有的节点，收尾该问一次它在领域图里该归哪儿：\n%s" % reply
    assert 核心 in reply, "那一问里没提是哪个节点：\n%s" % reply


def check_回显了默认模块(workspace, reply):
    assert 默认模块 in reply, \
        "那一问要带两个默认值，模块继承案件图里的「%s」（ADR-0019）：\n%s" % (默认模块, reply)


def check_回显了去案件化后的标题(workspace, reply):
    """提案里的标题得是去掉当事人与日期之后那个写法，不能把案件里的原标题原样端上去。"""
    剩下 = reply.replace(自加, "")
    命中 = [m.group(0) for m in re.finditer(r"[^\s，。、；：「」（）()\"'`*#]*补种[^\s，。、；：「」（）()\"'`*#]*", 剩下)]
    干净 = [t for t in 命中 if "乙家" not in t and "甲年" not in t]
    assert 干净, "回复里没有去案件化后的标题提案（原标题之外一个带「补种」的写法都没有）：\n%s" % reply[:600]
