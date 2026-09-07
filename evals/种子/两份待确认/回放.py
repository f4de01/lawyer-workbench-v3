"""种子「两份待确认」：两份文书同时等律师拍板。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按真实的破产领域目录整份起手，再摆出：承诺书已确认，印章备案与银行账户备案各出了一版、都没拍板。
印章备案在领域图上带时限句、银行账户备案没有；模块「接受指定与报备」里排在它们之前的
「管理人工作计划」未生成、没有时限。供 skill "ask-loo0ng" 的用例「两份同时待确认」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws, "--full")
    助手.办完(ws, "管理人承诺书及团队人员", "承诺书这份就这样，可以了")
    助手.出一版(ws, "管理人印章备案报告")
    助手.出一版(ws, "管理人银行账户备案报告")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
