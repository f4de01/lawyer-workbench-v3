#!/usr/bin/env python3
"""发布路径上的两道闸门，外加从 CHANGELOG 抽出这一版的发布说明。标准库零依赖。

`.github/workflows/release.yml` 逐步调它；YAML 只管 checkout、git 与 gh，判断都在这里，
这样在开发机上原样跑得动、也测得动（`tests/release/`）。任一条不成立即退出码 1，
workflow 随之停在结算前或结算后，不会推出一个半拉的版本。

  preflight   结算前：agents/openai.yaml 同步、版本三处对齐、有待结算的 changeset、工作树干净
  postflight  结算后：版本真的变了、三处仍对齐、changeset 都被吃掉了、CHANGELOG 有这一节、tag 还没有
  notes       把 CHANGELOG.md 里某一版那一节抽成一个文件（Release 正文）
  pending     打印待结算的 changeset 份数（干跑那条路靠它决定要不要临时造一份）

版本三处对齐那一条跑的就是 `npm run check-plugin-version` 背后的那个检查器
（`scripts/sync-plugin-version.py --check`），直接调脚本是为了这里零依赖、也测得动。

用法：
  python scripts/release.py preflight [--root <仓库根>]
  python scripts/release.py postflight --previous <结算前的版本> [--root <仓库根>]
  python scripts/release.py notes --out <文件> [--version <版本>] [--root <仓库根>]
  python scripts/release.py pending [--root <仓库根>]
退出码：0 全过；1 有一条不成立；2 用法错。
"""
import argparse
import json
import pathlib
import subprocess
import sys

LF = chr(10)


def 版本(根):
    return json.loads((根 / "package.json").read_text(encoding="utf-8"))["version"]


def 待结算的(根):
    目录 = 根 / ".changeset"
    if not 目录.is_dir():
        return []
    return sorted(p.name for p in 目录.glob("*.md") if p.name.lower() != "readme.md")


def 跑脚本(根, 名, *args):
    """用同一个解释器跑 scripts/ 下的检查器，输出直接落进 CI 日志。"""
    return subprocess.run([sys.executable, str(根 / "scripts" / 名), *args], cwd=str(根)).returncode


def git输出(根, *args):
    r = subprocess.run(["git", "-C", str(根), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "")


def 读CHANGELOG(根):
    """返回 CHANGELOG.md 的正文；没有这个文件就 None，由调用处报成自己那套「停在这里」。"""
    p = 根 / "CHANGELOG.md"
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def 抽一节(文, 号):
    """CHANGELOG.md 里 `## <版本>` 到下一个 `## ` 之间的正文，去掉首尾空行；没有就 None。"""
    行 = 文.splitlines()
    起 = None
    for i, l in enumerate(行):
        if l.strip() == "## " + 号:
            起 = i
            break
    if 起 is None:
        return None
    正文 = []
    for l in 行[起 + 1:]:
        if l.startswith("## "):
            break
        正文.append(l)
    while 正文 and not 正文[0].strip():
        正文.pop(0)
    while 正文 and not 正文[-1].strip():
        正文.pop()
    return LF.join(正文) if 正文 else None


def preflight(根, 允许没有changeset=False):
    坏 = []
    if 跑脚本(根, "gen-openai-yaml.py", "--check") != 0:
        坏.append("agents/openai.yaml 与 SKILL.md frontmatter 不同步：先跑 python scripts/gen-openai-yaml.py")
    if 跑脚本(根, "sync-plugin-version.py", "--check") != 0:
        坏.append("版本三处不齐（= npm run check-plugin-version）：先跑 python scripts/sync-plugin-version.py")
    单子 = 待结算的(根)
    if 单子:
        print("待结算的 changeset " + str(len(单子)) + " 份：" + "、".join(单子))
    elif 允许没有changeset:
        # 干跑那条路：刚发完版 .changeset 空着也该让发布机器自己跑一遍，不红在这上面
        print(".changeset/ 下没有待结算的，--allow-no-changeset 放行")
    else:
        坏.append(".changeset/ 下没有待结算的 changeset，没什么可发的")
    码, 脏 = git输出(根, "status", "--porcelain")
    if 码 != 0:
        坏.append("git status 跑不动，这不像一个仓库")
    elif 脏.strip():
        坏.append("工作树不干净，结算前必须是干净的：" + LF + 脏.rstrip())
    return 坏


def postflight(根, 上一版):
    坏 = []
    新 = 版本(根)
    if 新 == 上一版:
        坏.append("版本还是 " + 新 + "，changeset version 没结算出新版本")
    else:
        print("版本 " + 上一版 + " -> " + 新)
    if 跑脚本(根, "sync-plugin-version.py", "--check") != 0:
        坏.append("结算后版本三处不齐（scripts/sync-plugin-version.py --check）：npm run version 里的同步那一步没跑成")
    剩 = 待结算的(根)
    if 剩:
        坏.append(".changeset/ 下还剩 " + "、".join(剩) + "，没被结算掉")
    文 = 读CHANGELOG(根)
    if 文 is None:
        坏.append("没有 CHANGELOG.md 这个文件")
    elif not 抽一节(文, 新):
        坏.append("CHANGELOG.md 里没有 " + 新 + " 这一节")
    码, _ = git输出(根, "rev-parse", "-q", "--verify", "refs/tags/v" + 新)
    if 码 == 0:
        坏.append("tag v" + 新 + " 已经在了，这一版发过了")
    return 坏


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("动作", choices=["preflight", "postflight", "notes", "pending"])
    ap.add_argument("--root", default=None, help="仓库根，默认为脚本所在目录的上一级")
    ap.add_argument("--previous", default=None, help="postflight：结算前的版本号")
    ap.add_argument("--version", dest="指定版本", default=None, help="notes：要抽哪一版，默认 package.json 里的")
    ap.add_argument("--out", default=None, help="notes：写到哪个文件")
    ap.add_argument("--allow-no-changeset", action="store_true",
                    help="preflight：干跑时用，.changeset/ 空着也放行")
    args = ap.parse_args(argv)
    根 = pathlib.Path(args.root) if args.root else pathlib.Path(__file__).resolve().parents[1]

    if args.动作 == "pending":
        print(str(len(待结算的(根))))
        return 0

    if args.动作 == "notes":
        if not args.out:
            ap.error("notes 要 --out")
        号 = args.指定版本 or 版本(根)
        文 = 读CHANGELOG(根)
        if 文 is None:
            print("没有 CHANGELOG.md 这个文件，抽不出发布说明", file=sys.stderr)
            return 1
        节 = 抽一节(文, 号)
        if not 节:
            print("CHANGELOG.md 里没有 " + 号 + " 这一节，抽不出发布说明", file=sys.stderr)
            return 1
        出 = pathlib.Path(args.out)
        出.parent.mkdir(parents=True, exist_ok=True)
        出.write_text(节 + LF, encoding="utf-8")
        print("已写出 " + str(出) + "（" + 号 + "，" + str(len(节.splitlines())) + " 行）")
        return 0

    if args.动作 == "preflight":
        坏 = preflight(根, args.allow_no_changeset)
    else:
        if not args.previous:
            ap.error("postflight 要 --previous <结算前的版本>")
        坏 = postflight(根, args.previous)

    for 一条 in 坏:
        print(一条, file=sys.stderr)
    if 坏:
        print(args.动作 + " 不过，停在这里", file=sys.stderr)
        return 1
    print(args.动作 + " 全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
