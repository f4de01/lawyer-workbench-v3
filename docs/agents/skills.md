# Skills：登记、校验与发布

`AGENTS.md` 的结构不变量每条一行；这里是长约定：怎么登记一件 skill、改完跑什么、怎么发布。仓库结构与分发照 Matt Pocock 的 skill 体系（ADR-0009），被实测推翻的四项按 #18 的决议表。

## 目录布局

```
skills/<name>/
├── SKILL.md              # frontmatter：name、description；编排 skill 与路由另加 disable-model-invocation: true
├── agents/openai.yaml    # Codex 侧外观：interface.display_name、interface.short_description（中文进这里）；编排 skill 与路由另加 policy.allow_implicit_invocation: false
├── references/           # 正文按需指向的长材料
├── scripts/              # 标准库零依赖的 CLI
└── assets/               # 只有 loo0ng-domain 有：领域图、官方模板原件、指引手册原文（ADR-0004）
```

八件平铺在 `skills/` 下，不分桶；草稿放分支不放目录。分发清单：`.claude-plugin/plugin.json` 的 `skills` 数组逐件列路径（Claude Code 插件）；`.codex-plugin/plugin.json` 的 `skills` 是单一路径 `./skills/`（Codex 递归扫描，无需逐件登记）；`.claude-plugin/marketplace.json` 让仓库自成单插件市场。

## 命名与编码

- `name` 只用小写字母、数字、连字符，前缀 `loo0ng-` 写进 name 本身；路由是 `ask-loo0ng`。理由：skills.sh 分发链把非 ASCII 名装成 `unnamed-skill`，Codex `$` 提及只认 ASCII；两平台本身不拦（#18 项 1）。目录名与 `name` 一致。
- 中文只进三处：`agents/openai.yaml` 的 `interface.display_name` 与 `interface.short_description`（Matt 同款，本仓库用这两个），以及 `SKILL.md` frontmatter 的 `metadata.short-description`（Codex 也读，Claude Code 当自由映射不动作；可选）。`name` 与 `description` 之外的中文不进别处。
- `agents/openai.yaml` 按 ADR-0009 应机械生成；生成器随首件 skill 的实现票建立，在此之前手写，字段只有上面两个加双旗的 `policy`。
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

两平台各读各的旗，互不认对方的（#18 项 3）：两处必须同时改。

## 登记步骤（新增、改名、删除都走一遍）

1. `skills/<name>/` 落目录，按上面的布局与命名、编码规则。
2. 双旗按类型写齐。
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
```

## 测试命令

脚本层单测在 `tests/<名>/`，标准库 unittest，全部本地跑（ADR-0015）：

```bash
for d in tests/*/; do python -m unittest discover -s "$d" -p 'test_*.py' || exit 1; done
```

skill 层 eval（一个跑器两个后端 `scripts/skill-eval.py --harness claude|codex`，用例与种子在 `evals/`）随测试基建票建立，命令占位：

```bash
python scripts/skill-eval.py --harness claude    # 占位，跑器尚未落进仓库
python scripts/skill-eval.py --harness codex     # 占位
```

合入门槛 = 脚本层全绿 + 两侧 eval 全绿 + 三条校验；关票门槛 = 真实案件里 Codex 与 Claude Code 各触发一次（ADR-0015）。

## 发布

改名、改功能都是一次发布，只在开发者维护时做（ADR-0009）：`npm run changeset` 写条目，`npm run version` 合成 `CHANGELOG.md`、升 `package.json` 并同步两份插件清单的版本，提交、打 tag。流程细节在 `.changeset/README.md`。

## 分发事实（#18，2026-09-05 实测）

- junction 路线：两个 harness 都扫到；Claude Code 会话内热加载；Codex 从 junction 解析出真实路径后向上找到 `.codex-plugin/plugin.json`，把名字显示成 `loo0ng-skills:<name>`。
- 插件路线：`claude plugin marketplace add` 与 `codex plugin marketplace add … --ref` 对私有仓库都吃本机凭据，缓存是整仓库拷贝。
- 本机验证插件路线不必推分支：`claude plugin marketplace add <本仓库绝对路径>` 再 `claude plugin install loo0ng-skills@loo0ng-marketplace`，`claude -p "/loo0ng-skills:<name>"` 可触发；验完 `claude plugin uninstall` 与 `claude plugin marketplace remove loo0ng-marketplace`（#24）。
- skills.sh：`npx skills@latest add owner/repo` 只取默认分支，分支名含 `/` 时解析失败。
- junction 与插件同装时 Codex 清单同名两条、不合并；Claude Code 靠 `plugin:` 前缀分开。
