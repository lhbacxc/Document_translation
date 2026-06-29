"""
textproc.py — 学术文本清洗与写作特征提取核心模块

职责：
  1. clean_markdown(): 把 mineru 转换的 md 噪声(公式/图片/角标/表格/参考文献)清洗为纯正文
  2. extract_sentences(): 用 spaCy 分句并过滤掉非正文句(过短、数字堆、标题等)
  3. sentence_features(): 对单句计算一组与"人味/AI味"相关的可量化特征
  4. doc_features(): 对整篇文档(句子列表)聚合出文档级特征

该模块被 extract_features.py(建立人类基准) 与 translation-paper-detection/scripts/detect.py(逐句判定) 共用，
所以保持零外部状态、纯函数，方便整体拷贝进 skill。
"""

import re
import math
from collections import Counter

# ----------------------------------------------------------------------------
# 一、清洗
# ----------------------------------------------------------------------------

# 参考文献区起始标记：命中后正文到此为止
_REF_HEADER = re.compile(
    r'^\s*#{0,4}\s*(references|reference list|bibliography|literature cited|'
    r'notes and references|references and notes)\s*$',
    re.IGNORECASE | re.MULTILINE,
)

# 这些区段属于模板/元信息，不反映作者行文风格，整体剔除
_NONPROSE_HEADER = re.compile(
    r'^\s*#{0,4}\s*(acknowledg(e?ments?)|conflicts? of interest|'
    r'author contributions?|funding|supporting information|'
    r'data availability|abbreviations|crediT authorship|'
    r'declaration of competing interest|appendix)\b',
    re.IGNORECASE,
)


def _strip_inline_noise(text: str) -> str:
    """去除行内噪声：公式、图片、html 标签、引用角标、URL 等。"""
    # 图片占位符 ![](images/xxx)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', text)
    # 普通 markdown 链接 [text](url) -> text
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # 块级与行内 LaTeX 公式
    text = re.sub(r'\$\$.*?\$\$', ' ', text, flags=re.DOTALL)
    text = re.sub(r'\$[^$]*\$', ' ', text)
    # 还原 mineru 把 fi/fl 连字拆成 <sup>fl</sup> 之类：先取标签内文字再去标签
    text = re.sub(r'<sup>([a-zA-Z]{1,3})</sup>', r'\1', text)
    text = re.sub(r'<sub>([a-zA-Z]{1,3})</sub>', r'\1', text)
    # 引用角标 <sup>1,2</sup> / <sup>12</sup> 等纯数字上标 -> 删除
    text = re.sub(r'<sup>[\d,\s\-–]+</sup>', '', text)
    # 残余 html 标签
    text = re.sub(r'</?[a-zA-Z][^>]*>', '', text)
    # 方括号数字引用 [1] [2,3] [4–6]
    text = re.sub(r'\[\s*\d+(\s*[,\-–]\s*\d+)*\s*\]', '', text)
    # URL / DOI
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'\bdoi:\s*\S+', ' ', text, flags=re.IGNORECASE)
    # markdown 强调符号
    text = text.replace('**', '').replace('\\*', '').replace('*', '')
    return text


def clean_markdown(md: str) -> str:
    """把整篇 md 清洗为纯正文文本(段落以空行分隔)。"""
    # 截断参考文献区
    m = _REF_HEADER.search(md)
    if m:
        md = md[: m.start()]

    lines = md.split('\n')
    kept = []
    skip_section = False
    for line in lines:
        # 进入致谢/利益冲突等非正文区后，跳过直到下一个一级/二级标题
        if _NONPROSE_HEADER.match(line):
            skip_section = True
            continue
        if skip_section:
            if re.match(r'^\s*#{1,4}\s+\S', line):
                skip_section = False  # 新标题，结束跳过
            else:
                continue

        # markdown 表格行
        if re.match(r'^\s*\|', line) or re.match(r'^\s*[-:|]{4,}\s*$', line):
            continue
        # 标题行：去掉 # 记号但保留文字(有些正文被切成标题)，交给后续句子过滤
        line = re.sub(r'^\s*#{1,6}\s*', '', line)
        kept.append(line)

    text = '\n'.join(kept)
    text = _strip_inline_noise(text)
    # 规整空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    return text.strip()


# ----------------------------------------------------------------------------
# 二、分句与正文句过滤
# ----------------------------------------------------------------------------

def extract_sentences(clean_text: str, nlp) -> list:
    """用 spaCy 分句，返回过滤后的正文句子列表(spaCy Span)。"""
    sents = []
    # spaCy 默认 1MB 上限，长文分块处理
    for chunk in _chunk(clean_text, 90000):
        doc = nlp(chunk)
        for s in doc.sents:
            if _is_prose_sentence(s.text):
                sents.append(s)
    return sents


