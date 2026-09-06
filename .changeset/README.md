# Changesets

本目录由 `@changesets/cli` 管理。每次改 skill（改名、改功能、增删）都是一次发布（ADR-0009）：

1. `npm run changeset`：选 patch / minor / major，写一段面向读者的变更说明；生成一个 `.changeset/*.md`，随改动一起提交。
2. `npm run version`：把待发布的 changeset 合成 `CHANGELOG.md` 条目、升 `package.json` 的版本，再由 `scripts/sync-plugin-version.py` 把同一版本写进 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`。
3. 提交、打 tag。

`npm run check-plugin-version` 只检查三处版本是否一致，不改文件。完整登记步骤见 `docs/agents/skills.md`。
