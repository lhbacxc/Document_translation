---
name: translation-paper-detection
version: 1.2.2
description: 检测一段学术文本（尤其是分析化学、荧光传感、抗生素/金属离子检测、纳米材料方向的英文论文）中哪些句子像 AI 生成，并给出每句 0-100% 的 AI 可能性概率以及全文综合概率。当用户想要"检测 AI 写作痕迹""判断这段话是不是 AI 写的""AI 率/AI 概率""降 AIGC 前先看哪里像 AI""逐句标注机器生成嫌疑"时，务必使用本 skill。即使用户没有明说"AI 检测"，只要意图是评估学术英文文本的机器生成可能性、找出不像人类手笔的句子，也应触发。
---
# Paper Detection — 学术文本 AI 痕迹逐句检测

本 skill 基于 **340 篇真实人类学术文献**（分析化学/荧光传感/抗生素与金属离子检测/纳米材料方向）统计出的人类写作基准，对给定英文文本**逐句**评估其"像 AI 生成"的可能性，并给出全文综合概率。

## 环境要求与自动配置（首次运行必读）

本 skill 依赖 Python 3.11+ 和科学计算库。**首次运行时会自动检测并配置环境**：

### 非交互式环境规则（分享给他人时也必须遵守）

- 本机已安装 Miniconda，但在 CLI 工具或程序等**非交互式场景**下，`conda activate` 可能无法真正切换到目标环境，而是回退到 `base`。
- 因此，**禁止**在脚本、启动器、自动化流程或 skill 执行步骤中使用 `conda activate <env>` 作为环境切换方式。
- 需要运行 Python 脚本时，**必须直接使用目标环境的 Python 绝对路径**。
- 如果当前还不知道环境名称，先向用户确认，再拼出对应的 Python 绝对路径后执行。

示例：

```bash
# Windows
D:\Software\Miniconda\envs\PDF_AIGC\python.exe detect.py --file <文件路径>

# macOS / Linux
/path/to/miniconda/envs/PDF_AIGC/bin/python detect.py --file <文件路径>
```

### 自动配置流程

1. **有 Conda**：询问虚拟环境名称（默认 PDF_AIGC），自动创建并安装依赖
2. **无 Conda 但有 Python 3.11+**：询问是否创建 venv，选择"是"则创建 `.venv_paper_detection/`
3. **Python < 3.11**：询问是否升级（不会擅自操作），拒绝则提供升级指南
4. **无 Python**：提供安装指南后退出

配置完成后会在 skill 目录生成 `.env_status.json` 记录环境信息，后续运行直接使用。

### 手动配置（高级用户）

如果你已有符合要求的环境，可创建 `.env_status.json` 跳过自动配置：

```json
{
  "status": "ready",
  "env_type": "conda",
  "env_name": "your_env_name",
  "env_path": "/path/to/conda",
  "python_version": "3.11.5",
  "created_at": "2026-06-24T10:00:00"
}
```

### 依赖清单

- spacy ≥ 3.7.0（需额外下载 en_core_web_sm 模型，~450 MB）
- textstat ≥ 0.7.3
- numpy ≥ 1.24.0
- pandas ≥ 2.0.0
- tqdm ≥ 4.66.0

---

## 核心定位（先读这一段）

这是一套**基于统计偏离的启发式信号**，不是确定性鉴定工具。它能稳定地标出"读起来不像本领域人类手笔"的句子，但**不能作为学术不端的证据**。每次给用户结果时，都要附上这一免责说明。

判别的底层逻辑：把 340 篇文献当作人类范本，统计出每个写作维度的均值与标准差。当前主流大模型生成的学术文本，在若干维度上有**系统性、可测量的偏移**——本 skill 就是测量这种偏移。

## 判别用到的关键信号

详见 `references/写作特征说明.md`，核心是：

