# **ProseMirror 核心架构与扩展开发深度研究报告**

## **核心架构与模块化解耦设计**

ProseMirror 并非传统的开箱即用式富文本编辑器，而是一个由高度解耦的模块组成的底层构建套件 1。其核心设计理念在于将编辑器的运行机制分解为多个职责单一的包，赋予开发人员对文档结构、编辑行为及呈现机制的完全控制权 1。

### **核心包的职责划分与解耦逻辑**

ProseMirror 的运行依赖于四个核心互补模块，它们共同构成了编辑器的底层基石 1：

| 核心模块 | 职责定位 | 核心类与概念 | 设计目的与优势 |
| :---- | :---- | :---- | :---- |
| prosemirror-model | 定义文档的物理结构与约束规范。 | Schema, Node, Mark, Slice, Fragment 1 | 提供一个声明式的、类型安全的不可变文档树模型，与浏览器 DOM 彻底解耦 1。 |
| prosemirror-state | 管理编辑器在特定时刻的完整状态。 | EditorState, Selection, Transaction, Plugin 2 | 维护一个不可变的状态快照，保存文档、选区及插件的专属数据 4。 |
| prosemirror-transform | 提供级联执行与记录步骤的底层管道。 | Step, Transform, StepMap, Mapping 6 | 将文档变更转化为可逆、可重演的原子步骤，为历史记录和协同编辑奠定数理基础 1。 |
| prosemirror-view | 负责状态的可视化呈现与交互事件捕获。 | EditorView, NodeView, DecorationSet, Decoration 7 | 将抽象的状态树高效率地映射到 DOM，并拦截用户的底层物理输入 1。 |

这种解耦设计的优越性在于，开发者可以完全用自定义的渲染层替换原生的 DOM 视图层 prosemirror-view 10。在极端定制化场景（例如构建面向页面排版的编辑器）中，开发人员可以保留核心的 model、state、transform 及其插件生态，转而构建基于 Canvas 的自定义渲染系统 10。通过自定义事件桥接和布局管道，利用 Canvas 绘制选区几何图形并进行碰撞检测，从而在超大型文档下实现不随 DOM 复杂度线性衰减的稳定渲染性能 10。

## **数据状态的转换、联系与生命周期**

在 ProseMirror 中，用户输入、内存数据与视图呈现之间的流转是一个严格的闭环 1。

### **物理数据结构的本质差异**

ProseMirror 彻底抛弃了原生浏览器 DOM 的树状嵌套 inline 内容模型 1。  
在 DOM 架构中，加粗且斜体的文本段落通常呈现为嵌套的树状节点：

HTML  
\<p\>\<strong\>\<em\>Hello World\</em\>\</strong\>\</p\>

这种多层树级嵌套导致任何局部样式的拆解与合并都必须伴随复杂的 DOM 树重构 1。  
与此相反，ProseMirror 在宏观上虽保留了块级节点（Block Nodes）的树状分支，但在微观的行内（Inline）内容上采用了**扁平化序列模型** 1。段落内的文本片段是一条扁平的序列，修饰样式（Marks）作为元数据直接贴在指定的文本切片上 1。这种模型的优势在于：

1. **坐标归一化**：文档中的任意位置均可使用一个一维的整数指针进行标定，摒弃了 DOM 中复杂的 XPath 路径查询 1。  
2. **唯一性表征**：相邻且 Mark 相同的文本片段在内存中会自动合并，消除多余嵌套，使得任何文档状态都有唯一的、确定性的内存结构表达 1。  
3. **结构共享（Structural Sharing）**：内存中的 Node 实例均是不可变的值 1。对段落执行修改时，编辑器仅会重建该段落及其祖先节点，而未变化的其他子树则直接沿用旧引用，极大降低了垃圾回收压力与内存占用 1。

### **状态同步：ProseMirror 与现代组件化框架的竞态问题**

ProseMirror 维持着一种半双向的视图交互关系 7。在常规输入下，ProseMirror 会让浏览器首先处理底层的 DOM 输入事件，然后立即读取并审查该事件发生后的 DOM 变化，判定输入内容无误后，再同步逆向推演为状态事务，以此消除因输入法合成事件（Composition Events）带来的异步冲突 7。  
这一“立刻同步渲染并提交至 DOM（Render and Commit all at once）”的特征，使得 ProseMirror 在与采用异步批处理更新机制（如 React 的 Render & Commit 拆分）的第三方组件库结合时，极易诱发严重的测量偏差 7。  
当开发者使用 React 组件渲染自定义的节点视图（NodeViews）时，ProseMirror 的状态更新会同步触发并完成其物理 DOM 的占位。然而，此时 React 组件内的异步渲染阶段（如某些 Layout Effects）可能尚未在屏幕上完成实际的渲染与宽高提交 7。此时如果其他 ProseMirror 插件（例如选区菜单定位插件）立即通过 coordsAtPos 接口获取该节点的 DOM 屏幕坐标，就会读到过期的或尚未初始化的物理高度，导致悬浮小部件位置发生剧烈闪烁或定位偏移 7。

## **基于事务的数据流转机制**

ProseMirror 的状态演进严格遵循不可变数据流原则：所有的状态变更都必须被封装在事务（Transaction）中，然后原子性地应用于当前状态，生成一个全新的状态快照 1。

### **状态事务演化周期的物理流转**

编辑器的单向循环生命周期涉及以下关键步骤 1：

\+-------------------------------------------------------------+  
|                                                             |  
|                          DOM Event                          |  
|         (User Types, Pastes, Drag/Drops, Keydown)           |  
|                              |                              |  
\+------------------------------v------------------------------+  
                               | (Captured by EditorView)  
\+------------------------------v------------------------------+  
|                                                             |  
|                    Transaction Creation                     |  
|         (view.state.tr \-\> Creates a subclass of Transform)   |  
|                              |                              |  
\+------------------------------v------------------------------+  
                               | (Steps & Metadata attached)  
\+------------------------------v------------------------------+  
|                                                             |  
|                    Transaction Dispatch                     |  
|           (Intercepted by dispatchTransaction)              |  
|                              |                              |  
\+------------------------------v------------------------------+  
                               | (Apply steps and custom states)  
\+------------------------------v------------------------------+  
|                                                             |  
|                     State Mutation (Apply)                  |  
|          (newState \= currentState.apply(transaction))       |  
|                              |                              |  
\+------------------------------v------------------------------+  
                               | (Calculates minimal DOM diff)  
\+------------------------------v------------------------------+  
|                                                             |  
|                         DOM Sync                            |  
|             (view.updateState(newState) renders)            |  
|                              |                              |  
\+-------------------------------------------------------------+

1. **事件捕获**：用户向编辑器输入文本、粘贴数据或拖拽元素，这些原生物理事件被 EditorView 拦截 1。  
2. **事务构建**：通过 state.tr 实例化一个 Transaction，该对象记录了当前事件派生出的一系列改变文档内容的原子 Step 序列 1。  
3. **分发拦截**：事务被注入到 dispatchTransaction(tr) 管道。在此阶段，外部系统可以直接介入，或将事务合并到外部的应用级状态树（如 Redux）中 1。  
4. **状态生成**：执行 state.apply(tr) 运算，所有的 Step 依次在旧状态的文档树上运行。在此过程中，各激活插件注册的私有状态对象也会接收该事务，完成其自身状态的局部跃迁 2。  
5. **视图刷新**：计算得到的新状态被传回 view.updateState(newState) 1。视图层通过快速的比对算法，将有变动节点的物理 DOM 进行同步刷新 1。

### **位置映射体系（Position Mapping）**

在多步变更连续发生时，由于插入或删除文字会改变后续内容的物理偏移位置，ProseMirror 通过引入 StepMap 和位置映射体系（Position Mapping）来解决这一问题 6。  
每一个 Step 执行时，都会吐出一个原子的 StepMap，记录该步骤中发生改变的位置区间 $$ 以及替换后的文本实际长度 ![][image1] 6。例如，在位置 ![][image2] 执行一个替换，其映射逻辑可以通过一个偏置函数来表达。若某位置 ![][image3] 在此次变更之后，且 ![][image4]，则在经过该 StepMap 重新计算后，其最新绝对物理坐标 ![][image5] 可表达为：  
![][image6]  
一个复杂的事物会包含很多 Step，事务中累计的所有 StepMap 会被串联进 tr.mapping 容器 2。插件可以调用 tr.mapping.slice(fromStepIndex) 动态计算在任意历史时间节点产生的本地绝对坐标，将其精确平移投影到最新的文档树坐标中 11。这一位置映射机制是多人协作、行内装饰纠偏以及版本回滚功能的底层核心算法 6。  
在处理诸如“检测本次事务具体修改了哪些块级子节点”的需求时，开发人员可以通过 prosemirror-changeset 构建变更集，利用 change.fromB 和 change.toB（对应更新后文档中的新位置）进行 nodesBetween 检索，从而在 appendTransaction 生命周期内获取已被物理修改的直接子节点实例，避免对全量文档节点进行低效重算 13。

