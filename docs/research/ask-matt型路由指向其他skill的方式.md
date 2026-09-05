# ask-matt 型路由指向其他 skill 的方式

> **写于** 2026-09-05，对应 issue #15（`wayfinder:research`），供 #7「路由的定位机制」、#9「编排层与参考层的 skill 清单」参考。问题：只推荐不触发的路由，在 Claude Code 与 Codex 上究竟怎么把人送到下一个 skill；参数怎么到达；编排好的提示词能走多远；skill 互相指向的全部方式；合并入口的代价；两个已知缺陷怎么规避。只记事实与两边差异，不做决策。
> **来源等级**：一手来源三层。(1) 本机已装 `mattpocock-skills` 插件 1.2.3 原文（`~/.claude/plugins/cache/claude-plugins-official/mattpocock-skills/1.2.3/`），下文以 `插件:<路径>:<行>` 引用。(2) 官方文档：Claude Code `code.claude.com/docs/en/*`；Codex `developers.openai.com/codex/skills` 308 跳转到 `learn.chatgpt.com/docs/build-skills`，以及同站 `custom-prompts`、`developer-commands`、`config-reference`。(3) 源码：`openai/codex` main 分支 commit `ddf04ad`（2026-09-05T05:31Z），经 GitHub contents API 读取，未克隆；`agentskills/agentskills` main commit `69ef37e`（2026-08-09）的 `docs/specification.mdx`（agentskills.io 站点本次连接反复关闭，改读其仓库源文件）。所有网页访问日期均为 2026-09-05。
> **带入的已知事实**（引 `docs/research/skill-platforms-claude-code-与-codex.md`，#11，不重推）：Claude Code 上 `disable-model-invocation: true` 使描述整体不进上下文、模型不能调、只能 `/name`，Codex 等价物是 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`，`$name` 显式提及仍可；Claude Code 列表预算 1%、单条 1,536 字，Codex 列表 2%（未知窗口 8,000 字）、`skills.max_context_tokens` 上限 10,000；Codex 只读 `name`/`description`/`metadata.short-description`，其余 frontmatter 静默忽略；`$name` 歧义时不匹配。另引 `docs/research/ask-matt-路由写法解析.md`（#7）对 ask-matt 写法与两个缺陷的记录，本文只在其上加机制层。
> **标注**：凡官方文档未直接写明、由源码或旁证推断的，标 **推测**；GitHub issue 与插件 CHANGELOG 里的用户报告只作旁证。凡本次未能读到的，标 **未核实**。
> **红线**：不含任何案件内容、当事人、案号。

---

## 0. 结论速览

| 问题 | Claude Code | Codex |
| --- | --- | --- |
| 人打 `/name 参数` 后参数怎么到 skill | 文档明写：`$ARGUMENTS`（整串原样）、`$ARGUMENTS[N]` / `$N`（`$0` 为第一个，shell 式引号分词）、`arguments:` 声明的 `$name`；正文没有占位符时自动追加 `ARGUMENTS: <输入>` | skill **没有参数机制**。`$name` 只是把 `SKILL.md` 正文作为一段 `<skill>` 片段注入本轮；自由文本留在用户消息里原样送模型。带 `$1..$9` / `KEY=value` / `$ARGUMENTS` 的是**已弃用**的 custom prompts（`~/.codex/prompts`），不是 skill |
| 中文与空格 | 参数值任意文本，多词值加引号才成一个位置参数；skill **名字**文档未说，规范要求 `a-z 0-9 -` | `$` 提及名只认 ASCII `[A-Za-z0-9_\-:]`（源码），中文名无法被 `$` 提及；`display_name` 可任意（仅 UI） |
| 填好的提示词能否递给下一次调用 | 同一会话：模型可带参数调 Skill tool（仅模型可调的 skill）、`context: fork` 把 skill 正文当子代理的 prompt、`/a /b 参数` 叠加。新会话：无「排队一句话给下一个会话」的官方机制；能做的是 `claude "/skill 参数"`、`claude -p "/skill 参数"`、`--resume <id>`、SessionStart / UserPromptSubmit / UserPromptExpansion 三类 hook 改写或补上下文 | 同一会话：`interface.default_prompt`（静态）、模型按列表 path 自己读文件。新会话：`codex exec "…"`、`codex resume`、`codex fork`；无 hook 文档可引（**未核实**） |
| skill 互指的方式 | `Call the Skill tool with "x"`（可带参数）、`context: fork` + `agent:`、子代理 `skills:` 预载、`/name` 纯标签、`!`cmd`` 在展开时把别的文件读进来 | `$name` 提及（用户文本里才被解析，SKILL.md 正文里的 `$name` 是否解析：**推测**否）、列表里的 path 让模型自己读、纯文本标签 |
| 用户调用的 skill 为何不能被任何 skill 触发 | 文档：`disable-model-invocation` 的 skill 不在列表、Skill tool 调用被硬拦并告知「让用户自己跑 `/name`」；也不能预载进子代理、不能做定时任务的 prompt | 文档只说「不隐式调用，显式 `$name` 仍可」；一个 skill 正文里写 `$x` 能否算显式提及：**推测**不能（解析只跑用户输入） |
| 合并入口（一 skill 多动作） | 动作可由 `$0` / `arguments:` 分辨；用户调用的 skill 描述本就不进模型上下文，description 预算只影响 `/` 菜单一行；`/` 菜单一条 | 动作只能从自由文本分辨；描述在 2% 列表里，一条 description 装多触发词要与 1,024 字上限和列表截断共处；`/skills`、`$` 菜单一条 |
| 缺陷「报未安装」 | 根因是列表里没名字；文档承认模型会被告知「建议你自己跑 `/deploy`」；规避靠路由自持清单，或 `!`cmd`` 在展开时列出真实目录 | 列表含 name + path，用户调用的 skill 仍在列表（**推测**）；系统提示明写「若点名的 skill 不在列表或读不到，简短说明后用最佳替代继续」 |
| 缺陷「按摘要断言」 | 路由展开时可用 `!`cat ${CLAUDE_PLUGIN_ROOT}/skills/x/SKILL.md`` 把对方原文读进来；或让模型 Read | 系统提示已要求「决定用某 skill 后主代理必须完整读其 SKILL.md 再动作」，列表带路径 |

