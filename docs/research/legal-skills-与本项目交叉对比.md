# legal-skills 与本项目 3.0 交叉对比

> **写于** 2026-09-03。**输入**：(a) 《legal-skills-独立调研.md》（由未读过本项目的独立 agent 生成）；(b) 本项目 `docs/3.0-handoff.md`、`AGENTS.md`、`knowledge/`。本文是两者**唯一**被并排放置的地方，每一行都标出两侧出处。
> **红线**：不含案件数据。

## 0. 对象与命名

| 名称 | 指什么 | 关系 |
| --- | --- | --- |
| **legal-skills** | github.com/cat-xierluo/legal-skills，外部公开仓库，63 个 skill，commit `3a8fdd36` | 与本项目及作者**无任何关联**，仅同为中国法律业务的 agent skill 集 |
| **本项目 3.0** | 本仓库，律师工作台 3.0，破产业务先行 | 从零重构中 |
| **本项目 2.0** | 冻结在旧仓库 commit `25c0e37` 的上一版 | 只通过 handoff 与 `knowledge/` 进入本文 |

**独立性证据**：在 legal-skills 全库检索「律师工作台 / fill-docx / f4de01」零命中；「工业园区」「破产管理人」各命中一处，分别在短信归档示例与商标审查指南第 11 章，属通用法律文本。时间线平行：legal-skills 仓库建于 2026-01-07，模板填充器最新版 2026-08-30；本项目 2.0 裁定台账日期 2026-08-29，3.0 仓库首次提交 2026-09-03。两边互相引用的证据为零。

**相似从何而来**（用于读本文时校准，不是结论）：两边建在同一份 Agent Skills 规范上（SKILL.md、description 触发、scripts/references 目录），都采用「模型管语义、代码管确定性」这条通行分工（legal-skills 表述为「AI 负责判断和表达，脚本负责精确执行」，本项目 2.0 表述为「语义归模型、确定性归代码」），都对着同一个物理对象：法院下发的 Word 模板。事故形态相同是 OOXML 的性质，不是设计同源。

**读法**：每节先列本项目侧原文出处，再列 legal-skills 侧出处（`§` 指独立调研的节号），最后给「借鉴 / 避雷 / 无关」判断和落到哪张 wayfinder 票。

---

## 1. 逐条对照 handoff

### 1.1 handoff §1：保留的四件 Matt 式封装

| 封装项 | 本项目侧 | legal-skills 侧 | 判断 |
| --- | --- | --- | --- |
| setup 类 skill | handoff §1 第 1 件 | `legal-harness-init`：只 upsert 带 marker 的受管区块、`--dry-run` 先出 diff、完成状态分三档（`CONFIG_WRITTEN` 起）、附稳定性合同 JSON（独立调研 §1.4、§二未详列；`SKILL.md` 282 行 + `check-baseline.py` 146 行） | **借鉴骨架**：受管区块 + dry-run + 不夸大的完成状态。落「harness 范围」票 |
| router（只提示不触发） | handoff §1 第 2 件 | **没有**路由 skill，索引只有 README 表格，且漏 6 个 skill，含最重的 `elements-complaint-generator`（§1.1） | **反证支持本项目的选择**：无路由地图会漏。保留 router |
| 编排层 / 参考层分层 | handoff §1 第 3 件 | 63 个里只有 1 个 `disable-model-invocation: true`；9 个零脚本纯提示 skill；没有分层清单（§1.4）；`case-progress` / `case-dashboard` 在 SKILL.md 里宣称 `/progress` `/dashboard` 命令但仓库无对应入口（§1.4） | **本项目的分层比 legal-skills 明确，保留**。避雷：不在 SKILL.md 里声称不存在的入口 |
| 插件分发 | handoff §1 第 4 件；§6 新插件换名 | 已停用 marketplace（AGENTS.md v1.9.0），改 CalVer tag + 每 skill zip + 同步到三个外部平台（§1.6） | **避雷**：不接多平台链。**借鉴一招**：`.gitattributes` 的 `export-ignore` 在打包时剥离开发协作文件（§1.6） |

