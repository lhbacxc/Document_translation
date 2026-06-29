"""
detect.py — 学术文本 AI 痕迹逐句检测

依据 references/corpus_stats.json 中的人类写作基准，对输入文本逐句计算多维偏离，
加权汇总为每句 0-100% 的"AI 可能性"，并给出全文综合分。

设计原则：
  - 这是基于统计偏离的【启发式信号】，不是确定性鉴定，输出务必附免责说明。
  - 被动语态在本领域(实验论文)是常态，不作为 AI 信号。
  - 文档级信号(句长突发度、句首过渡词占比)对全文每句施加一个基线调整；
    句级信号(套话命中、具体性、句长偏离)决定单句的相对高低。

用法：
  python detect.py --text "..."                 # 直接传文本
  python detect.py --file path/to/text.txt      # 从文件读
  echo "..." | python detect.py                 # 标准输入
  附加 --json 输出机器可读结果

输出：逐句概率 + 触发理由 + 全文综合 AI 概率
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textproc as tp

import spacy


def load_baseline():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "references", "corpus_stats.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _z(value, mean, std):
    if not std:
        return 0.0
    return (value - mean) / std


def _logistic(x):
    import math
    return 1.0 / (1.0 + math.exp(-x))


def analyze(text, nlp, baseline):
    feats = baseline["features"]
    clean = tp.clean_markdown(text)  # 容忍用户直接贴 md；纯文本也安全
    if not clean.strip():
        clean = text.strip()

    # 分句（这里不过滤过短句，因为用户可能想看每一句；但标记是否为正���句）
    sents = []
    for chunk in tp._chunk(clean, 90000):
        doc = nlp(chunk)
        sents.extend(list(doc.sents))

    sfeats = [tp.sentence_features(s) for s in sents]
    valid = [f for f, s in zip(sfeats, sents) if tp._is_prose_sentence(s.text)]
    dfeat = tp.doc_features(valid) if len(valid) >= 5 else {}

    # ---- 文档级基线调整(对每句叠加) ----
    doc_adjust = 0.0
    doc_reasons = []
    if dfeat:
        # 突发度偏低 -> 偏 AI。z 为负越多越可疑
        zb = _z(dfeat["burstiness"], feats["burstiness"]["mean"], feats["burstiness"]["std"])
        if zb < -0.8:
            doc_adjust += min(-zb, 3) * 0.18
            doc_reasons.append(f"全文句长过于均匀(突发度{dfeat['burstiness']:.2f}，人类基准{feats['burstiness']['mean']:.2f})")
        # 句首过渡词占比偏高 -> 偏 AI
        zt = _z(dfeat["pct_starts_transition"], feats["pct_starts_transition"]["mean"], feats["pct_starts_transition"]["std"])
        if zt > 1.0:
            doc_adjust += min(zt, 3) * 0.12
            doc_reasons.append(f"句首过渡词偏多({dfeat['pct_starts_transition']:.0f}%，人类基准{feats['pct_starts_transition']['mean']:.0f}%)")
        # 全文具体性偏低 -> 偏 AI
        zc = _z(dfeat["concreteness_per_100w"], feats["concreteness_per_100w"]["mean"], feats["concreteness_per_100w"]["std"])
        if zc < -0.8:
            doc_adjust += min(-zc, 3) * 0.12
            doc_reasons.append(f"全文具体信息(数值/单位/仪器)偏少")

    # ---- 逐句打分 ----
    results = []
    sent_mean = feats["mean_sentence_len"]["mean"]
    sent_std = feats["mean_sentence_len"]["std"] * 0  # 用句级分布更合适
    # 句级句长分布
    sl = baseline["sentence_length_distribution"]
    for f, s in zip(sfeats, sents):
        if not tp._is_prose_sentence(s.text):
            continue
        score = 0.0
        reasons = []

        # 1) 套话命中(最强句级信号)
        if f["cliche_hits"] > 0:
            score += 1.6 + 0.6 * (f["cliche_hits"] - 1)
            reasons.append(f"含 AI 套话短语 x{f['cliche_hits']}")

        # 2) 句首过渡词
        if f["starts_with_transition"]:
            score += 0.5
            reasons.append("以过渡词开头")
        elif f["transition_hits"] >= 2:
            score += 0.4
            reasons.append("过渡词偏多")

        # 3) 句内零具体性 + 长度不短(泛泛而谈)
        if f["concreteness"] == 0 and f["n_words"] >= 18:
            score += 0.5
            reasons.append("较长但无任何具体数据/单位/仪器")

        # 4) 句长贴近"安全均值"(AI 偏好 18-26 词的标准句)
        if 18 <= f["n_words"] <= 27:
            score += 0.2

        # 5) 词长偏长(堆砌拉丁大词)
        if f["avg_word_len"] > 6.2:
            score += 0.25
            reasons.append("用词偏长/书面腔")

        # 叠加文档级基线
        score += doc_adjust

        prob = _logistic(1.5 * score - 2.0)  # 平移+放大，使无信号句概率偏低、强信号句拉满
        prob = round(min(max(prob, 0.02), 0.985) * 100, 1)

        results.append({
            "sentence": s.text.strip(),
            "ai_probability": prob,
            "reasons": reasons,
            "n_words": f["n_words"],
        })

    # ---- 全文综合 ----
    if results:
        probs = [r["ai_probability"] for r in results]
        # 综合分：均值与高分句的加权(高分句更说明问题)
        probs_sorted = sorted(probs, reverse=True)
        top = probs_sorted[: max(1, len(probs_sorted)//4)]
        overall = round(0.6 * (sum(probs)/len(probs)) + 0.4 * (sum(top)/len(top)), 1)
    else:
        overall = 0.0

    return {
        "overall_ai_probability": overall,
        "n_sentences_analyzed": len(results),
        "document_signals": doc_reasons,
        "sentences": results,
    }


def render(report):
    lines = []
    lines.append("=" * 70)
    lines.append(f"全文综合 AI 可能性：{report['overall_ai_probability']}%   "
                 f"(分析 {report['n_sentences_analyzed']} 句)")
    if report["document_signals"]:
        lines.append("文档级信号：")
        for r in report["document_signals"]:
            lines.append(f"  • {r}")
    lines.append("=" * 70)
    lines.append("")
    for i, s in enumerate(report["sentences"], 1):
        p = s["ai_probability"]
        flag = "🔴" if p >= 70 else ("🟡" if p >= 40 else "🟢")
        lines.append(f"[{i:>2}] {flag} {p:>5.1f}%  {s['sentence']}")
        if s["reasons"]:
            lines.append(f"          理由：{ '；'.join(s['reasons']) }")
    lines.append("")
    lines.append("-" * 70)
    lines.append("说明：本结果为基于人类语料统计偏离的启发式信号，非确定性鉴定，")
    lines.append("不能作为学术不端证据。被动语态等领域常态不计入 AI 信号。")
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("（无输入文本）", file=sys.stderr)
        sys.exit(1)

    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    nlp.max_length = 200000
    baseline = load_baseline()
    report = analyze(text, nlp, baseline)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))


if __name__ == "__main__":
    main()
