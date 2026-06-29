#!/usr/bin/env python3
"""
env_setup.py - 环境自动检测与配置

首次运行时执行，后续读取 .env_status.json 直接使用已配置环境。
支持 Windows PowerShell / Git Bash / Linux / Mac。

支持交互式和非交互式两种模式：
- 交互式（默认）：询问用户输入
- 非交互式：通过命令行参数指定配置

用法：
  python env_setup.py                                    # 交互式
  python env_setup.py --non-interactive                  # 非交互式（自动选择默认值）
  python env_setup.py --env-name PDF_AIGC --use-venv     # 指定参数
"""

import os
import sys
import json
import subprocess
import shutil
import time
import argparse
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent.absolute()
STATUS_FILE = SKILL_DIR / ".env_status.json"
REQUIREMENTS = SKILL_DIR.parent.parent.parent / "requirements.txt"
MIN_PYTHON_VERSION = (3, 11)


class EnvSetup:
    def __init__(self, non_interactive: bool = False, env_name: str = None,
                 use_venv: bool = None, use_existing: bool = None):
        """
        初始化环境配置器

        Args:
            non_interactive: 是否非交互式运行
            env_name: 指定环境名称（非交互式）
            use_venv: 是否使用 venv（非交互式）
            use_existing: 是否使用已存在的环境（非交互式）
        """
        self.platform = sys.platform  # win32, linux, darwin
        self.status = self.load_status()
        self.non_interactive = non_interactive
        self.env_name = env_name
        self.use_venv = use_venv
        self.use_existing = use_existing

    def load_status(self) -> dict:
        """加载环境状态文件"""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_status(self, data: dict):
        """保存环境状态"""
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def check_ready(self) -> bool:
        """检查环境是否已配置完成"""
        return self.status.get("status") == "ready"

    def run_command(self, cmd: str, shell: bool = True, timeout: int = 300) -> Tuple[int, str, str]:
        """执行系统命令并返回 (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except Exception as e:
            return -1, "", str(e)

    def check_conda(self) -> Optional[str]:
        """检测 conda 是否可用，返回 conda 路径或 None"""
        code, out, _ = self.run_command("conda --version")
        if code == 0:
            # 获取 conda 完整路径
            if self.platform == "win32":
                code, path, _ = self.run_command("where conda")
            else:
                code, path, _ = self.run_command("which conda")

            if code == 0 and path.strip():
                return path.strip().split('\n')[0]
            return "conda"

        # 检查常见安装路径
        common_paths = [
            "/opt/conda/bin/conda",
            Path.home() / "miniconda3" / "bin" / "conda",
            Path.home() / "anaconda3" / "bin" / "conda",
            Path("/d/Software/Miniconda/Scripts/conda.exe"),
            Path("C:/ProgramData/Miniconda3/Scripts/conda.exe"),
        ]

        for path in common_paths:
            if Path(path).exists():
                return str(path)

        return None

    def check_python(self) -> Optional[Tuple[str, Tuple[int, int, int]]]:
        """检测 python 并返回 (路径, 版本元组) 或 None"""
        for cmd in ["python", "python3", "python3.11", "python3.12"]:
            code, out, _ = self.run_command(f"{cmd} --version")
            if code == 0 and out.strip():
                try:
                    # 解析版本: "Python 3.11.5"
                    version_str = out.strip().split()[1]
                    version = tuple(map(int, version_str.split('.')[:3]))
                    return cmd, version
                except (IndexError, ValueError):
                    continue
        return None

    def ask_user(self, prompt: str, default: str = "") -> str:
        """询问用户输入（带默认值），支持非交互式模式"""
        if self.non_interactive:
            # 非交互式模式：直接返回默认值
            print(f"{prompt} [使用默认值: {default}]")
            return default

        # 交互式模式：等待用户输入
        if default:
            answer = input(f"{prompt} [{default}]: ").strip()
        else:
            answer = input(f"{prompt}: ").strip()
        return answer if answer else default

    def create_conda_env(self, env_name: str) -> bool:
        """创建 conda 环境"""
        print(f"\n正在创建 conda 环境: {env_name}")
        print("这可能需要几分钟...")

        code, out, err = self.run_command(f"conda create -n {env_name} python=3.11 -y", timeout=600)
        if code != 0:
            print(f"\nERROR: conda 环境创建失败")
            print(f"错误信息: {err}")
            return False

        print(f"✓ conda 环境 {env_name} 创建成功")
        return True

    def install_dependencies(self, env_type: str, env_name: str = None) -> bool:
        """安装项目依赖"""
        print("\n正在安装依赖（spacy, numpy, pandas 等）...")
        print("这可能需要几分钟...")

        if not REQUIREMENTS.exists():
            print(f"WARNING: requirements.txt 未找到，路径: {REQUIREMENTS}")
            print("跳过依赖安装")
            return True

        if env_type == "conda":
            cmd = f"conda run -n {env_name} pip install -r {REQUIREMENTS}"
        elif env_type == "venv":
            if self.platform == "win32":
                activate = f"{SKILL_DIR}\\.venv_paper_detection\\Scripts\\activate.bat &&"
            else:
                activate = f"source {SKILL_DIR}/.venv_paper_detection/bin/activate &&"
            cmd = f"{activate} pip install -r {REQUIREMENTS}"
        else:  # global
            cmd = f"pip install -r {REQUIREMENTS}"

        # 尝试默认源
        code, out, err = self.run_command(cmd, timeout=600)
        if code != 0:
            # 失败则尝试清华镜像
            print("\n默认源安装失败，尝试使用清华镜像...")
            cmd_mirror = cmd.replace("pip install", "pip install -i https://pypi.tuna.tsinghua.edu.cn/simple")
            code, out, err = self.run_command(cmd_mirror, timeout=600)
            if code != 0:
                print(f"\nERROR: 依赖安装失败")
                print(f"错误信息: {err}")
                print("\n请手动安装依赖:")
                print(f"  pip install -r {REQUIREMENTS}")
                return False

        print("✓ 依赖安装成功")
        return True

    def download_spacy_model(self, env_type: str, env_name: str = None) -> bool:
        """下载 spacy 模型，带重试机制"""
        print("\n正在下载 spacy 模型 en_core_web_sm (~450 MB)...")
        print("这可能需要几分钟，请耐心等待...")

        if env_type == "conda":
            cmd = f"conda run -n {env_name} python -m spacy download en_core_web_sm"
        elif env_type == "venv":
            if self.platform == "win32":
                activate = f"{SKILL_DIR}\\.venv_paper_detection\\Scripts\\activate.bat &&"
            else:
                activate = f"source {SKILL_DIR}/.venv_paper_detection/bin/activate &&"
            cmd = f"{activate} python -m spacy download en_core_web_sm"
        else:  # global
            cmd = "python -m spacy download en_core_web_sm"

        for attempt in range(3):
            if attempt > 0:
                print(f"\n重试第 {attempt + 1} 次...")
                time.sleep(2 ** attempt)  # 指数退避：2s, 4s, 8s

            code, out, err = self.run_command(cmd, timeout=600)
            if code == 0:
                print("✓ spacy 模型下载成功")
                return True

            print(f"下载失败（尝试 {attempt + 1}/3）")
            if "disk" in err.lower() or "space" in err.lower():
                print("\nERROR: 磁盘空间不足，请清理后重试")
                return False

        # 三次失败后提供离线安装指南
        print("\n" + "="*60)
        print("网络下载失败，请尝试离线安装：")
        print("="*60)
        print("1. 访问 https://github.com/explosion/spacy-models/releases")
        print("2. 下载 en_core_web_sm-3.7.0.tar.gz（或最新版本）")
        print("3. 手动安装:")
        if env_type == "conda":
            print(f"   conda run -n {env_name} pip install /path/to/en_core_web_sm-3.7.0.tar.gz")
        elif env_type == "venv":
            print(f"   {SKILL_DIR}/.venv_paper_detection/bin/pip install /path/to/en_core_web_sm-3.7.0.tar.gz")
        else:
            print("   pip install /path/to/en_core_web_sm-3.7.0.tar.gz")
        print("="*60)
        return False

    def get_venv_activate_cmd(self) -> str:
        """获取 venv 激活命令（跨平台）"""
        venv_dir = SKILL_DIR / ".venv_paper_detection"
        if self.platform == "win32":
            return f"{venv_dir}\\Scripts\\activate"
        else:
            return f"source {venv_dir}/bin/activate"

    def setup(self) -> bool:
        """主配置流程"""
        print("\n" + "="*60)
        print("Paper Detection Skill - 环境自动配置")
        if self.non_interactive:
            print("（非交互式模式）")
        print("="*60)

        # 1. 检查状态文件
        if self.check_ready():
            print("\n✓ 环境已配置完成，直接使用")
            print(f"环境类型: {self.status.get('env_type')}")
            if self.status.get('env_name'):
                print(f"环境名称: {self.status.get('env_name')}")
            return True

        print("\n首次运行，开始检测环境...\n")

        # 2. 检测 Conda
        conda_path = self.check_conda()
        if conda_path:
            print(f"✓ 检测到 Conda: {conda_path}")

            # 获取环境名称（优先使用参数，否则询问或使用默认值）
            if self.env_name:
                env_name = self.env_name
                print(f"使用指定环境名称: {env_name}")
            else:
                env_name = self.ask_user("\n请输入虚拟环境名称", "PDF_AIGC")

            # 检查环境是否已存在
            code, out, _ = self.run_command("conda env list")
            if code == 0 and env_name in out:
                # 优先使用参数，否则询问或使用默认值
                if self.use_existing is not None:
                    use_existing_env = self.use_existing
                    print(f"\n环境 {env_name} 已存在，{'使用现有环境' if use_existing_env else '创建新环境'}")
                else:
                    use_existing_input = self.ask_user(f"\n环境 {env_name} 已存在，是否使用现有环境？(y/n)", "y")
                    use_existing_env = use_existing_input.lower() == 'y'

                if use_existing_env:
                    print(f"使用现有环境: {env_name}")
                else:
                    env_name = self.ask_user("请输入新的环境名称", f"{env_name}_new")
                    if not self.create_conda_env(env_name):
                        return False
            else:
                if not self.create_conda_env(env_name):
                    return False

            if not self.install_dependencies("conda", env_name):
                return False
            if not self.download_spacy_model("conda", env_name):
                print("\nWARNING: spacy 模型下载失败，请稍后手动安装")
                print("环境配置已完成，但运行检测脚本前需要先安装模型")

            self.save_status({
                "status": "ready",
                "env_type": "conda",
                "env_name": env_name,
                "env_path": conda_path,
                "python_version": "3.11+",
                "created_at": datetime.now().isoformat()
            })
            print("\n" + "="*60)
            print("✓✓✓ 环境配置完成！")
            print("="*60)
            return True

        # 3. 无 Conda，检测 Python
        print("未检测到 Conda，检查 Python 环境...")
        python_info = self.check_python()

        if python_info:
            python_cmd, version = python_info
            print(f"✓ 检测到 Python: {python_cmd} {'.'.join(map(str, version))}")

            if version < MIN_PYTHON_VERSION:
                print(f"\nWARNING: 当前 Python 版本 {'.'.join(map(str, version))} < 3.11")
                if self.non_interactive:
                    print("\nERROR: Python 版本不满足要求（需要 >= 3.11），无法继续")
                    self.show_upgrade_guide()
                    return False
                else:
                    upgrade = self.ask_user("是否需要升级 Python？(y/n)", "n")
                    if upgrade.lower() != 'y':
                        print("\nERROR: Python 版本不满足要求（需要 >= 3.11），无法继续")
                        self.show_upgrade_guide()
                        return False
                    else:
                        self.show_upgrade_guide()
                        print("\n请升级 Python 后重新运行本脚本")
                        return False

            # 版本满足，决定是否创建 venv
            if self.use_venv is not None:
                create_venv = self.use_venv
                print(f"\n{'创建' if create_venv else '不创建'}虚拟环境")
            else:
                use_venv_input = self.ask_user("\n检测到符合要求的 Python，是否创建虚拟环境？(y/n)", "y")
                create_venv = use_venv_input.lower() == 'y'

            if create_venv:
                venv_dir = SKILL_DIR / ".venv_paper_detection"
                print(f"\n正在创建虚拟环境: {venv_dir}")

                code, out, err = self.run_command(f"{python_cmd} -m venv {venv_dir}")
                if code != 0:
                    print(f"\nERROR: venv 创建失败")
                    print(f"错误信息: {err}")
                    return False

                print("✓ 虚拟环境创建成功")

                if not self.install_dependencies("venv"):
                    return False
                if not self.download_spacy_model("venv"):
                    print("\nWARNING: spacy 模型下载失败，请稍后手动安装")

                self.save_status({
                    "status": "ready",
                    "env_type": "venv",
                    "env_path": str(venv_dir),
                    "python_version": '.'.join(map(str, version)),
                    "created_at": datetime.now().isoformat()
                })
                print("\n" + "="*60)
                print("✓✓✓ 环境配置完成！")
                print("="*60)
                return True
            else:
                # 使用全局 Python
                print("\n使用全局 Python 环境")
                if not self.install_dependencies("global"):
                    return False
                if not self.download_spacy_model("global"):
                    print("\nWARNING: spacy 模型下载失败，请稍后手动安装")

                self.save_status({
                    "status": "ready",
                    "env_type": "global",
                    "env_path": python_cmd,
                    "python_version": '.'.join(map(str, version)),
                    "created_at": datetime.now().isoformat()
                })
                print("\n" + "="*60)
                print("✓✓✓ 环境配置完成！")
                print("="*60)
                return True

        # 4. 既无 Conda 也无 Python
        print("\nERROR: 未检测到 Python 环境")
        self.show_install_guide()
        return False

    def show_upgrade_guide(self):
        """显示 Python 升级指南"""
        print("\n" + "="*60)
        print("Python 升级指南")
        print("="*60)
        if self.platform == "win32":
            print("Windows: 访问 https://www.python.org/downloads/")
            print("         下载 Python 3.11 或更高版本安装包")
        elif self.platform == "darwin":
            print("Mac: brew upgrade python")
            print("     或访问 https://www.python.org/downloads/")
        else:
            print("Linux: sudo apt-get install python3.11")
            print("       或 sudo yum install python3.11")
        print("="*60)

    def show_install_guide(self):
        """显示 Python 安装指南"""
        print("\n" + "="*60)
        print("Python 安装指南")
        print("="*60)
        if self.platform == "win32":
            print("Windows: 访问 https://www.python.org/downloads/")
            print("         下载 Python 3.11 或更高版本安装包")
        elif self.platform == "darwin":
            print("Mac: brew install python@3.11")
            print("     或访问 https://www.python.org/downloads/")
        else:
            print("Linux: sudo apt-get install python3.11")
            print("       或 sudo yum install python3.11")
        print("\n安装完成后请重新运行本脚本")
        print("="*60)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Paper Detection Skill - 环境自动配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python env_setup.py                                      # 交互式模式
  python env_setup.py --non-interactive                    # 非交互式（所有默认值）
  python env_setup.py --env-name MyEnv --use-venv          # 指定环境名和使用 venv
  python env_setup.py --non-interactive --use-existing     # 非交互式且使用已存在环境
        """
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='非交互式模式，自动使用默认值'
    )
    parser.add_argument(
        '--env-name',
        type=str,
        default=None,
        help='指定虚拟环境名称（默认: PDF_AIGC）'
    )
    parser.add_argument(
        '--use-venv',
        action='store_true',
        default=None,
        help='使用 Python venv（而非 conda 或全局环境）'
    )
    parser.add_argument(
        '--no-venv',
        action='store_true',
        help='不使用 venv，使用全局 Python 环境'
    )
    parser.add_argument(
        '--use-existing',
        action='store_true',
        default=None,
        help='如果环境已存在则使用现有环境'
    )
    parser.add_argument(
        '--no-existing',
        action='store_true',
        help='如果环境已存在则创建新环境'
    )

    args = parser.parse_args()

    # 处理互斥参数
    use_venv = None
    if args.use_venv:
        use_venv = True
    elif args.no_venv:
        use_venv = False

    use_existing = None
    if args.use_existing:
        use_existing = True
    elif args.no_existing:
        use_existing = False

    # 创建配置器并运行
    setup = EnvSetup(
        non_interactive=args.non_interactive,
        env_name=args.env_name,
        use_venv=use_venv,
        use_existing=use_existing
    )
    success = setup.setup()

    if success:
        print("\n现在可以运行检测脚本了！")
        return 0
    else:
        print("\n环境配置失败，请查看上述错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
