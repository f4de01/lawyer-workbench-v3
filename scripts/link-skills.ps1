# 开发者本机用：把仓库 skills/<name>/ 逐条以 junction 挂到两个 harness 的用户级 skill 目录。
#   ~/.claude/skills/<name>  Claude Code
#   ~/.agents/skills/<name>  Codex 及其他 Agent Skills 兼容 harness
# junction 不需要管理员权限或开发者模式；git pull 后无需重跑，改名/增删后重跑。
# 不是安装器；律师机器上的安装走插件或 skills.sh。
# 本文件须带 UTF-8 BOM：Windows PowerShell 5.1 无 BOM 时按 ANSI 读，中文注释会撕坏语法。
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
git -C $repo config core.hooksPath .githooks   # 隐私钩子（ADR-0014）：.githooks/ 里的 pre-commit 与 commit-msg
$skillsRoot = Join-Path $repo 'skills'
$dests = @((Join-Path $HOME '.claude\skills'), (Join-Path $HOME '.agents\skills'))

$srcs = Get-ChildItem -Path $skillsRoot -Recurse -Filter 'SKILL.md' -File |
  Where-Object { ($_.FullName -notlike '*\node_modules\*') -and ($_.FullName -notlike '*\deprecated\*') } |
  ForEach-Object { $_.Directory }

foreach ($dest in $dests) {
  if ((Test-Path $dest) -and ((Get-Item $dest -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    $target = (Get-Item $dest -Force).Target
    if ($target -and ($target -like "$repo*")) {
      throw "$dest 是指向本仓库的链接（$target），先删掉再重跑。"
    }
  }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  foreach ($src in $srcs) {
    $name = $src.Name
    $link = Join-Path $dest $name
    if (Test-Path $link) {
      $item = Get-Item $link -Force
      if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        $item.Delete()   # 只删链接本身，不进目标
      } else {
        Remove-Item $link -Recurse -Force
      }
    }
    New-Item -ItemType Junction -Path $link -Target $src.FullName | Out-Null
    Write-Output "linked $name -> $($src.FullName) ($dest)"
  }
}
