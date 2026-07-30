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
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import layout as layout_mod
except ImportError:  # pragma: no cover
    layout_mod = None

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# CJK 字体候选（T4 render 使用），按优先级
CJK_FONTS = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """加载配置：环境变量优先 > config.json > 内置默认。"""
    cfg: dict[str, Any] = {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "THUDM/GLM-4-9B-0414",
        "api_key": "",
        "target_lang": "zh",
        "batch_size": 20,
        "max_chars_per_batch": 6000,
        "max_output_tokens": 8192,
        "context_overlap": 1,
    }
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 读取配置失败 {path}: {e}", file=sys.stderr)
    # 环境变量覆盖
    if os.getenv("OPENAI_API_KEY"):
        cfg["api_key"] = os.environ["OPENAI_API_KEY"]
    if os.getenv("OPENAI_BASE_URL"):
        cfg["base_url"] = os.environ["OPENAI_BASE_URL"]
    if os.getenv("OPENAI_MODEL"):
        cfg["model"] = os.environ["OPENAI_MODEL"]
    if os.getenv("TARGET_LANG"):
        cfg["target_lang"] = os.environ["TARGET_LANG"]
    return cfg


def _get_fitz():
    """惰性导入 PyMuPDF，兼容 pymupdf / fitz 两种模块名。"""
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError:  # pragma: no cover
        import fitz  # type: ignore
    return fitz


