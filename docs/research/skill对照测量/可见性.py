#!/usr/bin/env python3
"""对照测量专用：临时控制本机 agent skill 目录里能看见哪几件 loo0ng skill。

三条腿要分得开，只靠提示词不行——2026-09-13 实测：一条本该"裸"的腿自己跑去
`Get-Content ~/.agents/skills/loo0ng-doit/SKILL.md` 把编排 skill 的正文读了进来。
模型够得到盘上的一切，所以变量只能在盘上控制。

三个状态：
    off   七件全部移走            → A 腿（真裸）
    ref   只留四件参考 skill      → B 腿、C 腿
    all   全部还原                → 跑完必须回到这里

移走不是删除：整条 junction 搬到 ~/.agents/_skills-off/，`--state all` 原样搬回。
只认指向本仓库 skills/ 的链接，别处来的条目一概不碰。零第三方依赖。

用法：
    python 可见性.py --show
    python 可见性.py --state off
    python 可见性.py --state ref
    python 可见性.py --state all
"""

import argparse
import os
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
LIVE = HOME / ".agents" / "skills"
PARK = HOME / ".agents" / "_skills-off"
REPO_SKILLS = Path(__file__).resolve().parents[3] / "skills"


def classify():
    """按 frontmatter 把仓库里的 skill 分成编排（含路由）与参考两类。"""
    orchestration, reference = [], []
    for d in sorted(REPO_SKILLS.iterdir()):
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            continue
        head = skill_md.read_text(encoding="utf-8", errors="replace")[:2000]
        (orchestration if "disable-model-invocation: true" in head else reference).append(d.name)
    return orchestration, reference


def link_target(p):
    try:
        return os.readlink(str(p))
    except OSError:
        return None


def locate(name):
    """返回 (当前位置, 是不是指向本仓库的链接)；不存在则 (None, False)。"""
    for root in (LIVE, PARK):
        p = root / name
        if p.exists() or link_target(p):
            tgt = link_target(p)
            ours = bool(tgt) and str(REPO_SKILLS).lower() in tgt.replace("/", "\\").lower()
            return p, ours
    return None, False


def move(name, dest_root):
    src, ours = locate(name)
    if src is None:
        return "缺失"
    if src.parent == dest_root:
        return "已在位"
    if not ours:
        return "不是本仓库的链接，跳过"
    dest_root.mkdir(parents=True, exist_ok=True)
    dst = dest_root / name
    if dst.exists() or link_target(dst):
        return "目标已存在，跳过"
    os.rename(str(src), str(dst))
    return "搬到 " + dest_root.name


def show(orchestration, reference):
    print("活目录 {}".format(LIVE))
    print("寄存处 {}".format(PARK))
    print()
    for kind, names in (("编排/路由", orchestration), ("参考", reference)):
        for n in names:
            p, ours = locate(n)
            where = "不在" if p is None else ("可见" if p.parent == LIVE else "已移走")
            print("{:<8}{:<20}{}".format(kind, n, where))


def main():
    ap = argparse.ArgumentParser(description="临时控制 loo0ng skill 在 agent 目录里的可见性")
    ap.add_argument("--state", choices=["off", "ref", "all"], help="off=七件全移走；ref=只留四件参考；all=全部还原")
    ap.add_argument("--show", action="store_true", help="只看现状")
    args = ap.parse_args()

    if not REPO_SKILLS.is_dir():
        print("找不到仓库的 skills/：{}".format(REPO_SKILLS), file=sys.stderr)
        return 2
    orchestration, reference = classify()

    if args.show or not args.state:
        show(orchestration, reference)
        if not args.state:
            print("\n（要改状态给 --state off|ref|all）")
        return 0

    plan = {
        "off": [(n, PARK) for n in orchestration + reference],
        "ref": [(n, PARK) for n in orchestration] + [(n, LIVE) for n in reference],
        "all": [(n, LIVE) for n in orchestration + reference],
    }[args.state]

    for name, dest in plan:
        print("{:<20}{}".format(name, move(name, dest)))
    print()
    show(orchestration, reference)
    if args.state != "all":
        print("\n>>> 跑完记得 `python 可见性.py --state all` 还原。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
