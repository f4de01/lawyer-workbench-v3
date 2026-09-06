"""把 package.json 的 version 写进 .claude-plugin/plugin.json 与 .codex-plugin/plugin.json。

随 `npm run version` 在 `changeset version` 之后跑。标准库零依赖。
只改 version 那一行，保住两份清单的键序与格式。

用法：
  python scripts/sync-plugin-version.py            同步（已一致则不动文件）
  python scripts/sync-plugin-version.py --check    只检查，不一致退出码 1
  可选 --root <仓库根>，默认为本脚本所在目录的上一级（测试用）。
"""
import argparse
import json
import pathlib
import re
import sys

MANIFESTS = (
    pathlib.Path(".claude-plugin") / "plugin.json",
    pathlib.Path(".codex-plugin") / "plugin.json",
)
VERSION_LINE = re.compile(r'("version"\s*:\s*")[^"]*(")')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="只检查，不一致退出码 1")
    ap.add_argument("--root", default=None, help="仓库根，默认为脚本所在目录的上一级")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root) if args.root else pathlib.Path(__file__).resolve().parents[1]

    version = json.loads((root / "package.json").read_text(encoding="utf-8"))["version"]
    stale = []
    for rel in MANIFESTS:
        path = root / rel
        source = path.read_text(encoding="utf-8")
        current = json.loads(source).get("version")
        if current == version:
            print(f"{rel.as_posix()} 已是 {version}")
            continue
        if args.check:
            stale.append((rel, current))
            continue
        updated, n = VERSION_LINE.subn(lambda m: m.group(1) + version + m.group(2), source, count=1)
        if n != 1 or json.loads(updated).get("version") != version:
            print(f"{rel.as_posix()} 里找不到可替换的 version 行", file=sys.stderr)
            return 1
        path.write_text(updated, encoding="utf-8")
        print(f"{rel.as_posix()} {current} -> {version}")
    for rel, current in stale:
        print(f"{rel.as_posix()} 是 {current}，package.json 是 {version}。跑 python scripts/sync-plugin-version.py",
              file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
