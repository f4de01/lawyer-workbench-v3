#!/usr/bin/env python3
"""把实测包打成给另一台机器的 zip。

兜底用的 skill 副本不入库（仓库里只该有一份领域图，AGENTS.md 结构不变量 5），
所以每次打包现从 skills/ 拷一份进去，顺手剔掉 __pycache__。

    python docs/实测/打包.py mac-20260907 [输出目录]

输出目录默认是仓库的上一级，免得 zip 自己躺进仓库里。
"""
import shutil
import sys
import tempfile
from pathlib import Path

仓库根 = Path(__file__).resolve().parents[2]


def 打包(包名: str, 输出目录: Path) -> Path:
    包目录 = Path(__file__).resolve().parent / 包名
    if not (包目录 / "AGENTS.md").is_file():
        raise SystemExit(f"{包目录} 不像一个实测包（没有 AGENTS.md）")

    源 = 仓库根 / "skills"
    if not 源.is_dir():
        raise SystemExit(f"找不到 {源}")

    with tempfile.TemporaryDirectory() as 临时:
        暂存 = Path(临时) / 包名
        shutil.copytree(
            包目录, 暂存,
            ignore=shutil.ignore_patterns("__pycache__", "skills-兜底", ".DS_Store"),
        )
        shutil.copytree(
            源, 暂存 / "skills-兜底",
            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
        )
        输出目录.mkdir(parents=True, exist_ok=True)
        产物 = shutil.make_archive(
            str(输出目录 / f"实测包-{包名}"), "zip",
            root_dir=临时, base_dir=包名,
        )
    return Path(产物)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    出 = Path(sys.argv[2]) if len(sys.argv) > 2 else 仓库根.parent
    产物 = 打包(sys.argv[1], 出)
    print(f"{产物}  {产物.stat().st_size / 1024 / 1024:.2f} MB")
