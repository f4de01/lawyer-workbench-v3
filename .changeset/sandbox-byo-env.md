---
"loo0ng-skills": patch
---

受限沙箱（Codex `workspace-write`）下 agent 自备环境**实测成立**，`evals` 里为绕开它而标着全权限的那 11 个用例全部改回默认的 `workspace-write`（#78，ADR-0018 明写的两处未验之一）。此前只在 Full access 下成过一次，跑器因此让凡要跑本仓库 CLI 的 Codex 用例都提权，绕法自 #28 起、#62 复验过一次。

实测（Codex CLI 0.153.4、uv 0.12.1、Windows 11，同一份探针脚本沙箱内外各跑一次，逐条记退出码）：沙箱里 `where.exe python` / `py` / `python3` 三条全空，这条老观察成立；但根因不是 PATH 而是 **ACL**：LocalAppData 下那个 Python 目录与 WindowsApps 的权限继承是断的，沙箱账户读不到，而 uv 自己与它管的解释器落在 Roaming 与 `~/.local/bin` 下，继承得到沙箱账户的读写权，所以 `uv --version`、`uv python find`、`uv pip install --target <临时目录>`、`PYTHONPATH` 指过去 `import docx`、转换器出件、门禁给结论，退出码与沙箱外逐条相同，产物是合规的 OOXML 包、门禁通过。11 个用例改回默认值后一次全绿，回合数 9 至 18、64 至 235 秒，比原先在全权限下记的还低（`起手` 27 至 38 → 16 至 17，`办节点出一版` 39 至 47 → 14 至 18）：模型在沙箱里直奔 uv，反而不再花回合去试那些读不到的解释器。

结论是**有条件成立**，三个条件写进了跑器的注释与 `docs/agents/skills.md` 的键说明：uv 得在沙箱账户读得到的地方；至少已有一个 uv 管的解释器（`uv python install` 在沙箱里写不了 uv 的锁文件，装不了新的）；uv 的缓存要指到能写的地方（默认缓存在 LocalAppData 下，沙箱里初始化即拒绝访问）。沙箱能写的只有工作区与 `%TEMP%`，用户主目录与 uv 默认缓存都写不了；网络本身没被拦（uv 冷缓存下真下载了 lxml），拦住的是走 Windows Schannel 的 TLS 客户端（`curl.exe` 报 `SEC_E_NO_CREDENTIALS`，`Invoke-WebRequest` 连接被关闭），uv 自带 TLS 栈所以不受影响。

`danger-full-access` 这个值留在跑器里不删：它是跑器的能力，不再是任何用例的前提。ADR-0018 的裁定一条没动；`loo0ng-to-docx` 的 `SKILL.md` 只把「受限沙箱与 mac 都尚未验证」那半句改成受限沙箱已验、mac 仍未验（#79）。
