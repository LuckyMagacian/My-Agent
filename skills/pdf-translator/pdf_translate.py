#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pymupdf",
#   "openai",
# ]
# ///
"""pdf-translator: 将文档型 PDF 原位翻译为指定语言（默认中文），保留页面排版。

流程：extract（PyMuPDF 提取文本块）-> translate（OpenAI 协议 API）-> render（原位覆盖 + CJK 字体 + 字号自适应）。

模块拆分：
- common.py    共享工具（_get_fitz、parse_pages）
- config.py    配置（load_config、_print_config）
- extractor.py 抽取
- translator.py 翻译
- renderer.py  排版
- 本文件       CLI 入口（build_parser、main）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import layout as layout_mod
except ImportError:  # pragma: no cover
    layout_mod = None

from common import _get_fitz, parse_pages
from config import DEFAULT_CONFIG_PATH, _print_config, load_config
from extractor import extract, extract_page
from renderer import render, render_page
from translator import translate, translate_page


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    p = argparse.ArgumentParser(
        prog="pdf_translate.py",
        description="将文档型 PDF 原位翻译为指定语言（默认中文），保留页面排版。",
    )
    p.add_argument("input", nargs="?", help="输入 PDF 路径")
    p.add_argument("--output", "-o", help="输出 PDF 路径（默认 <input>.<lang>.pdf）")
    p.add_argument("--lang", default="zh", help="目标语言（默认 zh）")
    p.add_argument("--pages", help="页码范围，如 1-5,8（默认全部）")
    p.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="配置文件路径")
    p.add_argument("--extract-only", action="store_true", help="仅提取文本块为 JSON，不翻译")
    p.add_argument("--translate-only", action="store_true", help="从 extract JSON 读取并翻译为译文 JSON（input 为 JSON 路径）")
    p.add_argument("--render-only", action="store_true", help="从 extract JSON + 译文 JSON 渲染 PDF（input 为原 PDF 路径）")
    p.add_argument("--layout-only", action="store_true", help="从 extract JSON + 译文 JSON 规划排版 layout JSON（input 为原 PDF）")
    p.add_argument("--layout", help="render-only 时的 layout JSON 路径（默认 <input>.layout.json）")
    p.add_argument("--blocks", help="render-only 时的 extract JSON 路径（默认 <input>.extract.json）")
    p.add_argument("--trans", help="render-only 时的译文 JSON 路径（默认 <input>.trans.json）")
    p.add_argument("--out", help="调试模式 JSON/中间产物输出路径")
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：按参数分发 extract/translate/render/全流程。"""
    args = build_parser().parse_args(argv)
    if not args.input:
        build_parser().print_help()
        return 0
    pdf_path = args.input
    if not Path(pdf_path).exists():
        print(f"[error] 输入文件不存在: {pdf_path}", file=sys.stderr)
        return 2
    config = load_config(Path(args.config))
    config["target_lang"] = args.lang

    if args.extract_only:
        blocks = extract(pdf_path, args.pages)
        out_path = args.out or (str(Path(pdf_path).with_suffix("")) + ".extract.json")
        Path(out_path).write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
        pages_set = {b["page"] for b in blocks}
        text_n = sum(1 for b in blocks if b.get("type") == "text")
        img_n = sum(1 for b in blocks if b.get("type") == "image")
        print(
            f"[info] 提取完成: {len(blocks)} 块（文本 {text_n} / 图片 {img_n}），"
            f"覆盖 {len(pages_set)} 页 -> {out_path}"
        )
        return 0

    if args.translate_only:
        blocks = json.loads(Path(pdf_path).read_text(encoding="utf-8"))
        _print_config(config)
        translations = translate(blocks, config)
        out_path = args.out or (str(Path(pdf_path).with_suffix("")) + ".trans.json")
        Path(out_path).write_text(json.dumps(translations, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[info] 翻译完成: {len(translations)} 条 -> {out_path}")
        return 0

    if args.render_only:
        blocks_path = args.blocks or (str(Path(pdf_path).with_suffix("")) + ".extract.json")
        trans_path = args.trans or (str(Path(pdf_path).with_suffix("")) + ".trans.json")
        blocks = json.loads(Path(blocks_path).read_text(encoding="utf-8"))
        translations = json.loads(Path(trans_path).read_text(encoding="utf-8"))
        out_path = args.output or (str(Path(pdf_path).with_suffix("")) + f".{args.lang}.pdf")
        render(pdf_path, blocks, translations, out_path)
        print(f"[info] 渲染完成 -> {out_path}")
        return 0

    if args.layout_only:
        if layout_mod is None:
            raise RuntimeError("未找到 layout 模块（应与 pdf_translate.py 同目录）")
        blocks_path = args.blocks or (str(Path(pdf_path).with_suffix("")) + ".extract.json")
        trans_path = args.trans or (str(Path(pdf_path).with_suffix("")) + ".trans.json")
        blocks_all = json.loads(Path(blocks_path).read_text(encoding="utf-8"))
        translations = json.loads(Path(trans_path).read_text(encoding="utf-8"))
        fitz = _get_fitz()
        doc = fitz.open(pdf_path)
        cjk_reg = layout_mod._first_exists(layout_mod.CJK_FONTS)
        cjk_bold = layout_mod._first_exists(layout_mod.CJK_FONTS_BOLD)
        by_page: dict[int, list[dict]] = {}
        for b in blocks_all:
            by_page.setdefault(b["page"], []).append(b)
        layout_by_page: dict[str, dict] = {}
        for pno, pg_blocks in by_page.items():
            page_width = doc[pno].rect.width
            layout_by_page[f"p{pno}"] = layout_mod.layout_page(pg_blocks, translations, page_width, cjk_reg, cjk_bold)
        doc.close()
        out_path = args.out or (str(Path(pdf_path).with_suffix("")) + ".layout.json")
        Path(out_path).write_text(json.dumps(layout_by_page, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[info] 排版规划完成: {sum(len(v) for v in layout_by_page.values())} 块 -> {out_path}")
        return 0

    # 完整流程：页级 extract -> translate -> layout -> render
    if layout_mod is None:
        raise RuntimeError("未找到 layout 模块（应与 pdf_translate.py 同目录）")
    _print_config(config)
    fitz = _get_fitz()
    doc = fitz.open(pdf_path)
    total = doc.page_count
    page_indices = parse_pages(args.pages, total) or list(range(total))
    cjk_reg = layout_mod._first_exists(layout_mod.CJK_FONTS)
    cjk_bold = layout_mod._first_exists(layout_mod.CJK_FONTS_BOLD)
    if not cjk_reg:
        doc.close()
        raise RuntimeError("未找到 CJK 字体（Songti.ttc/Hiragino Sans GB/STHeiti）")
    cjk_font = fitz.Font(fontfile=cjk_reg)
    cjk_font_bold = fitz.Font(fontfile=cjk_bold) if cjk_bold else cjk_font
    output = args.output or (str(Path(pdf_path).with_suffix("")) + f".{args.lang}.pdf")
    total_trans = 0
    for idx, pno in enumerate(page_indices, 1):
        print(f"[info] 第 {idx}/{len(page_indices)} 页（页码 {pno+1}）：提取->翻译->排版->渲染...", file=sys.stderr)
        blocks = extract_page(doc, pno)
        trans = translate_page(blocks, config)
        total_trans += len(trans)
        page_width = doc[pno].rect.width
        lay = layout_mod.layout_page(blocks, trans, page_width, cjk_reg, cjk_bold)
        render_page(doc[pno], blocks, trans, lay, cjk_font, cjk_font_bold, fitz)
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    print(f"[info] 译文 PDF（页级流水线，{total_trans} 条）: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
