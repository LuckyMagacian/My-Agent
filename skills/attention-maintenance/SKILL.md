---
name: attention-maintenance
description: "短期上下文维护系统 v11：最终形态。Focus → Active Decision → ADR（Trace）→ Landmarks。适用于单项目、几十轮对话、持续数周开发。"
---

# 短期上下文维护系统 v11

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：决策历史比知识库存量重要。Landmarks 记录思路演化，快速恢复整个项目思维轨迹。

## 最终结构（按重要性）

```
★★★★★ Focus            当前讨论什么
★★★★★ Active Decision  当前决定什么
★★★★★ ADR + Trace      为什么这样决定
★★★★★ Session Summary  最近发生什么
★★★★★ Landmarks        思路如何演化
★★★★ Current Stage     讨论到哪一步
★★★★ Current State     当前进展
★★★  Constraints       边界条件
★★   Goal              目标方向
★    Identity          项目身份
```

---

## Focus（★★★★★）

### 作用

**当前讨论什么**，决定检索方向。

### 输出格式

```xml
<focus importance="critical">
  <theme>当前讨论主题</theme>
  <scope>涉及范围</scope>
</focus>
```

### 示例

```xml
<focus importance="critical">
  <theme>Selection Context 实现</theme>
  <scope>状态管理、变更监听、生命周期</scope>
</focus>
```

### 限制

```xml
<Focus max="1"/>  <!-- 永远单例 -->
```

---

## Active Decision（★★★★★）

### 作用

**当前决定什么**，具体决策问题。

### 输出格式

```xml
<active-decision importance="critical">
  <question>决策问题</question>
  <authority>[ai|user]</authority>
  <options>
    <option id="A" status="[considering|rejected|accepted]">
      方案描述
    </option>
  </options>
</active-decision>
```

### Authority 简化

| Authority | AI 行为 |
| --- | --- |
| ai | AI 可推理决定 |
| user | AI **不能**决定，必须询问用户 |

### 示例

```xml
<active-decision importance="critical">
  <question>Observer 生命周期如何管理</question>
  <authority>ai</authority>
  <options>
    <option id="A" status="considering">手动 dispose</option>
    <option id="B" status="considering">自动垃圾回收</option>
  </options>
</active-decision>
```

### 限制

```xml
<Active-Decision max="1"/>  <!-- 永远单例 -->
```

---

## ADR + Trace（★★★★★）

### 作用

**为什么这样决定**，防止重复讨论已否决方案。

### 输出格式

```xml
<adr>
  <record id="001" importance="high">
    <scope>[architecture|module|implementation]</scope>
    <decision>决策内容</decision>
    <trace>
      <option id="A" status="rejected">
        方案描述
        <reason>为什么拒绝</reason>
      </option>
      <option id="B" status="accepted">
        方案描述
        <reason>为什么接受</reason>
      </option>
    </trace>
  </record>
</adr>
```

### 示例

```xml
<adr>
  <record id="001" importance="high">
    <scope>architecture</scope>
    <decision>Selection 与 Document 分离</decision>
    <trace>
      <option id="A" status="rejected">
        Selection 作为 Document 子状态
        <reason>耦合度高，无法独立演进</reason>
      </option>
      <option id="B" status="accepted">
        独立 Selection Context
        <reason>可独立演进，符合 Plugin First</reason>
      </option>
    </trace>
  </record>
</adr>
```

### 核心价值

**Trace 比决策本身重要**：否决理由防止未来重开讨论。

---

## Landmarks（★★★★★，新增）

### 作用

**思路如何演化**，记录关键认知变化，快速恢复整个项目思维轨迹。

### 与 ADR 的区别

| ADR | Landmarks |
| --- | --- |
| 最终决策 | 关键认知变化 |
| 例：选择 Observer 模式 | 例：发现 NodeView 不适合作为状态容器 |

### 输出格式

```xml
<landmarks>
  <landmark id="L001" importance="high">
    <insight>关键认知</insight>
    <context>背景</context>
  </landmark>
</landmarks>
```

### 示例

```xml
<landmarks>
  <landmark id="L001" importance="high">
    <insight>Selection 应该从 Document 中拆出</insight>
    <context>发现 Selection 状态变更不需要触发 Document 更新</context>
  </landmark>
  <landmark id="L002" importance="high">
    <insight>Observer 必须显式销毁</insight>
    <context>发现 Observer 导致内存泄漏</context>
  </landmark>
  <landmark id="L003" importance="normal">
    <insight>NodeView 不适合作为状态容器</insight>
    <context>NodeView 生命周期由 PM 管理，不可控</context>
  </landmark>
</landmarks>
```

### 限制

```xml
<Landmarks max="10"/>
```

