#!/bin/bash
# 第三批：要人在场。第一次自动化办公套件时 macOS 会弹一次授权框，脚本自己点不了。
# 依据 issue #41。
#
# 律师这台机器上的主力是 WPS，多半没有 Word。所以顺序是：先 WPS，有 Word 再顺手试 Word。
# WPS for Mac 的 AppleScript 支持没有公开文档，能不能驱动本身就是要拿的事实。
# 真正的答案多半在 出/06-字典.txt 里（不用起 app），这一批是去验证字典说的对不对。

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

# 找 WPS 的 app 名：AppleScript 的 tell application 要准确的名字
WPS_APP=""
for a in "/Applications/wpsoffice.app" "/Applications/WPS Office.app"; do
  [ -e "$a" ] && WPS_APP="$(basename "$a" .app)" && break
done
if [ -z "$WPS_APP" ]; then
  for a in /Applications/WPS*.app; do
    [ -e "$a" ] && WPS_APP="$(basename "$a" .app)" && break
  done
fi

probe "找到的 WPS app 名" bash -c "echo \"WPS_APP='$WPS_APP'\"; [ -n '$WPS_APP' ] || echo '没找到 WPS，下面 WPS 的几步会全部跳过'"

# ---- wpscli：上一轮在 WPS 的 bundle 里发现的命令行入口，比 AppleScript 更有戏，先试它 ----
# 一律先抄它自己的帮助，不猜参数（02-装.sh 同一条规矩）。
WPSCLI=""
for c in /Applications/wpsoffice.app/Contents/MacOS/wpscli "/Applications/WPS Office.app/Contents/MacOS/wpscli"; do
  [ -x "$c" ] && WPSCLI="$c" && break
done

probe "wpscli 在不在" bash -c "echo \"WPSCLI='$WPSCLI'\"; [ -n '$WPSCLI' ] || echo '没找到 wpscli'"

if [ -n "$WPSCLI" ]; then
  echo "wpscli：先抄帮助，不猜参数"
  probe "wpscli --help"    bash -c "perl -e 'alarm 30; exec @ARGV' \"$WPSCLI\" --help  < /dev/null 2>&1"
  probe "wpscli -h"        bash -c "perl -e 'alarm 30; exec @ARGV' \"$WPSCLI\" -h      < /dev/null 2>&1"
  probe "wpscli（无参数）" bash -c "perl -e 'alarm 30; exec @ARGV' \"$WPSCLI\"         < /dev/null 2>&1"
  probe "wpscli --version" bash -c "perl -e 'alarm 30; exec @ARGV' \"$WPSCLI\" --version < /dev/null 2>&1"

  echo "wpscli：照 LibreOffice 那套最常见的写法试一次转换（成不成都记）"
  probe "wpscli --convert-to pdf（样例A）" bash -c "
    perl -e 'alarm 120; exec @ARGV' \"$WPSCLI\" --convert-to pdf --outdir \"$HERE/出\" \"$HERE/样例/样例A-单页.docx\" < /dev/null 2>&1"
  probe "wpscli --headless --convert-to pdf（样例A）" bash -c "
    perl -e 'alarm 120; exec @ARGV' \"$WPSCLI\" --headless --convert-to pdf --outdir \"$HERE/出\" \"$HERE/样例/样例A-单页.docx\" < /dev/null 2>&1"
  probe "wpscli 转换后出了什么" bash -c 'ls -l 出/*.pdf 2>&1 || echo 没有 PDF'
else
  probe "wpscli" bash -c 'echo 没有 wpscli，跳过'
fi

if [ -n "$WPS_APP" ]; then
  echo "WPS：样例 A（单页）"
  probe "WPS 样例A 导出" osascript "probe/wps-导出.applescript" "$WPS_APP" "$HERE/样例/样例A-单页.docx" "$HERE/出/wps-样例A.pdf"

  echo "WPS：样例 B（多页带页脚，Windows 侧 Word 就是这件稳定崩）"
  probe "WPS 样例B 导出" osascript "probe/wps-导出.applescript" "$WPS_APP" "$HERE/样例/样例B-多页带页脚.docx" "$HERE/出/wps-样例B.pdf"
else
  probe "WPS 导出" bash -c 'echo 没有 WPS，跳过'
fi

if [ -e "/Applications/Microsoft Word.app" ]; then
  echo "Word 也在，顺手试一遍（预期这台机器上没有）"
  probe "Word 样例A 导出" osascript "probe/word-导出.applescript" "$HERE/样例/样例A-单页.docx" "$HERE/出/word-样例A.pdf"
  probe "Word 样例B 导出" osascript "probe/word-导出.applescript" "$HERE/样例/样例B-多页带页脚.docx" "$HERE/出/word-样例B.pdf"
else
  probe "Word 导出" bash -c 'echo 这台机器没有 Microsoft Word，跳过（预期如此）'
fi

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
probe "进程还活着吗" bash -c 'pgrep -fl "wps\|WPS\|Microsoft Word" || echo 相关进程都不在（正常收尾或已崩）'

printf '\n第三批跑完，看 出/07-渲染.txt\n'
