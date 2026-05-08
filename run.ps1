# OneShot 启动脚本
# 双击此脚本即可运行

$ErrorActionPreference = "Stop"

# 获取脚本所在目录（项目根目录）
$ProjectRoot = $PSScriptRoot

# 激活虚拟环境
& "$ProjectRoot\venv\Scripts\Activate.ps1"

# 检查是否需要构建前端
$FrontendDist = Join-Path $ProjectRoot "frontend\dist"
$IndexHtml = Join-Path $FrontendDist "index.html"

if (-not (Test-Path $IndexHtml)) {
    Write-Host "[OneShot] 前端未构建，正在构建..." -ForegroundColor Yellow
    
    Push-Location (Join-Path $ProjectRoot "frontend")
    npm install
    npm run build
    Pop-Location
    
    Write-Host "[OneShot] 前端构建完成" -ForegroundColor Green
}

# 启动应用
python oneshot/main.py