---
"loo0ng-skills": patch
---

图引擎与雏形在 python 3.9 上写得成图（#61）：`Path.write_text` 的 `newline=` 是 3.10 才加的，而律师那台 mac 的 `/usr/bin/python3` 是 3.9.6，于是唯一写图路径 `write_text_atomic` 每次都抛 TypeError，起手、追加条目、改构成、雏形拍板全部写不成图。`graph.py` 与 `sketch.py` 两处改成显式 `open(..., newline=)`，`newline` 的语义（不让 Windows 把换行翻成 CRLF）一字不变，行为无改动，所以是 patch。同因的第三处在票外：`evals/种子/回流/回放.py` 不随包分发，但 `replay_seed` 用跑测试的那个解释器起它，#61 的验收里 `tests/loo0ng-domain/test_seeds.py` 就卡在它上面，一并改了。新增 `tests/python-floor/`：按 3.9 的 feature_version 解析这两批文件、再按名字拦 `write_text/read_text` 的 `newline=`，让这条版本地板不必靠人记；别的 3.10 API 等真栽了再加（ADR-0015：事故先红后绿）。`docs/agents/skills.md` 的「命名与编码」段随之多一行。
