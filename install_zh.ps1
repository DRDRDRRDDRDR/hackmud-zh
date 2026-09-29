# hackmud 简体中文汉化补丁 — 安装 / 回滚 / 校验 脚本
# 用法(右键"使用 PowerShell 运行",或):
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 install
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 rollback
#   powershell -ExecutionPolicy Bypass -File install_zh.ps1 verify
# 参数: install | rollback | verify (缺省 install)，可选 -GameData <数据目录>
#
# 说明：哈希常量 __HASH_n__ / __ORIG_n__ 由 build_release.py 在打包时按实际载荷回填，
#       不要手改。补丁清单是表格驱动的，新增文件只需往 $Files 里加一行。

param(
    [ValidateSet("install", "rollback", "verify")]
    [string]$Action = "install",
    [string]$GameData = "C:\Program Files (x86)\Steam\steamapps\common\hackmud\hackmud_win_Data"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 补丁清单：相对路径 / 补丁版期望哈希 / 原版哈希
$Files = @(
    @{ Rel = "Managed\Core.dll";     Patch = "04523E88269020BF92A20A05F132BB3FEF6C19F12D6AAE8855BC3437FA4FBF52";  Orig = "D424EAB9372946946B5FFD9DC49B17D9C5060B3CEC638A5952E7EAD99CD696E6" },
    @{ Rel = "resources.assets";     Patch = "5B2345F938D02A4289A76518D3DEA8B604CD3EAEDDE870C3BAE8958CDAB2C6D7";  Orig = "E2E661C96397F9C444936B9767F7F723B5FDAF64FC4ECB04B52E7D5B678C0003" },
    @{ Rel = "sharedassets0.assets"; Patch = "436939FD6091DB230F84E0632DBD6AF6D231A9A81C125FF74444F270EB4E221E";  Orig = "E07F027F18A41DB03E387DF729DB77D933AC1B0593826640A4E91FE6E7709D9B" },
    @{ Rel = "level0";               Patch = "0B31BD4938643F9084B47AC0E5B91E60A120BC9CC10207F45028E09F1B6FE35C";  Orig = "2D7FC2DA43E6273E8D1A2A3D2E2761869563C7C4D99DA34905E0581463B7441A" }
)

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Assert-GameStopped {
    $p = Get-Process -Name "hackmud_win" -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "!! hackmud 正在运行,请先完全退出游戏再操作" -ForegroundColor Red
        exit 1
    }
}

function Test-IsPatched {
    foreach ($f in $Files) {
        if ((Get-Sha256 (Join-Path $GameData $f.Rel)) -ne $f.Patch) { return $false }
    }
    return $true
}

function Test-IsOriginal {
    foreach ($f in $Files) {
        if ((Get-Sha256 (Join-Path $GameData $f.Rel)) -ne $f.Orig) { return $false }
    }
    return $true
}

# ---------- 安装 ----------
if ($Action -eq "install") {
    Write-Host "== hackmud 汉化补丁 安装 ==" -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $GameData)) { Write-Host "!! 找不到游戏目录: $GameData" -ForegroundColor Red; exit 1 }

    foreach ($f in $Files) {
        $src = Join-Path $ScriptDir $f.Rel
        if (-not (Test-Path -LiteralPath $src)) { Write-Host "!! 缺少补丁文件 $($f.Rel)" -ForegroundColor Red; exit 1 }
    }
    Assert-GameStopped

    if (Test-IsPatched) {
        Write-Host "已检测到汉化已安装,跳过(幂等)" -ForegroundColor Yellow
        exit 0
    }

    foreach ($f in $Files) {
        $dst = Join-Path $GameData $f.Rel
        $bak = "$dst.bak"
        if ((Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $bak)) {
            Copy-Item -LiteralPath $dst -Destination $bak -Force
            Write-Host "已备份 $($f.Rel) -> $($f.Rel).bak" -ForegroundColor DarkGray
        }
    }

    foreach ($f in $Files) {
        Copy-Item -LiteralPath (Join-Path $ScriptDir $f.Rel) -Destination (Join-Path $GameData $f.Rel) -Force
    }
    Write-Host "已复制汉化文件" -ForegroundColor Green

    $bad = 0
    foreach ($f in $Files) {
        $h = Get-Sha256 (Join-Path $GameData $f.Rel)
        if ($h -ne $f.Patch) { Write-Host "!! $($f.Rel) 校验不符: $h" -ForegroundColor Red; $bad++ }
    }
    if ($bad -eq 0) {
        Write-Host "✔ 安装校验通过。启动 hackmud 即可看到中文界面。" -ForegroundColor Green
    } else {
        Write-Host "!! 安装后有文件哈希不符! 请检查是否被其它程序改动" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# ---------- 回滚 ----------
if ($Action -eq "rollback") {
    Write-Host "== hackmud 汉化补丁 回滚 ==" -ForegroundColor Cyan
    Assert-GameStopped
    $ok = $true
    foreach ($f in $Files) {
        $dst = Join-Path $GameData $f.Rel
        $bak = "$dst.bak"
        if (-not (Test-Path -LiteralPath $bak)) {
            Write-Host "!! 找不到备份 $($f.Rel).bak,该文件无法回滚" -ForegroundColor Yellow
            $ok = $false
            continue
        }
        Copy-Item -LiteralPath $bak -Destination $dst -Force
        Write-Host "已从备份恢复 $($f.Rel)" -ForegroundColor Green
    }
    if ($ok) {
        if (Test-IsOriginal) {
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
    foreach ($f in $Files) {
        Write-Host ("{0,-24}: {1}" -f $f.Rel, (Get-Sha256 (Join-Path $GameData $f.Rel)))
    }
    if (Test-IsPatched) {
        Write-Host "✔ 状态: 已安装汉化版" -ForegroundColor Green
    } elseif (Test-IsOriginal) {
        Write-Host "✔ 状态: 原版(未安装汉化)" -ForegroundColor Gray
    } else {
        Write-Host "! 状态: 未知/混合(可能被其他补丁改动,或只装了部分文件)" -ForegroundColor Yellow
    }
    exit 0
}
