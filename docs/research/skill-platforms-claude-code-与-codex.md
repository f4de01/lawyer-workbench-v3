# Claude Code 与 Codex 的 skill 分发与调用控制现状

> **写于** 2026-09-04，对应 issue #11（`wayfinder:research`），供 #7「路由的定位机制」、#9「编排层与参考层的 skill 清单」、#10「图存档与可视化接口」参考。
> **来源等级**：只读官方一手来源——Claude Code 文档（code.claude.com / platform.claude.com）、Anthropic `anthropics/skills` 仓库、OpenAI Codex 文档（`developers.openai.com/codex/*` 现 308 跳转到 `learn.chatgpt.com/docs/*`，二者同为官方站）、`openai/codex` 仓库源码与 issue、MCP 规范与 `modelcontextprotocol/ext-apps`、OpenAI Apps SDK 文档。未克隆任何外部仓库，全部经网页读取。所有 URL 访问日期均为 2026-09-04，下文不再逐条重复。
> **带入的已知事实**（不重推）：2.0 在 Codex 侧用 `~/.agents/skills` 下的 junction 挂 skill、用 MCP server 出图（`docs/3.0-handoff.md` §6）；Windows 下 symlink 双注册（`.claude/skills -> ../skills`、`.agents/skills -> ../skills`）曾表现为空目录（`docs/research/legal-skills-与本项目交叉对比.md` §1.1）。
> **标注**：凡官方文档未直接写明、由源码或 issue 推断的，标 **推测**。GitHub issue 是用户报告，不是官方声明，只作旁证。
> **红线**：不含任何案件材料。

---

## 0. 结论速览

| 问题 | Claude Code | Codex |
| --- | --- | --- |
| skill 目录 | `~/.claude/skills/`、`.claude/skills/`（cwd 向上到仓库根 + 嵌套子目录懒加载）、企业 managed 目录、插件 `<plugin>/skills/` | `.agents/skills/`（cwd 向上到仓库根）、`~/.agents/skills/`、`/etc/codex/skills/`、内置 SYSTEM |
| 认不认对方目录 | 不读 `.agents/skills`（无文档，有开放 feature request） | 不读 `.claude/skills`（无文档、源码无此路径） |
| 入口文件 | `SKILL.md` | `SKILL.md`（大小写敏感，推测） |
| 读哪些 frontmatter | 全部扩展字段（`disable-model-invocation`、`user-invocable`、`allowed-tools`、`context`、`paths`… 共 20 余项） | 只读 `name`、`description`、`metadata.short-description`，其余静默忽略 |
| 「只许人触发」 | frontmatter `disable-model-invocation: true`：描述**不进上下文**，模型不能调，只能 `/name` | `<skill>/agents/openai.yaml` 里 `policy.allow_implicit_invocation: false`：模型不隐式选用，`$name` 显式提及仍可 |
| 「只许模型触发」 | `user-invocable: false` | 无等价物 |
| 同名冲突 | enterprise > personal > project；插件永远带 `plugin:` 前缀不冲突 | 不合并、不去重，两者都列出；`$name` 歧义时不匹配 |
| 上下文预算 | 列表占模型上下文 1%，单条 description+when_to_use 截到 1,536 字 | 列表占 2%（未知窗口时 8,000 字），`skills.max_context_tokens` 上限 10,000 |
| 插件形态 | `.claude-plugin/plugin.json` + `skills/`、`.mcp.json`、`agents/`、`hooks/`；marketplace `.claude-plugin/marketplace.json` | `.codex-plugin/plugin.json` + `skills/`、`.mcp.json`；marketplace `.agents/plugins/marketplace.json` |
| 共同遵循的规范 | agentskills.io（Claude Code 自称「扩展该标准」） | agentskills.io（Codex 文档「建立在开放 agent skills 标准之上」） |
| 会话内渲染 MCP App UI | 不渲染（不在官方宿主矩阵；MCP 文档无 UI 条目） | 默认不渲染（`EnableMcpApps` 特性旗标默认 false） |

---

## 1. (a) 发现与加载

### 1.1 Claude Code

