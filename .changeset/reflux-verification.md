---
"loo0ng-skills": patch
---

回流有了验收层（#34，ADR-0012）：机制本身（`sketch.py from-case` 与 `references/回流.md`）随 #30 已在，这一票只补验证，`skills/` 下除 `references/回流.md` 多一行「跑两侧的用例「回流」」外没有行为改动，所以是 patch；真正的一次回流改的是 `assets/<领域>/领域图.json`，那一次才是 minor。新增种子「回流」：借跑器的 `replay_seed` 把种子「在办中」摊进 `案件/`，再加两个律师自加节点（一个已确认、一个只生成，标题都带着本案的当事人与日期），工作区根另有破产领域图的可写副本与一份 `基线.json`（案件图与领域图的 sha256、领域图的模块数与节点数）；副本而不是 `skills/` 下那份原件，一次 eval 不该动到仓库里的领域图（ADR-0015），基线让断言不必硬写「72 个节点」。新增用例「回流」：开发者一句话给案件工作区的路径，两侧都是裸提示词，断言回显清单标出了去案件化后的标题、领域图恰好多出那一个节点且排在模块末尾、id 与案件图一致、条目为空、只生成没拍板的那个没回流、案件图字节不变、雏形文件没落进工作区。`tests/loo0ng-domain/test_seeds.py` 复核种子状态与 `from-case` 恰好提出已确认的那一个；`test_sketch.py` 加一条「`from-case` 与 `check --kind domain` 两张图的字节都不变」，即拍板前领域图一字不动；`test_isolation.py` 加一条会话边界，律师面对的三个入口（含还没建的 `ask-loo0ng`）的正文里出现「回流」即报红。分支加 PR 那一道不进 eval：隐私钩子在 `main` 上守 `loo0ng-domain/assets/` 下的图由 `tests/privacy-check` 覆盖，第二双眼是另一会话的 AFK 代理审 diff。
