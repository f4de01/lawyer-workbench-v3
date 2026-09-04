# legal-skills 独立调研报告（就仓库论仓库）

> **生成方式**：由一个独立调研 agent 在 2026-09-03 生成。该 agent 只被允许读取 legal-skills 的本地克隆，**未读取本项目（律师工作台 3.0）的任何文件**，也不知道本项目的存在。因此本文只描述 legal-skills 本身，不含任何对比。对比见同目录《legal-skills-与本项目交叉对比.md》。
> **对象**：github.com/cat-xierluo/legal-skills，外部公开仓库，与本项目及本项目作者无任何关联，仅业务领域相同。
> **红线**：本文不含案件数据；legal-skills 仓库内出现的真实当事人姓名、内部案件编号一律不转录。

## 0. 元信息

| 项 | 值 | 证据 |
|---|---|---|
| commit | `3a8fdd36…`，提交日期 2026-09-04，标题「fix(multi-agent-orchestration): 封堵 reviewer Update 越界 (#122)」 | `git log -1 --date=short` |
| 历史深度 | 本地克隆只有 1 个 commit（`git rev-list --count HEAD` = 1），作者为仓库署名律师本人；**无法做提交频率/多作者统计** | `git rev-list --count HEAD`、`git log --format=%an` |
| skill 数量 | 63 个（`find skills -maxdepth 2 -name SKILL.md \| wc -l` = 63；`ls skills \| wc -l` = 63） | — |
| 仓库文件数 | 3570（`git ls-tree -r HEAD --name-only \| wc -l`），其中 `.md` 915 个 | — |
| 脚本规模 | 非测试脚本约 12.3 万行，测试脚本约 2.4 万行（`find … ! -path '*test*' \| xargs cat \| wc -l`），有测试文件的 skill 20 个 | — |
| 许可证 | 双轨：MIT（工具类）与 CC-BY-NC（法律专业类）；`skills/*/LICENSE.txt` 55 份 | `README.md` L13-L23「本项目采用两种许可证」；`AGENTS.md` L86-L105 |
| 最近更新 | `skills/multi-agent-orchestration/CHANGELOG.md` 顶部「## [2.15.0] - 2026-09-04」；README 最近更新表首行 2026-09-04 | `README.md` L37 |
| 作者定位（原文） | 「本项目旨在沉淀并分发面向法律工作者的 AI Agent Skills。法律从业者兼具专业工作者与创作者的双重身份——既要处理法律业务，也需要撰写专业文章、整理资料、分享知识。」 | `README.md` L49 |
| 作者自述方向 | 「我正在探索法律领域的 FDE（Forward Deployed Engineer）协作模式：深入真实法律业务场景……」 | `README.md` L5 |

---

## 一、仓库级组织方式

### 1.1 目录布局与 skill 注册方式

- 顶层：`.agents/`、`.claude/`、`.githooks/`、`.github/workflows/`、`docs/`、`skills/`，加 `AGENTS.md`（22 KB）、`CLAUDE.md`（仅一行「@include ./AGENTS.md」）、`README.md`（50 KB）、`.gitattributes`、`.gitignore`。
- **注册方式 = 两条符号链接指向 `skills/`**：`git ls-tree -r HEAD` 中 mode 120000 的条目恰好 2 个，`.claude/skills -> ../skills`、`.agents/skills -> ../skills`（`git cat-file -p` 读取的链接目标）。也就是说 Claude Code 与 Codex 风格的 `.agents/` 共用同一份 `skills/` 树，不做复制。Windows 克隆下这两处表现为空目录。
- `.gitignore` L12「Claude Code config - selective sync (keep skills symlink, ignore rest)」、L19「Agent config - keep skills symlink, ignore runtime files」印证这是有意设计。
- **没有路由型 skill，也没有机器可读索引**。索引只有 README 的 HTML 表格（分「内容获取 / 法律专业应用 / 内容处理 / 个人效率 / 开发工具」五节，`README.md` L78/L179/L361/L507/L536）。README 表格只收录 57 个 skill，**6 个未入表**：case-dashboard、case-progress、dsh-plugin-lint、elements-complaint-generator、lecture-review、workbuddy-checkin（`comm -23 <(ls skills) <(grep -o 'href="skills/…' README.md)`）。elements-complaint-generator 只出现在"最近更新"区（`README.md` L38）。
- 私有目录约定：`AGENTS.md` L429-L436「私有 Skill（`private-skills/`）与 Customer Skill（`custom-skills/`）均为本地私有符号链接目录」；`.gitignore` L130、L184 忽略之。
- `skill-manager` 有安装注册表 `assets/skill-registry.json`（`skills/skill-manager/SKILL.md` L142），但那是消费侧运行时文件，不是仓库索引。

### 1.2 SKILL.md frontmatter 约定

统计口径：解析 63 个 `skills/*/SKILL.md` 首个 `---` 块，按顶层键名计数（脚本见调研过程，`re.match(r'^[a-zA-Z_-]+:', line)`）。

| 字段 | 出现数 | 说明 |
|---|---|---|
| name / description | 63 / 63 | 全覆盖 |
| license | 62 | 缺 lecture-review。取值不统一：`MIT`、`CC-BY-NC`、`Complete terms in LICENSE.txt`（5 个）、`MIT License - 详见 LICENSE.txt`（2 个） |
| version | 58 | 5 个缺：de-ai-polish、multi-agent-orchestration（二者把 version 塞进 `metadata:` 子块）、lecture-review、release-workflow、video-compressor。引号风格混用（`"1.0.0"` 与 `1.0.0`） |
| author | 57 | 固定值（仓库作者署名，附微信号，此处不转录） |
| homepage | 55 | 固定仓库 URL |
| metadata | 3 | de-ai-polish、dingtalk-minutes、multi-agent-orchestration 用嵌套 `metadata: {version, homepage, author}` |
| disable-model-invocation | 1 | 仅 legal-proposal-generator（`SKILL.md` L8 `disable-model-invocation: true`） |

规范来源：`AGENTS.md` L322-L351「ClawHub 发布适配」定义 name/description 必填，version/homepage 推荐；`docs/SKILL-DEV-GUIDE.md` L196「普通 Skill 只硬性要求 name、description；version、license、author、homepage 等发布元数据按项目规则添加」。

**版本字段与 CHANGELOG 顶部版本不一致**（frontmatter vs `CHANGELOG.md` 首个 `## [x]`）：case-dashboard 0.1.0 vs 0.9.0；case-progress 0.1.0 vs 0.8.1；litigation-analysis 1.3.2 vs 1.4.0；legal-qa-extractor 1.0.0 vs 1.1.0；tingwu-asr 0.1.0 vs 0.4.1；github-star-manager 0.6.1 vs 0.6.2；svg-article-illustrator 1.0.4 vs 1.0.5；course-generator 2.9.3 vs README 写 v2.9.4。发布脚本以 CHANGELOG 为准（`skills/release-workflow/scripts/build-zips.sh` L49-L62 从 CHANGELOG 头部读 semver），frontmatter 的 version 实际上没有被任何流程校验（推测）。

### 1.3 description 写法规律

统计（同一脚本）：63 条中 52 条含触发短语（「本技能应在…时使用」「当用户…」「触发词」「Use when」），34 条含负向触发（「不要用于」「不适用」「不做」等），9 条点名邻居 skill（如 case-progress 点名 case-dashboard、new-case；course-generator 点名 article2book、lecture-review、transcription-corrector；invoice-organizer 点名 legal-ocr、pdf-processor）。规范：`docs/SKILL-DEV-GUIDE.md` L95-L117「使用第三人称」「添加负向触发条件」「总长度不超过 1024 字符」。最长 394 字（multi-agent-orchestration），最短 28 字。

**好例子**
1. `skills/case-progress/SKILL.md` L7：功能（「case.yaml 的唯一写入引擎」）+ 触发（「更新案件进度/推进任务/登记期限…」）+ 负向互指（「不要用于：看板展示与周研判（用 case-dashboard）、案件建档初始化（用 new-case）」）。三要素齐全，邻居边界清楚。
2. `skills/img2pdf/SKILL.md`：「将图片或 PDF 页面按 N 张/页编排为标准化 A4 PDF……本技能应在用户需要将截图……合并为 PDF 时使用。不要用于：OCR 文字识别、PDF 内容编辑、图片格式转换。」短、具体、有负向。
3. `skills/legal-case-analysis/SKILL.md` L7：「它是法律任务的前置分析引擎，不要求每次都生成正式报告。不要用于：单纯 OCR、单纯法条案例检索、单纯 Word 排版转换……」把自身定位（引擎而非出件）说清，并排除三个易混邻居。

**差例子**
1. `skills/litigation-analysis/SKILL.md` L7：「诉讼分析工具 - 判决书深度分析，生成上诉/再审决策支持」，28 字，无触发、无负向；正文 L18-L40 其实有三种场景（起诉状/判决书/庭审笔录），description 没体现。
2. `skills/md2word/SKILL.md` L7：「Markdown转Word文档技能……适用于正式文档、论文、报告等需要规范排版的文档转换。」无触发词、无负向，也不提它是全仓库 Word 出件的公共后端。
3. `skills/github-star-manager/SKILL.md`：「GitHub Star 项目管理工具，支持从内容自动发现并 Star 项目，同步追踪更新，生成可视化 Dashboard」，纯功能罗列。
（另：`skills/elements-complaint-generator/SKILL.md` L3 以英文「Use when」开头混中文，与全仓中文风格不一致。）

### 1.4 skill 分层：人工触发 / 模型自动触发 / 纯参考

- **显式人工触发**：仅 legal-proposal-generator（`disable-model-invocation: true`）。理由见其 `CHANGELOG.md` L7「明确该 skill 需用户主动调用（`/` 触发），禁止模型在普通对话中自动生成法律…」。
- **模型自动触发**：其余 62 个均无该字段，依 description 匹配。其中 case-dashboard、case-progress 同时挂斜杠命令语义（`case-dashboard/SKILL.md` L18「`/dashboard`」，`case-progress/SKILL.md` L21「`/progress` 命令」），但没有对应的 `.claude/commands/`（`.gitignore` L13 忽略该目录）。
- **零脚本、纯提示词+参考资料的 skill**（inventory 脚本文件数 = 0）：code2patent、court-sms、legal-case-analysis、legal-proposal-generator、legal-qa-extractor、litigation-analysis、new-case、transcription-corrector、verification-gate，共 9 个。它们全靠 SKILL.md + `references/` + `templates/` 驱动模型；court-sms 甚至把 curl/Playwright 的操作步骤直接写在 SKILL.md 里（`skills/court-sms/SKILL.md` L116-L238）。
- **重脚本 skill**：multi-agent-orchestration 60 个脚本 2.0 万行、pdf-processor 20 个 1.08 万行、contract-copilot 19 个 6937 行、video-screenshot 8 个 6921 行、skill-lint 4 个 5556 行。
- 依据只有 frontmatter 与目录内容，仓库没有一份"分层清单"。

### 1.5 治理文件：存在情况与执行率

| 文件 | 要求 | 实际 |
|---|---|---|
| AGENTS.md | 根目录，436 行，含 28 版变更历史（L393-L427，v1.0.0 2026-01-07 → v1.9.0 2026-08-09） | 存在 |
| CONTRIBUTING | 无此文件 | — |
| CHANGELOG.md（技能级） | `AGENTS.md` L9「本项目的 CHANGELOG.md、DECISIONS.md、TASKS.md 等文档均为技能级别……不创建项目级别的文档」 | 63/63 存在。篇幅从 9 行（dsh-plugin-lint）到 1491 行（multi-agent-orchestration），contract-copilot 1112、pdf-processor 1176 |
| DECISIONS.md / TASKS.md | `AGENTS.md` L6、L14 要求每个技能目录含之；L165-L172 要求执行时写入 | **`.gitignore` L21-L22 `**/DECISIONS.md` `**/TASKS.md` 全局忽略**；`git ls-tree -r HEAD` 中仅 5 个例外被强制入库：md2word（DECISIONS+TASKS）、multica-skill-update、skill-lint、svg-book-illustrator（DECISIONS）。即 63 个 skill 中 4 个有 DECISIONS.md（6%），1 个有 TASKS.md |
| DEC 引用 | CHANGELOG 里 `DEC-xxx` 引用共 181 处（`grep -o 'DEC-[A-Z]*-\?[0-9]\+' skills/*/CHANGELOG.md \| wc -l`），9 个 SKILL.md 直接链接 DECISIONS.md | 绝大多数被引用的决策文本在公开仓库里**不存在** |
| 发布排除 | `.gitattributes` L16-L17 `**/DECISIONS.md export-ignore`、`**/TASKS.md export-ignore` | 说明作者把这两类文件定位为"开发协作文件"（`docs/SKILL-DEV-GUIDE.md` L36「不属于最终 skill 产品」） |
| README 最近更新区 | `AGENTS.md` L145-L153「只保留最近 8 条」「更新要点必须来自对应 Skill 的 CHANGELOG.md」 | README L35-L44 恰 8 条 |
| 复盘类 | 无统一要求 | `skills/contract-copilot/DEVELOPMENT-RETROSPECTIVE.md`（181 行）、`skills/verification-gate/references/lessons-from-practice.md`（177 行）、`skills/multi-agent-orchestration/references/10-parallel-lessons.md`（791 行）、`skills/elements-complaint-generator/references/qa-checklist.md`（103 行） |

`docs/` 另有 9 份指南共 3698 行（SKILL-DEV-GUIDE 506、SKILL-EVALUATION-GUIDE 481、SKILL-HANDOFF-GUIDE 363、SKILL-ROBUSTNESS-AUDIT-GUIDE 345、EXPERT-SUITE-DESIGN 626 等）。

### 1.6 分发与安装

- **Release**：`.github/workflows/release.yml` 监听 CalVer tag `v20YY.MM.DD*`，调用 `skills/release-workflow/scripts/build-zips.sh` 为每个 skill 打 `<name>-<semver>.zip`，semver 取自 CHANGELOG 头部（L49-L62）；用 `git archive HEAD --worktree-attributes` 使 `.gitattributes` 的 export-ignore 生效（L78），排除 `archive/ downloads/ output/ .claude/ *.db DECISIONS.md TASKS.md` 等（`.gitattributes` L2-L17）。
- **README 下载链接回写**：`.github/workflows/update-readme.yml` 在 release 发布后把 `releases/latest/download/<skill>.zip` 占位替换为真实资产 URL。
- **安装说明**：`README.md` L710-L723，只有一句给 Agent 的自然语言（「请帮我从 GitHub 安装 legal-skills 技能集合」）和"下载 zip 解压复制到 `~/.claude/skills/`"。
- **多平台**：符号链接同时服务 `.claude/` 与 `.agents/`；skill-manager 声称支持「Claude Code、Codex、OpenClaw、WorkBuddy/CodeBuddy 和 QoderWork」（其 description）；skill-publish-sync 同步到「ClawHub、腾讯 SkillHub 与联想开放平台」；README L677 注明「ClawHub 要求 MIT-0」。
- **Marketplace 已停用**：`AGENTS.md` L397 v1.9.0「停用 Cloud Plugin Marketplace，删除 `.claude-plugin/marketplace.json` 与 `plugin.json`」。
- **CI 只覆盖两个 skill**：`skill-lint-harness.yml`（unittest 三个门禁）与 `svg-book-producer-contract.yml`，其余 skill 的测试不在 CI 里跑。

### 1.7 隐私与安全工程

- **pre-commit 隐私守门**：`.githooks/pre-commit`（39 行）对暂存 diff 硬拦截「手机号 / 18 位身份证 / 座机 / 本机绝对路径 / 真实法院案号」（L4、L23-L28），案号正则覆盖「民初|刑初|行初|民终|民申|执|破」；支持本地黑名单 `.githooks/local-denylist`，「该文件通过 .git/info/exclude 排除，本地维护、绝不入库——黑名单放公开仓库等于二次泄露」（L7）。需用户手动 `git config core.hooksPath .githooks`（`README.md` L743）。
- **矛盾之处**：被跟踪的 `.claude/settings.local.json` 内含一条作者本机 `/Users/<用户名>/…` 的 hook 路径（`grep -c '/Users/' .claude/settings.local.json` = 1），正是该钩子第 26 行要拦的模式；推测该文件早于钩子提交或用 `--no-verify` 绕过。
- **敏感信息规范**：`AGENTS.md` L250-L301（.env 模板、提交前检查、泄露应急）；`.gitignore` 大量 `!skills/x/config/*.schema.json` 白名单与 `config/*.local.*` 黑名单（L43-L66）。
- **脱敏规则**：legal-case-analysis 在 `SKILL.md` L47-L60 定义「脱敏输出模式（场景化可选）」+「安全底线」（身份证号、银行账号等「无论是否开启脱敏模式，都不应原样输出」）；legal-qa-extractor `SKILL.md` L28「脱敏处理标准」；13 个 SKILL.md 提到脱敏（`grep -c 脱敏`）。
- **外发检索/云端提示**：yuandian-law-search `SKILL.md` L14「## 数据留存与隐私警示」、L20「敏感内容最小化」；court-sms L12「隐私与合规说明（透明告知，不阻挡执行）」、L16「下载的文书与归档记录会落到本地文件系统……勿提交到公开仓库」；mineru-ocr L164「当前 skill 仅面向官方云端 API」；tingwu-asr L12「逆向封装通义听悟网页端内部 REST API」（无隐私章节）；md2word L134-L139 披露「自动向任意 HTTP/HTTPS 地址发起请求」及 SSRF 风险。
- **静态安全扫描器**：`skills/skill-lint/scripts/security_scan.py`（1404 行）docstring 列出 14 类模式（Data Exfiltration、Credential Access、Prompt Injection、Hardcoded Secrets 等），退出码「1 FAIL（存在 critical 或 high finding）」。

---

## 二、结构上值得作为样板的 skill

### 2.1 elements-complaint-generator（要素式起诉状生成）
- 路径 `skills/elements-complaint-generator/`；文件 2075 个（`templates/` 1878 个解包 OOXML 文件、`references/case-types` 68、`skeletons` 66、`tests` 42）。
- 分工（`SKILL.md` L16-L24「分工铁律」）：「Agent 负责"抽取"……语义理解是 LLM 强项」；「代码负责"填充与客观版式门禁"：fill_template.py 在模板 XML 上做 `<w:t>` 跨 run 精确替换……LLM 不直接修改 OOXML」。
- 脚本 12 个 5484 行（fill_template.py 2942、layout_gate.py 567、extract_from_markdown.py 466）。测试：`tests/run_e2e.sh` + 4 个 smoke 脚本 + 35 个 fixture（`SKILL.md` L109「113 棵树 DOCX 版式静态门禁 + 21 类文书真实 PDF 渲染」）。
- 为何是样板：模板以「解包 OOXML 源码树」入库使「官方版本更新……git diff 直接看到官方改了什么」（L138、L173）；门禁 fail-closed「任一步失败均非零退出，且不覆盖已有目标文件」（L103）；三层 reference（通用/路由/案由，L155-L163）；模板版本与复查日期显式化（L171-L172）。
- 缺陷：`SKILL.md` frontmatter `license: MIT`、`LICENSE.txt` MIT，但其 `README.md` 末尾写「CC-BY-NC」，与 `AGENTS.md` L90「涉及……文书生成……的技能」应用 CC-BY-NC 的规则也冲突；SKILL.md 与 README 覆盖数据不同步（README「精调级 26」vs SKILL.md L187「68/68 全案由精调完毕」）；L218 引用了真实案件当事人姓名，越过了自己的隐私守门。

### 2.2 contract-copilot（合同审查/起草）
- 路径 `skills/contract-copilot/`；123 个文件；`scripts/` 分 `docx/`（document.py 1423、reviewer.py 938）、`review/`（review_runtime.py 679、action_executor.py 674）、`report/`（reporting.py 702、report_docx.py 731）三包，合计 19 个脚本 6937 行；`references/contract-types/` 64 份、固定 12 类。
- 分工：`DEVELOPMENT-RETROSPECTIVE.md` L15「脚本负责 DOCX 精确编辑（批注/修订），AI 负责分析与建议输出」，中间用 `review-plan.json` 作契约（`SKILL.md` L20-L22）。
- 测试 4 个文件（test_runtime_regressions.py 360、test_report_integrity.py 213、contract-calibration 162）。
- 为何是样板：直接编辑 OOXML 而非 python-docx（`scripts/docx/document.py` 只 import 自家 `XMLEditor`/`DOCXSchemaValidator`）；「强制文件交付规则」写明例外条件（`SKILL.md` L16-L33）；有 181 行开发复盘。
- 缺陷：`archive/` 目录随包存在；SKILL.md 413 行偏长；复盘引用的 DEC-001…DEC-062 文本在仓库中不存在。

### 2.3 case-progress + case-dashboard（案件台账与看板）
- 路径 `skills/case-progress/`（5 个文件：`scripts/case_store.py` 2038 行，`references/schema.md` 380 行，`references/contract.md` 70 行）；`skills/case-dashboard/`（4 个文件：`scripts/dashboard_server.py` 933 行，`assets/dashboard.html` 1513 行）。
- 分工：case-progress 是「case.yaml 的唯一写入引擎」，case-dashboard「经 subprocess 调用本 CLI，禁止跨 skill Python import」（`case-progress/SKILL.md` L31；`case-dashboard/SKILL.md` L28）。
- 无测试文件。
- 为何是样板：写入链路「schema 校验 → 行级 source 保护 → flock → 临时文件 + os.replace 原子替换」（`case-progress/SKILL.md` L28）在代码中可对应（`case_store.py` L126 `atomic_write`、L143 `case_lock`、L172 `validate_data`）；「路径解算禁止 `__file__.resolve()`」考虑了符号链接安装（L27）；「运行时数据绝不入 skill 目录（本仓库公开）」（L30）。
- 缺陷：两者 frontmatter 都停在 `version: "0.1.0"`，CHANGELOG 已到 0.8.1/0.9.0；SKILL.md 反复引用「消费项目 SuitAgent `docs/…`」「TASKS.md」等仓库外/未入库文件；`case_lock` 用 `fcntl.flock`（L151），Windows 不可用而文档未说明。

### 2.4 md2word（Markdown → Word 公共后端）
- 路径 `skills/md2word/`；32 个文件；脚本 9 个 4826 行（md2word.py 1437、table_handler.py 1139、formatter.py 504）+ `test_regressions.py` 1144 行；6 个 YAML 预设 + 6 份 theme-notes；是仓库里 4 个保留 DECISIONS.md 的 skill 之一（且唯一有 TASKS.md）。
- 分工：纯代码转换，模型只准备 Markdown；`SKILL.md` L124-L148「所需权限与安全说明」逐项披露本地执行、网络、环境变量、文件访问。
- 为何是样板：预设/主题/模板三分离（L110-L116）；CHANGELOG 480 行记录了三次「### 回退」（见第六节）；有回归测试。
- 缺陷：description 未写触发与邻居；SKILL.md L157-L179 目录树漏列 footnote_handler.py、svg_handler.py、test_regressions.py；外链图片默认下载（L134）安全上偏松。

### 2.5 skill-lint（Skill 审查器）
- 路径 `skills/skill-lint/`；34 个文件；脚本 4 个 5556 行（instruction_stability_gate.py 2743、security_scan.py 1404、harness_failure_audit.py 958、harness_evidence_gate.py 451），测试 4 个 2185 行；12 份 references 标准文档；是唯一有专属 CI 的 skill（`skill-lint-harness.yml`）。
- 为何是样板：把「不采信生产者自报的 PASS」「客观缺陷 fail-closed；语义质量保留人工判断」写成工作原则（`SKILL.md` L16-L26）；四种模式（创建预检/快速审查/旧版稳定性审查/正式验收，L40-L46）。
- 缺陷：references 里 `skill-dev-guide.md`（513 行）与根 `docs/SKILL-DEV-GUIDE.md`（506 行）近乎重复维护。

### 2.6 legal-industry-report / legal-client-brief（HTML → PDF 出件对）
- 两目录 `scripts/` 11 个文件 3362 行**完全相同**（`diff -rq` 无差异），`references/report-template.html` 亦相同。分工：模型写 Markdown/YAML 内容，`render.py` 渲染 HTML，`pdf.py` 用 Playwright Chromium `page.pdf()`（`legal-industry-report/scripts/pdf.py` L43），`validate_report.py` 校验结构。有 3 个 selftest。
- 为何列入：法律报告的"内容/模板/校验"三分与自测齐全；`SKILL.md` 明确「DRAFT 人工发布门禁」。
- 缺陷：CHANGELOG 自述曾「通过 symlink 复用 Skill 1」（`legal-client-brief/CHANGELOG.md` L88-L92），现已改为整包复制，重复 3362 行代码。

---

## 三、内容层面的 skill 清单（按法律业务阶段）

列格式：名称｜一句话｜脚本｜测试｜内容依赖。

**建档**
- new-case｜诉讼/咨询/商标/专利四类标准目录初始化（`assets/*.yaml` 预设）｜无｜无｜`assets/litigation.yaml` 等 4 预设、`templates/` 9 份、`references/` 3 份
- court-sms｜解析法院短信、下载文书并归档到案件目录｜无（步骤写在 SKILL.md）｜无｜`references/sms-patterns.json`、`config/user-preferences.example.json`
- invoice-organizer｜发票按抬头归档并出报销清单｜2（147 行）｜无｜references

**材料整理**
- legal-ocr｜OCR/文档→Markdown 统一入口｜13（4429 行）｜1｜config
- mineru-ocr｜MinerU 云端 API 转 Markdown｜1（1106 行）｜无｜.env
- paddle-ocr｜PaddleOCR 结构化解析｜6（1145 行）｜1｜config
- pdf-processor｜扫描件预处理/双层 PDF/合并/压缩｜20（10841 行）｜5｜config
- pdf-organizer｜法律 PDF 页面索引、拆分、重命名｜1（1295 行）｜无｜—
- img2pdf｜截图/长图排版为 A4 PDF｜1（496 行）｜无｜—
- video-screenshot｜录屏抽帧、证据线索索引｜8（6921 行）｜无｜config 两份 JSON
- funasr-transcribe / tingwu-asr / dingtalk-minutes｜本地/云端/钉钉转录｜9/10/5｜0/2/0｜config
- transcription-corrector｜按词典纠 ASR｜无｜无｜config.env
- wechat-article-fetch｜抓公众号文章｜1（582 行）｜无｜—
- legal-text-format｜法条/案例文本规范化为 Markdown｜1（365 行）｜无｜archive 机制

**检索**
- yuandian-law-search｜元典法律数据库检索中间层｜4（2810 行；yd_search.py 2417）｜无｜`endpoints/` 接口文档、templates
- patent-download｜专利 PDF 批量下载｜11（1913 行）｜无｜config
- （已归档 zhihe-legal-research，`README.md` L735）

**分析**
- legal-case-analysis｜通用法律分析引擎（民商九步法、刑事二阶层）｜无｜无｜14 份 references、6 份 templates
- litigation-analysis｜起诉状/判决书/庭审笔录三场景分析｜无｜无｜references 5 + domains、templates 3
- contract-copilot｜合同审查/起草，出批注修订版与意见书｜19｜4｜12 类 64 份合同知识、clause-library
- patent-analysis｜权利要求拆解、侵权比对、FTO｜3（1643 行）｜1｜`config/legal-source-register.json`
- trademark-assistant｜商标分类、可注册性初筛｜2（443 行）｜1｜105 文件：尼斯分类 v13、审查审理指南分章、法规
- opc-legal-counsel｜一人公司/小微企业法律分诊｜1（427 行）｜无（有 `evals/` 断言）｜references 11、assets 模板 5
- code2patent｜从代码生成技术交底书/专利初稿｜无｜无｜references、templates

**成文**
- legal-proposal-generator｜诉讼方案/咨询报告/结案汇报等 Markdown｜无｜无｜templates 8 份、`config/team-config.md`（gitignore）
- legal-qa-extractor｜从沟通记录提炼问答知识库｜无｜无｜assets、config
- legal-visualization｜法律关系图/流程图/时间轴（draw.io）｜6（1949 行）｜4｜21 份 references（scene-library、vizspec-schema）、7 类 templates
- de-ai-polish｜去 AI 腔｜7（2134 行）｜3｜config rubric JSON

**出件**
- md2word｜Markdown→Word｜9｜1｜presets 6
- elements-complaint-generator｜要素式起诉状 docx｜12｜7 类 + fixtures｜113 棵 OOXML 模板树、68 案由文档
- legal-industry-report / legal-client-brief｜行业报告/客户简报 PDF｜7/7（同一份代码）｜3/3｜report-template.html、industry-rules

**案件跟踪**
- case-progress｜case.yaml 写入引擎｜1（2038 行）｜无｜`references/schema.md` v4.0
- case-dashboard｜本地看板 + 周研判｜1（933 行）+ HTML｜无｜依赖 case-progress CLI
- apple-smart-schedule｜自然语言→苹果日历/提醒｜5（201 行）｜无｜config

**其他（内容创作/效率/开发工具，共 24 个）**：article2book、course-generator、lecture-review、svg-article-illustrator、svg-book-illustrator、handdrawn-article-illustrator、piclist-upload、video-compressor、douyin-batch-download、universal-media-downloader、agent-email、workbuddy-checkin、github-star-manager、project-init、legal-harness-init、skill-manager、skill-lint、skill-publish-sync、subtree-publish、multica-skill-update、dsh-plugin-lint、verification-gate、git-batch-commit、git-workflow、cross-agent-coordination、multi-agent-orchestration、release-workflow。

**破产/清算/管理人/债权/重整相关内容**（`grep -r -o -E '破产|清算|管理人|债权|重整' skills docs README.md AGENTS.md | wc -l` = 357；分项：破产 23、清算 30、管理人 6、债权 287、重整 11）：
- **没有任何 skill 以破产/重整为主题**。「债权」287 次几乎全是民间借贷、金融借款、担保等语境（elements-complaint-generator `fill_template.py` 14 次、`references/case-types/09-private-lending.md` 5 次、contract-copilot `05-guarantee/*.md` 合计 20 次）。
- 最集中的破产内容在 **legal-visualization**：`references/scene-library.md` L251「## 债务化解、破产重整与执行」，含 DR-02「债权申报与审查流程图」、DR-03「清偿顺位瀑布图……破产费用、共益债务、优先债权、普通债权」、DR-05「重整方案结构图」、RP-07「执行转破产路径图」；`scene-composition-playbook.md` L331-L347 同主题。
- elements-complaint-generator 的 68 个案由里无破产案由，最接近的是 `62-参与分配申请书`、`68-申请不予执行…公证债权文书`。
- 其余只是零星提及：legal-case-analysis `references/civil-commercial-analysis-workflow.md` L27「程序关系：保全、执行异议、执行异议之诉、破产、仲裁」；contract-copilot `contract-routing.md` L193「破产重整投资协议（归入：投资协议）」；yuandian-law-search `endpoints/04-case-semantic-search.md` L31 案件类型枚举含「强制清算与破产案件」；trademark-assistant 审查指南 chapter-11 L33 提到「破产管理人」办理移转。

---

## 四、文书生成机制（内容 → Word/PDF）

| 路径 | 模型做什么 | 代码做什么 | 脚本规模 | 门禁/校验 |
|---|---|---|---|---|
| **A. Markdown → md2word → docx** | 写 Markdown（legal-proposal-generator `SKILL.md` L216「自动保存为 Markdown 文件」；patent-analysis L161「md2word 将最终 Markdown 底稿转换为 Word」） | python-docx 构建文档，表格列宽算法、脚注、Mermaid/SVG 渲染 | 4826 行 + 1144 行测试 | `test_regressions.py`；无版式门禁；外链图片默认下载 |
| **B. elements.json → fill_template → docx → LibreOffice PDF 门禁** | 按案由 Schema 抽要素成 `elements.json`（`SKILL.md` L23） | lxml 编辑解包 OOXML `<w:t>`；`layout_gate.py` 做 DOCX 不变量检查；LibreOffice 真实渲染后用 PyMuPDF 检查「A4、表格居中/列宽、跨页行、连续页码和空白页」（L34） | 5484 行 | `--layout-check rendered` 默认，「失败不覆盖目标文件」；`--verify-residual` 防旧案信息残留（L102）；缺 LibreOffice/PyMuPDF 时「明确报错并拒绝发布」（L122） |
| **C. review-plan.json → contract-copilot → 修订版 docx + 意见书 docx** | 分层审查、写 `review-plan.json` | 自研 `XMLEditor` 直接写 `w:ins/w:del/comments`，`report_docx.py` 生成意见书，`report/integrity.py` 完整性 verifier | 6937 行 + 735 行测试 | 「交付前由独立完整性 verifier 阻断」（RETROSPECTIVE L119）；不可信 DOCX 预检、`defusedxml`（L120） |
| **D. Markdown/YAML → render.py → HTML → Playwright PDF** | 写报告内容、选调色板 | `render.py`（468 行）套 HTML 模板，`pdf.py`（182 行）Chromium `page.pdf()`，`validate_report.py` 校验 | 1478 行 ×2 | selftest 3 个；「DRAFT 人工发布门禁」 |
| **E. VizSpec → draw.io → SVG/PNG/PDF** | 写 VizSpec/选场景 | `apply_visual_roles.py` 改样式不改几何，`export_drawio.py` 调 drawio CLI `--export` | 1949 行 | `check_vizspec.py`、`validate_drawio.py`，4 个单测 |
| **F. 直接 OOXML 模板（无脚本）** | legal-proposal-generator、litigation-analysis 等只出 Markdown，Word 转换交给 A | — | 0 | 无 |

CHANGELOG/复盘里记录的返工与事故（原文）：
- ECG 五轮返工：`references/qa-checklist.md` L10「250612 案（22-著作权案由）连续 5 轮返工，以下每一条都是实际踩过的坑」；L24「v1.1 勘误（2026-08-28）：v1 所记"法院发放件实宽约 7008"实测有误……据此衍生出的"缩表到 7008"修补路线是错的」。
- ECG `CHANGELOG.md` 0.14.0「几何修复（推翻 v0.13 的 1800 边距归一）……根因：归一后可用 8306 < 表宽 9344 → 溢出 → 催生"缩表 7008"错误修补路线」；0.13.3「模板 footer 用 `<w:t>351</w:t>` 等硬编码页码，渲染后永远显示 351」。
- md2word 三次回退（见第六节）。
- contract-copilot：RETROSPECTIVE L96「DEC-039：时间线只能从命令执行时点向后顺延——修正了『客户中午给合同，Word 却显示上午已审完』的穿帮」；L97「DEC-042：w:date 改用本机本地时区写入……否则客户 Word 里会显示成美国时间」。
- legal-industry-report `CHANGELOG.md` L263（0.6.2，2026-08-25）「之前"封面没渲染成功"的印象,根因是 v0.6.0 早期版本封面 CSS 注入丢失 + 章节内容被静默裁切」。

---

## 五、案件状态与目录管理

- **建档**：new-case 按 `assets/{litigation,consultation,trademark,patent}.yaml` 预设建目录（诉讼 12 目录「00 - 日程管理」至「11 - 参考文件」，`SKILL.md` L90），生成「案件信息看板、工时记录和期限管理文件」（L13）；材料编号「A-001（活文档）、B-001（常查）、C-001（存档）、D-001（待激活）」（L18）；操作铁律「复制/移动文件时必须用 cp -p」（L195）。
- **数据模型**：`skills/case-progress/references/schema.md`「case.yaml v4.0 字段字典（唯一权威契约）」，16 节：meta、案件基本信息、当事人与代理、法定期限（list）、任务（list，「唯一任务真源」）、时间线、证据索引、费用、争议焦点索引、工时统计、上下文指针、同步、审级记录、开庭与听证、扩展信息、更新历史（L36-L219）。「行键（稳定身份）：列表行的身份用业务键，不用数组下标——AI 重排后人工修改不错位」（L20）。
- **写入引擎**：`scripts/case_store.py` CLI（show/list/add-task/set-status/add-deadline/set-stage/set-fields/validate/migrate/render/log-work/extract/scan）；每次写入「自动刷新已存在的视图文件」（`SKILL.md` L19）生成 `案件视图.md/.html`；「写入采用整文件 dump，yaml 注释不保留」（`case_store.py` L29）。
- **人工内容保护**：「行级 `source: user|ai`；AI 永不覆写 source=user 的行；`生命周期状态=已结案` 仅手工标记；`程序阶段锁定=true` 时 AI 不得改写程序阶段」（`schema.md` L13）；代码 L417「程序阶段已锁定，AI 不得改写（律师可用 --actor user --unlock 解锁）」、L422「加锁属律师操作」；`_deep_merge` 合并后「source 保护与校验已过」（L1863）。并发保护：`<case.yaml>.lock` + `fcntl.flock`（L143-L155），`CHANGELOG.md` 0.3.0「首版仅锁写入瞬间，并发测试 1/5 暴露丢失更新，修复后 5/5」。
- **看板**：case-dashboard 零依赖 HTTP 服务（端口 7879）+ 单文件 HTML，「一切对 case.yaml 的写入经 case-progress skill 的 case_store CLI」（`SKILL.md` L28）；`/dashboard --review` 周研判（L19）。
- **工时**：`case-progress/SKILL.md` L48「AI 协作完成的每项工作……都边完成边记录」，时长三态「用户明示 / auto / ?」。
- 缺口：无测试；依赖 Unix `fcntl`；SKILL.md 多处引用未入库的消费项目文档与 TASKS.md。

---

## 六、仓库自述的教训（作者原文）

1. 2026-08-27/28，ECG `references/qa-checklist.md` L10「连续 5 轮返工」；L18-L20 把问题归为「入库模板库 / 渲染引擎 / 人工 XML 修补」三源，L73「修改在 /tmp 完成并通过步骤 6 后一次性覆盖目标件；禁止对目标件多轮就地覆写」。
2. 2026-08-28，同文件 L24「v1 所记……实测有误……正确做法：保 9344 表宽 + 收窄页边距」——自己写的 QA 清单第二天就勘误。
3. 2026-08-17，ECG `CHANGELOG.md` 0.6.0「叠加顺序：案由特定规则在前、通用层在后——通用勾选先跑会把"包含□"变 ☑ 致特定重写规则锚失效（24 实测踩坑，DEC-007）」；0.5.0「标题锚定位（occurrence 与段非 1:1 时错位的教训）」。
4. 2026-07-14，md2word `CHANGELOG.md` 1.1.7「### 回退 列宽算法回退到 v1.1.5 旧版（DEC-008）：v1.1.6 的"短/中/长三分类自适应"导致部分表格列宽被过度拉长，作者反馈不满意」。
5. 2026-08-05，md2word 1.2.0「### 回退 恢复外链图片默认下载（作者确认）：撤销 v1.1.9 的 `--allow-remote-images` 开关」——同一天上午加安全开关、当天回退。
6. 2026-08-11，md2word 1.2.1「### 回退 book-publish 代码字体 JetBrains Mono → Courier New……md2word 不做字体嵌入、依赖印刷厂 Windows 字体库」。
7. 2026-08-25，legal-industry-report 0.4.1「### 回退 律所引言章 motto 暂不启用(DEC-IR-011):应用户反馈"各家律所引言差异大,先不显示"」；legal-client-brief 0.3.1 同步回退。
8. 2026-08-06，legal-case-analysis 0.4.0「方向性调整：脱敏从「P0 强制项」降级为「场景化可选 + 安全底线」。办案场景下材料本要提交法院/客户……强制脱敏反而失真」。
9. 2026-08-05，legal-case-analysis 0.3.4「竞赛原始材料包（赛题材料/、法律检索存档/）已丢失」。
10. 2026-08-14，case-progress 0.3.0「首版仅锁写入瞬间，并发测试 1/5 暴露丢失更新，修复后 5/5，见 DEC-008」。
11. 2026-08-17，course-generator 2.7.4「华商 2.7.3 实测暴露两类执行失败——7 章正文一张配图都没插（注意力被"讲者归零"吸走……）」；2.7.2「去来源痕迹把承载在框架词里的工具功能细节……连坐删除」。
12. 2026-06-30，git-workflow 1.4.2「`--merged main` 两方向都不可靠……来自 book repo 误删活跃 deai 分支的实战教训」。
13. 2026-09-01，multi-agent-orchestration 2.11.0「删除 claude-code `--bare` 自动降级……撤销 v1.20.2 Task-019……不再静默降级 prompt-only」；2.10.3「2026-09-01 custom-skills 实测事故……Orca 模式被静默降级为 tmux」；2.14.2（2026-09-03）「真实事故：……`pm-monitor` 把……仍存活的 session 报为 SESSION_GONE」；2.9.2.1「2026-08-28 三波撞号教训」。
14. verification-gate `references/lessons-from-practice.md` 13 条：教训 10「NOT_VERIFIED 整批移交用户 = 反模式」、教训 11「测试套件「永不完成」比「测试失败」更危险……立即暴露 3 条被掩盖数周的真实失败」（2026-08-14）、教训 13「chromium 全绿 ≠ WKWebView 过」。
15. contract-copilot `DEVELOPMENT-RETROSPECTIVE.md` L49-L58「references 目录经历了至少五轮结构调整」（DEC-018→DEC-032）；L123「『部分失败却被误判为全部成功』比『有失败』更危险（DEC-033）」。
16. 2026-04-19，funasr-transcribe 1.9.4「当 FunASR 内部 API 变化时直接报错，而不是静默回退到不兼容导出路径」。

---

## 七、调研员评价

**优点**
1. "模型抽取 + 代码确定性填充 + 真实渲染门禁"的出件分工在三条主线上一致落地（ECG `SKILL.md` L16-L24、contract-copilot RETROSPECTIVE L15、case-progress `SKILL.md` L28），并且都有 fail-closed 语义（ECG L103、L122）。
2. 教训被写回文件而不是留在聊天里：4 份复盘/教训文档 + CHANGELOG 里 262 条含「回退/回滚/事故/踩坑/教训」关键词的记录（`grep -n -E '回退|回滚|事故|踩坑|教训|…' skills/*/CHANGELOG.md | wc -l`）。
3. 隐私工程有实体：版本化 pre-commit 钩子（`.githooks/pre-commit`）+ 本地黑名单不入库设计 + 案件运行时数据「绝不入 skill 目录」（case-progress L30）。
4. 法律内容资产厚：113 棵官方模板树、68 案由要素文档、12 类 64 份合同审查知识、尼斯分类 v13 全量、商标审查指南分章、legal-visualization 场景库含破产重整图谱。
5. 一份 `skills/` 树同时服务 `.claude/` 与 `.agents/`（两条 symlink），发布走 `git archive --worktree-attributes` 自动剥离开发文件（`.gitattributes`、`build-zips.sh` L78）。
6. 案件数据模型的人工保护是代码级的（`case_store.py` L417、L422 直接 `die`），不是提示词级的。

**缺陷**
1. 治理规范与仓库现状脱节：`AGENTS.md` 要求每技能带 DECISIONS/TASKS，`.gitignore` L21-L22 却全局忽略，公开仓库里 181 处 `DEC-xxx` 引用绝大多数无处可查（第 1.5 节）。
2. 版本元数据三处不一致（frontmatter / CHANGELOG / README），至少 8 个 skill 对不上（第 1.2 节）；license 字段 4 种写法；lecture-review 无 license、无 version。
3. README 索引漏掉 6 个 skill（第 1.1 节），包括仓库最重的两个法律 skill 之一 elements-complaint-generator。
4. 测试覆盖不均：63 个 skill 中 20 个有任何测试文件，CI 只跑 skill-lint 与 svg-book-illustrator；case-progress/case-dashboard（2971 行核心代码）零测试。
5. 代码重复：legal-industry-report 与 legal-client-brief 的 `scripts/` 11 个文件 3362 行逐字节相同（`diff -rq` 无输出）。
6. 平台假设未声明：case-progress 用 `fcntl.flock`（Unix only），ECG 门禁依赖 LibreOffice + 方正字体别名（`SKILL.md` L195 自认「不包含跨机器字体可用性结论」），而 README L69 声称「全面支持 Windows、macOS 和 Linux」。

**可疑之处**
1. elements-complaint-generator 许可证自相矛盾：`SKILL.md` L4 `license: MIT`、`LICENSE.txt` MIT、其 `README.md` 末尾「CC-BY-NC」；按 `AGENTS.md` L90-L92 文书生成类应为 CC-BY-NC。
2. `.claude/settings.local.json` 被跟踪入库且含作者本机绝对路径与 MCP 服务器启用清单（L47-L53），与自家钩子 L26 拦截规则冲突；`permissions.allow` 里还留有一次性备份命令（L18-L19）。
3. ECG `SKILL.md` L218 与 `qa-checklist.md` L3 出现真实案件当事人姓名（本报告不转录），说明隐私守门对"姓名"这一类无结构化拦截，只靠本地黑名单。
4. tingwu-asr 自述「逆向封装通义听悟网页端内部 REST API」（`SKILL.md` L12），court-sms 参考了 PolyForm Noncommercial 许可的项目（`references/ATTRIBUTION.md`），二者的合规边界仅靠一句说明。
5. skill-lint 的 `references/skill-dev-guide.md` 与 `docs/SKILL-DEV-GUIDE.md` 双份维护（513 vs 506 行），推测已出现漂移。
6. 多个 SKILL.md 引用仓库外文件（case-dashboard L12「消费项目 SuitAgent docs/…」、ECG L212「docs/plans/…（不入仓）」），公开使用者无法复现设计真值。

---

## 附录：skills/ 一级目录树（63 个）

```
agent-email                   Agent 专用邮箱收发（网易/腾讯后端）
apple-smart-schedule          自然语言/票据截图 → 苹果日历+提醒（macOS）
article2book                  判断内容资产适合做书/课程并出策划意见
case-dashboard                本地案件看板服务 + 周研判
case-progress                 case.yaml 唯一写入引擎（任务/期限/阶段/工时）
code2patent                   从代码仓库生成技术交底书与专利初稿
contract-copilot              合同审查/起草，OOXML 批注修订 + 意见书
course-generator              转录稿 → 结构化课程
court-sms                     法院短信解析、文书下载归档
cross-agent-coordination      跨平台 Agent 任务分配与交接
de-ai-polish                  中文文章去 AI 腔
dingtalk-minutes              钉钉 AI 听记读取封装
douyin-batch-download         抖音博主视频批量下载（F2）
dsh-plugin-lint               DeepSeek Harness 插件审查
elements-complaint-generator  最高法 67 类要素式起诉状 Word 生成
funasr-transcribe             本地 FunASR 音视频转录
git-batch-commit              暂存变更拆分为多个聚焦 commit
git-workflow                  分支/Monorepo 合并/PR/清理安全规则
github-star-manager           GitHub Star 发现、追踪、看板
handdrawn-article-illustrator 文章手绘风配图（Image Brief + 出图）
img2pdf                       图片/长截图排版为 A4 PDF
invoice-organizer             发票按抬头归档并出报销清单
lecture-review                讲课转录稿复盘（口癖/节奏/课件对照）
legal-case-analysis           通用法律分析引擎（民商九步法/刑事二阶层）
legal-client-brief            客户日常法律简报（日/周/事件）PDF 三件套
legal-harness-init            为法律工作者生成 AGENTS.md/CLAUDE.md 基线
legal-industry-report         行业法律月报/季报 PDF
legal-ocr                     OCR/文档转 Markdown 统一入口
legal-proposal-generator      诉讼方案/咨询报告/结案汇报（人工触发）
legal-qa-extractor            沟通记录 → 法律问答知识库（脱敏）
legal-text-format             法条/案例文本规范化 Markdown
legal-visualization           法律关系图/流程图/时间轴（draw.io 导出）
litigation-analysis           起诉状/判决书/庭审笔录三场景分析
md2word                       Markdown → 中文排版 Word（多预设）
mineru-ocr                    MinerU 云端 API 文档转 Markdown
multi-agent-orchestration     PM 主控多 worker 并行（Orca/tmux）
multica-skill-update          Multica 工作区 Skill 批量同步
new-case                      诉讼/咨询/商标/专利案件目录初始化
opc-legal-counsel             一人公司/小微企业法律分诊
paddle-ocr                    PaddleOCR 法律 PDF 结构化解析
patent-analysis               权利要求拆解、侵权比对、FTO
patent-download               专利 PDF 批量下载
pdf-organizer                 法律 PDF 页面索引、拆分、重命名
pdf-processor                 扫描件预处理/双层 PDF/合并/压缩
piclist-upload                Markdown 图片上传图床替换链接
project-init                  生成项目 CLAUDE.md 与 docs 上下文
release-workflow              GitHub 版本发布全流程（含 monorepo 打包）
skill-lint                    Skill 预检、稳定性验收、安全扫描
skill-manager                 多平台 Skill 安装/更新/注册表
skill-publish-sync            同步 Skill 到 ClawHub/SkillHub/联想
subtree-publish               子目录 git subtree 推独立仓库
svg-article-illustrator       文章 SVG 配图（动态/静态/PNG）
svg-book-illustrator          书籍架构图/流程图 SVG 配图
tingwu-asr                    阿里云通义听悟云端转录
trademark-assistant           商标类别规划、可注册性初筛（尼斯 v13）
transcription-corrector       按用户词典纠正 ASR 转录稿
universal-media-downloader    yt-dlp 多平台媒体下载
verification-gate             代码改完后的 8 阶段验证门禁
video-compressor              FFmpeg 视频压缩与静默剪切
video-screenshot              录屏抽帧与证据线索索引
wechat-article-fetch          Playwright 抓公众号文章
workbuddy-checkin             WorkBuddy 每日积分签到
yuandian-law-search           元典法律数据库检索中间层
```