## **插件系统与装饰机制**

ProseMirror 的插件系统（Plugin）是其状态扩展、交互捕捉以及渲染层深度定制的基础 4。

### **插件的三维集成能力**

一个 ProseMirror 插件不仅能作为行为的拦截器，还能深度介入数据模型与物理呈现 11：

1. **State 状态扩展**：通过在插件中定义 state 的 init 与 apply(tr, value) 周期，可以赋予编辑器维护自定义状态（例如正在上传的文件队列、当前联想面板的激活态）的能力 11。  
2. **View 生命周期伴随**：通过提供 view(editorView) 钩子，插件能够生成一个与编辑器实例同生共死的专属视图对象，并在该对象内执行 DOM 监听、悬浮层挂载等操作 8。  
3. **Props 行为介入**：插件可以通过配置 props 拦截物理键入、鼠标点击、剪贴板读取，或者向编辑器动态注入**装饰（Decorations）** 11。

### **装饰（Decorations）的三大分类与运作机理**

装饰是一种在不真正修改底层 doc 数据的前提下，向视图展示层动态增加额外表现力的机制 9。这保证了文档内容的纯净。

| 装饰类型 | 调用方法 | 作用域与机制 | 经典用例 |
| :---- | :---- | :---- | :---- |
| **行内装饰 (Inline)** | Decoration.inline(from, to, attrs) | 直接为指定区间内的文本片段附加自定义的 CSS 类名、内联样式或自定义 Data 属性 9。 | 搜索结果局部高亮、语法拼写检测报错波浪线、AI 正在流式生成时的临时灰度文本 9。 |
| **小部件装饰 (Widget)** | Decoration.widget(pos, domNode, spec) | 在绝对位置指针处插入一个纯虚拟、不占物理字符位置的 DOM 元素 9。 | 协同编辑下的他人光标、文件上传动画进度条、行首段落拖拽手柄 9。 |
| **节点装饰 (Node)** | Decoration.node(from, to, attrs) | 直接为某个物理节点（如 Heading、Image）的最外层容器 DOM 附加自定义属性或 CSS 类名 9。 | 选定某代码块时的高亮描边、被折叠 Section 的隐藏类名样式注入 9。 |

装饰集 DecorationSet 是只读、不可变的平衡树结构 9。在实际更新中，高效率的 DecorationSet.map(tr.mapping, tr.doc) 方法可以确保所有的 Widget 装饰与 Inline 装饰无感地在文档坐标轴上与用户的敲击输入共同平移 9。

#### **视图 Editable 状态切换时的 NodeView 重新渲染难题**

当外层应用切换编辑器的只读状态（例如将 view.editable 从 true 改写为 false）时，ProseMirror 的视图层重绘逻辑默认并不会遍历重建这些底层的 NodeView 21。这会导致嵌套的 NodeView 无法感知当前的只读切换，其内部复杂的编辑控件（如嵌套的代码编辑器）可能依然允许用户点击交互 21。  
由于视图层不会将 editable 变化的事务向下分发到所有的 NodeView 21，标准的工程解决方案是：编写一个全局状态监听插件，在内部缓存 view.editable。一旦该状态发生质变，立即构造一个带有元数据的 Transaction，向所有关键节点注入临时的 Node 装饰（Node Decoration），强制该部分的节点发生重绘，从而让 NodeView 顺畅地在内部执行禁用/启用状态切换 21。

## **核心扩展功能的架构设计与实现方案**

### **1\. 自定义悬浮选区菜单 (Selection Menu)**

悬浮菜单需要监听编辑器的选区变化，当存在非空文本选区时，将浮动控制台渲染至选区物理正上方，并在选区变化或消失时进行定位校准或隐藏 16。

#### **架构实现核心**

使用插件的 view 生命周期绑定，结合 view.coordsAtPos(pos) 获取当前选区的屏幕绝对坐标，通过第三方浮动定位引擎（如 @floating-ui/dom）计算边界并实施绝对定位挂载 16。

JavaScript  
import { Plugin } from "prosemirror-state";  
import { autoUpdate, computePosition, flip, offset, shift } from "@floating-ui/dom";

