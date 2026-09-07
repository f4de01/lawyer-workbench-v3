"""种子「重出」：一个已确认的节点又出了一版。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按真实的破产领域目录空图起手，再摆出：承诺书已确认、印章备案已确认，
之后承诺书又出了 v2（法院要求改一版），于是它现在是已生成、等律师拍板，旧的确认留在历史里。
仍处于已确认的只剩印章备案。供 skill "ask-loo0ng" 的用例「已确认后重出」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws, "--empty")
    助手.办完(ws, "管理人承诺书及团队人员", "承诺书这份就这样，可以了")
    助手.办完(ws, "管理人印章备案报告", "印章备案这份可以了")
    助手.出一版(ws, "管理人承诺书及团队人员", 第几版=2)
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