def extract_page(doc, pno: int) -> list[dict]:
    """提取单页文本块（含行级 lines 元信息），区分图片。

    使用 PyMuPDF 的 dict 模式，按 block 输出，保留阅读顺序。
    每个文本块含 bbox/font/size/color/text/lines（行级 {x0,y0,x1,y1,text}），
    lines 供排版阶段做对齐识别。图片块仅记录 bbox。
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
        # 收集每个非空 line 的几何信息：(y0, y1, x0, x1, text)
        line_infos: list[tuple[float, float, float, float, str]] = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_text = "".join(s.get("text", "") for s in spans)
            if line_text.strip():
                lbbox = line.get("bbox", [0, 0, 0, 0])
                line_infos.append(
                    (float(lbbox[1]), float(lbbox[3]), float(lbbox[0]), float(lbbox[2]), line_text)
                )
            for s in spans:
                txt = s.get("text", "")
                if not txt:
                    continue
                cnt = len(txt)
                size_counter[round(float(s.get("size", 12.0)), 2)] += cnt
                font_counter[s.get("font", "")] += cnt
                color_counter[int(s.get("color", 0))] += cnt
        # 同一视觉行的 line 按 x 顺序用空格连接，不同视觉行用 \n。
        # PyMuPDF 常把目录/页眉等 x 不连续的同行文本拆成多 line，直接 \n 连接
        # 会把一行误变多行，故按 y 区间重叠判定真实视觉行。
        line_infos.sort(key=lambda t: (t[0], t[2]))
        visual_rows: list[list[tuple[float, float, float, float, str]]] = []
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
        blocks_out.append({
            "page": pno,
            "id": f"p{pno}b{bidx}",
            "type": "text",
            "bbox": bbox,
            "font": dom_font,
            "size": dom_size,
            "color": dom_color,
            "text": text,
            "lines": lines_out,
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


def _print_config(config: dict) -> None:
    """打印生效配置（不打印 apikey）。"""
    print(
        f"[info] 配置: model={config.get('model')} "
        f"base_url={config.get('base_url')} lang={config.get('target_lang')}",
        flush=True,
    )


def translate(blocks: list[dict], config: dict) -> dict[str, str]:
    """按批调用 OpenAI 协议 API 翻译文本块，返回 {block_id: 译文}。

    图片块与空文本块跳过。按 seg_id 语义段不拆批，叠加 batch_size / 字符预算 /
    输出 token 预算分批；每批携带前文 seg 作参考上下文（滑动窗口），失败重试。
    """
    from openai import OpenAI

    lang_map = {"zh": "中文（简体）", "en": "English", "ja": "日本語"}
    lang_name = lang_map.get(config.get("target_lang", "zh"), config.get("target_lang", "zh"))
    batch_size = int(config.get("batch_size", 20))
    max_chars = int(config.get("max_chars_per_batch", 6000))
    max_out = int(config.get("max_output_tokens", 8192))
    out_budget = int(max_out * 0.8)  # 单批输出 token 预算，留余量防截断
    context_overlap = int(config.get("context_overlap", 1))
    text_blocks = [b for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
    if not text_blocks:
        return {}
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    # 按 seg_id 保序聚合成段组（同段 block 不拆批）；无 seg_id 时每块自成一组
    groups: list[list[dict]] = []
    cur_sid: object = object()  # 哨兵，保证首块开新组
    for b in text_blocks:
        sid = b.get("seg_id") or b["id"]
        if sid != cur_sid:
            groups.append([b])
            cur_sid = sid
        else:
            groups[-1].append(b)

    # 以段组为不可拆单元分批：块数 / 字符 / 输出 token 任一超限即切批
    batches: list[list[dict]] = []
    cur: list[dict] = []
    cur_chars = 0
    cur_out = 0
    for g in groups:
        g_chars = sum(len(b["text"]) for b in g)
        g_out = int(g_chars * 1.3)
        if cur and (
            len(cur) + len(g) > batch_size
            or cur_chars + g_chars > max_chars
            or cur_out + g_out > out_budget
        ):
            batches.append(cur)
            cur, cur_chars, cur_out = [], 0, 0
        cur.extend(g)
        cur_chars += g_chars
        cur_out += g_out
    if cur:
        batches.append(cur)

    translations: dict[str, str] = {}
    total = len(batches)
    prev_ctx: list[dict] = []  # 上一批末尾段组（滑动窗口上下文来源）
    for i, batch in enumerate(batches, 1):
        items = [{"id": b["id"], "text": b["text"], "font": b.get("font", "")} for b in batch]
        ctx = _build_context(prev_ctx, context_overlap)
        print(
            f"[translate] 批次 {i}/{total}（{len(items)} 块，上下文 {len(ctx)} 块）...",
            file=sys.stderr,
        )
        translations.update(_translate_batch(client, config, items, lang_name, ctx))
        prev_ctx = _tail_group(batch)
    return translations


def translate_page(blocks: list[dict], config: dict) -> dict[str, str]:
    """页级翻译：对单页 blocks 翻译，保留原 seg 滑动窗口上下文（页内批间传递）。

    与 translate 等价，仅限单页 blocks 传入；滑动窗口上下文在页内批间衔接，
    不跨页（跨页信息由排版阶段使用）。供页级流水线调用。
    """
    return translate(blocks, config)


def _tail_group(batch: list[dict]) -> list[dict]:
    """取一批末尾连续同 seg_id 的 block，作为下一批的滑动窗口上下文来源。"""
    if not batch:
        return []
    last_sid = batch[-1].get("seg_id")
    if last_sid is None:
        return [batch[-1]]  # 退化：无 seg_id，每块自成一组
    tail = [batch[-1]]
    for b in reversed(batch[:-1]):
        if b.get("seg_id") == last_sid:
            tail.append(b)
        else:
            break
    return list(reversed(tail))


def _build_context(ctx_blocks: list[dict], overlap: int) -> list[dict]:
    """构造滑动窗口上下文：取末尾段组的 block，总字符限 2000 防膨胀。

    overlap=0 关闭上下文。返回 [{id,text}] 供 LLM 参考（不翻译）。
    """
    if overlap <= 0 or not ctx_blocks:
        return []
    ctx: list[dict] = []
    chars = 0
    for b in reversed(ctx_blocks):
        if chars + len(b["text"]) > 2000:
            break
        ctx.insert(0, {"id": b["id"], "text": b["text"]})
        chars += len(b["text"])
    return ctx


def _looks_truncated(content: str) -> bool:
    """启发式判断模型输出是否被 max_tokens 截断（JSON 末尾未闭合）。"""
    if not content:
        return False
    c = content.rstrip()
    if c.endswith("```"):  # 围栏闭合，非截断
        return False
    return not (c.endswith("}") or c.endswith("]"))


# 等宽代码字体与数学公式字体的名称特征（小写子串匹配）。
# 代码字体原样保留（代码不应翻译）；数学字体为公式符号，亦不应翻译。
_NONTRANSL_FONT_PATTERNS = (
    # 等宽 / 代码字体
    "lettergothic", "courier", "mono", "menlo", "monaco", "consolas", "inconsolata",
    "source code", "fira code", "jetbrains", "lucida console", "andale",
    "dejavu sans mono", "noto sans mono", "ubuntu mono", "robotomono",
    "typewriter", "prestige", "ocr",
    # 数学公式字体（TeX / MathTime 符号字体）
    "mtex", "mtsyn", "mtmi", "mtmub", "msam", "msbm", "cmsy", "cmmi", "cmex", "esint", "wasy",
)


def _is_nontranslatable_font(font: str) -> bool:
    """判断字体是否为代码/数学字体（此类块不应翻译，原样返回属正确行为）。"""
    f = (font or "").lower()
    return any(p in f for p in _NONTRANSL_FONT_PATTERNS)


def _looks_like_code(text: str) -> bool:
    """保守启发式：两行及以上以 ; { } 结尾视为代码（散文几乎不会）。

    字体未知或为比例字体时的兜底；主信号见 _is_nontranslatable_font。
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    strong_end = sum(1 for ln in lines if ln.rstrip().endswith((";", "{", "}")))
    return strong_end >= 2


