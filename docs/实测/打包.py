#!/usr/bin/env python3
"""把实测包打成给另一台机器的 zip。

兜底用的 skill 副本不入库（仓库里只该有一份领域图，AGENTS.md 结构不变量 5），
所以每次打包现从 skills/ 拷一份进去，顺手剔掉 __pycache__。

文本文件一律转成 LF：开发机是 Windows，工作区里的 SKILL.md 是 CRLF；原样打进 zip
拷到 ~/.agents/skills 之后，name 字段末尾会多一个 CR，Codex 认到的名字就带尾巴
（2026-09-07 实测：六件里四件中招）。docx 之类的二进制不动。

    python docs/实测/打包.py mac-20260907 [输出目录]

输出目录默认是仓库的上一级，免得 zip 自己躺进仓库里。
"""
import shutil
import sys
import tempfile
from pathlib import Path

仓库根 = Path(__file__).resolve().parents[2]

# 要转成 LF 的文本后缀；这之外（docx、png…）一概按二进制原样拷。
文本后缀 = {".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt", ".applescript", ".gitattributes"}


def 转成LF(根: Path) -> int:
    """把树里的文本文件就地转成 LF；返回改了几个。带 CRLF 的 SKILL.md 会让 name 多一个尾巴。"""
    CR = chr(13).encode()
    LF = chr(10).encode()
    CRLF = CR + LF
    改了 = 0
    for f in 根.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in 文本后缀 and f.name != ".gitattributes":
            continue
        原 = f.read_bytes()
        if CR not in 原:
            continue
        f.write_bytes(原.replace(CRLF, LF).replace(CR, LF))
        改了 += 1
    return 改了


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
        改了 = 转成LF(暂存)
        print(f"换行统一为 LF：改了 {改了} 个文本文件")
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
