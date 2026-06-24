# 中文论文英译工作流模板

一个**可复用**的中→英学术论文翻译工作流。完整文档请查看 [项目概览.md](./项目概览.md)。

## 快速开始

详细使用说明请参考 [项目概览.md](./项目概览.md)。

## 核心特性

- ✅ 完整的 docx → Markdown → docx 转换流程
- ✅ 保留上下标和表格格式
- ✅ 集成 AI 写作痕迹去除（humanizer）
- ✅ 集成 AI 痕迹检测（paper-detection）
- ✅ 基于输入文件名的自动命名
- ✅ 支持多论文并行处理

## 文档

- [项目概览.md](./项目概览.md) - 完整的使用说明
- [开发历程.md](./开发历程.md) - 开发过程和技术决策
- [TODO.md](./TODO.md) - 待优化项

## 环境要求

- Python 3.11+
- Miniconda
- 依赖包见 [requirements.txt](./requirements.txt)

## 同步到 GitHub（可选）

本项目已配置 `.gitignore` 保护所有包含论文内容的文件隐私。如需同步到 GitHub：

```bash
# 1. 在 GitHub 创建新仓库（不要初始化 README）
# 2. 添加远程仓库
git remote add origin https://github.com/你的用户名/仓库名.git

# 3. 推送到远程（首次推送）
git push -u origin main
```

**重要提示：** `.gitignore` 已配置忽略以下内容，确保论文隐私安全：
- `input/` - 输入的原始 docx 文件
- `temp/` - 中间产物
- `output/` - 生成的 docx 文件
- 所有 `*_translation*.md` 文件
- 所有 `*_humanize_comparison.md` 文件
- 所有 `*_ai_detection_report.md` 文件

推送前请务必确认 `git status` 中没有包含敏感文件。

## 许可

本项目仅供学术研究使用。
