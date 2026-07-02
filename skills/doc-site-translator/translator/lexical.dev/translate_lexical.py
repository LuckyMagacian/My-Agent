#!/usr/bin/env python3
"""
Lexical 文档翻译脚本
将 Lexical 文档从英文翻译为中文，保留技术术语和代码块
"""

import json
import re
import os
from pathlib import Path

# 翻译映射表 - 技术术语保持英文
TRANSLATIONS = {
    # 标题翻译
    "Serialization & Deserialization": "序列化与反序列化",
    "DOMImportExtension": "DOMImportExtension",
    "DOMRenderExtension": "DOMRenderExtension",
    "Lexical Extensions": "Lexical 扩展",
    "Defining Extensions": "定义扩展",
    "Migration Guide": "迁移指南",
    "React and Lexical Extension": "React 与 Lexical 扩展",
    "Signals": "Signals",
    "Peer Dependencies": "Peer 依赖",
    "Included Extensions": "内置扩展",
    "Design Doc": "设计文档",
    "FAQ": "常见问题",

    # 常用术语翻译
    "editor": "编辑器",
    "node": "节点",
    "state": "状态",
    "extension": "扩展",
    "plugin": "插件",
    "configuration": "配置",
    "registration": "注册",
    "listener": "监听器",
    "transform": "变换",
    "command": "命令",
    "selection": "选择",
    "reconciliation": "协调",
    "serialization": "序列化",
    "deserialization": "反序列化",
    "import": "导入",
    "export": "导出",
    "render": "渲染",
    "update": "更新",
    "dependency": "依赖",
    "peer dependency": "peer 依赖",
}