**扫描位置**（[skills 页](https://code.claude.com/docs/en/skills)）：

| 级别 | 路径 |
| --- | --- |
| Enterprise | managed settings 目录下 `.claude/skills/<name>/`（Linux 示例 `/etc/claude-code/.claude/skills/`；Windows 对应路径文档未给，**推测**为 `C:\Program Files\ClaudeCode\.claude\skills\`） |
| Personal | `~/.claude/skills/<name>/SKILL.md` |
| Project | `.claude/skills/<name>/SKILL.md` |
| Plugin | `<plugin>/skills/<name>/SKILL.md` |

- 项目级「从启动目录的 `.claude/skills/` 以及**每一级父目录直到仓库根**加载」。启动目录**以下**的嵌套 `.claude/skills/` 不在启动时加载，「第一次读或改该子目录内文件时才加载」，之前不出现在补全里也不能按名调用。
- `--add-dir` / `/add-dir` / SDK `additionalDirectories` 会加载该目录的 `.claude/skills/` 与 `.claude/commands/`；但 **`settings.json` 里的 `permissions.additionalDirectories` 只授文件权限、不加载 skill**（同名不同效）。
- 会话内热更新：监视 `~/.claude/skills/`、项目 `.claude/skills/` 与 add-dir 内的 `.claude/skills/`，改 `SKILL.md` 即生效；新建顶层 skills 目录要重启。
- **symlink**：「enterprise、personal、project 位置下的 `<skill-name>` 条目可以是指向磁盘他处目录的 symlink。Claude Code 跟随 symlink 读取目标的 `SKILL.md`；同一目标从多处可达时只加载一次。」插件侧另有规则（见 1.3）。文档没有任何关于 Windows junction 的说法——**未找到**。
- 保留名：`synced`（任何大小写）保留给 claude.ai 同步的 skill。

**优先级**（同页，原文）：「Across levels, enterprise overrides personal, and personal overrides project.」即个人 `~/.claude/skills/deploy` **压过**项目 `.claude/skills/deploy`，与 settings 的惯常方向相反。插件 skill 走 `plugin-name:skill-name` 命名空间，「不会与其他级别冲突」。同名 skill 与 `.claude/commands/*.md` 并存时 skill 优先。嵌套目录同名时两者都保留，嵌套的得到目录限定名 `apps/web:deploy`。

**命令与 skill 已合并**：「Custom commands have been merged into skills.」`.claude/commands/deploy.md` 与 `.claude/skills/deploy/SKILL.md` 都产生 `/deploy`；命令文件支持同样的 frontmatter，但忽略 `name` 与 `paths`。

**进入上下文的内容**：常规会话「skill 描述进上下文，完整内容只在调用时加载」；预加载给子代理的 skill 例外，「完整内容在启动时注入」。列表预算「占模型上下文窗口 1%」，溢出时「从最少调用的 skill 开始丢描述」，名字永远保留；单条 `description` + `when_to_use` 截到 1,536 字（`skillListingMaxDescChars` 可调，`skillListingBudgetFraction` / `SLASH_COMMAND_TOOL_CHAR_BUDGET` 调总预算）。调用后内容作为一条消息驻留后续轮次，不重读文件；自动压缩后按每个 skill 最近一次调用保留前 5,000 token、合计 25,000 token 重挂。

**参数替换**：`$ARGUMENTS`、`$ARGUMENTS[N]`、`$N`（**`$0` 是第一个参数**）、`arguments:` 声明的 `$name`、`${CLAUDE_SKILL_DIR}`、`${CLAUDE_PROJECT_DIR}`、`${CLAUDE_PLUGIN_ROOT}`、`${CLAUDE_PLUGIN_DATA}`、`${CLAUDE_SESSION_ID}`。`${CLAUDE_SKILL_DIR}` 在正文与 `allowed-tools` 的 Bash 规则两处都替换，「同一变量两处都用，可让 skill 运行自带脚本而不弹权限提示」。

### 1.2 Codex

**扫描位置**（[build-skills](https://learn.chatgpt.com/docs/build-skills.md)，表按优先级顺序列出）：

| 范围 | 路径 |
| --- | --- |
| REPO | `$CWD/.agents/skills`、`$CWD/../.agents/skills`、`$REPO_ROOT/.agents/skills`——「从当前工作目录向上到仓库根的每一级目录都扫 `.agents/skills`」 |
| USER | `$HOME/.agents/skills` |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | 随 Codex 内置 |

- 源码 `codex-rs/core/src/skills.rs` 的 `SkillScope { User, Repo, System, Admin }` 与此对应。`$CODEX_HOME/skills`（`~/.codex/skills`）只作内置 SYSTEM skill 的落盘缓存（`codex-rs/skills/src/lib.rs` `install_system_skills()` 装到 `CODEX_HOME/skills/.system`）。issue [#22590](https://github.com/openai/codex/issues/22590)「支持 `.codex/skills` 作为发现目录」被关闭为 not planned——**`~/.codex/skills` 不是用户发现根**。
- **不读 `.claude/skills`**：官方文档与 skills crate 源码均无此路径。
- 目录布局：`SKILL.md`（必需）+ `scripts/`、`references/`、`assets/`（可选）+ `agents/openai.yaml`（可选，外观与依赖）。
- symlink：文档原文「Codex supports symlinked skill folders and follows the symlink target when scanning these locations.」但 issue [#11314](https://github.com/openai/codex/issues/11314)「`.agents/skills` 本身是 symlink 时不加载」关闭为 not planned；[#8400](https://github.com/openai/codex/issues/8400)「Windows 下 symlink 或 junction 的 skill 不被检测」（标签 `windows-os`）关闭为 #8369 的重复。**推测**：跟随的是 `.agents/skills` 真实目录**之内**的 symlink 条目，`.agents/skills` **根本身**为链接则不保证；Windows 上 junction 有用户报告失败。
- 递归扫描：issue [#22275](https://github.com/openai/codex/issues/22275) 报告 skill 包内嵌套的 `SKILL.md` 被当独立 skill 注册——**推测**扫描是递归的且无深度限制。入口文件名大小写敏感（issue [#20637](https://github.com/openai/codex/issues/20637)，**推测**）。

**优先级 / 去重**（原文）：「If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors.」源码 `codex-rs/skills/src/selection.rs` 按 `path_to_skills_md` 去重，`$name` 匹配到多个候选时直接跳过（`if skill_count != 1 || connector_count != 0 { continue; }`）。范围间的具体覆盖规则**未核实**——文档只承诺不合并。

**进入上下文的内容**（原文）：「ChatGPT and Codex start with each skill's name and description, then load the full `SKILL.md` instructions when they decide to use that skill.」「In Codex, the initial list also includes each skill's file path. …this list uses at most 2% of the model's context window, or 8,000 characters when the context window is unknown. If many skills are installed, Codex shortens skill descriptions first. For large skill sets, Codex may omit some skills from the initial list and show a warning.」配置项 `skills.max_context_tokens`「显式值上限 10,000 token」（[config-reference](https://learn.chatgpt.com/docs/config-file/config-reference.md)、`codex-rs/config/src/skills_config.rs`）。

**调用方式**：「In Codex CLI or the IDE extension, run `/skills` or type `$` to mention a skill.」隐式调用「当任务匹配 skill `description` 时 Codex 可自行选用」。源码 `mentions.rs` 支持 `$name` 与 `[$name](skill://path)` 两种形式；`normalize_host_skill_path()` 把 `\` 换成 `/`（Windows 路径归一化）。**没有 `codex skills` 子命令、没有 `--skill` 旗标**（[developer-commands](https://learn.chatgpt.com/docs/developer-commands.md?surface=cli)）。

**启停**：`~/.codex/config.toml` 的 `[[skills.config]] path = "…/SKILL.md"  enabled = false`（改后重启）；源码还支持 `name =` 选择器、`skills.bundled.enabled`、`skills.include_instructions`。没有 skill 相关环境变量；`AGENTS_HOME` 未见文档。

### 1.3 插件 vs 裸 skill 目录

**Claude Code**（[plugins-reference](https://code.claude.com/docs/en/plugins-reference)、[plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)）：

- 清单 `.claude-plugin/plugin.json`，必填 `name`；组件路径字段 `skills`、`commands`、`agents`、`hooks`、`mcpServers`、`lspServers` 等。`skills` 字段是**追加**（「默认 `skills/` 目录总会扫描」），`commands`/`agents` 等是**替换**默认目录。
- 插件可带 MCP server（`.mcp.json` 或内联），启用插件即自动启动，工具名 `mcp__plugin_<plugin>_<server>__<tool>`；`${CLAUDE_PLUGIN_ROOT}` 在 `command`/`args`/`env`/`url` 里替换。
- marketplace：仓库根 `.claude-plugin/marketplace.json`，必填 `name`、`owner`、`plugins[]`；source 支持相对路径、GitHub、git URL、git-subdir、npm、zip、command。本地目录 marketplace：`claude plugin marketplace add ./my-marketplace --scope project`。
- 插件 skill **总带** `plugin:` 前缀，「原 `/skill-name` 与插件副本同时可用」；**不受** `skillOverrides` 影响。
- **裸 skill 目录升格**：「在 skill 文件夹里加 `.claude-plugin/plugin.json`，它就作为名为 `<name>@skills-dir` 的插件加载，可以捆绑 agents、hooks、MCP servers。」项目级需先过 workspace trust；限制：只从会话主工作目录的 `.claude/skills/` 加载（不向上走）、MCP server 逐个审批、后台 monitor 不加载。
- **插件内 symlink**（Windows 唯一直接相关的官方句子）：装入缓存时，指向插件自身目录内的 symlink 保留为相对链接；指向同一 marketplace 内他处的被解引用复制；指向 marketplace 之外的「出于安全跳过」。「On Windows, use `mklink /D` from an elevated Command Prompt or enable Developer Mode.」

**Codex**（[plugins](https://learn.chatgpt.com/docs/plugins)、[build-plugins](https://learn.chatgpt.com/docs/build-plugins.md)、[openai/plugins README](https://raw.githubusercontent.com/openai/plugins/main/README.md)）：

- 清单 `.codex-plugin/plugin.json`：`name`、`version`、`description`、`skills: "./skills/"`，可加 `apps`；MCP 走 `.mcp.json`（camelCase `mcpServers`）。
- 默认 marketplace 在 `.agents/plugins/marketplace.json`；CLI `codex plugin add|list|remove`、`codex plugin marketplace add|list|upgrade|remove`；TUI `/plugins`。
- `openai/skills` 仓库 README 自述已弃用，改用 `openai/plugins`；安装用内置 `$skill-installer`（无 `npx skills add`）。
- 源码 `SkillMetadata` 带 `plugin_id` / `remote_plugin_id`，说明插件内 skill 与裸 skill 是同一数据结构加来源标记。

### 1.4 Agent Skills 开放规范（两边的公共交集）

- Claude Code：「Claude Code skills follow the [Agent Skills](https://agentskills.io) open standard… Claude Code extends the standard with additional features like invocation control, subagent execution, and dynamic context injection.」规范只允许六个 frontmatter 字段：**`name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`**；claude.ai 上传 / Skills API / `package_skill.py` 遇到其他字段报硬错误（`Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name`）。
- Codex：「Skills build on the [open agent skills standard](https://agentskills.io).」并链接 `agentskills.io/specification`。
- `anthropics/skills` 仓库 `spec/agent-skills-spec.md` 已改为指向 `agentskills.io/specification`；本次 **未能抓取** agentskills.io 页面（连接反复关闭），规范原文条款**未核实**，以上字段清单以 Claude Code 文档的转述为准。
- 校验硬限（[platform 最佳实践](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 与 Codex `parser.rs`/`interface.rs` 一致）：`name` ≤ 64 字、小写字母数字连字符；`description` 非空 ≤ 1,024 字。

---

## 2. (b) `disable-model-invocation` 的现行语义与 Codex 等价物

### 2.1 Claude Code

[frontmatter 参考](https://code.claude.com/docs/en/skills#frontmatter-reference) 的调用矩阵（原文）：

| Frontmatter | 用户可调 | Claude 可调 | 何时进上下文 |
| --- | --- | --- | --- |
| （默认） | Yes | Yes | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | **Description not in context**, full skill loads when you invoke |
| `user-invocable: false` | No | Yes | Description always in context, full skill loads when invoked |

- 另处原文：「**Hide individual skills** by adding `disable-model-invocation: true` to their frontmatter. This removes the skill from Claude's context entirely.」强制执行：「If Claude tries anyway, Claude Code blocks the call and instructs it not to reproduce the deploy steps another way, so expect Claude to suggest running `/deploy` yourself.」
- 附带效果：「也阻止该 skill 被预加载进子代理」；「自 v2.1.196 起，也阻止定时任务以该 skill 为 prompt 触发」。
- `user-invocable`（拼写以此为准，文档中无 `invokable`）：`false` 时「从 `/` 菜单隐藏，输入 `/name` 也不运行」，「Claude 仍可调用；要让 Claude 也不能通过 Skill tool 调用，设 `disable-model-invocation: true`」。
- 不改文件的替代：settings `skillOverrides`，四态 `on` / `name-only` / `user-invocable-only` / `off`（`/skills` 菜单标 `user-only`）；写入 `.claude/settings.local.json`；**插件 skill 不受此影响**。
- 布尔值自 v2.1.218 起接受 `yes/no/on/off/1/0`。

**对本项目的直接含义**：编排层 skill 标 `disable-model-invocation: true` 后，它的 description **不在**模型可见列表里。因此「路由」若要指向编排 skill，必须自己持有那份清单（写在 router 的 SKILL.md 或它读取的文件里），不能指望模型从内置列表看到。这是 #7 的一个硬约束。

### 2.2 Codex

**有等价物，但不在 frontmatter**。`<skill>/agents/openai.yaml`：

```yaml
policy:
  allow_implicit_invocation: false
```

原文：「`allow_implicit_invocation` (default: `true`): When `false`, Codex won't implicitly invoke the skill based on user prompt; explicit `$skill` invocation still works.」源码 `codex-rs/skills/src/model.rs` `SkillPolicy { allow_implicit_invocation: Option<bool>, products: Vec<Product> }`，`SkillMetadata::allows_implicit_invocation()`。

与 Claude Code 的差异（重要）：
1. **描述是否还在列表里**：文档只说「不隐式调用」，没说从可用 skill 列表移除。**推测**：name/description/path 仍进初始列表（否则 `$name` 补全无从来）；Claude Code 则是整体从上下文移除。
2. **执行位置**：Claude Code 在 Skill tool 调用处硬拦；Codex 是选择阶段不隐式选（`detect_implicit_skill_invocation()`），模型读到列表后能否绕过——**未核实**。
3. **反向控制**：Codex **没有** `user-invocable: false` 等价物，也没有「常驻 / pinned」skill；全局只有 `skills.include_instructions` 开关。
4. Codex `parser.rs` 无 `deny_unknown_fields`，所以 SKILL.md 里写 `disable-model-invocation: true` **不报错、也不生效**，静默忽略；反之 Claude Code 也不读 `agents/openai.yaml`。两边控制项必须**各写一份**。

---

## 3. (c) 交集封装格式与分层映射

### 3.1 单个 skill 包同时命中两平台的最小格式

```
<skill-name>/
├── SKILL.md                 # frontmatter 只用规范六字段中的 name / description（可加 metadata、license、compatibility）
├── agents/
│   └── openai.yaml          # Codex 专属：policy.allow_implicit_invocation、interface、dependencies
├── scripts/                 # 两边都按「执行不读入」处理
├── references/              # 两边都按需读取（Codex 文档用 references/，Anthropic 最佳实践用 reference/；无强制）
└── assets/                  # Codex 图标只能指向 assets/ 下相对路径
```

- **frontmatter**：`name`、`description` 两边都读；`description` ≤ 1,024 字、第三人称、含功能 + 触发条件 + 负向条件（Anthropic 最佳实践）。Codex 额外读 `metadata.short-description`（kebab-case）；Claude Code 把 `metadata` 当自由映射不动作，所以这个键两边都安全。
- **Claude Code 扩展字段**（`disable-model-invocation`、`user-invocable`、`allowed-tools`、`argument-hint`、`context`、`paths`、`when_to_use`、`model`、`effort`、`hooks`、`shell`…）在 Codex 被静默忽略，**不会**破坏加载；但会让该 SKILL.md 在 claude.ai 上传 / Skills API / `package_skill.py` 处报硬错误。本项目不走那三条路，可以照用；若日后要上传 claude.ai，只能保留六字段。
- **正文**：Claude Code 独有的 `!`cmd`` 动态注入、`$ARGUMENTS`、`${CLAUDE_SKILL_DIR}` 在 Codex 里是普通文本。Codex 提供的是文件路径（列表含 path），脚本引用宜写相对于 SKILL.md 的路径并用正斜杠（Anthropic 最佳实践「Always use forward slashes in file paths, even on Windows」）。**推测**：正文用「本目录的 `scripts/x.py`」这类相对措辞，两边都能落。
- **`agents/openai.yaml`**：Claude Code 不认识 `agents/` 子目录里的 yaml（它的 `agents/` 概念在插件根，文件是 `.md`），放在 skill 内无副作用——**推测**，未在文档见到相反说明。

### 3.2 分发：两套目录，不共享同一棵树

| | Claude Code | Codex |
| --- | --- | --- |
| 项目内 | `.claude/skills/<name>/` 或插件 `<plugin>/skills/<name>/` | `.agents/skills/<name>/` |
| 用户级 | `~/.claude/skills/<name>/` | `~/.agents/skills/<name>/` |
| 插件清单 | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |

两边互不读对方目录（§1.1、§1.2）。把一份 `skills/` 树同时暴露给两边只有三条路：
1. **symlink / junction**：Claude Code 明确支持 skill 条目级 symlink 并去重；Codex 文档说支持但 Windows 上有 junction 失败的用户报告（#8400），且 `.agents/skills` 根本身为链接不保证（#11314）。带入的两条已知事实与此一致：2.0 的 `~/.agents/skills` junction 是**条目级**（11 个各指一个 skill），能工作；legal-skills 的 `.claude/skills -> ../skills` 是**根级** symlink，在 Windows 克隆下是空目录（git 在 Windows 默认不建 symlink，是 git 侧问题，与两平台无关——**推测**）。
2. **复制**：把同一 skill 包分别放进两棵树，靠脚本同步。最稳，代价是双份。
3. **插件**：Claude Code 插件 + Codex 插件各写一份清单指向同一 `skills/`；Claude 插件缓存时会解引用 marketplace 内 symlink、跳过外部 symlink（§1.3）。

`.claude-plugin/` 与 `.codex-plugin/` 可以并存于同一插件根，各指 `./skills/`——**推测**，两边文档都没有禁止，也没有说明互相忽略；需实测。

### 3.3 编排层 / 参考层在两边怎么落

本项目定义（`CONTEXT.md`）：编排 skill = 用户主动调用、驱动一段流程；参考 skill = 被编排 skill 或模型按需调用的工具类 skill。

| 层 | Claude Code | Codex |
| --- | --- | --- |
| **编排层**（只许人触发） | frontmatter `disable-model-invocation: true`；描述不进上下文；`/name` 触发；可加 `argument-hint`、`arguments:`；用 `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/… *)` 免提示跑自带脚本 | `agents/openai.yaml` `policy.allow_implicit_invocation: false`；`$name` 或 `/skills` 触发；描述**仍在**列表（推测）；`interface.display_name` / `default_prompt` 可给人用的名字和起手 prompt |
| **参考层**（模型按需调） | 默认即可；若不想出现在 `/` 菜单，`user-invocable: false`；`paths:` 可按文件 glob 自动挂载 | 默认即可；**无法**对人隐藏 |
| **路由**（只提示不触发） | 默认或 `user-invocable: false`；它必须**自己列出**编排 skill 的名字与用途，因为那些描述已从模型列表移除 | 默认；编排 skill 描述仍在列表（推测），路由可少列但为一致起见仍自列 |
| **被编排 skill 调用参考 skill** | 编排 skill 正文让模型调 Skill tool（参考 skill 描述在列表中）；或 `context: fork` + `agent:` 把参考 skill 预加载进子代理 | 编排 skill 正文用 `$参考名` 提及（mentions 解析 `$name`）；无子代理预加载机制（未见文档） |
| **停用某个 skill** | `skillOverrides: off`（插件 skill 不适用）或 `claude plugin disable` | `[[skills.config]] enabled = false` |

一处不对称要在 #9 记下：Codex 里参考层 skill 对人永远可见、可 `$` 提及；Claude Code 里可以藏。若本项目要求「律师只看见两三个命令」，只有 Claude Code 能在平台层做到，Codex 侧只能靠命名与 `interface.short_description` 引导。

---

## 4. (d) 可视化宿主消费的数据形状

### 4.1 MCP Apps 扩展（`io.modelcontextprotocol/ui`）

[规范 2026-01-26](https://raw.githubusercontent.com/modelcontextprotocol/ext-apps/main/specification/2026-01-26/apps.mdx)（Status: Stable，源自 SEP-1865；核心规范 2026-07-28 版把它列为正式扩展）。

- **工具声明 UI**：`tools/list` 返回项的 `_meta.ui.resourceUri: "ui://<server>/<view>"`，可选 `_meta.ui.visibility: ["model","app"]`。
- **UI 资源**：URI 必须 `ui://` 开头；`mimeType` 应为 **`text/html;profile=mcp-app`**；经普通 `resources/read` 返回 `text`（HTML 字符串）或 `blob`；资源级 `_meta.ui.csp { connectDomains, resourceDomains, frameDomains, baseUriDomains }`、`permissions`、`domain`、`prefersBorder`。
- **宿主渲染**：「All View content MUST be rendered in sandboxed iframes」，宿主按声明域构造 CSP，未声明的域一律不放行；默认 CSP `connect-src 'none'`。
- **能力协商**：客户端 `initialize` 里 `capabilities.extensions["io.modelcontextprotocol/ui"].mimeTypes`。
- **iframe ↔ 宿主**：JSON-RPC over postMessage。View → Host：`ui/initialize`、`tools/call`、`resources/read`、`ui/message`、`ui/open-link`、`ui/request-display-mode`（`inline|fullscreen|pip`）、`ui/update-model-context`。Host → View 通知：`ui/notifications/tool-input`（`params.arguments`）、`tool-input-partial`、**`ui/notifications/tool-result`**、`tool-cancelled`、`size-changed`（`{width,height}`）、`host-context-changed`（`theme`、`displayMode`、`containerDimensions`、`locale`、`platform`…）。
- **视图收到的核心数据形状**（原文示例结构）：

```json
{ "jsonrpc": "2.0", "method": "ui/notifications/tool-result",
  "params": {
    "content": [{ "type": "text", "text": "…给模型看的文字…" }],
    "structuredContent": { "…给 UI 用的结构化 JSON…": 1 },
    "_meta": { "…不进模型上下文的元数据…": 1 } } }
```

`content` 是模型看到的文本表示，`structuredContent` 是 UI 消费的结构化数据（由工具的 `outputSchema` 约束），`_meta` 不进模型上下文。
- **降级规则**（原文）：「If host does not support MCP Apps, tool behaves as standard tool (text-only fallback).」

### 4.2 哪些宿主渲染

- 官方[客户端矩阵](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/extensions/client-matrix.mdx)（社区维护）列出 Claude (web)、Claude Desktop、VS Code Copilot、M365 Copilot、Goose、Postman、MCPJam、ChatGPT、Cursor 等；**Claude Code 不在列，Codex 未提及**。Anthropic 帮助中心「interactive connectors」可用面：Claude、Cowork、Claude Desktop、iOS/Android——**无 Claude Code**。
- **Claude Code**：[MCP 页](https://code.claude.com/docs/en/mcp) 只有 tools（输出上限 25,000 token，`MAX_MCP_OUTPUT_TOKENS` / `_meta["anthropic/maxResultSizeChars"]` 可调）、resources（`@server:resource` 提及，**部分核实**——搜索索引可见、页面锚点抓取截断）、prompts 作 `/` 命令、OAuth、`.mcp.json` 项目级配置；**无任何 UI / HTML / widget 渲染条目**。
- **Codex**：[MCP 页](https://learn.chatgpt.com/docs/extend/mcp.md) 支持项只有三条：STDIO、Streamable HTTP、server `instructions`；resources/prompts/UI 不在列。源码 `codex-rs/features/src/lib.rs` 有 **`EnableMcpApps`「Enable MCP apps」默认 `false`**；issue [#21019](https://github.com/openai/codex/issues/21019) 报告 Desktop 收到 `ui://` 资源仍只显示文本、不发 `resources/read`。对应 TOML 键**推测**为 `features.enable_mcp_apps`，未见于配置参考。Apps SDK 文档明说「Keep the MCP tools useful without a component so ChatGPT and Codex can complete the workflow without UI.」
- **OpenAI Apps SDK** 已收敛到 MCP Apps：「ChatGPT implements the open MCP Apps standard」，`_meta["openai/outputTemplate"]` 是 `_meta.ui.resourceUri` 的兼容别名，`window.openai.toolOutput` 对应 `ui/notifications/tool-result`，`text/html+skybridge` 为旧 MIME（新作用 `text/html;profile=mcp-app`；是否正式弃用**未核实**）。这套只对 ChatGPT，不对 Codex。

### 4.3 无 UI 宿主的普通 MCP 回落（核心规范 2026-07-28）

[tools](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/server/tools.mdx) 结果块类型：`text`、`image`（`data`、`mimeType`）、`audio`、`resource_link`（`uri`、`name`、`mimeType`）、`resource`（内嵌 `uri`、`mimeType`、`text|blob`）；加 `structuredContent`（任意 JSON，受 `outputSchema` 约束）、`isError`、`_meta`。[resources](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/server/resources.mdx)：`uri`、`name`、`mimeType`、`size`，`resources/read` 返 `contents[]`（`text` 或 base64 `blob`）；模板用 RFC 6570 `uriTemplate`。规范示例 MIME 不含 `image/svg+xml`（合法但未被列为示例，**未核实**是否有宿主特殊处理）。

### 4.4 对本项目的形状结论

一个本地图谱 MCP server 若按标准写一次：
- 工具 `_meta.ui.resourceUri: "ui://<server>/graph"`；资源 `ui://<server>/graph` 为 `text/html;profile=mcp-app` 的自包含 HTML（CSP 默认 `connect-src 'none'`，图数据只能从 `structuredContent` 拿，不能自己回连本地端口——除非 `csp.connectDomains` 声明）；
- 工具结果 `structuredContent` 装图（例如 `{nodes:[…], edges:[…], meta:{…}}`，由 `outputSchema` 声明），`content` 装模型可读摘要。

这份产物在 Claude.ai / Claude Desktop / ChatGPT / VS Code 里出 iframe；在 **Claude Code 与 Codex CLI 里按规范降级为文本**——两个本项目实际使用的宿主目前都不渲染。所以 #10 的决策空间是：(i) 图存档本身就是 `structuredContent` 那份 JSON，MCP server 只是搬运；(ii) 会话内可视化在两个 CLI 宿主里暂不可得，落盘 HTML 快照（2.0 的第二出口）仍是唯一「律师看得见」的通道，除非换宿主（Claude Desktop 等）——**这是一个事实约束，不是推荐**；(iii) Codex 的 `EnableMcpApps` 旗标存在，说明方向在走，但默认关。

---

## 5. 对三张票的要点

- **#7 路由的定位机制**：Claude Code 侧编排 skill 的描述不在模型列表中，路由必须自持清单；Codex 侧列表含 path 且 `$name` 歧义即不匹配，路由给出的名字要唯一。两边 skill 列表都有预算（1% / 2%）并会先砍描述，路由自己的 description 要把触发词放前面（1,536 / 1,024 字截断）。
- **#9 编排层与参考层的 skill 清单**：每个 skill 两份控制项（frontmatter + `agents/openai.yaml`）；Codex 无「对人隐藏」，参考层在 Codex 永远可 `$` 提及；Claude Code 个人级压过项目级，开发机上 `~/.claude/skills/` 若有同名残留会盖掉仓库版本。
- **#10 图存档与可视化接口**：数据形状就是 `structuredContent` JSON + `ui://` HTML；两个 CLI 宿主目前都不渲染，落盘 HTML 出口不能删。

## 6. 与带入的已知事实核对

| 已知事实 | 本次核对 |
| --- | --- |
| 2.0 用 `~/.agents/skills` 条目级 junction 挂 Codex skill | 与 Codex 文档「用户级 `$HOME/.agents/skills`」「支持 symlinked skill folders」一致；条目级链接可行，根级链接与 Windows junction 有用户报告失败（#11314、#8400），2.0 能工作属于前者 |
| 2.0 用 MCP server 出图（ADR-0008 会话内 widget） | Codex 至今默认不渲染 MCP App UI（`EnableMcpApps` 默认 false，#21019）；ADR-0008「不符预期」在平台层有解释 |
| legal-skills 的根级 symlink 双注册在 Windows 是空目录 | 两平台都不读对方目录，双注册思路本身成立；空目录是 git-on-Windows 不建 symlink 所致（**推测**），与两平台的 symlink 支持无关 |

## 7. 来源清单（均 2026-09-04 访问）

Claude Code / Anthropic：
- https://code.claude.com/docs/en/skills（发现位置、优先级、frontmatter、调用矩阵、预算、参数替换、skillOverrides、规范六字段）
- https://code.claude.com/docs/en/plugins 、https://code.claude.com/docs/en/plugins-reference 、https://code.claude.com/docs/en/plugin-marketplaces（插件清单、目录、marketplace、symlink 处理、skills-dir 插件）
- https://code.claude.com/docs/en/memory（Windows symlink 需管理员或开发者模式；只读 CLAUDE.md 不读 AGENTS.md）
- https://code.claude.com/docs/en/mcp 、https://code.claude.com/docs/en/mcp-quickstart 、https://code.claude.com/docs/en/commands（MCP 能力面）
- https://code.claude.com/docs/en/agent-sdk/skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices（name/description 硬限、渐进披露、正斜杠）
- https://github.com/anthropics/skills 、https://github.com/anthropics/skills/blob/main/spec/agent-skills-spec.md
- https://github.com/anthropics/claude-code/issues/66352（`.agents/skills` 支持请求，开放）
- https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude

OpenAI Codex：
- https://learn.chatgpt.com/docs/build-skills.md（扫描位置、`agents/openai.yaml`、`allow_implicit_invocation`、预算、调用方式、agentskills.io）
- https://learn.chatgpt.com/docs/config-file/config-reference.md 、https://learn.chatgpt.com/docs/config-file/environment-variables.md
- https://learn.chatgpt.com/docs/developer-commands.md?surface=cli
- https://learn.chatgpt.com/docs/plugins 、https://learn.chatgpt.com/docs/build-plugins.md 、https://raw.githubusercontent.com/openai/plugins/main/README.md 、https://raw.githubusercontent.com/openai/skills/main/README.md
- https://learn.chatgpt.com/docs/extend/mcp.md 、https://learn.chatgpt.com/docs/mcp-server.md 、https://raw.githubusercontent.com/openai/codex/main/codex-rs/docs/codex_mcp_interface.md
- 源码：https://raw.githubusercontent.com/openai/codex/main/codex-rs/skills/src/parser.rs 、…/skills/src/model.rs 、…/skills/src/interface.rs 、…/skills/src/selection.rs 、…/skills/src/mentions.rs 、…/skills/src/loading.rs 、…/skills/src/lib.rs 、…/core/src/skills.rs 、…/config/src/skills_config.rs 、…/features/src/lib.rs
- issue（用户报告，仅旁证）：https://github.com/openai/codex/issues/22590 、/11314 、/8400 、/8369 、/15136 、/22275 、/20637 、/21019

MCP / Apps SDK：
- https://raw.githubusercontent.com/modelcontextprotocol/ext-apps/main/specification/2026-01-26/apps.mdx 、https://modelcontextprotocol.io/docs/extensions/apps
- https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/extensions/client-matrix.mdx
- https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/server/tools.mdx 、…/server/resources.mdx
- https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt 、https://developers.openai.com/apps-sdk/reference 、https://developers.openai.com/apps-sdk/build/custom-ux/
