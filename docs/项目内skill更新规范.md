# 项目内 skill 更新规范

本规范用于指导 AI 助手把**全局 skill** 或外部来源的 skill 更新并同步到本项目，使其继续符合本项目的目录结构、命名约定、环境规则和文档要求。

适用对象：

- `skills/translation-humanizer/`
- `skills/translation-paper-detection/`
- `skills/translation-paper-editing/`
- 未来新增的其他项目级 skill

---

## 一、更新目标

当需要把某个上游 skill 的新版本同步到本项目时，AI 助手的目标不是“原样复制”，而是：

1. 保留上游 skill 的核心能力与新改动
2. 继续使用本项目内的 skill 名称，避免与全局 skill 同名冲突
3. 继续使用本项目的相对路径结构
4. 继续遵守本项目的 Python 环境规则
5. 同步更新所有引用该 skill 的项目文档
6. 清理或忽略新引入的本地状态文件、缓存文件、环境文件

---

## 二、项目固定约定

AI 助手在更新 skill 时，必须保留以下项目约定：

### 1. skill 存放位置

所有项目级 skill 统一放在：

```text
skills/<skill-name>/
```

不要放回全局目录、用户目录或其他外部目录。

### 2. skill 命名

当前项目内 skill 名称固定为：

- `translation-humanizer`
- `translation-paper-detection`
- `translation-paper-editing`

如果上游 skill 原名是：

- `humanizer`
- `paper-detection`
- `paper-editing`

同步到本项目后，必须改回上述项目名，不得直接保留上游原名。

### 3. 路径写法

文档和 skill 内部说明统一优先使用**相对路径**，例如：

- `skills/translation-paper-detection/scripts/detect.py`
- `docs/环境准备.md`

禁止把你本机的绝对路径写进项目文档或 skill 说明，例如：

- `C:\Users\...`
- `D:\Software\Miniconda\...`

### 4. Python 环境规则

本项目禁止在自动化流程、脚本说明、skill 执行步骤里使用：

```bash
conda activate <env>
```

必须改为“直接使用目标环境的 Python 绝对路径调用脚本”。

如果更新后的上游 skill 把 `conda activate`、`source venv/bin/activate` 一类内容重新带回来了，AI 助手必须按本项目约定改写。

---

## 三、AI 助手执行更新时的标准步骤

### 步骤 1：复制上游 skill 到项目内

把上游 skill 的最新内容复制到本项目的对应目录，例如：

- 上游 `humanizer` → 项目 `skills/translation-humanizer/`
- 上游 `paper-detection` → 项目 `skills/translation-paper-detection/`
- 上游 `paper-editing` → 项目 `skills/translation-paper-editing/`

如果目录已存在，先读取并理解现有项目版本，再覆盖式更新，避免误删本项目额外加的适配内容。

### 步骤 2：修改 skill 元数据

重点检查每个 skill 根目录下的 `SKILL.md`：

1. `name:` 是否仍为项目内名称
2. 是否引用了其他 skill 的旧全局名
3. 是否包含绝对路径
4. 是否包含不符合本项目约定的环境切换说明
5. 是否把项目内相对路径又改回了全局安装路径

### 步骤 3：修改 skill 内部引用

检查以下目录中的文件：

- `SKILL.md`
- `README.md`
- `AGENTS.md`
- `references/`
- `scripts/`
- `assets/`

把其中不符合本项目的内容改掉，尤其是：

- 旧 skill 名
- 全局安装路径
- 用户目录路径
- `.claude/skills/...`
- `.codex/skills/...`
- `conda activate`

### 步骤 4：同步项目文档

如果 skill 的能力、依赖、调用方式、输出文件或推荐流程发生变化，必须同步检查并更新：

- `项目概览.md`
- `README.md`
- `docs/常见操作与脚本说明.md`
- `docs/环境准备.md`
- `docs/表格处理说明.md`
- `docs/对照表格式.md`

如果新增了新的项目级 skill，也要把它补进文档索引与目录结构说明中。

### 步骤 5：处理新增依赖与本地状态文件

