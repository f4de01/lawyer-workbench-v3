# 律师工作台 3.0

破产业务先行的法律工作台，以 skill 形态构建，在 Claude Code 与 Codex 两个 harness 上都能触发。律师面对两个入口加一个可选路由；四个参考 skill 由模型按律师一句话自行够到。案件材料永不进本仓库（`AGENTS.md` 硬边界 1）。词汇以 `CONTEXT.md` 为准，决策在 `docs/adr/`。

## 安装

两条路二选一：插件是只读的整包订阅，skills.sh 把 skill 文件拷进你的项目由你改。两条都装，每件 skill 会出现两次。

<details>
<summary><strong>Claude Code：插件</strong></summary>

本仓库自成单插件市场（`.claude-plugin/marketplace.json`），在会话里：

```
/plugin marketplace add f4de01/lawyer-workbench-v3
/plugin install loo0ng-skills@loo0ng-marketplace
```

`owner/repo` 形式只取默认分支；要装某个分支，用 `https://github.com/f4de01/lawyer-workbench-v3.git#<branch>`。私有仓库凭本机 gh 或 git 凭据克隆。装上后 skill 名带 `loo0ng-skills:` 前缀，例如 `/loo0ng-skills:ask-loo0ng`。

</details>

<details>
<summary><strong>Codex 及其他 agent：skills.sh</strong></summary>

```bash
npx skills@latest add f4de01/lawyer-workbench-v3 -a codex -a claude-code
```

安装器让你挑 skill 与目标 agent；`-a` 可重复，一次装到两个 harness。`.codex-plugin/plugin.json` 指向 `skills/`，也可经 Codex 插件市场安装（`codex plugin marketplace add`，再 `codex plugin add`）。

</details>

<details>
<summary><strong>开发者本机：junction</strong></summary>

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1
```

把 `skills/<name>/` 逐条以 junction 挂到 `~/.claude/skills/` 与 `~/.agents/skills/`，顺手设 `core.hooksPath` 启用隐私钩子。改 skill 内容即时生效；只在改名、增删 skill 后重跑。与插件同装时 Codex 会列出同名两条。

</details>

## Skill 清单

按谁能触发分两组。八件的名单与分工见 ADR-0009；两组随实现票逐件填入。

**User-invoked**

律师打名字触发：Claude Code 里是 `/名 …`，Codex 里是 `$名 …`。这一组只做编排，模型不会自己调用它们。

- `loo0ng-setup-case`（起手）：在一个空目录里长出案件工作区，一案一次。一条命令落下六格（`收件箱/`、`材料/律师陈述/`、`指南/`、`模板/官方/`、`模板/生成/`、`文书/`）、起手图三选一（空图、整份领域图、开发者交付的定制图）、起手图挂到的官方模板原件与工作区指针块（`AGENTS.md` 记领域目录绝对路径、图与视图文件名、入口名与只读声明，`CLAUDE.md` 一行引它）；再归档收件箱、`指南/` 非空则跑一次雏形，末尾把雏形与既有成品的建议登记合成一张起手清单，律师一句话拍板后才写图。既有成品登记为已生成、来源律师，确认永不自动。
- `loo0ng-doit`（办节点）：一个对话办一个节点。律师一句自由文本说动作加节点：「出一版 X」走归档、复制律师指的文件、惰性建节点、整读材料指南模板与过往文书、写 Markdown 最小集、转换、门禁、落盘 `文书/<节点标题>/` 三件、经图引擎追加生成条目、回显审查报告要点；「X 我自己写好了」跑一次只披露不阻断的门禁后登记为已生成、来源律师；「确认 X」「X 不适用」「模块 Y 不适用」经引擎落一条原样存着律师那句话的条目。生成不问缺事实，缺项进审查报告的待律师裁定，律师答一句先落成陈述再重出。拍板也在这个对话里说，下一个节点开新对话。
- `ask-loo0ng`（问路）：随时可问的只读地图，可选，永远不是流程里的一步。读 `图.json` 与按顶层「领域」名找到的领域图（靠 id 对应），答当前节点（已生成待确认，可复数）、上一完成（仍处于已确认里确认最晚的）、下一任务（先列全部待确认，再由五问有序决策树定一个，回复里标出命中哪一问）；再给往下的路（每步标出拍板点、要不要开新对话，带时限的节点原样附上那句话）、相近入口的分界线，最后给下一句该打的整串（`/名 …` 或 `$名 …`，裸名），然后停。它自持入口表不读目录，不触发 skill、不写图、不替律师按下去；说的事在图里对不上就说对不上并指向 `loo0ng-doit`，不编入口。

**Model-invoked**

参考 skill 由模型够到，律师无需记名：律师一句话说到相关的事，模型自行调用。

- `loo0ng-graph`（图引擎）：`图.json` 的唯一写入口。律师一句话改图的构成（加节点、改标题、调顺序、跨模块移动、改空白模板、增删改模块、节点或模块不适用）由它落盘并回显；编排 skill 经它追加生成与确认条目；每次写图后重算 `图视图.md` 与 `图视图.json`。
- `loo0ng-domain`（领域目录与雏形）：领域目录三样的家（`assets/<领域>/` 下的领域图、官方模板原件、指引手册原文；内置「破产」，领域图 12 模块 72 节点，由两份通用指引手册跑雏形长出）与雏形机制的零依赖 CLI。模型整读指南或指引手册写成雏形文件，`check` 按标题判重（同名不重复提出、相似不同名列为待定）并回显清单、图一字不动，律师一句话拍板后 `apply` 逐条经图引擎写入；`from-case` 从案件图算回流候选、保留原 id；`docx-text` 把 docx 打成纯文本供整读。它不含领域语义，没有领域图也能从空图起手。
- `loo0ng-filing`（归档与陈述）：两个零依赖 CLI，互不引用。归档搬运把收件箱里的文件按相对路径原样搬到材料、指南、模板/官方、模板/生成（判断去向归模型，不改名、不覆盖、不越界）；陈述落档把律师在对话里说的一句话落成 `材料/律师陈述/` 下一条一文件、落盘后只读（六字段头部、原话逐字、整条取代）。起手末尾、出一版开场与律师一句话三处进入。
- `loo0ng-to-docx`（出件与门禁）：两个 CLI，互不引用。转换器把模型写的 Markdown 最小集以该节点的官方模板为版式载体转成 DOCX（段落格式与字体照模板，表格的列宽、行高、格式照抄，合并单元格用 `<` `^` 约定），只依赖 python-docx、离线，默认写到临时位置；门禁对任意 DOCX 做只读检查，本体零第三方依赖（静态检查加 CJK 版面推算），有 Word COM 时以真实渲染取代推算的区间；结论三档（通过 / 需人眼 / 不通过），通过与需人眼 `--deliver` 一次性落进 `文书/`，不通过不落盘。缺渲染器不阻断出件，测不准也不算通过（ADR-0017）。审查报告格式、最小集与合并约定在它的 `references/`。

## 维护

登记步骤、三条校验命令与测试命令见 `docs/agents/skills.md`。发布走 changesets（`.changeset/README.md`），版本记录在 `CHANGELOG.md`，`package.json` 与两份插件清单的版本由 `scripts/sync-plugin-version.py` 同步。
