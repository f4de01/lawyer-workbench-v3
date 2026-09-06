---
"loo0ng-skills": minor
---

新增参考 skill `loo0ng-to-docx`：两个 CLI，互不 import。`scripts/md2docx.py` 冻结转换器只依赖 python-docx、离线：输入 Markdown 最小集（一级标题、正文段、`:left:` 顶格、`:right:` 右对齐、管道表、空行分隔），打开该节点的官方模板、清 body 只留 sectPr、段落格式与字体取自模板里现成的段落，第 n 张管道表照抄模板第 n 张表的 tblPr、列宽、每行行高与格格式，合并单元格用 `<`（并左）`^`（并上）约定，模板里没有对应的表就出等宽自由表；最小集之外的写法与表形不合一律拒绝；收尾清元数据、正文以表格收尾补一个空段；默认写到 `%TEMP%/loo0ng-to-docx/`。`scripts/gate.py` 门禁只依赖 PyMuPDF 与 powershell.exe（Word COM 出 PDF），只读、可单独对任意 DOCX 跑：不通过项有行高与页数阈值、空白页、表宽超页面、页脚 PAGE 域写死或丢失、表格直接接 sectPr、元数据残留、模板占位与说明段残留；披露项有空单元格坐标、请求字体不在嵌入字体里、页数、有字没渲出来；`--deliver` 通过才一次性拷进工作区且不覆盖；没有渲染后端退出码 2、不降级。`references/最小集.md` 与 `references/审查报告.md` 定稿最小集、合并约定与审查报告五段格式。跑器 `用例.json` 新增可选键 `Codex沙箱`（Codex 沙箱里起不来 Word COM）。另交付种子「模板」与用例「出一版」。
