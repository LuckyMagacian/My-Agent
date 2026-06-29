---
name: doc-site-translator
description: "文档网站翻译方案。从入口 URL 开始，使用 chrome-devtools-mcp 爬取文档页面，翻译为中文并输出静态 HTML。保留原始交互结构（折叠面板、代码块、导航），链接回原站对应页面。支持单页翻译和整站翻译，整站翻译前可先翻译样本页确认效果。当用户需要翻译文档网站、翻译文档页面、整站文档中文化、将英文文档站点转为中文静态页面、批量翻译在线文档时自动应用。"
---

# 文档网站翻译

## 触发条件

| 条件 | 示例 |
|------|------|
| 翻译单个文档页面 | "把这个页面翻译成中文" |
| 翻译文档网站 | "把 react.dev 翻译成中文" |
| 整站文档中文化 | "把这个文档站翻译一下" |
| 英文文档站点转中文 | "帮我翻译这个技术文档站" |
| 批量翻译在线文档 | "把这个站点的文档都翻译了" |
| 文档本地化 | "我需要一份中文版的文档站" |

**不触发**：PDF 翻译、视频字幕翻译、代码注释翻译。

## 翻译模式

| 模式 | 触发信号 | 流程 |
|------|---------|------|
| **单页翻译** | 用户提供单个 URL，或明确说"翻译这个页面" | 站点发现（单页）→ 提取翻译 → 生成 HTML |
| **整站翻译** | 用户提供站点入口 URL，或说"翻译整个站点" | 站点发现 → 页面清单 → **样本页确认** → 批量翻译 → 生成 HTML |
| **整站翻译（续翻）** | 存在未完成的 manifest.json | 从断点继续 |

**模式判断**：
1. 用户明确指定单个页面 URL → 单页翻译
2. 用户给出站点入口（首页/文档根目录）→ 整站翻译
3. 无法判断 → 用 `AskUserQuestion` 询问用户

## 前置条件

### chrome-devtools-mcp 配置

本 skill 依赖 chrome-devtools-mcp 进行页面导航和内容提取。

**前提**：chrome-devtools-mcp 需要在 Claude Code MCP 配置中已激活。当前环境已配置此 MCP，无需额外操作。

**配置检查**（每次执行前）：

```
1. 检查 chrome-devtools-mcp 工具是否可用（尝试调用 list_pages）
   - 不可用 → 提示用户在 .mcp.json 中添加 chrome-devtools-mcp 配置
   - 可用 → 继续

2. 如需配置，在项目根目录 .mcp.json 中添加：
   {
     "mcpServers": {
       "chrome-devtools-mcp": {
         "command": "npx",
         "args": ["@anthropic-ai/chrome-devtools-mcp@latest"]
       }
     }
   }
```

### 浏览器复用策略

chrome-devtools-mcp 启动专用 Chrome 实例（独立 profile，通过 `--remote-debugging-pipe` 连接），同一时间只有一个 MCP 实例能连接。

**核心约束**：
- 只有一个 Chrome 实例，一个 MCP 连接
- 关闭最后一个标签页可能导致浏览器退出或 MCP 断连
- 因此**不要关闭标签页，而是在同一标签页内复用**

**核心原则：同一标签页内导航切换，提取完即导航离开**

```
标签页 1（常驻）：
  导航到页面 A → 提取文本 + 导出 HTML 快照 → 导航到 about:blank（释放页面 A）
  → 翻译（浏览器空闲，标签页显示 about:blank）
  → 导航到 about:blank → 注入 HTML 快照 → 回写翻译 → 导出最终 HTML
  → 导航到 about:blank → 导航到页面 B → ...
```

**页面生命周期**：

| 阶段 | 浏览器操作 | 占用时长 |
|------|-----------|---------|
| 提取 | navigate_page → wait_for → evaluate_script → navigate to about:blank | 数秒 |
| 翻译 | 无浏览器操作（标签页显示 about:blank） | 数分钟（模型思考） |
| 回写 | navigate to about:blank → document.write 注入 HTML → evaluate_script 回写 → 导出 → navigate to about:blank | 数秒 |

**标签页管理规则**：

1. **保留至少一个标签页**：永远不要 `close_page` 关闭最后一个标签页，否则浏览器可能退出
2. **navigate_page 复用同一标签页**：不需要 `new_page` / `close_page`，在同一个标签页内通过 `navigate_page` 切换页面
3. **提取后导航到 about:blank**：释放当前页面资源，为下一次操作做准备
4. **回写时用 document.write 注入**：在 about:blank 页面中注入 HTML 快照重建 DOM

**多站点交替**：

```
标签页 1：
  站点 A 页面 1 → 提取 → about:blank（释放）
  站点 B 页面 1 → 提取 → about:blank（释放）
  站点 A 页面 1 → 回写 → about:blank（释放）
  站点 B 页面 1 → 回写 → about:blank（释放）
```

**降级方案**：如 chrome-devtools-mcp 不可用，使用 `WebFetch` 工具降级，但以下能力受限：
- 无法执行 JavaScript（SPA 页面可能无法获取完整内容）
- 无法处理需要交互才能展开的内容
- 无法截图辅助判断页面结构

---

## 核心工作流

### 单页翻译流程

```
页面 URL → 阶段一：站点发现（单页）→ 阶段三：内容提取与翻译 → 阶段四：静态 HTML 生成
```

跳过页面清单和样本确认，直接翻译目标页面。

### 整站翻译流程

```
入口 URL → 阶段一：站点发现与结构识别 → 阶段二：页面清单确认
→ 阶段二.五：样本页翻译确认 → 阶段三：批量内容提取与翻译
→ 阶段四：静态 HTML 生成 → 阶段五：验证与交付
```

