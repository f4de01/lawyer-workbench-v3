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

- （尚无）

**Model-invoked**

参考 skill 由模型够到，律师无需记名：律师一句话说到相关的事，模型自行调用。

- `loo0ng-graph`（图引擎）：`图.json` 的唯一写入口。律师一句话改图的构成（加节点、改标题、调顺序、跨模块移动、改空白模板、增删改模块、节点或模块不适用）由它落盘并回显；编排 skill 经它追加生成与确认条目；每次写图后重算 `图视图.md` 与 `图视图.json`。

## 维护

登记步骤、三条校验命令与测试命令见 `docs/agents/skills.md`。发布走 changesets（`.changeset/README.md`），版本记录在 `CHANGELOG.md`，`package.json` 与两份插件清单的版本由 `scripts/sync-plugin-version.py` 同步。
