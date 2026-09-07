#!/bin/bash
# 第三批：要人在场。第一次自动化办公套件时 macOS 会弹一次授权框，脚本自己点不了。
# 依据 issue #41。
#
# 律师这台机器上的主力是 WPS，没有 Word。两条路，先命令行后 AppleScript：
#   1. wpscli：WPS bundle 里自带的命令行入口（上一轮发现），比 AppleScript 有戏
#   2. osascript 逐条：每条单独一个进程、单独编译，一条挂了其余照跑
#
# 为什么不用 .applescript 文件：整份文件只要有一处编译不过就一行都跑不了。
# 上一轮就是这么白跑的（中文 handler 名，报 -2740，WPS 一次都没被驱动过）。
# 逐条 osascript -e 之后，app 名经 shell 展开成字面量，编译器能正常加载术语字典；
# format PDF 之类的专有术语解析不了时，只失败那一条，报错原文照样拿到。

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

# 逐条试一小段 AppleScript：独立进程、独立编译，失败只失败这一条
tryas() {
  local label="$1" script="$2"
  {
    printf '### AS: %s\n' "$label"
    printf '%s\n' "$script"
    printf -- '---\n'
    perl -e 'alarm 90; exec @ARGV' osascript -e "$script" < /dev/null 2>&1
    printf -- '\n--- 退出码 %s ---\n\n' "$?"
  } >> "$OUT/07-渲染.txt"
}

HERE="$(pwd)"
INA="$HERE/样例/样例A-单页.docx"
INB="$HERE/样例/样例B-多页带页脚.docx"
OUTA="$HERE/出/as-样例A.pdf"
OUTB="$HERE/出/as-样例B.pdf"

# ---------------------------------------------------------------- 找 WPS
WPS_APP=""
for a in "/Applications/wpsoffice.app" "/Applications/WPS Office.app" /Applications/WPS*.app; do
  [ -e "$a" ] || continue
  WPS_APP="$(basename "$a" .app)"
  break
done
probe "找到的 WPS app 名" bash -c "echo \"WPS_APP='$WPS_APP'\"; [ -n '$WPS_APP' ] || echo '没找到 WPS'"

# ---------------------------------------------------------------- 路线一：wpscli
WPSCLI=""
for c in /Applications/wpsoffice.app/Contents/MacOS/wpscli "/Applications/WPS Office.app/Contents/MacOS/wpscli"; do
  [ -x "$c" ] && WPSCLI="$c" && break
done
probe "wpscli 在不在" bash -c "echo \"WPSCLI='$WPSCLI'\"; [ -n '$WPSCLI' ] || echo '没找到 wpscli'"

if [ -n "$WPSCLI" ]; then
  echo "wpscli：先抄它自己的帮助，不猜参数"
  probe "wpscli --help"    bash -c "perl -e 'alarm 30; exec @ARGV' '$WPSCLI' --help    < /dev/null 2>&1"
  probe "wpscli -h"        bash -c "perl -e 'alarm 30; exec @ARGV' '$WPSCLI' -h        < /dev/null 2>&1"
  probe "wpscli（无参数）" bash -c "perl -e 'alarm 30; exec @ARGV' '$WPSCLI'           < /dev/null 2>&1"
  probe "wpscli --version" bash -c "perl -e 'alarm 30; exec @ARGV' '$WPSCLI' --version < /dev/null 2>&1"

  echo "wpscli：照最常见的几种写法各试一次（成不成都记）"
  probe "wpscli --convert-to pdf"        bash -c "perl -e 'alarm 120; exec @ARGV' '$WPSCLI' --convert-to pdf --outdir '$HERE/出' '$INA' < /dev/null 2>&1"
  probe "wpscli --headless --convert-to" bash -c "perl -e 'alarm 120; exec @ARGV' '$WPSCLI' --headless --convert-to pdf --outdir '$HERE/出' '$INA' < /dev/null 2>&1"
  probe "wpscli -o 输出 输入"            bash -c "perl -e 'alarm 120; exec @ARGV' '$WPSCLI' -o '$HERE/出/cli-样例A.pdf' '$INA' < /dev/null 2>&1"
  probe "wpscli 之后出了什么"            bash -c 'ls -l 出/*.pdf 2>&1 || echo 没有 PDF'
