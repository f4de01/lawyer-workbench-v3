"""把 package.json 的 version 写进两份插件清单与 package-lock.json。

随 `npm run version` 在 `changeset version` 之后跑。标准库零依赖。
只改 version 那一行（lock 是根与 packages[""] 两行），保住键序与格式。

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
LOCK = pathlib.Path("package-lock.json")
VERSION_LINE = re.compile(r'("version"\s*:\s*")[^"]*(")')
# lock 里 "version" 出现上百次，VERSION_LINE 在它身上会打中第一个依赖。只认两处：
# 根那行（顶层缩进两格，全文件独一份）与 packages[""] 那行（缩进六格，但它是
# "packages" 里的头一个条目，所以从那个锚点起算第一处）。
LOCK_ROOT_VERSION = re.compile(r'^(  "version": ")[^"]*(")', re.M)
LOCK_SELF_VERSION = re.compile(r'^(      "version": ")[^"]*(")', re.M)
LOCK_ANCHOR = '''  "packages": {
    "": {
'''


def sync_lock(source, version):
    """只改根与 packages[""] 两处 version，别的包一个字不动；改不动就回 None。"""
    head, anchor, rest = source.partition(LOCK_ANCHOR)
    if not anchor:
        return None
    head, n_root = LOCK_ROOT_VERSION.subn(lambda m: m.group(1) + version + m.group(2), head, count=1)
    rest, n_self = LOCK_SELF_VERSION.subn(lambda m: m.group(1) + version + m.group(2), rest, count=1)
    if n_root != 1 or n_self != 1:
        return None
    updated = head + anchor + rest
    before, after = json.loads(source), json.loads(updated)
    if after.get("version") != version or after["packages"][""].get("version") != version:
        return None
    others = {k: v for k, v in before["packages"].items() if k != ""}
    if {k: v for k, v in after["packages"].items() if k != ""} != others:
        return None
    return updated


def lock_versions(source):
    data = json.loads(source)
    return data.get("version"), data["packages"][""].get("version")


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
    lock_path = root / LOCK
    if not lock_path.exists():
        print(f"{LOCK.as_posix()} 不存在，跳过")
    else:
        source = lock_path.read_text(encoding="utf-8")
        current = lock_versions(source)
        if current == (version, version):
            print(f"{LOCK.as_posix()} 已是 {version}")
        elif args.check:
            stale.append((LOCK, "/".join(str(c) for c in current)))
        else:
            updated = sync_lock(source, version)
            if updated is None:
                print(f"{LOCK.as_posix()} 里找不到可替换的两处 version", file=sys.stderr)
                return 1
            lock_path.write_text(updated, encoding="utf-8")
            print(f"{LOCK.as_posix()} {'/'.join(str(c) for c in current)} -> {version}")
    for rel, current in stale:
        print(f"{rel.as_posix()} 是 {current}，package.json 是 {version}。跑 python scripts/sync-plugin-version.py",
              file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
