#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境配置脚本 - 自动检测并配置 Python 虚拟环境
首次运行项目时自动执行，配置完成后生成 .project_env.json 记录

支持两种模式：
1. 交互式模式（默认）：运行时询问用户配置选项
2. 非交互式模式：通过命令行参数指定配置，适用于 AI 助手自动化执行
"""

import sys
import json
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = PROJECT_DIR / ".project_env.json"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"

# 默认配置
DEFAULT_ENV_NAME = "doc_translation"
MIN_PYTHON_VERSION = (3, 11)


class EnvSetup:
    """环境配置类"""

    def __init__(self, non_interactive=False, env_type=None, env_name=None, force_recreate=False):
        """
        初始化环境配置

        Args:
            non_interactive: 是否为非交互式模式
            env_type: 环境类型 ('conda' 或 'venv')
            env_name: 环境名称（conda）或路径（venv）
            force_recreate: 是否强制重新创建环境
        """
        self.config = {}
        self.non_interactive = non_interactive
        self.env_type = env_type
        self.env_name = env_name
        self.force_recreate = force_recreate

    def check_existing_config(self):
        """检查是否已有配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                return True
            except Exception as e:
                print(f"[警告] 配置文件损坏: {e}")
                return False
        return False

    def detect_conda(self):
        """检测 Conda 是否可用"""
        try:
            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"[成功] 检测到 Conda: {version}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    def detect_python(self):
        """检测 Python 版本"""
        for cmd in ["python", "python3", "python3.11", "python3.12"]:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip().split()[1]  # "Python 3.11.5" -> "3.11.5"
                    version_parts = version_str.split('.')
                    version = (int(version_parts[0]), int(version_parts[1]))
                    return cmd, version, version_str
            except (FileNotFoundError, subprocess.TimeoutExpired, IndexError, ValueError):
                continue
        return None, None, None

    def ask_user(self, prompt, default=None):
        """询问用户输入"""
        if self.non_interactive:
            # 非交互式模式，使用默认值或预设值
            return default if default else ""

        if default:
            prompt_text = f"{prompt} [默认: {default}]: "
        else:
            prompt_text = f"{prompt}: "

        user_input = input(prompt_text).strip()
        return user_input if user_input else default

    def ask_yes_no(self, prompt, default=True):
        """询问是/否问题"""
        if self.non_interactive:
            # 非交互式模式，使用默认值
            return default

        default_str = "Y/n" if default else "y/N"
        user_input = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not user_input:
            return default
        return user_input in ['y', 'yes', '是']

    def setup_conda_env(self):
        """配置 Conda 虚拟环境"""
        print("\n=== 使用 Conda 配置虚拟环境 ===")

        # 获取环境名称
        if self.non_interactive and self.env_name:
            env_name = self.env_name
            print(f"使用指定的环境名称: {env_name}")
        else:
            # 询问环境名称
            env_name = self.ask_user(
                "请输入虚拟环境名称",
                default=DEFAULT_ENV_NAME
            )

        # 检查环境是否已存在
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True
        )

        env_exists = False
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip().startswith(env_name + ' '):
                    env_exists = True
                    break

        if env_exists:
            if self.force_recreate:
                print(f"[执行] 删除已存在的环境 '{env_name}'")
                subprocess.run(["conda", "env", "remove", "-n", env_name, "-y"], check=False)
                env_exists = False
            else:
                print(f"[警告] 环境 '{env_name}' 已存在")
                reuse = self.ask_yes_no("是否复用该环境？", default=True)
                if not reuse:
                    if self.non_interactive:
                        print("[错误] 非交互式模式下环境已存在且未指定 --force-recreate，退出")
                        return False
                    env_name = self.ask_user("请输入新的环境名称")
                    env_exists = False

        # 创建环境
        if not env_exists:
            print(f"\n[执行] 创建 Conda 环境: {env_name}")
            result = subprocess.run(
                ["conda", "create", "-n", env_name, "python=3.11", "-y"],
                check=False
            )
            if result.returncode != 0:
                print("[失败] 创建环境失败")
                return False

        # 安装依赖
        print(f"\n[执行] 安装依赖到环境: {env_name}")

        # Windows 和 Linux/Mac 的激活命令不同
        if sys.platform == "win32":
            pip_cmd = f"conda run -n {env_name} pip install -r {REQUIREMENTS_FILE}"
        else:
            pip_cmd = f"conda run -n {env_name} pip install -r {REQUIREMENTS_FILE}"

        result = subprocess.run(pip_cmd, shell=True, check=False)
        if result.returncode != 0:
            print("[失败] 安装依赖失败")
            return False

        # 保存配置
        self.config = {
            "env_type": "conda",
            "env_name": env_name,
            "python_version": "3.11",
            "created_at": datetime.now().isoformat(),
            "requirements_installed": True
        }
        self.save_config()

        print(f"\n[成功] 环境配置完成！")
        print(f"   环境名称: {env_name}")
        print(f"   激活命令: conda activate {env_name}")
        return True

    def setup_venv(self, python_cmd):
        """配置 venv 虚拟环境"""
        print("\n=== 使用 venv 配置虚拟环境 ===")

        # 获取环境路径
        if self.non_interactive and self.env_name:
            venv_path = PROJECT_DIR / self.env_name
            print(f"使用指定的环境路径: {venv_path}")
        else:
            venv_path = PROJECT_DIR / ".venv_paper_detection"

        # 检查是否已存在
        if venv_path.exists():
            if self.force_recreate:
                print(f"[执行] 删除已存在的环境: {venv_path}")
                shutil.rmtree(venv_path)
            else:
                print(f"[警告] 虚拟环境目录已存在: {venv_path}")
                reuse = self.ask_yes_no("是否复用该环境？", default=True)
                if not reuse:
                    if self.non_interactive:
                        print("[错误] 非交互式模式下环境已存在且未指定 --force-recreate，退出")
                        return False
                    print("请手动删除旧环境后重新运行此脚本")
                    return False
        else:
            # 创建 venv
            print(f"\n[执行] 创建 venv 环境: {venv_path}")
            result = subprocess.run(
                [python_cmd, "-m", "venv", str(venv_path)],
                check=False
            )
            if result.returncode != 0:
                print("[失败] 创建环境失败")
                return False

        # 获取 pip 路径
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip.exe"
            activate_cmd = f".\\{venv_path}\\Scripts\\Activate.ps1"
        else:
            pip_path = venv_path / "bin" / "pip"
            activate_cmd = f"source {venv_path}/bin/activate"

        # 安装依赖
        print(f"\n[执行] 安装依赖")
        result = subprocess.run(
            [str(pip_path), "install", "-r", str(REQUIREMENTS_FILE)],
            check=False
        )
        if result.returncode != 0:
            print("[失败] 安装依赖失败")
            return False

        # 保存配置
        self.config = {
            "env_type": "venv",
            "env_path": str(venv_path),
            "python_version": sys.version.split()[0],
            "created_at": datetime.now().isoformat(),
            "requirements_installed": True
        }
        self.save_config()

        print(f"\n[成功] 环境配置完成！")
        print(f"   环境路径: {venv_path}")
        print(f"   激活命令: {activate_cmd}")
        return True

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"\n[保存] 配置已保存到: {CONFIG_FILE}")
        except Exception as e:
            print(f"[失败] 保存配置失败: {e}")

    def run(self):
        """运行环境配置流程"""
        print("=" * 60)
        print("中文论文英译工作流 - 环境配置")
        print("=" * 60)

        # 检查是否已配置
        if self.check_existing_config() and not self.force_recreate:
            print("\n[检测] 检测到已有配置:")
            print(f"   环境类型: {self.config.get('env_type')}")
            if self.config.get('env_type') == 'conda':
                print(f"   环境名称: {self.config.get('env_name')}")
            else:
                print(f"   环境路径: {self.config.get('env_path')}")
            print(f"   配置时间: {self.config.get('created_at')}")

            if self.non_interactive:
                print("\n非交互式模式：使用现有配置，退出。")
                return True

            reconfigure = self.ask_yes_no("\n是否重新配置环境？", default=False)
            if not reconfigure:
                print("\n使用现有配置，退出。")
                return True

        # 如果指定了环境类型，直接使用
        if self.non_interactive and self.env_type:
            if self.env_type == "conda":
                has_conda = self.detect_conda()
                if not has_conda:
                    print("[错误] 指定使用 Conda 但未检测到 Conda")
                    return False
                return self.setup_conda_env()
            elif self.env_type == "venv":
                python_cmd, python_version, version_str = self.detect_python()
                if not python_cmd:
                    print("[错误] 未检测到 Python")
                    return False
                if python_version < MIN_PYTHON_VERSION:
                    print(f"[错误] Python 版本 {version_str} 低于最低要求 3.11")
                    return False
                return self.setup_venv(python_cmd)
            else:
                print(f"[错误] 未知的环境类型: {self.env_type}")
                return False

        # 交互式模式：自动检测
        # 检测 Conda
        has_conda = self.detect_conda()

        if has_conda:
            # 场景 1: 有 Conda
            if self.setup_conda_env():
                return True
            else:
                print("\n配置失败，请检查错误信息后重试。")
                return False

        # 检测 Python
        python_cmd, python_version, version_str = self.detect_python()

        if not python_cmd:
            # 场景 4: 无 Python
            print("\n[失败] 未检测到 Python")
            print("\n请先安装 Python 3.11 或更高版本：")
            print("   - Windows: https://www.python.org/downloads/")
            print("   - Linux: sudo apt install python3.11")
            print("   - Mac: brew install python@3.11")
            return False

        print(f"[成功] 检测到 Python: {version_str} (命令: {python_cmd})")

        # 检查版本
        if python_version < MIN_PYTHON_VERSION:
            # 场景 3: Python < 3.11
            print(f"\n[警告] 当前 Python 版本 {version_str} 低于最低要求 3.11")
            upgrade = self.ask_yes_no("是否希望升级 Python？", default=False)

            if upgrade:
                print("\nPython 升级指南：")
                print("   - Windows: 访问 https://www.python.org/downloads/ 下载最新版本")
                print("   - Linux: sudo apt install python3.11")
                print("   - Mac: brew install python@3.11")
                print("\n升级完成后，请重新运行此脚本。")
            else:
                print("\n提示: 本项目需要 Python 3.11+，请升级后继续。")

            return False

        # 场景 2: 无 Conda 但有 Python 3.11+
        print("\n未检测到 Conda，将使用 venv 创建虚拟环境")
        create_venv = self.ask_yes_no("是否创建 venv 虚拟环境？", default=True)

        if create_venv:
            return self.setup_venv(python_cmd)
        else:
            print("\n取消配置。")
            return False


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="中文论文英译工作流 - 环境配置脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 交互式模式（默认）
  python setup_env.py

  # 非交互式模式 - 使用 Conda
  python setup_env.py --non-interactive --env-type conda --env-name doc_translation

  # 非交互式模式 - 使用 venv
  python setup_env.py --non-interactive --env-type venv --env-name .venv_paper_detection

  # 强制重新创建环境
  python setup_env.py --non-interactive --env-type conda --env-name doc_translation --force-recreate
        """
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="非交互式模式，使用命令行参数指定配置（适用于 AI 助手自动化执行）"
    )

    parser.add_argument(
        "--env-type",
        choices=["conda", "venv"],
        help="环境类型：conda 或 venv"
    )

    parser.add_argument(
        "--env-name",
        help="环境名称（conda）或路径（venv），默认：conda 使用 'doc_translation'，venv 使用 '.venv_paper_detection'"
    )

    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="强制重新创建环境（即使已存在）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 创建配置对象
    setup = EnvSetup(
        non_interactive=args.non_interactive,
        env_type=args.env_type,
        env_name=args.env_name,
        force_recreate=args.force_recreate
    )

    # 运行配置流程
    success = setup.run()

    if success:
        print("\n" + "=" * 60)
        print("[成功] 环境配置成功！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 激活虚拟环境")
        if setup.config.get('env_type') == 'conda':
            print(f"   conda activate {setup.config.get('env_name')}")
        else:
            if sys.platform == "win32":
                print(f"   .\\{setup.config.get('env_path')}\\Scripts\\Activate.ps1")
            else:
                print(f"   source {setup.config.get('env_path')}/bin/activate")

        print("\n2. 开始翻译工作流")
        print("   python extract_text.py input/你的论文.docx")

        print("\n3. 使用 /paper-detection skill 时")
        print("   首次运行会询问环境选择，请选择上面创建的虚拟环境")
        print("   skill 会自动安装其所需的额外依赖 (spacy, numpy, pandas 等)")
    else:
        print("\n" + "=" * 60)
        print("[失败] 环境配置未完成")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
