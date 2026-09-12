# Changesets

本目录由 `@changesets/cli` 管理。每次改 skill（改名、改功能、增删）都是一次发布（ADR-0009）：

1. `npm run changeset`：选 patch / minor / major，写一段面向读者的变更说明；生成一个 `.changeset/*.md`，随改动一起提交。**说明里带上本票的 issue 号**（`（#75）` 或 `随 #62 改写` 都行）：结算之后这段话就是 `CHANGELOG.md` 里的一条，issue 号是它唯一的溯源锚点。
2. **结算交给 GitHub Actions**（`.github/workflows/release.yml`，#96）：Actions -> release -> Run workflow，**先按默认的干跑跑一次**。干跑把 changeset 结算完、把包打出来，但不提交、不打 tag、不发 Release；结算出来的那一节 CHANGELOG 摆在 job summary 里，读它；要读什么见下面「攒了几份再结算」。不顺就回去改 changeset 再干跑一次，别手改 `CHANGELOG.md`。
3. 读顺了，在 `main` 上再跑一次、把 `dry_run` 关掉。它做的是：`npm run version`（= `changeset version` 合成 `CHANGELOG.md` 条目、升 `package.json` 的版本，再由 `scripts/sync-plugin-version.py` 把同一版本写进 `.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` 与 `package-lock.json`，后者是根与 packages 里本包那两处、依赖一个字不动）、提交、打 `v<版本>` tag 推上去、发一个 Release 并附**离线兜底包**（`scripts/pack-offline.py` 按登记清单打的七件 skill，LF、无 BOM，`docs/交付/现场清单.md` 段 0 P2 要的就是它）。

   两道闸门卡在结算前后（`scripts/release.py preflight` / `postflight`，测试在 `tests/release/`）：`agents/openai.yaml` 与 frontmatter 不同步、版本三处不齐、没有待结算的 changeset、工作树不干净、结算后版本没变、changeset 没被吃干净、`CHANGELOG.md` 缺这一节、tag 已经在了，任一条即停，不会推出半拉的一版。

   **手工路仍然通**（断网、Actions 坏了、或就是想在本机看看）：`npm run version`，提交，`git tag -a v<版本> -m "…"` 加 `git push origin v<版本>`，tag 打在合进 `main` 之后的那个 commit 上（首例见 `v0.1.0`，那一次全程手工）。想在本机干跑一遍同样的判断：`python scripts/release.py preflight` -> `npm run version` -> `python scripts/release.py postflight --previous <结算前的版本>`，看完 `git restore .` 撤回。

`npm run check-plugin-version` 只检查两份插件清单与 `package-lock.json` 有没有跟上 `package.json`，不改文件。完整登记步骤见 `docs/agents/skills.md`。

## 攒了几份再结算（#82 的教训）

一次结算掉多份 changeset 时，合出来的那一节是律师和后来者唯一会读的东西，值得在跑 `npm run version` 之前先摆一摆。首发 0.1.0 一次吃掉 19 份，栽在两件事上：

- **顺序**。changesets 按文件名读目录，不按时间。19 份按文件名排下来，「领域图『破产』」排在建 `loo0ng-domain` 那条前面、三值门禁排在建门禁那条前面，从上往下读不通。办法是先给文件加两位序号前缀（`01-graph-engine.md`…），按各自落地的先后排，Minor 与 Patch 两节就各自成时间序。前缀只活到 `changeset version` 把文件吃掉为止，最终 diff 里不留痕、不留约定。
- **锚点**。默认生成器（`config.json` 里的 `@changesets/cli/changelog`）会给每条前缀一个 commit hash，那个 hash 来自「加进这份 changeset 的那个 commit」；**文件一改名就查不到，前缀随之消失**。所以第 1 步要求 issue 号写进正文：它比 hash 好查，也不受改名影响。

结算前把 `CHANGELOG.md` 那一节从头读一遍（走 workflow 时读的是干跑那次 job summary 里的它，本机一个字没改，不用撤）。要改就改 changeset 再重跑，别去手改 `CHANGELOG.md`：在本机跑过的话 `git restore .` 可以把 `changeset version` 干的事整个撤回（`.changeset/*.md` 回来、各处版本回落），改完再跑一次。这一趟里改掉的还有一处死引用：某条正文指着另一份同批被消费掉的 changeset 文件名，读者无从查起，改成指 issue 号。