### 价值

快速恢复思维轨迹，比大量知识条目更有价值。

---

## Session Summary（★★★★★）

### 作用

**最近发生什么**，本轮讨论产出。

### 职责边界

只负责"本轮产出"，不与 Current State 重叠。

### 输出格式

```xml
<session-summary>
  <new-decisions importance="high">
    - 本轮新决策
  </new-decisions>
  <new-findings importance="normal">
    - 本轮新发现
  </new-findings>
  <open-questions importance="normal">
    - 待解决问题
  </open-questions>
</session-summary>
```

### 示例

```xml
<session-summary>
  <new-decisions importance="high">
    - Selection 与 Document 分离
    - 使用 Observer 模式
  </new-decisions>
  <new-findings importance="normal">
    - Selection 更新不触发 Document 变更
    - Observer 生命周期需手动管理
  </new-findings>
  <open-questions importance="normal">
    - Observer dispose 时机
    - Selection 缓存策略
  </open-questions>
</session-summary>
```

### 更新时机

事件驱动：决策完成、发现新认知、遇到阻碍。

---

## Current Stage（★★★★）

### 作用

**讨论到哪一步**，贴近对话而非项目管理。

### 与 Milestone 的区别

| Milestone | Current Stage |
| --- | --- |
| 项目执行阶段 | 对话讨论阶段 |
| design → implement → test | exploring → deciding → implementing → validating |

### 输出格式

```xml
<current-stage importance="high">
  <name>当前讨论主题</name>
  <status>[exploring|deciding|implementing|validating|done]</status>
</current-stage>
```

### 状态说明

| 状态 | 说明 |
| --- | --- |
| exploring | 探索问题，收集信息 |
| deciding | 讨论决策，权衡方案 |
| implementing | 实现方案，编写代码 |
| validating | 验证效果，调整优化 |
| done | 完成，准备下一阶段 |

### 示例

```xml
<current-stage importance="high">
  <name>Selection Context 设计</name>
  <status>deciding</status>
</current-stage>
```

---

## Current State（★★★★）

### 作用

**当前进展**，明确正在做什么。

### 输出格式

```xml
<current-state>
  <doing importance="high">正在做什么</doing>
  <blocked importance="normal">阻碍点</blocked>
  <evidence importance="normal">为什么 blocked</evidence>
  <next importance="high">下一步</next>
</current-state>
```

### 示例

```xml
<current-state>
  <doing importance="high">分析 Observer 生命周期</doing>
  <blocked importance="normal">不确定 GC 时机</blocked>
  <evidence importance="normal">
    查看 Observer.ts 未发现 dispose 调用点
  </evidence>
  <next importance="high">查看 Plugin 生命周期</next>
</current-state>
```

---

## Constraints（★★★）

```xml
<constraints>
  <hard importance="critical">
    - 硬约束（违反 → block）
  </hard>
  <soft importance="high">
    - 软约束（违反 → warn）
  </soft>
</constraints>
```

---

## Goal（★★）

```xml
<goal importance="high">
  <primary>项目目标</primary>
</goal>
```

---

## Identity（★）

```xml
<identity>
  <project importance="critical">Block Cheese</project>
  <tech-stack importance="critical">React, Tiptap v3</tech-stack>
</identity>
```

---

## 弱化的组件

### Pending Decisions（简化 Decision Queue）

```xml
<pending-decisions importance="normal">
  - Observer 生命周期
  - Selection 缓存策略
  - 多 Selection 支持
</pending-decisions>
```

无需完整结构，列表即可。

---

## 删除的组件

| 组件 | 原因 |
| --- | --- |
| Project Knowledge | 合并到 ADR |
| Activation | 简化为直接引用 ADR/Landmarks |
| Decision Queue 完整结构 | 简化为 Pending Decisions 列表 |
| Milestone 任务树 | 改为 Current Stage |

---

## 条目限制

```xml
<limits>
  <!-- 单例 -->
  <Focus max="1"/>
  <Active-Decision max="1"/>
  <Current-Stage max="1"/>
  <Current-State max="1"/>
  <Session-Summary max="1"/>

  <!-- 队列 -->
  <ADR max="30"/>
  <Landmarks max="10"/>
  <Constraints max="10"/>
  <Pending-Decisions max="10"/>
</limits>
```

---

## 状态机流转

```
┌─────────────────────────────────────────────────────────────┐
│                     核心状态机                               │
│  Focus → Active Decision → ADR + Trace → Landmark          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     进度追踪                                 │
│  Current Stage → Current State → Session Summary           │
└─────────────────────────────────────────────────────────────┘
```

---

## 使用示例

