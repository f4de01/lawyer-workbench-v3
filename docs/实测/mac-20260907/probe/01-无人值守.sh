#!/bin/bash
# 第一批：不需要人在场的探针。依据 issue #40、#41。
# 一律不 set -e：任何一条失败都要继续，失败本身就是要收集的事实。
# 所有输出只落 ../出/，一步都不出这个包的目录。

cd "$(dirname "$0")/.." || exit 2
OUT="出"
mkdir -p "$OUT"

# macOS 自带没有 timeout：下面凡是要限时的都用 perl 的 alarm，就地写在 bash -c 里
say() { printf '\n=== %s ===\n' "$1"; }

# 每条探针：标题、命令原文、退出码、原始输出，全落同一个文件
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
: > "$OUT/04-安装.txt"
: > "$OUT/05-清单.txt"
: > "$OUT/06-字典.txt"

say "01 环境"
probe 01-环境.txt "系统版本"   sw_vers
probe 01-环境.txt "芯片"       uname -m
probe 01-环境.txt "python3 在哪" bash -c 'command -v python3 || echo 没有 python3'
probe 01-环境.txt "python3 版本" bash -c 'python3 -V 2>&1 || true'
probe 01-环境.txt "node"       bash -c 'command -v node && node -v || echo 没有 node'
probe 01-环境.txt "npx"        bash -c 'command -v npx || echo 没有 npx'
probe 01-环境.txt "codex"      bash -c 'command -v codex && codex --version || echo 没有 codex 命令'
probe 01-环境.txt "git"        bash -c 'git --version 2>&1 || true'
probe 01-环境.txt "gh 登录态"  bash -c 'command -v gh >/dev/null && gh auth status 2>&1 || echo 没有 gh'

say "02 依赖"
probe 02-依赖.txt "python-docx" bash -c 'python3 -c "import docx, sys; print(\"python-docx OK\", getattr(docx, \"__version__\", \"版本号未暴露\"))" 2>&1'
probe 02-依赖.txt "PyMuPDF"     bash -c 'python3 -c "import pymupdf; print(\"PyMuPDF OK\", pymupdf.__version__)" 2>&1'
probe 02-依赖.txt "pip 列表（只看这两件）" bash -c 'python3 -m pip list 2>/dev/null | grep -iE "docx|mupdf|fitz" || echo pip 里没有这两件'

say "03 Word"
probe 03-Word.txt "Word 装在哪"  bash -c 'ls -d /Applications/Microsoft*Word.app 2>&1 || echo 没找到 Word'
probe 03-Word.txt "Word 版本"    bash -c 'defaults read "/Applications/Microsoft Word.app/Contents/Info.plist" CFBundleShortVersionString 2>&1 || echo 读不到版本'
probe 03-Word.txt "Word 构建号"  bash -c 'defaults read "/Applications/Microsoft Word.app/Contents/Info.plist" CFBundleVersion 2>&1 || echo 读不到构建号'
probe 03-Word.txt "LibreOffice"  bash -c 'ls -d /Applications/LibreOffice.app 2>/dev/null || command -v soffice || echo 没有 LibreOffice'

say "04 安装（先抄 CLI 自己的帮助，再试装；不猜参数）"
probe 04-安装.txt "skills CLI 帮助"     bash -c 'npx --yes skills@latest --help 2>&1 < /dev/null'
probe 04-安装.txt "skills add 帮助"     bash -c 'npx --yes skills@latest add --help 2>&1 < /dev/null'
probe 04-安装.txt "试装（非交互，180 秒上限）" bash -c 'perl -e "alarm 180; exec @ARGV" npx --yes skills@latest add f4de01/lawyer-workbench-v3 -a codex < /dev/null 2>&1; echo "（若上面停在交互提问或超时，见 AGENTS.md 第 4 步）"'
probe 04-安装.txt "装到哪了：~/.agents/skills" bash -c 'ls -1 ~/.agents/skills 2>&1 || echo 没有这个目录'
probe 04-安装.txt "装到哪了：~/.codex"         bash -c 'ls -1 ~/.codex 2>&1 || echo 没有这个目录'

say "05 模型可见的 skill 清单"
probe 05-清单.txt "codex debug prompt-input" bash -c 'perl -e "alarm 120; exec @ARGV" codex debug prompt-input "hi" 2>&1 < /dev/null'
probe 05-清单.txt "清单里有没有这七件（逐个 grep）" bash -c '
  for n in loo0ng-setup-case loo0ng-doit ask-loo0ng loo0ng-graph loo0ng-domain loo0ng-filing loo0ng-to-docx; do
    if grep -q -- "$n" "出/05-清单.txt" 2>/dev/null; then
      printf "%-22s 命中，原样的那一行是：\n" "$n"; grep -n -- "$n" "出/05-清单.txt" | head -3
    else
      printf "%-22s 未出现\n" "$n"
    fi
  done'

say "06 Word 的 AppleScript 字典（#41 的第 2、3 问靠它直接答）"
probe 06-字典.txt "sdef 能不能读出来" bash -c 'sdef "/Applications/Microsoft Word.app" > 出/word-字典.sdef 2>&1 && echo "已写到 出/word-字典.sdef，字节数：$(wc -c < 出/word-字典.sdef)" || echo "sdef 失败（上面就是报错）"'
probe 06-字典.txt "有没有 save as / PDF 格式" bash -c 'grep -oiE "<command name=\"save as\"|format PDF|\"PDF\"" 出/word-字典.sdef 2>/dev/null | sort | uniq -c | head -20 || echo 字典里没搜到'
probe 06-字典.txt "有没有 compute statistics（对应 ComputeStatistics）" bash -c 'grep -n -iE "compute statistics|statistic" 出/word-字典.sdef 2>/dev/null | head -20 || echo 字典里没有 compute statistics'
probe 06-字典.txt "有没有 export / repaginate" bash -c 'grep -n -iE "<command name=\"(export|repaginate|print out)\"" 出/word-字典.sdef 2>/dev/null | head -20 || echo 没有 export / repaginate / print out'

printf '\n第一批跑完。输出在 出/ 下：\n'
ls -1 "$OUT"
