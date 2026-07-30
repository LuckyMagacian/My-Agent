"""pdf-translator 抽取：PyMuPDF 提取文本块，区分图片/公式，标注语义段。"""
from __future__ import annotations

import re
from collections import Counter

from common import _get_fitz, parse_pages

# 数学字体识别（TeX/MathType 系列）；用于块级公式判定
_MATH_FONT_RE = re.compile(
    r"(MTSY|MTMI|MTEX|CMMI|CMSY|CMEX|CMR|LMMath|LatinModernMath|Math|Symbol|STIX|XITS|Asana|Euler|CambriaMath)",
    re.I,
)
# 数学符号字符（希腊字母/运算符/关系符等）
_MATH_SYMBOLS = set(
    "θαβγδεζηικλμνξπρστυφχψωΘΛΩΣΠΔΓΦΨ±∓×÷≤≥≠≈∝∂∇∑∏∫∮√∞∈∉∪∩⊂⊃⊆⊇¬←->↔⇒⇐⇔·′″°"
)
_MATH_OPERATORS = set("=+-−/<>")
# 行内公式判定用的强数学符号：剔除 - < > 等散文常见字符，避免把 prose 误判为公式
_STRONG_MATH_SYMBOLS = _MATH_SYMBOLS - set("-<>")


def _is_math_font(font: str) -> bool:
    """字体名是否为数学字体（TeX/MathType 系列）。"""
    return bool(_MATH_FONT_RE.search(font or ""))


def _is_formula_span(text: str, font: str, size: float, main_size: float) -> bool:
    """判定单个 span 是否为行内公式：数学字体 / 强数学符号 / 短上标。

    高精度优先：数学字体与强符号（希腊字母/大运算符/关系符）直接判定；
    上标仅在文本极短（<=3 字符）时判定，避免把脚注/小字 prose 误判。
    """
    if _is_math_font(font):
        return True
    if any(c in _STRONG_MATH_SYMBOLS for c in text):
        return True
    if main_size > 0 and size < main_size * 0.75 and len(text.strip()) <= 3:
        return True
    return False


def _is_formula_block(text: str, span_features: list[tuple[str, str, int, float]]) -> bool:
    """启发式判定块级公式：短文本 + 数学特征强 + 非完整英文句子。

    span_features: 每个非空 span 的 (text, font, flags, size)。
    块级公式特征：含数学字体/数学符号/上下标 span，且非完整英文句子（连续英文词<4）、文本短(<=60)。
    行内数学（如句中变量 θ）位于完整句子内（连续英文词>=4）被排除，随句子正常翻译。
    """
    t = text.strip()
    if not t:
        return False
    # 完整英文句子（连续英文词 >= 4）-> 行内文本，非块级公式
    if len(re.findall(r"[A-Za-z]{2,}", t)) >= 4:
        return False
    feats = [f for f in span_features if f[0].strip()]
    if not feats:
        return False
    sizes = [round(f[3], 2) for f in feats]
    main_size = Counter(sizes).most_common(1)[0][0] if sizes else 12.0
    has_superscript = any(f[3] < main_size * 0.75 for f in feats)
    has_math_font = any(_is_math_font(f[1]) for f in feats)
    has_math_symbol = any(c in _MATH_SYMBOLS for c in t)
    has_operator = any(c in _MATH_OPERATORS for c in t)
    # 必须有数学字体/符号/上标信号（排除普通短文本如 "result."）
    if not (has_superscript or has_math_font or has_math_symbol):
        return False
    # 短文本（块级公式通常 <= 60 字符）
    if len(t) > 60:
        return False
    return has_operator or has_math_symbol or has_superscript or has_math_font


