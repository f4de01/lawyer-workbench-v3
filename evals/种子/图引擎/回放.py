"""种子「图引擎」：用合成小领域整份起手一个测试工作区，并写下起手会落的工作区指针块。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
起手 skill（loo0ng-setup-case）落地前，AGENTS.md / CLAUDE.md 的块由这里照 ADR-0009 机制 B 写；
起手 skill 落地后这里改为调它。工作区里没有任何案件内容。
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
ENGINE = REPO / "skills" / "loo0ng-graph" / "scripts" / "graph.py"
DOMAIN_DIR = REPO / "evals" / "领域" / "菜园"

AGENTS_MD = """# 案件工作区

- 领域：菜园
- 领域目录：{domain}
- 图：图.json；视图：图视图.md、图视图.json（都在本目录）
- 入口：loo0ng-setup-case（起手）、loo0ng-doit（办节点）、ask-loo0ng（问路）
- 本工作区对 skill 仓库只读。
"""


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    r = subprocess.run([sys.executable, str(ENGINE), "--graph", str(ws / "图.json"), "--domain", str(DOMAIN_DIR),
                        "init", "--full"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        return r.returncode
    (ws / "AGENTS.md").write_text(AGENTS_MD.format(domain=DOMAIN_DIR.as_posix()), encoding="utf-8")
    (ws / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