def _is_translatable(text: str, font: str = "") -> bool:
    """判断文本是否为可翻译的英文正文（长度 > 30 且拉丁字母占比 > 60%）。

    短文本（人名/标题/专有名词）保留原文属合理行为，不判未翻译。
    代码/数学字体块或明显代码文本原样返回属正确行为，不判未翻译。
    """
    if len(text.strip()) <= 30:
        return False
    if _is_nontranslatable_font(font) or _looks_like_code(text):
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = [c for c in letters if c.isascii()]
    return len(latin) / len(letters) > 0.6


def _translate_batch(
    client,
    config: dict,
    items: list[dict],
    lang_name: str,
    context: list[dict] | None = None,
    max_retries: int = 5,
    depth: int = 0,
) -> dict[str, str]:
    """翻译单批，返回 {id: 译文}。

    携带 context 参考上下文（不翻译）；max_tokens 按批动态估算；
    输出截断时二分降批自愈（depth≤2），网络/解析错误走 max_retries 重试。
    """
    model = config["model"]
    sys_prompt = (
        f"你是专业翻译。将给定文本块翻译为{lang_name}。要求："
        "1) 译文准确、自然、符合原意与语气；"
        "2) 译文尽量简洁以适配原排版；"
        "3) 仅代码、变量名、数字、数学公式符号保持原样不翻译；完整句子与段落必须翻译为中文，不得原样返回原文；"
        "4) 输入为 JSON 数组，元素形如 {\"id\":\"...\",\"text\":\"...\"}；"
        "仅返回 JSON 对象，键为每个元素的 id、值为译文，例如 {\"p1b0\":\"译文\"}；"
        "必须覆盖全部 id，不得遗漏；"
        "禁止数组、禁止 markdown 围栏、禁止额外说明。"
    )
    if context:
        sys_prompt += (
            "5) 用户消息开头的【上文参考】段落仅供理解指代与术语，"
            "不得翻译、其 id 不得出现在返回结果中。"
        )
    # 发往 API 的负载仅含 id/text，剥离 font 等元信息
    api_items = [{"id": it["id"], "text": it["text"]} for it in items]
    # context 作为 user 前缀参考文本；items 保持数组（兼容模型原输入格式，降低漏译）
    if context:
        ctx_lines = "\n".join(f"[{c['id']}] {c['text']}" for c in context)
        user_text = (
            "【上文参考，勿翻译】\n" + ctx_lines
            + "\n\n【待译，请逐条翻译并返回全部 id】\n"
            + json.dumps(api_items, ensure_ascii=False)
        )
    else:
        user_text = json.dumps(api_items, ensure_ascii=False)
    ids = {it["id"] for it in items}
    est_out = int(sum(len(it["text"]) for it in items) * 1.3)
    max_tokens = max(1024, min(est_out + 512, int(config.get("max_output_tokens", 8192))))
    last_err: Exception | None = None
    last_parsed: dict[str, str] = {}
    content = ""
    finish_reason = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            choice = resp.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            content = (choice.message.content or "").strip()
            parsed = _parse_translation_json(content)
            last_parsed = parsed
            # 兜底：代码块缺失时回退原文（代码不应翻译，原样即正确），
            # 避免模型漏掉代码块导致"译文缺失 id"失败。
            for it in items:
                if it["id"] not in parsed and (
                    _is_nontranslatable_font(it.get("font", "")) or _looks_like_code(it["text"])
                ):
                    parsed[it["id"]] = it["text"]
            missing = [it["id"] for it in items if it["id"] not in parsed]
            if missing:
                raise ValueError(f"译文缺失 id: {missing[:5]}")
            # 未翻译检测：译文=原文且原文可翻译（英文为主）-> 视为未翻译
            untranslated = [
                it["id"] for it in items
                if it["id"] in parsed and parsed[it["id"]].strip() == it["text"].strip()
                and _is_translatable(it["text"], it.get("font", ""))
            ]
            if untranslated:
                # 整批原样返回：视为模型整体失败，走重试/降批自愈
                if len(untranslated) == len(items):
                    raise ValueError(f"整批未翻译 id: {untranslated[:5]}")
                # 部分原样返回：多为公式/符号等不应翻译内容，保留原文并告警，不中断
                for uid in untranslated:
                    print(
                        f"[translate] 警告: 块 {uid} 疑似不可翻译内容（公式/符号等），保留原文",
                        file=sys.stderr,
                    )
            return {k: v for k, v in parsed.items() if k in ids}
        except Exception as e:  # noqa: BLE001
            last_err = e
            # 自愈：截断立即降批；漏译重试>=2次降批；网络/解析错误只重试
            truncated = finish_reason == "length" or _looks_truncated(content)
            is_missing = isinstance(e, ValueError) and ("译文缺失" in str(e) or "整批未翻译" in str(e))
            do_split = depth < 2 and len(items) > 1 and (
                truncated or (is_missing and attempt >= 2)
            )
            if do_split:
                mid = len(items) // 2
                reason = "截断" if truncated else "漏译"
                print(
                    f"[translate] {reason}自愈（finish={finish_reason}），"
                    f"二分降批深度 {depth + 1}（{len(items)} -> {mid}+{len(items) - mid}）...",
                    file=sys.stderr,
                )
                left = _translate_batch(
                    client, config, items[:mid], lang_name, context, max_retries, depth + 1
                )
                right_ctx = (context or []) + [
                    {"id": it["id"], "text": it["text"]} for it in items[:mid]
                ]
                right = _translate_batch(
                    client, config, items[mid:], lang_name, right_ctx, max_retries, depth + 1
                )
                return {**left, **right}
            print(
                f"[translate] 重试 {attempt}/{max_retries}: {type(e).__name__}: {str(e)[:120]}",
                file=sys.stderr,
            )
    # 重试耗尽仍未成功：未译块回退原文并告警，避免单块中断全书翻译
    print(
        f"[translate] 警告: 批次重试 {max_retries} 次仍失败（{last_err}），未译块保留原文以继续",
        file=sys.stderr,
    )
    result = {it["id"]: (last_parsed.get(it["id"]) or it["text"]) for it in items}
    return {k: v for k, v in result.items() if k in ids}


