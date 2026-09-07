#!/bin/bash
# 第二批：要人在场。第一次自动化 Word 时 macOS 会弹一次授权框，脚本自己点不了。
# 依据 issue #41。

cd "$(dirname "$0")/.." || exit 2
OUT="出"
mkdir -p "$OUT"
: > "$OUT/07-渲染.txt"

probe() {
  local title="$1"; shift
  {
    printf '### %s\n' "$title"
    printf '$ %s\n' "$*"
    printf -- '---\n'
    "$@" 2>&1
    printf -- '\n--- 退出码 %s ---\n\n' "$?"
  } >> "$OUT/07-渲染.txt"
}

HERE="$(pwd)"

echo "样例 A（单页）"
probe "样例A 导出" osascript "probe/word-导出.applescript" "$HERE/样例/样例A-单页.docx" "$HERE/出/样例A.pdf"

echo "样例 B（多页带页脚，Windows 侧就是这件稳定崩）"
probe "样例B 导出" osascript "probe/word-导出.applescript" "$HERE/样例/样例B-多页带页脚.docx" "$HERE/出/样例B.pdf"

probe "产出的 PDF" bash -c 'ls -l 出/*.pdf 2>&1 || echo 一个 PDF 都没出来'
probe "PDF 页数（mdls）" bash -c 'for f in 出/*.pdf; do [ -e "$f" ] || continue; printf "%s: " "$f"; mdls -name kMDItemNumberOfPages -raw "$f" 2>&1; echo; done'
probe "PDF 页数（PyMuPDF，装了才有）" bash -c 'python3 -c "
import glob, sys
try:
    import pymupdf
except Exception as e:
    print(\"PyMuPDF 不可用：\", e); sys.exit(0)
for f in sorted(glob.glob(\"出/*.pdf\")):
    d = pymupdf.open(f); print(f, d.page_count, \"页\"); d.close()
" 2>&1'
probe "Word 还活着吗" bash -c 'pgrep -fl "Microsoft Word" || echo Word 进程不在（正常收尾或已崩）'

printf '\n第二批跑完，看 出/07-渲染.txt\n'