如果更新后的 skill：

- 新增 Python 依赖
- 新增模型下载
- 新增缓存目录
- 新增 `.json` 状态文件
- 新增 `.venv_*` 或其他本地环境目录

AI 助手必须：

1. 先向用户确认是否安装新依赖
2. 更新 `requirements.txt`（若该依赖属于项目层而不是纯 skill 私有层）
3. 更新 `.gitignore`
4. 在 `docs/环境准备.md` 中补充说明

### 步骤 6：全文检索校验

更新完成后，必须全文检索是否还有遗漏的旧内容。

推荐检索目标：

- 旧 skill 名
- 全局安装目录
- 本机绝对路径
- `conda activate`
- 旧的互相引用关系

---

## 四、必改项清单

AI 助手每次更新项目内 skill 时，至少检查以下项目。

### A. `SKILL.md` 必查

- `name:` 是否是项目名
- 对其他 skill 的引用名是否已经改成项目名
- 示例命令中的路径是否是项目相对路径
- 环境说明是否符合“直接使用 Python 绝对路径”的规则

### B. `scripts/` 必查

- 是否写死旧 skill 名
- 是否写死全局目录
- 是否会在 skill 目录中生成新的状态文件或环境目录

### C. `references/` 必查

- 是否仍提到旧 skill 名
- 是否说明了错误的运行位置

### D. 项目文档必查

- `项目概览.md`
- `README.md`
- `docs/常见操作与脚本说明.md`
- `docs/环境准备.md`

### E. Git 忽略规则必查

- `.gitignore` 是否需要新增本地状态文件
- `.gitignore` 是否需要新增缓存或环境目录

---

## 五、建议使用的检索命令

AI 助手更新完后，建议运行：

```powershell
rg -n "humanizer|paper-detection|paper-editing|\.claude/skills|\.codex/skills|conda activate|C:\\|D:\\" skills docs README.md 项目概览.md .gitignore requirements.txt
```

如果是更新某一个具体 skill，也可以缩小范围，例如：

```powershell
rg -n "paper-detection|\.claude/skills|conda activate|C:\\|D:\\" skills/translation-paper-detection docs README.md 项目概览.md
```

注意：检索结果里如果命中的是**新项目名的一部分**，需要人工判断是否正常；不要机械地把所有命中都当错误。

---

## 六、推荐给 AI 的执行指令模板

以后你可以直接对 AI 助手下达类似指令：

```text
请按 docs/项目内skill更新规范.md，把全局的 <skill 名> 同步更新到本项目对应的项目级 skill。
要求：
1. 保留上游新改动
2. 继续使用项目内 skill 名称
3. 同步修改内部引用、相关文档和 .gitignore
4. 全文检索校验后再汇报
```

如果要同时更新多个 skill，可以这样说：

```text
请按 docs/项目内skill更新规范.md，
把全局的 humanizer、paper-detection、paper-editing 同步到项目内，
并保持项目名 translation-humanizer、translation-paper-detection、translation-paper-editing 不变。
完成后请同步更新项目文档并做全文检索校验。
```

---

## 七、不要做的事

AI 助手更新 skill 时，不应做以下事情：

1. 不要把项目内 skill 改回全局原名
2. 不要把 skill 放回 `C:\Users\...`、`~/.claude/skills/...` 这类用户目录
3. 不要在项目文档里写绝对路径
4. 不要把 `conda activate` 写回自动化流程
5. 不要新增依赖却不更新说明
6. 不要新增本地状态文件却不更新 `.gitignore`
7. 不要只复制 skill 本体而不检查项目文档引用

---

## 八、更新完成后的最小验收标准

只有同时满足以下条件，才算一次合格的 skill 更新：

1. `skills/` 中的目标 skill 已更新到新版本
2. `SKILL.md` 的 `name:` 保持项目名
3. skill 内部不再引用旧全局路径或旧全局名
4. 项目文档已同步
5. `.gitignore` 与依赖说明已同步
6. 已做全文检索校验，确认没有明显遗漏
