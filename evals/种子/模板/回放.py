"""种子「模板」：在种子「图引擎」的工作区之上，把一件官方模板放进 模板/官方/，供出件用例转换与门禁。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
官方模板原件随 loo0ng-domain 搬进 skills/loo0ng-domain/assets/ 之前在 knowledge/模板/，这里按文件名找。
工作区里没有任何案件内容。
"""
import importlib.util
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
GRAPH_SEED_REPLAY = pathlib.Path(__file__).resolve().parent.parent / "图引擎" / "回放.py"
TEMPLATE_NAME = "1-2.关于管理人印章备案的报告.docx"


def find_template() -> pathlib.Path:
    assets = REPO / "skills" / "loo0ng-domain" / "assets"
    if assets.is_dir():
        for hit in assets.rglob(TEMPLATE_NAME):
            return hit
    legacy = REPO / "knowledge" / "模板" / TEMPLATE_NAME
    if legacy.is_file():
        return legacy
    raise FileNotFoundError("找不到官方模板 %s" % TEMPLATE_NAME)


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_graph_replay", GRAPH_SEED_REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code
    target = pathlib.Path(workspace) / "模板" / "官方"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(find_template(), target / TEMPLATE_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