| 阶段 | 核心动作 | 输出 |
|------|---------|------|
| 一、站点发现 | 导航到入口 URL，识别站点结构 | 站点结构描述 |
| 二、页面清单 | 自动发现同域文档链接，建立页面清单 | manifest.json（用户确认） |
| **二.五、样本页确认** | **翻译 1 个代表性页面，用户确认效果** | **样本 HTML + 用户反馈** |
| 三、内容提取与翻译 | 逐页提取内容、翻译、保留结构 | 翻译后的 HTML 片段 |
| 四、静态 HTML 生成 | 组装完整 HTML 页面，生成站点 | 静态 HTML 文件集 |
| 五、验证与交付 | 检查链接、结构、翻译质量 | 最终交付物 |

**强制规则**：
1. **阶段二必须用户确认**：页面清单需用户确认范围后才可开始翻译
2. **阶段二.五必须用户确认**：样本页翻译效果需用户确认后才可批量翻译
3. **同域限制**：只爬取与入口 URL 同域的页面
4. **分批处理**：大型站点（>10 页）必须分批，每批不超过 10-20 页
5. **中间文件零残留**：HTML 骨架和原始内容只存在于浏览器 DOM 中，不落盘为 JSON/HTML 中间文件；所有翻译产出只写入 `translator/{域名}/` 目录

---

## 一、站点发现与结构识别

**目标**：了解站点结构，识别导航模式和内容区域。

**单页模式**：只识别目标页面的框架和内容区域，跳过步骤 1.4（页面链接发现）。
**整站模式**：完整执行所有步骤。

### 步骤 1.1：导航到入口 URL

使用 chrome-devtools-mcp 导航到用户提供的入口 URL：

```
chrome-devtools-mcp: navigate_page → 入口 URL
chrome-devtools-mcp: wait_for → 页面主要内容的标志性文本
```

**如导航失败**：
1. 检查是否需要代理（参考 `http-retry-handler` skill）
2. 注入代理环境变量后重试
3. 仍失败则降级到 WebFetch

**chrome-devtools-mcp 特有注意**：
- 导航前需确认浏览器已打开且 chrome-devtools-mcp 已连接（通过 `list_pages` 验证）
- 如浏览器未打开，提示用户先打开 Chrome 浏览器
- **不要关闭最后一个标签页**，始终保留至少一个标签页，通过 `navigate_page` 切换页面复用

### 步骤 1.2：识别站点框架

通过截图和 DOM 快照判断站点类型：

| 站点类型 | 识别特征 | 内容选择器 | 侧边栏选择器 |
|----------|---------|-----------|-------------|
| VitePress / VuePress | `__vue__` 属性、`VPDoc` class | `.vp-doc`, `div.content` | `aside.VPSidebar` |
| Docusaurus | `docusaurus` class、`theme-doc-markdown` | `article.markdown` | `nav.menu` |
| Next.js (Nextra) | `__next` 容器、`nextra-body` | `main.nextra-body` | `aside.nextra-sidebar` |
| MkDocs | `md-content` class | `.md-content__inner` | `.md-sidebar` |
| ReadTheDocs | `readthedocs` 属性 | `[role=main]` | `.wy-menu` |
| GitBook | `gitbook` class | `div.page-content` | `nav.sidebar` |
| 通用 SPA | 无明确框架特征 | 需手动识别 | 需手动识别 |
| 传统 SSR | 完整 HTML，无 JS 框架 | `main` 或 `article` | `aside` |

**识别方法**：
1. 使用 `chrome-devtools-mcp: take_snapshot` 获取页面结构
2. 使用 `chrome-devtools-mcp: evaluate_script` 检测框架特征
3. 使用 `chrome-devtools-mcp: take_screenshot` 辅助视觉判断

### 步骤 1.3：识别内容区域 vs 重复区域

| 区域类型 | 常见选择器 | 处理方式 |
|----------|-----------|---------|
| 导航栏（Header） | `header`, `nav`, `.navbar` | 提取链接结构，翻译标签后链接回原站 |
| 侧边栏（Sidebar） | `aside`, `.sidebar`, `nav.sidebar` | 提取链接结构，翻译标签后链接回原站 |
| 主内容区 | `main`, `article`, `.content` | **翻译此区域内容** |
| 页脚（Footer） | `footer` | 提取链接结构，翻译标签后链接回原站 |
| 目录（TOC） | `.toc`, `[aria-label="Table of Contents"]` | 保留结构，翻译标题文字 |
| 面包屑 | `.breadcrumb` | 保留结构，翻译文字 |

**内容区域识别策略**（按优先级）：
1. 框架已知 → 使用框架特定的内容选择器
2. 框架未知 → 使用语义化选择器：`main > article` > `main` > `[role=main]` > `.content`
3. 仍无法确定 → 截图让用户确认内容区域

### 步骤 1.4：发现站点页面链接（整站模式）

从入口页面开始，收集所有同域链接：

```javascript
// 使用 chrome-devtools-mcp evaluate_script 收集同域链接
() => {
  const baseUrl = window.location.origin;
  const links = Array.from(document.querySelectorAll('a[href]'));
  const sameDomainLinks = links
    .map(a => {
      try { return new URL(a.href, baseUrl).href; }
      catch { return null; }
    })
    .filter(href => href && href.startsWith(baseUrl))
    .filter((v, i, arr) => arr.indexOf(v) === i); // 去重
  return sameDomainLinks;
}
```

