#!/usr/bin/env bash
# run_detect.sh - 跨平台检测脚本启动器（Bash）
#
# 功能：
# 1. 首次运行时自动调用 env_setup.py 配置环境（非交互式模式）
# 2. 读取 .env_status.json 获取环境配置
# 3. 自动激活对应环境（conda/venv/global）
# 4. 执行 detect.py 并传递所有参数

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
STATUS_FILE="$SKILL_DIR/.env_status.json"

# 1. 检查环境是否已配置
if [[ ! -f "$STATUS_FILE" ]]; then
    echo "首次运行，正在配置环境（非交互式模式）..."
    python3 "$SCRIPT_DIR/env_setup.py" --non-interactive
    if [[ $? -ne 0 ]]; then
        echo "环境配置失败，退出"
        exit 1
    fi
    echo ""
fi

# 2. 读取环境配置
if ! command -v jq &> /dev/null; then
    # jq 不可用，使用 Python 解析 JSON
    ENV_TYPE=$(python3 -c "import json; print(json.load(open('$STATUS_FILE'))['env_type'])")
    ENV_NAME=$(python3 -c "import json; data=json.load(open('$STATUS_FILE')); print(data.get('env_name', ''))")
    ENV_PATH=$(python3 -c "import json; data=json.load(open('$STATUS_FILE')); print(data.get('env_path', ''))")
else
    ENV_TYPE=$(jq -r '.env_type' "$STATUS_FILE")
    ENV_NAME=$(jq -r '.env_name // empty' "$STATUS_FILE")
    ENV_PATH=$(jq -r '.env_path // empty' "$STATUS_FILE")
fi

# 3. 激活环境并运行检测
case "$ENV_TYPE" in
    conda)
        echo "激活 conda 环境: $ENV_NAME"
        # 尝试常见 conda.sh 路径
        CONDA_SH=""
        for path in "/opt/conda" "$HOME/miniconda3" "$HOME/anaconda3" "/d/Software/Miniconda" "/c/ProgramData/Miniconda3"; do
            if [[ -f "$path/etc/profile.d/conda.sh" ]]; then
                CONDA_SH="$path/etc/profile.d/conda.sh"
                break
            fi
        done

        if [[ -n "$CONDA_SH" ]]; then
            source "$CONDA_SH"
            conda activate "$ENV_NAME"
        else
            echo "WARNING: 未找到 conda.sh，尝试直接激活"
            conda activate "$ENV_NAME"
        fi
        ;;
    venv)
        echo "激活 venv 环境: $ENV_PATH"
        if [[ -f "$ENV_PATH/bin/activate" ]]; then
            source "$ENV_PATH/bin/activate"
        else
            echo "ERROR: venv 激活脚本未找到: $ENV_PATH/bin/activate"
            exit 1
        fi
        ;;
    global)
        echo "使用全局 Python 环境"
        # 无需激活
        ;;
    *)
        echo "ERROR: 未知的环境类型: $ENV_TYPE"
        exit 1
        ;;
esac

# 4. 执行检测脚本，传递所有参数
export PYTHONIOENCODING=utf-8
cd "$SCRIPT_DIR"
python detect.py "$@"
