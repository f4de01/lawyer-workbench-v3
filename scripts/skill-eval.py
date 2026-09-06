#!/usr/bin/env python3
"""skill 层 eval 跑器：一个脚本两个后端，判据是临时工作区里的文件与回复的形状。

依据 ADR-0015。Python 标准库、零依赖；只约束开发者，不随 skill 包分发。

用法：
  python scripts/skill-eval.py --harness claude [--case 名 ...] [--runs N] [--max-turns N] [--timeout 秒]
  python scripts/skill-eval.py --harness codex  ...
  可选 --evals <用例根>（默认 evals/用例）、--keep（跑完不删工作区，只为排障）。

用例是一个目录 evals/用例/<名>/，三个文件：
  提示词.md   律师原本会打的那一句
  用例.json   种子（evals/种子/<场景>，可空）、skill（编排 skill 名，可空）、回复正则（可空）、
              回合上限、超时秒、允许工具（Claude Code 侧 --allowedTools）、说明
  断言.py     每个 check_ 开头的函数是一条断言，签名 (workspace: Path, reply: str)，
              用 assert 判真伪，函数名即报红时给出的断言名

每次运行：建临时工作区 → 回放种子 → 调 harness → 回复正则 → 逐条断言 → 删工作区（finally）。
Claude Code 侧走 claude -p（--max-turns 由它自己数；MSYS_NO_PATHCONV=1 防 Git Bash 改写 /名）；
Codex 侧走 codex exec --json，回合数按流里的工具类 item 数，超上限即杀进程树。
Codex 侧编排 skill 用替身提示词（读 ~/.agents/skills/<名>/SKILL.md 并照做），测的是正文不是触发。
结果只打印不进仓库。退出码：0 全绿；1 有红；2 用法或用例配置错误。
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

DEFAULT_EVALS = pathlib.Path("evals") / "用例"
SEEDS_DIRNAME = "种子"
DEFAULT_MAX_TURNS = 30
DEFAULT_TIMEOUT = 300
CASE_KEYS = {"种子", "skill", "回复正则", "回合上限", "超时秒", "允许工具", "说明"}
CASE_REQUIRED = ("种子", "回复正则")
SEED_META_FILES = ("回放.py", "状态.md")
CODEX_TOOL_ITEMS = {"command_execution", "file_change", "mcp_tool_call", "web_search"}
CODEX_STAND_IN = "读 ~/.agents/skills/{skill}/SKILL.md 并照做：{prompt}"


class EvalError(Exception):
    """用例或跑器配置的错误（退出码 2），不是 skill 跑红。"""


@dataclass
class Case:
    name: str
    path: pathlib.Path
    prompt: str
    seed: str
    skill: str
    reply_re: str
    max_turns: Optional[int]
    timeout: Optional[int]
    allowed_tools: List[str]
    checks: List[Tuple[str, Callable]]


@dataclass
class Invocation:
    status: str  # ok | timeout | max_turns | error
    reply: str
    turns: int
    detail: str = ""


@dataclass
class Failure:
    name: str
    message: str


@dataclass
class RunResult:
    case: str
    run: int
    seconds: float
    turns: int
    failures: List[Failure] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


# ---------------------------------------------------------------- 参数

def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="skill-eval.py", description=__doc__.splitlines()[0])
    ap.add_argument("--harness", required=True, choices=("claude", "codex"))
    ap.add_argument("--evals", default=str(DEFAULT_EVALS), help="用例根目录，默认 evals/用例")
    ap.add_argument("--case", action="append", default=[], help="只跑这些用例（目录名），可重复")
    ap.add_argument("--runs", type=positive_int, default=1, help="每用例跑几次，默认 1")
    ap.add_argument("--max-turns", type=positive_int, default=None, help="回合上限，覆盖用例里的值")
    ap.add_argument("--timeout", type=positive_int, default=None, help="单次超时秒数，覆盖用例里的值")
    ap.add_argument("--keep", action="store_true", help="跑完不删临时工作区（排障用）")
    return ap.parse_args(argv)


def positive_int(text):
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("须为正整数")
    return n


# ---------------------------------------------------------------- 用例

def load_assertions(path: pathlib.Path) -> List[Tuple[str, Callable]]:
    sys.dont_write_bytecode = True  # 别在用例目录里留 __pycache__
    module_name = "skill_eval_assertions_" + secrets.token_hex(4)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001
        raise EvalError("%s 加载失败：%s: %s" % (path, type(e).__name__, e)) from e
    checks = [(name, fn) for name, fn in vars(module).items()
              if name.startswith("check_") and callable(fn)]
    if not checks:
        raise EvalError("%s 里没有 check_ 开头的函数" % path)
    return checks


def load_case(path: pathlib.Path) -> Case:
    path = pathlib.Path(path)
    for filename in ("提示词.md", "用例.json", "断言.py"):
        if not (path / filename).is_file():
            raise EvalError("用例 %s 缺 %s" % (path.name, filename))
    try:
        meta = json.loads((path / "用例.json").read_text(encoding="utf-8"))
    except ValueError as e:
        raise EvalError("用例 %s 的 用例.json 不是合法 JSON：%s" % (path.name, e)) from e
    if not isinstance(meta, dict):
        raise EvalError("用例 %s 的 用例.json 顶层须是对象" % path.name)
    unknown = sorted(set(meta) - CASE_KEYS)
    if unknown:
        raise EvalError("用例 %s 的 用例.json 有未知键：%s" % (path.name, "、".join(unknown)))
    missing = [k for k in CASE_REQUIRED if k not in meta]
    if missing:
        raise EvalError("用例 %s 的 用例.json 缺键：%s" % (path.name, "、".join(missing)))
    if meta.get("skill") and not (meta.get("说明") or "").strip():
        raise EvalError("用例 %s 带 skill 就须有 说明：写明 Codex 侧用替身提示词、测的是正文不是触发" % path.name)
    reply_re = meta.get("回复正则") or ""
    try:
        re.compile(reply_re)
    except re.error as e:
        raise EvalError("用例 %s 的回复正则无效：%s" % (path.name, e)) from e
    return Case(
        name=path.name,
        path=path,
        prompt=(path / "提示词.md").read_text(encoding="utf-8").strip(),
        seed=meta.get("种子") or "",
        skill=meta.get("skill") or "",
        reply_re=reply_re,
        max_turns=meta.get("回合上限"),
        timeout=meta.get("超时秒"),
        allowed_tools=list(meta.get("允许工具") or []),
        checks=load_assertions(path / "断言.py"),
    )


def discover_cases(root: pathlib.Path, names: List[str]) -> List[Case]:
    root = pathlib.Path(root)
    if not root.is_dir():
        raise EvalError("用例根目录不存在：%s" % root)
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "用例.json").is_file())
    if names:
        by_name = {p.name: p for p in dirs}
        absent = [n for n in names if n not in by_name]
        if absent:
            raise EvalError("找不到用例：%s（在 %s 下）" % ("、".join(absent), root))
        dirs = [by_name[n] for n in names]
    if not dirs:
        raise EvalError("%s 下没有用例" % root)
    return [load_case(p) for p in dirs]


# ---------------------------------------------------------------- 工作区与种子

def make_workspace(case_name: str) -> pathlib.Path:
    """临时目录用 os.mkdir 而不用 tempfile.mkdtemp：Windows 上 mkdtemp 建的目录只有 SYSTEM、
    Administrators 与 OWNER RIGHTS 三条 ACE，Codex 沙箱账户在里面写的文件本用户读不了；
    直接 mkdir 会继承 %TEMP% 的 ACL，本用户自带一条。Codex 的 -o 输出目录同理，也走这里。"""
    base = pathlib.Path(tempfile.gettempdir())
    while True:
        path = base / ("skill-eval-%s-%s" % (case_name, secrets.token_hex(4)))
        try:
            os.mkdir(path)
        except FileExistsError:
            continue
        return path


def remove_workspace(path: pathlib.Path) -> None:
    def on_error(func, target, exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if path.exists():
        shutil.rmtree(path, onerror=on_error)


def replay_seed(evals_root: pathlib.Path, seed: str, workspace: pathlib.Path) -> None:
    """种子接口：evals/种子/<场景>/ 里除 回放.py 与 状态.md 之外的东西拷进工作区，
    再在工作区里跑 python 回放.py <工作区>（起手 + 引擎 CLI + 归档脚本都写在回放里）。"""
    # 回放在工作区里跑（cwd 是工作区），evals 根默认是相对路径，须先转绝对。
    seed_dir = (pathlib.Path(evals_root).resolve().parent / SEEDS_DIRNAME / seed)
    if not seed_dir.is_dir():
        raise EvalError("种子不存在：%s" % seed_dir)
    for entry in seed_dir.iterdir():
        if entry.name in SEED_META_FILES:
            continue
        target = workspace / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)
    replay = seed_dir / "回放.py"
    if replay.is_file():
        r = subprocess.run([sys.executable, str(replay), str(workspace)], cwd=str(workspace),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise EvalError("种子 %s 回放失败（退出码 %d）：\n%s" % (seed, r.returncode, (r.stderr or r.stdout).strip()))


# ---------------------------------------------------------------- harness

def harness_executable(harness: str) -> List[str]:
    exe = shutil.which(harness)
    if not exe:
        raise EvalError("PATH 里找不到 %s" % harness)
    return [exe]


def harness_env(base: Dict[str, str]) -> Dict[str, str]:
    env = dict(base)
    # 从 Claude Code 会话内起 claude -p 要去掉这两个，否则被当成嵌套会话拒绝。
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    # Git Bash 会把 "/loo0ng-xxx" 这样的参数改写成 C:/Program Files/Git/loo0ng-xxx。
    env["MSYS_NO_PATHCONV"] = "1"
    return env


def build_prompt(harness: str, case: Case) -> str:
    if not case.skill:
        return case.prompt
    if harness == "codex":
        return CODEX_STAND_IN.format(skill=case.skill, prompt=case.prompt)
    return "/%s %s" % (case.skill, case.prompt)


def build_command(harness: str, exe: List[str], prompt: str, workspace: pathlib.Path, *,
                  max_turns: int, last_path: pathlib.Path, allowed_tools: List[str]) -> List[str]:
    if harness == "claude":
        cmd = [*exe, "-p", prompt, "--output-format", "json", "--max-turns", str(max_turns),
               "--permission-mode", "acceptEdits", "--no-session-persistence"]
        if allowed_tools:
            cmd += ["--allowedTools", *allowed_tools]
        return cmd
    return [*exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write",
            "-C", str(workspace), "--json", "-o", str(last_path), prompt]


def kill_tree(proc: subprocess.Popen) -> None:
    """杀整棵进程树。Windows 上先 taskkill /T；它偶尔会卡住（本机见过 RPC 超时 60 秒，#26），
    等 2 秒等不到就放弃它、只杀直接子进程，跑器自己不能跟着卡死。"""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        killer = subprocess.Popen(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            killer.wait(timeout=2)
        except subprocess.TimeoutExpired:
            killer.kill()
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def invoke(harness: str, case: Case, workspace: pathlib.Path, prompt: str, max_turns: int, timeout: int) -> Invocation:
    exe = harness_executable(harness)
    out_dir = make_workspace(case.name + "-out")
    try:
        last_path = out_dir / "last.md"
        cmd = build_command(harness, exe, prompt, workspace, max_turns=max_turns,
                            last_path=last_path, allowed_tools=case.allowed_tools)
        if harness == "claude":
            return _invoke_claude(cmd, workspace, timeout)
        return _invoke_codex(cmd, workspace, max_turns, timeout, last_path)
    finally:
        remove_workspace(out_dir)


def _popen(cmd: List[str], workspace: pathlib.Path) -> subprocess.Popen:
    return subprocess.Popen(cmd, cwd=str(workspace), env=harness_env(os.environ),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")


def _invoke_claude(cmd: List[str], workspace: pathlib.Path, timeout: int) -> Invocation:
    proc = _popen(cmd, workspace)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        return Invocation("timeout", "", 0, "超过 %d 秒，已杀进程树" % timeout)
    try:
        result = json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return Invocation("error", "", 0, "claude 没有输出 JSON 结果（退出码 %d）：%s" % (
            proc.returncode, (stderr or stdout).strip()[-800:]))
    turns = int(result.get("num_turns") or 0)
    if result.get("subtype") == "error_max_turns":
        return Invocation("max_turns", "", turns, "; ".join(result.get("errors") or ["回合上限"]))
    if result.get("is_error") or result.get("subtype") != "success":
        return Invocation("error", str(result.get("result") or ""), turns,
                          "claude 报错：%s" % "; ".join(result.get("errors") or [str(result.get("subtype"))]))
    return Invocation("ok", str(result.get("result") or ""), turns)


def _invoke_codex(cmd: List[str], workspace: pathlib.Path, max_turns: int, timeout: int,
                  last_path: pathlib.Path) -> Invocation:
    proc = _popen(cmd, workspace)
    state = {"turns": 0, "capped": False, "last_message": "", "error": ""}

    def read_stream():
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            item = event.get("item") or {}
            if event.get("type") == "error" and event.get("message"):
                state["error"] = str(event["message"])  # 用量上限之类的错只在流里，stderr 没有
            if event.get("type") == "item.started" and item.get("type") in CODEX_TOOL_ITEMS:
                state["turns"] += 1
                if state["turns"] > max_turns and not state["capped"]:
                    state["capped"] = True
                    kill_tree(proc)
                    return
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                state["last_message"] = item.get("text") or ""

    reader = threading.Thread(target=read_stream, daemon=True)
    reader.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(proc)
    reader.join(timeout=10)
    stderr = proc.stderr.read()
    proc.stdout.close()
    proc.stderr.close()
    if timed_out:
        return Invocation("timeout", "", state["turns"], "超过 %d 秒，已杀进程树" % timeout)
    if state["capped"]:
        return Invocation("max_turns", "", state["turns"], "工具调用超过回合上限 %d，已杀进程树" % max_turns)
    reply = last_path.read_text(encoding="utf-8") if last_path.is_file() else state["last_message"]
    if proc.returncode != 0:
        detail = state["error"] or stderr.strip()[-800:]
        return Invocation("error", reply, state["turns"], "codex 退出码 %d：%s" % (proc.returncode, detail))
    return Invocation("ok", reply, state["turns"])


# ---------------------------------------------------------------- 判定

def evaluate(case: Case, workspace: pathlib.Path, inv: Invocation) -> List[Failure]:
    if inv.status != "ok":
        return [Failure("harness:" + inv.status, inv.detail)]
    failures = []
    if case.reply_re and not re.search(case.reply_re, inv.reply, re.S):
        failures.append(Failure("回复正则", "/%s/ 不匹配回复：%s" % (case.reply_re, inv.reply.strip()[:200])))
    for name, fn in case.checks:
        try:
            fn(workspace, inv.reply)
        except AssertionError as e:
            failures.append(Failure(name, str(e) or "断言失败"))
        except Exception as e:  # noqa: BLE001
            failures.append(Failure(name, "断言抛出 %s: %s" % (type(e).__name__, e)))
    return failures


def run_case(case: Case, opts, invoke: Callable = invoke) -> List[RunResult]:
    max_turns = opts.max_turns or case.max_turns or DEFAULT_MAX_TURNS
    timeout = opts.timeout or case.timeout or DEFAULT_TIMEOUT
    prompt = build_prompt(opts.harness, case)
    results = []
    for run in range(1, opts.runs + 1):
        workspace = make_workspace(case.name)
        started = time.monotonic()
        try:
            if case.seed:
                replay_seed(pathlib.Path(opts.evals), case.seed, workspace)
            inv = invoke(opts.harness, case, workspace, prompt, max_turns, timeout)
            failures = evaluate(case, workspace, inv)
        finally:
            if opts.keep:
                print("  工作区保留：%s" % workspace)
            else:
                remove_workspace(workspace)
        results.append(RunResult(case.name, run, time.monotonic() - started, inv.turns, failures))
    return results


def main(argv=None, invoke: Callable = invoke, out=sys.stdout) -> int:
    opts = parse_args(argv)
    try:
        cases = discover_cases(pathlib.Path(opts.evals), opts.case)
    except EvalError as e:
        print("错误：%s" % e, file=sys.stderr)
        return 2
    results: List[RunResult] = []
    for case in cases:
        try:
            case_results = run_case(case, opts, invoke=invoke)
        except EvalError as e:
            print("错误：%s" % e, file=sys.stderr)
            return 2
        for r in case_results:
            verdict = "PASS" if r.passed else "FAIL"
            print("[%s] %s #%d %s (%.1fs, %d 回合)" % (opts.harness, r.case, r.run, verdict, r.seconds, r.turns), file=out)
            for f in r.failures:
                print("    ✗ %s: %s" % (f.name, f.message), file=out)
        results += case_results
    passed = sum(1 for r in results if r.passed)
    print("通过 %d / 失败 %d / 共 %d" % (passed, len(results) - passed, len(results)), file=out)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