**链接过滤规则**：
- 只保留同域链接（与入口 URL 同一域名）
- 排除锚点链接（`#` 开头）
- 排除文件下载链接（`.pdf`, `.zip`, `.png` 等后缀）
- 排除非文档路径（`/api/`, `/admin/`, `/dashboard/`, `/login/`）
- 保留 URL 路径片段用于后续深度判断

---

## 二、页面清单确认（整站模式）

**目标**：建立完整的翻译页面清单，用户确认范围。

**仅在整站翻译模式下执行此阶段。单页翻译跳过。**

### 步骤 2.1：递归发现页面

从入口 URL 开始，BFS 遍历同域链接：

```
入口 URL → 提取同域链接 → 访问每个链接 → 提取新链接 → 去重合并
```

**深度控制**：
- 默认最大深度：与入口 URL 相比不超过 3 级路径
- 同一路径前缀下的页面不限深度（如 `/docs/` 下所有页面）
- 用户可指定深度限制

**页面分类**：

| 类别 | 判断依据 | 是否翻译 |
|------|---------|---------|
| 文档页面 | `/docs/`, `/guide/`, `/tutorial/`, `/learn/` | 是 |
| 首页 | 入口 URL 本身 | 是 |
| API 参考 | `/api/`, `/reference/` | 是 |
| 博客/新闻 | `/blog/`, `/news/`, `/changelog/` | 询问用户 |
| 社区/关于 | `/community/`, `/about/` | 询问用户 |
| 外部链接 | 不同域名 | 否，链接回原站 |

### 步骤 2.2：生成页面清单

创建页面清单文件 `{output_dir}/manifest.json`：

```json
{
  "source_url": "https://example.com/docs",
  "domain": "example.com",
  "framework": "vitepress",
  "discovered_at": "2026-06-29T10:00:00Z",
  "total_pages": 42,
  "pages": [
    {
      "url": "https://example.com/docs/getting-started",
      "path": "/docs/getting-started",
      "title": "Getting Started",
      "category": "docs",
      "depth": 1,
      "status": "pending"
    }
  ]
}
```

### 步骤 2.3：用户确认

**必须**向用户展示页面清单并确认：
1. 展示发现的总页面数和分类统计
2. 询问是否排除某些页面
3. 询问博客/社区等可选类别是否翻译
4. 告知输出目录为 `skills/doc-site-translator/translator/{站点域名}/`

**禁止**：未获用户确认就开始翻译任何页面。

---

## 二.五、样本页翻译确认（整站翻译专用）

**目标**：先翻译 1 个代表性页面，让用户确认翻译效果后再批量翻译。

**仅在整站翻译模式下执行此阶段。单页翻译直接进入阶段三。**

### 步骤 2.5.1：选择样本页

从页面清单中选择 1 个代表性页面：

**选择优先级**：
1. 入口 URL 对应的首页
2. `/docs/` 或 `/guide/` 下的第一个子页面（内容丰富、结构典型）
3. 页面清单中的第一个文档类页面

### 步骤 2.5.2：翻译样本页

按照阶段三的流程翻译该样本页，生成完整 HTML 文件。

### 步骤 2.5.3：用户确认

**必须**向用户展示翻译结果并确认：
1. 在浏览器中打开生成的 HTML 文件（使用 `open` 命令或 chrome-devtools-mcp）
2. 询问用户确认以下维度：
   - **翻译质量**：术语是否准确、语句是否通顺
   - **结构保留**：标题/代码块/表格/列表是否正确
   - **交互保留**：折叠面板/链接是否可用
   - **整体风格**：是否满意翻译风格
3. 如用户不满意，根据反馈调整：
   - 翻译风格问题 → 更新术语表和翻译原则，重新翻译样本页
   - 结构保留问题 → 调整内容区域选择器，重新提取
   - 交互保留问题 → 调整交互元素处理策略
4. 用户确认满意后，记录翻译参数（术语表、风格偏好），用于后续批量翻译

**禁止**：用户未确认样本页效果就开始批量翻译。

---

## 三、内容提取与翻译

**目标**：逐页提取文档内容并翻译，保留 HTML 结构和交互元素。

**单页模式**：直接翻译目标页面，不分批。
**整站模式**：基于样本页确认的翻译参数批量翻译，分批处理。

**浏览器占用原则**：每个页面的处理分为"提取"和"回写"两个短占用阶段，中间的翻译过程不占用浏览器。

### 步骤 3.1：提取阶段（导航 → 提取 → 导航离开）

```
navigate_page → 目标页面 → wait_for → 提取文本节点 → 导出 HTML 快照 → navigate_page → about:blank
```

1. **导航到目标页面**：

```
chrome-devtools-mcp: navigate_page → url: 目标页面 URL
chrome-devtools-mcp: wait_for → 页面加载完成标志
```

**SPA 处理**：
- 等待内容区域渲染完成（检测主内容区域的 DOM 稳定）
- 使用 `wait_for` 等待关键文本出现
- 设置合理的超时（默认 10 秒）

2. **提取文本节点**：按步骤 3.2 执行
3. **导出 HTML 快照**：按步骤 3.3.4 执行，保存原始 HTML 骨架到变量
4. **导航离开**（释放当前页面资源）：

```
chrome-devtools-mcp: navigate_page → url: about:blank
```

### 步骤 3.2：提取可翻译文本

**核心原则：HTML 骨架始终留在浏览器 DOM 中，进入模型的只有纯文本。**

使用 chrome-devtools-mcp `evaluate_script` 从浏览器 DOM 中提取所有需要翻译的文本节点：

