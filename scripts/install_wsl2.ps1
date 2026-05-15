# WSL2 Ubuntu-22.04 安装脚本
# 如果自动安装失败，请使用此脚本

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WSL2 Ubuntu-22.04 安装助手" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 WSL 是否启用
Write-Host "[1/4] 检查 WSL 状态..." -ForegroundColor Yellow
$wslFeature = Get-WindowsOptionalFeature -Online | Where-Object { $_.FeatureName -eq "Microsoft-Windows-Subsystem-Linux" }
$vmFeature = Get-WindowsOptionalFeature -Online | Where-Object { $_.FeatureName -eq "VirtualMachinePlatform" }

if ($wslFeature.State -ne "Enabled" -or $vmFeature.State -ne "Enabled") {
    Write-Host "[警告] WSL 功能未完全启用" -ForegroundColor Red
    Write-Host "请以管理员身份运行以下命令：" -ForegroundColor Yellow
    Write-Host "  dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart" -ForegroundColor White
    Write-Host "  dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart" -ForegroundColor White
    Write-Host "然后重启电脑" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] WSL 功能已启用" -ForegroundColor Green

# 设置 WSL2 为默认版本
Write-Host ""
Write-Host "[2/4] 设置 WSL2 为默认版本..." -ForegroundColor Yellow
wsl --set-default-version 2
Write-Host "[OK] WSL2 已设为默认版本" -ForegroundColor Green

# 提供安装选项
Write-Host ""
Write-Host "[3/4] 选择安装方式：" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Microsoft Store 安装（推荐，最简单）" -ForegroundColor White
Write-Host "  2. 手动下载安装包" -ForegroundColor White
Write-Host "  3. 稍后手动安装" -ForegroundColor White
Write-Host ""

$choice = Read-Host "请输入选项 (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "正在打开 Microsoft Store..." -ForegroundColor Cyan
        Start-Process "ms-windows-store://pdp/?ProductId=9PN20MSR04DW"
        Write-Host ""
        Write-Host "请在 Microsoft Store 中点击'获取'安装 Ubuntu 22.04" -ForegroundColor Yellow
        Write-Host "安装完成后，请启动 Ubuntu 22.04 并设置用户名和密码" -ForegroundColor Yellow
    }
    "2" {
        Write-Host ""
        Write-Host "手动安装步骤：" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "1. 使用浏览器下载 Ubuntu 22.04：" -ForegroundColor White
        Write-Host "   https://aka.ms/wslubuntu2204" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "2. 下载完成后，在 PowerShell 中运行：" -ForegroundColor White
        Write-Host "   Add-AppxPackage <下载的文件路径>" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "3. 启动 Ubuntu 22.04 并设置用户名密码" -ForegroundColor White
        Write-Host ""
        
        $download = Read-Host "是否现在打开下载链接？(y/n)"
        if ($download -eq "y") {
            Start-Process "https://aka.ms/wslubuntu2204"
        }
    }
    "3" {
        Write-Host ""
        Write-Host "稍后请手动安装 Ubuntu 22.04" -ForegroundColor Yellow
        Write-Host "安装完成后，重新运行此脚本或执行：wsl -l -v" -ForegroundColor Yellow
    }
    default {
        Write-Host "无效选项" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[4/4] 验证安装..." -ForegroundColor Yellow
Write-Host "安装完成后，请运行以下命令验证：" -ForegroundColor Yellow
Write-Host "  wsl -l -v" -ForegroundColor Cyan
Write-Host ""
Write-Host "预期输出：" -ForegroundColor Yellow
Write-Host "  NAME            STATE           VERSION" -ForegroundColor White
Write-Host "  Ubuntu-22.04    Running         2" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装助手完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