def _build_segments(visual_rows: list[list[tuple]], main_size: float) -> list[dict]:
    """按阅读序构造 segments：[{text,type,font,size,flags,bbox}]，与 block text 对齐。

    相邻同类型 span 合并；同行多 line 间插空格、不同视觉行间插 \\n。
    首尾空白去除，保证 "".join(seg["text"]) == block["text"]。
    formula 段保留原 font/size/flags 供渲染；text 段元信息仅供参考。
    """
    segs: list[dict] = []

    def push(text: str, font: str, size: float, flags: int, bbox, is_formula: bool) -> None:
        if not text:
            return
        seg_type = "formula" if is_formula else "text"
        if segs and segs[-1]["type"] == seg_type:
            segs[-1]["text"] += text
            if bbox and segs[-1].get("bbox"):
                b = segs[-1]["bbox"]
                segs[-1]["bbox"] = [
                    min(b[0], bbox[0]), min(b[1], bbox[1]),
                    max(b[2], bbox[2]), max(b[3], bbox[3]),
                ]
        else:
            segs.append({
                "text": text, "type": seg_type, "font": font,
                "size": size, "flags": flags, "bbox": bbox,
            })

    for ri, row in enumerate(visual_rows):
        if ri > 0 and segs:
            push("\n", "", main_size, 0, None, False)
        row_sorted = sorted(row, key=lambda t: t[2])
        for li, info in enumerate(row_sorted):
            if li > 0:
                push(" ", "", main_size, 0, None, False)
            for (stxt, sfont, sflags, ssize, sbbox) in info[5]:
                push(stxt, sfont, ssize, sflags, sbbox,
                     _is_formula_span(stxt, sfont, ssize, main_size))
    # 首尾空白去除，与 text 对齐
    while segs and not segs[0]["text"].strip():
        segs.pop(0)
    if segs:
        segs[0]["text"] = segs[0]["text"].lstrip()
    while segs and not segs[-1]["text"].strip():
        segs.pop()
    if segs:
        segs[-1]["text"] = segs[-1]["text"].rstrip()
    return segs


def extract_page(doc, pno: int) -> list[dict]:
    """提取单页文本块（含行级 lines 元信息），区分图片。

    使用 PyMuPDF 的 dict 模式，按 block 输出，保留阅读顺序。
    每个文本块含 bbox/font/size/color/text/lines（行级 {x0,y0,x1,y1,text}），
    lines 供排版阶段做对齐识别；segments 标注 span 级类型（text/formula）供翻译保真与差异化渲染。
    图片块仅记录 bbox。
    """
    page = doc[pno]
    page_dict = page.get_text("dict")
    blocks_out: list[dict] = []
    for bidx, block in enumerate(page_dict.get("blocks", [])):
        bbox = [round(float(c), 2) for c in block.get("bbox", [0, 0, 0, 0])]
        if block.get("type") == 1:  # 图片块
            blocks_out.append({
                "page": pno,
                "id": f"p{pno}b{bidx}",
                "type": "image",
                "bbox": bbox,
            })
            continue
        # 文本块：按行聚合 span
        size_counter: Counter = Counter()
        font_counter: Counter = Counter()
        color_counter: Counter = Counter()
        span_features: list[tuple[str, str, int, float]] = []  # (text,font,flags,size) 供块级公式判定
        # 收集每个非空 line 的几何信息与 span 列表：(y0, y1, x0, x1, text, spans)
        # spans = [(text, font, flags, size, bbox)] 非空 span，供 segments 构造
        line_infos: list[tuple] = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = "".join(s.get("text", "") for s in spans)
            line_spans: list[tuple] = []
            for s in spans:
                txt = s.get("text", "")
                if not txt:
                    continue
                cnt = len(txt)
                size_counter[round(float(s.get("size", 12.0)), 2)] += cnt
                font_counter[s.get("font", "")] += cnt
                color_counter[int(s.get("color", 0))] += cnt
                sfont = s.get("font", "")
                sflags = int(s.get("flags", 0))
                ssize = float(s.get("size", 12.0))
                sbbox = [round(float(c), 2) for c in s.get("bbox", [0, 0, 0, 0])]
                span_features.append((txt, sfont, sflags, ssize))
                line_spans.append((txt, sfont, sflags, ssize, sbbox))
            if line_text.strip():
                lbbox = line.get("bbox", [0, 0, 0, 0])
                line_infos.append(
                    (float(lbbox[1]), float(lbbox[3]), float(lbbox[0]), float(lbbox[2]), line_text, line_spans)
                )
        # 同一视觉行的 line 按 x 顺序用空格连接，不同视觉行用 \n。
        # PyMuPDF 常把目录/页眉等 x 不连续的同行文本拆成多 line，直接 \n 连接
        # 会把一行误变多行，故按 y 区间重叠判定真实视觉行。
        line_infos.sort(key=lambda t: (t[0], t[2]))
        visual_rows: list[list[tuple]] = []
        for info in line_infos:
            if visual_rows:
                prev = visual_rows[-1][-1]
                min_h = min(prev[1] - prev[0], info[1] - info[0])
                overlap = min(prev[1], info[1]) - max(prev[0], info[0])
                if min_h > 0 and overlap >= min_h * 0.5:
                    visual_rows[-1].append(info)
                    continue
            visual_rows.append([info])
        # 每个 visual_row 聚合为一条 line：x0=min/x1=max，text 按 x 排序空格连接
        lines_out: list[dict] = []
        row_texts: list[str] = []
        for row in visual_rows:
            row_sorted = sorted(row, key=lambda t: t[2])
            row_text = " ".join(t[4] for t in row_sorted)
            lines_out.append({
                "x0": round(min(t[2] for t in row_sorted), 2),
                "y0": round(min(t[0] for t in row_sorted), 2),
                "x1": round(max(t[3] for t in row_sorted), 2),
                "y1": round(max(t[1] for t in row_sorted), 2),
                "text": row_text,
            })
            row_texts.append(row_text)
        text = "\n".join(row_texts).strip()
        if not text:
            continue
        dom_size = size_counter.most_common(1)[0][0] if size_counter else 12.0
        dom_font = font_counter.most_common(1)[0][0] if font_counter else ""
        dom_color = color_counter.most_common(1)[0][0] if color_counter else 0
        is_formula = _is_formula_block(text, span_features)
        segments = _build_segments(visual_rows, dom_size)
        blocks_out.append({
            "page": pno,
            "id": f"p{pno}b{bidx}",
            "type": "formula" if is_formula else "text",
            "bbox": bbox,
            "font": dom_font,
            "size": dom_size,
            "color": dom_color,
            "text": text,
            "lines": lines_out,
            "segments": segments,
        })
    return _group_segments(blocks_out)