def _chunk(text, size):
    if len(text) <= size:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # 尽量在段落边界切
        nl = text.rfind('\n', start, end)
        if nl > start + size // 2:
            end = nl
        yield text[start:end]
        start = end


def _is_prose_sentence(s: str) -> bool:
    """判断是否为合格的正文句：足够长、字母占比高、含动词性结构、非公式���渣。"""
    s = s.strip()
    words = s.split()
    if len(words) < 6 or len(words) > 80:
        return False
    letters = sum(c.isalpha() for c in s)
    if letters / max(len(s), 1) < 0.6:  # 字母占比太低 -> 多半是公式/数据表残渣
        return False
    digits = sum(c.isdigit() for c in s)
    if digits / max(len(s), 1) > 0.18:  # 数字过密
        return False
    if not re.search(r'[.!?]["\')\]]?$', s):  # 句子应有终止标点
        return False
    if sum(c.isupper() for c in s) / max(letters, 1) > 0.45:  # 全大写标题
        return False
    return True


# ----------------------------------------------------------------------------
# 三、特征词表(基于本领域语料先验)
# ----------------------------------------------------------------------------

# AI 常用套话/华丽短语（小写匹配）。这些在人类分析化学论文里出现极少，是强信号。
AI_CLICHE_PHRASES = [
    "delve into", "delves into", "delving into",
    "play a crucial role", "plays a crucial role", "playing a crucial role",
    "play a pivotal role", "plays a pivotal role", "play a vital role",
    "play a significant role", "plays a significant role",
    "shed light on", "sheds light on", "shedding light on",
    "a testament to", "stands as a testament",
    "in the realm of", "in the world of", "in the landscape of",
    "navigate the", "navigating the", "navigating this",
    "it is worth noting that", "it is important to note that",
    "it is crucial to", "it is essential to note",
    "a wide range of", "a wide array of", "a myriad of", "a plethora of",
    "rich tapestry", "intricate", "intricacies",
    "underscore", "underscores", "underscoring",
    "pave the way", "paves the way", "paving the way",
    "harness the power", "harnessing the power", "unlock the potential",
    "at the forefront", "cutting-edge", "state-of-the-art landscape",
    "ever-evolving", "ever-growing", "rapidly evolving landscape",
    "holds immense", "holds great promise", "immense potential",
    "revolutionize", "revolutionizing", "groundbreaking",
    "seamless", "seamlessly", "robust framework",
    "leverage", "leveraging", "leverages",
    "multifaceted", "comprehensive understanding", "nuanced",
    "foster", "fostering", "fosters",
    "realm of possibilities", "transformative", "paradigm shift",
    "in today's world", "in an era", "in the era of",
    "meticulous", "meticulously", "garner", "garnered",
]

# 过渡/连接副词（句首或句中），AI 倾向高频且规整使用
TRANSITION_WORDS = [
    "moreover", "furthermore", "additionally", "consequently",
    "however", "therefore", "thus", "hence", "nevertheless",
    "nonetheless", "accordingly", "subsequently", "notably",
    "importantly", "significantly", "overall", "in conclusion",
    "in summary", "in essence", "ultimately", "indeed",
    "specifically", "particularly", "essentially", "fundamentally",
]

# 具体性词：单位、仪器、定量——人类实验论文密度高，AI 泛泛而谈密度低
_UNIT_RE = re.compile(
    r'\b(\d+(\.\d+)?\s?(nm|µm|um|mm|cm|nM|µM|uM|mM|M|mg|µg|ug|ng|g|kg|mL|µL|uL|L|'
    r'mol|mmol|ppm|ppb|kV|mV|V|mA|°C|K|min|h|s|Hz|rpm|wt%|v/v|w/w|%))\b',
    re.IGNORECASE,
)
_INSTRUMENT_RE = re.compile(
    r'\b(HPLC|LC-MS|GC-MS|UV-vis|FTIR|FT-IR|XPS|XRD|SEM|TEM|HR-TEM|NMR|'
    r'SERS|FRET|DFT|TGA|DLS|EDS|EDX|ICP|MALDI|TCSPC|PL|QY|LOD|LOQ)\b'
)


# ----------------------------------------------------------------------------
# 四、句级特征
# ----------------------------------------------------------------------------

