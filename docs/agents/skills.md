# Skills：登记、校验与发布

`AGENTS.md` 的结构不变量每条一行；这里是长约定：怎么登记一件 skill、改完跑什么、怎么发布。仓库结构与分发照 Matt Pocock 的 skill 体系（ADR-0009），被实测推翻的四项按 #18 的决议表。

## 目录布局

```
skills/<name>/
├── SKILL.md              # frontmatter：name、description；编排 skill 与路由另加 disable-model-invocation: true
├── agents/openai.yaml    # Codex 侧外观：interface.display_name、interface.short_description（中文进这里）；编排 skill 与路由另加 policy.allow_implicit_invocation: false
├── references/           # 正文按需指向的长材料
├── scripts/              # 标准库零依赖的 CLI；只有 loo0ng-to-docx 例外（python-docx、PyMuPDF，ADR-0006）
└── assets/               # 只有 loo0ng-domain 有：领域图、官方模板原件、指引手册原文（ADR-0004）
```

八件平铺在 `skills/` 下，不分桶；草稿放分支不放目录。分发清单：`.claude-plugin/plugin.json` 的 `skills` 数组逐件列路径（Claude Code 插件）；`.codex-plugin/plugin.json` 的 `skills` 是单一路径 `./skills/`（Codex 递归扫描，无需逐件登记）；`.claude-plugin/marketplace.json` 让仓库自成单插件市场。

## 命名与编码

- `name` 只用小写字母、数字、连字符，前缀 `loo0ng-` 写进 name 本身；路由是 `ask-loo0ng`。理由：skills.sh 分发链把非 ASCII 名装成 `unnamed-skill`，Codex `$` 提及只认 ASCII；两平台本身不拦（#18 项 1）。目录名与 `name` 一致。
- 中文显示名与短描述只写在 `SKILL.md` frontmatter 的 `metadata.display-name` 与 `metadata.short-description`（后者 Codex 也读，Claude Code 当自由映射不动作）；`agents/openai.yaml` 的 `interface.display_name` / `interface.short_description` 由生成器从这两处抄出，不手写。`name` 与 `description` 之外的中文不进别处。
- `agents/openai.yaml` 由 `python scripts/gen-openai-yaml.py` 机械生成（ADR-0009；#26 随首件 skill 建立）：字段只有上面两个，编排 skill 与路由按 frontmatter 的 `disable-model-invocation: true` 推出 `policy.allow_implicit_invocation: false`。`--check` 只比对不写，任一份不同步即退出码 1。
- `SKILL.md`、`agents/openai.yaml` 与所有 PowerShell 以外的文本文件不带 BOM：带 BOM 的 `SKILL.md` 会让 Codex 静默跳过整个根目录（#20）。PowerShell 5.1 脚本必须带 UTF-8 BOM，否则中文注释按 ANSI 读会撕坏语法（#18）。
- 全仓禁破折号（U+2014）。连接号 U+2013 用于数字区间，不在此列。
- frontmatter 的 `description` 加双引号：不加引号时 ` #` 起 YAML 注释，两平台都把其后的字截掉（#24 空壳验证时发现）。

## description 两套

- User-invoked（编排 skill 与路由）：一句人话，功能加后面跟什么，去掉触发词。
- Model-invoked（参考 skill）：四要素齐全（功能、触发、负向、邻居互指），第三人称、中文、触发词放最前、不超过 1,024 字。
- 跨 skill 只用「调用 skill "loo0ng-xxx"」一种句式，散文里用中文显示名；改名于是成为纯机械替换。

## 双旗

| 类型 | `SKILL.md` frontmatter | `agents/openai.yaml` |
| --- | --- | --- |
| 编排 skill、路由 | `disable-model-invocation: true` | `policy.allow_implicit_invocation: false` |
| 参考 skill | 不写 | 不写 `policy` |

两平台各读各的旗，互不认对方的（#18 项 3）：`SKILL.md` 的旗是源，`openai.yaml` 的 `policy` 由生成器推出，重跑生成器即同步。

## 登记步骤（新增、改名、删除都走一遍）

