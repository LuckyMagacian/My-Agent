#!/usr/bin/env python3
"""排版优化模块：基于原文元信息规划译文的对齐/字号/换行/字体风格。

由 pdf_translate.py 的页级流水线在 translate 后、render 前调用。
输入 extract_page 产出的 blocks（含行级 lines 元信息）+ translations，
输出 layout 供 render 消费。纯几何/文本驱动，不依赖截图/多模态。
"""
from __future__ import annotations

import statistics
from pathlib import Path

from common import trans_text

# CJK 字体候选（常规）
CJK_FONTS = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]
# CJK 字体候选（粗体，标题用）
CJK_FONTS_BOLD = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",  # 退化为常规
]

# 行首禁则标点（不放行首）
CLOSE_PUNCT = "。，、；：！？）》」』】〕.,;:!?)>\"'"

ALIGN_TOL = 3.0  # 对齐判定方差阈值（pt）


def _get_fitz():
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError:
        import fitz  # type: ignore
    return fitz


def _first_exists(paths):
    return next((p for p in paths if Path(p).exists()), None)


def _int_to_rgb(color_int):
    c = int(color_int)
    return ((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0


def is_toc_block(block: dict, col_w: float) -> bool:
    """检测目录 block：多数行末尾为页码数字、且去页码后仍有标题文本（字母/中文）。"""
    import re
    lines = block.get("lines") or []
    if not lines:
        return False
    num_tail = 0
    has_title = 0
    for l in lines:
        txt = (l.get("text") or "").strip()
        if not txt:
            continue
        if re.search(r"\d+$", txt):
            num_tail += 1
        title = re.sub(r"\s*\d+$", "", txt).strip()
        if title and re.search(r"[A-Za-z一-鿿]", title):
            has_title += 1
    total = len(lines)
    return total >= 1 and num_tail / total >= 0.5 and has_title / total >= 0.5


def detect_alignment(block: dict, col_left: float, col_right: float) -> str:
    """基于行级 lines 的 x0/x1/center 方差识别对齐方式。

    多行：两端对齐（排除末行后 x0/x1 都齐）/左对齐/右对齐/居中。
    单行：按列边界（col_left/col_right）判定右对齐/居中。
    """
    lines = block.get("lines") or []
    rows = [(float(l["x0"]), float(l["x1"])) for l in lines]
    if len(rows) >= 2:
        # 两端对齐：排除末行（末行通常不齐），看 inner 行 x0/x1 是否都齐
        inner = rows[:-1] if len(rows) >= 3 else rows
        x0_inner = [r[0] for r in inner]
        x1_inner = [r[1] for r in inner]
        if statistics.pstdev(x0_inner) < ALIGN_TOL and statistics.pstdev(x1_inner) < ALIGN_TOL:
            return "justify"
        x0_all = [r[0] for r in rows]
        x1_all = [r[1] for r in rows]
        cen_all = [(r[0] + r[1]) / 2 for r in rows]
        if statistics.pstdev(x0_all) < ALIGN_TOL:
            return "left"
        if statistics.pstdev(x1_all) < ALIGN_TOL:
            return "right"
        if statistics.pstdev(cen_all) < ALIGN_TOL:
            return "center"
        return "left"
    if not rows:
        return "left"
    # 单行：按列边界判定
    x0, x1 = rows[0]
    cen = (x0 + x1) / 2
    w = x1 - x0
    col_w = col_right - col_left
    if abs(x1 - col_right) < 15 and w < col_w * 0.6:
        return "right"
    if abs(cen - (col_left + col_right) / 2) < 15:
        return "center"
    return "left"


def wrap_cjk(text: str, font, fs: float, rect_w: float) -> list[str]:
    """按中文词/标点边界换行，行首禁则（闭合标点不放行首）。"""
    lines: list[str] = []
    for seg in text.split("\n"):
        if not seg:
            lines.append("")
            continue
        cur = ""
        for ch in seg:
            cand = cur + ch
            if font.text_length(cand, fs) > rect_w and cur:
                if ch in CLOSE_PUNCT:  # 禁则：闭合标点留本行末（轻微超宽可接受）
                    cur = cand
                    continue
                lines.append(cur)
                cur = ch
            else:
                cur = cand
        lines.append(cur)
    return lines


def wrap_segments(segments: list[dict], font, text_fs: float, rect_w: float) -> list[list[dict]]:
    """按 segment 类型流式换行，返回 [line, ...]，line = [run, ...]。

    run = {text, type, size}：text 段用 text_fs 逐字 CJK 换行（行首禁则）；
    formula 段用原字号、作为原子单位不拆分，放不下整体移到下一行。
    供含行内公式的 block 生成 run 级 lines，渲染时 formula 不被换行/拉伸。
    """
    lines: list[list[dict]] = []
    cur_runs: list[dict] = []
    cur_w = 0.0
    pending = ""  # 累积的 text 字符（合并为单个 text run）

    def flush_text() -> None:
        nonlocal pending
        if pending:
            cur_runs.append({"text": pending, "type": "text", "size": text_fs})
            pending = ""

    def new_line() -> None:
        nonlocal cur_runs, cur_w
        flush_text()
        if cur_runs:
            lines.append(cur_runs)
        cur_runs = []
        cur_w = 0.0

    for seg in segments:
        stype = seg.get("type", "text")
        stext = seg.get("text", "")
        if stype == "formula":
            flush_text()
            fsize = float(seg.get("size", text_fs))
            fw = font.text_length(stext, fsize)
            if (cur_runs or pending) and cur_w + fw > rect_w:
                new_line()
            cur_runs.append({"text": stext, "type": "formula", "size": fsize})
            cur_w += fw
        else:
            for ch in stext:
                if ch == "\n":
                    new_line()
                    continue
                cw = font.text_length(ch, text_fs)
                if (cur_runs or pending) and cur_w + cw > rect_w and ch not in CLOSE_PUNCT:
                    new_line()
                pending += ch
                cur_w += cw
    new_line()
    return lines


def _fit_fs(font, text, rect_w, rect_h, min_fs, max_fs, line_h_factor=1.25):
    """二分查找适配矩形的最大字号（下限 min_fs），返回 (fs, lines)。"""
    lo, hi = min_fs, max(max_fs, min_fs)
    best_fs, best_lines = min_fs, wrap_cjk(text, font, min_fs, rect_w)
    for _ in range(20):
        if hi - lo < 0.2:
            break
        mid = (lo + hi) / 2
        lines = wrap_cjk(text, font, mid, rect_w)
        if len(lines) * mid * line_h_factor <= rect_h:
            best_fs, best_lines = mid, lines
            lo = mid
        else:
            hi = mid
    return best_fs, best_lines


def plan_fontsize(block, font, trans, rect_w, rect_h, y0, next_below_y0):
    """字号策略：下限 max(7, 原字号*0.7)；优先用原文行高系数保留更大字号（标题）；
    塞不下时向下扩展，不覆盖下方 block。

    返回 (fs, lines, ext_y1, line_h_factor)。ext_y1=None 表示无需扩展。
    line_h_factor 为渲染行高系数（单行原文用其实际系数，多行用 1.25）。
    """
    max_fs = float(block.get("size", 12.0))
    min_fs = max(7.0, max_fs * 0.7)
    # 原文行高系数：bbox 高 / 字号（单行原文≈1.0，多行≈1.25），clamp [1.0, 1.25]
    orig_h = block["bbox"][3] - block["bbox"][1]
    orig_lhf = max(1.0, min(1.25, orig_h / max_fs)) if max_fs > 0 else 1.25
    # 先用原行高系数尝试（保留更大字号，适合单行标题/短行）
    fs, lines = _fit_fs(font, trans, rect_w, rect_h, min_fs, max_fs, orig_lhf)
    if len(lines) * fs * orig_lhf <= rect_h:
        return fs, lines, None, orig_lhf
    # 塞不下：用标准 1.25 重试（多行情况）
    fs, lines = _fit_fs(font, trans, rect_w, rect_h, min_fs, max_fs, 1.25)
    total_h = len(lines) * fs * 1.25
    if total_h <= rect_h:
        return fs, lines, None, 1.25
    # 仍塞不下：向下扩展
    needed_h = total_h
    if next_below_y0 is None:
        return fs, lines, y0 + needed_h, 1.25  # 下方无 block，自由扩展
    max_y1 = next_below_y0 - 1
    avail_h = max_y1 - y0
    if avail_h >= needed_h:
        return fs, lines, y0 + needed_h, 1.25
    # 受限：在 avail_h 内重算字号
    fs2, lines2 = _fit_fs(font, trans, rect_w, avail_h, min_fs, max_fs, 1.25)
    if len(lines2) * fs2 * 1.25 <= avail_h:
        return fs2, lines2, max_y1, 1.25
    # 仍塞不下：min_fs + 截断渲染
    fs3, lines3 = _fit_fs(font, trans, rect_w, avail_h, min_fs, min_fs, 1.25)
    return fs3, lines3, max_y1, 1.25


def plan_font_style(block, med_size, cjk_regular, cjk_bold):
    """字体风格：标题（字号>med*1.4）用粗体，否则常规。引言斜体映射留待字体支持。

    返回 (fontfile, fontname)。
    """
    size = float(block.get("size", 12.0))
    font_name = block.get("font", "")
    is_title = size > med_size * 1.3 or "bold" in font_name.lower()
    if is_title and cjk_bold:
        return cjk_bold, "cjk-bold"
    return cjk_regular, "cjk"


def layout_page(blocks, translations, page_width, cjk_regular_path, cjk_bold_path):
    """规划单页排版：返回 {block_id: layout_dict}。

    layout_dict: {alignment, fontsize, lines, fontname, fontfile, color, rect}
    rect 为渲染区域 [x0,y0,x1,y1]（含向下扩展后的 y1）。
    """
    fitz = _get_fitz()
    font_reg = fitz.Font(fontfile=cjk_regular_path)
    font_bold = fitz.Font(fontfile=cjk_bold_path) if cjk_bold_path else font_reg
    text_blocks = [
        b for b in blocks
        if b.get("type") == "text" and b["id"] in translations and trans_text(translations[b["id"]])
    ]
    if not text_blocks:
        return {}
    sizes = sorted(float(b.get("size", 12.0)) for b in text_blocks)
    med = sizes[len(sizes) // 2] if sizes else 12.0
    # 列边界：多行 block inner 行 x0 最小、x1 最大（单行 block 对齐判定用）
    multi = [b for b in text_blocks if len(b.get("lines", [])) >= 2]
    col_left, col_right = 0.0, page_width
    if multi:
        x0s, x1s = [], []
        for b in multi:
            rows = b["lines"][:-1] if len(b["lines"]) >= 3 else b["lines"]
            x0s += [float(l["x0"]) for l in rows]
            x1s += [float(l["x1"]) for l in rows]
        if x0s and x1s:
            col_left, col_right = min(x0s), max(x1s)
    # 按 y0 排序，便于找下方相邻 block
    text_blocks_sorted = sorted(text_blocks, key=lambda b: b["bbox"][1])
    layout = {}
    for i, b in enumerate(text_blocks_sorted):
        trans_obj = translations[b["id"]]
        trans = trans_text(trans_obj)
        segments = trans_obj.get("segments") if isinstance(trans_obj, dict) else None
        has_formula = bool(segments) and any(s.get("type") == "formula" for s in segments)
        rect = b["bbox"]
        inset_w = max(rect[2] - rect[0] - 2, 1)
        rect_h = rect[3] - rect[1]  # 上下不 inset，单行标题保留原字号空间
        y0 = rect[1]
        # 下方最近 block 的 y0（避免扩展覆盖）
        next_below_y0 = None
        for nb in text_blocks_sorted[i + 1:]:
            if nb["bbox"][1] >= rect[3] - 1:
                next_below_y0 = nb["bbox"][1]
                break
        font_path, fontname = plan_font_style(b, med, cjk_regular_path, cjk_bold_path)
        font = font_bold if fontname == "cjk-bold" else font_reg
        if is_toc_block(b, col_right - col_left):
            alignment = "toc"
        else:
            alignment = detect_alignment(b, col_left, col_right)
        fs, lines, ext_y1, lhf = plan_fontsize(b, font, trans, inset_w, rect_h, y0, next_below_y0)
        y1_out = ext_y1 if ext_y1 is not None else rect[3]
        entry = {
            "alignment": alignment,
            "fontsize": round(fs, 2),
            "lines": lines,
            "fontname": fontname,
            "fontfile": font_path,
            "color": _int_to_rgb(b.get("color", 0)),
            "rect": [rect[0] + 1, rect[1], rect[2] - 1, y1_out],
            "line_h_factor": round(lhf, 3),
        }
        # 含行内公式：生成 run 级 lines，formula 原字号原子不换行，渲染差异化
        if has_formula:
            entry["runs"] = wrap_segments(segments, font, fs, inset_w)
        layout[b["id"]] = entry
    return layout