```xml
<!-- Focus（当前讨论什么） -->
<focus importance="critical">
  <theme>Selection Context 实现</theme>
  <scope>状态管理、变更监听</scope>
</focus>

<!-- Active Decision（当前决定什么） -->
<active-decision importance="critical">
  <question>Observer 生命周期如何管理</question>
  <authority>ai</authority>
  <options>
    <option id="A" status="considering">手动 dispose</option>
    <option id="B" status="considering">自动垃圾回收</option>
  </options>
</active-decision>

<!-- ADR + Trace（为什么这样决定） -->
<adr>
  <record id="001" importance="high">
    <scope>architecture</scope>
    <decision>Selection 与 Document 分离</decision>
    <trace>
      <option id="A" status="rejected">
        Selection 作为 Document 子状态
        <reason>耦合度高</reason>
      </option>
      <option id="B" status="accepted">
        独立 Selection Context
        <reason>可独立演进</reason>
      </option>
    </trace>
  </record>
</adr>

<!-- Landmarks（思路如何演化） -->
<landmarks>
  <landmark id="L001" importance="high">
    <insight>Selection 应该从 Document 中拆出</insight>
    <context>发现 Selection 状态变更不需要触发 Document 更新</context>
  </landmark>
  <landmark id="L002" importance="high">
    <insight>Observer 必须显式销毁</insight>
    <context>发现 Observer 导致内存泄漏</context>
  </landmark>
</landmarks>

<!-- Current Stage（讨论到哪一步） -->
<current-stage importance="high">
  <name>Selection Context 设计</name>
  <status>deciding</status>
</current-stage>

<!-- Current State（当前进展） -->
<current-state>
  <doing importance="high">分析 Observer 生命周期</doing>
  <blocked importance="normal">不确定 GC 时机</blocked>
  <evidence importance="normal">未发现 dispose 调用点</evidence>
  <next importance="high">查看 Plugin 生命周期</next>
</current-state>

<!-- Session Summary（最近发生什么） -->
<session-summary>
  <new-decisions importance="high">
    - Selection 与 Document 分离
    - 使用 Observer 模式
  </new-decisions>
  <new-findings importance="normal">
    - Observer 生命周期需手动管理
  </new-findings>
  <open-questions importance="normal">
    - Observer dispose 时机
  </open-questions>
</session-summary>

<!-- Pending Decisions -->
<pending-decisions importance="normal">
  - Selection 缓存策略
  - 多 Selection 支持
</pending-decisions>
```

---

## 执行流程

```
用户输入
    ↓
检查 Focus（当前讨论什么）
    ↓
检查 Active Decision（当前决定什么）
    ↓
检查 ADR（已决定，避免重复）
    ↓
检查 Landmarks（思维轨迹）
    ↓
检查 Authority（AI 可决定 / 需用户决定）
    ↓
更新 Current State
    ↓
更新 Session Summary（本轮产出）
```

---

## 对比：v10.5 vs v11

| 项目 | v10.5 | v11 |
| --- | --- | --- |
| 核心组件 | 多个 | **5 个五星组件** |
| Landmarks | 无 | **新增，记录思维轨迹** |
| Milestone | 任务树 | **改为 Current Stage** |
| Decision Queue | 完整结构 | **简化为列表** |
| Owner | architect/developer/user | **简化为 ai/user** |
| Session Summary | done/decided/pending | **new-decisions/findings/questions** |
| Project Knowledge | 保留 | **删除，合并到 ADR** |
| Activation | 保留 | **删除，直接引用** |

---

## 执行原则

1. **Focus 单例**：永远只有一个当前讨论主题
2. **Active Decision 单例**：永远只有一个当前决策问题
3. **Trace 防重开**：否决理由防止未来重开讨论
4. **Landmarks 记轨迹**：关键认知变化，快速恢复思维
5. **事件驱动更新**：决策完成、发现认知时更新
6. **Authority 简化**：只有 ai/user 两种

---

## 注意事项

1. **Landmarks 是关键**：比知识条目更有价值
2. **Trace 比决策重要**：否决理由比接受理由更有价值
3. **Stage 贴近对话**：exploring/deciding/validating，不是项目管理
4. **Session Summary 职责**：只记录本轮产出，不与 State 重叠
5. **authority=user**：AI 必须询问用户，不能自动决定

---

## 总结

对于「单项目、几十轮对话、持续数周的软件设计与开发」，v11 已经是完成形态：

- **Focus** → 当前讨论什么
- **Active Decision** → 当前决定什么
- **ADR + Trace** → 为什么这样决定
- **Landmarks** → 思路如何演化
- **Session Summary** → 最近发生什么

覆盖 90% 以上的上下文恢复需求。再增加结构收益快速下降，维护成本上升。