1. `skills/<name>/` 落目录，按上面的布局与命名、编码规则。
2. 双旗按类型写齐：`SKILL.md` 里写旗与 `metadata.display-name` / `short-description`，再跑 `python scripts/gen-openai-yaml.py` 生成 `agents/openai.yaml`。
3. `.claude-plugin/plugin.json` 的 `skills` 数组加（或改、删）`./skills/<name>`。
4. `README.md` 的 User-invoked 或 Model-invoked 组加（或改、删）一行。
5. 动到任一入口（`loo0ng-setup-case`、`loo0ng-doit`、`ask-loo0ng`）时，改 `ask-loo0ng` 自持的入口表（ADR-0005）。
6. 重跑 relink：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1`。改内容不用重跑，只有改名、增删要。
7. `npm run changeset` 写一条 changeset。
8. 跑下面的校验与测试。

## 三条校验命令

`claude plugin validate .` 有 `marketplace.json` 时只验它、不验 `plugin.json`；`plugin.json` 在 `--strict` 下因根 `CLAUDE.md` 的 warning 必败（Matt 自己的插件同样），所以拆三条（#18 项 2）：

```bash
claude plugin validate . --strict                    # marketplace.json，严格
claude plugin validate skills --strict               # 全部 skill 的 frontmatter，严格
claude plugin validate .claude-plugin/plugin.json    # plugin.json，非严格
```

## 其他检查

```bash
# 破折号：期望无输出
git ls-files -z | xargs -0 grep -l -I -P '\x{2014}'

# BOM：PowerShell 以外的文本文件不得带 BOM，期望无输出
git ls-files -z | grep -z -v '\.ps1$' | xargs -0 grep -l -I $'^\xEF\xBB\xBF'