export function floatingSelectionMenuPlugin(menuDOM) {  
  let cleanupPositioning \= null;

  return new Plugin({  
    view(editorView) {  
      const menuContainer \= menuDOM;  
      menuContainer.style.position \= "absolute";  
      menuContainer.style.display \= "none";  
      editorView.dom.parentNode.appendChild(menuContainer);

      const updateMenuPosition \= () \=\> {  
        const { state } \= editorView;  
        const { selection } \= state;

        if (selection.empty) {  
          menuContainer.style.display \= "none";  
          if (cleanupPositioning) {  
            cleanupPositioning();  
            cleanupPositioning \= null;  
          }  
          return;  
        }

        menuContainer.style.display \= "";

        // 构造满足 Floating UI 要求的虚拟定位锚点元素 \[22\]  
        const virtualAnchor \= {  
          getBoundingClientRect() {  
            const startCoords \= editorView.coordsAtPos(selection.from);  
            const endCoords \= editorView.coordsAtPos(selection.to);  
            return {  
              x: startCoords.left,  
              y: startCoords.top,  
              width: endCoords.right \- startCoords.left,  
              height: startCoords.bottom \- startCoords.top,  
              left: startCoords.left,  
              right: endCoords.right,  
              top: startCoords.top,  
              bottom: startCoords.bottom  
            };  
          }  
        };

        if (cleanupPositioning) cleanupPositioning();

        // 启动高阶自动位置纠偏更新循环 \[22\]  
        cleanupPositioning \= autoUpdate(virtualAnchor, menuContainer, () \=\> {  
          computePosition(virtualAnchor, menuContainer, {  
            placement: "top",  
            middleware: \[  
              offset(8),  
              flip({ crossAxis: false, padding: 4 }),  
              shift({ padding: 4 })  
            \]  
          }).then(({ x, y }) \=\> {  
            menuContainer.style.left \= \`${x}px\`;  
            menuContainer.style.top \= \`${y}px\`;  
          });  
        });  
      };

      return {  
        update(view, prevState) {  
          const { state } \= view;  
          if (prevState && prevState.doc.eq(state.doc) && prevState.selection.eq(state.selection)) {  
            return;  
          }  
          updateMenuPosition();  
        },  
        destroy() {  
          if (cleanupPositioning) cleanupPositioning();  
          menuContainer.remove();  
        }  
      };  
    }  
  });  
}

### **2\. 异步文件上传 (File Upload with Progress Indicator)**

在用户拖拽或选择本地图片时，立即通过 Widget 占位符在目标位置渲染出一个包含进度条的临时小部件，上传成功后再将其平滑替换为真正的物理 image 节点 11。

#### **架构实现核心**

使用专门的 uploadPlaceholderPlugin 来托管一个 DecorationSet 11。上传前通过 Unique Object Reference 作为标识符分发 add 事务，完成占位符就地悬挂；异步 promise 敲定后通过该标识符打捞因用户高频编辑而漂移的新位置，完成节点的真实落子与占位符销毁 11。同时，当节点尚未输入任何字符时，可通过对空块级节点应用 Decoration.node 注入专属 Class，结合 CSS 属性 content: attr(data-placeholder) 渲染出空行文字提示 14。

JavaScript  
import { Plugin, PluginKey } from "prosemirror-state";  
import { Decoration, DecorationSet } from "prosemirror-view";

const uploadPluginKey \= new PluginKey("upload\_placeholder");

export const fileUploadPlugin \= new Plugin({  
  key: uploadPluginKey,  
  state: {  
    init() { return DecorationSet.empty; },  
    apply(tr, set) {  
      // 1\. 极其关键的一步：将现存所有的图片上传占位符位置穿过本次 Step 映射向未来投影   
      set \= set.map(tr.mapping, tr.doc);

      const meta \= tr.getMeta(uploadPluginKey);  
      if (meta && meta.add) {  
        const progressWidget \= document.createElement("div");  
        progressWidget.className \= "upload-progress-card";  
        progressWidget.innerHTML \= \`  
          \<div class="spinner"\>\</div\>  
          \<span class="text"\>正在上传图片...\</span\>  
        \`;  
        const deco \= Decoration.widget(meta.add.pos, progressWidget, { id: meta.add.id });  
        set \= set.add(tr.doc, \[deco\]); //   
      } else if (meta && meta.remove) {  
        const found \= set.find(null, null, spec \=\> spec.id \=== meta.remove.id);  
        if (found.length) set \= set.remove(found); //   
      }  
      return set;  
    }  
  },  
  props: {  
    decorations(state) {  
      return this.getState(state);  
    }  
  }  
});

// 精准打捞：穿过编辑波澜，定位占位符当前最新的物理偏移地址   
export function findPlaceholderPosition(state, id) {  
  const decos \= fileUploadPlugin.getState(state);  
  const found \= decos.find(null, null, spec \=\> spec.id \=== id);  
  return found.length? found.from : null; //   
}

export function handleImageUpload(view, file, uploadService) {  
  const uniqueId \= {}; // 空对象做唯一地址引用标识   
  const { state, dispatch } \= view;  
    
  let tr \= state.tr;  
  if (\!tr.selection.empty) tr.deleteSelection();  
    
  const uploadInitPos \= tr.selection.from;  
  tr.setMeta(fileUploadPlugin, { add: { id: uniqueId, pos: uploadInitPos } });  
  dispatch(tr);

  uploadService(file)  
   .then(imageUrl \=\> {  
      const currentPos \= findPlaceholderPosition(view.state, uniqueId);  
      if (currentPos \=== null) return; // 文档包含它的那部分内容已被用户完全抹除，直接退出 

      const imageNode \= view.state.schema.nodes.image.create({ src: imageUrl });  
      // 用真实图片节点物理替换掉占位符，并优雅移除占位装饰   
      view.dispatch(  
        view.state.tr  
         .replaceWith(currentPos, currentPos, imageNode)  
         .setMeta(fileUploadPlugin, { remove: { id: uniqueId } })  
      );  
    })  
   .catch(() \=\> {  
      const currentPos \= findPlaceholderPosition(view.state, uniqueId);  
      if (currentPos\!== null) {  
        view.dispatch(view.state.tr.setMeta(fileUploadPlugin, { remove: { id: uniqueId } }));  
      }  
    });  
}

### **3\. 新增高亮节点类型 (Callout Node Specs & NodeViews)**

高亮提示框（Callout）是编辑场景中常见的容器块级节点，可自由选择警告、信息等模式，并在内部支持包含段落、列表等多行混合富文本 24。

#### **架构实现核心**

在 Schema 中声明高亮框节点模型，将其 content 约束定义为 block+（表明这是一个能容纳多行块级节点的容器元素） 24。通过定义 isolating: true 保证在内部按下退格键时不会误将容器壳结构直接删除，同时在 React 等框架渲染的 NodeView 中使用 callback ref 将物理子节点渲染容器绑定到 ProseMirror 规定的 contentDOM 节点上 24。

JavaScript  
import { Schema } from "prosemirror-model";

// 1\. 定义 Callout 的 Schema Spec 约束规范   
export const calloutNodeSpec \= {  
  group: "block",  
  content: "block+", // 限制容器内至少有一个块级节点   
  defining: true,   // 使得在粘贴操作时，Callout 外壳不易被过滤剔除   
  isolating: true,  // 强隔离：防止内部按退格键直接融化删除容器外框   
  attrs: {  
    type: { default: "info" } // 提示框的色彩级别属性   
  },  
  parseDOM: \[{  
    tag: "div.custom-callout",  
    getAttrs: dom \=\> ({  
      type: dom.getAttribute("data-type") || "info"  
    })  
  }\],  
  toDOM(node) {  
    return \["div", { class: \`custom-callout callout-${node.attrs.type}\`, "data-type": node.attrs.type }, 0\]; //   
  }  
};

// 2\. NodeView 挂载与子元素通道建立   
export class CalloutNodeView {  
  constructor(node, view, getPos) {  
    this.node \= node;  
    this.view \= view;  
    this.getPos \= getPos;

    // 创建最外层容器元素   
    this.dom \= document.createElement("div");  
    this.dom.className \= \`custom-callout callout-${this.node.attrs.type}\`;

    // 创建控制属性切换的交互层（非物理编辑内容区，设置 contentEditable \= false 防止光标进入） \[25\]  
    const settingsPanel \= document.createElement("div");  
    settingsPanel.className \= "callout-settings-panel";  
    settingsPanel.contentEditable \= "false"; // \[25\]  
    settingsPanel.innerHTML \= \`  
      \<select class="type-selector"\>  
        \<option value="info"\>信息\</option\>  
        \<option value="warning"\>警告\</option\>  
      \</select\>  
    \`;

    settingsPanel.querySelector(".type-selector").value \= this.node.attrs.type;  
    settingsPanel.querySelector(".type-selector").addEventListener("change", (e) \=\> {  
      const type \= e.target.value;  
      this.view.dispatch(  
        this.view.state.tr.setNodeMarkup(this.getPos(), null, { type })  
      );  
    });

    this.dom.appendChild(settingsPanel);

    // 【核心基石】：建立物理子元素宿主 DOM（contentDOM） \[8, 24\]  
    this.contentDOM \= document.createElement("div");  
    this.contentDOM.className \= "callout-rich-content";  
    this.dom.appendChild(this.contentDOM);  
  }

  update(node) {  
    if (node.type\!== this.node.type) return false;  
    this.node \= node;  
    this.dom.className \= \`custom-callout callout-${this.node.attrs.type}\`;  
    return true;  
  }  
}

### **4\. 可折叠块级类型 (Collapsible Section)**

可折叠面板需要支持包含标题（Heading）和后续的一组 Block 兄弟元素，当用户触发折叠开关时，视觉隐藏所有后续 Block，并将用户的输入光标强制驱逐出隐藏区域，避免产生无法感知的输入异常 20。

#### **架构实现核心**

在 Schema 设计上，构造专属折叠块容器 section，语法严格限制首子级必须是 heading，随后是多个 block 20。使用插件维护一个 Node 级别的 DecorationSet 20。折叠时在 NodeView 内为 contentDOM 容器注入 CSS 属性 display: none 进行物理隐藏 20。  
如果折叠时用户的 Selection 选区正陷在折叠内容区内，必须执行选区驱逐算法，在事务派发前将其强力定位到当前折叠 Section 外的首个可见块起始位置 20。

JavaScript  
import { Schema } from "prosemirror-model";  
import { Plugin, Selection } from "prosemirror-state";  
import { Decoration, DecorationSet } from "prosemirror-view";

// 1\. 结构模型：设计包含 heading 与后续内容的 section   
export const collapsibleSchemaSpec \= {  
  section: {  
    content: "heading block+", //   
    parseDOM: \[{ tag: "section" }\],  
    toDOM() { return \["section", 0\]; }  
  }  
};

export const foldPlugin \= new Plugin({  
  state: {  
    init() { return DecorationSet.empty; },  
    apply(tr, set) {  
      set \= set.map(tr.mapping, tr.doc);  
      const meta \= tr.getMeta(foldPlugin);  
      if (meta && meta.fold) {  
        const node \= tr.doc.nodeAt(meta.fold.pos);  
        if (node && node.type.name \=== "section") {  
          // 向该 section 节点附上折叠 node 装饰   
          const deco \= Decoration.node(meta.fold.pos, meta.fold.pos \+ node.nodeSize, {}, { isFolded: true });  
          set \= set.add(tr.doc, \[deco\]);  
        }  
      } else if (meta && meta.unfold) {  
        const found \= set.find(meta.unfold.pos, meta.unfold.pos \+ 1);  
        if (found.length) set \= set.remove(found);  
      }  
      return set;  
    }  
  },  
  props: {  
    decorations(state) {  
      return this.getState(state);  
    },  
    nodeViews: {  
      section(node, view, getPos, decorations) {  
        return new CollapsibleSectionView(node, view, getPos, decorations);  
      }  
    }  
  }  
});

class CollapsibleSectionView {  
  constructor(node, view, getPos, decorations) {  
    this.node \= node;  
    this.view \= view;  
    this.getPos \= getPos;

    this.dom \= document.createElement("section");

    // 提取子代装饰集中的折叠状态   
    this.isFolded \= decorations.some(d \=\> d.spec.isFolded);

    // 物理子内容容器  
    this.contentDOM \= document.createElement("div");  
    this.contentDOM.className \= "section-collapsible-wrapper";  
    this.contentDOM.style.display \= this.isFolded? "none" : ""; // 

    // 渲染折叠开关头部   
    this.foldToggle \= document.createElement("button");  
    this.foldToggle.contentEditable \= "false"; // \[25\]  
    this.foldToggle.className \= "fold-toggle-btn";  
    this.foldToggle.textContent \= this.isFolded? "▶" : "▼";  
    this.foldToggle.addEventListener("mousedown", (e) \=\> {  
      e.preventDefault();  
      this.toggleFold();  
    });

    this.dom.appendChild(this.foldToggle);  
    this.dom.appendChild(this.contentDOM);  
  }

  toggleFold() {  
    const pos \= this.getPos();  
    const nextFoldState \=\!this.isFolded;  
    const { state } \= this.view;  
    const sectionNode \= state.doc.nodeAt(pos);

    let tr \= state.tr;  
    if (nextFoldState) {  
      tr.setMeta(foldPlugin, { fold: { pos } });

      // 【驱逐算法】：拦截并保障被隐藏内容区光标的安全转移   
      const { from, to } \= state.selection;  
      const sectionEnd \= pos \+ sectionNode.nodeSize;  
        
      if (from \< sectionEnd && to \> pos) {  
        // 先尝试将光标向后推到 Section 外，若后方没有内容，则向前驱逐   
        const safeSelection \= Selection.findFrom(state.doc.resolve(sectionEnd), 1) ||  
                              Selection.findFrom(state.doc.resolve(pos), \-1);  
        if (safeSelection) tr.setSelection(safeSelection); //   
      }  
    } else {  
      tr.setMeta(foldPlugin, {unfold: { pos }});  
    }  
    this.view.dispatch(tr);  
  }

  update(node, decorations) {  
    if (node.type\!== this.node.type) return false;  
    this.node \= node;  
    const isNowFolded \= decorations.some(d \=\> d.spec.isFolded);  
    if (isNowFolded\!== this.isFolded) {  
      this.isFolded \= isNowFolded;  
      this.foldToggle.textContent \= this.isFolded? "▶" : "▼";  
      this.contentDOM.style.display \= this.isFolded? "none" : ""; //   
    }  
    return true;  
  }  
}

折叠功能亦有一种完全在状态树上剔除内容的替代方案：在折叠触发时，通过 Transaction 的 replace 步骤将当前 Section 之后的所有块级内容切片（Slice）彻底删除，并将这些真实数据的 JSON 序列化对象编码后存储在 heading 节点的 DOM 私有 data 属性上；解折叠时，再通过 PHP/JavaScript 重新解析该 JSON，将富文本结构通过 replace 步骤还原注入。但此方案会破坏协作光标在被折叠区域内的定位，只适用于非多人协同环境 27。

### **5\. 动态提示 (Mention Suggestions & Slash Autocomplete)**

动态提示系统在用户键入特定触发字符（如 @、/）时实时分析，并唤起推荐交互浮层。需要过滤普通邮箱输入场景，支持 Esc 键拦截关闭，并提供键盘事件劫持支持 29。

#### **架构实现核心**

使用双插件架构（输入规则 InputRule 插件与高阶行内装饰 Decoration 插件） 29。匹配到正则前置因子（如 /(?:^|\\s)@(\[a-zA-Z0-9\_\]\*)$/）时触发 onOpen 打开外部悬浮气泡，并将查询串暂存至插件 State 29；在 props 中注入 handleKeyDown，在提示激活时拦截 Up/Down/Enter 键直接分发自定义指令，不让原生回车换行或方向光标移动事件传导给编辑器 29。

JavaScript  
import { Plugin } from "prosemirror-state";  
import { Decoration, DecorationSet } from "prosemirror-view";

export function createAutocompletePlugin({ triggerChar, onOpen, onUpdate, onClose, onApply }) {  
  const triggerRegex \= new RegExp(\`(?:^|\\\\s)(${triggerChar})(\[a-zA-Z0-9\_\]\*)$\`); // 严谨匹配，防止邮箱触发 

  return new Plugin({  
    state: {  
      init() { return { active: false, triggerPos: null, filterText: "" }; },  
      apply(tr, stateVal) {  
        if (\!tr.docChanged &&\!tr.selectionSet) return stateVal;

        const { $from } \= tr.selection;  
        // 扫瞄光标前所在段落内的物理行内字符   
        const textBefore \= $from.parent.textContent.slice(0, $from.parentOffset);  
        const match \= triggerRegex.exec(textBefore); // 

        if (match) {  
          const matchStart \= $from.pos \- match.trim().length;  
          const currentFilter \= match;  
            
          return { active: true, triggerPos: matchStart, filterText: currentFilter };  
        }  
        return { active: false, triggerPos: null, filterText: "" };  
      }  
    },  
    props: {  
      decorations(state) {  
        const pluginState \= this.getState(state);  
        if (\!pluginState.active) return DecorationSet.empty;

        // 为正在输入检索词的物理区间加一层高亮行内装饰，方便定位与指示   
        const { selection } \= state;  
        const deco \= Decoration.inline(pluginState.triggerPos, selection.to, { class: "autocomplete-active-query" });  
        return DecorationSet.create(state.doc, \[deco\]);  
      },  
      handleKeyDown(view, event) {  
        const pluginState \= this.getState(view.state);  
        if (\!pluginState.active) return false;

        // 强力消费键盘导航操作：不向下冒泡，直接路由给外部气泡组件消费   
        if (event.key \=== "ArrowUp") {  
          onUpdate({ action: "up" });  
          return true; // 彻底切断该按键事件的流传 \[31\]  
        }  
        if (event.key \=== "ArrowDown") {  
          onUpdate({ action: "down" });  
          return true;  
        }  
        if (event.key \=== "Escape") {  
          onClose();  
          // 分发事务关闭自动联想状态  
          view.dispatch(view.state.tr.scrollIntoView());  
          return true;  
        }  
        if (event.key \=== "Enter" || event.key \=== "Tab") {  
          onApply(pluginState.triggerPos, view.state.selection.to);  
          return true;  
        }  
        return false;  
      }  
    }  
  });  
}

### **6\. 自定义代码编辑器 (Nested CodeMirror 6 NodeView)**

在富文本内部嵌套专业的多行代码编辑器，要求代码块内支持专业语法高亮与缩进，并且其 undo/redo 历史需要和外层富文本编辑器保持在同一个 Undo Stack 内，保证单次撤销的原子性 28。

#### **架构实现核心**

在 NodeView 的 constructor 中对 CodeMirror 6 进行就地挂载 32。双向数据同步会引入一个死循环（CM 更新触发 PM 更新，PM 更新又会触发 CM 重绘） 32。  
为了解决这个问题，需要设置核心状态锁 this.updating \= true 实施并发限制 32。当外部 PM 文档变化流入时，使用 charCodeAt 执行头尾最大共同子序列 Diff，进行最小局部的 CodeMirror dispatch，避免全量重绘 32。  
此外，还需要在 CM 的 Keymap 中监听按键，当光标处于 CM 文档顶边界（第 1 行第 0 字符）且按下 ArrowUp 时，调用外层 PM 的 Selection.near 寻址，将 Selection 跨物理组件驱逐移出 32。

JavaScript  
import { EditorView as CodeMirror, drawSelection, keymap as cmKeymap } from "@codemirror/view";  
import { javascript } from "@codemirror/lang-javascript";  
import { defaultKeymap } from "@codemirror/commands";  
import { Selection, TextSelection } from "prosemirror-state";

export class CodeMirrorBlockView {  
  constructor(node, view, getPos) {  
    this.node \= node;  
    this.view \= view;  
    this.getPos \= getPos;  
    this.updating \= false; // 核心状态防抖锁 

    // 初始化内联 CM 编辑器   
    this.cm \= new CodeMirror({  
      doc: this.node.textContent,  
      extensions:),  
        CodeMirror.updateListener.of(update \=\> this.handleCodeMirrorChange(update)) //   
    });

    this.dom \= this.cm.dom; // 劫持 NodeView 根元素   
  }

  handleCodeMirrorChange(update) {  
    if (this.updating ||\!this.cm.hasFocus) return; // 

    const offset \= this.getPos() \+ 1; // 跳过 block 的首 token 围栏   
    const tr \= this.view.state.tr;

    if (update.docChanged) {  
      this.updating \= true;  
      update.changes.iterChanges((fromA, toA, fromB, toB, text) \=\> {  
        if (text.length) {  
          tr.replaceWith(offset \+ fromA, offset \+ toA, this.view.state.schema.text(text.toString()));  
        } else {  
          tr.delete(offset \+ fromA, offset \+ toA);  
        }  
      });  
      tr.setSelection(TextSelection.create(tr.doc, offset \+ update.state.selection.main.from));  
      this.view.dispatch(tr);  
      this.updating \= false; //   
    }  
  }

  update(node) {  
    if (node.type\!== this.node.type) return false;  
    this.node \= node;

    if (this.updating) return true; // 

    const newText \= node.textContent;  
    const currentText \= this.cm.state.doc.toString();

    if (newText\!== currentText) {  
      // 局部最长匹配 Diff 算法以实现性能损耗最小化更新   
      let start \= 0, curEnd \= currentText.length, newEnd \= newText.length;  
      while (start \< curEnd && currentText.charCodeAt(start) \=== newText.charCodeAt(start)) start++;  
      while (curEnd \> start && newEnd \> start && currentText.charCodeAt(curEnd \- 1) \=== newText.charCodeAt(newEnd \- 1)) {  
        curEnd--;  
        newEnd--;  
      }

      this.updating \= true;  
      this.cm.dispatch({  
        changes: { from: start, to: curEnd, insert: newText.slice(start, newEnd) }  
      });  
      this.updating \= false; //   
    }  
    return true;  
  }

  maybeEscapeBoundary(direction) {  
    const { selection, doc } \= this.cm.state;  
    if (\!selection.main.empty) return false;

    if (direction \< 0) {  
      const line \= doc.lineAt(selection.main.head);  
      if (line.number \=== 1 && selection.main.head \=== 0) {  
        // 光标处于代码第一行顶格位置，通知外部 PM 往上移出选区   
        const targetPos \= this.getPos();  
        const selectionAfterEsc \= Selection.near(this.view.state.doc.resolve(targetPos), \-1);  
        this.view.dispatch(this.view.state.tr.setSelection(selectionAfterEsc));  
        this.view.focus();  
        return true;  
      }  
    } else {  
      if (selection.main.head \=== doc.length) {  
        // 光标处于代码尾行底格位置，向外向下驱逐移出   
        const targetPos \= this.getPos() \+ this.node.nodeSize;  
        const selectionAfterEsc \= Selection.near(this.view.state.doc.resolve(targetPos), 1);  
        this.view.dispatch(this.view.state.tr.setSelection(selectionAfterEsc));  
        this.view.focus();  
        return true;  
      }  
    }  
    return false;  
  }

  setSelection(anchor, head) {  
    this.cm.focus();  
    this.updating \= true;  
    this.cm.dispatch({ selection: { anchor, head } }); //   
    this.updating \= false;  
  }

  destroy() {  
    this.cm.destroy();  
  }  
}

### **7\. 多人实时协作 (Multiplayer Collaboration)**

多人协作系统必须能够解决多客户端并行编辑导致的文档冲突，使最终文档一致收敛 33。在 ProseMirror 体系下，协作实现通常有 OT（操作转换）与 CRDT（无冲突复制数据类型）两条路径 33。

#### **OT 机制与 CRDT 协作体系的物理差异**

| 特性维度 | 原生 OT 协作体系 (prosemirror-collab) | CRDT 协同引擎 (y-prosemirror / Yjs) |
| :---- | :---- | :---- |
| **协同拓扑** | 必须维持星型中心化拓扑结构，依赖唯一的权威服务器对所有人产生的所有 Steps 进行全局原子序号物理排序 33。 | 支持无中心的 Peer-to-Peer 拓扑或者基于中心化服务端 Peer 级联的多维拓扑 33。 |
| **冲突消解** | 服务器收到客户端的 Step 串。若该 Step 依赖的旧版本已过期，服务器会通过 Map Forward 算法重写（Transform/Remap）这些 Steps 的坐标，重新应用于当前版本并向全网下发广播 2。 | 文档被编译映射为全局一致的 CRDT 拓扑节点树 33。通过独特的两阶段数学合并模型计算，不依赖中央权威即可获得严格收敛的文档终态 33。 |
| **位置锚定** | 采用整型数值作为坐标，结合 StepMaps 执行运行时向前/向后重写，保真度极高且运算轻量 2。 | 采用 Yjs 的相对位置锚点（Relative Positions），该锚点将坐标绑定在固定的 Yjs 抽象字符单元上，不受物理偏移量增删的影响 36。 |
| **对视图层与 NodeView 的物理冲击** | 极低 33。因为流入的仅是精准且微观的原生 Step 33。ProseMirror 执行最小差异 DOM 比对，现存节点状态与 NodeView 运行安全稳定 1。 | 极大 33。在接收协同同步时，为了消解树状冲突，Yjs 往往会销毁旧节点并重建 ProseMirror 的整个物理文档节点树 33。 |

#### **Yjs 文档物理树重建引发的视图层痛点**

在大中型复杂扩展开发中，Yjs 的“物理树完全重建（Replace the whole document）”机制是一个重大痛点 33。  
当远端用户触发同步，由于本地 Yjs XML 片段合并的最终结果需要强制回馈给 ProseMirror，y-prosemirror 会采用直接将新文档树一次性替换写入 ProseMirror 状态树的方案 33。这种高强度的回写破坏了 ProseMirror 赖以自豪的不可变节点物理引用。由于没有保留相同节点的物理对象地址，ProseMirror 的 DOM-diff 算法会误判定原有的某些自定义 NodeView 节点已被用户完全删除，转而对其直接执行销毁周期（destroy），然后在其物理位置重新构建该节点 33。  
这直接导致了挂载在 NodeView 上的临时内联状态（如包含交互操作的 iframe 状态、未完成的 Canvas 涂鸦历史、正在播放的视频进度条位置）被瞬间清除，同时用户原本聚焦的光标也可能在物理树重建时由于原文本节点的消亡而发生严重的选区漂移、跳转甚至崩溃 33。  
相比之下，ProseMirror 原生的 prosemirror-collab 由于是百分之百基于 Steps 执行微观增量局部更新（100% Fidelity），避免了这种粗暴的“整树重建”过程，对 NodeView 没有任何负面影响 33。因此，在具有大量嵌套复杂交互小部件或 React 深度挂载 NodeView 的高级富文本研发中，基于 prosemirror-collab 自研一套服务器端 OT 协调中心往往是更能确保交互稳定性的最佳选择 33。

## **结论**

ProseMirror 凭借高度模块化和不可变的架构，为高级富文本开发提供了一个高度灵活、性能稳定的底层引擎 1。其核心优势在于：

1. **扁平化与不可变性**：通过微观的扁平 inline 序列和全局不可变的物理节点树，消除了原生 HTML DOM 的复杂性与不确定性，保证了文档数据的一致性与可预测性 1。  
2. **位置映射系统**：通过 StepMap 和位置映射，完美解决了复杂编辑场景下的坐标同步难题，使历史撤销、行内高亮装饰、多人协同编辑等高级功能得以稳定实现 2。  
3. **强大的插件与装饰**：提供了跨状态、视图、交互三个维度的全场景定制能力，通过 Inline、Widget、Node 三类装饰，使开发者能构建出如高亮 Callout 框、可折叠面板、自动联想输入法等企业级功能，且不破坏底层文档数据的纯净度 9。

在多人协作实现上，原生 OT 方案虽然架构上对中央服务器有较强依赖，但其纯物理增量的微观 Step 修改机制能完美适配复杂的 NodeView，保证用户体验的顺畅 33；而 Yjs 等 CRDT 引擎虽具备无中心协同的弹性，但其“重建整物理树”的同步策略会对视图和 NodeView 造成较大冲击 33。开发团队应针对实际业务中的 NodeView 复杂度及物理协同拓扑环境，进行合理的技术方案权衡 33。

#### **引用的著作**

1. ProseMirror Guide, 访问时间为 六月 8, 2026， [https://prosemirror.net/docs/guide/](https://prosemirror.net/docs/guide/)  
2. Reference manual \- ProseMirror, 访问时间为 六月 8, 2026， [https://prosemirror.net/docs/ref/](https://prosemirror.net/docs/ref/)  
3. Tech Deep Dive: Exploring CKEditor and Prosemirror's Core Designs \- Medium, 访问时间为 六月 8, 2026， [https://medium.com/juro-tech/tech-deep-dive-exploring-ckeditor-and-prosemirrors-core-designs-50ee608bbdc5](https://medium.com/juro-tech/tech-deep-dive-exploring-ckeditor-and-prosemirrors-core-designs-50ee608bbdc5)  
4. module state \- ProseMirror Reference manual, 访问时间为 六月 8, 2026， [https://prosemirror.net/docs/ref/version/0.17.0.html](https://prosemirror.net/docs/ref/version/0.17.0.html)  
5. This is the reference manual for the ProseMirror rich text editor. It lists and describes the full public API exported by the library., 访问时间为 六月 8, 2026， [https://prosemirror.net/docs/ref/version/0.16.0.html](https://prosemirror.net/docs/ref/version/0.16.0.html)  
6. prosemirror-transform/src/README.md at master \- GitHub, 访问时间为 六月 8, 2026， [https://github.com/ProseMirror/prosemirror-transform/blob/master/src/README.md](https://github.com/ProseMirror/prosemirror-transform/blob/master/src/README.md)  
7. Why I rebuilt ProseMirror's renderer in React \- smoores.dev, 访问时间为 六月 8, 2026， [https://smoores.dev/post/why\_i\_rebuilt\_prosemirror\_view/](https://smoores.dev/post/why_i_rebuilt_prosemirror_view/)  
8. RFC: 'Node views' to manage the representation of nodes \- Show \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/rfc-node-views-to-manage-the-representation-of-nodes/463](https://discuss.prosemirror.net/t/rfc-node-views-to-manage-the-representation-of-nodes/463)  
9. ProseMirror DecorationSet in React: Everything I Wish Someone Had Told Me \- Medium, 访问时间为 六月 8, 2026， [https://medium.com/@faisalmujtaba/prosemirror-decorationset-in-react-everything-i-wish-someone-had-told-me-6262eabae7ca](https://medium.com/@faisalmujtaba/prosemirror-decorationset-in-react-everything-i-wish-someone-had-told-me-6262eabae7ca)  
10. Building a Canvas-Based Editor on Top of ProseMirror's State and Plugin System, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/building-a-canvas-based-editor-on-top-of-prosemirror-s-state-and-plugin-system/8982](https://discuss.prosemirror.net/t/building-a-canvas-based-editor-on-top-of-prosemirror-s-state-and-plugin-system/8982)  
11. ProseMirror upload example, 访问时间为 六月 8, 2026， [https://prosemirror.net/examples/upload/](https://prosemirror.net/examples/upload/)  
12. Properly relating step.from/to to the document \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/properly-relating-step-from-to-to-the-document/5974](https://discuss.prosemirror.net/t/properly-relating-step-from-to-to-the-document/5974)  
13. Identifying the changed nodes for a given transaction \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/identifying-the-changed-nodes-for-a-given-transaction/6382](https://discuss.prosemirror.net/t/identifying-the-changed-nodes-for-a-given-transaction/6382)  
14. How to: input-like placeholder behavior \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/how-to-input-like-placeholder-behavior/705](https://discuss.prosemirror.net/t/how-to-input-like-placeholder-behavior/705)  
15. How to insert an async uploaded image? \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/how-to-insert-an-async-uploaded-image/589](https://discuss.prosemirror.net/t/how-to-insert-an-async-uploaded-image/589)  
16. ProseMirror tooltip example, 访问时间为 六月 8, 2026， [https://prosemirror.net/examples/tooltip/](https://prosemirror.net/examples/tooltip/)  
17. Floating menu (bubble menu) \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/floating-menu-bubble-menu/2313](https://discuss.prosemirror.net/t/floating-menu-bubble-menu/2313)  
18. Showing some tools by entering "/" \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/showing-some-tools-by-entering/4443](https://discuss.prosemirror.net/t/showing-some-tools-by-entering/4443)  
19. Selection changes when inline Decoration is applied \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/selection-changes-when-inline-decoration-is-applied/1027](https://discuss.prosemirror.net/t/selection-changes-when-inline-decoration-is-applied/1027)  
20. ProseMirror folding example, 访问时间为 六月 8, 2026， [https://prosemirror.net/examples/fold/](https://prosemirror.net/examples/fold/)  
21. Re-render Custom NodeView when View Editable changes \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/re-render-custom-nodeview-when-view-editable-changes/6441](https://discuss.prosemirror.net/t/re-render-custom-nodeview-when-view-editable-changes/6441)  
22. Letterboxd/prosemirror-selection-menu \- GitHub, 访问时间为 六月 8, 2026， [https://github.com/Letterboxd/prosemirror-selection-menu](https://github.com/Letterboxd/prosemirror-selection-menu)  
23. Prosemirror placeholder plugin approach \- Gist \- GitHub, 访问时间为 六月 8, 2026， [https://gist.github.com/amk221/1f9657e92e003a3725aaa4cf86a07cc0](https://gist.github.com/amk221/1f9657e92e003a3725aaa4cf86a07cc0)  
24. Prosemirror: Render node as react component \- Gearheart.io, 访问时间为 六月 8, 2026， [https://gearheart.io/blog/prosemirror-render-node-as-react-component/](https://gearheart.io/blog/prosemirror-render-node-as-react-component/)  
25. Custom NodeView containing an editable node \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/custom-nodeview-containing-an-editable-node/587](https://discuss.prosemirror.net/t/custom-nodeview-containing-an-editable-node/587)  
26. Patterns for rendering subsets of a document \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/patterns-for-rendering-subsets-of-a-document/9002](https://discuss.prosemirror.net/t/patterns-for-rendering-subsets-of-a-document/9002)  
27. Text folding \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/text-folding/439](https://discuss.prosemirror.net/t/text-folding/439)  
28. Block-based schema for a document \- discuss.ProseMirror, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/block-based-schema-for-a-document/8950](https://discuss.prosemirror.net/t/block-based-schema-for-a-document/8950)  
29. prosemirror-autocomplete \- NPM, 访问时间为 六月 8, 2026， [https://www.npmjs.com/package/prosemirror-autocomplete](https://www.npmjs.com/package/prosemirror-autocomplete)  
30. Suggestions and autocomplete plugin library, \`prosemirror-autocomplete\` \- Show, 访问时间为 六月 8, 2026， [https://discuss.prosemirror.net/t/suggestions-and-autocomplete-plugin-library-prosemirror-autocomplete/4151](https://discuss.prosemirror.net/t/suggestions-and-autocomplete-plugin-library-prosemirror-autocomplete/4151)  
31. emergence-engineering/prosemirror-slash-menu \- GitHub, 访问时间为 六月 8, 2026， [https://github.com/emergence-engineering/prosemirror-slash-menu](https://github.com/emergence-engineering/prosemirror-slash-menu)  
32. ProseMirror embedded editor example, 访问时间为 六月 8, 2026， [https://prosemirror.net/examples/codemirror/](https://prosemirror.net/examples/codemirror/)  
33. Lies I was told about collaborative editing, Part 2: Why we don't use Yjs | Hacker News, 访问时间为 六月 8, 2026， [https://news.ycombinator.com/item?id=47359712](https://news.ycombinator.com/item?id=47359712)  
34. Comparison to raw ProseMirror, esp. regarding collaboration. · ueberdosis tiptap · Discussion \#1507 \- GitHub, 访问时间为 六月 8, 2026， [https://github.com/ueberdosis/tiptap/discussions/1507](https://github.com/ueberdosis/tiptap/discussions/1507)  
35. Lies I was Told About Collaborative Editing, Part 2: Why we don't use Yjs \- Reddit, 访问时间为 六月 8, 2026， [https://www.reddit.com/r/SoftwareEngineering/comments/1tjlpbf/lies\_i\_was\_told\_about\_collaborative\_editing\_part/](https://www.reddit.com/r/SoftwareEngineering/comments/1tjlpbf/lies_i_was_told_about_collaborative_editing_part/)  
36. I'm actually in the middle of rewriting the y-prosemirror binding with Kevin Jah... | Hacker News, 访问时间为 六月 8, 2026， [https://news.ycombinator.com/item?id=47409955](https://news.ycombinator.com/item?id=47409955)  
37. AI agents as CRDT peers — building collaborative AI with Yjs | Electric, 访问时间为 六月 8, 2026， [https://electric.ax/blog/2026/04/08/ai-agents-as-crdt-peers-with-yjs](https://electric.ax/blog/2026/04/08/ai-agents-as-crdt-peers-with-yjs)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAaCAYAAACHD21cAAABE0lEQVR4AeyRu2oCQRiFNyEkkDQJKVKkSMitDykCKXIhhc/hK/gwVj6AhWClYCHeK0HB1nsrWIhaqeB3llXcYRS0EASX8+2Z+ec/7M7MqbPjc8DBf7bchDbUQeMGngKfzD2mWX2GGrxACOQB3CczuFj8ZDCEBFhlC77ReQcFmIJVtuCP15n13Gqbghlrwivagr+sDaAKa2UGX+m8hyLMwNQNhXNwzOCfipAHmyIUr2FtMKdFA93vBbUe+IInFPTFEV6BVSkQphAFV6u/+k5F91fCJ7DQB4MkfEEcXCmoe2sx04VjzjevDnShD2VQTwwfgysFtZ8nZleg373EH+EBbkE9Z3gQllJxOdlmcAxuOK39H84cAAD//wAOiG4AAAAGSURBVAMAFhImNUnfUzQAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAABSklEQVR4AeyTuUpDQRiFLzaCNmJjoaKCgghiI4IIbp21dla+hBb24htYWNuIheIDuOGCWoiICGYhEEKqQKqkSch3hklyM7lkAikCIeF8c2b5c+ZmMncg6PDTgwFrHMk/ZCAL8iQeA/k7fgiDYOSewTOzc/AIY7ALMzALC3AOJ3ABRm6AmaRZgTxoR8yoQKuAOF4NDqICJinQrk94CcJS/bidUD8yYN0WPFgP2waDYXgDPUlkwCaL0p2aECP0TyEN+2BkHsP06o0Cygx34AiO4Qw+4ReWIAFGbsAEszrxL/wH/uAbLmERDiAHNbkB2l2LtzTXcAPq6+foX2DYKDdgyy7fW/eaG7DNN7STTpmuX+GAecqn4QOK0JYUsEql7v8Lrt2X8RTsgVcKeKVK938UHwJdlCn8CrxSgLeoVUE/IIh8G1udWdNa9w+xAgAA//+kvr5oAAAABklEQVQDABo8NDVJLve1AAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAABaElEQVR4AeyTO0sDQRSFfRS+EUGwEESxEFG0sbCw8BeIhYVaaCOCoChY2VjZ2Vhoo52CCoqtjYhaWdmJkneVIk3KJEVCvrPshrC7M5CQLlnOd++d2ZnDzmM72hr4NKnZBFuYckm6OUGeBOmGoHaULP7J3eDIv2cyGOfNHij3kWchDtI+oRc+YQVmIA+O/GZOJ+EVfmEYFsHTOcUl7MAfFKEik5kGXCvALkgnhHY4g1DZzO6YoSWsko9hHg7BKJtZllnP0AVrsA0lMMpmpknvCjAIBbDKZjbFTJ1qhDwNS2CVyWyUWbewCVcgeQehOpQwsyFGPoG+KkbWQeTI2je9owyX30wX8oWhp/ADkg5C5j00tsAoz0x5gVEf8A1vUK17t6Gv7XTrQJLJOr0Z+II5OIBl8HREoSuiOzdGnYYHCEhmj/Tqt9ES9dP209YXkhxdEAdAy9SYEeoNCEhmgc56O1pmte9ck+xZGQAA//9VV4s4AAAABklEQVQDADKiNjXpE4ccAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAaCAYAAAAAPoRaAAADZUlEQVR4AeyXWahNURjHzbPMPBgyPMhcUmQmkQdSlKkMkShTJCHygBfCAyWKIkORokQyT0nhSeYxmTKFDBl/v9vet+Pse889+57DvXXO7f8739prf2vtNa/vVqqQw3/5zufq5OdnPmHm25B+FPAwsA+w7UBt48fnu1i5ha0BZaXTfPgpvAh4grV9tv0x6UPQH4pU8sxbqDWes0BbG9sZ7oOazU8tOAsjoRN8hbLSID48GZrBXmgFbcFJHIA17QCZ5vFvJXc+fHuUxA1oDL0g1FoSm2A63ISfUJKaluSQ4fueQfnjgQ2NK3gHD/ZxAjYiX0Qyg4ytgZ0R2CXYirAK4mghzodhCPwL9aPSH3ABkuXMm3fbn2RSdX4Xzi7pUVg70A07D+JqMQVmwnA4A2Mg1Xd5nbaq4NkHrsJHSFQXHibCHdgOEaVqxDu8D0B1sMHurV+kS6NnFHIAR2M9Q5ylaaSrQSbqTuG6cAUaQiNoAfPBreuK6036PUSUqvM6n/IH6sE3yFRvqGAlDIUG4CAswHqwYmJrYFDC22gD6fWwBpyoc1jTfpNkVKk63x53T32XTQfSfSFb+kRF68Br6DPWQV6GrQ9xZOfd72MpZIdlEuke4GF9Het2xURVXOeb47oTPCU3Y1V48JnOFp4pHqzOmtfoiBgVV8XXw+4a1sHEFMpbyCVfk5ypUKSK6rzLcT/ezvo9rAffF6z73ncksyIbP4WaLoLxggeU3+IxLTm7dfA05sBE1DLIeRvYiEnuvAHMQbxWgCOKqeDB52A4ii4p8zLBb8yhgvPQBIbBcngNcTQ4cHZvB8lC45J3C3wgZzcUqbDzWkfSq+gynicgUXuCB1dD5SAd17ifl1LoJHwH96tBkw3kMZaMNxw0l7eDGBY236DHqM6V5VkQRqehT6G10+N4egWOYFess2LDSBbIa8Mrz/1p+Oi1ZShZ8DKNH2dhNX7uQcNn9+kWnq0PE1tOzEtKWY/tNxK1XmN6Y3yjOjvvlXoMv2Jl4X28tYEuR/9JcR+5Asgu0EZ+vUtd9voYR48nL10Z5FzC2fjaQfN05rHUMlI0ZHaWbb/3urG80Zxt60jNc+E5pJSFUzpk4eUi6jgCv6Fc6X90vlx1OLEx+c4njkYupfMzn0uzndjX/MwnjkYupf8AAAD//1hTbO8AAAAGSURBVAMA3k6SNR8pKbUAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAaCAYAAADMp76xAAAC3UlEQVR4AeyWWahNURyHN5I5kfKgZMgsMiuKPClzlCHDAyllyvAgQhlSImSKByJDGd7wYAh5UIYX8zw8UB4MUeZ77/fdzq5z9zl71619zu7Wvf2+9f+vde5e67fWXnvt3TCoY3/1hkt9w+r8Cndmhd7meJOLr4ldQR2msP6CKE+JTaFsiq6wJjsx+iIwtiD2hVegFlM0hxswEfrALyiboobDgS+RPIJ2MBxCbSfZCwvgCfyHsirOsCYOWcBCUGsoGsBmyExJho/jyts9mbgS+sMyyFRJhr/g7Cw0gWkwDyogUyUZ1tg1C2gNvyFzJRnugTtPi+fEXjASMlec4Q44OwazYB+o8OEzz4xihtvg5gy4ui+JPnw/ie5jfyPNTlHDvhTOY2c93Aflw+cEmlGZC1ENomEn9IbZsAHmQL58g9q+kcYRoEZRbIOeoHybjiVpDPvBdwChpkLDxsH8dB1uwxXI18lcxVVvlMvDMJ7kPVwAJ7mJeBDagtKYE3ZraXgJje1hKHwHJ0kIVlP0A8/6McRuUCCNzqD1E9wEL7DD0eShlpN4vHkmdyT/AKdAeeSdIxkIu+ExuDKVxB/g4L6AHpBPhx1wAPz+OEqcBLdAOaav/D9UnOAzYoE0fJpWB3E72FFL6q40oVq7KFuBW8L/cXVmUlcedQ9JHCw8AidQvwwObL/dyb3FTtIXkKbe0WZ/ruJVcvv0Qb9HrpzoZ5MoGo621bbehQscXOOkwVQKV2gt0buicVdLAxoZR7tyz/pQ/6XiR5Tb6h+5+90JkRYqDcPD6PYihG9BjQ2g7meoe9RvkD3U/dLbSnT7EYK7FI6/ijgFnNwK4nw4AkXlBUV/qEWjp4pfb+ElPkRbqLgFCIEniM+Fx6Pm79gITmYI8QQsBU8br1lH7koTCpWGYfextzW/96/5FXLNfSNG5V35SKMPKSEwN8aShuHYzkvxQ6zhUgyWRp/1htNYxaQ+qgAAAP//hYX5wAAAAAZJREFUAwCwJoY1rLrkSAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAxCAYAAABnGvUlAAAKRElEQVR4AeycBag01xmGp+6eeqm7Qo2Wugv1FuqlSltqtLSlSksLLRVaSEKEJMRDnLgLceIkIe5KhHhCXN7n5p9l7v67N3dzZ/fO2Xl+vu8/MrPnfOeZe/e+HJmHV/6TgAQkIAEJSEACEug0AQVbpx+PwUlAAhIohYBxSkAC0ySgYJsmXduWgAQkIAEJSEACLRBQsLUA0SbKIGCUEpCABCQggVIJKNhKfXLGLQEJSEACEpDAahBYlT4VbKuC3U4lIAEJSEACEpDA8gko2JbPyjslIAEJlEHAKCUggbkjoGCbu0fqgCQgAQlIQAISmDcCCrZ5e6JljMcoJSABCUhAAhKYgICCbQJY3ioBCUhAAhKQQJcI9CcWBVt/nrUjlYAEJCABCUigUAIKtkIfnGFLQAJjCTwiV54Yn5U9aamOZnztMenvcfGmPbVZMC8BCZRJQMFW5nMzagnUBBAnH0/hq/GvxV8Tf2z8y2v8o0m7YI9KEMRY+/NTfl78K3Fi/WDSh8VXao9OA7+LN0XL+1KmH5y+npFyW/asNPSNeG30Sz/UfT2VjJfyO5PnWSVp1RjvumnxRXGM7/TfJtMUrLAlhjb4pmlNAhJYDQL8cq9Gv/bZGQIGUjiBexL/gfHPxb8bPydOHXn+mB+achfsrgSxU/w78W/Hr4xfHf9f/N744fH74iu1L6aBo+PXxGs7Kpnvxz8W3yV+XbwNQ4Adm4Z2jdd2WzKM8y9JT4zvGCc9Iunn423b29PgD+MviGP0v0cyf4jXRnyvTuHJcU0CEiiUgIKt0Adn2BJoEECgbZwyszgvTvrj+N/iW8cRSkk6YXcnim3izAIyy/W95D8VR+BwLdmxhgB5+tirD1xgaZL7TnqgOPifGcfnpoRwoZ82hGGaq96V/3aPXxVv2hNSuCN+Vpxnc15SBOpLk7ZpCPJvpkH6arI5PXXMur48aW0HJwObJJoEpkTAZqdKQME2Vbw2LoGZETg5PV0f3yB+SZxZpSSdM8TZ4xPVX+PMsA2Lq1SPNPZmPdj31TvyyYvjN8abxvIgS5dtzzay1Lpps6M1+S8lPT7ODBxi8ZPJIxL3TtqWsbzJrOF2afDWeFOw3ZkyfSHgk12w8/P/t+KIvCSaBCRQGoEH+wIsbTzGK4G+EkCs7ZfB84d7t6TTss+k4fUbvl7yOPuo/p38s+NLGUt2zLJ9ODe1HefL0uZx8WF7WypOrarqlqRtGjNYzKINt/mDVKwT/3P87/EfxZmNY+Yr2VaMWTxm71hqRaA9bahVOMCjrr42GUQveweT1SQggdIIKNhKe2LGK4HRBN6S6gvibD5/ZdJpGfujfprGa/9Z8vjPk7LZfXh5MNWLjFkphMNzUsv+qyQj7SmpZbm0dsbEAYq6zJ6s3LLIWBId1T+HMfZv3PnI5D8Ub9ozU6jbHk4RW7m8ljEOZs6aF1jqZabvn6lkFvE3SdljuE9S7k8yML5/ORAw3B9lBO242TA+96e0wuzdp5Mi3BDqyQ6M2cvmnjWWTRF2zbrBzWYkIIHuE+AXv/tR9iVCxymBh0aAfWssd/0rHz8g/p/4tAxBiMgY5YgxZn7G9Y2YeUMu/iLOEh2nKJMdaTenln1XtSNGD2vU8fkUFxmChFOazUpED6KGwwF1/buTQdwlGRgHEeq+htMTBnctzrAfbnFNVbE/j7rmzBtLtK9KJSdlkwyMwxYsXQ/3R/nI3DVu/yFLnRfl+mbxg+IcahgWbHBAyOXygvFdj1AdFfPCDf4nAQl0mwC/xN2O0OgkIIFxBPj9fWsuckqQV1nwB5oZsPenDhGXpGL/FicWOYjwhVRwQjNJhVj6QDKcXGTJcJPk14n/I87sFZ9Jdi1j79TtqR3niJBcXmR8BjH339RuEUdYcTqUjfGMIVVrGe2wfFo7QoNZoro8SsxwMvQlQy0x88hnL009cbwx6U/ie8WbBru67eGUfpv31vkbkmE/XpKB0T7iEAFIf2/KFfaawX3UkixtD/dHGb7Ds3dpqmLmkWVpDpnQHvvXLssFxHCSgcGBgw51BT8H7Klj5q2uM51jAg5t/giM+7Kcv5E6IgnMHwFOgW6ZYfG6ivqPOzNt/AHndRIsq7EEhvhhJoaZHk5LclqR118gzDigcFPaQLwxA8Nnzk6ZGZwkaxn1vDZjlCNUEBvND/HS1j1TsWH8zXFmfjgAwGtHEFK0g2DMpRXbKWmBZdP6e+2XKW8UR8htlZR9XbzWg1ef0HeqVmTMvH1iTQssT9IHy8OII15TgrOP7de5Z9v4Sg3xR5sINg4y0B4nbT+SDDOX2yetx05c8EjVgvHOuzOSg0USTQISKI1A/ctdWtzGKwEJVAuzZK8LCIQQMzLJVux/oo79YYi0K1LJMiWvlmAv1zEpsx+MfVXMqiHiUlVxYIFlu0NSQBgs9/Rmbl/SmIUiptfmLtpFMFxdVRUCkTr2e3GiMpeXNMTRsBgc/gBC88xU1pvt/588fb4iKcugCEPyf0y5DWPD/+/TEDNX8EcssyT6+tS9N/6eOCdGEbLJrtgQYIyHPjgFSoMsi9IfzstxEecIYoQ58XEPzs8IwpG8LgEJFEhAwVbgQzNkCUxIgFd+MAPHXic2viPkKPOyXZbtLk977Bl7YVL+4DMbc1ryXTJm6Vj+WyomZs0QJcyyMa6l7m3jGvvodkhDLPcm6Ywhhn+VaFhuTVKxvw0Rz/OnrEtAAgUSULCNeWhWS2COCLA8ynB4RxuHEhA27IFiefDcXGAvFC9V5XUbzD7tm7pS7cIEzoZ/lnuTnbpx0ANBNPWOltkBp10Rq8xI1h/5bDLsH2TvYLKaBCRQIgEFW4lPzZglMBkBZtPqT9R5UrxZT7n2ur60lPg5ZcnS6Cxip7+dZ9HRMvtgyZm9bMRVf2TzZHhPXxJtFQjYpQRaIaBgawWjjUhAAhKQgAQkIIHpEVCwTY+tLUugDAJGKQEJSEACnSegYOv8IzJACUhAAhKQgAT6TqAEwdb3Z+T4JSABCUhAAhLoOQEFW89/ABy+BCQggf4QcKQSKJeAgq3cZ2fkEpCABCQgAQn0hICCrScP2mGWQcAoJSABCUhAAqMIKNhGUbFOAhKQgAQkIAEJdIjAhIKtQ5EbigQkIAEJSEACEugJAQVbTx60w5SABCTQKQIGIwEJTERAwTYRLm+WgAQkIAEJSEACsyegYJs9c3ssg4BRSkACEpCABDpDQMHWmUdhIBKQgAQkIAEJzB+BdkakYGuHo61IQAISkIAEJCCBqRFQsE0NrQ1LQAISKIOAUUpAAt0noGDr/jMyQglIQAISkIAEek5AwdbzH4Ayhm+UEpCABCQggX4TULD1+/k7eglIQAISkEB/CBQ8UgVbwQ/P0CUgAQlIQAIS6AcBBVs/nrOjlIAEyiBglBKQgARGElCwjcRipQQkIAEJSEACEugOAQVbd55FGZEYpQQkIAEJSEACMyegYJs5cjuUgAQkIAEJSEACkxFQsE3Gy7slIAEJSEACEpDAzAncDwAA///K5xyiAAAABklEQVQDAPanV3KCqbJzAAAAAElFTkSuQmCC>