```javascript
// 只提取文本节点，不携带任何 HTML
() => {
  const main = document.querySelector('main article')
    || document.querySelector('main')
    || document.querySelector('[role=main]');
  if (!main) return null;

  // 给每个文本节点分配唯一 ID，用于回写定位
  let nodeId = 0;
  const texts = [];

  const walk = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
    acceptNode: function(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      const tag = parent.tagName.toLowerCase();
      // 跳过代码、脚本、样式
      if (['script', 'style', 'code', 'pre', 'kbd', 'samp', 'var'].includes(tag)) return NodeFilter.FILTER_REJECT;
      // 跳过纯空白
      if (node.textContent.trim().length === 0) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  let node;
  while (node = walk.nextNode()) {
    const id = '_tr_' + (nodeId++);
    node.parentElement.setAttribute('data-tr-id', id);  // 在 DOM 中标记
    texts.push({
      id: id,
      text: node.textContent.trim(),
      parentTag: node.parentElement.tagName.toLowerCase()
    });
  }

  return { totalTextNodes: texts.length, texts: texts };
}
```

**返回给模型的数据只有**：
- `id`：文本节点的定位标识
- `text`：纯文本内容
- `parentTag`：父元素标签（辅助翻译策略判断）

**不返回**：HTML 标签、属性、CSS、代码块内容等任何非文本数据。

**提取顺序**：
1. 主内容区文本节点（翻译核心）
2. 侧边栏链接文字（导航用，结构简单）
3. 页头/页脚文字（结构简单）

### 步骤 3.2.1：文本分批（防止上下文溢出）

**问题**：单页可能有数百个文本节点，一次性全部翻译会导致：
- token 消耗过大（虽然只有纯文本，但数量多时仍然很长）
- 翻译质量下降（注意力分散、前后不一致）

**解决方案**：将文本节点分批翻译，每批控制在合理 token 范围内。

**分批策略**：

| 文本节点数 | 处理方式 |
|-----------|---------|
| ≤ 30 个 | 一次翻译完成 |
| 31-80 个 | 分批，每批 ≤ 30 个 |
| > 80 个 | 分批，每批 ≤ 25 个 |
| 单个文本节点 > 2000 字符 | 超长段落，单独翻译 |

**分批原则**：
- 相邻文本节点分到同一批（保持上下文连贯）
- 标题和其紧接的段落分到同一批（标题为段落提供翻译上下文）
- 超长节点单独翻译，避免一批中一个超长节点挤占过多 token

**每批翻译后立即回写浏览器 DOM**：
- 翻译完一批文本 → 保存翻译结果到上下文变量（浏览器已释放）
- 翻译下一批时，上下文中只有当前批的纯文本
- 所有批完成后，进入回写阶段重新占用浏览器

### 步骤 3.3：翻译与回写

**核心原则：进入模型的只有纯文本，HTML 骨架通过快照在回写阶段重新注入浏览器**

```
提取阶段：浏览器 DOM → 提取纯文本 + 导出 HTML 快照 → 关闭标签页（释放浏览器）
翻译阶段：模型翻译纯文本（浏览器空闲，可处理其他站点）
回写阶段：打开标签页 → 注入 HTML 快照 → 回写翻译文本 → 链接处理 → 导出最终 HTML → 关闭标签页
```

**不翻译的内容**（留在 DOM 中，不进入模型）：
- HTML 标签、属性、CSS class、内联样式
- `href`, `src`, `id`, `data-*` 等属性值
- `<code>` / `<pre>` / `<kbd>` / `<script>` / `<style>` 内的代码文本
- 所有 HTML 结构信息

**翻译的内容**（仅纯文本）：

| 文本所在父元素 | 翻译策略 | 示例 |
|----------|---------|------|
| 标题（h1-h6） | 翻译文本 | "Getting Started" → "快速开始" |
| 段落（p） | 翻译文本 | 整段翻译，保持语句通顺 |
| 列表项（li） | 翻译文本 | "First item" → "第一项" |
| 表格单元格（th/td） | 翻译文本 | 表头和数据均翻译 |
| 链接（a） | 翻译链接文字 | 文字翻译，href 在后续步骤处理 |
| 图片（img） | 翻译 `alt` 属性值 | 另见步骤 3.3.2 |
| 强调（strong/em） | 翻译包裹的文本 | 标签不变 |

**术语处理**：

| 规则 | 示例 |
|------|------|
| 技术术语保留英文 | API, SDK, CLI, React, Component, Hook, Middleware |
| 专有名词保留英文 | VitePress, Docusaurus, Next.js |
| 有通用中文译名的术语使用中文 | 数据库、服务器、客户端、接口、组件 |
| 首次出现时可标注英文原文 | "响应式（Reactive）" |
| 代码相关术语保留英文 | props, state, ref, context, slot |

**翻译与回写流程**（每页）：

**阶段 A：提取（占用浏览器数秒）**
1. 打开标签页，导航到目标页面
2. 提取纯文本节点列表（只有 `id` + `text` + `parentTag`）
3. 导出原始 HTML 快照（`innerHTML` 保存到变量）
4. 关闭标签页（**释放浏览器**）

**阶段 B：翻译（不占用浏览器）**
5. 按步骤 3.2.1 分批翻译纯文本，模型只看到文本内容
6. 翻译结果保存在上下文变量中

**阶段 C：回写（占用浏览器数秒）**
7. 确保当前在 about:blank 页面，注入 HTML 快照
8. 逐批回写翻译文本到 DOM
9. 链接处理
10. 导出最终 HTML
11. 导航离开（`navigate_page → about:blank`）
12. 写入文件

**步骤 3.3.0：HTML 快照注入（回写阶段开头）**