def extract(pdf_path: str, pages: str | None = None) -> list[dict]:
    """提取每页文本块（含行级 lines 元信息），区分图片。逐页 extract_page 拼接。"""
    fitz = _get_fitz()
    doc = fitz.open(pdf_path)
    total = doc.page_count
    page_indices = parse_pages(pages, total) or list(range(total))
    blocks_out: list[dict] = []
    for pno in page_indices:
        blocks_out.extend(extract_page(doc, pno))
    doc.close()
    return blocks_out


def _group_segments(blocks: list[dict]) -> list[dict]:
    """为文本块标注 seg_id：同页内相邻、排版一致的 block 归入同一语义段。

    仅标注上下文关系，不合并文本、不改 block 粒度，render 零影响。
    旧 extract JSON 无 seg_id 时，translate 退化为每块自成一组。
    """
    # 中位字号作为标题判定基准（字号显著偏大视为标题，作段组分隔点）
    text_sizes = sorted(float(b.get("size", 12.0)) for b in blocks if b.get("type") == "text")
    med = text_sizes[len(text_sizes) // 2] if text_sizes else 12.0
    title_thr = med * 1.4

    seg_idx = 0
    prev_text: dict | None = None  # 上一个可延续的文本块
    for b in blocks:
        if b.get("type") != "text" or not b.get("text", "").strip():
            prev_text = None  # 图片/空块打断段组
            continue
        size = float(b.get("size") or 12.0)
        if size > title_thr:  # 标题自成一段并打断前后
            seg_idx += 1
            b["seg_id"] = f"s{seg_idx}"
            prev_text = None
            continue
        if prev_text is not None:
            cur_bbox, prev_bbox = b["bbox"], prev_text["bbox"]
            gap = cur_bbox[1] - prev_bbox[3]  # 垂直间距：当前顶 - 前块底
            line_h = float(prev_text.get("size") or 12.0) * 1.25
            if (
                b.get("page") == prev_text.get("page")
                and 0 <= gap < line_h * 1.5
                and abs(size - float(prev_text.get("size") or 12.0)) < 0.5
                and b.get("font") == prev_text.get("font")
                and b.get("color") == prev_text.get("color")
            ):
                b["seg_id"] = prev_text["seg_id"]
                prev_text = b
                continue
        seg_idx += 1
        b["seg_id"] = f"s{seg_idx}"
        prev_text = b
    return blocks
