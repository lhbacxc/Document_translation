---
name: translation-paper-editing
version: 1.2.2
description: 优化/润色一段学术英文文本（尤其是分析化学、荧光传感、抗生素/金属离子检测、纳米材料方向的论文），使其更接近真实人类学术写作习惯、去除 AI 生成痕迹。当用户想要"润色论文""降低 AIGC/AI 率""去 AI 味""让这段更像人写的""improve/polish 我的论文段落""把 AI 生成的文字改自然"时，务必使用本 skill。即使用户没明说"降 AI"，只要意图是优化学术英文文本的写作质量、让行文更自然更像本领域真实论文，也应触发。
---
# Paper Editing — 学术文本人性化改写

本 skill 基于 **340 篇真实人类学术文献**（分析化学/荧光传感/抗生素与金属离子检测/纳米材料方向）统计出的人类写作基准，把给定英文文本改写得**更接近人类学术写作习惯**，从而降低"AI 生成"的痕迹。

## 核心理念（先读这一段）

"更像人写"的本质，是让文本向人类基准**回归**，而**不是堆砌辞藻**。真实的本领域论文恰恰朴素、具体、客观——大量被动语态、术语重复、平实动词、密集的实验数据。很多"AI 味"��是来自过度华丽、过度流畅、过度均匀。所以改写方向往往是做**减法**和**具体化**，而非加修辞。

**绝对底线：不得编造任何实验数据、数值、仪器型号、文献引用。** 改写只动语言形式与组织方式；凡是原文缺具体信息的地方，只能**提示作者补充**（用 `[建议补入：具体浓度/检出限/仪器型号]` 这样的占位标注），不能凭空生成数字。这是学术诚信的红线。

## 六条改写规则

基准数值与维度详解见 `references/写作特征说明.md`。

### 1. 删除 AI 套话（最重要）

人类语料几乎不出现这类短语（密度中位数为 0）。逐一清除并替换为领域内朴素表达：

| AI 套话                                         | 改为                                           |
| ----------------------------------------------- | ---------------------------------------------- |
| play a crucial/pivotal role in                  | is important for / is used in / contributes to |
| delve into                                      | investigate / examine / study                  |
| shed light on                                   | clarify / reveal / show                        |
| a wide range of                                 | various / many / several                       |
| underscore / highlight the importance           | show / indicate / demonstrate                  |
| pave the way for                                | enable / allow / facilitate                    |
| leverage                                        | use / employ / utilize                         |
| it is worth noting that                         | （多数可直接删，或 notably，）                 |
| cutting-edge / state-of-the-art                 | （删，或 recently developed）                  |
| revolutionize / transformative / groundbreaking | improve / advance / （删夸张）                 |

### 2. 制造句长起伏（突发度）

人类句长长短交错（突发度≈0.47），AI 偏均匀。改写时：把过于整齐的中长句**打破节奏**——长复杂句之后补一个短断言句（如 "This is significant."→更好是给出具体结论的短句）；或把一个堆砌的长句拆成"一长一短"。目标是让句长方差接近人类水平，而不是每句都 20–25 词。

### 3. 增加具体性（只提示，不编造）

人类实验论文具体性密度≈6.4/百词，充满数值/单位/仪器/条件。凡遇到"具有优异的灵敏度和选择性"这类空泛赞美，改写为更克制的客观陈述，并在缺数据处插入占位标注，例如：

> 原：The probe showed excellent sensitivity.
> 改：The probe showed a detection limit of `[建议补入：LOD 数值与单位]`, indicating high sensitivity.

### 4. 打散过渡词链条

人类句首过渡词占比≈7.8%，AI 常机械串接（Firstly… Moreover… Furthermore… In conclusion…）。删掉冗余过渡词，让逻辑靠内容承载；保留少量真正必要的转折（However、In contrast）。不要每段都以过渡副词开头。

### 5. 保留领域常态（不要"过度优化"）

以下是人类实验论文的**正常样子**，应当保留，不要为了"更生动"而改掉：

- **被动语态**（占比≈45%）："The spectra were recorded…""CPNPs were synthesized…" 是规范方法学写作。
- **术语重复**：同一材料/离子反复出现是正常的，不必强行用同义词替换。
- **客观平实的语气**：学术写作不需要文学性修辞。

### 6. 词汇朴素化

AI 偏好长拉丁大词（平均词长偏高）。在不损失准确性的前提下，用更常见的动词与名词替换生僻华丽词。

## 标准工作流程

1. **（推荐）先检测**：如果 `translation-paper-detection` skill 可用，先对原文跑一次，拿到逐句 AI 概率，**优先改写被标红/标黄的句子**，做到有的放矢。
   - **说明**：`translation-paper-detection` 已支持自动环境配置，首次运行会自动检测并设置 Python 环境，无需手动配置。
   - **环境规则**：如果需要手动运行 `skills/translation-paper-detection/scripts/detect.py`，不要使用 `conda activate`。在 CLI 工具、脚本和其他非交互式场景下，必须改用目标 Conda 环境的 Python 绝对路径；若环境名未确定，应先向用户确认。
2. **按六条规则改写**：以减法和具体化为主，逐句处理高嫌疑句，保留领域常态。
3. **给出对照**：呈现"原文 → 改写"对照，并简要说明每处改了什么、为什么（引用具体规则，如"删除套话 play a crucial role""拆分长句制造节奏"）。缺数据处用 `[建议补入：…]` 明确标出，提醒用户这些必须由本人填真实数据。
4. **（推荐）改写后自检**：用 `translation-paper-detection` 对改写稿再跑一次，报告 AI 概率前后变化，验证确实下降。若仍有高嫌疑句，再迭代。

## 重要原则

- **诚信第一**：宁可留占位标注，也绝不编造数据/引用。
- **改写不是越花越好**：警惕把文本改得更华丽——那会让 AI 味更重。本领域的"好"是准确、具体、克制。
- **保留作者原意与技术准确性**：化学/材料术语、机理描述、数值一律不得改错。不确定的专业表述要保守，必要时向用户确认。
- **尊重领域常态**：被动语态、术语重复不是缺点，不要消灭它们。

## 文件说明

- `references/写作特征说明.md` — 各写作维度的含义与人类基准数值
- `references/corpus_stats.json` — 340 篇人类文献的写作基准向量
- 自检依赖同项目的 `translation-paper-detection` skill（`skills/translation-paper-detection/scripts/detect.py`），且其 Python 调用应遵循“使用目标环境 Python 绝对路径，不使用 `conda activate`”的规则
