"""种子「自加节点」：律师自己加了一个领域图里没有的节点，又把一个节点改了短标题。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按真实的破产领域目录空图起手，再摆出：承诺书出了一版还没拍板，随后被律师改标题为「承诺书」
（id 不变，所以领域图上那句时限仍按 id 查得出）；模块「接受指定与报备」下多一个
领域图里没有的节点「补充材料说明」，未生成。供 skill "ask-loo0ng" 的用例「律师自加节点与改标题」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws, "--empty")
    助手.出一版(ws, "管理人承诺书及团队人员")
    助手.引擎(ws, "add-node", "--module", "接受指定与报备", "--title", "补充材料说明")
    助手.引擎(ws, "rename-node", "--node", "管理人承诺书及团队人员", "--title", "承诺书")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
