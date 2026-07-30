"""pdf-translator 翻译：按批调用 OpenAI 协议 API 翻译文本块。"""
from __future__ import annotations

import json
import re
import sys

# 公式占位符 ⟦Fk⟧（U+27E6/U+27E7），翻译时替换行内公式，保证不被 LLM 改写
_PLACEHOLDER_RE = re.compile(r"(⟦F\d+⟧)")


def _build_item(block: dict, start_fidx: int = 0) -> tuple[dict, int]:
    """构造翻译项：把 segments 中 formula 段替换为占位符，得到送 LLM 的 text。

    占位符序号自 start_fidx 起跨块全局递增（同批唯一），便于检测 LLM 跨块映射错位
    （若各块都从 ⟦F0⟧ 起算，错配后占位符集合相同无法识别）。
    返回 (item, next_fidx)。无 segments 时整块作单一 text 段。
    formula_map: {占位符: {text,font,size,flags}} 供还原。
    """
    segments = block.get("segments")
    if not segments:
        return {"id": block["id"], "text": block.get("text", ""), "formula_map": {}}, start_fidx
    formula_map: dict[str, dict] = {}
    parts: list[str] = []
    fidx = start_fidx
    for seg in segments:
        if seg.get("type") == "formula":
            ph = f"⟦F{fidx}⟧"
            formula_map[ph] = {
                "text": seg.get("text", ""),
                "font": seg.get("font", ""),
                "size": seg.get("size", 12.0),
                "flags": seg.get("flags", 0),
            }
            parts.append(ph)
            fidx += 1
        else:
            parts.append(seg.get("text", ""))
    return {"id": block["id"], "text": "".join(parts).strip(), "formula_map": formula_map}, fidx


def _restore_segments(translated: str, formula_map: dict) -> dict:
    """将含占位符的译文还原为 {text, segments}：占位符->原公式段，其余为译文 text 段。"""
    if not formula_map:
        return {"text": translated, "segments": [{"text": translated, "type": "text"}]}
    out_segs: list[dict] = []
    for part in _PLACEHOLDER_RE.split(translated):
        if not part:
            continue
        if part in formula_map:
            m = formula_map[part]
            out_segs.append({
                "text": m["text"], "type": "formula",
                "font": m["font"], "size": m["size"], "flags": m["flags"],
            })
        else:
            out_segs.append({"text": part, "type": "text"})
    full = translated
    for ph, m in formula_map.items():
        full = full.replace(ph, m["text"])
    return {"text": full, "segments": out_segs}