---

## 1. `/name` 是标签；参数怎么到达那个 skill

### 1.1 插件里的约定

`.agents/invocation.md` 把两种写法分开（`插件:.agents/invocation.md:16-18`）：其他 skill 的**操作性**指令必须写 `Call the Skill tool with "grilling"`，理由是「多数 harness 把 skill 调用暴露为一个模型可调的 tool，点名 tool 的命中率高于在散文里丢一个 `/name` 指望它被读成命令」；路由散文（`ask-matt`、bucket README）只是给人挑，「不在触发任何东西，所以保留 `/skill` 式名字当普通标签」。插件里带参数的用户调用 skill 只有四个，全部只写 `argument-hint`、正文用一句话处理参数，没有一个用 `$ARGUMENTS` 占位：

| skill | `argument-hint` | 正文如何用参数 |
| --- | --- | --- |
| `handoff` | `"What will the next session be used for?"` | `插件:skills/productivity/handoff/SKILL.md:16`「If the user passed arguments, treat them as a description of what the next session will focus on」 |
| `teach` | `"What would you like to learn about?"` | 正文不引用参数，靠 Claude Code 的自动追加 |
| `claude-handoff`（in-progress） | 同 `handoff` | 同上 |
| `loop-me`（in-progress） | `"A workflow to design, or nothing to go find one"` | 同上 |

全插件 `grep '\$ARGUMENTS'` 零命中；唯一的 `$1` 出现在 `setup-ts-deep-modules/SKILL.md:99`，说的是 dependency-cruiser 配置的反向引用，与参数无关。

### 1.2 Claude Code：官方语义

