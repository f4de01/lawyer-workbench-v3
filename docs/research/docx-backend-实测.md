# 本机 Markdown→DOCX 转换与真实渲染门禁实测

票：[#13](https://github.com/f4de01/lawyer-workbench-v3/issues/13)。日期 2026-09-04。只记事实，不做决策；决策在「文书出件机制与验收项」票。

**机器**：Windows 11 Pro、Word 2021 C2R 16.0.20326、Python 3.14.2、python-docx 1.2.0、PyMuPDF 1.28.2、lxml 6.1.1、node 24.16 / npm 11.13、uv 0.12.1。无 LibreOffice、pandoc、pywin32、任何 Markdown 解析库。中文路径全程正常。
**模板**：`knowledge/模板/1-2.关于管理人印章备案的报告.docx`（主测）、`3-1.…无异议债权的报告.docx`（页脚页码验证）。样例正文全用甲乙丙占位，无案件内容。

## 一、Markdown → DOCX 的链

| 链 | 做法 | 结果 | 耗时 |
|---|---|---|---|
| 链 1 | Markdown → python-docx，以官方模板为版式载体：打开模板、清空 body 只留 `sectPr`、按约定写段/表；收尾清元数据、表后留空段 | **跑通**。A4、页边距、页脚 PAGE 字段（模板 3-1）全部保留并渲出；字体按模板写入 run（方正小标宋简体 18pt 标题、仿宋 16pt 正文、固定行距 25pt、首行缩进 2 字） | < 0.2 s |
| 链 2 | Markdown → HTML（自写 CSS）→ Word COM `Documents.Open` → `SaveAs2(…, 12)` | **跑通但降级**：段落样式落为 `Normal (Web)` / `Heading 1`，h1 字体丢失（渲出 SimSun）；Word 把本机用户名写进 author / lastModifiedBy（新的第三方信息源）；表格列宽按内容分配。`@page` 生效（A4、3.17/2.54cm） | open 1.0 s、save 0.3 s |
| pandoc | 未安装 | 未测 | — |
| node `docx` | npm registry 可达（9.7.1） | 未安装、未测 | — |

链 1 的 Markdown 约定是自定最小集（`# ` 标题、管道表、`:right:` 右对齐），没有用解析库；脚本见 `docs/research/docx-backend/md2docx_tpl.py`。列宽、行高沿用 python-docx 默认，与模板不一致（模板的「印章名称」列更窄、「印模」行更高）。全程无网络请求（B8）。

## 二、真实渲染后端

**Word COM 可用**，PowerShell `New-Object -ComObject Word.Application`，不需要 pywin32：`Documents.Open(path, $false, $true)` 只读打开，`ComputeStatistics(2)` 取页数，`ExportAsFixedFormat(path, 17)` 出 PDF。

| 项 | 数值 |
|---|---|
| Word 冷启动 | 2.4–4.4 s |
| 同会话首个文件 open+export | 1.0–1.7 s |
| 其后每个文件 | 0.17–0.2 s |
| 一次瞬时失败 | 同会话第 6 个文件报「由于出现意外错误，导出失败」，重试即成功 |

**Python 侧的坑**（原因未查，只记现象）：`python -m pip install`（含本地 wheel `--no-deps`）60–150 s 不结束，`pip download` 秒级完成；`uv run --with X` 装包 14 ms 后卡在 `Querying Python at …archive-v0…` 超过 3 分钟，裸 `uv run python` 正常。因此 Python 驱动 Word 的可用方式是 `subprocess` 调 `powershell.exe`（已验证）。

**PDF 检查**：PyMuPDF 已装。可取页数、空白页（无文字无图片）、嵌入字体名、文本块越界、`find_tables()` 行高；60 dpi 光栅 4 页 55 ms，可供人眼或模型视觉核对。原型见 `docs/research/docx-backend/gate.py`。

## 三、字体事实

本机未装 方正小标宋简体、仿宋_GB2312、黑体/宋体/楷体（本地化名）；有 FangSong(simfang.ttf)、SimSun、KaiTi、华文仿宋、方正姚体/舒体。Word 把方正小标宋简体替换成 Microsoft YaHei 渲出——**官方模板自身在本机渲染也是如此**。门禁能检出「请求字体 ≠ 嵌入字体」，但不能证明法院机器上的效果。

## 四、五种事故在这条链上的检出

构造五个故障件，走 链 1 → Word PDF → PyMuPDF / python-docx：

| 事故（台账 #8–#11 + 元数据） | 构造 | 静态检查（DOCX） | 渲染检查（PDF） |
|---|---|---|---|
| 空表格填不了 | 「印模」格留空 | 可检（空格坐标 (0,1,1)），但模板该格本来就空（纸质要件，台账 #13），须白名单 | 不可 |
| 长标记撑列 | 5 列分工表「组长」列写长句 | 不可（XML 全对） | **可**：页数 1→2，行高 313 pt / 250 pt。宽列版页数不变但行高 281 pt——行高阈值比页数灵敏 |
| 模板带第三方作者信息 | 保留模板 core.xml | **可**：author / lastModifiedBy 非空、revision=6 | 不可 |
| 空白页 | 末尾 30 个空段 | 不可靠 | **可**：第 2 页无文字无图 |
| 表格收尾触发修复 | `tbl` 直接接 `sectPr` | **可**：body 最后块级元素是 tbl | 不可：本机 Word 静默打开、导出正常（与台账所记一致） |

结论性事实：两种只能靠渲染检出，三种只能靠静态检出，没有一种两边都能检。

## 五、清元数据

python-docx 可置空 author / last_modified_by、revision=1、created / modified 置当前时间；`last_printed` 不接受 `None`，须直接删 `cp:lastPrinted` 元素。链 2 经 Word 存盘会重新写入本机用户名。

## 六、19 件模板全景

均单节、A4 纵向、无页眉、无图片；18/19 页脚含 PAGE 字段（1-2 无）；8-2 页脚有文字。有表格 6 件（1-1 五张）；**含合并单元格 4 件（1-1、3-1、3-2、8-2），Markdown 管道表表达不了**。numbering.xml 9 件。字体：仿宋正文、方正小标宋简体标题、1-1 用黑体、3-1/3-2 用仿宋_GB2312。