description 纪律（handoff §4「不变量 4、5、7 沿用」）：legal-skills 63 条里 52 条有触发、34 条有负向、9 条互指邻居，好例 `case-progress`、`img2pdf`、`legal-case-analysis`，差例 `litigation-analysis`（28 字无触发）、`md2word`（不提自己是公共后端）（§1.3）。**借鉴**：功能 + 触发 + 负向 + 邻居互指四件写进每张 skill 票的完成定义；本项目 skill 少，不需要 legal-skills 那种 5,556 行的 `skill-lint`。

### 1.2 handoff §2.1：命令太多、反复确认

- **本项目侧**：6 个 user-invoked skill + 4 个律师动作脚本，每个再分 `--show`/`--commit` 两段；「批准即确认」与「两段式执行」互相抵消（handoff §2.1）。
- **legal-skills 侧**：律师面对自然语言触发；`case-progress` 的 CLI 有 12 个子命令但由模型调用，律师不直接敲（§五）。**确认点被数据保护替代**：行级 `source: user|ai`，「AI 永不覆写 source=user 的行」；`程序阶段锁定=true` 时 AI 不得改写，解锁「属律师操作」，代码里直接 `die`（§五、§七优点 6）。
- **判断**：**借鉴思路**：把「律师发起权四项」从对话确认改为数据层保护：律师写过的东西 AI 永不覆盖，于是 AI 可以放手写、不必每步问。这直接对应 handoff §4「发起权归律师保留，两段式脚本形态重裁」。**避雷**：legal-skills 没有定义过「律师一天的主循环」，`EXPERT-SUITE-DESIGN.md` 是 skill 套件视角（§一），与本项目 2.0 一样是能力正推，不能当主循环样板。落「律师主循环」票。

### 1.3 handoff §2.2：可见工作台的呈现形态

- **本项目侧**：网页 → 插件 → MCP widget + HTML 快照，律师期望官方 MCP 格式或 app（handoff §2.2）。
- **legal-skills 侧**：`case-dashboard` 是本地 HTTP 服务（7879 端口）+ 单文件 HTML，纯派生视图，「一切写入经 case-progress 的 CLI」；每次写入自动刷新 `案件视图.md/.html`（§五）。没有 MCP 形态。
- **判断**：只提供一个数据点，看板是派生视图、不承载状态，这与本项目 2.0 ADR-0003「快照不承载图谱数据」方向一致，handoff 已判「机制本身没出事」。对 MCP/app 之争 legal-skills **无关**。落「呈现形态」票作旁证。

### 1.4 handoff §2.3：文书生成机制

**本项目侧**：2.0 只有一条通道，模型产「槽位→值」清单，`fill-docx.py` 校验指纹后写入；代价是裁定台账 #8–#11（空单元格要加 `cells` 定址、窄列待决标记撑页、模板带第三方作者信息、末尾空段删过头触发修复）；handoff 判「每遇一种新版式就开一个口子」，3.0 「从 agent 直接产出文书这一端出发，只在出真实事故时才加确定性脚本」。

**legal-skills 侧**（§四）：四条主线并存。A：模型写 Markdown → `md2word`（4,826 行）出 DOCX，是法律专业 skill 的默认出件后端。B：`elements-complaint-generator` 模型抽 `elements.json` → `fill_template.py`（2,942 行）改 OOXML → `layout_gate.py`（567 行）+ LibreOffice 真实渲染门禁，合计 5,484 行 + 113 棵解包模板树。C：`contract-copilot` 自研 XMLEditor 写批注/修订。D：HTML → Playwright PDF。

**事故对照**（本项目 2.0 裁定台账 ↔ legal-skills 自述）：

