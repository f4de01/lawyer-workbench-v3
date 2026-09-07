"""种子「整块不走」：一整个模块被律师宣告不适用。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按真实的破产领域目录空图起手，再摆出：承诺书已确认；模块「自行和解」整个不适用
（引擎把它在领域图里的两个节点带进案件图、逐个记一条不适用）。
案件图里没有未生成的节点了，最近动过的模块也没有剩下的节点。
供 skill "ask-loo0ng" 的用例「整块不走」。
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
    助手.引擎(ws, "not-applicable", "--module", "自行和解", "--words", "本案不走和解，自行和解那一块整个不办")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
