#!/bin/bash
# 第一批：环境、依赖、Word 版本、Word 的 AppleScript 字典。
# 不联网、不起 Word、不装东西；沙箱里也该跑得动。依据 issue #40、#41。
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

echo "03 办公套件（WPS 是律师那台机器的主力，Word 多半没有）"
probe 03-Word.txt "装了哪些候选 app" bash -c '
  for pat in "/Applications/wpsoffice.app" "/Applications/WPS Office.app" "/Applications/WPS Office"*.app \
             "/Applications/Microsoft Word.app" "/Applications/LibreOffice.app" "/Applications/Pages.app"; do
    for a in $pat; do [ -e "$a" ] && echo "有：$a"; done
  done
  echo "--- 再按 bundle id 全盘找一遍（mdfind，可能有别的装法）---"
  mdfind "kMDItemCFBundleIdentifier == *wps*" 2>/dev/null | head -5 || true
  mdfind "kMDItemKind == Application && kMDItemDisplayName == *WPS*" 2>/dev/null | head -5 || true
  echo "（上面没有行就是没找到）"'

probe 03-Word.txt "每个候选的版本、bundle id、脚本支持标志" bash -c '
  for a in /Applications/wpsoffice.app "/Applications/WPS Office.app" "/Applications/Microsoft Word.app" /Applications/LibreOffice.app; do
    [ -e "$a" ] || continue
    plist="$a/Contents/Info.plist"
    printf "\n=== %s\n" "$a"
    # defaults read 要不带 .plist 后缀的路径，带了就一个键都读不出来（上一轮 WPS 全报「读不到」
    # 就是踩这个）。一律走 plutil -p，二进制 plist 也认。
    键() { plutil -p "$plist" 2>/dev/null | sed -n "s/.*\"$1\" => //p" | head -1; }
    printf "  版本      : %s
" "$(键 CFBundleShortVersionString)"
    printf "  构建号    : %s
" "$(键 CFBundleVersion)"
    printf "  bundle id : %s
" "$(键 CFBundleIdentifier)"
    printf "  可执行名  : %s
" "$(键 CFBundleExecutable)"
    printf "  NSAppleScriptEnabled : %s
" "$(键 NSAppleScriptEnabled)"
    printf "  OSAScriptingDefinition: %s
" "$(键 OSAScriptingDefinition)"
    printf "  （上面空白 = plist 里没有这个键；plutil 整份 dump 见下）
"
    printf "  --- plist 整份（前 40 行）---
"
    plutil -p "$plist" 2>&1 | head -40 | sed "s/^/    /"
    printf "  bundle 里的 .sdef 文件：\n"
    find "$a" -name "*.sdef" -maxdepth 4 2>/dev/null | head -5 || echo "    （没有）"
    printf "  bundle 里的可执行文件（有没有 CLI 入口）：\n"
    ls -1 "$a/Contents/MacOS" 2>/dev/null | head -10 || echo "    （读不到）"
  done'


echo "06 AppleScript 字典：这一问不用起任何 app 就能答（#41 的第 2、3 问）"
probe 06-字典.txt "逐个 app 抓字典" bash -c '
  抓() {
    local app="$1" tag="$2"
    [ -e "$app" ] || { echo "跳过 $tag：没装"; return; }
    if sdef "$app" > "出/$tag-字典.sdef" 2>"出/$tag-字典.err" && [ -s "出/$tag-字典.sdef" ]; then
      echo "$tag：sdef 成功，字节数 $(wc -c < "出/$tag-字典.sdef")"
      return
    fi
    echo "$tag：sdef 没出东西 -> $(head -3 "出/$tag-字典.err" 2>/dev/null)"
    # sdef 是 Xcode 工具，只装 Command Line Tools 时用不了（上一轮就卡在这）。
    # 它失败不代表 app 不支持 AppleScript，所以再走两条不依赖 Xcode 的路。
    echo "     fallback 1：bundle 里直接找 .sdef 文件"
    find "$app" -name "*.sdef" -maxdepth 5 2>/dev/null | head -3 | while read -r f; do
      cp "$f" "出/$tag-字典.sdef" && echo "     从 bundle 里拷到了：$f（$(wc -c < "出/$tag-字典.sdef") 字节）"
    done
    if [ -s "出/$tag-字典.sdef" ]; then return; fi
    echo "     fallback 2：osascript 问它认不认脚本（这一条会起 app，可能要授权）"
    osascript -e "tell application \"$(basename "$app" .app)\" to return name" 2>&1 | head -3 | sed "s/^/     /"
  }
  抓 /Applications/wpsoffice.app wps
  抓 "/Applications/WPS Office.app" wps
  抓 "/Applications/Microsoft Word.app" word
  抓 /Applications/LibreOffice.app libreoffice'

probe 06-字典.txt "字典里有哪些动词（导出、分页、打印）" bash -c '
  for f in 出/*-字典.sdef; do
    [ -e "$f" ] || continue
    printf "\n=== %s\n" "$f"
    printf "  命令总数：%s\n" "$(grep -c "<command name=" "$f" 2>/dev/null || echo 0)"
    printf "  --- 与导出 / 保存相关 ---\n"
    grep -oiE "<command name=\"[^\"]*(save|export|convert|print)[^\"]*\"" "$f" 2>/dev/null | sort -u | head -20 || echo "    （无）"
    printf "  --- PDF 字样 ---\n"
    grep -oiE "(format PDF|\"PDF\"|PDF file format)" "$f" 2>/dev/null | sort -u | head -10 || echo "    （无）"
    printf "  --- 分页强制（对应 Windows 的 ComputeStatistics(2)，ADR-0006 那个坑）---\n"
    grep -n -iE "compute statistics|repaginate|pagination" "$f" 2>/dev/null | head -10 || echo "    （无）"
    printf "  --- 全部命令名（供开发者自己看）---\n"
    grep -oE "<command name=\"[^\"]*\"" "$f" 2>/dev/null | sed "s/<command name=//" | sort -u | head -60
  done
  ls 出/*-字典.sdef >/dev/null 2>&1 || echo "一个字典都没抓到：这本身就是结论，说明装的 app 都不支持 AppleScript"'


printf '\n第一批跑完，出/ 下现在有：\n'
ls -1 "$OUT"
