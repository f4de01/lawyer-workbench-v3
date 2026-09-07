#!/bin/bash
# 第一批：环境、依赖、Word 版本、Word 的 AppleScript 字典。
# 不联网、不起 Word、不装东西 —— 沙箱里也该跑得动。依据 issue #40、#41。
# 一律不 set -e：任何一条失败都要继续，失败本身就是要收集的事实。

cd "$(dirname "$0")/.." || exit 2
OUT="出"
mkdir -p "$OUT"

probe() {
  local file="$1"; shift
  local title="$1"; shift
  {
    printf '### %s\n' "$title"
    printf '$ %s\n' "$*"
    printf -- '---\n'
    "$@" 2>&1
    printf -- '\n--- 退出码 %s ---\n\n' "$?"
  } >> "$OUT/$file"
}

: > "$OUT/01-环境.txt"
: > "$OUT/02-依赖.txt"
: > "$OUT/03-Word.txt"
: > "$OUT/06-字典.txt"

echo "01 环境"
probe 01-环境.txt "系统版本"      sw_vers
probe 01-环境.txt "芯片"          uname -m
probe 01-环境.txt "python3 在哪"  bash -c 'command -v python3 || echo 没有 python3'
probe 01-环境.txt "python3 版本"  bash -c 'python3 -V 2>&1 || true'
probe 01-环境.txt "node"          bash -c '(command -v node && node -v) || echo 没有 node（npx 那条会整条落空）'
probe 01-环境.txt "npx"           bash -c 'command -v npx || echo 没有 npx'
probe 01-环境.txt "codex"         bash -c '(command -v codex && codex --version) || echo 没有 codex 命令'
probe 01-环境.txt "git"           bash -c 'git --version 2>&1 || true'
probe 01-环境.txt "gh 登录态"     bash -c 'command -v gh >/dev/null && gh auth status 2>&1 || echo 没有 gh'

echo "02 依赖"
probe 02-依赖.txt "python-docx" bash -c 'python3 -c "import docx; print(\"python-docx OK\", getattr(docx, \"__version__\", \"版本号未暴露\"))" 2>&1'
probe 02-依赖.txt "PyMuPDF"     bash -c 'python3 -c "import pymupdf; print(\"PyMuPDF OK\", pymupdf.__version__)" 2>&1'
probe 02-依赖.txt "pip 里有没有这两件" bash -c 'python3 -m pip list 2>/dev/null | grep -iE "docx|mupdf|fitz" || echo pip 里没有这两件'

echo "03 Word"
probe 03-Word.txt "Word 装在哪" bash -c 'ls -d /Applications/Microsoft*Word.app 2>&1 || echo 没找到 Word'
probe 03-Word.txt "Word 版本"   bash -c 'defaults read "/Applications/Microsoft Word.app/Contents/Info.plist" CFBundleShortVersionString 2>&1 || echo 读不到版本'
probe 03-Word.txt "Word 构建号" bash -c 'defaults read "/Applications/Microsoft Word.app/Contents/Info.plist" CFBundleVersion 2>&1 || echo 读不到构建号'
probe 03-Word.txt "LibreOffice" bash -c 'ls -d /Applications/LibreOffice.app 2>/dev/null || command -v soffice || echo 没有 LibreOffice'

echo "06 Word 的 AppleScript 字典（#41 的第 2、3 问靠它直接答，不用起 Word）"
probe 06-字典.txt "sdef 读字典" bash -c 'sdef "/Applications/Microsoft Word.app" > 出/word-字典.sdef 2>&1 && echo "已写到 出/word-字典.sdef，字节数：$(wc -c < 出/word-字典.sdef)" || echo "sdef 失败（上面就是报错）"'
probe 06-字典.txt "有没有 save as / PDF" bash -c 'grep -oiE "<command name=\"save as\"|format PDF|\"PDF\"" 出/word-字典.sdef 2>/dev/null | sort | uniq -c | head -20 || echo 字典里没搜到'
probe 06-字典.txt "有没有 compute statistics（对应 ComputeStatistics）" bash -c 'grep -n -iE "compute statistics|statistic" 出/word-字典.sdef 2>/dev/null | head -20 || echo 字典里没有 compute statistics'
probe 06-字典.txt "有没有 export / repaginate / print out" bash -c 'grep -n -iE "<command name=\"(export|repaginate|print out)\"" 出/word-字典.sdef 2>/dev/null | head -20 || echo 没有这三个'

printf '\n第一批跑完，出/ 下现在有：\n'
ls -1 "$OUT"
