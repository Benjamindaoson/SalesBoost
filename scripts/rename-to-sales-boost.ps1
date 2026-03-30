# SalesBoost -> sales-boost 根目录重命名脚本
# 硅谷 AI 项目标准: 小写 kebab-case
# 执行前请关闭 Cursor/IDE，执行后重新打开 D:\sales-boost

$ErrorActionPreference = "Stop"
$oldPath = "D:\SalesBoost"
$newPath = "D:\sales-boost"

if (-not (Test-Path $oldPath)) {
    Write-Host "路径不存在: $oldPath" -ForegroundColor Red
    exit 1
}

if (Test-Path $newPath) {
    Write-Host "目标已存在: $newPath" -ForegroundColor Red
    exit 1
}

Write-Host "重命名: $oldPath -> $newPath" -ForegroundColor Yellow
Rename-Item -Path $oldPath -NewName "sales-boost"
Write-Host "完成! 请重新打开 D:\sales-boost" -ForegroundColor Green