def _parse_translation_json(content: str) -> dict[str, str]:
    """从模型输出解析 {id: 译文}，兼容围栏/额外文本/对象或数组/尾逗号。"""
    import re

    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content).strip()
    cleaned = re.sub(r",\s*([}\]])", r"\1", content)  # 容忍尾逗号
    idx_obj = cleaned.find("{")
    idx_arr = cleaned.find("[")
    candidates = [i for i in (idx_obj, idx_arr) if i != -1]
    if candidates:
        start = min(candidates)
        decoder = json.JSONDecoder()
        try:
            obj, _end = decoder.raw_decode(cleaned[start:])
            return _normalize_translation(obj)
        except Exception:  # noqa: BLE001
            pass
    # 兜底：正则提取 "id":"value" 对（对象形式）
    pairs = re.findall(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
    if pairs:
        return {k: _unescape(v) for k, v in pairs}
    raise ValueError(f"无法解析翻译 JSON: {content[:120]}")


def _unescape(s: str) -> str:
    """二次反转义：模型偶发双逃逸（\\n -> 字面 反斜杠+n），还原为真实换行/制表。"""
    return s.replace("\\n", "\n").replace("\\t", "\t")


def _normalize_translation(obj) -> dict[str, str]:
    """将 dict 或 list 形式的翻译结果归一为 {id: 译文}。"""
    result: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            result[str(k)] = _unescape(str(v))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                if "id" in item and ("translated" in item or "text" in item):
                    key = "translated" if "translated" in item else "text"
                    result[str(item["id"])] = _unescape(str(item[key]))
                else:
                    for k, v in item.items():
                        result[str(k)] = _unescape(str(v))
    return result


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
    import re
    m = re.match(r"^(.*?)(\s+)(\d+)$", line.strip())
    if m:
        title = m.group(1).rstrip()
        page_num = m.group(3)
        page.insert_text((x0, y), title, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
        pw = font.text_length(page_num, fs)
        page.insert_text((x1 - pw, y), page_num, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)
    else:
        page.insert_text((x0, y), line, fontsize=fs, fontname=fontname, fontfile=fontfile, color=color)


def render_page(page, page_blocks, translations, layout, cjk_font, cjk_font_bold, fitz):
    """渲染单页：redact 原文区域 + 按 layout 渲染译文（对齐/字号/换行/字体）。

    layout 为 {block_id: {alignment,fontsize,lines,fontname,fontfile,color,rect}}。
    无 layout 的块跳过（调用方保证 layout 覆盖待渲染块）。
    """
    text_blocks = [
        b for b in page_blocks
        if b.get("type") == "text" and b["id"] in translations and translations[b["id"]]
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
        lines = lay["lines"]
        color = lay["color"]
        fontname = lay["fontname"]
        fontfile = lay["fontfile"]
        font = cjk_font_bold if fontname == "cjk-bold" else cjk_font
        line_h = fs * lay.get("line_h_factor", 1.25)
        y = rect.y0 + fs
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
            if b.get("type") == "text" and b["id"] in translations and translations[b["id"]]
        ]
        if not text_blocks:
            continue
        for b in text_blocks:
            page.add_redact_annot(fitz.Rect(b["bbox"]), fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        for b in text_blocks:
            trans = translations[b["id"]]
            rect = fitz.Rect(b["bbox"])
            inset = fitz.Rect(rect.x0 + 1, rect.y0 + 1, rect.x1 - 1, rect.y1 - 1)
            if inset.width <= 0 or inset.height <= 0:
                inset = rect
            color = _int_to_rgb(b.get("color", 0))
            max_fs = float(b.get("size", 12.0))
            fs, lines = _fit_fontsize(cjk_font, trans, inset.width, inset.height, max_fs)
            line_h = fs * 1.25
            y = inset.y0 + fs
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


def parse_pages(spec: str | None, total: int) -> list[int] | None:
    """解析页码范围（1-based），返回 0-based 页号列表；None 表示全部。"""
    if not spec:
        return None
    result: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            for i in range(int(a), int(b) + 1):
                if 1 <= i <= total:
                    result.append(i - 1)
        else:
            i = int(part)
            if 1 <= i <= total:
                result.append(i - 1)
    return result


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
