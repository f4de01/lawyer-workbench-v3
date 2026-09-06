# 「先 Markdown 再 DOCX」中间层的必要性调研

> 引文里的破折号已按全仓禁破折号的规则改为逗号或冒号，其余逐字。

> **写于** 2026-09-05，供「文书出件机制与验收项」票参考。只查事实、给结论，不改任何已有文件、不做决策。
> **来源等级**：一手来源优先，Anthropic `anthropics/skills` 仓库（含历史提交）、python-docx 官方文档与源码、docx-js 官方文档与源码、npm registry、GFM 规范、pandoc 手册；本仓库已核对材料（`docs/research/docx-backend-实测.md`（分支 `research/docx-backend`）、`docs/research/legal-skills-独立调研.md`、`docs/research/legal-skills-与本项目交叉对比.md` §1.4、`knowledge/通用裁定台账.md`、`docs/adr/0002-*.md`、`docs/research/skill-platforms-claude-code-与-codex.md`）；本机实验（第 4 节）。OOXML 规范引文取自 Microsoft Learn Open XML SDK 类文档所引的 ISO/IEC 29500-1 原文；Codex 事实取自 learn.chatgpt.com（developers.openai.com/codex/* 308 跳转至此）与 `openai/codex` 源码。所有 URL 访问日期均为 2026-09-05。
> **红线**：不含任何案件材料；实验正文只用甲乙丙占位；模板原作者姓名不转录。

---

## 1. 问题与范围

本项目要让 agent 依据材料生成法律文书 DOCX，每次生成是一个新文件（ADR-0002），另有独立只读的版式门禁（Word COM 渲染 + PyMuPDF 检查，`docx-backend-实测.md` §二）。候选出件机制是「模型只写 Markdown（自定最小集）→ 冻结的确定性转换器（python-docx，以官方模板为版式载体）→ DOCX」。

问题：这层 Markdown 中间物是否必要？对比对象：

| 代号 | 方式 | 模型产出的中间物 |
|---|---|---|
| A | Markdown → 冻结转换器（python-docx，开官方模板、清 body 留 `sectPr`、按模板字体写段/表） | Markdown 全文 |
| B | 模型每次现写一段 python-docx 代码生成 DOCX | Python 代码 |
| C | 模型直接编辑 OOXML：解包模板、改 `document.xml`、重新打包 | XML 片段/diff |
| D | 模型写 docx-js（JavaScript）→ node 构建 DOCX | JS 代码 |
| E | 模型只产槽位值 → 确定性填充器写入模板（2.0 `fill-docx.py`、legal-skills `fill_template.py`） | JSON 替换清单 |
| F | 模型写 HTML → Word COM 打开另存 DOCX | HTML |

评价维度：①确定性与可复现；②对官方模板的保真（单节 A4、页边距、页脚 PAGE 域、方正小标宋简体/仿宋、4 件模板的合并单元格）；③可审查性；④Claude Code 与 Codex CLI 两平台可用性；⑤本机依赖；⑥门禁不过后的重试；⑦与「每版必带审查报告、文书本体直接可提交、律师随后在 Word 里手改」的配合。

范围外：不评价文书内容质量；不评价门禁本身；不做决策。

---

## 2. 逐方式事实表（A–F × 7 维度）

本节只记事实与出处，不带判断。「本机实验 n」指第 4 节编号。

### 2.1 维度 ①确定性与可复现

| 方式 | 事实 | 出处 |
|---|---|---|
| A | 同一 Markdown 两次转换，`word/document.xml` 及除 `docProps/core.xml` 外全部 zip 条目字节相同；`core.xml` 不同仅因转换器**主动**把 created/modified 置为当前时间（脚本第 65 行 `cp.created = now`）。python-docx 自身不自动写时间戳：「python-docx does not automatically set any of the document core properties other than to add a core properties part to a presentation that doesn't have one (very uncommon)」；源码 grep 未见 random/uuid。 | 本机实验 2；https://python-docx.readthedocs.io/en/latest/api/document.html#coreproperties-objects ；https://raw.githubusercontent.com/python-openxml/python-docx/master/src/docx/opc/parts/coreprops.py |
| B | 转换代码本身即 A 的转换器（`md2docx_tpl.py` 76 行）；区别只在代码是否冻结。模型每次现写代码时，python-docx 的已知坑必须每次重新绕开：`Font.name` 只写 `w:ascii`/`w:hAnsi`，「Initially, only the base typeface name is supported by the API」，中文字体须手写 `rFonts.set(qn('w:eastAsia'), …)`（issue #346 至今 open）；无 PAGE 域 API；`last_printed` 不接受 `None`。 | https://python-docx.readthedocs.io/en/latest/dev/analysis/features/text/font.html ；https://github.com/python-openxml/python-docx/issues/346 ；`docx-backend-实测.md` §五 |
| C | 解包→改 XML→重打包是纯文本操作，本机实验 3 两次输出字节全同（zip 条目时间固定后）。失败模式：Word 把可见文本拆成多个 `<w:r>`，「a phrase you can see in the document often doesn't exist as a contiguous string in the XML」；模板 3-1 里 `XXXXXX` 在 XML 中是 `<w:t>XXX</w:t>…<w:t>XXX</w:t>`，直接字符串替换命中 0 处。Anthropic 官方 skill 为此专门配 `merge_runs.py`，并要求「do NOT reformat or pretty-print」。 | 本机实验 3；https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 47–61 行 |
| D | docx-js 输出**不**是字节级确定：`CoreProperties` 构造函数固定 `new TimestampElement("dcterms:created")` / `"dcterms:modified"`，值为 `new Date().toISOString()`，`IPropertiesOptions` 无 created/modified 选项；JSZip 条目时间取当前时间；超链接/文本框/嵌入字体用 `nanoid` 随机 id。本机实验 4 两次输出仅 `docProps/core.xml` 不同，`document.xml` 相同。 | https://raw.githubusercontent.com/dolanmiu/docx/master/src/file/core-properties/properties.ts ；https://raw.githubusercontent.com/dolanmiu/docx/master/src/util/convenience-functions.ts ；本机实验 4 |
| E | 填充器是确定性代码（2.0 `fill-docx.py`「校验模板指纹后原样写入」；legal-skills「fill_template.py 在模板 XML 上做 `<w:t>` 跨 run 精确替换……LLM 不直接修改 OOXML」）。失败模式记录在案：空单元格无锚点（台账 #8）、「每遇一种新版式，就要在脚本里开一个新口子」；legal-skills 同路线「连续 5 轮返工」、QA 清单次日勘误、0.14.0 推翻 0.13 几何修复。 | `docs/3.0-handoff.md` §2.3；`legal-skills-独立调研.md` L114、§六 1–3；`legal-skills-与本项目交叉对比.md` §1.4 |
| F | 经 Word 存盘，Word 把本机用户名写入 author/lastModifiedBy；样式落为 `Normal (Web)`/`Heading 1`。 | `docx-backend-实测.md` §一 链 2 |

### 2.2 维度 ②对官方模板的保真

| 方式 | 事实 | 出处 |
|---|---|---|
| A | 开模板、清 body 只留 `sectPr`：A4、页边距、页脚 PAGE 域（模板 3-1）全部保留并渲出；字体按模板名写入 run（含 `w:eastAsia`）。python-docx 文档：「A lot of how a document looks is determined by the parts that are left when you delete all the content. Things like styles and page headers and footers are contained separately from the main content」。**合并单元格**：Markdown 管道表（GFM §4.10）没有跨行跨列语法；转换器当前不表达合并；但底层 python-docx `_Cell.merge()` 可产出与模板同形的 `<w:gridSpan w:val="2"/>`、`<w:vMerge w:val="restart"/>`、`<w:vMerge/>`（本机实验 1），即转换器加一条约定即可覆盖。列宽、行高沿用默认，与模板不一致。 | `docx-backend-实测.md` §一、§六；https://python-docx.readthedocs.io/en/latest/user/documents.html ；https://github.github.com/gfm/#tables-extension- ；https://python-docx.readthedocs.io/en/latest/api/table.html#docx.table._Cell.merge ；本机实验 1 |
| B | 与 A 同库同能力；差别是每次由模型决定是否清 body、是否写 `eastAsia`、是否保留 `sectPr`。 | 同上 |
| C | 模板原样保留一切（只改 `document.xml` 文本），合并单元格、页脚、字体天然保真；本机实验 3 输出 python-docx 可开、表格与页脚在。代价：`docProps/core.xml` 的模板原作者信息**也**原样保留（台账 #10 的事故来源），须另行清除。 | 本机实验 3；`knowledge/通用裁定台账.md` #10 |
| D | `Document` 只能新建，「docx-js cannot open existing files」；`patchDocument` 只做 `{{占位符}}` 替换（「This algorithm is limited to one patch per text run」）。新建时可声明 A4（`size: {width: 11906, height: 16838}`）、边距、页脚 `PageNumber.CURRENT`（渲出 `fldChar begin/instrText PAGE/separate/end`）、`columnSpan`/`rowSpan`（渲出 gridSpan/vMerge）、`font: {ascii, hAnsi, eastAsia, cs}`，本机实验 4 全部验证，Word 渲染 1 页、页脚 "1"、PyMuPDF 检出 FangSong。但模板的样式表、列宽、行高、段落细节须由模型逐项在代码里复刻。`patchDocument` 空补丁往返官方模板 3-1：`sectPr`、vMerge、gridSpan 均保留，`document.xml` 仅 `mc:Ignorable` 多一个 `w15`，原作者信息保留（本机实验 5）。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 14 行；https://raw.githubusercontent.com/dolanmiu/docx/master/docs/usage/patcher.md ；https://raw.githubusercontent.com/dolanmiu/docx/master/src/patcher/from-docx.ts ；https://raw.githubusercontent.com/dolanmiu/docx/master/docs/usage/tables.md ；https://raw.githubusercontent.com/dolanmiu/docx/master/src/file/paragraph/run/run-fonts.ts ；本机实验 4、5 |
| E | 模板原件不动、只替换文本，保真最高；但「空单元格无锚点」（台账 #8）、窄列长文撑页（#9）、末尾空段（#11）证明「XML 全对、渲出来仍错」与填充器无关，属模板+内容长度问题。 | `knowledge/通用裁定台账.md` #8–#11 |
| F | 「段落样式落为 `Normal (Web)`/`Heading 1`，h1 字体丢失（渲出 SimSun）……表格列宽按内容分配。`@page` 生效」。HTML `<td colspan/rowspan>` 能表达合并，但本机未验证 Word 转换后的 gridSpan/vMerge 形态（未查到）。 | `docx-backend-实测.md` §一 链 2 |

**规范层事实**（ISO/IEC 29500-1 原文，经 Microsoft Learn Open XML SDK 页转引；ECMA-376 现行为 5th edition，Part 1 为 2016 年 12 月版，https://ecma-international.org/publications-and-standards/standards/ecma-376/ ）：
- `gridSpan`：「This element specifies the number of grid columns in the parent table's table grid which shall be spanned by the current cell. This property allows cells to have the appearance of being merged」（https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.gridspan ）。
- `vMerge`：「this cell is part of a vertically merged set of cells … whether this cell continues the vertical merge or starts a new merged group」；`val` 取 `restart` / `continue`；「If a vertically merged group of cells do not span the same set of grid columns, then the document is non-conformant」（https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.verticalmerge ）。
- `sectPr`：「For the final section, this information is stored as the last child element of the body element」，子元素含 `pgSz` §17.6.13、`pgMar` §17.6.11、`footerReference` §17.10.2（https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.sectionproperties ）。
- PAGE 域：简单域 `fldSimple w:instr`（§17.16.19）或复杂域 `fldChar begin/separate/end` + `instrText`（§17.16.18）；「if a complex field is not closed before the end of a document story, then no field shall be generated」（https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.fieldchar ）。PAGE 域码：「The PAGE field inserts the number of the page that the Page field is located on」（https://support.microsoft.com/en-us/word/field-codes-page-field ）。
- `rFonts`：「Within a single run, there can be up to four types of content present which shall each be allowed to use a unique font: ASCII … High ANSI … Complex Script … East Asian」，对应 `w:ascii`/`w:hAnsi`/`w:cs`/`w:eastAsia`（https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.runfonts ）。
- 本机模板 3-1 与两库产出与上述同形（本机实验 1、4：`<w:vMerge w:val="restart"/>` + `<w:vMerge/>`、`gridSpan w:val="2"`、页脚 `fldChar` 复杂域）。

### 2.3 维度 ③可审查性

| 方式 | 事实 | 出处 |
|---|---|---|
| A | 中间物是 Markdown 全文：律师可直接读，第二个 agent 可逐行 diff，审查报告可按行号/段落引用；不含任何版式信息，审查只覆盖内容。 | `docx-backend-实测.md` §一（Markdown 约定）；本文自证 |
| B | 中间物是 Python 代码：内容与版式指令混在字符串与调用里；diff 可做但审查者要读代码。 | 无 |
| C | 中间物是 XML diff：Anthropic 历史版 skill 明确「DO NOT use markdown line numbers - they don't map to XML structure」，并把 Markdown 只用于「plan comprehensive tracked changes using markdown before implementing them in OOXML」；模板 3-1 的 `document.xml` 97 KB，可见文本被 rsid/run 切碎。 | https://raw.githubusercontent.com/anthropics/skills/69c0b1a0674149f27b61b2635f935524b6add202/skills/docx/SKILL.md 第 77、107 行；本机实验 3、5 |
| D | 中间物是 JS 代码（本机实验 4 的最小件 40 行）：同 B。 | 本机实验 4 |
| E | 中间物是 JSON 槽位表：可读、可 diff，但只能审查「填了什么」，看不到全文语境。 | `docs/3.0-handoff.md` §2.3 |
| F | 中间物是 HTML：可读可 diff，含样式噪音。 | 无 |
| 通用 | Anthropic 官方 skill 的**读取**通道是「`pandoc -t markdown file.docx`」；本机无 pandoc。成品 DOCX 的审查在任一方式下都要另走渲染（Word COM → PDF → PyMuPDF/看图）。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 15、35–45 行；`docx-backend-实测.md` §二 |

### 2.4 维度 ④两平台可用性

| 方式 | 事实 | 出处 |
|---|---|---|
| A / B / E | 只需模型写文本 + 调 `python 脚本.py`；两平台都有 shell 执行（Claude Code Bash；Codex 通过 `/skills`/`$name` 调 skill 并运行 `scripts/`）。Codex skill 目录布局「`SKILL.md`（必需）+ `scripts/`、`references/`、`assets/`」；Codex 不读 `.claude/skills`，Claude Code 不读 `.agents/skills`。 | `docs/research/skill-platforms-claude-code-与-codex.md` §1.1、§1.2（引 https://learn.chatgpt.com/docs/build-skills.md ） |
| C | 依赖模型直接改 XML 的可靠性；Anthropic 的做法绑定其私有 skill 脚本（`merge_runs.py`、`validate.py` 含 XSD、`soffice.py`）；该 skill 许可为 Proprietary，「users may not … Create derivative works … Distribute」；README 称「provided for demonstration and educational purposes only」。Codex 侧：`openai/skills` 已标 deprecated，`.curated` 40 个 skill 中文档类仅 `pdf`（reportlab）；`openai/plugins` 62 个插件无通用 docx skill，仅两处插件内脚本产 DOCX（一处用 python-docx，一处用 zipfile 直写 OOXML）。Codex CLI 无内置文档工具：「Codex CLI can create and edit files in the working directory, but it doesn't include a visual file preview」。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/LICENSE.txt ；https://raw.githubusercontent.com/anthropics/skills/main/README.md 第 20、24 行 |
| D | Anthropic skill 假设「`docx` is preinstalled, do not run `npm install` first」（其沙箱环境）；Codex/本机无此预装，须 `npm install docx`（本机可行，见 ⑤）。Codex 默认「the agent runs with network access turned off」，`workspace-write` 下「keeps network access turned off unless you enable it」（`[sandbox_workspace_write] network_access = true`），需网络的命令触发审批；`-a never` 下直接失败返回模型。首次安装后离线可跑（本机实验 4）。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 21 行；https://learn.chatgpt.com/docs/agent-approvals-security.md |
| F | 依赖 Windows + Word COM，与平台无关但与机器强绑定。 | `docx-backend-实测.md` §二 |

### 2.5 维度 ⑤本机依赖

| 方式 | 事实 | 出处 |
|---|---|---|
| A / B / E | python-docx 1.2.0、lxml 6.1.1 已装；离线；A 转换 0.25 s。 | 本机实验 2 |
| C | 仅需标准库 `zipfile`；0.004 s。 | 本机实验 3 |
| D | node 24.16、npm 11.13；`npm install docx@latest` 8.3 s 装 22 个包（docx 9.7.1，依赖 jszip、nanoid、xml-js 等）；生成 0.12 s；离线运行。Anthropic skill 的验证链另需 LibreOffice、pandoc、Poppler `pdftoppm`，本机均无。 | 本机实验 4；https://registry.npmjs.org/docx/latest ；https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 89–91 行 |
| F | Word 2021 COM 可用；open 1.0 s、save 0.3 s。 | `docx-backend-实测.md` §一 |
| 通用 | `pip install` 与 `uv --with` 本机挂起（未再尝试）。 | `docx-backend-实测.md` §二 |

### 2.6 维度 ⑥门禁不过后的重试

| 方式 | 事实 | 出处 |
|---|---|---|
| A | 改 Markdown 的一行（如台账 #9 的长待决标记缩短）再重转，其余段落字节不变（①）。版式类问题（列宽、合并）无法在 Markdown 层修，只能改冻结转换器。 | 本机实验 2；台账 #9 |
| B / D | 改代码再跑；内容修改与版式修改都在同一份代码里，D 每次重跑 core.xml 时间戳必变。 | ① |
| C | 改 XML 再打包；须再次面对 run 切碎（merge_runs）与 XSD 合法性。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 57 行 |
| E | 改 JSON 槽位值；版式问题需改填充器（台账 #8–#11 每条都是改脚本）。 | 台账 #8–#11 |
| F | 改 HTML 再经 Word；每次重写本机用户名。 | `docx-backend-实测.md` §一 链 2 |

### 2.7 维度 ⑦与「每版必带审查报告、文书本体直接可提交、律师随后在 Word 里手改」的配合

| 方式 | 事实 | 出处 |
|---|---|---|
| A | 审查报告可引用 Markdown 段落；成品是模板载体上的 DOCX，律师在 Word 里改的是成品，Markdown 不回流（ADR-0002「agent 永不写入案件工作区里已存在的文书文件」）。 | `docs/adr/0002-*.md` |
| B / D | 审查报告引用代码或成品；律师改成品，代码不回流。 | 无 |
| C | 成品最接近模板原件；若律师改过的成品要 agent 续改，只有 C 能直接开既有文件（Anthropic「Edit an existing document → unzip → edit → zip」）；ADR-0002 把「改了一半要 agent 续」列为待议。 | https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md 第 14 行；`docs/adr/0002-*.md` |
| E | 审查报告引用槽位表；律师改成品。 | 无 |
| F | 成品带本机用户名，不满足「直接可提交」（台账 #10 同类）。 | `docx-backend-实测.md` §一 链 2 |

---

## 3. 关键一手引文

### 3.1 Anthropic 官方 docx skill（`anthropics/skills` main，SKILL.md 最近提交 `fa0fa64`，2026-07-17）

决策表（第 9–15 行）：

> | **Create** a new document | Write a `docx` (npm) script, see gotchas below |
> | **Edit** an existing document | `unzip` → edit `word/document.xml` → `zip` (docx-js cannot open existing files) |
> | **Read** content | `pandoc -t markdown file.docx` |

- 给出的**唯一**分工理由是括号里那句「docx-js cannot open existing files」；没有保真度/样式论述。
- Markdown 只作为读取输出，从不作生成中间态；三个历史版本零提及 python-docx。
- 三个版本均**未覆盖** `columnSpan`/`rowSpan`/`gridSpan`/`vMerge`、PAGE 域 XML、`sectPr`、`eastAsia` 字体；字体建议全是 Arial/Times。
- 验证双轨：`validate.py`（XSD + 修订完整性）+「`soffice … --convert-to pdf` → `pdftoppm` → Read the images」。
- 编辑既有文档的核心前提（第 61 行）：「Word splits text across many `<w:r>` runs (revision ids, spell-check markers), so a phrase you can see in the document often doesn't exist as a contiguous string in the XML.」
- 历史 2 月版对编辑的指令：「**Use the Edit tool directly for string replacement. Do not write Python scripts.** Scripts introduce unnecessary complexity.」（https://raw.githubusercontent.com/anthropics/skills/9d2f1ae187231d8199c64b5b762e1bdf2244733d/skills/docx/SKILL.md ）
- 许可：Proprietary，禁止派生与分发；README「provided for demonstration and educational purposes only」。

### 3.2 python-docx

- 模板打开（documents.html）：「Actually, it only lets you make changes to existing documents … Things like styles and page headers and footers are contained separately from the main content, allowing you to place a good deal of customization in your starting document that then appears in the document you produce.」
- `merge()`：「Return a merged cell created by spanning the rectangular region having this cell and other_cell as diagonal corners. Raises InvalidSpanError if the cells do not define a rectangular region.」合并时「any existing content is concatenated … separated … by a paragraph mark」（本机实验 1 验证：`'上\n下'`）。
- 字体：`Font.name` setter 只写 `rFonts_ascii`/`rFonts_hAnsi`；`CT_Fonts` 只声明 `ascii`、`hAnsi` 两属性。
- PAGE 域 API：未找到（站内搜索 `fldSimple` 只命中 hyperlink 分析页）。

### 3.3 docx-js 9.7.1

- 合并：「rowSpan … It is similar to how HTML's `rowspan` works」「columnSpan … similar to how HTML's `colspan` works」。
- 字体：`font({ascii, cs, eastAsia, hAnsi, hint})`；传字符串时四属性同名写入。
- 页码：「This feature only works on Headers and Footers」`children: ["Page #: ", PageNumber.CURRENT]`。
- 模板：`patchDocument`「searches for placeholder text (e.g., {{name}}), and replaces it」「This algorithm is limited to one patch per text run」。
- 时间戳：`CoreProperties` 固定 push `new TimestampElement("dcterms:created")`/`modified`，值 `new Date().toISOString()`，无选项关闭。

### 3.4 Markdown 表格规范

- GFM §4.10：「A table is an arrangement of data with rows and columns, consisting of a single header row, a delimiter row separating the header from the data, and zero or more data rows. … Block-level elements cannot be inserted in a table.」全规范无 colspan/rowspan/span 字样。（https://github.github.com/gfm/#tables-extension- ）
- pandoc 手册 grid tables：「Cells can span multiple columns or rows」；pipe tables「cannot contain block elements … and cannot span multiple lines」。本机无 pandoc。（https://pandoc.org/MANUAL.html#extension-grid_tables ）

### 3.5 Codex 能做什么（learn.chatgpt.com，2026-09-05；本机 codex-cli 0.152.0 `--help`）

- 执行：「Select the sandbox policy to use when executing model-generated shell commands [possible values: read-only, workspace-write, danger-full-access]」；git 目录默认推荐「`Auto` (workspace write + on-request approvals)」；「By default, `codex exec` runs in a read-only sandbox」（https://learn.chatgpt.com/docs/agent-approvals-security.md ；https://learn.chatgpt.com/docs/non-interactive-mode.md ）。
- 网络：「By default, the agent runs with network access turned off」；「the default `workspace-write` sandbox mode keeps network access turned off unless you enable it in your configuration: `[sandbox_workspace_write] network_access = true`」。
- Windows：「The app can run natively in PowerShell with a Windows sandbox instead of requiring WSL」；`[windows] sandbox = "elevated"`（首选）或 `"unelevated"`；WSL2 可选，WSL1 自 0.115 不支持（https://learn.chatgpt.com/docs/windows/windows-sandbox.md ）。
- Skills：「A skill is a directory with a `SKILL.md` file plus optional scripts and references」；「Prefer instructions over scripts unless you need deterministic behavior or external tooling」；skill 脚本经 shell 执行，受 `approval_policy.granular.skill_approval` 审批（https://learn.chatgpt.com/docs/build-skills.md ；config-reference）。
- Shell 工具：`shell`（Windows 默认）或 unified_exec 的 `exec_command`/`write_stdin`；默认 `timeout_ms`/`yield_time_ms` 10000 ms，上限 30000 ms，后台轮询最长 300000 ms（`codex-rs/core/src/exec.rs` `DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000`；config-reference `background_terminal_max_timeout`）。本机 Word COM 冷启动 2.4–4.4 s、docx-js 安装 8 s，均在 10 s 内；渲染门禁多件时须注意此默认值。
- 官方 docx skill：未找到（见 2.4 C 行）。

---

## 4. 本机实验记录

环境同 `docx-backend-实测.md`：Windows 11、Word 2021、Python 3.14、python-docx 1.2.0、PyMuPDF 1.28.2、node 24.16、npm 11.13。全部在 scratchpad 目录，产物不入仓库；正文只用甲乙丙占位。注意 Git Bash 下的 Windows Python 不认 `/d/…` 路径，须用 `D:/…`。

| # | 做了什么 | 结果 | 耗时 |
|---|---|---|---|
| 0 | 扫描 19 件模板的 gridSpan/vMerge/页脚域形态 | 含合并的 4 件：1-1（5 表，vMerge 4）、3-1（1 表，gridSpan 1、vMerge 4）、3-2（同 3-1）、8-2（1 表，gridSpan 1）。四件页脚均为 `fldChar` 复杂域含 PAGE。3-1 表格 5 列 grid `[866,3330,1445,1350,1345]`，第 3–4 行第 0/1 列 vMerge restart/continue，末行「合计」gridSpan=2 | 无 |
| 1 | 打开模板 3-1、清 body 留 sectPr、`add_table(8,5)`，用 `merge()` 复现同位置纵向合并与末行横向合并；另测两格都有内容时合并 | 产出 `<w:gridSpan w:val="2"/>`、`<w:vMerge w:val="restart"/>`、`<w:vMerge/>`，与模板形态一致；有内容合并得 `'上\n下'`（与文档「concatenated … by a paragraph mark」一致）。Word 打开 1 页，页脚渲出 "1"，PyMuPDF 检出 8 行表格 | 0.016 s 生成；Word 1.7 s（会话首件） |
| 2 | 方式 A：`md2docx_tpl.py` + 模板 1-2 + 样例 Markdown 跑两次，逐 zip 条目比对 | 除 `docProps/core.xml`（脚本主动写当前时间）外全部条目相同；`document.xml` 相同。Word 1 页，字体 FangSong/MicrosoftYaHei（后者为方正小标宋简体替换，与 §三事实一致） | 0.25 s |
| 3 | 方式 C：标准库 zipfile 解包 3-1、对 `document.xml` 做 `XXXXXX→甲乙丙` 字符串替换、固定条目时间重打包，跑两次 | 替换命中 **0** 处（XML 里是 `<w:t>XXX</w:t>` + 另一 run 的 `XXX`，63 个 `<w:t>` 含 X 的碎片）；两次输出字节全同；python-docx 可开，表格 1、页脚段 1 | 0.004 s |
| 4 | 方式 D：`npm install docx@latest`；写 40 行 docx-js（A4、边距、页脚 `PageNumber.CURRENT`、`font:{ascii,hAnsi,eastAsia,cs}`、`rowSpan`/`columnSpan` 表格）跑两次；Word 渲染；PyMuPDF 检查 | 安装 8.3 s / 22 包 / 9.7.1；生成 0.12 s；两次仅 `core.xml` 不同（`dcterms:created/modified` 毫秒级时间）；`document.xml` 相同，gridSpan 2、vMerge 6、`w:eastAsia="仿宋"` 24 处，`pgSz 11906×16838`，页脚 `fldChar begin / instrText PAGE / separate / end`；python-docx 可开；Word 1 页，页脚 "1"，字体 FangSong + MicrosoftYaHei（方正小标宋简体替换） | 见左 |
| 5 | docx-js `patchDocument` 空补丁往返模板 3-1 | 输出多 5 个目录条目；`document.xml` 仅 `mc:Ignorable` 追加 `w15`；`app.xml` 少量差异；sectPr、vMerge 4、gridSpan 1 保留；`core.xml` 原作者信息原样保留；Word 3 页正常 | 0.3 s |
| 6 | Word COM 批量渲染四件（实验 1、2、4、5 产物） | 全部正常导出，无修复提示；Word 启动 1.1 s，首件 1.7 s，其后 0.26–0.35 s | 无 |

---

## 5. 结论

### 5.1 一句话

**「先 Markdown 再 DOCX」这层中间物本身不是必要条件；必要的是「冻结的确定性转换步骤 + 官方模板作为版式载体」。** Markdown 只是这一步的输入格式之一，它的价值在可审查性（③）和局部重试（⑥），代价在表达力（②的合并单元格、列宽）。

### 5.2 分条

1. **确定性不来自 Markdown，来自冻结代码。** A 与 B 用同一库、同一产出；唯一差别是代码是否冻结（2.1）。B、C、D 每次由模型现写中间物，失败面就是各库的已知坑：python-docx 不写 `eastAsia`、无 PAGE 域 API（B）；Word run 切碎让「看得见的字在 XML 里不存在」（C，Anthropic 为此配了专用脚本）；docx-js 不能开模板、要逐项复刻版式、时间戳不可关（D）。所以「模型现产 DOCX」的三条路都要再配一层确定性工具才稳，Anthropic 自己的 skill 就是「模型写代码 + 私有脚本 + LibreOffice 渲染目视」的组合，且许可不允许派生分发。
2. **对官方模板的保真取决于「是否开模板」而不是「是否经过 Markdown」。** A、C、E 开模板，天然继承单节 A4、页边距、页脚 PAGE 域、样式表；D 不能开模板（只能 patch 占位符），所有版式要在代码里重打一遍；F 经 Word 转换降级并写入用户名。
3. **合并单元格是 A 当前约定的缺口，不是 A 路线的缺口。** GFM 表格没有跨行跨列语法（3.4），但转换器底下的 `merge()` 能产出与模板同形的 gridSpan/vMerge（实验 1）。补一条最小集约定（例如单元格续接标记）即可覆盖 4 件模板；这仍是冻结转换器的一次性改动，不是模型每次的负担。列宽、行高同理（实验 0 已有模板 grid 数值可直接照抄）。
4. **可审查性与局部重试是 Markdown 相对代码/XML 的实质优势。** 审查报告按段落引用 Markdown；门禁不过时改一行重转，其余字节不变（2.6）。代码（B、D）和 XML（C）作为中间物，律师读不了，第二个 agent 也只能审「意图」而非「文本」。这条优势与本项目「每版必带审查报告」直接对应（2.7）。
5. **两平台与本机依赖上 A 最轻。** 只要 python + 已装的 python-docx；不依赖任何平台私有 skill、不依赖 npm 安装、不依赖 LibreOffice/pandoc/Poppler。D 在本机也可行（npm 8 s、离线运行），但 Anthropic 的验证链在本机不存在，要换成本项目自己的 Word COM 门禁。

### 5.3 若不用 Markdown，替代是什么、代价是什么

| 替代 | 能换到什么 | 代价 |
|---|---|---|
| **D（docx-js）** | 合并单元格、`eastAsia` 字体、PAGE 域都是一等 API，模型无需绕坑；生成快、离线 | 不能以官方模板为载体，19 件模板的版式全部要在代码里复刻并长期维护；中间物是代码，律师不可审；每次输出时间戳必变；npm 依赖 |
| **C（直接 OOXML）** | 保真最高；律师改过的成品可续改 | 模型直接改 97 KB 的 XML，run 切碎与 XSD 合法性要靠专用脚本（本机没有、官方的不能派生）；中间物不可审；原作者信息要另清 |
| **E（槽位填充）** | 语义与版式分界清晰、已有 2.0 代码 | 已被裁定「门禁前不做」；台账 #8–#11 与 legal-skills 五轮返工证明「每种新版式开一个口子」是路线固有 |
| **B（现写 python-docx）** | 与 A 同产出、零新依赖 | 等于把冻结转换器交给模型每次重写；确定性与可审查性都退回代码层 |

### 5.4 在何条件下 Markdown 层是必要的

- 要求「审查报告能按段落引用中间物、律师或第二个 agent 能直接读 diff」时，必要（只有 A、E、F 的中间物是非代码文本，E 无全文、F 有样式噪音）。
- 要求「同一输入两次产出除时间戳外字节一致」且不额外写工具时，A 已满足，D 不满足，C 需先解决 run 切碎。
- 若上述两条都不要求、且接受把 19 件模板版式用代码复刻并维护，D 是可行替代；若需要续改律师已改过的成品，则无论主路线为何，都要另有一条 C 类通道（ADR-0002 已把它列为待议）。

### 5.5 本调研留下的空格

- ECMA-376 Part 1 PDF 原文未直接抓取，规范引文经 Microsoft Learn 转引；PAGE 域在 §17.16.5 下的具体小节号未查到。
- Codex 文档未点名 `npm install`/`pip install`，「需网络的命令触发审批」是按其网络策略推论。
- F 方式经 Word 转换后合并单元格的 XML 形态：未测。
