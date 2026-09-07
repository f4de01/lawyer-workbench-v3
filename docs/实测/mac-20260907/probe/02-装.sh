#!/bin/bash
# 第二批：装 skill 包，然后看 Codex 到底看见了什么。依据 issue #40。
# 三级兜底，一级不成自动降到下一级；最后一定要把「走的是哪条路线」记清楚：
# $ 前缀本来就随安装路线变，路线记错了，开发者那边整张入口表就是错的。

cd "$(dirname "$0")/.." || exit 2
OUT="出"
mkdir -p "$OUT"
: > "$OUT/04-安装.txt"
: > "$OUT/05-清单.txt"

REPO="f4de01/lawyer-workbench-v3"
ROUTE="未确定"

log() { printf '%s\n' "$*" >> "$OUT/04-安装.txt"; }
run() {
  local title="$1"; shift
  {
    printf '### %s\n' "$title"
    printf '$ %s\n' "$*"
    printf -- '---\n'
    "$@" 2>&1
    printf -- '\n--- 退出码 %s ---\n\n' "$?"
  } >> "$OUT/04-安装.txt"
}

# macOS 自带没有 timeout，限时一律用 perl 的 alarm

echo "先抄 CLI 自己的帮助，不猜参数"
run "skills CLI 帮助"  bash -c 'npx --yes skills@latest --help 2>&1 < /dev/null'
run "skills add 帮助"  bash -c 'npx --yes skills@latest add --help 2>&1 < /dev/null'

echo
echo "第 1 级：网络装（私有仓库，可能因为凭据装不上）"
run "npx skills add（180 秒上限，非交互）" bash -c "perl -e 'alarm 180; exec @ARGV' npx --yes skills@latest add $REPO -a codex < /dev/null 2>&1"

装上了() { ls ~/.agents/skills/loo0ng-doit >/dev/null 2>&1 || ls ~/.agents/skills/*/loo0ng-doit >/dev/null 2>&1; }

if 装上了; then
  ROUTE="1-skills.sh 网络装"
  log "==> 第 1 级成功，路线：$ROUTE"
else
  log "==> 第 1 级没成（上面有原因）。降到第 2 级。"

  echo
  echo "第 2 级：本机 gh 已登录的话，克隆下来再从本地装"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    run "gh clone 到包内 临时仓库/" bash -c "perl -e 'alarm 300; exec @ARGV' gh repo clone $REPO 临时仓库 -- --depth 1 2>&1"
    if [ -d "临时仓库/skills" ]; then
      run "从本地目录装" bash -c "perl -e 'alarm 180; exec @ARGV' npx --yes skills@latest add ./临时仓库 -a codex < /dev/null 2>&1"
      if 装上了; then
        ROUTE="2-gh clone 后本地装"
        log "==> 第 2 级成功，路线：$ROUTE"
      fi
    fi
  else
    log "==> 本机 gh 没装或没登录，第 2 级跳过。不要去弄令牌，直接降到第 3 级。"
  fi
fi

if ! 装上了; then
  log "==> 降到第 3 级：直接把包里自带的 skills-兜底/ 拷进 Codex 的 skill 目录。"
  echo
  echo "第 3 级：拷目录"
  SRC="skills-兜底"
  [ -d "临时仓库/skills" ] && SRC="临时仓库/skills"
  run "拷贝到 ~/.agents/skills/" bash -c "
    mkdir -p ~/.agents/skills
    for d in $SRC/*/; do
      n=\$(basename \"\$d\")
      [ -f \"\$d/SKILL.md\" ] || continue
      rm -rf ~/.agents/skills/\"\$n\"
      cp -R \"\$d\" ~/.agents/skills/\"\$n\" && echo \"拷了 \$n\"
    done
    echo '--- ~/.agents/skills 现在有 ---'
    ls -1 ~/.agents/skills"
  if 装上了; then
    ROUTE="3-直接拷目录到 ~/.agents/skills"
    log "==> 第 3 级成功，路线：$ROUTE"
  else
    ROUTE="全都没成"
    log "==> 三级都没成。"
  fi
fi

run "装到哪了：~/.agents/skills" bash -c 'ls -1 ~/.agents/skills 2>&1 || echo 没有这个目录'
run "装到哪了：~/.codex"         bash -c 'ls -1 ~/.codex 2>&1 || echo 没有这个目录'

printf '\n\n########  走通的路线：%s  ########\n' "$ROUTE" >> "$OUT/04-安装.txt"

echo
echo "看 Codex 模型侧到底看见了什么"
run() {  # 05 用另一个文件
  local title="$1"; shift
  {
    printf '### %s\n' "$title"
    printf '$ %s\n' "$*"
    printf -- '---\n'
    "$@" 2>&1
    printf -- '\n--- 退出码 %s ---\n\n' "$?"
  } >> "$OUT/05-清单.txt"
}
run "codex debug prompt-input" bash -c "perl -e 'alarm 120; exec @ARGV' codex debug prompt-input \"hi\" 2>&1 < /dev/null"
run "七件逐个 grep（原样那一行最重要）" bash -c '
  for n in loo0ng-setup-case loo0ng-doit loo0ng-graph loo0ng-domain loo0ng-filing loo0ng-to-docx; do
    if grep -q -- "$n" "出/05-清单.txt" 2>/dev/null; then
      printf "\n%-22s 命中，原样：\n" "$n"; grep -o -- "[A-Za-z0-9_:.-]*${n}[A-Za-z0-9_:.-]*" "出/05-清单.txt" | sort -u | head -5
    else
      printf "\n%-22s 未出现\n" "$n"
    fi
  done'

printf '\n第二批跑完。路线：%s\n看 出/04-安装.txt 与 出/05-清单.txt\n' "$ROUTE"
