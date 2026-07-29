---
name: pdf-translator
description: 将文档型 PDF 原位翻译为中文（或指定语言），保留页面排版与格式，基于 OpenAI 协议翻译 API（可配置 baseUrl/model/apikey）。
---

# pdf-translator

将文档型（非扫描版）PDF 原位翻译为指定语言（当前中文），保留原有页面排版与格式：提取文本块 → 调用 OpenAI 协议 API 翻译 → 原位覆盖写入中文（CJK 字体 + 字号自适应）。

## 前置条件

- `uv`（自动安装 PyMuPDF + openai 依赖，无需手动装包）
- CJK 字体（macOS 自带 Songti.ttc / Hiragino Sans GB / STHeiti；Linux 需自备并修改脚本顶部 `CJK_FONTS`）
- OpenAI 协议翻译 API（默认硅基流动 GLM-4-9B-0414，可配置）

## 用法

### 完整翻译（推荐）
```bash
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --output <output.pdf>
```
一条命令完成提取→翻译→渲染，输出纯中文译文 PDF。

### 指定页范围
```bash
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --pages 1-5,8 --output <out.pdf>
```

### 分步调试
```bash
# 1. 仅提取文本块为 JSON
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --extract-only --out blocks.json
# 2. 仅翻译（input 为 extract JSON）
uv run skills/pdf-translator/pdf_translate.py blocks.json --translate-only --out trans.json
# 3. 仅渲染（input 为原 PDF + blocks + trans）
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --render-only --blocks blocks.json --trans trans.json --output out.pdf
```

## 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `input` | 输入 PDF（translate-only 时为 extract JSON） | 必填 |
| `--output, -o` | 输出 PDF 路径 | `<input>.<lang>.pdf` |
| `--lang` | 目标语言 | `zh` |
| `--pages` | 页码范围（1-based），如 `1-5,8` | 全部 |
| `--config` | 配置文件路径 | 同目录 `config.json` |
| `--extract-only` | 仅提取文本块为 JSON | off |
| `--translate-only` | 仅翻译（input 为 extract JSON） | off |
| `--render-only` | 仅渲染（input 为原 PDF） | off |
| `--blocks` | render-only 的 extract JSON | `<input>.extract.json` |
| `--trans` | render-only 的译文 JSON | `<input>.trans.json` |
| `--out` | 调试模式中间产物路径 | 自动 |

## 配置

翻译 API 基于 OpenAI 协议，优先级：**环境变量 > config.json > 内置默认**。

| 环境变量 | config 字段 | 说明 |
|----------|-------------|------|
| `OPENAI_API_KEY` | `api_key` | API 密钥 |
| `OPENAI_BASE_URL` | `base_url` | 接口地址 |
| `OPENAI_MODEL` | `model` | 模型名 |
| `TARGET_LANG` | `target_lang` | 目标语言 |

`config.json` 字段：`base_url` / `model` / `api_key` / `target_lang` / `batch_size` / `max_chars_per_batch` / `max_output_tokens` / `context_overlap`。

| 翻译参数 | 默认 | 说明 |
|----------|------|------|
| `batch_size` | 20 | 每批块数上限 |
| `max_chars_per_batch` | 6000 | 每批输入字符预算 |
| `max_output_tokens` | 8192 | 单批输出 token 上限（动态估算的硬约束） |
| `context_overlap` | 1 | 滑动窗口携带前文 seg 数；0 关闭上下文 |
默认使用硅基流动 `THUDM/GLM-4-9B-0414`。复制 `config.example.json` 为 `config.json` 填入密钥即可。

## 工作原理

1. **提取**：PyMuPDF dict 模式按文本块提取 bbox/字号/字体/颜色/文本，图片块仅记录 bbox
2. **翻译**：先为同段文本块标注 `seg_id`（bbox 邻近 + 排版一致，不合并文本、不破坏渲染）；按 seg 不拆批 + 块数/字符/输出 token 预算分批，每批携带前文 seg 作参考上下文（滑动窗口）；`max_tokens` 按批动态估算，输出截断时二分降批自愈，失败重试 5 次
3. **渲染**：每文本块原位 redact 原文（白底覆盖、保留图片）→ 以 CJK 字体逐行写入译文，字号二分自适应原区域

## 限制

- 仅处理文档型 PDF（文本可提取），不支持扫描版（无 OCR）
- 仅纯译文输出（原位覆盖 + 字号自适应，非双语对照）
- 代码块/数学公式符号保留原样
- 翻译 API 输出截断时自动二分降批重试；跨批上下文由滑动窗口衔接；长文档可分页范围处理

## 排错

- **`未找到 CJK 字体`**：修改脚本顶部 `CJK_FONTS` 指向系统 CJK 字体路径
- **翻译失败/超时**：减小 `batch_size`，或换更强模型（`OPENAI_MODEL`）
- **输出截断频繁**：增大 `max_output_tokens`，或减小 `max_chars_per_batch`（单批输入过大导致译文超 token）
- **译文溢出**：脚本已字号自适应；原区域过小属 PDF 本身限制