回写阶段需先在浏览器中重建 DOM 环境，才能执行后续的文本回写和链接处理：

```javascript
// 在 about:blank 页面中注入原始 HTML 快照
(htmlSnapshot) => {
  document.open();
  document.write(htmlSnapshot);
  document.close();
  return 'injected';
}
```

**步骤 3.3.1：文本回写**

```javascript
// 将翻译结果回写到浏览器 DOM 中对应的文本节点
(translations) => {
  // translations: [{ id: "_tr_0", translated: "快速开始" }, ...]
  let replaced = 0;
  translations.forEach(({ id, translated }) => {
    const el = document.querySelector('[data-tr-id="' + id + '"]');
    if (!el) return;
    // 找到该元素下的文本节点并替换
    for (const node of el.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) {
        const leading = node.textContent.match(/^\s*/)?.[0] || '';
        const trailing = node.textContent.match(/\s*$/)?.[0] || '';
        node.textContent = leading + translated + trailing;
        replaced++;
        break;
      }
    }
  });
  return { replaced: replaced, total: translations.length };
}
```

**步骤 3.3.2：图片 alt 属性回写**

```javascript
// 翻译 img 的 alt 属性
(altTranslations) => {
  // altTranslations: [{ selector: "img[src='...']", alt: "翻译文字" }, ...]
  let replaced = 0;
  altTranslations.forEach(({ selector, alt }) => {
    const img = document.querySelector(selector);
    if (img) { img.setAttribute('alt', alt); replaced++; }
  });
  return { replaced: replaced };
}
```

**步骤 3.3.3：链接处理**

所有文本回写完成后，统一处理链接地址。链接处理的核心逻辑：

- **已翻译页面**的站内链接 → 指向本地翻译版 HTML（互链）
- **未翻译页面**的站内链接 → 指向原站对应页面
- **锚点链接** → 指向本地翻译版中的对应锚点（或原站锚点）
- **站外链接** → 保持原始 href，添加 `target="_blank"`

```javascript
// 链接地址替换
// translatedPages: 已翻译页面的路径映射 { "/docs/guide": "docs/guide.html", ... }
// siteOrigin: 原站域名 "https://example.com"
(translatedPages, siteOrigin) => {
  const links = document.querySelectorAll('a[href]');
  let localLinks = 0, remoteLinks = 0, externalLinks = 0;

  links.forEach(a => {
    try {
      const url = new URL(a.href, siteOrigin);

      if (url.origin !== siteOrigin) {
        // 站外链接：添加新窗口打开
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener noreferrer');
        externalLinks++;
        return;
      }

      // 站内链接：去掉 hash 和 query 得到纯路径
      const path = url.pathname;

      if (url.hash) {
        // 锚点链接：如当前页面已翻译，指向本地锚点；否则指向原站
        const currentPath = window.location.pathname;
        if (translatedPages[currentPath]) {
          a.setAttribute('href', url.hash);  // 本地锚点
        } else {
          a.setAttribute('href', siteOrigin + path + url.hash);  // 原站锚点
        }
        localLinks++;
      } else if (translatedPages[path]) {
        // 已翻译页面：指向本地翻译版
        a.setAttribute('href', translatedPages[path]);
        localLinks++;
      } else {
        // 未翻译页面：指向原站
        a.setAttribute('href', siteOrigin + path + url.search);
        remoteLinks++;
      }
    } catch {}
  });

  return { localLinks, remoteLinks, externalLinks };
}
```

**`translatedPages` 映射构建**：

整站翻译时，从 `manifest.json` 构建 `translatedPages` 映射：

```javascript
// manifest.json 中每条记录: { path: "/docs/guide", status: "translated", output_file: "docs/guide.html" }
// 构建: { "/docs/guide": "docs/guide.html", "/docs/intro": "docs/intro.html", ... }
```

单页翻译时，`translatedPages` 只包含当前页面一条记录。

**链接路径计算规则**：

由于翻译后的 HTML 文件存放在 `translator/{域名}/` 下的对应路径，页面间互链需要计算相对路径：

```
源页面: docs/guide/basics.html
目标页面: docs/intro.html
相对路径: ../intro.html

源页面: index.html
目标页面: docs/getting-started.html
相对路径: docs/getting-started.html
```

```javascript
// 计算从源文件到目标文件的相对路径
function getRelativePath(fromFile, toFile) {
  const fromDir = fromFile.substring(0, fromFile.lastIndexOf('/'));
  const fromParts = fromDir.split('/').filter(Boolean);
  const toParts = toFile.split('/').filter(Boolean);

  // 找到公共前缀
  let common = 0;
  while (common < fromParts.length && common < toParts.length - 1 && fromParts[common] === toParts[common]) {
    common++;
  }

  // 从 fromDir 回退到公共祖先，再到 toFile
  const upCount = fromParts.length - common;
  const up = Array(upCount).fill('..').join('/');
  const down = toParts.slice(common).join('/');

  return (up ? up + '/' : '') + down;
}
```

4. **导出最终 HTML**：清理标记后，从浏览器 DOM 导出翻译后的完整 HTML

```javascript
// 清理 data-tr-id 属性并导出最终 HTML
() => {
  document.querySelectorAll('[data-tr-id]').forEach(el => {
    el.removeAttribute('data-tr-id');
  });
  const main = document.querySelector('main article')
    || document.querySelector('main')
    || document.querySelector('[role=main]');
  return main ? main.innerHTML : null;
}
```

5. **导航离开**（释放当前页面资源）：

```
chrome-devtools-mcp: navigate_page → url: about:blank
```

6. **写入文件**：将导出的 HTML 包装到完整页面模板中（步骤 4.2），写入输出文件