1. **AI 套话短语**（最强句级信号）：delve into、play a crucial role、shed light on、a wide range of、underscore、pave the way、leverage、it is worth noting that … 这类短语在人类语料中几乎不出现（套话密度中位数为 0），一句话里命中即显著提升 AI 概率。
2. **句长突发度**（文档级强信号）：人类句长长短交错（突发度≈0.47），AI 倾向句长均匀（突发度<0.40）。
3. **具体性密度**：人类实验论文充满数值、单位、仪器型号、浓度、检出限（≈6.4/百词）；AI 泛泛而谈时密度骤降。
4. **句首过渡词占比**：人类克制（≈7.8%），AI 机械串接（常>15%）。
5. **被动语态不作判别**：本领域被动语态高达 45%，是方法学写作常态，绝不能因此判成 AI。

## 标准工作流程

### 第 1 步：运行检测脚本

脚本已封装全部统计逻辑，**优先直接调用**，不要自己凭语感打分（脚本结果可复现、有客观依据）。

#### 自动执行（推荐）

Skill 会自动检测环境并运行脚本，你只需提供待测文本：

```bash
# Skill 内部自动调用 scripts/run_detect.sh 或 run_detect.ps1（跨平台）
# 首次运行会自动配置环境（询问环境名称等）
# 后续运行直接使用已配置环境
```

#### 手动执行（调试场景）

如果需要手动运行：

**Conda 环境**:

```bash
cd ./skills/translation-paper-detection/scripts
<目标环境的 Python 绝对路径> detect.py --file <文件路径>
```

**Venv 环境**:

```bash
# Linux/Mac
source ./skills/translation-paper-detection/.venv_paper_detection/bin/activate

# Windows PowerShell
./skills/translation-paper-detection/.venv_paper_detection/Scripts/Activate.ps1

cd ./skills/translation-paper-detection/scripts
python detect.py --file <文件路径>
```

**命令参数**:

```bash
<目标环境的 Python 绝对路径> detect.py --file <待测文本文件>      # 推荐：长文本走文件
# 或
<目标环境的 Python 绝对路径> detect.py --text "<短文本>"
# 机器可读：加 --json
```

脚本输出：每句的 AI 概率（🔴≥70% / 🟡40-70% / 🟢<40%）+ 触发理由，以及全文综合概率和文档级信号。

### 第 2 步：解读并呈现给用户

把脚本结果整理成清晰的中文报告：

- **开头给全文综合 AI 概率**，并一句话定性（如"整体偏 AI / 偏人类 / 混合"）。
- **逐句列出概率与理由**，重点解释被标红/标黄的句子为什么可疑（引用具体触发的特征，如"连续使用 3 个 AI 套话""全段无任何实验数据"）。
- **列出文档级信号**（如句长过于均匀、句首过渡词偏多）。
- **结尾附免责说明**。

### 第 3 步（可选）：给改写建议

如果用户想进一步降低 AI 痕迹，提示可使用 **translation-paper-editing** skill 来改写，并说明改写后可再跑一次本检测对比前后概率。

## 重要原则

- **不要编造概率**：一律以脚本输出为准。若脚本因环境问题无法运行，先尝试修复环境（确认 `PDF_AIGC` 环境与 `references/corpus_stats.json` 存在），不要凭空给分。
- **解释要落到具体句子和具体特征**，而不是笼统说"这段像 AI"。用户需要知道"哪一句、为什么"。
- **诚实对待不确定性**：高具体性、被动语态规范的句子即使句式平稳，也应判为偏人类——这正是本领域真实论文的样子。反过来，再流畅的句子只要堆满套话且零具体信息，就应判高。
- 输入若是 mineru 转换的 md，脚本会自动清洗公式/图片/角标等噪声，可直接传入。

## 文件说明

- `scripts/detect.py` — 检测主程序
- `scripts/textproc.py` — 文本清洗与特征提取模块（与统计基准同源，勿改动以保持一致）
- `references/corpus_stats.json` — 340 篇人类文献的写作基准向量
- `references/写作特征说明.md` — 各判别维度的含义与人类基准数值
