"""种子「回流」：一份律师自己长出过两个节点的案件工作区，加一份可写的破产领域图副本。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
回流只在开发会话发生（ADR-0012）：当前目录是本仓库、开发者一句话给出案件工作区的路径。
跑器把 cwd 设在临时工作区，所以这里在工作区里摆出那个开发会话看得见的三样东西：

    <工作区>/案件/         案件工作区（先照「在办中」回放一遍，再加两个律师自加节点）
    <工作区>/领域图.json   破产领域图的可写副本，回流写的就是它
    <工作区>/基线.json     回流之前的三个数：案件图的 sha256、领域图的模块数与节点数

副本而不是仓库里那份原件：eval 只生不存（ADR-0015），不能让一次跑动到 skills/ 下的领域图。
两个自加节点都挂在领域图已有的模块「接管与调查」下，标题带着本案的当事人与日期：
    乙公司甲年乙月丙日厂区接管现场情况说明   一版生成 + 律师确认 → 回流候选
    乙公司食堂承包合同解除请示               只生成没拍板 → 不是候选（判据 a，ADR-0012）
工作区里没有任何案件内容：文书与审查报告都是合成的几行字，当事人与法院一律写甲乙丙。
"""
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
ENGINE = REPO / "skills" / "loo0ng-graph" / "scripts" / "graph.py"
DOMAIN_DIR = REPO / "skills" / "loo0ng-domain" / "assets" / "破产"
RUNNER = REPO / "scripts" / "skill-eval.py"
EVALS = REPO / "evals" / "用例"


def load_runner():
    """借跑器自己的 replay_seed 把「在办中」摊进 案件/：元文件名单只该有一份（scripts/skill-eval.py）。"""
    spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


模块 = "接管与调查"
已确认 = "乙公司甲年乙月丙日厂区接管现场情况说明"
已生成 = "乙公司食堂承包合同解除请示"

# 一节点一目录，每版一份文书加一份同名审查报告（ADR-0007）。内容只求形状对，不是真的文书。
DOCS = {
    "文书/%s/%s-v1.md" % (已确认, 已确认):
        "# %s\n\n甲年乙月丙日，管理人到乙公司厂区现场接管，清点厂房一栋、仓库两间，"
        "由丙移交钥匙一串。现场未见第三人占用。\n" % 已确认,
    "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt\n\n"
        "## 存疑点\n\n无\n\n## 待律师裁定\n\n无\n\n## 版式门禁\n\n通过\n\n"
        "## 时限\n\n本节点无明示时限\n" % 已确认,
    "文书/%s/%s-v1.md" % (已生成, 已生成):
        "# %s\n\n乙公司与丙签订的食堂承包合同，管理人拟解除，报请裁定。\n" % 已生成,
    "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt\n\n"
        "## 存疑点\n\n合同原件没在材料里\n\n## 待律师裁定\n\n解除还是继续履行\n\n"
        "## 版式门禁\n\n通过\n\n## 时限\n\n本节点无明示时限\n" % 已生成,
}


def run(cmd, cwd) -> int:
    r = subprocess.run([sys.executable, *[str(c) for c in cmd]], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    case = ws / "案件"
    case.mkdir(parents=True, exist_ok=True)
    load_runner().replay_seed(EVALS, "在办中", case)

    for rel, text in DOCS.items():
        path = case / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # 律师自己长出的两个节点：id 由引擎生成，回流时原样带进领域图（ADR-0012）。
    engine = [ENGINE, "--domain", DOMAIN_DIR]
    steps = [
        [*engine, "add-node", "--module", 模块, "--title", 已确认],
        [*engine, "generate", "--node", 已确认, "--doc", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--source", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认)],
        [*engine, "confirm", "--node", 已确认, "--words", "现场情况说明这份可以了，就这样定"],
        [*engine, "add-node", "--module", 模块, "--title", 已生成],
        [*engine, "generate", "--node", 已生成, "--doc", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--source", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成)],
    ]
    for cmd in steps:
        code = run(cmd, case)
        if code != 0:
            return code

    shutil.copy2(DOMAIN_DIR / "领域图.json", ws / "领域图.json")
    # 基线让断言不必硬写「72 个节点」：下一次回流让领域图长大，这份种子跟着长，用例不动。
    domain = json.loads((ws / "领域图.json").read_text(encoding="utf-8"))
    基线 = {
        "案件图sha256": hashlib.sha256((case / "图.json").read_bytes()).hexdigest(),
        "领域图sha256": hashlib.sha256((ws / "领域图.json").read_bytes()).hexdigest(),
        "领域图模块数": len(domain["模块"]),
        "领域图节点数": sum(len(m["节点"]) for m in domain["模块"]),
    }
    (ws / "基线.json").write_text(json.dumps(基线, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
