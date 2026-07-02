#!/usr/bin/env python3
"""
为已翻译的 Lexical 文档页面添加侧边栏
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

# 侧边栏 HTML (从原网站提取)
SIDEBAR_HTML = '''<nav aria-label="Docs sidebar" class="menu thin-scrollbar">
<style>
  /* 侧边栏样式 */
  .menu {
    background: #fff;
    border-right: 1px solid #e1e4e8;
    padding: 1rem 0;
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 280px;
    overflow-y: auto;
    z-index: 100;
  }
  .menu__list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .menu__list-item {
    margin: 0;
  }
  .menu__link {
    display: block;
    padding: 0.5rem 1rem;
    color: #24292e;
    text-decoration: none;
    font-size: 14px;
    border-left: 3px solid transparent;
    transition: all 0.2s;
  }
  .menu__link:hover {
    background: #f6f8fa;
    color: #0366d6;
  }
  .menu__link--active {
    background: #f6f8fa;
    border-left-color: #0366d6;
    color: #0366d6;
    font-weight: 600;
  }
  .menu__link--sublist {
    font-weight: 600;
    padding-left: 1rem;
  }
  .menu__list-item-collapsible {
    cursor: pointer;
  }
  .categoryLinkLabel, .linkLabel {
    display: block;
  }
  .theme-doc-sidebar-item-category > .menu__list {
    padding-left: 1rem;
    display: block;
  }
  .theme-doc-sidebar-item-category.menu__list-item--collapsed > .menu__list {
    display: none;
  }
  .menu__list-item--collapsed .menu__link--sublist::after {
    content: ' ▸';
  }
  .menu__list-item--expanded .menu__link--sublist::after {
    content: ' ▾';
  }
</style>
<ul class="theme-doc-sidebar-menu menu__list">
<li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-1 menu__list-item">
  <a class="menu__link" href="intro.html"><span class="linkLabel">介绍</span></a>
</li>
<li data-category="getting-started" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">快速开始</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/quick-start.html"><span class="linkLabel">快速开始 (Vanilla JS)</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/react.html"><span class="linkLabel">React 快速开始</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/theming.html"><span class="linkLabel">主题</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/supported-browsers.html"><span class="linkLabel">支持的浏览器</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/creating-plugin.html"><span class="linkLabel">创建插件</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="getting-started/devtools.html"><span class="linkLabel">开发者工具</span></a>
    </li>
  </ul>
</li>
<li data-category="concepts" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">概念</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/editor-state.html"><span class="linkLabel">编辑器状态</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/nodes.html"><span class="linkLabel">节点</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/node-replacement.html"><span class="linkLabel">节点替换</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/node-state.html"><span class="linkLabel">节点状态</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/named-slots.html"><span class="linkLabel">命名插槽</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/key-management.html"><span class="linkLabel">键管理</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/node-cloning.html"><span class="linkLabel">节点克隆</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/listeners.html"><span class="linkLabel">监听器</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/transforms.html"><span class="linkLabel">节点变换</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/commands.html"><span class="linkLabel">命令</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/selection.html"><span class="linkLabel">选择</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/read-only.html"><span class="linkLabel">只读模式 / 编辑模式</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/history.html"><span class="linkLabel">useHistory</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/dom-events.html"><span class="linkLabel">处理 DOM 事件</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/keyboard-accessibility.html"><span class="linkLabel">键盘无障碍</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/shadow-dom.html"><span class="linkLabel">Shadow DOM 和 iframe</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/traversals.html"><span class="linkLabel">使用 NodeCaret 遍历节点</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="concepts/updates.html"><span class="linkLabel">更新</span></a>
    </li>
  </ul>
</li>
<li data-category="serialization" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">序列化</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="serialization/index.html"><span class="linkLabel">序列化与反序列化</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="serialization/dom-import.html"><span class="linkLabel">DOM 导入扩展</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="serialization/dom-render.html"><span class="linkLabel">DOM 渲染扩展</span></a>
    </li>
  </ul>
</li>
<li data-category="extensions" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">扩展</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/intro.html"><span class="linkLabel">Lexical 扩展</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/defining-extensions.html"><span class="linkLabel">定义扩展</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/migration.html"><span class="linkLabel">迁移指南</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/react.html"><span class="linkLabel">React 和 Lexical 扩展</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/signals.html"><span class="linkLabel">信号</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/peer-dependencies.html"><span class="linkLabel">对等依赖</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/included-extensions.html"><span class="linkLabel">内置扩展</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/design.html"><span class="linkLabel">设计文档</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="extensions/faq.html"><span class="linkLabel">FAQ</span></a>
    </li>
  </ul>
</li>
<li data-category="packages" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">包</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical.html"><span class="linkLabel">lexical (核心)</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-a11y.html"><span class="linkLabel">@lexical/a11y</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-clipboard.html"><span class="linkLabel">@lexical/clipboard</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-code-core.html"><span class="linkLabel">@lexical/code-core</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-code-prism.html"><span class="linkLabel">@lexical/code-prism</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-code-shiki.html"><span class="linkLabel">@lexical/code-shiki</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-code.html"><span class="linkLabel">@lexical/code</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-devtools-core.html"><span class="linkLabel">@lexical/devtools-core</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-dragon.html"><span class="linkLabel">@lexical/dragon</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-eslint-plugin.html"><span class="linkLabel">@lexical/eslint-plugin</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-extension.html"><span class="linkLabel">@lexical/extension</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-file.html"><span class="linkLabel">@lexical/file</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-hashtag.html"><span class="linkLabel">@lexical/hashtag</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-headless.html"><span class="linkLabel">@lexical/headless</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-history.html"><span class="linkLabel">@lexical/history</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-html.html"><span class="linkLabel">@lexical/html</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-internal.html"><span class="linkLabel">@lexical/internal</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-link.html"><span class="linkLabel">@lexical/link</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-list.html"><span class="linkLabel">@lexical/list</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-mark.html"><span class="linkLabel">@lexical/mark</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-markdown.html"><span class="linkLabel">@lexical/markdown</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-offset.html"><span class="linkLabel">@lexical/offset</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-overflow.html"><span class="linkLabel">@lexical/overflow</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-plain-text.html"><span class="linkLabel">@lexical/plain-text</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-react.html"><span class="linkLabel">@lexical/react</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-rich-text.html"><span class="linkLabel">@lexical/rich-text</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-selection.html"><span class="linkLabel">@lexical/selection</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-table.html"><span class="linkLabel">@lexical/table</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-tailwind.html"><span class="linkLabel">@lexical/tailwind</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-text.html"><span class="linkLabel">@lexical/text</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-utils.html"><span class="linkLabel">@lexical/utils</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="packages/lexical-yjs.html"><span class="linkLabel">@lexical/yjs</span></a>
    </li>
  </ul>
</li>
<li data-category="react" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">React</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="react/index.html"><span class="linkLabel">介绍</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="react/plugins.html"><span class="linkLabel">Lexical 插件</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="react/create_plugin.html"><span class="linkLabel">创建 React 插件</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="react/faq.html"><span class="linkLabel">React FAQ</span></a>
    </li>
  </ul>
</li>
<li data-category="collaboration" class="theme-doc-sidebar-item-category theme-doc-sidebar-item-category-level-1 menu__list-item menu__list-item--expanded">
  <div class="menu__list-item-collapsible">
    <a class="menu__link menu__link--sublist" role="button">
      <span class="categoryLinkLabel">协作</span>
    </a>
  </div>
  <ul class="menu__list">
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="collaboration/react.html"><span class="linkLabel">React</span></a>
    </li>
    <li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-2 menu__list-item">
      <a class="menu__link" href="collaboration/faq.html"><span class="linkLabel">协作 FAQ</span></a>
    </li>
  </ul>
</li>
<li class="theme-doc-sidebar-item-link theme-doc-sidebar-item-link-level-1 menu__list-item">
  <a class="menu__link" href="faq.html"><span class="linkLabel">FAQ</span></a>
</li>
</ul>
</nav>'''

# JavaScript 用于折叠/展开菜单和保存状态
TOGGLE_SCRIPT = '''
<script>
document.addEventListener('DOMContentLoaded', function() {
  // 从 localStorage 恢复展开状态
  const savedState = localStorage.getItem('sidebar_expanded_state');
  if (savedState) {
    const expandedCategories = JSON.parse(savedState);
    expandedCategories.forEach(category => {
      const item = document.querySelector(`.theme-doc-sidebar-item-category[data-category="${category}"]`);
      if (item) {
        item.classList.remove('menu__list-item--expanded');
        item.classList.add('menu__list-item--expanded');
      }
    });
  }

  // 为折叠菜单添加交互
  const collapsibles = document.querySelectorAll('.menu__list-item-collapsible');
  collapsibles.forEach(collapsible => {
    collapsible.addEventListener('click', function(e) {
      e.preventDefault();
      const parent = this.parentElement;
      parent.classList.toggle('menu__list-item--expanded');
      parent.classList.toggle('menu__list-item--expanded');

      // 保存展开状态到 localStorage
      saveExpandedState();
    });
  });

  // 高亮当前页面
  const currentPath = window.location.pathname.split('/').pop();
  const activeLink = document.querySelector(`a[href$="${currentPath}"]`);
  if (activeLink) {
    activeLink.classList.add('menu__link--active');
    // 确保父分类展开
    let parent = activeLink.closest('.theme-doc-sidebar-item-category');
    while (parent) {
      parent.classList.remove('menu__list-item--expanded');
      parent.classList.add('menu__list-item--expanded');
      parent = parent.parentElement.closest('.theme-doc-sidebar-item-category');
    }

    // 保存展开状态
    saveExpandedState();
  }

  // 保存展开状态的函数
  function saveExpandedState() {
    const expandedCategories = [];
    document.querySelectorAll('.theme-doc-sidebar-item-category.menu__list-item--expanded').forEach(item => {
      const category = item.getAttribute('data-category');
      if (category) {
        expandedCategories.push(category);
      }
    });
    localStorage.setItem('sidebar_expanded_state', JSON.stringify(expandedCategories));
  }
});
</script>
'''

def adjust_links_for_page(sidebar_html, html_file, base_dir):
    """根据页面位置调整侧边栏中的链接"""
    soup = BeautifulSoup(sidebar_html, 'html.parser')

    # 计算页面相对于根目录的深度
    rel_path = html_file.relative_to(base_dir)
    depth = len(rel_path.parts) - 1  # -1 因为最后一部分是文件名

    # 根据深度添加 ../ 前缀
    if depth == 0:  # 根目录文件
        prefix = ''
    else:  # 子目录文件
        prefix = '../' * depth

    # 调整所有链接
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.html') and not href.startswith('http'):
            link['href'] = prefix + href

    return str(soup)

def add_sidebar_to_page(html_file, base_dir):
    """为单个页面添加侧边栏"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 如果已经有侧边栏,跳过
    if 'class="menu thin-scrollbar' in content:
        print(f"跳过 {html_file} (已有侧边栏)")
        return

    # 调整侧边栏链接
    adjusted_sidebar = adjust_links_for_page(SIDEBAR_HTML, html_file, base_dir)

    # 解析 HTML
    soup = BeautifulSoup(content, 'html.parser')

    # 调整 body 样式以容纳侧边栏
    body = soup.find('body')
    if body:
        style = body.get('style', '')
        # 移除 max-width,添加左边距
        style = re.sub(r'max-width:\s*[^;]+;?', '', style)
        style = re.sub(r'margin:\s*[^;]+;?', 'margin: 0;', style)
        style += ' padding-left: 300px;'
        body['style'] = style

    # 在 body 开始处插入侧边栏
    if body:
        sidebar_soup = BeautifulSoup(adjusted_sidebar + TOGGLE_SCRIPT, 'html.parser')
        body.insert(0, sidebar_soup)

    # 写回文件
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    print(f"已添加侧边栏到 {html_file}")

def main():
    """主函数"""
    base_dir = Path('/Users/whiteyang/aiCoder/My-Agent/skills/doc-site-translator/translator/lexical.dev')

    # 找到所有 HTML 文件
    html_files = list(base_dir.rglob('*.html'))

    # 排除 _template.html
    html_files = [f for f in html_files if f.name != '_template.html']

    print(f"找到 {len(html_files)} 个 HTML 文件")

    # 为每个文件添加侧边栏
    for html_file in html_files:
        try:
            add_sidebar_to_page(html_file, base_dir)
        except Exception as e:
            print(f"处理 {html_file} 时出错: {e}")

if __name__ == '__main__':
    main()