[skills 页](https://code.claude.com/docs/en/skills)「Pass arguments to skills」与「Available string substitutions」，原文：

- 「Both you and Claude can pass arguments when invoking a skill. Arguments are available via the `$ARGUMENTS` placeholder.」
- `$ARGUMENTS`：「All arguments passed when invoking the skill. When no placeholder receives an argument, Claude Code appends them as `ARGUMENTS: <value>`.」
- `$ARGUMENTS[N]` 按 0 起索引；`$N` 是简写，「`$0` for the first argument or `$1` for the second」。
- `$name`：「Named argument declared in the `arguments` frontmatter list. Names map to positions in order, so with `arguments: [issue, branch]` the placeholder `$issue` expands to the first argument and `$branch` to the second.」`arguments` 字段「Accepts a space-separated string or a YAML list」。
- **没有占位符时**：「Claude Code appends `ARGUMENTS: <your input>` to the end of the skill content so Claude still sees what you typed. A placeholder is `$ARGUMENTS`, an indexed form such as `$1`, or a named argument. An indexed placeholder with no argument at its position stays as literal text and doesn't count as receiving one. A named placeholder counts even when its position has no argument, because it expands to an empty string.」这就是插件四个 skill 只写 `argument-hint` 也能收到参数的原因。
- **带空格的参数**：「Indexed arguments use shell-style quoting, so wrap multi-word values in quotes to pass them as a single argument. For example, `/my-skill "hello world" second` makes `$0` expand to `hello world` and `$1` to `second`. The `$ARGUMENTS` placeholder always expands to the full argument string as typed.」
- 缺位：「An indexed placeholder with no corresponding argument … stays in the content unchanged. A named placeholder … with no matching argument expands to an empty string.」
- 转义：`\$1.00` 保留字面，`\\$1` 两个反斜杠都留下且 `$1` 仍展开。
- `argument-hint`：「Hint shown during autocomplete to indicate expected arguments.」只影响补全提示。
- 叠加：「Typing `/write-tests /fix-issue 123` loads both skills and passes the trailing text `123` as `$ARGUMENTS` to each of them.」最多首个加五个；「Expansion stops at the first token that isn't an inline user-invocable skill」，`context: fork` 的 skill 也会终止叠加。
- 其他替换：`${CLAUDE_SESSION_ID}`、`${CLAUDE_SKILL_DIR}`（插件 skill 指 skill 子目录）、`${CLAUDE_PROJECT_DIR}`、`${CLAUDE_PLUGIN_ROOT}`、`${CLAUDE_PLUGIN_DATA}`、`${CLAUDE_EFFORT}`。
- [commands 页](https://code.claude.com/docs/en/commands)：「A command is only recognized at the start of your message. Text that follows the command name becomes its arguments.」

**中文**：文档没有任何关于 skill 名字或参数字符集的句子（**未找到**）。参数值经 `$ARGUMENTS` 原样进正文，中文只是文本；位置参数按 shell 式引号分词，只认空格与引号，与字符集无关。名字方面只有 agentskills 规范可引（§1.5）。插件 skill 的命令名带命名空间：「`my-plugin/skills/review/SKILL.md` → `/my-plugin:review`」。

### 1.3 Codex：skill 没有参数，只有提及

[build-skills](https://learn.chatgpt.com/docs/build-skills) 原文：「In Codex CLI or the IDE extension, run `/skills` or type `$` to mention a skill.」「ChatGPT and Codex start with each skill's name and description, then load the full `SKILL.md` instructions when they decide to use that skill.」页面**没有任何**关于 skill 参数、`$ARGUMENTS`、占位符的句子（**未找到**）。

源码给出提及之后发生的事（commit `ddf04ad`）：

- `codex-rs/protocol/src/user_input.rs:45-49`：`UserInput::Skill { name, path }`「Skill selected by the user (name + path to SKILL.md)」，是 TUI 从 `$` 菜单选中时发出的结构化项；自由文本另行以 `UserInput::Text` 发送。
- `codex-rs/skills/src/mentions.rs:84-149`：`extract_tool_mentions()` 扫描用户文本，`$` 后紧接的名字只由 `is_mention_name_char()` 允许的字节组成，即 `a-z A-Z 0-9 _ - :`（`mentions.rs:226-228`）；另支持 `[$name](skill://path)` 链接式。`PATH`、`HOME`、`TMP` 等常见环境变量名被排除（`mentions.rs:208-224`）。
- `codex-rs/ext/skills/src/selection.rs:21-79`：`collect_explicit_skill_mentions()` 先收结构化 `Skill`/`Mention` 项，再对每个 `Text` 项跑 `extract_tool_mentions`，按 `entry.enabled && entry.name == name` 匹配目录里的 skill。
- `codex-rs/ext/skills/src/fragments.rs:62-110`：命中的 skill 以一段 `role = "user"`、`content_kind = "skills.selected_skill_instructions"` 的片段注入，形如 `<skill>\n<name>{name}</name>\n<path>{path}</path>\n{contents}\n</skill>`。**用户输入本身不被改写**，`$name` 与其后文本原样留在 `Text` 里。
- `codex-rs/ext/skills/src/catalog_prompt.rs:8`（系统提示里的触发规则原文）：「If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.」

所以 Codex 上「参数」只有一种形态：`$name` 后面的自由文本作为**同一条用户消息**送给模型，skill 正文另附；不做替换，不分词。**中文**：`$中文名` 的中文字节不在允许集合，不会被解析成提及（源码事实）；`interface.display_name` 是 UI 显示名，文档未限制字符（**未找到**限制）。

[custom-prompts](https://learn.chatgpt.com/docs/custom-prompts)（页面自标「deprecated」）才有参数：`/prompts:name` 调用；「Positional placeholders: `$1` through `$9` expand from space-separated arguments」「Named placeholders: Use uppercase names like `$FILE` or `$TICKET_ID` and supply values as `KEY=value`」「Quote values with spaces (for example, `FOCUS="loading state"`)」「`$ARGUMENTS` includes them all」「Write `$$` to emit a single `$`」；并说「Use skills for reusable instructions that Codex can invoke explicitly or implicitly」，custom prompts「require explicit invocation」。它们存放在 `~/.codex/prompts`，「not shared through your repository」。

### 1.4 `agents/openai.yaml` 全字段（Codex 文档）

`interface.display_name`、`interface.short_description`、`interface.icon_small`、`interface.icon_large`、`interface.brand_color`、`interface.default_prompt`（「Optional surrounding prompt to use the skill with」）、`policy.allow_implicit_invocation`（默认 `true`）、`dependencies.tools`。插件里每个 skill 只用前两项加 `policy`。

### 1.5 agentskills 规范对参数与命名的立场

`docs/specification.mdx`（`agentskills/agentskills@69ef37e`）：frontmatter 只有 `name`、`description`、`license`、`compatibility`、`metadata`、`allowed-tools`（后者「Experimental」）。`name`「Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen」，正文另一处写「May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens」「Must match the parent directory name」。规范**没有**任何参数、占位符、调用语法条款；只定义三层渐进披露：「Metadata (~100 tokens): The `name` and `description` fields are loaded at startup for all skills」「Instructions (< 5000 tokens recommended): The full `SKILL.md` body is loaded when the skill is activated」「Resources (as needed)」。「unicode lowercase alphanumeric」与括号里的 `a-z` 互相矛盾，中文目录名是否合规规范本身没说清（**未核实**）；Codex `$` 解析只认 ASCII（§1.3）是实际约束。

**两边差异**：Claude Code 有完整参数机制（整串、位置、命名、无占位符自动追加、引号分词），Codex 的 skill 没有参数，只有把正文附进本轮的提及，参数即用户消息本身；两边都没有为中文名做过说明，Codex 的 `$` 提及名在源码层只认 ASCII。

## 2. 「帮助编排提示词」能走多远

### 2.1 同一会话内

**Claude Code**：

- 模型可以带参数调 Skill tool：文档「Both you and Claude can pass arguments」；权限语法「`Skill(name)` for exact match, `Skill(name *)` for prefix match with any arguments」也印证参数随调用一起走。本会话可观察到 Skill tool 的入参就是 `skill` 与 `args` 两项（本机观察）。但只对**模型可调**的 skill 成立：「By default, Claude can invoke any skill that doesn't have `disable-model-invocation: true` set」；对用户调用的 skill，「If Claude tries anyway, Claude Code blocks the call and instructs it not to reproduce the deploy steps another way, so expect Claude to suggest running `/deploy` yourself」。即路由能替人**填好**参数，却不能替人**按下**一个用户调用的 skill；它能做到的是把「下一句该打什么」原样打印出来。
- `context: fork`：「The skill content becomes the prompt that drives the subagent. It won't have access to your conversation history.」子代理收到的是替换过 `$ARGUMENTS` 的 skill 正文（文档示例「The subagent receives the skill content as its prompt ("Research \$ARGUMENTS thoroughly...")」）；`agent:` 决定用哪个子代理配置（`Explore`、`Plan`、`general-purpose` 或 `.claude/agents/` 自定义）；默认后台跑，`background: false` 改为本轮等待（v2.1.218 起）。这是「填好的提示词递给一个新上下文」在同一会话里的官方形态，但它是子代理，不是新会话。
- 叠加 `/a /b 参数`：两个 skill 都收到同一串尾部文本（§1.2）。
- 子代理 `skills:` 预载：「The full content of each listed skill is injected into the subagent's context at startup」；「You can't preload skills that set `disable-model-invocation: true`」。
- `/fork [prompt]`（[commands 页](https://code.claude.com/docs/en/commands)）：「Copy the current conversation into a new background session and keep working here. Pass a prompt and the copy starts working on it immediately」，v2.1.212 起。它是内置命令；内置命令能否经 Skill tool 调用，文档只列了 `/init`、`/security-review` 可、`/compact` 不可，`/fork` 未列（**未核实**）。
- `/compact [instructions]`：「replace history with a summary, optionally focused on what you specify」。

**Codex**：

- `interface.default_prompt`：「Optional surrounding prompt to use the skill with」，是 skill 作者写死的一段起手提示，不随对话变化。文档没说它在 CLI 里如何被填入（**未核实**）。
- 提及即注入（§1.3）：路由 skill 的正文可以指导模型「本轮就按 `$x` 的方式去做」，但 `$x` 写在 SKILL.md 里能否被当作提及见 §3.2。
- 没有 `context: fork` 等价物；`/agent` 在 TUI 命令表里存在，与 skill 的关系文档未述（**未核实**）。

### 2.2 递给新会话

ADR-0003 定下「每个节点的文书生成都在新对话里跑」，所以这一节是关键。

**Claude Code**：

- 文档里**没有**「当前会话给下一个会话排队一句提示词」的机制（skills、hooks、sessions、headless 四页均无；`--cloud <session-id>` 与 `-p` 组合可以「queue a message into that existing session」，但只对 claude.ai 云端会话）。
- 能做的是从 shell 起新会话并把提示词当首句：「`claude "query"`: Start interactive session with initial prompt」「`claude -p "query"`: Query via SDK, then exit」；[headless 页](https://code.claude.com/docs/en/headless)明写「User-invoked skills and custom commands work in `-p` mode: include `/skill-name` in the prompt string and Claude Code expands it before running.」因此一个 skill 的 Bash 步骤可以执行 `claude -p "/x 参数"` 起一个子进程会话（这只是普通 Bash 命令；嵌套会话的行为文档未述，**推测**可行，**未核实**）。
- `--resume <session-id>` 可从任意目录恢复（v2.1.223 起）；`claude -p --resume <id> "…"` 给既有会话追加一句并拿结构化结果；`--fork-session` 复制成新 id；`--session-id` 指定 UUID。
- Hook 能改写或补充提示词（[hooks 页](https://code.claude.com/docs/en/hooks)）：`SessionStart`（matcher `startup|resume|clear|compact|fork`）「Plain-text stdout … is added as context that Claude can see」，支持 `additionalContext`、`systemMessage`；`UserPromptSubmit` 支持 `updatedPrompt`「Replaces the user's original prompt text」；`UserPromptExpansion`「fires when a user-typed command (like a slash command or skill invocation) expands into a full prompt before it reaches Claude」，matcher 是 skill/命令名，可 `exit 2` 拦截、`updatedPrompt` 替换展开后的提示词、加 `additionalContext`。也就是说：一个新会话启动时，hook 可以把上一会话留在磁盘上的「填好的提示词」读进上下文；人打 `/x` 时，hook 可以把展开结果替换成任何文本。这些都是 harness 层配置，不是 skill 能自己声明的。
- 定时任务（[scheduled-tasks](https://code.claude.com/docs/en/scheduled-tasks)）：`/loop 20m /review-pr 1234` 可以把 skill 当 prompt 反复跑，但「Skills marked `disable-model-invocation: true`」「reach Claude as plain text instead of executing」；任务是会话内的，`--resume`/`--continue` 才恢复。
- 插件自己的做法（`插件:skills/productivity/handoff/SKILL.md`）：写一份 handoff 文件到临时目录，「Include a "suggested skills" section … naming which skills the next agent should call the Skill tool for」；ask-matt 主线第 2 步「`/handoff` out, then open a fresh session against that file」。即**人开新会话、人把文件给它**。

**Codex**：

- `codex exec "…"`（[developer-commands](https://learn.chatgpt.com/docs/developer-commands.md?surface=cli)）用于「scripted or CI-style runs that should finish without human interaction」，`--json` 出事件流；`codex exec resume --last`；`codex resume <id|--last>`；`codex fork --last`「fork a previous interactive session into a new chat」；`-c key=value` 单次覆盖配置。`codex exec` 的提示词里 `$name` 是否被解析：提及收集在 `ext/skills` 层对所有 `UserInput::Text` 运行（§1.3），不依赖 TUI，**推测**可解析，文档未述。
- Codex hook：TUI 命令表里有 `/hooks`，本次未读到 hook 文档（**未核实**）。
- 没有会话内定时任务文档可引（**未核实**）。

**两边差异**：同一会话内，Claude Code 能让模型带参数调模型可调的 skill、能把 skill 正文当子代理 prompt；Codex 只有静态 `default_prompt` 与提及注入。跨会话，两边都没有「排队给下一会话」的机制，都只剩「起新进程时把提示词当首句」；Claude Code 多出三类 hook 可在新会话启动或 `/x` 展开时改写提示词，且明写 `-p` 模式接受 `/skill` 字符串。

## 3. 插件里 skill 互相指向的全部方式

### 3.1 目录（含出处）

对 `skills/**/SKILL.md` 与 `agents/openai.yaml` 全量 grep，指向别的 skill 的写法共六种：

| # | 写法 | 例子 | 能否带参数 | 谁能用 |
| --- | --- | --- | --- | --- |
| A | `Call the Skill tool with "x"` | `插件:skills/productivity/grill-me/SKILL.md:7`（整个 skill 就这一句）；`tdd/SKILL.md:26`；`improve-codebase-architecture/SKILL.md:13,64,66,71`；`setup-ts-deep-modules/SKILL.md:11` | 能：文档「Claude can pass arguments」；插件里没有一处带参数 | 只能指向模型可调的 skill |
| B | `Call the Skill tool twice, for "x" and "y"` | `grill-with-docs/SKILL.md:7`；`triage/SKILL.md:76`；`wayfinder/SKILL.md:79,111,124` | 同 A | 同 A；`invocation.md:20`「The Skill tool takes one skill per call」 |
| C | 子代理里调 Skill tool | `wayfinder/SKILL.md:77,115`「spin up a subagent that calls the Skill tool with "research"」 | 子代理可以自己调 Skill tool（sub-agents 页「the subagent can still discover and invoke project, user, and plugin skills through the Skill tool」），能带参数 | 同 A |
| D | 「tell the user to run `/x`」 | `code-review/SKILL.md:13`；`to-spec/SKILL.md:9`；`to-tickets/SKILL.md:11`；`triage/SKILL.md:43`；`wayfinder/SKILL.md:25`（全部指向 `/setup-matt-pocock-skills`） | 只是文字，参数由人打 | 指向用户调用的 skill 时唯一可用的写法（`invocation.md:22`） |
| E | 纯标签 `/x` | `ask-matt/SKILL.md` 全篇；`PHASE-BOUNDARIES.md`；bucket README | 无 | 路由与人读文档 |
| F | 「suggested skills … call the Skill tool for」写进交接文件 | `handoff/SKILL.md:10`；`claude-handoff/SKILL.md:12` | 由下一个会话的模型决定 | 跨会话的文字指向 |

插件里**没有**使用 `context: fork`、`agent:`、`allowed-tools`、`user-invocable`、`arguments:` 的 skill（frontmatter 全量核对，只有 `name`、`description`、`disable-model-invocation`、`argument-hint` 四种键）。子代理派发（`code-review`、`codebase-design/DESIGN-IT-TWICE.md`、`research`）用的是散文「spawn a sub-agent」，CHANGELOG 1.2.3 #781 特意「Drop Claude Code's tool and agent-type names from the subagent-dispatch instructions … so the step is followable on Codex and other harnesses」。Codex 侧 `agents/openai.yaml` 里没有任何指向别的 skill 的字段；`$name` 写法在插件 SKILL.md 里**零出现**。

### 3.2 平台层还有哪些方式

**Claude Code**（skills、sub-agents 两页）：

- `context: fork` + `agent:`：skill 正文成为子代理 prompt（§2.1）；「With `skills` in a subagent, the subagent controls the system prompt and loads skill content. With `context: fork` in a skill, the skill content is injected into the agent you specify. Both use the same underlying system.」
- 子代理 frontmatter `skills:`：整份内容启动时注入；不能预载 `disable-model-invocation` 的 skill。
- `!`command``：「runs shell commands before the skill content is sent to Claude. The command output replaces the placeholder」；一次替换、不递归；失败则「aborts the entire skill invocation」；`disableSkillShellExecution` 可全局关闭；`${CLAUDE_SKILL_DIR}`、`${CLAUDE_PLUGIN_ROOT}` 可在其中引用。这使一个 skill 能在展开时把**另一个 skill 的原文或目录清单**读进自己的正文（机制事实；用法见 §5）。
- `@file`：common-workflows 页只讲了用户消息里的 `@path`；skill 正文里 `@path` 是否展开，skills 页未述（**未核实**）。
- 权限：`Skill(name)` / `Skill(name *)` allow/deny；`skillOverrides` 四态（#11 已记）。

**Codex**：

- `$name` 提及：解析只对 `UserInput::Text` 运行（`selection.rs:49-52`），`<skill>` 片段是另一种 `ContextualUserFragment`，不再送回解析器；因此 SKILL.md 正文里写 `$other` **推测**不会自动注入 `other` 的正文，只是模型看到的文本。但系统提示允许「plain text」点名（`catalog_prompt.rs:8`），且列表带 path，模型可自行读文件。
- 列表里的 path：系统提示「After deciding to use a skill, the main agent must … open and read its `SKILL.md` completely before taking task actions」「Do not delegate reading, summarizing, or interpreting skill instructions to a subagent」（`catalog_prompt.rs:28-30`）。
- `allow_implicit_invocation: false`：只关掉隐式选用，显式提及仍可（#11）。

### 3.3 用户调用的 skill 为何不能被任何 skill 触发

- Claude Code 文档：调用矩阵里 `disable-model-invocation: true` 一行「Description not in context」；「Hide individual skills … This removes the skill from Claude's context entirely」；Skill tool 硬拦并要求模型不要绕过；不能预载进子代理；定时任务里当纯文本。一个 skill 的正文只是模型上下文里的文字，它「调用」别的 skill 只能经 Skill tool，所以被同一条规则拦住。插件 `invocation.md:8`「no other skill can. A user-invoked skill may invoke model-invoked skills, but it can never reach another user-invoked skill」是对这条机制的转述；`SKILL-MECHANICS.md:14`进一步推论「Shared reference that two user-invoked skills both need can live in neither … Push it to a plain file outside the skill system」。
- Codex 文档只有一句「When `false`, Codex won't implicitly invoke the skill based on user prompt; explicit `$skill` invocation still works」。「显式」在源码里等于用户输入里的结构化项或 `$` 提及（§1.3）；skill 正文不是用户输入，所以**推测**一个 skill 无法用 `$x` 显式触发用户调用的 `x`；但模型读到 `x` 的 path 后自己 `cat` 一遍，没有任何机制阻止（**推测**，`allow_implicit_invocation` 只作用于选择阶段，#11 §2.2 已记「模型读到列表后能否绕过未核实」）。

**两边差异**：Claude Code 的互指有五种带机制的写法（Skill tool、fork、预载、`!`cmd``、叠加）且用户调用的 skill 被平台硬拦；Codex 只有 `$` 提及与「自己读路径」，`allow_implicit_invocation` 是软门，插件作者为此把互指全部写成 harness 中立的「Call the Skill tool」+「spawn a sub-agent」散文。

## 4. 一个 skill 办多个动作：动作怎么分辨、代价是什么

### 4.1 分辨动作的机制

| | Claude Code | Codex |
| --- | --- | --- |
| 从参数分辨 | `$0` / `$ARGUMENTS[0]` 取第一个词当动作；`arguments: [动作, 对象]` 后正文用 `$动作`；`argument-hint: "[动作] [节点]"` 在补全里提示。位置参数按空格与引号分词，中文动作词与中文对象各占一位；缺位时命名占位符展开为空串、索引占位符原样留下 | 无参数机制；动作只能出现在 `$name` 后的自由文本里，由模型从整条消息里读 |
| 从自然语言分辨 | 无占位符时整串追加为 `ARGUMENTS: …`，模型自己读；`UserPromptExpansion` hook 还可按 skill 名拦截并改写展开结果 | 同上，且是唯一途径 |
| 模型自己选动作 | 只对模型可调的 skill；用户调用的 skill 由人打 | 隐式选用只对 `allow_implicit_invocation` 未关的 skill |

### 4.2 三项代价

**触发准确率**：两边文档都没有给出任何合并/拆分下的命中数据（**未找到**）。可引的只有写法要求：agentskills 规范「Should describe both what the skill does and when to use it」「Should include specific keywords」；插件 `writing-for-agents/SKILL.md:14-18`「One trigger per branch」是作者约定，不是平台承诺。对**用户调用**的 skill，触发由人完成，准确率问题落在「人记不记得名字」（`SKILL-MECHANICS.md:10`「you are the index that must remember it exists」），路由 skill 正是为此而设（`SKILL-MECHANICS.md:22`）。

**description 预算**：

- Claude Code：用户调用的 skill 的 description 根本不进模型上下文，预算对它没有意义；模型可调的 skill 每条 `description + when_to_use` 截到 1,536 字，总预算 1%（可用 `skillListingBudgetFraction` / `SLASH_COMMAND_TOOL_CHAR_BUDGET` / `skillListingMaxDescChars` 调）。合并入口意味着一条 description 装多组触发词，与拆开相比总字数少、但每条更长。
- Codex：所有 skill（含 `allow_implicit_invocation: false` 的，**推测**）都在 2% 列表里，「If many skills are installed, Codex shortens skill descriptions first. For large skill sets, Codex may omit some skills from the initial list and show a warning」；`description` 硬上限 1,024 字。合并入口在这里少占一条，但一条被截断时丢的是整组触发词。

**`/` 菜单可见性**：

- Claude Code：一个 SKILL.md 一条 `/plugin:name`；`user-invocable: false` 从菜单隐藏。合并入口菜单里少几行，靠 `argument-hint` 提示动作。
- Codex：`/skills` 与 `$` 菜单按 `display_name` / `short_description` 列出，无隐藏机制（#11）。CHANGELOG 1.2.0（`插件:CHANGELOG.md` #680）提到 issue #693「drops user-invoked skills from the listing on Claude's desktop and web surfaces」，属旁证，且是 Claude 桌面/网页面，不是 CLI。

**两边差异**：Claude Code 能用位置/命名参数把动作变成结构化输入，合并入口的分辨落在替换层；Codex 只能靠模型读自由文本，合并入口的分辨完全落在模型。description 预算的压力方向相反：Claude Code 上用户调用的 skill 无预算问题，Codex 上每个 skill 都占列表。

## 5. 两个已知缺陷在两边怎么规避；「改 skill 必改路由」的落点

### 5.1 缺陷一：报「未安装」

机理（`插件:docs/engineering/ask-matt.md:56`）：被路由指向的 skill 多数 `disable-model-invocation: true`，harness 不把它们放进模型的 skill 列表，模型把列表当全集。

- **Claude Code**：文档同时给了根因与模型会得到的提示：「Description not in context」「removes the skill from Claude's context entirely」「expect Claude to suggest running `/deploy` yourself」。可用的规避：(i) 路由正文自持清单（#7 文与 #11 §5 已记）；(ii) 路由展开时用 `!`ls ${CLAUDE_PLUGIN_ROOT}/skills`` 之类把**真实安装目录**读进正文，让「装了什么」成为事实而非记忆（`${CLAUDE_PLUGIN_ROOT}`「Substituted only in plugin skills」；非插件时用 `${CLAUDE_SKILL_DIR}/..`）；(iii) `skillOverrides` 不适用于插件 skill。
- **Codex**：`allow_implicit_invocation: false` 的 skill 是否仍在列表，文档未说、#11 **推测**在；若在，则「未安装」不会发生；系统提示还规定「Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback」（`catalog_prompt.rs:26`），即模型被要求报告而非静默改道。CHANGELOG 1.2.2 #766 记录 `writing-for-agents` 在 Codex 上被 `allow_implicit_invocation: false`「filtered … out of the model-visible skills list, so its description could not trigger it — only an explicit `$writing-for-agents` mention worked」，这条旁证与 #11 的推测**相反**，说明至少某版本 Codex 会把该 skill 从模型可见列表滤掉；哪一种是当前行为**未核实**。

### 5.2 缺陷二：按一行摘要断言对方行为

机理（`ask-matt.md:60`）：路由从不打开对方 `SKILL.md`，凭自己的一句话断言；验收项要求「Any claim it makes about another skill's behaviour shows up in the trace as it reading that skill's `SKILL.md`」（`ask-matt.md:83`）。

- **Claude Code**：(i) 正文写明「断言前先 Read 对方 SKILL.md」，是提示词层；(ii) `!`cat ${CLAUDE_PLUGIN_ROOT}/skills/<x>/SKILL.md`` 在展开时把对方原文整段并入路由正文，是机制层，代价是路由每次调用都加载全部被指 skill 的正文（`!`cmd`` 失败会中止整个调用）；(iii) `context: fork` + 子代理 `skills:` 预载不可用于用户调用的 skill。
- **Codex**：系统提示已经要求主代理「read its `SKILL.md` completely before taking task actions」且「Do not delegate reading … to a subagent」（`catalog_prompt.rs:28-30`）；列表自带 path。路由正文只需给出名字，读取由平台提示词兜底；但这条只约束「决定使用」的 skill，路由**描述**别的 skill 时不在此列，仍靠路由正文自己要求。

### 5.3 `CLAUDE.md`「改 skill 必改路由」在本项目的落点

插件规则原文（`插件:CLAUDE.md`）：「whenever you add, rename, remove, or change how a user-reachable skill fits the flows, re-read `ask-matt`'s `SKILL.md` and update it so the map stays accurate: a new skill it never mentions, or a stale one it still routes to, is a router that lies.」

本项目的事实约束：`AGENTS.md`「其余规则尚未建立。一条规则只在真实使用里被违反过一次之后才写进本文件。」所以这条规则**现在不能进 `AGENTS.md`**。#7 文 §4 已记「落点在 skill 清单票之后」；`docs/3.0-wayfinder起手.md`「Not yet specified」里有「规则元规则：规则如何进入 AGENTS.md … 等 7 之后看」。现有可放的位置只有：路由 skill 自己的文件（插件把它放在仓库根 `CLAUDE.md`，不放在 ask-matt 里）、#9 的 skill 清单产物、或等待一次真实违反。这是三个事实位置，不是推荐。

**两边差异**：缺陷一在 Claude Code 是平台设计的必然，规避只能在路由侧（自持清单或 `!`cmd`` 读目录）；在 Codex 取决于列表是否过滤，两条一手材料互相矛盾。缺陷二在 Codex 有平台提示词兜底一半，在 Claude Code 全靠路由正文或 `!`cmd`` 并入原文。

## 6. 对 #7 / #9 的事实输入（不作决策）

1. **参数形态**：Claude Code 有 `$ARGUMENTS` / `$N` / `arguments:`，多词值须引号；Codex 的 skill 无参数，`$name` 后文本即用户消息。一份 SKILL.md 若写 `$0`，在 Codex 是普通文本。
2. **中文名**：Claude Code 文档未述；agentskills 规范要求 `a-z 0-9 -` 且与目录名一致；Codex `$` 提及只认 ASCII。中文只能进 `display_name` / `argument-hint` / 参数值。
3. **路由能不能替人按下去**：Claude Code 上对用户调用的 skill 不能（硬拦），对模型可调的 skill 可以带参数调；Codex 上路由无法显式触发（**推测**），只能给出 `$name` 让人打。
4. **跨会话**：两边都没有「排队给下一会话」机制；有的是 `claude "/skill 参数"` / `claude -p "/skill 参数"` / `--resume` 与 `codex exec` / `codex resume` / `codex fork`；Claude Code 另有 SessionStart / UserPromptSubmit / UserPromptExpansion hook 可在新会话启动或 `/x` 展开时补入或替换提示词，hook 是 harness 配置，不随 skill 走。
5. **互指写法的交集**：两边都可读的只有「Call the Skill tool with "x"」散文与「spawn a sub-agent」散文（插件 1.2.3 已把 Claude 专名从派发语句里删掉）；`context: fork`、`skills:` 预载、`!`cmd`` 是 Claude Code 独有；`$name`、`default_prompt` 是 Codex 独有。
6. **用户调用的 skill 之间共享参考**：Claude Code 上两者都不能经 Skill tool 到达对方，插件作者的做法是放到 skill 系统之外的普通文件；Codex 上无此硬约束但也无参数。
7. **合并入口的分辨层**：Claude Code 在替换层（`$0`），Codex 在模型层（自由文本）；description 预算对 Claude Code 的用户调用 skill 无效，对 Codex 的每个 skill 都有效（列表截断先砍描述、再整条省略）。
8. **缺陷规避的机制位**：Claude Code 有 `!`cmd`` 可在展开时读真实目录与对方原文（失败即中止调用，`disableSkillShellExecution` 可被策略关闭）；Codex 平台提示词已要求「用前完整读 SKILL.md」「点名 skill 不在列表要说明」，且列表带 path。
9. **维护规则的位置**：`AGENTS.md` 的元规则挡住「改 skill 必改路由」现在入本文件；可选位置是路由 skill 自身、#9 清单产物、或等一次真实违反。

## 7. 未核实清单

- agentskills.io 站点本次不可达，规范读的是仓库源文件；「unicode lowercase alphanumeric」与 `a-z` 的矛盾未有官方解释。
- Codex 当前版本是否把 `allow_implicit_invocation: false` 的 skill 从模型可见列表过滤（#11 推测「在」，插件 CHANGELOG #766 旁证「被滤掉」）。
- Codex `codex exec` 提示词里 `$name` 是否被解析为提及；`interface.default_prompt` 在 CLI 的实际注入点；Codex hook 文档；`/agent` 与 skill 的关系。
- Claude Code skill 正文里 `@path` 是否展开；`/fork` 能否经 Skill tool 调用；从 skill 的 Bash 步骤起 `claude -p` 嵌套会话的行为。
- 两边关于合并入口与拆分入口触发准确率的任何官方数据。

## 8. 来源清单（均 2026-09-05 访问）

插件原文（本机 1.2.3）：`skills/engineering/ask-matt/{SKILL.md,PHASE-BOUNDARIES.md,agents/openai.yaml}`、`.agents/{invocation.md,writing-docs.md,install-block.md}`、`.agents/adr/0001`、`0002`、`skills/productivity/writing-for-agents/{SKILL.md,SKILL-MECHANICS.md}`、`skills/productivity/{handoff,grill-me,teach}/SKILL.md`、`skills/engineering/{grill-with-docs,tdd,triage,wayfinder,code-review,to-spec,to-tickets,research,improve-codebase-architecture}/SKILL.md`、`skills/in-progress/{claude-handoff,loop-me,setup-ts-deep-modules}/SKILL.md`、`CLAUDE.md`、`CHANGELOG.md`（1.2.0 #551/#680/#763、1.2.2 #766、1.2.3 #781）、`.claude-plugin/plugin.json`、`docs/engineering/ask-matt.md`、`scripts/link-skills.sh`。

Claude Code：
- https://code.claude.com/docs/en/skills（参数替换、无占位符追加、引号分词、Skill tool 与 `disable-model-invocation` 硬拦、`context: fork` / `agent:` / `background`、`!`cmd``、`when_to_use` 与 1,536 字、`user-invocable`、`${CLAUDE_*}`、命令名来源）
- https://code.claude.com/docs/en/slash-commands（命令并入 skill、叠加 skill、权限语法）
- https://code.claude.com/docs/en/sub-agents（`skills:` 预载、不能预载 `disable-model-invocation`、子代理可调 Skill tool、fork 语义）
- https://code.claude.com/docs/en/plugins-reference（`plugin:skill` 命名空间、`${CLAUDE_PLUGIN_ROOT}`、插件 agents/hooks）
- https://code.claude.com/docs/en/headless（`-p` 接受 `/skill-name`、`--continue`/`--resume`、`--bare`、`--cloud` 排队）
- https://code.claude.com/docs/en/cli-reference（`--resume`、`--session-id`、`--fork-session`、`--bg`、`claude "query"`）
- https://code.claude.com/docs/en/sessions（`/branch`、`/clear [name]`、`/compact [instructions]`、`claude -p --resume`）
- https://code.claude.com/docs/en/commands（命令解析、`/fork [prompt]`、`/loop`）
- https://code.claude.com/docs/en/hooks（SessionStart、UserPromptSubmit `updatedPrompt`、UserPromptExpansion）
- https://code.claude.com/docs/en/scheduled-tasks（`/loop` 与 `disable-model-invocation` skill）
- https://code.claude.com/docs/en/common-workflows（`@` 引用、`--worktree`、管道）

Codex：
- https://developers.openai.com/codex/skills → 308 → https://learn.chatgpt.com/docs/build-skills（`$` 提及、`/skills`、`agents/openai.yaml` 全字段、2% / 8,000 字）
- https://learn.chatgpt.com/docs/custom-prompts（已弃用的 `$1..$9` / `KEY=value` / `$ARGUMENTS`）
- https://learn.chatgpt.com/docs/developer-commands.md?surface=cli（`codex exec` / `resume` / `fork`、TUI 命令表）
- https://learn.chatgpt.com/docs/config-file/config-reference.md（`skills.max_context_tokens`、`skills.config`）
- 源码 `openai/codex@ddf04ad`：`codex-rs/skills/src/mentions.rs`、`codex-rs/ext/skills/src/{selection.rs,fragments.rs,catalog_prompt.rs,extension.rs}`、`codex-rs/protocol/src/user_input.rs`

规范：`agentskills/agentskills@69ef37e` `docs/specification.mdx`（agentskills.io/specification 的源文件）。
