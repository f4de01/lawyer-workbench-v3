"""种子「收件箱」：在种子「图引擎」的工作区之上再放一个待归档的收件箱。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
收件箱/ 里的文件由跑器按种子接口原样拷进工作区；这里只复用「图引擎」的回放把 图.json 与工作区指针块落下。
工作区里没有任何案件内容。
"""
import importlib.util
import pathlib
import sys

GRAPH_SEED_REPLAY = pathlib.Path(__file__).resolve().parent.parent / "图引擎" / "回放.py"


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_graph_replay", GRAPH_SEED_REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main(workspace)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