# BOM：每个 .ps1 首三字节须为 ef bb bf
for f in scripts/*.ps1; do printf '%s ' "$f"; head -c 3 "$f" | od -An -tx1; done

# 三处版本一致
npm run check-plugin-version

# agents/openai.yaml 与 SKILL.md frontmatter 同步，期望退出码 0
python scripts/gen-openai-yaml.py --check
```

## 测试命令

脚本层单测在 `tests/<名>/`，标准库 unittest，全部本地跑（ADR-0015）：

```bash
for d in tests/*/; do python -m unittest discover -s "$d" -p 'test_*.py' || exit 1; done
```

`tests/loo0ng-to-docx/` 要 Word COM，缺了 fail 不 skip（ADR-0006、ADR-0015）：`test_gate.py` 每件门禁起一次 Word（约 7 秒，16 例约两分钟）；`test_templates.py` 是 19 件官方模板各出一份占位件过门禁的回归，约一分半，只在开发侧跑，不进 Codex 的 30 秒 shell。别在门禁测试跑的同时另起 Word 出件，两件门禁同时跑会互相关掉对方的实例。

skill 层 eval：一个跑器两个后端，用例与种子在 `evals/`（ADR-0015，#25）：

```bash
python scripts/skill-eval.py --harness claude                 # Claude Code 侧，走 claude -p
python scripts/skill-eval.py --harness codex                  # Codex 侧，走 codex exec
python scripts/skill-eval.py --harness claude --case 冒烟     # 只跑一个用例；--case 可重复
python scripts/skill-eval.py --harness codex --runs 3         # 怀疑抖动时多跑几次
python scripts/skill-eval.py --harness claude --evals evals/自检   # 跑器自检用例（故意失败），不进门槛
```

Codex 侧提示词经 stdin 送入（`PROMPT` 位置是 `-`）：PATH 上的 `codex` 是 npm 的 `.cmd` 垫片，cmd.exe 会把参数里第一个换行之后的字吞掉，多行提示词（如带一段稿子的「出一版」用例）只剩第一行（#28）。其他参数：`--max-turns N`、`--timeout 秒` 覆盖用例里的值；`--keep` 跑完不删工作区，只为排障。退出码 0 全绿、1 有红、2 用法或用例配置错。结果只打印不进仓库。从 Claude Code 会话内跑 `--harness claude` 不用自己去环境变量：跑器已去掉 `CLAUDECODE` 两项并带上 `MSYS_NO_PATHCONV=1`。

### `evals/` 目录

```
evals/
├── 用例/<名>/           # 合入门槛跑的用例，目录名即用例名
│   ├── 提示词.md        # 律师原本会打的那一句
│   ├── 用例.json        # 见下
│   └── 断言.py          # check_ 开头的函数各是一条断言，签名 (workspace: Path, reply: str)，assert 判真伪
├── 自检/<名>/           # 只测跑器自己的用例（如 故意失败），同格式，用 --evals evals/自检 跑
├── 种子/<场景>/         # 收件箱/ 等直接拷进工作区的东西 + 回放.py + 状态.md；「图引擎」种子（#26）在起手 skill 落地前自己写工作区指针块
└── 领域/<领域名>/领域图.json   # 脚本层用的合成小领域「菜园」（ADR-0015，#26），tests/loo0ng-graph 全用它跑；领域/说明.md 一段说明
```

ADR-0015「目录名保持 ASCII」只指 `tests/`、`evals/` 两个顶层；其下按仓库习惯用中文（ADR 自己的例子 `evals/种子/<场景>/` 即如此），`--case 冒烟` 直接传中文名。

`用例.json` 的键（多一个未知键即报错）：

| 键 | 含义 |
| --- | --- |
| `种子` | `evals/种子/` 下的场景名，本票允许为空 |
| `skill` | 编排 skill 名，可空。Claude Code 侧拼成 `/<skill> <提示词>`，按 junction 路线（`link-skills.ps1`）的名字，插件路线的 `/loo0ng-skills:<skill>` 不在此列；Codex 侧用替身提示词「读 `~/.agents/skills/<skill>/SKILL.md` 并照做：<提示词>」，测的是正文不是触发，触发另由人工实测与完成定义那一次覆盖。带 skill 的用例必须有 `说明` |
| `回复正则` | 对最后一条回复做 `re.search`，可空；报红时断言名是「回复正则」 |
| `回合上限` | Claude Code 侧交给 `--max-turns`；Codex 侧数 JSONL 流里工具类 item（命令、改文件、MCP、搜索），超了杀进程树。默认 30 |
| `超时秒` | 单次调用的墙钟上限，超了杀进程树。默认 300 |
| `允许工具` | Claude Code 侧 `--allowedTools` 的列表（如 `["Bash(python *)"]`）；权限模式固定 acceptEdits。Codex 侧靠沙箱，不需要 |
| `Codex沙箱` | Codex 侧 `codex exec -s` 的值：`workspace-write`（默认）或 `danger-full-access`。沙箱里起不来 Word COM（0x80070520 登录会话不存在）、`python` 也不在沙箱 PATH 上，所以要跑门禁的用例用后者（#28）。Claude Code 侧不看这个键 |
| `说明` | 一句话，含用例的局限；带 skill 时必填，写明替身提示词的局限 |

每次运行：在 `%TEMP%` 下建临时工作区 → 回放种子 → 调 harness（cwd 即工作区）→ 回复正则 → 逐条断言 → 删工作区（超时、超回合、断言抛错都删）。断言报红时给出函数名与 assert 的消息。

种子接口（实现随起手票）：`evals/种子/<场景>/` 里除 `回放.py` 与 `状态.md` 之外的条目原样拷进工作区，再在工作区里跑 `python 回放.py <工作区>`；起手（`loo0ng-setup-case`）、引擎 CLI、归档脚本都写在回放里，跑器不另定回放格式。

Windows 上工作区用 `os.mkdir` 而不用 `tempfile.mkdtemp`：后者建的目录只有 SYSTEM、Administrators、OWNER RIGHTS 三条 ACE，Codex 沙箱账户写进去的文件本用户读不了也删不了。

合入门槛 = 脚本层全绿 + 两侧 eval 全绿 + 三条校验；关票门槛 = 真实案件里 Codex 与 Claude Code 各触发一次（ADR-0015）。

## 发布

改名、改功能都是一次发布，只在开发者维护时做（ADR-0009）：`npm run changeset` 写条目，`npm run version` 合成 `CHANGELOG.md`、升 `package.json` 并同步两份插件清单的版本，提交、打 tag。流程细节在 `.changeset/README.md`。

## 分发事实（#18，2026-09-05 实测）

- junction 路线：两个 harness 都扫到；Claude Code 会话内热加载；Codex 从 junction 解析出真实路径后向上找到 `.codex-plugin/plugin.json`，把名字显示成 `loo0ng-skills:<name>`。
- 插件路线：`claude plugin marketplace add` 与 `codex plugin marketplace add … --ref` 对私有仓库都吃本机凭据，缓存是整仓库拷贝。
- 本机验证插件路线不必推分支：`claude plugin marketplace add <本仓库绝对路径>` 再 `claude plugin install loo0ng-skills@loo0ng-marketplace`，`claude -p "/loo0ng-skills:<name>"` 可触发；验完 `claude plugin uninstall` 与 `claude plugin marketplace remove loo0ng-marketplace`（#24）。
- skills.sh：`npx skills@latest add owner/repo` 只取默认分支，分支名含 `/` 时解析失败。
- junction 与插件同装时 Codex 清单同名两条、不合并；Claude Code 靠 `plugin:` 前缀分开。