| 本项目 2.0 事故（裁定台账） | legal-skills 记录（独立调研 §四、§六） |
| --- | --- |
| #9 窄列待决标记撑满整页 | qa-checklist「表宽 9344 twips 溢出 A4 可用宽 8306」；v1.1 勘误「缩表到 7008 是错的，正确做法：保 9344 表宽 + 收窄页边距」 |
| #10 模板 docProps 带第三方作者 | `--verify-residual` 残留校验「防旧案信息残留」 |
| #11 末尾空段溢出成空白页 | `layout_gate.py`「只有页码的页面对用户仍是空白页」；0.15.0「避免分节符 + 分页符叠加产生空白页」 |
| #11 续 表格收尾触发修复 | 0.13.1「4 个段落级 sectPr 把表单分成 5 节…表格视觉断裂」；0.15.0「所有表格行加入 cantSplit」 |
| #8 空单元格无锚点 | 无直接对应；legal-skills 用解包 OOXML 树 + `<w:t>` 跨 run 替换绕开 |

legal-skills 在 B 路线上走到「连续 5 轮返工」、QA 清单**次日**勘误、0.14.0 推翻 0.13 的几何修复（§六 1–3）。**这证实 handoff §2.3 的判断是路线固有的，不是本项目 2.0 的脚本写得差。**

**判断**：
- **借鉴 1**：默认通道 = 模型写全文 → 通用转换器（legal-skills 的 A）。方向来自 handoff §2.3，legal-skills 提供「法律 skill 全走 A 也能出件」的实证。
- **借鉴 2**：独立版式门禁从第一天就有，规格照 `layout_gate.py`：独立于生成器、只读、不修改产物、不过就不覆盖目标文件、基于真实渲染而非 XML 猜测（§2.1、§四）。本项目 2.0 的五种事故形态即门禁的检查项（handoff §5 已要求作验收项）。
- **借鉴 3**：`--verify-residual` 式的残留检查对应裁定 #10。
- **可选、慎用**：legal-skills 把官方模板以解包 OOXML 树入库以便 `git diff` 官方更新（§2.1）。本项目 19 件模板是只读原件，解包会变成上千文件，只在需要追踪官方改版时考虑。
- **避雷 1**：不要在门禁之前先写填充器。legal-skills 的 `fill_template.py` 63 条 build_rules 是「每案由一套规则」的极致版；本项目 3.0 只在法院退件一次之后引入填充器，且先做单一模板。
- **避雷 2**：`md2word` 外链图片默认下载并自认有 SSRF 风险（§2.4、§1.7）。本项目若引入通用转换器，关掉网络访问。
- **避雷 3**：legal-skills 门禁依赖 LibreOffice + 方正字体别名，自认「不包含跨机器字体可用性结论」，README 却称全平台支持（§七缺陷 6）。本项目在 Windows 中文路径上，门禁的渲染后端要在本机验证过再写进票。

落「文书生成机制」票。

### 1.5 handoff §2.4 / §7 第 6 票：规则先于证据、规则元规则

- **本项目侧**：2.0 在第一个真实案件前写了 13 条不变量、9 份 ADR、六条原则；3.0 候选元规则「一条规则只在真实使用里被违反过一次之后才写进 AGENTS.md」，目前 AGENTS.md 只有两条硬边界。
- **legal-skills 侧**：AGENTS.md 436 行、28 版；要求每 skill 带 DECISIONS.md / TASKS.md，但 `.gitignore` 全局忽略两者，公开仓库里 181 处 `DEC-xxx` 引用绝大多数无处可查，执行率 4/63（§1.5、§七缺陷 1）。另一面：CHANGELOG 里 262 条含「回退 / 事故 / 踩坑 / 教训」的记录，每条带日期和背景（§六、§七优点 2）。
- **判断**：**借鉴**：元规则加一个形式要求，每条规则附「被违反的那一次」的日期与出处，格式照 legal-skills CHANGELOG 的「背景：实际使用中发现…」。**避雷**：不要求每 skill 带 DECISIONS/TASKS；本项目已配 GitHub issue 作决策记录（`docs/agents/issue-tracker.md`），一处即可。legal-skills 的 AGENTS.md 大半是许可证与发布纪律，几乎没有办案纪律，是「规则多、执行少」的反面教材。落「规则元规则」票。

