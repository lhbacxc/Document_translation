"""
从 docx 文件中提取纯文本，保留上下标信息和表格结构。

上下标处理：Word 中通过 <w:vertAlign> 标记的上下标文字会被自动转为
Unicode 上下标字符（⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ / ₀₁₂₃₄₅₆₇₈₉），确保后续翻译
和 build_docx.py 生成 Word 时能还原为原生上下标格式。

表格处理：Word 中的表格会被转换为 Markdown 表格格式。

用法：
    python extract_text.py <输入docx路径> [输出txt路径]

例：
    python extract_text.py input/我的论文.docx
    # 输出到 temp/我的论文_extracted_text.txt

    python extract_text.py input/我的论文.docx temp/custom_output.txt
    # 自定义输出路径

若不指定输出路径，默认基于输入文件名写到 temp/<输入文件名>_extracted_text.txt。
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_TO_SUPERSCRIPT = str.maketrans(
    "0123456789+-=()nδ",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿᵟ",
)
_TO_SUBSCRIPT = str.maketrans(
    "0123456789+-=()",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎",
)


def _convert_script(text: str, mode: str) -> str:
    """将文本中可映射的字符转为 Unicode 上/下标，不可映射的原样保留。"""
    if mode == "superscript":
        return text.translate(_TO_SUPERSCRIPT)
    elif mode == "subscript":
        return text.translate(_TO_SUBSCRIPT)
    return text


def _get_vert_align(run_elem) -> str:
    """从 <w:r> 元素中读取 vertAlign 值，返回 'superscript'/'subscript'/''。"""
    rpr = run_elem.find(f"{W_NS}rPr")
    if rpr is None:
        return ""
    vert = rpr.find(f"{W_NS}vertAlign")
    if vert is None:
        return ""
    return vert.get(f"{W_NS}val", "")


def _extract_cell_text(cell_elem) -> str:
    """从表格单元格中提取文本（支持上下标）。"""
    parts = []
    for p in cell_elem.iter(f"{W_NS}p"):
        for run in p.iter(f"{W_NS}r"):
            align = _get_vert_align(run)
            for t in run.iter(f"{W_NS}t"):
                txt = t.text or ""
                if txt and align:
                    txt = _convert_script(txt, align)
                parts.append(txt)
    return " ".join(parts).strip()


def _extract_table(tbl_elem) -> str:
    """从 Word 表格元素提取并转换为 Markdown 表格。"""
    rows = []
    for tr in tbl_elem.findall(f"{W_NS}tr"):
        cells = []
        for tc in tr.findall(f"{W_NS}tc"):
            cell_text = _extract_cell_text(tc)
            cells.append(cell_text)
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # 构建 Markdown 表格
    md_lines = []
    for i, row in enumerate(rows):
        md_lines.append("| " + " | ".join(row) + " |")
        # 第一行后添加分隔符
        if i == 0:
            md_lines.append("| " + " | ".join(["---"] * len(row)) + " |")

    return "\n".join(md_lines)


def extract_text_from_docx(docx_path: str) -> str:
    """解压 docx，解析 word/document.xml，按段落和表格顺序输出。

    Word 中的上下标 run 会被转为 Unicode 上下标字符。
    表格会被转换为 Markdown 表格格式。
    """
    with zipfile.ZipFile(docx_path, "r") as zf:
        with zf.open("word/document.xml") as f:
            tree = ET.parse(f)

    root = tree.getroot()
    body = root.find(f"{W_NS}body")
    if body is None:
        return ""

    blocks = []

    # 遍历 body 的直接子元素，保持段落和表格的顺序
    for elem in body:
        if elem.tag == f"{W_NS}p":
            # 普通段落
            parts = []
            for run in elem.iter(f"{W_NS}r"):
                align = _get_vert_align(run)
                for t in run.iter(f"{W_NS}t"):
                    txt = t.text or ""
                    if txt and align:
                        txt = _convert_script(txt, align)
                    parts.append(txt)
            line = "".join(parts).strip()
            if line:
                blocks.append(line)

        elif elem.tag == f"{W_NS}tbl":
            # 表格
            table_md = _extract_table(elem)
            if table_md:
                blocks.append(table_md)

    return "\n\n".join(blocks)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    docx_path = sys.argv[1]
    if not os.path.isfile(docx_path):
        print(f"[错误] 找不到文件: {docx_path}")
        sys.exit(1)

    # 提取输入文件名（不含扩展名）
    input_basename = os.path.splitext(os.path.basename(docx_path))[0]

    # 默认输出路径基于输入文件名
    default_out = os.path.join("temp", f"{input_basename}_extracted_text.txt")
    out_path = sys.argv[2] if len(sys.argv) >= 3 else default_out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    text = extract_text_from_docx(docx_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"[完成] 已提取 {len(text)} 字符 -> {out_path}")


if __name__ == "__main__":
    main()