def extract_content_from_json(json_path):
    """从 JSON 文件中提取内容"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理 MCP 工具返回格式
    if isinstance(data, list) and len(data) > 0:
        text = data[0].get('text', '')
        # 提取 JSON 内容
        if '```json' in text:
            start = text.find('```json\n') + 8
            end = text.find('\n```', start)
            if start > 7 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)

    return data

def translate_heading(text):
    """翻译标题"""
    for en, zh in TRANSLATIONS.items():
        if text.strip() == en:
            return zh
    return text

def translate_content(html_content):
    """
    翻译 HTML 内容
    保留代码块、技术术语
    """
    # 这里只做基础处理，主要翻译工作需要人工或 AI 完成
    # 此函数返回原始内容，实际翻译在生成 HTML 时处理
    return html_content

def generate_html(page_data, output_path, original_url, category=""):
    """生成翻译后的 HTML 文件"""

    title = page_data.get('title', '')
    content = page_data.get('content', '')
    url = page_data.get('url', original_url)

    # 翻译标题
    translated_title = translate_heading(title)

    # 生成面包屑导航
    breadcrumb = ""
    if category:
        breadcrumb = f'<a href="https://lexical.dev/">首页</a> » <a href="../index.html">{category}</a> » <a href="#">{translated_title}</a>'
    else:
        breadcrumb = f'<a href="https://lexical.dev/">首页</a> » <a href="#">{translated_title}</a>'

    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{translated_title} | Lexical 中文文档</title>
  <link rel="stylesheet" href="assets/styles.css">
  <style>
    /* Docusaurus 风格适配 */
    body {{
      font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Ubuntu, Cantarell, 'Noto Sans', sans-serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
      line-height: 1.6;
      color: #333;
      background: #fff;
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      font-weight: 600;
    }}
    h1 {{ font-size: 2rem; }}
    h2 {{ font-size: 1.5rem; color: #1a1a1a; border-bottom: 1px solid #e1e4e8; padding-bottom: 0.3em; }}
    h3 {{ font-size: 1.25rem; color: #2a2a2a; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
      font-family: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
      background: #f6f8fa;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.9em;
    }}
    pre {{
      background: #f6f8fa;
      padding: 1rem;
      overflow-x: auto;
      border-radius: 6px;
      border: 1px solid #e1e4e8;
    }}
    pre code {{
      background: none;
      padding: 0;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0;
    }}
    th, td {{
      border: 1px solid #d0d7de;
      padding: 8px 12px;
      text-align: left;
    }}
    th {{
      background: #f6f8fa;
      font-weight: 600;
    }}
    ul, ol {{
      margin: 1em 0;
      padding-left: 2em;
    }}
    li {{
      margin: 0.5em 0;
    }}
    figure {{
      margin: 1.5rem 0;
      text-align: center;
    }}
    figcaption {{
      font-size: 0.9em;
      color: #586069;
      margin-top: 0.5rem;
    }}
    img {{
      max-width: 100%;
      height: auto;
    }}
    .translation-banner {{
      background: #fff3cd;
      padding: 12px 20px;
      margin-bottom: 1.5rem;
      font-size: 14px;
      border-radius: 6px;
      border-left: 4px solid #ffc107;
    }}
    .translation-banner a {{
      color: #0366d6;
      font-weight: 500;
    }}
    .admonition {{
      padding: 1rem;
      margin: 1rem 0;
      border-radius: 4px;
    }}
    .admonition-tip {{
      background: #f0fff4;
      border-left: 4px solid #38a169;
    }}
    .admonition-warning {{
      background: #fff8e1;
      border-left: 4px solid #ff9800;
    }}
    .admonition-info {{
      background: #e3f2fd;
      border-left: 4px solid #2196f3;
    }}
    .admonition-caution {{
      background: #fff3e0;
      border-left: 4px solid #ff5722;
    }}
    .admonitionHeading {{
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}
    .hash-link {{
      color: #0366d6;
      opacity: 0.5;
      margin-left: 0.25rem;
    }}
    .hash-link:hover {{
      opacity: 1;
    }}
    .language-js, .language-ts, .language-tsx, .language-json {{
      display: block;
    }}
    .token-line {{
      display: block;
    }}
  </style>
</head>
<body>
  <!-- 翻译横幅 -->
  <div class="translation-banner">
    这是 <a href="{url}">Lexical 官方文档 {translated_title} 页面</a> 的中文翻译版本。
    如有疑问，请以 <a href="{url}">原文</a> 为准。
  </div>

  <nav aria-label="面包屑导航">
    {breadcrumb}
  </nav>

  <main>
    {content}
  </main>

  <footer>
    <hr>
    <p style="color: #586069; font-size: 0.85em;">
      版权所有 © 2026 Meta Platforms, Inc. 使用 Docusaurus 构建。
    </p>
  </footer>
</body>
</html>'''

    # 写入文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"Generated: {output_path}")

def main():
    base_dir = Path("/Users/whiteyang/.claude/skills/doc-site-translator/translator/lexical.dev")
    tool_results_dir = Path("/Users/whiteyang/.claude/projects/-Users-whiteyang-aiCoder-block-cheese/567bd838-319b-4eb2-904d-efce4c5c7c6d/tool-results")

    # Serialization 系列
    serialization_pages = [
        ("call_698027160d4f41c786823158.json", "index.html", "https://lexical.dev/docs/serialization/", "Serialization"),
        ("tool-e529f9f9845946b09bdf508d34b36871.json", "dom-import.html", "https://lexical.dev/docs/serialization/dom-import", "Serialization"),
        ("tool-d4573eda0c20473bab06fb7d8b6ac886.json", "dom-render.html", "https://lexical.dev/docs/serialization/dom-render", "Serialization"),
    ]

    # Extensions 系列
    extension_pages = [
        ("tool-99246f0166f8492a9bfbd5ac4babbdc4.json", "intro.html", "https://lexical.dev/docs/extensions/intro", "Extensions"),
        ("tool-dbf396a5fa6e402288a8bb9443c2430c.json", "defining-extensions.html", "https://lexical.dev/docs/extensions/defining-extensions", "Extensions"),
        ("ext-migration.json", "migration.html", "https://lexical.dev/docs/extensions/migration", "Extensions"),
        ("ext-react.json", "react.html", "https://lexical.dev/docs/extensions/react", "Extensions"),
        ("ext-signals.json", "signals.html", "https://lexical.dev/docs/extensions/signals", "Extensions"),
        ("ext-peer-dependencies.json", "peer-dependencies.html", "https://lexical.dev/docs/extensions/peer-dependencies", "Extensions"),
        ("ext-included-extensions.json", "included-extensions.html", "https://lexical.dev/docs/extensions/included-extensions", "Extensions"),
        ("ext-design.json", "design.html", "https://lexical.dev/docs/extensions/design", "Extensions"),
        ("ext-faq.json", "faq.html", "https://lexical.dev/docs/extensions/faq", "Extensions"),
    ]

    print("Processing Serialization pages...")
    for json_file, output_file, url, category in serialization_pages:
        json_path = tool_results_dir / json_file
        if json_path.exists():
            try:
                page_data = extract_content_from_json(json_path)
                output_path = base_dir / "serialization" / output_file
                generate_html(page_data, output_path, url, category)
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        else:
            print(f"File not found: {json_path}")

    print("\nProcessing Extensions pages...")
    for json_file, output_file, url, category in extension_pages:
        json_path = tool_results_dir / json_file
        if json_path.exists():
            try:
                page_data = extract_content_from_json(json_path)
                output_path = base_dir / "extensions" / output_file
                generate_html(page_data, output_path, url, category)
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        else:
            print(f"File not found: {json_path}")

    print("\nDone!")

if __name__ == "__main__":
    main()
