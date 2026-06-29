# run_detect.ps1 - Windows PowerShell 启动器
#
# 功能：
# 1. 首次运行时自动调用 env_setup.py 配置环境（非交互式模式）
# 2. 读取 .env_status.json 获取环境配置
# 3. 自动激活对应环境（conda/venv/global）
# 4. 执行 detect.py 并传递所有参数

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$StatusFile = Join-Path $SkillDir ".env_status.json"

# 1. 检查环境是否已配置
if (-not (Test-Path $StatusFile)) {
    Write-Host "首次运行，正在配置环境（非交互式模式）..."
    python "$ScriptDir\env_setup.py" --non-interactive
    if ($LASTEXITCODE -ne 0) {
        Write-Error "环境配置失败，退出"
        exit 1
    }
    Write-Host ""
}

# 2. 读取环境配置
$Config = Get-Content $StatusFile | ConvertFrom-Json
$EnvType = $Config.env_type
$EnvName = $Config.env_name
$EnvPath = $Config.env_path

# 3. 激活环境并运行检测
switch ($EnvType) {
    "conda" {
        Write-Host "激活 conda 环境: $EnvName"
        conda activate $EnvName
        if ($LASTEXITCODE -ne 0) {
            Write-Error "conda 环境激活失败"
            exit 1
        }
    }
    "venv" {
        Write-Host "激活 venv 环境: $EnvPath"
        $ActivateScript = Join-Path $EnvPath "Scripts\Activate.ps1"
        if (Test-Path $ActivateScript) {
            & $ActivateScript
        } else {
            Write-Error "venv 激活脚本未找到: $ActivateScript"
            exit 1
        }
    }
    "global" {
        Write-Host "使用全局 Python 环境"
        # 无需激活
    }
    default {
        Write-Error "未知的环境类型: $EnvType"
        exit 1
    }
}

# 4. 执行检测脚本，传递所有参数
$env:PYTHONIOENCODING = "utf-8"
Set-Location $ScriptDir
python detect.py @args