### 1.6 handoff §3：两条硬边界

**边界 1 案件材料永不入仓库**：
- legal-skills 有版本化 `.githooks/pre-commit`，硬拦手机号、18 位身份证、座机、`/Users/` 绝对路径、真实法院案号（正则已含「破」字号），外加本地黑名单 `local-denylist`「绝不入库，黑名单放公开仓库等于二次泄露」（§1.7）。
- 但 legal-skills 自己的 `.claude/settings.local.json` 入库且含本机绝对路径，`elements-complaint-generator/SKILL.md` 含真实当事人姓名（§七可疑 2、3）。说明正则钩子挡不住姓名，也挡不住 `--no-verify`。
- **借鉴**：移植这个钩子，把绝对路径模式改成本机路径与 `D:\Claude\Data\Cases\`；敏感词表放仓库外，与本项目硬边界 1「敏感词表只存在于案件工作区」设计相同。**避雷**：钩子是机械保障，不替代「第二双眼」。

**边界 2 办案会话对仓库只读**：
- legal-skills 没有对应规则。相近的只有 `case-progress`「运行时数据绝不入 skill 目录（本仓库公开）」和「路径解算禁止 `__file__.resolve()`，符号链接安装会穿透回源仓库」（§五、§2.3）。
- **借鉴**：案件工作区的发现要显式（参数或环境变量），不靠脚本所在位置推导。**本项目独有**：办案会话只读 + 裁定誊入经第二双眼，legal-skills 无此机制。

### 1.7 handoff §4 末行、§5 现实约束、§7 第 5 票：案件目录规范与迁移

| 维度 | 本项目 2.0（`knowledge/规范/案件目录规范.md`） | legal-skills（§五） |
| --- | --- | --- |
| 目录 | 收件箱 / 原始材料（7 子目录）/ 既有文书 / 工作副本 / 已批准 / 审查报告 / 快照 | `new-case` 按 `assets/{litigation,…}.yaml` 预设建 12 个编号目录 |
| 状态载体 | 6 个登记 `.md` 表，只增不改；节点标记是「节点走完的唯一依据」 | 单文件 `case.yaml` v4.0，16 节；「整文件 dump，yaml 注释不保留」 |
| 写入 | 律师动作脚本，两段式 | `case_store.py` 单一写入引擎：schema 校验 → 行级 source 保护 → flock → 临时文件 + `os.replace` |
| 人工保护 | 发起权归律师（流程规则） | 行级 `source: user`，代码级拒写 |
| 派生视图 | 快照 `.md`，只增不删 | 每次写入自动刷新 `案件视图.md/.html` |
| 迁移 | handoff §5：回放案按 2.0 规范落盘，改规范须迁移或重导 | `schema.md` §3「v3.0 → v4.0 章节处置表」、§4「存量格式映射要点」 |

**判断**：
- **借鉴 a**：目录规范写成 YAML 预设而不是散文，迁移脚本和 import 都对着预设做。本项目只需一份「破产.yaml」。
- **借鉴 b**：单一写入引擎 + 校验 + 原子写 + 派生视图自动刷新，四件一起替代 2.0 的两段式脚本。
- **借鉴 c**：迁移写成「处置表」（旧节 → 新节 → 处置），legal-skills 的 §3/§4 是现成格式。
- **避雷 a**：**不要抄 `case.yaml` 16 节 schema**。那是诉讼语义（审级记录、开庭与听证、当事人与代理）。本项目的状态结构是「模块 / 节点 / 要件 / 期限 / 并行依赖」，唯一来源是 `knowledge/流程模型/破产.md`（12 模块、911 行、逐节点两源出处）。
- **避雷 b**：单文件 YAML 与「只增不改」登记表是两种哲学。legal-skills 0.3.0 记录「首版仅锁写入瞬间，并发测试 1/5 暴露丢失更新」（§六 10），单文件必须带锁；而 `case_lock` 用 `fcntl.flock`，Windows 不可用（§七缺陷 6）。选哪种是票的内容，选单文件就得自己写 Windows 锁。

### 1.8 handoff §5：领域资产的对照

- **legal-skills 没有任何破产 / 重整 / 清算 / 管理人主题的 skill**（§三）。「债权」287 次几乎全在民间借贷、担保语境；68 个要素式起诉状案由无破产案由。最集中的只有 `legal-visualization` 场景库的 DR-02 债权申报与审查流程图、DR-03 清偿顺位瀑布图、DR-05 重整方案结构图、RP-07 执行转破产路径图。
- **本项目有而 legal-skills 没有**：12 模块流程模型（要件清单、法定期限、两源出处）、19 件园区法院官方模板、债权审查确认表文书卡、去案件化裁定台账。**内容上本项目比 legal-skills 深，只是窄。**
- **可改造的通用件**：`legal-case-analysis` 的「前置分析引擎、不要求每次出报告」定位与 14 份 references（§三分析组），对本项目「债权审查」skill 的定位有参考；`yuandian-law-search` 法条检索外发第三方，SKILL.md 自带「数据留存与隐私警示」（§1.7），放进本项目办案会话须过硬边界 1；`court-sms` 解析法院短信归档，对应本项目「收件箱 / 导入归档」，但其短信模式是诉讼庭审通知，破产案件的法院通知形式是否相同**未验证（推测）**。
- **可对照的图**：DR-02 / DR-03 可与本项目流程模型模块三、模块六、模块九的节点对照，作为「律师想看到什么」的一个外部样本，落「呈现形态」票。

---

## 2. 借鉴清单（本项目 3.0 可以拿的）

| # | 借鉴项 | legal-skills 出处 | 本项目落点 | 条件 |
| --- | --- | --- | --- | --- |
| J1 | 独立版式门禁：只读、不改产物、fail-closed、真实渲染 | `elements-complaint-generator/scripts/layout_gate.py`；独立调研 §2.1、§四 | 文书生成机制票；检查项 = 裁定台账 #8–#11 五种事故 + 残留第三方信息 | 渲染后端先在 Windows 本机验证 |
| J2 | 默认出件 = 模型写全文 → 通用转换器 | `md2word` 作为法律 skill 默认后端；§四 A | 文书生成机制票（方向本来自 handoff §2.3） | 转换器关网络 |
| J3 | 行级 `source: user` 保护替代对话确认 | `case-progress` schema L13、`case_store.py` L417–422；§五 | 律师主循环票、案件目录票 | 无 |
| J4 | 目录规范写成 YAML 预设 | `new-case/assets/*.yaml`；§五 | 案件目录票 | 只做一份破产预设 |
| J5 | 单一写入引擎 + 校验 + 原子写 + 派生视图自动刷新 | `case_store.py`；§五 | 案件目录票 | 锁要自己写 Windows 版 |
| J6 | 迁移写成处置表 | `case-progress/references/schema.md` §3–4；§五 | 案件目录票（回放案迁移） | 无 |
| J7 | pre-commit 隐私守门 + 仓库外黑名单 | `.githooks/pre-commit`；§1.7 | 硬边界 1 的机械保障 | 改路径模式；不替代第二双眼 |
| J8 | 案件工作区显式发现，禁 `__file__.resolve()` | `case_store.py` L75；§2.3 | 硬边界 2 | 无 |
| J9 | setup skill 骨架：受管区块 marker + dry-run + 三档完成状态 | `legal-harness-init`；§1.4 | harness 范围票 / setup skill 票 | 无 |
| J10 | description 四件：功能、触发、负向、邻居互指 | §1.3 好例 | 每张 skill 票的完成定义 | 不造 lint 工具 |
| J11 | 规则带「被违反的那一次」的日期与出处 | 各 CHANGELOG「背景：实际使用中发现」；§六 | 规则元规则票 | 无 |
| J12 | 打包时 `export-ignore` 剥离开发文件 | `.gitattributes` L16–17；§1.6 | 插件分发 | 无 |

## 3. 避雷清单（本项目 3.0 要避开的）

| # | 避雷项 | legal-skills 出处 | 为什么与本项目相关 |
| --- | --- | --- | --- |
| B1 | 不在门禁前写模板填充器；不做「每案由一套规则」 | `fill_template.py` 2,942 行、63 条 build_rules，5 轮返工、次日勘误；§四、§六 1–3 | 与本项目 2.0 `fill-docx` 同一路线，handoff §2.3 已判；只在法院退件后引入 |
| B2 | 不抄 `case.yaml` 16 节 schema | `schema.md`；§五 | 诉讼语义；本项目数据模型来自 `knowledge/流程模型/破产.md` |
| B3 | 不指望 legal-skills 提供破产领域内容 | §三 | 零专题 skill；本项目资产更深 |
| B4 | 不接多平台分发链、不做 CalVer + zip + 外部平台同步 | §1.6 | 本项目面向单一律所，handoff §1 保留插件分发 |
| B5 | 不要求每 skill 带 DECISIONS/TASKS | §1.5 执行率 4/63，`.gitignore` 自我否定 | 本项目用 GitHub issue，一处记录 |
| B6 | 不写 22KB 的 AGENTS.md | §1.5、§七缺陷 1 | 本项目元规则「违反一次才写」正是反向 |
| B7 | 不在 SKILL.md 里声称不存在的命令入口 | `case-progress` `/progress`；§1.4 | 本项目 router 只提示不触发，入口要真存在 |
| B8 | 通用转换器不默认下载外链 | `md2word` L134；§2.4 | 案件文书里不该有外网请求 |
| B9 | 门禁与锁的 Unix 假设 | `fcntl.flock`、LibreOffice 字体；§七缺陷 6 | 本项目在 Windows 中文路径上 |
| B10 | 外发检索先过硬边界 1 | `yuandian-law-search` 自带隐私警示；§1.7 | 原始响应不得落进本仓库 |
| B11 | 正则钩子挡不住姓名 | legal-skills 自己的 SKILL.md 含真实姓名；§七可疑 3 | 本项目敏感词表在仓库外 + 第二双眼，两者都不能省 |
| B12 | 不复制整包代码做「姐妹 skill」 | `legal-industry-report` 与 `legal-client-brief` 3,362 行逐字节相同；§2.6 | 本项目参考层 skill 可被编排层调用，正是为了避免这个 |

## 4. 与六张 wayfinder 票的映射

| handoff §7 决策票 | 本文对应节 | legal-skills 能给的 |
| --- | --- | --- |
| 呈现形态 | 1.3、1.8 | 看板是派生视图这一数据点；DR-02/03 图作外部样本。MCP/app 之争无关 |
| harness 范围 | 1.1 | setup skill 骨架（J9）；symlink 双注册在 Windows 下是空目录（§1.1），本项目先做一侧的理由 |
| 律师主循环 | 1.2 | 数据层保护替代对话确认（J3）；主循环定义本身 legal-skills 没有 |
| 文书生成机制 | 1.4 | J1、J2、B1、B8、B9；事故对照表 |
| 案件目录规范与迁移 | 1.7 | J4、J5、J6、B2 |
| 规则元规则 | 1.5 | J11、B5、B6 |