### 步骤 3.4：翻译侧边栏和导航

**同样遵循"只提取纯文本 → 翻译 → 回写浏览器 DOM"原则。**

侧边栏和导航的文本节点通常较少（链接文字），可以一次提取翻译回写，不需要分批。

**注意**：侧边栏/导航的提取和回写与主内容区在**同一个浏览器标签页生命周期内**完成，不需要单独开关标签页。即：
- 提取阶段：主内容区文本 + 侧边栏文本 + 导航文本 一起提取
- 回写阶段：注入 HTML 快照后，主内容区回写 + 侧边栏回写 + 导航回写 一起完成

### 步骤 3.5：分批处理

**大型站点分批策略**：

| 页面数 | 批次大小 | 说明 |
|--------|---------|------|
| ≤ 10 | 不分批 | 一次完成 |
| 11-30 | 10 页/批 | 分 2-3 批 |
| 31-100 | 15 页/批 | 分 3-7 批 |
| > 100 | 20 页/批 | 分 5+ 批，需确认是否继续 |

**批次间操作**：
1. 每批完成后向用户汇报进度
2. 保存已完成的翻译结果
3. 下一批开始前确认是否继续
4. 支持断点续翻（检查已完成的页面）

---

## 四、静态 HTML 生成

**目标**：为每个页面生成独立的静态 HTML 文件，组成可浏览的站点。

### 步骤 4.1：确定输出目录结构

**输出目录固定为本 skill 目录下的 `translator/` 子目录**：

```
skills/doc-site-translator/translator/
├── {站点域名}/                         # 每个站点一个目录，按域名命名
│   ├── index.html                      # 首页（翻译后的入口页面）
│   ├── docs/
│   │   ├── getting-started.html        # 翻译后的文档页面
│   │   ├── installation.html
│   │   └── guide/
│   │       ├── basics.html
│   │       └── advanced.html
│   ├── assets/
│   │   └── styles.css                  # 最小化样式
│   ├── manifest.json                   # 页面清单（含翻译状态）
│   └── README.md                       # 站点说明
```

**多站点场景**：翻译不同站点时，各自存放在以域名命名的子目录下，互不干扰：
- `translator/react.dev/`
- `translator/vitepress.dev/`
- `translator/docs.python.org/`

**路径映射规则**：
- 原站 `/docs/getting-started` → 输出 `translator/{域名}/docs/getting-started.html`
- 原站 `/docs/guide/basics` → 输出 `translator/{域名}/docs/guide/basics.html`
- 保留原站的路径层级结构

### 步骤 4.1.1：中间文件管理规范

**原则：所有中间数据只存在于浏览器 DOM 内存中，不落盘为文件。**

**允许写入的文件**（仅在 `translator/{域名}/` 下）：
- `*.html` — 翻译后的最终页面
- `assets/styles.css` — 最小化样式
- `manifest.json` — 页面清单和翻译状态
- `README.md` — 站点说明

**禁止写入的文件**（不允许出现在任何位置）：

| 禁止项 | 说明 | 为什么禁止 |
|--------|------|-----------|
| `*-raw.json` | 原始 HTML 存为 JSON | HTML 骨架只在浏览器 DOM 中操作，不需要落盘；会浪费 token 和磁盘空间 |
| `section-*.json` | 按章节拆分的 HTML 块 | 分块只在浏览器 DOM 中进行，纯文本提取后翻译回写，不需要中间文件 |
| `translated/` 目录 | 翻译后的 HTML 片段 | 翻译回写直接在 DOM 中完成，导出的是最终完整 HTML |
| `*-styles.json` | 页面样式信息 | 样式直接从原站提取写入 `assets/styles.css`，不需要中间 JSON |
| `sections/` 目录 | 拆分后的原始 HTML | 拆分逻辑在浏览器 DOM 中完成，纯文本提取给模型翻译 |

**数据流转路径**：

```
【提取阶段 - 占用浏览器数秒】
navigate_page → 目标页面
  ↓ evaluate_script 提取纯文本节点
  ↓ evaluate_script 导出 HTML 快照（innerHTML 保存到变量）
  ↓ navigate_page → about:blank（释放页面资源）

【翻译阶段 - 不占用浏览器】
模型上下文（只有 id + text + parentTag）
  ↓ 模型翻译纯文本
翻译结果保存在上下文变量中

【回写阶段 - 占用浏览器数秒】
确认当前在 about:blank
  ↓ evaluate_script → document.write 注入 HTML 快照
  ↓ evaluate_script 回写翻译文本
  ↓ evaluate_script 链接处理
  ↓ evaluate_script 清理标记 + 导出最终 HTML
  ↓ navigate_page → about:blank（释放页面资源）

文件系统（只写 translator/{域名}/ 下的最终产物）
```

**如果翻译中断**：断点续翻信息保存在 `manifest.json` 的 `status` 字段中，不依赖任何中间文件。

### 步骤 4.2：生成 HTML 页面

每个页面的 HTML 结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{翻译后的标题} | {站点名}</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <!-- 翻译横幅 -->
  <div class="translation-banner">
    这是 <a href="{原站页面URL}">原文</a> 的中文翻译版本。
    如有疑问，请以 <a href="{原站页面URL}">原文</a> 为准。
  </div>

  <!-- 翻译后的侧边栏 -->
  <nav class="sidebar">
    {翻译后的侧边栏链接，href 指向原站}
  </nav>

  <!-- 翻译后的主内容 -->
  <main>
    {翻译后的主内容区 HTML}
  </main>

  <!-- 翻译后的页脚 -->
  <footer>
    {翻译后的页脚内容}
  </footer>