def translate(blocks: list[dict], config: dict) -> dict[str, dict]:
    """按批调用 OpenAI 协议 API 翻译文本块，返回 {block_id: {text, segments}}。

    图片块与空文本块跳过。按 seg_id 语义段不拆批，叠加 batch_size / 字符预算 /
    输出 token 预算分批；每批携带前文 seg 作参考上下文（滑动窗口），失败重试。
    行内公式段以占位符替换送译，还原时保留原文不译。

    本地模型（local_model.enabled=true）自动使用简化模式：逐块直译，无需 JSON
    结构化输出，适配 Hy-MT2-7B 等专业翻译模型（指令遵循能力弱于通用 LLM）。
    """
    from openai import OpenAI

    lang_map = {"zh": "中文（简体）", "en": "English", "ja": "日本語"}
    lang_name = lang_map.get(config.get("target_lang", "zh"), config.get("target_lang", "zh"))
    text_blocks = [b for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
    if not text_blocks:
        return {}
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    # 本地模型：逐块简化翻译，不走 JSON 批处理流程
    local_cfg = config.get("local_model")
    if isinstance(local_cfg, dict) and local_cfg.get("enabled"):
        return _translate_simple(client, config, text_blocks, lang_name)

    batch_size = int(config.get("batch_size", 20))
    max_chars = int(config.get("max_chars_per_batch", 6000))
    max_out = int(config.get("max_output_tokens", 8192))
    out_budget = int(max_out * 0.8)  # 单批输出 token 预算，留余量防截断
    context_overlap = int(config.get("context_overlap", 1))

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

    translations: dict[str, dict] = {}
    total = len(batches)
    prev_ctx: list[dict] = []  # 上一批末尾段组（滑动窗口上下文来源）
    for i, batch in enumerate(batches, 1):
        items = []
        fidx = 0
        for b in batch:
            item, fidx = _build_item(b, fidx)
            items.append(item)
        ctx = _build_context(prev_ctx, context_overlap)
        print(
            f"[translate] 批次 {i}/{total}（{len(items)} 块，上下文 {len(ctx)} 块）...",
            file=sys.stderr,
        )
        translations.update(_translate_batch(client, config, items, lang_name, ctx))
        prev_ctx = _tail_group(batch)
    return translations


def translate_page(blocks: list[dict], config: dict) -> dict[str, dict]:
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


def _is_translatable(text: str) -> bool:
    """判断文本是否为可翻译的英文正文（长度 > 15 且拉丁字母占比 > 50%）。

    极短文本（<16字符，如单个人名/缩写）保留原文属合理行为，不判未翻译。
    """
    if len(text.strip()) <= 15:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = [c for c in letters if c.isascii()]
    return len(latin) / len(letters) > 0.5


def _is_formula_dominant(item: dict) -> bool:
    """块内公式字符占比高（>=40%）：原样返回属正确行为（纯数学无可译内容），
    跳过"未翻译"误判。按 formula_map 原文字符 vs 非公式字符估算。
    """
    fmap = item.get("formula_map") or {}
    if not fmap:
        return False
    formula_len = sum(len(m["text"]) for m in fmap.values())
    non_formula_len = max(len(item["text"]) - sum(len(ph) for ph in fmap), 0)
    total = formula_len + non_formula_len
    return total > 0 and formula_len / total >= 0.4


def _translate_batch(
    client,
    config: dict,
    items: list[dict],
    lang_name: str,
    context: list[dict] | None = None,
    max_retries: int = 5,
    depth: int = 0,
) -> dict[str, dict]:
    """翻译单批，返回 {id: {text, segments}}。

    携带 context 参考上下文（不翻译）；max_tokens 按批动态估算；
    行内公式以占位符送译，还原时保留原文；占位符缺失触发重试/降批自愈；
    输出截断时二分降批自愈（depth≤2），网络/解析错误走 max_retries 重试。
    """
    model = config["model"]
    has_formula = any(it.get("formula_map") for it in items)
    sys_prompt = (
        f"你是专业科技文献翻译。将英文文本块翻译为{lang_name}。"
        "铁律：每个文本块都必须翻译为中文，严禁原样返回英文原文，严禁以'术语'为由跳过翻译。"
        "规则："
        "1) 译文准确、自然、简洁，适配原排版；"
        "2) 所有英文自然语言必须翻译——包括标题、术语、图注、表格文字、说明、人名机构名；"
        "3) 仅以下三类保持原样不翻译："
        "   a) 纯数学公式符号（∫, Σ, ∂, √ 等）及其所在表达式；"
        "   b) 完整代码行（如 for (int i=0; i<n; i++)）；"
        "   c) 纯数字；"
        "4) 输入为 JSON 数组，元素形如 {\"id\":\"...\",\"text\":\"...\"}；"
        "仅返回 JSON 对象，键为 id、值为译文，如 {\"p1b0\":\"译文\"}；"
        "必须覆盖全部 id，不得遗漏；禁止数组、禁止 markdown 围栏、禁止额外说明。"
    )
    if has_formula:
        sys_prompt += (
            "5) 文本中的 ⟦Fk⟧ 形式标记为公式占位符，代表原公式；"
            "必须原样保留在译文对应位置，不得翻译、改写、拆分或增删。"
        )
    if context:
        sys_prompt += (
            "6) 用户消息开头的【上文参考】段落仅供理解指代与术语，"
            "不得翻译、其 id 不得出现在返回结果中。"
        )
    # context 作为 user 前缀参考文本；送 LLM 的 items 仅含 id+text（不含 formula_map）
    send_items = [{"id": it["id"], "text": it["text"]} for it in items]
    if context:
        ctx_lines = "\n".join(f"[{c['id']}] {c['text']}" for c in context)
        user_text = (
            "【上文参考，勿翻译】\n" + ctx_lines
            + "\n\n【待译，请逐条翻译并返回全部 id】\n"
            + json.dumps(send_items, ensure_ascii=False)
        )
    else:
        user_text = json.dumps(send_items, ensure_ascii=False)
    est_out = int(sum(len(it["text"]) for it in items) * 1.3)
    max_tokens = max(1024, min(est_out + 512, int(config.get("max_output_tokens", 8192))))
    last_err: Exception | None = None
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
            missing = [it["id"] for it in items if it["id"] not in parsed]
            if missing:
                raise ValueError(f"译文缺失 id: {missing[:5]}")
            # 未翻译检测：译文=原文且原文可翻译（英文为主）-> 视为未翻译
            # 公式占比高的块原样返回本就正确（纯数学无可译内容），跳过误判
            untranslated = [
                it["id"] for it in items
                if it["id"] in parsed and parsed[it["id"]].strip() == it["text"].strip()
                and _is_translatable(it["text"])
                and not _is_formula_dominant(it)
            ]
            if untranslated:
                raise ValueError(f"译文未翻译 id: {untranslated[:5]}")
            # 公式占位符校验：译文占位符集合必须与该块 formula_map 完全一致
            # 不一致（缺失或含他块占位符）-> 跨块映射错位，触发重试/降批
            bad_placeholder = []
            for it in items:
                expected = set(it.get("formula_map") or {})
                found = set(_PLACEHOLDER_RE.findall(parsed[it["id"]]))
                if found != expected:
                    bad_placeholder.append(it["id"])
            if bad_placeholder:
                raise ValueError(f"公式占位符错位 id: {bad_placeholder[:5]}")
            return {
                it["id"]: _restore_segments(parsed[it["id"]], it.get("formula_map") or {})
                for it in items
            }
        except Exception as e:  # noqa: BLE001
            last_err = e
            # 自愈：截断立即降批；漏译重试>=2次降批；网络/解析错误只重试
            truncated = finish_reason == "length" or _looks_truncated(content)
            is_missing = isinstance(e, ValueError) and (
                "译文缺失" in str(e) or "译文未翻译" in str(e) or "公式占位符" in str(e)
            )
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
    # 优雅降级：耗尽重试后保留原文继续，避免单块失败中断整轮（数学块原文即正确）
    print(
        f"[translate] 警告: 批次耗尽重试（{max_retries}次），保留原文继续: "
        f"{[it['id'] for it in items]}（{last_err}）",
        file=sys.stderr,
    )
    return {
        it["id"]: _restore_segments(it["text"], it.get("formula_map") or {})
        for it in items
    }


def _translate_simple(
    client,
    config: dict,
    blocks: list[dict],
    lang_name: str,
) -> dict[str, dict]:
    """简化翻译模式：逐块直译，无需 JSON 结构化输出。

    适配 Hy-MT2-7B 等专业翻译模型（指令遵循能力弱于通用 LLM）。
    每块独立发送简单 prompt，直接取模型输出作为译文。
    携带前一块译文作为上下文（滑动窗口），保持术语连贯。
    """
    max_retries = int(config.get("max_retries", 5))
    ctx_size = int(config.get("context_overlap", 2))
    translations: dict[str, dict] = {}
    total = len(blocks)
    ctx_buffer: list[str] = []  # 最近 N 条译文，作为上下文窗口

    for i, b in enumerate(blocks, 1):
        item, _ = _build_item(b, 0)
        has_formula = bool(item.get("formula_map"))

        sys_prompt = (
            f"你是专业科技文献翻译。将英文文本翻译为{lang_name}。"
            "铁律：必须翻译为中文，严禁原样返回英文原文。"
            "规则：译文准确、自然、简洁。仅输出译文，禁止任何额外说明、禁止加前缀后缀。"
        )
        if has_formula:
            sys_prompt += (
                "文本中的 ⟦Fk⟧ 形式标记为公式占位符，必须原样保留在译文对应位置，"
                "不得翻译、改写、拆分或增删。"
            )

        user_text = item["text"]
        if ctx_buffer:
            ctx_text = "\n".join(
                f"[上文{i}] {t}" for i, t in enumerate(ctx_buffer[-ctx_size:], 1)
            )
            user_text = f"【上文参考，勿翻译】\n{ctx_text}\n\n【待译】\n{user_text}"

        est_out = int(len(item["text"]) * 2.5)
        max_tokens = max(256, min(est_out, int(config.get("max_output_tokens", 4096))))

        translated = ""
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=config["model"],
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_text},
                    ],
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
                translated = (resp.choices[0].message.content or "").strip()

                # 公式占位符校验
                if has_formula:
                    expected = set(item["formula_map"].keys())
                    found = set(_PLACEHOLDER_RE.findall(translated))
                    if found != expected:
                        raise ValueError(
                            f"公式占位符不匹配: 期望 {expected}, 实际 {found}"
                        )

                # 未翻译检测
                if translated == item["text"].strip() and _is_translatable(item["text"]):
                    raise ValueError("译文与原文一致，未翻译")

                break  # 成功
            except Exception as e:
                if attempt < max_retries:
                    print(
                        f"[translate] 块 {i}/{total} 重试 {attempt}/{max_retries}: "
                        f"{type(e).__name__}: {str(e)[:80]}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"[translate] 警告: 块 {i}/{total} 耗尽重试，保留原文: "
                        f"{item['id']}（{str(e)[:80]}）",
                        file=sys.stderr,
                    )
                    translated = item["text"]

        translations[item["id"]] = _restore_segments(
            translated, item.get("formula_map") or {}
        )
        ctx_buffer.append(translated)
        if i % 10 == 0 or i == total:
            print(
                f"[translate] 进度 {i}/{total} 块",
                file=sys.stderr,
            )

    return translations


def _parse_translation_json(content: str) -> dict[str, str]:
    """从模型输出解析 {id: 译文}，兼容围栏/额外文本/对象或数组/尾逗号。"""
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