def sentence_features(span) -> dict:
    """对单个 spaCy 句子计算特征。返回 dict。"""
    text = span.text.strip()
    low = text.lower()
    tokens = [t for t in span if not t.is_space]
    words = [t for t in tokens if t.is_alpha]
    n_words = len(words)

    # 被动语态：助动词 be + 过去分词(VBN) 依存
    passive = any(t.dep_ in ("nsubjpass", "auxpass") for t in span)

    # 套话短语命中
    cliche_hits = sum(low.count(p) for p in AI_CLICHE_PHRASES)

    # 过渡词命中(整句)
    trans_hits = sum(1 for w in TRANSITION_WORDS if re.search(r'\b' + re.escape(w) + r'\b', low))
    # 句首过渡词(更强的 AI 模板信号)
    first_word = words[0].text.lower() if words else ""
    starts_with_transition = first_word in TRANSITION_WORDS

    # 具体性
    unit_hits = len(_UNIT_RE.findall(text))
    instrument_hits = len(_INSTRUMENT_RE.findall(text))
    digit_tokens = sum(1 for t in tokens if any(c.isdigit() for c in t.text))

    # 标点
    commas = text.count(',')
    semicolons = text.count(';')
    dashes = text.count('—') + text.count(' - ') + text.count('–')

    # 词长(字符)均值——AI 倾向更长的拉丁词
    avg_word_len = sum(len(w.text) for w in words) / max(n_words, 1)

    return {
        "n_words": n_words,
        "passive": int(passive),
        "cliche_hits": cliche_hits,
        "transition_hits": trans_hits,
        "starts_with_transition": int(starts_with_transition),
        "unit_hits": unit_hits,
        "instrument_hits": instrument_hits,
        "digit_tokens": digit_tokens,
        "concreteness": unit_hits + instrument_hits + digit_tokens,
        "commas": commas,
        "semicolons": semicolons,
        "dashes": dashes,
        "avg_word_len": avg_word_len,
    }


# ----------------------------------------------------------------------------
# 五、文档级聚合特征
# ----------------------------------------------------------------------------

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def doc_features(sent_feats: list) -> dict:
    """把一篇文档的句级特征列表聚合成文档级指标。"""
    if not sent_feats:
        return {}
    lens = [f["n_words"] for f in sent_feats]
    n = len(sent_feats)
    total_words = sum(lens)

    mean_len = _mean(lens)
    std_len = _std(lens)
    # burstiness 突发度：句长变异系数。人类高(长短交错)，AI 低(均匀)
    burstiness = std_len / mean_len if mean_len else 0.0

    per_100w = lambda key: sum(f[key] for f in sent_feats) / max(total_words, 1) * 100

    return {
        "n_sentences": n,
        "total_words": total_words,
        "mean_sentence_len": mean_len,
        "std_sentence_len": std_len,
        "burstiness": burstiness,
        "pct_passive": _mean([f["passive"] for f in sent_feats]) * 100,
        "pct_starts_transition": _mean([f["starts_with_transition"] for f in sent_feats]) * 100,
        "cliche_per_1000w": per_100w("cliche_hits") * 10,
        "transition_per_100w": per_100w("transition_hits"),
        "concreteness_per_100w": per_100w("concreteness"),
        "unit_per_100w": per_100w("unit_hits"),
        "instrument_per_100w": per_100w("instrument_hits"),
        "commas_per_sent": _mean([f["commas"] for f in sent_feats]),
        "semicolons_per_100w": per_100w("semicolons"),
        "dashes_per_100w": per_100w("dashes"),
        "mean_word_len": _mean([f["avg_word_len"] for f in sent_feats]),
    }


def lexical_diversity(sent_feats_words: list) -> dict:
    """词汇多样性：TTR 与近似 MTLD。输入为全文小写词 token 列表。"""
    words = sent_feats_words
    n = len(words)
    if n == 0:
        return {"ttr": 0.0, "mtld": 0.0}
    types = len(set(words))
    ttr = types / n
    return {"ttr": ttr, "mtld": _mtld(words)}


def _mtld(words, threshold=0.72):
    """MTLD(Measure of Textual Lexical Diversity)单向计算的简化实现。"""
    def _one_pass(seq):
        factors = 0
        types = set()
        token_count = 0
        for w in seq:
            token_count += 1
            types.add(w)
            ttr = len(types) / token_count
            if ttr <= threshold:
                factors += 1
                types = set()
                token_count = 0
        if token_count > 0:
            ttr = len(types) / token_count
            factors += (1 - ttr) / (1 - threshold)
        return len(seq) / factors if factors else len(seq)

    forward = _one_pass(words)
    backward = _one_pass(list(reversed(words)))
    return (forward + backward) / 2
