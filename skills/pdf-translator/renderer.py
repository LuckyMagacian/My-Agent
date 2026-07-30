"""pdf-translator 排版：原位覆盖原文 + CJK 字体 + 字号自适应换行渲染译文。"""
from __future__ import annotations

import re
from pathlib import Path

from common import _get_fitz, trans_text

# CJK 字体候选（render 使用），按优先级
CJK_FONTS = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]


def _int_to_rgb(color_int: int) -> tuple[float, float, float]:
    """PyMuPDF 颜色整数（sRGB 打包）转 (r,g,b) 0-1。"""
    c = int(color_int)
    return ((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0


def _fit_fontsize(
    font, text: str, rect_w: float, rect_h: float, max_fs: float, min_fs: float = 4.0
) -> tuple[float, list[str]]:
    """二分查找适配矩形最大字号，返回 (fontsize, lines)。逐字符按宽度换行。"""
    def wrap(fs: float) -> list[str]:
        lines: list[str] = []
        for seg in text.split("\n"):
            if not seg:
                lines.append("")
                continue
            cur = ""
            for ch in seg:
                cand = cur + ch
                if cur and font.text_length(cand, fs) > rect_w:
                    lines.append(cur)
                    cur = ch
                else:
                    cur = cand
            if cur:
                lines.append(cur)
        return lines

    def total_h(fs: float) -> float:
        return len(wrap(fs)) * fs * 1.25

    lo, hi = min_fs, max(max_fs, min_fs)
    best_fs, best_lines = min_fs, wrap(min_fs)
    for _ in range(20):
        if hi - lo < 0.2:
            break
        mid = (lo + hi) / 2
        if total_h(mid) <= rect_h:
            best_fs, best_lines = mid, wrap(mid)
            lo = mid
        else:
            hi = mid
    return best_fs, best_lines


def _insert_justified_line(page, line, x0, x1, y, fs, fontname, fontfile, color, font):
    """两端对齐：逐字符均匀分布间距填满 [x0, x1]。"""
    if len(line) <= 1:
        page.insert_text((x0, y), line, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
        return
    char_w = [font.text_length(ch, fs) for ch in line]
    sum_w = sum(char_w)
    target_w = x1 - x0
    if sum_w >= target_w:
        page.insert_text((x0, y), line, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
        return
    gap = (target_w - sum_w) / (len(line) - 1)
    x = x0
    for i, ch in enumerate(line):
        page.insert_text((x, y), ch, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
        x += char_w[i] + gap


def _insert_toc_line(page, line, x0, x1, y, fs, fontname, fontfile, color, font):
    """目录条目：标题左对齐 + 页码右对齐到 x1。"""
    m = re.match(r"^(.*?)(\s+)(\d+)$", line.strip())
    if m:
        title = m.group(1).rstrip()
        page_num = m.group(3)
        page.insert_text((x0, y), title, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
        pw = font.text_length(page_num, fs)
        page.insert_text((x1 - pw, y), page_num, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
    else:
        page.insert_text((x0, y), line, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)


def _place_runs_left(page, runs, widths, x, y, fontname, fontfile, color):
    """runs 从 x 起逐个左排，各 run 用自身 size。"""
    for r, w in zip(runs, widths):
        page.insert_text((x, y), r["text"], fontsize=r["size"],
                         fontname=fontname, fontfile=fontfile, color=color)
        x += w


def _place_runs_justify(page, runs, widths, x0, target, total, y,
                        fontname, fontfile, color, font):
    """两端对齐：仅拉伸 text run 内部字符间距，formula run 固定宽度不拉伸。"""
    extra = target - total
    text_gaps = sum(max(0, len(r["text"]) - 1) for r in runs if r["type"] == "text")
    gap = extra / text_gaps if text_gaps > 0 else 0.0
    x = x0
    for r, w in zip(runs, widths):
        if r["type"] == "text" and gap > 0 and len(r["text"]) > 1:
            chars = list(r["text"])
            for j, ch in enumerate(chars):
                page.insert_text((x, y), ch, fontsize=r["size"],
                                 fontname=fontname, fontfile=fontfile, color=color)
                x += font.text_length(ch, r["size"])
                if j < len(chars) - 1:
                    x += gap
        else:
            page.insert_text((x, y), r["text"], fontsize=r["size"],
                             fontname=fontname, fontfile=fontfile, color=color)
            x += w


def _render_runs_line(page, runs, x0, x1, y, fontname, fontfile, color, font, align, is_last):
    """渲染一条 run 级行：text run 用 CJK+规划字号，formula run 用原字号、不拉伸。"""
    widths = [font.text_length(r["text"], r["size"]) for r in runs]
    total = sum(widths)
    target = x1 - x0
    if align == "center":
        _place_runs_left(page, runs, widths, x0 + max(0, (target - total) / 2), y,
                         fontname, fontfile, color)
    elif align == "right":
        _place_runs_left(page, runs, widths, x0 + max(0, target - total), y,
                         fontname, fontfile, color)
    elif align == "justify" and not is_last and 0 < total < target:
        _place_runs_justify(page, runs, widths, x0, target, total, y,
                            fontname, fontfile, color, font)
    else:  # left / justify 末行 / toc
        _place_runs_left(page, runs, widths, x0, y, fontname, fontfile, color)


def render_page(page, page_blocks, translations, layout, cjk_font, cjk_font_bold, fitz):
    """渲染单页：redact 原文区域 + 按 layout 渲染译文（对齐/字号/换行/字体）。

    layout 为 {block_id: {alignment,fontsize,lines,fontname,fontfile,color,rect}}。
    无 layout 的块跳过（调用方保证 layout 覆盖待渲染块）。
    """
    text_blocks = [
        b for b in page_blocks
        if b.get("type") == "text" and b["id"] in translations and trans_text(translations[b["id"]])
    ]
    if not text_blocks:
        return
    for b in text_blocks:
        page.add_redact_annot(fitz.Rect(b["bbox"]), fill=(1, 1, 1))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    for b in text_blocks:
        lay = layout.get(b["id"])
        if not lay:
            continue
        rect = fitz.Rect(lay["rect"])
        fs = lay["fontsize"]
        color = lay["color"]
        fontname = lay["fontname"]
        fontfile = lay["fontfile"]
        font = cjk_font_bold if fontname == "cjk-bold" else cjk_font
        line_h = fs * lay.get("line_h_factor", 1.25)
        y = rect.y0 + fs
        runs_lines = lay.get("runs")
        if runs_lines:
            for li, runs in enumerate(runs_lines):
                if y - fs > rect.y1:
                    break
                _render_runs_line(page, runs, rect.x0, rect.x1, y, fontname, fontfile,
                                  color, font, lay["alignment"], li == len(runs_lines) - 1)
                y += line_h
            continue
        lines = lay["lines"]
        for li, line in enumerate(lines):
            if y - fs > rect.y1:
                break
            is_last = li == len(lines) - 1
            align = lay["alignment"]
            if align == "center":
                w = font.text_length(line, fs)
                page.insert_text((rect.x0 + (rect.width - w) / 2, y), line,
                    fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
            elif align == "right":
                w = font.text_length(line, fs)
                page.insert_text((rect.x1 - w, y), line,
                    fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
            elif align == "toc":
                _insert_toc_line(page, line, rect.x0, rect.x1, y, fs,
                    fontname, fontfile, color, font)
            elif align == "justify" and not is_last and len(line) > 1:
                if font.text_length(line, fs) >= rect.width * 0.85:
                    _insert_justified_line(page, line, rect.x0, rect.x1, y, fs,
                        fontname, fontfile, color, font)
                else:
                    page.insert_text((rect.x0, y), line,
                        fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
            else:  # left 或 justify 末行
                page.insert_text((rect.x0, y), line,
                    fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
            y += line_h


def render(pdf_path: str, blocks: list[dict], translations: dict[str, str], output: str) -> str:
    """原位 redact 原文 + 写入中文（CJK 字体 + 字号自适应换行），保留图片。"""
    fitz = _get_fitz()
    cjk_path = next((p for p in CJK_FONTS if Path(p).exists()), None)
    if not cjk_path:
        raise RuntimeError("未找到 CJK 字体（Songti.ttc/Hiragino Sans GB/STHeiti）")
    cjk_font = fitz.Font(fontfile=cjk_path)
    cjk_fontname = "cjk"
    doc = fitz.open(pdf_path)
    by_page: dict[int, list[dict]] = {}
    for b in blocks:
        by_page.setdefault(b["page"], []).append(b)
    for pno, page_blocks in by_page.items():
        page = doc[pno]
        text_blocks = [
            b for b in page_blocks
            if b.get("type") == "text" and b["id"] in translations and trans_text(translations[b["id"]])
        ]
        if not text_blocks:
            continue
        for b in text_blocks:
            page.add_redact_annot(fitz.Rect(b["bbox"]), fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        for b in text_blocks:
            trans_obj = translations[b["id"]]
            trans = trans_text(trans_obj)
            rect = fitz.Rect(b["bbox"])
            inset = fitz.Rect(rect.x0 + 1, rect.y0 + 1, rect.x1 - 1, rect.y1 - 1)
            if inset.width <= 0 or inset.height <= 0:
                inset = rect
            color = _int_to_rgb(b.get("color", 0))
            max_fs = float(b.get("size", 12.0))
            fs, lines = _fit_fontsize(cjk_font, trans, inset.width, inset.height, max_fs)
            line_h = fs * 1.25
            y = inset.y0 + fs
            segments = trans_obj.get("segments") if isinstance(trans_obj, dict) else None
            runs_lines = None
            if segments and any(s.get("type") == "formula" for s in segments):
                try:
                    from layout import wrap_segments
                    runs_lines = wrap_segments(segments, cjk_font, fs, inset.width)
                except Exception:  # noqa: BLE001
                    runs_lines = None
            if runs_lines:
                for ri, runs in enumerate(runs_lines):
                    if y - fs > inset.y1:
                        break
                    _render_runs_line(page, runs, inset.x0, inset.x1, y, cjk_fontname,
                                      cjk_path, color, cjk_font, "left", ri == len(runs_lines) - 1)
                    y += line_h
            else:
                for line in lines:
                    if y - fs > inset.y1:
                        break
                    page.insert_text(
                        (inset.x0, y), line, fontsize=fs,
                        fontname=cjk_fontname, fontfile=cjk_path, color=color,
                    )
                    y += line_h
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output
