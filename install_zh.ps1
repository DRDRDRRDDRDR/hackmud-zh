# hackmud 简体中文汉化补丁 — 安装 / 回滚 / 校验 脚本
# 用法(右键"使用 PowerShell 运行",或):
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 install
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 rollback
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 verify
# 参数: install | rollback | verify (缺省 install)

param(
    [ValidateSet("install", "rollback", "verify")]
    [string]$Action = "install",
    [string]$GameData = "C:\Program Files (x86)\Steam\steamapps\common\hackmud\hackmud_win_Data"
)

$ErrorActionPreference = "Stop"

# --- 路径 ---
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$PatchCore   = Join-Path $ScriptDir "Managed\Core.dll"
$PatchAssets = Join-Path $ScriptDir "resources.assets"

$GameCore   = Join-Path $GameData "Managed\Core.dll"
$GameAssets = Join-Path $GameData "resources.assets"

# 期望哈希(补丁包 SHA256SUMS.txt 内容)
$PatchCoreHash   = "04523E88269020BF92A20A05F132BB3FEF6C19F12D6AAE8855BC3437FA4FBF52"
$PatchAssetsHash = "5B2345F938D02A4289A76518D3DEA8B604CD3EAEDDE870C3BAE8958CDAB2C6D7"
# 原版哈希(用于回滚校验)
$OrigCoreHash   = "D424EAB9372946946B5FFD9DC49B17D9C5060B3CEC638A5952E7EAD99CD696E6"
$OrigAssetsHash = "E2E661C96397F9C444936B9767F7F723B5FDAF64FC4ECB04B52E7D5B678C0003"

function Get-Sha256([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

function Assert-GameStopped {
    $p = Get-Process -Name "hackmud_win" -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "!! hackmud 正在运行,请先完全退出游戏再操作" -ForegroundColor Red
        exit 1
    }
}

function Test-IsPatched {
    $h1 = Get-Sha256 $GameCore
    $h2 = Get-Sha256 $GameAssets
    return ($h1 -eq $PatchCoreHash) -and ($h2 -eq $PatchAssetsHash)
}

# ---------- 安装 ----------
if ($Action -eq "install") {
    Write-Host "== hackmud 汉化补丁 安装 ==" -ForegroundColor Cyan
    if (-not (Test-Path $GameData)) { Write-Host "!! 找不到游戏目录: $GameData" -ForegroundColor Red; exit 1 }
    if (-not (Test-Path $PatchCore)) { Write-Host "!! 缺少补丁文件 Managed\Core.dll" -ForegroundColor Red; exit 1 }
    if (-not (Test-Path $PatchAssets)) { Write-Host "!! 缺少补丁文件 resources.assets" -ForegroundColor Red; exit 1 }
    Assert-GameStopped

    if (Test-IsPatched) {
        Write-Host "已检测到汉化已安装,跳过(幂等)" -ForegroundColor Yellow
        exit 0
    }

    # 备份原文件(仅当当前不是汉化版时)
    foreach ($pair in @(@($GameCore, "$GameCore.bak"), @($GameAssets, "$GameAssets.bak"))) {
        $src = $pair[0]; $dst = $pair[1]
        if ((Test-Path $src) -and -not (Test-Path $dst)) {
            Copy-Item -Path $src -Destination $dst -Force
            Write-Host "已备份 $src -> $dst" -ForegroundColor DarkGray
        }
    }

    Copy-Item -Path $PatchCore   -Destination $GameCore   -Force
    Copy-Item -Path $PatchAssets -Destination $GameAssets -Force
    Write-Host "已复制汉化文件" -ForegroundColor Green

    # 校验
    $c = Get-Sha256 $GameCore
    $a = Get-Sha256 $GameAssets
    if ($c -eq $PatchCoreHash -and $a -eq $PatchAssetsHash) {
        Write-Host "✔ 安装校验通过。启动 hackmud 即可看到中文界面。" -ForegroundColor Green
    } else {
        Write-Host "!! 安装后哈希不符! 请检查文件是否被其他程序改动" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# ---------- 回滚 ----------
if ($Action -eq "rollback") {
    Write-Host "== hackmud 汉化补丁 回滚 ==" -ForegroundColor Cyan
    Assert-GameStopped
    $ok = $true
    foreach ($pair in @(@($GameCore, "$GameCore.bak"), @($GameAssets, "$GameAssets.bak"))) {
        $src = $pair[0]; $dst = $pair[1]
        if (-not (Test-Path $dst)) { Write-Host "!! 找不到备份 $dst,无法回滚" -ForegroundColor Red; $ok = $false; continue }
        Copy-Item -Path $dst -Destination $src -Force
        Write-Host "已从备份恢复 $src" -ForegroundColor Green
    }
    if ($ok) {
        $c = Get-Sha256 $GameCore
        $a = Get-Sha256 $GameAssets
        if ($c -eq $OrigCoreHash -and $a -eq $OrigAssetsHash) {
            Write-Host "✔ 回滚校验通过,已恢复原版" -ForegroundColor Green
        } else {
            Write-Host "!! 回滚后哈希与原版不符! 可再用 Steam 验证文件完整性恢复" -ForegroundColor Yellow
        }
    }
    exit 0
}

# ---------- 校验 ----------
if ($Action -eq "verify") {
    Write-Host "== hackmud 汉化补丁 状态校验 ==" -ForegroundColor Cyan
    $c = Get-Sha256 $GameCore
    $a = Get-Sha256 $GameAssets
    Write-Host "Core.dll        : $c"
    Write-Host "resources.assets: $a"
    if ($c -eq $PatchCoreHash -and $a -eq $PatchAssetsHash) {
        Write-Host "✔ 状态: 已安装汉化版" -ForegroundColor Green
    } elseif ($c -eq $OrigCoreHash -and $a -eq $OrigAssetsHash) {
        Write-Host "✔ 状态: 原版(未安装汉化)" -ForegroundColor Gray
    } else {
        Write-Host "! 状态: 未知/混合(可能被其他补丁改动)" -ForegroundColor Yellow
    }
    exit 0
}
