---
name: pdf-translator
description: 将文档型 PDF 原位翻译为中文（或指定语言），页级流水线（extract->translate->layout->render）保留并优化页面排版，基于 OpenAI 协议翻译 API（可配置 baseUrl/model/apikey）。
---

# pdf-translator

将文档型（非扫描版）PDF 原位翻译为指定语言（当前中文），**页级流水线**保留并优化排版：每页 extract（提取文本块 + 行级元信息）→ translate（OpenAI 协议 API，seg 片段上下文）→ layout（对齐/字号/换行/字体规划）→ render（原位覆盖写入中文，CJK 字体 + 排版优化）。排版优化逻辑独立为 `layout.py`。

## 前置条件

- `uv`（自动安装 PyMuPDF + openai 依赖，无需手动装包）
- CJK 字体（macOS 自带 Songti.ttc / Hiragino Sans GB / STHeiti；Linux 需自备并修改脚本顶部 `CJK_FONTS`）
- 翻译后端二选一：
  - **本地模型**（默认）：Hy-MT2-7B via llama.cpp，需 `brew install llama.cpp` + 模型文件，详见 [model_service.md](model_service.md)
  - **远程 API**：OpenAI 协议兼容 API（DeepSeek / 硅基流动等）

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
# 1. 仅提取文本块为 JSON（含行级 lines 元信息）
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --extract-only --out blocks.json
# 2. 仅翻译（input 为 extract JSON）
uv run skills/pdf-translator/pdf_translate.py blocks.json --translate-only --out trans.json
# 3. 仅排版规划（input 为原 PDF + blocks + trans，输出 layout JSON）
uv run skills/pdf-translator/pdf_translate.py <input.pdf> --layout-only --blocks blocks.json --trans trans.json --out layout.json
# 4. 仅渲染（input 为原 PDF + blocks + trans）
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
| `--extract-only` | 仅提取文本块为 JSON（含行级 lines 元信息） | off |
| `--translate-only` | 仅翻译（input 为 extract JSON） | off |
| `--layout-only` | 仅排版规划（input 为原 PDF + blocks + trans，输出 layout JSON） | off |
| `--render-only` | 仅渲染（input 为原 PDF） | off |
| `--blocks` | render-only / layout-only 的 extract JSON | `<input>.extract.json` |
| `--trans` | render-only / layout-only 的译文 JSON | `<input>.trans.json` |
| `--layout` | render-only 的 layout JSON | `<input>.layout.json` |
| `--out` | 调试模式中间产物路径 | 自动 |

## 配置

翻译 API 基于 OpenAI 协议，优先级：**环境变量 > local_model 覆盖 > config.json 字段 > 内置默认**。

### 本地模型 vs 远程 API

通过 `config.json` 中 `local_model.enabled` 切换：

| 开关 | 行为 |
|------|------|
| `"enabled": true` | 使用本地 Hy-MT2-7B 模型（默认 Q6_K 精度），需先启动服务 |
| `"enabled": false` | 使用远程 API（DeepSeek / 硅基流动等） |

本地模型管理详见 [model_service.md](model_service.md)。`local_model.enabled=true` 时自动覆盖 `base_url`/`model`/`api_key`，并适当降低批参数以适应本地模型上下文限制。

### 环境变量

| 环境变量 | 覆盖字段 | 说明 |
|----------|-------------|------|
| `LOCAL_MODEL` | `local_model.enabled` | `1`/`true` 启用，`0`/`false` 禁用本地模型 |
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

**页级流水线**：以页面为粒度，每页依次执行 extract → translate → layout → render。

1. **提取（extract_page）**：PyMuPDF dict 模式按文本块提取 bbox/字号/字体/颜色/文本 + 行级 `lines`（每行 x0/y0/x1/y1/text，供排版对齐识别）；同段块标注 `seg_id`；图片块仅记录 bbox
2. **翻译（translate_page）**：保留原 seg 片段滑动窗口上下文（页内批间衔接）；按 seg 不拆批 + 块数/字符/输出 token 预算分批；`max_tokens` 按批动态估算，输出截断时二分降批自愈，失败重试 5 次
3. **排版规划（layout_page，layout.py）**：基于行级元信息规划每块：对齐识别（行级 x0/x1/center 方差判 left/center/right/justify）、智能换行（wrap_cjk 标点禁则）、字号策略（下限 max(7, 原字号*0.7)，塞不下时向下扩展不覆盖相邻 block）、字体风格（标题加粗）；输出 layout 供 render 消费
4. **渲染（render_page）**：原位 redact 原文（白底覆盖、保留图片）→ 按 layout 以 CJK 字体写入译文（两端对齐调整字间距、居中/右对齐、标题加粗）

## 限制

- 仅处理文档型 PDF（文本可提取），不支持扫描版（无 OCR）
- 仅纯译文输出（原位覆盖 + 字号自适应，非双语对照）
- 代码块/数学公式符号保留原样
- 翻译 API 输出截断时自动二分降批重试；跨批上下文由滑动窗口衔接；长文档可分页范围处理

## 排错

- **`未找到 CJK 字体`**：修改脚本顶部 `CJK_FONTS` 指向系统 CJK 字体路径
- **翻译失败/超时**：减小 `batch_size`，或换更强模型（`OPENAI_MODEL`）；本地模型可尝试 `Q8` 精度
- **本地模型未就绪**：检查 `~/scripts/hy-mt2 status`，确保服务已启动，详见 [model_service.md](model_service.md)
- **输出截断频繁**：增大 `max_output_tokens`，或减小 `max_chars_per_batch`（单批输入过大导致译文超 token）
- **译文溢出**：脚本已字号自适应；原区域过小属 PDF 本身限制