else
  probe "wpscli" bash -c 'echo 没有 wpscli，跳过'
fi

# ---------------------------------------------------------------- 路线二：osascript 逐条
if [ -n "$WPS_APP" ]; then
  echo "WPS：逐条试 AppleScript（第一条会弹授权框）"

  tryas "activate" "tell application \"$WPS_APP\" to activate"
  sleep 3

  tryas "open(POSIX file 对象)" "tell application \"$WPS_APP\" to open POSIX file \"$INA\""
  tryas "open(纯字符串路径)"    "tell application \"$WPS_APP\" to open \"$INA\""
  sleep 2

  tryas "count of documents"      "tell application \"$WPS_APP\" to count of documents"
  tryas "name of front document"  "tell application \"$WPS_APP\" to get name of front document"

  tryas "compute statistics(pages)" "tell application \"$WPS_APP\" to compute statistics front document statistic statistic pages"
  tryas "repaginate"                "tell application \"$WPS_APP\" to repaginate front document"
  tryas "count of pages"            "tell application \"$WPS_APP\" to count of pages of front document"

  tryas "save in ... as PDF"      "tell application \"$WPS_APP\" to save front document in POSIX file \"$OUTA\" as \"PDF\""
  tryas "save as(Word 写法)"      "tell application \"$WPS_APP\" to save as front document file name \"$OUTA\" file format format PDF"
  tryas "export to ... as PDF"    "tell application \"$WPS_APP\" to export front document to POSIX file \"$OUTA\" as \"PDF\""
  tryas "save in(不指定格式)"     "tell application \"$WPS_APP\" to save front document in POSIX file \"$OUTA\""
  tryas "print front document"    "tell application \"$WPS_APP\" to print front document"

  tryas "close saving no" "tell application \"$WPS_APP\" to close front document saving no"

  echo "WPS：样例 B（多页带页脚）再走一遍能走通的那条路"
  tryas "B: open"          "tell application \"$WPS_APP\" to open POSIX file \"$INB\""
  sleep 2
  tryas "B: count pages"   "tell application \"$WPS_APP\" to count of pages of front document"
  tryas "B: save in as PDF" "tell application \"$WPS_APP\" to save front document in POSIX file \"$OUTB\" as \"PDF\""
  tryas "B: close"         "tell application \"$WPS_APP\" to close front document saving no"
else
  probe "WPS AppleScript" bash -c 'echo 没有 WPS，跳过'
fi

# ---------------------------------------------------------------- Word（预期没有）
if [ -e "/Applications/Microsoft Word.app" ]; then
  echo "Word 也在，顺手试一遍"
  tryas "Word activate"      "tell application \"Microsoft Word\" to activate"
  tryas "Word open"          "tell application \"Microsoft Word\" to open POSIX file \"$INA\""
  tryas "Word compute stats" "tell application \"Microsoft Word\" to compute statistics active document statistic statistic pages"
  tryas "Word save as PDF"   "tell application \"Microsoft Word\" to save as active document file name \"$HERE/出/word-样例A.pdf\" file format format PDF"
  tryas "Word close"         "tell application \"Microsoft Word\" to close active document saving no"
else
  probe "Word" bash -c 'echo 这台机器没有 Microsoft Word，跳过（预期如此）'
fi

# ---------------------------------------------------------------- 收尾
probe "产出的 PDF" bash -c 'ls -l 出/*.pdf 2>&1 || echo 一个 PDF 都没出来'
probe "PDF 页数（mdls）" bash -c 'for f in 出/*.pdf; do [ -e "$f" ] || continue; printf "%s: " "$f"; mdls -name kMDItemNumberOfPages -raw "$f" 2>&1; echo; done'
probe "PDF 页数（PyMuPDF）" bash -c 'python3 -c "
import glob, sys
try:
    import pymupdf
except Exception as e:
    print(\"PyMuPDF 不可用：\", e); sys.exit(0)
for f in sorted(glob.glob(\"出/*.pdf\")):
    d = pymupdf.open(f); print(f, d.page_count, \"页\"); d.close()
" 2>&1'
probe "进程还活着吗" bash -c 'pgrep -fl "wps" ; pgrep -fl "Microsoft Word" ; echo "（上面没有行就是都不在）"'

printf '\n第三批跑完，看 出/07-渲染.txt\n'
