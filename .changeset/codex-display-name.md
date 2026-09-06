---
"loo0ng-skills": patch
---

Codex `$` 补全里的显示名改为 skill 名：四件 `SKILL.md` 的 `metadata.display-name` 改成各自的 `name`，`agents/openai.yaml` 重生成；生成器加一条校验，`display-name` 不等于目录名即报错（ADR-0009 附注，#29 真实触发时发现律师按 `loo0ng-` 名字找不到中文显示名）。短描述保留中文。
