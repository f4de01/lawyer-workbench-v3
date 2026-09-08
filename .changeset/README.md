# Changesets

本目录由 `@changesets/cli` 管理。每次改 skill（改名、改功能、增删）都是一次发布（ADR-0009）：

1. `npm run changeset`：选 patch / minor / major，写一段面向读者的变更说明；生成一个 `.changeset/*.md`，随改动一起提交。**说明里带上本票的 issue 号**（`（#75）` 或 `随 #62 改写` 都行）：结算之后这段话就是 `CHANGELOG.md` 里的一条，issue 号是它唯一的溯源锚点。
2. `npm run version`：把待发布的 changeset 合成 `CHANGELOG.md` 条目、升 `package.json` 的版本，再由 `scripts/sync-plugin-version.py` 把同一版本写进 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`。跑之前先读下面「攒了几份再结算」。
3. 提交、打 tag：`git tag -a v<版本> -m "…"` 加 `git push origin v<版本>`，tag 打在合进 `main` 之后的那个 commit 上（首例见 `v0.1.0`）。

`npm run check-plugin-version` 只检查三处版本是否一致，不改文件。完整登记步骤见 `docs/agents/skills.md`。

## 攒了几份再结算（#82 的教训）

一次结算掉多份 changeset 时，合出来的那一节是律师和后来者唯一会读的东西，值得在跑 `npm run version` 之前先摆一摆。首发 0.1.0 一次吃掉 19 份，栽在两件事上：

- **顺序**。changesets 按文件名读目录，不按时间。19 份按文件名排下来，「领域图『破产』」排在建 `loo0ng-domain` 那条前面、三值门禁排在建门禁那条前面，从上往下读不通。办法是先给文件加两位序号前缀（`01-graph-engine.md`…），按各自落地的先后排，Minor 与 Patch 两节就各自成时间序。前缀只活到 `changeset version` 把文件吃掉为止，最终 diff 里不留痕、不留约定。
- **锚点**。默认生成器（`config.json` 里的 `@changesets/cli/changelog`）会给每条前缀一个 commit hash，那个 hash 来自「加进这份 changeset 的那个 commit」；**文件一改名就查不到，前缀随之消失**。所以第 1 步要求 issue 号写进正文：它比 hash 好查，也不受改名影响。

结算前把 `CHANGELOG.md` 那一节从头读一遍。要改就改 changeset 再重跑，别去手改 `CHANGELOG.md`：`git restore .` 可以把 `changeset version` 干的事整个撤回（`.changeset/*.md` 回来、三处版本回落），改完再跑一次。这一趟里改掉的还有一处死引用：某条正文指着另一份同批被消费掉的 changeset 文件名，读者无从查起，改成指 issue 号。
