# OneShot 一键安装脚本 (Windows)
# 以管理员身份运行 PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
#   .\install.ps1

$ErrorActionPreference = "Stop"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OneShot - 依赖安装脚本"              -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ═══════════════════════════════════════════
# 1. 检查 Python >= 3.14.4
# ═══════════════════════════════════════════
Write-Host "[1/4] 检查 Python..." -ForegroundColor Yellow

$pythonOk = $false
try {
    $pyVersion = (python --version 2>&1) -replace "Python ", ""
    $pyMajor = [int]($pyVersion.Split(".")[0])
    $pyMinor = [int]($pyVersion.Split(".")[1])
    $pyPatch = [int]($pyVersion.Split(".")[2])
    if ($pyMajor -gt 3 -or ($pyMajor -eq 3 -and $pyMinor -gt 14) -or ($pyMajor -eq 3 -and $pyMinor -eq 14 -and $pyPatch -ge 4)) {
        Write-Host "  Python $pyVersion 已安装" -ForegroundColor Green
        $pythonOk = $true
    } else {
        Write-Host "  Python $pyVersion 版本过低 (需要 >= 3.14.4)" -ForegroundColor Red
    }
} catch {
    Write-Host "  Python 未安装" -ForegroundColor Red
}

if (-not $pythonOk) {
    Write-Host ""
    Write-Host "  请手动安装 Python 3.14.4+:" -ForegroundColor Yellow
    Write-Host "    https://www.python.org/downloads/" -ForegroundColor White
    exit 1
}

# ═══════════════════════════════════════════
# 2. pip install
# ═══════════════════════════════════════════
Write-Host ""
Write-Host "[2/4] 安装 Python 依赖..." -ForegroundColor Yellow

$requirements = Join-Path $PSScriptRoot "oneshot" "requirements.txt"
if (-not (Test-Path $requirements)) {
    Write-Host "  错误: 找不到 $requirements" -ForegroundColor Red
    exit 1
}

pip install -r $requirements
Write-Host "  Python 依赖安装完成" -ForegroundColor Green

# ═══════════════════════════════════════════
# 3. 检查 Ruby >= 3.4 (with DevKit)
# ═══════════════════════════════════════════
Write-Host ""
Write-Host "[3/4] 检查 Ruby..." -ForegroundColor Yellow

$rubyOk = $false
try {
    $rubyVersion = (ruby --version 2>&1) -replace "ruby ", ""
    $rubyShort = $rubyVersion.Split("p")[0].Trim()
    $rbMajor = [int]($rubyShort.Split(".")[0])
    $rbMinor = [int]($rubyShort.Split(".")[1])
    if ($rbMajor -ge 3 -and $rbMinor -ge 4) {
        Write-Host "  Ruby $rubyShort 已安装" -ForegroundColor Green
        $rubyOk = $true
    } else {
        Write-Host "  Ruby $rubyShort 版本过低 (需要 >= 3.4)" -ForegroundColor Red
    }
} catch {
    Write-Host "  Ruby 未安装" -ForegroundColor Red
}

# 检查 DevKit
if ($rubyOk) {
    try {
        ridk version 2>&1 | Out-Null
        Write-Host "  DevKit 已就绪" -ForegroundColor Green
    } catch {
        Write-Host "  警告: DevKit 未检测到，Anystyle 安装可能失败" -ForegroundColor Yellow
    }
}

if (-not $rubyOk) {
    Write-Host ""
    Write-Host "  请手动安装 Ruby+DevKit:" -ForegroundColor Yellow
    Write-Host "    1. 打开 https://rubyinstaller.org/downloads/" -ForegroundColor White
    Write-Host "    2. 下载 Ruby+Devkit 3.4.x (x64)" -ForegroundColor White
    Write-Host "    3. 运行安装程序，勾选 'Add Ruby to PATH'" -ForegroundColor White
    Write-Host "    4. 安装完成后重新运行此脚本" -ForegroundColor White
    exit 1
}

# ═══════════════════════════════════════════
# 4. gem install anystyle
# ═══════════════════════════════════════════
Write-Host ""
Write-Host "[4/4] 安装 Anystyle..." -ForegroundColor Yellow

gem install anystyle
Write-Host "  Anystyle 安装完成" -ForegroundColor Green

# ═══════════════════════════════════════════
# 完成
# ═══════════════════════════════════════════
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  所有依赖安装完成！"                    -ForegroundColor Green
Write-Host ""                                       -ForegroundColor Green
Write-Host "  运行方式:"                             -ForegroundColor White
Write-Host "    python -m oneshot.main"             -ForegroundColor White
Write-Host "    python -m oneshot.main --debug"     -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
