# Lexical 中文文档 - 已知问题

## 缺失页面

以下页面尚未翻译,因为原站访问超时或其他原因:

1. `concepts/keyboard-accessibility.html` - 键盘无障碍

### 翻译方法

如需翻译缺失的页面,可以使用以下方法:

```bash
# 使用 doc-site-translator skill 翻译单个页面
# 例如:翻译 keyboard-accessibility
打开 https://lexical.dev/docs/concepts/keyboard-accessibility
手动复制内容到翻译工具
```

## 提示框图标问题

### 问题描述

部分页面的提示框(TIP/WARNING/DANGER)图标显示为大图,而不是小图标。

### 原因

Docusaurus 使用 SVG 图标和特定的 CSS 类名(如 `admonitionHeading_ibya`),这些图标通过 React 组件动态渲染。在静态 HTML 中,这些 SVG 可能无法正确显示。

### 解决方案

已在 CSS 中定义了提示框的备用样式,使用文字标识(💡, ⚠️, 🚫)代替 SVG 图标:

```css
.admonition-tip {
  background: #f0fff4;
  border-left: 4px solid #38a169;
  padding: 1rem;
  margin: 1rem 0;
  border-radius: 4px;
}

.admonition-tip-title {
  font-weight: 600;
  color: #38a169;
  margin-bottom: 0.5rem;
}

/* 类似的样式应用于 warning 和 danger */
```

### 需要修复的页面

如发现提示框图标显示异常,可以手动编辑 HTML,将 Docusaurus 的复杂 SVG 结构替换为简单的文字标识:

```html
<!-- 替换前 -->
<div class="admonition-tip">
  <div class="admonitionHeading_ibya">
    <svg>...</svg>
    提示
  </div>
  <div>内容</div>
</div>

<!-- 替换后 -->
<div class="admonition-tip">
  <div class="admonition-tip-title">💡 提示</div>
  <div>内容</div>
</div>
```

## 已翻译页面统计

- 总页面数: 77
- 已翻译: 76
- 缺失: 1 (keyboard-accessibility)

## 联系方式

如需补充翻译或修复问题,请:
1. 检查 `manifest.json` 确认页面状态
2. 使用 `doc-site-translator` skill 翻译缺失页面
3. 使用 `add_sidebar.py` 为新页面添加侧边栏