</body>
</html>
```

### 步骤 4.3：生成最小化样式

`assets/styles.css` 包含保证可读性的最小样式集：

```css
/* 基础排版 */
body { font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }
h1, h2, h3, h4, h5, h6 { margin-top: 1.5em; margin-bottom: 0.5em; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }

/* 代码块 */
pre { background: #f6f8fa; padding: 1rem; overflow-x: auto; border-radius: 6px; }
code { font-family: 'SF Mono', Consolas, monospace; font-size: 0.9em; }
pre code { background: none; padding: 0; }
:not(pre) > code { background: #f6f8fa; padding: 2px 6px; border-radius: 3px; }

/* 表格 */
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
th { background: #f6f8fa; font-weight: 600; }

/* 折叠面板 */
details { margin: 1rem 0; border: 1px solid #d0d7de; border-radius: 6px; padding: 0.5rem 1rem; }
summary { cursor: pointer; font-weight: 600; padding: 0.5rem 0; }

/* 提示框 */
.tip, .warning, .danger { padding: 1rem; border-radius: 6px; margin: 1rem 0; }
.tip { background: #f0fff4; border-left: 4px solid #38a169; }
.warning { background: #fffff0; border-left: 4px solid #d69e2e; }
.danger { background: #fff5f5; border-left: 4px solid #e53e3e; }

/* 翻译横幅 */
.translation-banner { background: #fff3cd; padding: 8px 16px; margin-bottom: 1rem; font-size: 14px; border-radius: 4px; }

/* 侧边栏 */
.sidebar { position: sticky; top: 0; max-height: 100vh; overflow-y: auto; }
```

### 步骤 4.4：处理交互元素

| 交互元素 | 处理方式 |
|----------|---------|
| 折叠面板（details/summary） | 保留 HTML 结构，翻译 summary 文字和内容 |
| Tab 切换 | 保留所有 tab 内容，默认展开第一个 tab |
| 代码运行按钮 | 保留按钮 HTML，href 指向原站 playground |
| 搜索框 | 替换为链接到原站搜索页面的提示 |
| 链接（站内，已翻译） | 指向本地翻译版 HTML 的相对路径 |
| 链接（站内，未翻译） | 指向原站对应页面的绝对 URL |
| 链接（站外） | 保持原始 href，添加 `target="_blank"` |
| 锚点链接 | 已翻译页面内指向本地锚点，否则指向原站锚点 |

### 步骤 4.5：更新页面清单

翻译完成后更新 `manifest.json`，记录每个页面的翻译状态：

```json
{
  "pages": [
    {
      "url": "https://example.com/docs/getting-started",
      "path": "/docs/getting-started",
      "title_en": "Getting Started",
      "title_zh": "快速开始",
      "category": "docs",
      "depth": 1,
      "status": "translated",
      "output_file": "docs/getting-started.html",
      "translated_at": "2026-06-29T10:05:00Z"
    }
  ]
}
```

---

## 五、验证与交付

**目标**：抽查翻译质量，确认交付物可用。

### 步骤 5.1：链接可达性检查

随机抽查 3-5 个页面中的链接，确认：
- 原站链接可访问（HTTP 200）
- 锚点链接对应元素存在

### 步骤 5.2：结构完整性检查

抽查页面确认：
- 折叠面板可正常展开/折叠
- 代码块显示完整
- 表格结构正确
- 图片可加载（或 alt 文字存在）

### 步骤 5.3：翻译质量检查

抽查 3-5 个页面确认：
- 术语翻译一致（同一术语在不同页面翻译相同）
- 代码块未被翻译
- 技术术语保留英文
- 语句通顺无遗漏

### 步骤 5.4：生成 README.md

```markdown
# {站点名} 中文翻译

- 原站地址：{原站 URL}
- 翻译时间：{日期}
- 页面数量：{N} 页
- 基于版本：{版本号（如可获取）}

## 使用方式

直接用浏览器打开 `index.html` 即可浏览。

## 注意事项

- 所有导航链接指向原站，需联网访问
- 图片资源引用原站 URL，需联网加载
- 如有翻译不准确之处，请以[原站]({原站URL})为准
```

---

## 交互保留策略

### 核心原则：可读 > 可交互 > 完全还原

| 优先级 | 交互类型 | 保留策略 |
|--------|---------|---------|
| P0 必须 | 内容可读性 | 翻译后的文字必须正确显示，排版不错乱 |
| P0 必须 | 导航可达性 | 已翻译页面间本地互链，未翻译页面链接回原站 |
| P1 重要 | 折叠面板 | 保留 `<details><summary>` 原生 HTML 折叠 |
| P1 重要 | 代码块 | 保留代码块结构，可链接回原站查看高亮 |
| P2 有则更好 | Tab 切换 | 保留所有 tab 内容，默认展开第一个 tab |
| P2 有则更好 | 代码运行 | 保留按钮，链接回原站 playground |
| P3 降级 | 搜索 | 替换为链接到原站搜索页 |
| P3 降级 | 主题切换 | 不保留，使用固定浅色主题 |
| P3 降级 | 版本切换 | 不保留，标注翻译对应的版本号 |

### 链接处理详解

**站内链接**（同域），根据翻译状态分流：

| 链接目标 | 翻译状态 | href 值 | 示例 |
|----------|---------|---------|------|
| `/docs/intro` | 已翻译 | 本地翻译版相对路径 | `../intro.html` |
| `/docs/intro` | 未翻译 | 原站绝对 URL | `https://example.com/docs/intro` |
| `/docs/guide#section` | 当前页已翻译 | 本地锚点 | `#section` |
| `/docs/guide#section` | 当前页未翻译 | 原站锚点 | `https://example.com/docs/guide#section` |

**判断依据**：`manifest.json` 中页面的 `status` 字段。整站翻译时按批次更新，已翻译页面的链接会在后续页面翻译时被正确互链。

**站外链接**：
- 保持原始 href 不变
- 添加 `target="_blank"` 和 `rel="noopener noreferrer"`

**图片和资源**：
- `<img src>` → 保持指向原站的绝对 URL
- CSS 背景图 → 保持原站 URL 或内联 base64
- 字体文件 → 使用系统字体栈

---

## 异常处理

| 异常场景 | 处理方式 |
|----------|---------|
| 页面加载超时 | 重试一次（增加超时到 30s），仍失败则跳过并记录 |
| 页面需要登录 | 记录并跳过，在清单中标注 `status: "skipped_auth"` |
| 页面内容为空 | 检查是否 SPA 未渲染完成，尝试等待更长时间 |
| 页面重定向到其他域名 | 记录重定向 URL，不翻译重定向目标 |
| 翻译中断（用户中断或异常） | 保存已完成页面到 manifest.json，支持断点续翻 |
| 原站 CSS 不可用 | 使用内置最小化样式集 |
| 图片加载失败 | 保留 alt 文字，不影响阅读 |

## 断点续翻

当翻译中断后恢复时：

1. 读取 `skills/doc-site-translator/translator/{站点域名}/manifest.json`
2. 检查 `status: "translated"` 的页面，跳过已完成的
3. 从第一个 `status: "pending"` 的页面继续
4. 无 manifest.json 则从头开始

---

## chrome-devtools-mcp 常用操作映射

| 操作 | chrome-devtools-mcp 工具 | 参数 |
|------|------------------------|------|
| 导航到页面 | `navigate_page` | `type: "url", url: "{URL}"` |
| 等待内容加载 | `wait_for` | `text: ["标志性文本"]` |
| 获取页面结构 | `take_snapshot` | - |
| 截图 | `take_screenshot` | - |
| 执行 JS | `evaluate_script` | `function: "() => {...}"` |
| 点击元素 | `click` | `uid: "{元素uid}"` |
| 打开新页面 | `new_page` | `url: "{URL}"` |
| 获取页面列表 | `list_pages` | - |
| 选择页面 | `select_page` | `pageId: "{页面ID}"` |

---

## 与其他 Skill 的协作

### http-retry-handler

**协作场景**：chrome-devtools-mcp 导航失败时。

**协作方式**：
1. 当 chrome-devtools-mcp 导航返回网络错误（ETIMEDOUT、ECONNREFUSED 等）
2. 注入代理环境变量后重试（`http://127.0.0.1:7890`）
3. 具体重试策略参考 `http-retry-handler` skill 第零节

### attention-maintenance

**协作场景**：大型站点翻译跨多轮对话时保持上下文。

**协作方式**：
1. 使用 `<decision>` 记录当前翻译阶段和进度
2. 使用 `<knowledge>` 记录已识别的站点框架、内容选择器、术语表
3. 使用 `<state>` 记录当前翻译到哪一页/哪一批
4. 对话中断时保存 workspace，恢复后继续

### software-development-workflow

**协作场景**：翻译结果需要进一步加工（如集成到现有项目中）。

**协作方式**：
1. 翻译本身是独立操作，不走开发流程
2. 但如果翻译后需要修改代码集成，走功能变更流程

---

## 检查清单

### 模式判断检查
- [ ] 已判断翻译模式（单页 / 整站）
- [ ] 单页模式：确认目标页面 URL
- [ ] 整站模式：确认站点入口 URL

### 阶段一完成检查
- [ ] 已成功导航到目标 URL
- [ ] 已识别站点框架类型
- [ ] 已识别内容区域选择器
- [ ] 已识别重复区域（导航、侧边栏、页脚）
- [ ] 整站模式：已收集首页同域链接

### 阶段二完成检查（整站模式）
- [ ] 已递归发现所有同域文档页面
- [ ] 已生成页面清单（translator/{域名}/manifest.json）
- [ ] 用户已确认翻译范围

### 阶段二.五完成检查（整站模式）
- [ ] 已选择代表性样本页
- [ ] 样本页已完整翻译并生成 HTML
- [ ] 用户已在浏览器中查看翻译效果
- [ ] 用户已确认翻译质量、结构保留、交互保留、整体风格
- [ ] 翻译参数（术语表、风格偏好）已记录

### 阶段三完成检查（每页）
- [ ] 主内容区已完整提取
- [ ] 标题、段落、列表、表格已翻译
- [ ] 代码块未翻译（仅注释翻译）
- [ ] 技术术语保留英文
- [ ] 所有链接正确指向：已翻译页面互链本地、未翻译页面指向原站、站外链接新窗口打开
- [ ] 图片 alt 文字已翻译
- [ ] 侧边栏/导航文字已翻译
- [ ] 折叠面板等交互结构已保留

### 阶段四完成检查
- [ ] 所有页面已生成独立 HTML 文件（translator/{域名}/ 下）
- [ ] 路径结构与原站一致
- [ ] 翻译横幅已添加
- [ ] manifest.json 已更新翻译状态
- [ ] README.md 已生成

### 阶段五完成检查（整站模式）
- [ ] 随机抽查 3-5 个页面，链接可达（本地互链 + 原站链接）
- [ ] 折叠面板可正常展开/折叠
- [ ] 代码块显示完整
- [ ] 翻译无明显错误（术语一致性）
- [ ] 页面在浏览器中可正常浏览
