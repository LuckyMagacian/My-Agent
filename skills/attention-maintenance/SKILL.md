---
name: attention-maintenance
description: "短期上下文维护系统 v19 + workspace：工作记忆模型。Decision（问题）+Knowledge（结论）+Evidence（来源标记：constraint/fact/test/hypothesis）+State（doing/until）。4 组件最小充分集 + 跨对话工作上下文快照 + 架构决策库（promote/replace/remove 失效机制）。"
---

# 短期上下文维护系统 v19

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：真正的"工作记忆（Working Memory）"模型，而非压缩过的项目档案系统。

**v19 核心改进**：
- ADR → Knowledge，语义对齐"当前有效前提"
- 删除 confidence，从 Evidence 推导
- 删除 Next，未来目标属于计划不是记忆
- Evidence 增加 constraint 类型

## 最终结构

```xml
<decision>
Observer 生命周期如何管理
</decision>

<knowledge>
Selection 与 Document 分离
使用 Observer
</knowledge>

<evidence>
[constraint] 必须兼容 Tiptap Extension API
[fact] Plugin 有 destroy 生命周期
[hypothesis] Observer 导致泄漏
</evidence>

<state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</state>
```

---

## 组件说明

### Decision（当前问题）

```xml
<decision>
Observer 生命周期如何管理
</decision>
```

**只回答**：当前在解决什么？

**关键规则**：
- Decision 存在 = 当前活跃
- Decision 不存在 = 无活跃问题
- 无需 active/resolved 属性

**职责约束**：
- Decision = 要解决的问题
- State.doing = 当前执行动作
- 两者不可重复

**正确示例**：
```xml
<decision>
Observer 生命周期如何管理
</decision>
<state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</state>
```

**错误示例**：
```xml
<decision>
验证 Plugin.destroy 覆盖范围
</decision>
<state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</state>
```
↑ Decision 写成了动作，与 State.doing 重复

---

### Knowledge（已确定结论）

```xml
<knowledge>
Selection 与 Document 分离
使用 Observer
</knowledge>
```

**只回答**：已经确定什么？

**命名原因**：
- ADR（Architecture Decision Record）天然包含决策、原因、背景、历史
- v19 中这些条目只是"当前有效前提"，不是完整的决策记录
- Knowledge 更准确描述"后续推理需要知道的事实"

**关键特点**：
- 只记录最终结论内容
- 不编号、不分级
- 不记录 superseded/rejected

**Freshness 规则（relevance-first）**：
- Knowledge 是当前推理的前提条件，不是项目历史
- 超出 max=8 时，删除与当前 Decision 最不相关的条目
- 判断依据：是否仍影响当前 Decision

**示例**：
```
当前 Decision: 实现 WeakMap 缓存

保留: Selection 与 Document 分离（影响缓存设计）
保留: 使用 WeakMap 作为缓存（直接相关）
删除: Plugin.destroy 作为 dispose 时机（已沉淀，不影响缓存实现）
```

**约束**：max=8

---

### Evidence（当前证据 + 来源标记）

```xml
<evidence>
[constraint] 必须兼容 Tiptap Extension API
[fact] Plugin 有 destroy 生命周期
[test] destroy 已覆盖 NodeView 销毁
[hypothesis] Observer 可能导致泄漏
</evidence>
```

**只回答**：为什么这样推理？

**来源标记**：
| 标记 | 含义 | 推理权重 |
| --- | --- | --- |
| constraint | 硬约束，不可违反 | 最高 |
| fact | 已确认的事实 | 高 |
| test | 实验或测试结果 | 中高 |
| hypothesis | 推测，尚未验证 | 低 |

**constraint 的价值**：
- 软件设计中大量关键前提属于约束
- 例如：必须兼容 Tiptap、不能修改 ProseMirror Core、必须支持协同编辑
- 这些既不是 fact/test/hypothesis，也不是结论，却强烈影响推理

**生命周期规则**：
```
Evidence 生命周期 = Decision 生命周期

Decision 消失 → Evidence = ∅
```

**confidence 推导规则**（隐式，不存储）：
```
大量 hypothesis → 推测阶段
fact + hypothesis → 部分验证
fact + test + constraint → 已验证
```

**约束**：max=5

---

### State（当前动作）

```xml
<state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</state>
```

**只回答**：当前在执行什么？

**结构化字段**：
- `doing`：当前动作
- `until`：完成条件

**confidence 不存储的原因**：
- confidence 是 Derived State，不是 Primary State
- 可从 Evidence 类型组合推导
- 手工维护容易失真：新增 hypothesis 后 confidence 已过期
- 工作记忆优先保存原始证据，而非"我觉得有 70% 把握"

**生命周期绑定**：
- Decision 存在 ⇔ State 存在
- Decision 消失 → State 清空
- 不存在"无 Decision 的 State"
- 新 Decision 产生 → 新 State 随之产生

---

## 被删除的组件

### Focus（讨论对象）

**删除原因**：由 Decision 内容推导

### Stage（独立组件）

**删除原因**：由 Decision 内容推导

### Decision.stage

**删除原因**：由 Decision 内容推导

### Decision.active/resolved

**删除原因**：Decision 存在即活跃，resolved 后结论进入 Knowledge

### ADR（→ Knowledge）

**重命名原因**：ADR 含决策/原因/背景/历史，v19 中只是"当前有效前提"

### State.result

**删除原因**：结论进入 Knowledge

### State.confidence

**删除原因**：Derived State，从 Evidence 推导

### ADR.Level / Knowledge.Level

**删除原因**：对工作记忆无价值

### Next（→ 删除）

**删除原因**：未来目标属于计划不是记忆，极易变化

### Pending.? backlog

**删除原因**：属于项目管理，不是工作记忆

---

## 条目限制

```xml
<limits>
  <!-- 单例 -->
  <Decision max="1"/>
  <State max="1"/>

  <!-- 队列 -->
  <Knowledge max="8"/>
  <Evidence max="5"/>
</limits>
```

---

## 状态流转

```
Decision 存在
    ↓
收集 Evidence
    ↓
Evidence 充分（fact + test 为主）
    ↓
State.until 满足
    ↓
结论进入 Knowledge
    ↓
Decision 消失
    ↓
Evidence = ∅（自动清空）
State = ∅（自动清空）
```

**注意**：
- Decision 存在 ⇔ State 存在。不存在"无 Decision 的 State"。
- 没有"Next"环节。Decision 消失后，新 Decision 由对话上下文自然产生，新 State 随之产生。

---

## 对比：v18 vs v19

| 项目 | v18 | v19 |
| --- | --- | --- |
| ADR | `<adr>` | **`<knowledge>`** |
| Evidence 来源标记 | fact/test/hypothesis | **+ constraint** |
| State.confidence | 存在 | **删除，从 Evidence 推导** |
| Next | 存在 | **删除，属于计划不是记忆** |
| 组件数量 | 5 | **4** |

---

## 使用示例

### 完整示例（决策中）

```xml
<decision>
Observer 生命周期如何管理
</decision>

<knowledge>
Selection 与 Document 分离
使用 Observer
</knowledge>

<evidence>
[constraint] 必须兼容 Tiptap Extension API
[fact] Plugin 有 destroy 生命周期
[hypothesis] Observer 导致泄漏
</evidence>

<state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</state>
```

---

### 决策完成后

```xml
<knowledge>
Selection 与 Document 分离
使用 Observer
Plugin.destroy 作为 dispose 时机
</knowledge>

<!-- Decision 消失 → Evidence 自动清空 → State 自动清空 -->
<evidence>
</evidence>

<state>
</state>
```

**注意**：Decision 消失后 State 也清空。新 State 由新 Decision 自然产生，不存在"无 Decision 的 State"。

---

### 实现阶段

```xml
<decision>
实现 Selection 缓存逻辑
</decision>

<knowledge>
Selection 与 Document 分离
使用 Observer
Plugin.destroy 作为 dispose 时机
使用 WeakMap 作为缓存
</knowledge>

<evidence>
[fact] WeakMap 自动清理引用
[test] Selection 对象生命周期可控
</evidence>

<state>
doing: 实现 WeakMap 缓存
until: 缓存命中率测试通过
</state>
```

---

## 执行原则

1. **Decision 存在即活跃**：无需 active/resolved 属性
2. **Decision = 问题，State.doing = 动作**：两者不可重复
3. **Decision ⇔ State 绑定**：Decision 存在 ⇔ State 存在，不存在"无 Decision 的 State"
4. **Knowledge 只存最终结论**：不记录 Level/superseded/rejected
5. **Knowledge Freshness**：relevance-first，删除与当前 Decision 最不相关的条目
6. **Evidence 来源标记**：constraint/fact/test/hypothesis，区分推理权重
7. **Evidence 自动清空**：Decision 消失 → Evidence = ∅
8. **State 自动清空**：Decision 消失 → State = ∅
9. **confidence 不存储**：从 Evidence 类型组合推导
10. **结论进入 Knowledge**：不留在 State.result
11. **不存 Next**：未来目标由对话上下文自然产生

---

## 注意事项

1. **只保留核心记忆**：删除所有推导信息
2. **Decision 无状态属性**：存在即活跃，消失即结束
3. **Decision/State 职责分离**：Decision 是问题，State.doing 是动作
4. **Decision ⇔ State 绑定**：同时存在，同时消失
5. **Evidence 自动遗忘**：决策结束自动清空
6. **Evidence 来源标记**：constraint > fact > test > hypothesis
7. **Knowledge 不膨胀**：max=8，relevance-first 遗忘
8. **confidence 不存储**：从 Evidence 推导，避免派生信息失真
9. **不存 Next**：未来目标属于计划，不是工作记忆

---

## 总结

v19 是工作记忆模型的不可再压缩形态：

| 组件 | 回答的问题 | 推理链位置 |
| --- | --- | --- |
| Decision | 当前在解决什么 | Problem |
| Knowledge | 已经确定什么 | Known Facts |
| Evidence | 为什么这样推理 | Evidence |
| State | 当前在执行什么 | Current Action |

**形成推理链**：
```
Problem
    ↓
Known Facts
    ↓
Evidence
    ↓
Current Action
```

**v19 改进**：
- ADR → Knowledge — 语义对齐"当前有效前提"
- 删除 confidence — Derived State，从 Evidence 推导
- 删除 Next — 未来目标属于计划不是记忆
- Evidence + constraint — 软件设计中的硬约束

**不可再压缩**：再压缩会损失恢复能力，再增加会走向项目档案系统。

**4 组件 = 短期上下文维护的最小充分集**。

## 版本演进记录

- v1-2:  行为检测模式（无记忆结构）
- v11:   10 组件，全面但冗余
- v12:   7 组件，极简收敛
- v13:   8 组件，信息密度优化
- v14:   7 组件，工作记忆模型转折
- v15:   5 组件，删除冗余
- v16:   5 组件，最小充分集探索
- v17:   5 组件，语义精炼
- v18:   5 组件，语义对齐
- v19:   4 组件，MVP Stable Version

---

# attention-workspace：脱离内存的短期记忆模块

## 设计目标

**解决**：v19 工作记忆纯对话内维护，对话结束即消失，下次对话需重新建立上下文。

**定位**：v19 的独立外挂层，不修改 v19 的 4 组件结构。持久化的是 **Workspace Snapshot**（工作上下文快照），不是 Knowledge Base（知识库）。类比 IDE 恢复上次打开的文件、光标位置、未完成任务——这是 Workspace，不是 Memory。

**核心哲学对齐**：v19 的遗忘机制是 **relevance-first**（按相关性淘汰），workspace 层必须遵循同一原则，不引入时间衰减遗忘。两套遗忘机制会相互冲突。

**原则**：
- 持久化的是"工作上下文快照"，不是项目档案
- 恢复的记忆是"建议"，Claude 有权拒绝不相关的恢复
- 不改变 v19 的任何规则（max 限制、生命周期、relevance-first）
- Knowledge 遗忘 = relevance-first，不是 time-first

## 持久化范围

| 组件 | 持久化策略 | 理由 |
|------|-----------|------|
| Principles | 全量持久化（无时间戳，带 reason，带失效机制） | 架构决策记录，可长期有效，可被替换/废弃 |
| Decision | 条件持久化为 `pending-decision` | 未解决的 Decision 恢复为待确认状态，不直接进入 v19 |
| State | 条件持久化（随 pending-decision） | pending-decision 不存在时 State 无持久化价值 |
| Evidence | 不持久化 | Evidence 生命周期=Decision 生命周期，跨对话后来源标记失效 |

## 命名说明：Knowledge → Principles

v19 中使用 `<knowledge>` 存储已确定结论。但持久化后，这些条目包含 **Decision + Reason**，已不再是单纯的"知识"，而是"架构决策记录"：

```
<item>
使用 WeakMap
<reason>自动释放引用防泄漏</reason>
</item>
```

这包含：
- Decision：使用 WeakMap
- Reason：自动释放引用防泄漏

因此持久化层使用 `<principles>` 而非 `<knowledge>`，语义更准确：
- **Knowledge**（v19）：当前有效前提，对话内即时可追溯
- **Principles**（workspace）：架构决策记录，跨对话需要 reason 才可追溯

**注意**：v19 内部仍使用 `<knowledge>`，只在 workspace 持久化层使用 `<principles>`。Restore 时 `<principles>` 条目进入 v19 的 `<knowledge>` 区域。

## 存储位置

```
skills/attention-maintenance/persistence/
  workspace.xml                   # 工作上下文（pending-decision + state）
  principles.xml                  # 架构决策库（已确定结论 + reason）
```

**拆分理由**：Workspace 和 Principles 生命周期不同。
- Workspace（pending-decision + state）：强时效，Decision 解决即清空
- Principles：弱时效，结论可长期有效，但可被替换/废弃
- 拆分后：clear workspace 不会误删 principles；Promotion 也更自然

**无 archive**：v19 是工作记忆，只关心当前状态，不关心历史状态。archive 是项目历史，不是工作记忆。

## workspace.xml 格式

```xml
<workspace>
  <pending-decision>
  Observer 生命周期如何管理
  </pending-decision>

  <state>
  doing: 验证 Plugin.destroy 覆盖范围
  until: 覆盖所有销毁路径
  </state>
</workspace>
```

**Decision 已解决时**：

```xml
<workspace>
  <!-- 无未解决问题 -->
</workspace>
```

**格式要点**：
- State 必须依附 pending-decision：无 pending-decision 时 workspace 为空
- 与 v19 保持一致：Decision ⇔ State 绑定

## principles.xml 格式

```xml
<principles>
<item>
Selection 与 Document 分离
<reason>Document 变更时需独立追踪选区</reason>
</item>

<item>
使用 Observer
<reason>监听 Document 变更触发更新</reason>
<avoid>MutationTracker 复杂度过高</avoid>
</item>

<item status="replaced-by" ref="MutationTracker">
使用 Observer
<reason>监听 Document 变更触发更新</reason>
</item>

<item status="removed">
Observer 全局共享实例
<reason>已被废弃，改为按 Plugin 隔离</reason>
</item>

<item>
Plugin.destroy 作为 dispose 时机
<reason>Observer 需在插件销毁时清理</reason>
</item>

<item>
使用 WeakMap 作为缓存
<reason>自动释放引用防止内存泄漏</reason>
<avoid>Map 会导致强引用无法 GC</avoid>
</item>
</principles>
```

### reason 字段规则

- **必填**：每个 item 必须附带 `<reason>`
- **长度限制**：≤ 50 字
- **作用**：恢复后保持可解释性——"为什么这样做？"
- **本质**：ADR Summary（架构决策摘要），不是标签

### avoid 字段规则

- **可选**：记录"为什么不选其他方案"的极简反向理由
- **长度限制**：≤ 30 字
- **作用**：恢复后回答"为什么不那样做？"。没有 avoid 的条目跨对话后可能被重新质疑
- **本质**：ADR Alternatives 的极简形式，不是完整方案对比

**为什么需要 avoid**：
- reason 回答"为什么这样做"
- avoid 回答"为什么不那样做"
- 两者组合 = 最小可追溯的决策记录
- 示例：`使用 WeakMap` + `reason: 自动释放引用` + `avoid: Map 导致强引用无法 GC`

**对比**：

| 内容 | 位置 | 长度 | 回答的问题 | 生命周期 |
|------|------|------|-----------|---------|
| Evidence | v19 `<evidence>` | 不限 | 为什么这样推理 | Decision 生命周期 |
| reason | principles.xml `<reason>` | ≤ 50 字 | 为什么这样做 | Principle 生命周期 |
| avoid | principles.xml `<avoid>` | ≤ 30 字 | 为什么不那样做 | Principle 生命周期 |

### 失效机制

Principles 不是只增不减的。架构演进中决策会被替换或废弃。三种失效操作：

| 操作 | 含义 | 格式 |
|------|------|------|
| **promote** | 长期稳定 → 迁移到 MEMORY.md | 从 principles.xml 删除 |
| **replace** | 被新决策替代 | `status="replaced-by" ref="{新决策关键词}"` |
| **remove** | 直接废弃 | `status="removed"` |

**replace 示例**：
```xml
<!-- 旧决策：被 MutationTracker 替代 -->
<item status="replaced-by" ref="MutationTracker">
使用 Observer
<reason>监听 Document 变更触发更新</reason>
</item>

<!-- 新决策 -->
<item>
使用 MutationTracker 替代 Observer
<reason>Observer 无法追踪局部变更，MutationTracker 支持 Range 级粒度</reason>
</item>
```

**remove 示例**：
```xml
<item status="removed">
Observer 全局共享实例
<reason>已被废弃，改为按 Plugin 隔离</reason>
</item>
```

**Restore 时处理规则**：
- `status` 无（默认）= active → 正常恢复
- `status="replaced-by"` → 不恢复，如 ref 条目存在则恢复 ref 条目
- `status="removed"` → 不恢复

**为什么保留 replaced-by/removed 条目而不直接删除**：
- 保留失效记录可防止"重新做出已废弃的决策"
- 体积极小（每条 ≤ 100 字），不构成膨胀风险
- 如 principles.xml 条目超过 max=16，优先清理 removed 条目

### Merge + 失效的完整规则

```
principles.xml（旧） + v19 Knowledge（当前） → principles.xml（新）
```

| 场景 | 行为 |
|------|------|
| 旧有(active) + 新有 | 保留（去重），reason 以新为准 |
| 旧有(active) + 新无 | 保留（未使用 ≠ 无效） |
| 旧有(replaced-by) + 新有同内容 | 升级为 active，更新 reason |
| 旧无 + 新有 | 新增 |
| 旧有(active) + 新有矛盾内容 | 旧条目标记 replaced-by |

## 恢复机制

### 三级恢复策略

SessionStart 时，根据 **LLM 相关性判断** 自动选择恢复策略：

| 判断结果 | 策略 | 行为 |
|---------|------|------|
| 高相关 | **Auto**（自动恢复） | Principles + pending-decision 全部恢复 |
| 中相关 | **Prompt**（提示确认） | 显示快照摘要，询问是否恢复 |
| 低相关 / 无关 | **Ignore**（忽略） | 不恢复，不提示 |

### 相关性判断：LLM Judgement

语义相关性无法用数值公式客观定义，这是 LLM 擅长的事。不伪造数值评分。

**判断 Prompt**：

```
Given:
- Current topic: {用户第一条消息的核心主题}
- Pending decision: {workspace.xml 中的 pending-decision}
- Principles summary: {principles.xml 中 active 条目的摘要}

Output one of:
- HIGH: same project, same module, or direct dependency
- MEDIUM: same project, different module, shared tech stack
- LOW: different project or unrelated domain
```

**映射**：

| LLM 输出 | 策略 |
|----------|------|
| HIGH | Auto |
| MEDIUM | Prompt |
| LOW | Ignore |

**为什么不用数值评分**：
- "主题重叠 × 3 + 实体重叠 × 2"看似精确，实则每个维度都无法客观定义
- 不同模型对"主题重叠"判断不同，数值不可复现
- LLM 天然擅长语义相关性判断，直接用 LLM Judgement 更可靠

### 恢复注入格式

**Auto 恢复**（直接注入）：

```
[attention-workspace] 自动恢复工作上下文（高相关）：

<restored-principles>
Selection 与 Document 分离
使用 Observer
Plugin.destroy 作为 dispose 时机
使用 WeakMap 作为缓存
</restored-principles>

<pending-decision>
Observer 生命周期如何管理
</pending-decision>

<restored-state>
doing: 验证 Plugin.destroy 覆盖范围
until: 覆盖所有销毁路径
</restored-state>

请判断：pending-decision 是否仍需继续？Principles 条目是否仍 relevant？不相关的请忽略。
```

**Prompt 恢复**（提示确认）：

```
[attention-workspace] 检测到上次工作上下文（中相关）：
- 未解决问题: Observer 生命周期如何管理
- Principles: 4 条

是否恢复？
```

**Ignore**：不输出任何内容。

### 恢复后的 v19 行为

1. **Principles 恢复**：active 条目进入 v19 `<knowledge>` 区域，受 max=8 约束，统一受 relevance-first 规则管理
2. **pending-decision**：Agent 判断是否激活为当前 `<decision>`。如激活，State 随之恢复；如不激活，pending-decision 忽略
3. **Evidence 不恢复**：`<evidence>` 区域从空开始，按 v19 原有规则收集
4. **Knowledge 淘汰 = relevance-first**：与 v19 完全一致，不引入时间维度

## Principles 与 MEMORY.md 的关系：Promotion

Principles 条目可迁移到 MEMORY.md，但判定标准是**作用域**而非次数。

### 作用域判定

| 作用域 | 含义 | 归属 | 示例 |
|--------|------|------|------|
| **Project Scope** | 项目级架构决策 | 留在 principles.xml | Selection 与 Document 分离、使用 Observer |
| **Global Scope** | 跨项目、跨任务、长期稳定 | Promotion → MEMORY.md | 用户偏好中文交流、项目统一采用 WeakMap 缓存策略 |

**为什么不用次数判定**：
- "3 次对话仍 relevant" 太弱：`Selection 与 Document 分离` 可能 100 次对话都 relevant，但仍是项目级 ADR，不应进入 MEMORY.md
- MEMORY.md 应保存**跨项目通用**的知识，不是**项目内持久**的知识
- 项目级 ADR 永远留在 principles.xml，即使它非常稳定

### Promotion 规则

- 判定标准：**Global Scope**（跨项目通用）→ 迁移到 MEMORY.md
- 迁移 = **从 principles.xml 删除** + **写入 MEMORY.md**
- 已迁移到 MEMORY.md 的条目不再出现在 principles.xml 中（避免双写/重复恢复）

**对比**：

| 操作 | 行为 | 问题 |
|------|------|------|
| ~~次数判定~~（旧方案） | 跨 3+ 次对话 → 迁移 | 项目级 ADR 被误迁出 |
| **作用域判定**（当前方案） | Global Scope → 迁移 | 项目级 ADR 留在 principles.xml |

**数据流向**：
```
对话中产生 Knowledge
    ↓
写入 principles.xml（Project Scope）
    ↓
作用域 = Global Scope？
    ↓ 是
迁移到 MEMORY.md（Promotion）
    ↓
从 principles.xml 删除
```

**整体记忆体系**：

```
MEMORY.md           ← Global Scope 决策（跨项目通用）
    ↑ Promotion（Global Scope）
principles.xml      ← Project Scope 决策（项目级 ADR + replace/remove 失效）
    ↑ Restore
workspace.xml       ← 短期工作上下文（pending-decision 驱动）
    ↑ Activate
v19 Working Memory  ← 实时工作记忆（4 组件）
```

## 保存机制：Merge + 失效

save 不是全量覆盖，而是 **merge + 失效检查**。避免意外遗忘，也避免知识腐烂。

### workspace.xml 保存规则

workspace.xml 不需要 merge，因为它是强时效状态：
- Decision 未解决 → 写入 pending-decision + state
- Decision 已解决 → workspace 清空
- 无需合并，直接覆盖

### save 操作指令

1. 读取当前 v19 工作记忆状态（Decision/Knowledge/Evidence/State）
2. **workspace.xml**：直接覆盖写入
   - Decision 未解决 → 写入 `<pending-decision>` + `<state>`
   - Decision 已解决 → workspace 清空
3. **principles.xml**：merge + 失效检查
   - 读取旧 principles.xml
   - 与 v19 当前 Knowledge 合并（去重，新 reason 覆盖旧 reason）
   - 检查是否有矛盾：新 Knowledge 与旧 active 条目冲突 → 旧条目标记 replaced-by
   - 写入 principles.xml
4. 检查 Promotion 条件：Global Scope 条目迁移到 MEMORY.md，从 principles.xml 删除
5. 检查膨胀：超过 max=16 时，优先清理 removed 条目

## Skill 命令

通过 Skill tool 触发，args 传入命令名：

| 命令 | 行为 |
|------|------|
| `save` | 保存当前工作上下文（workspace 覆盖，principles merge + 失效检查） |
| `restore` | 从快照恢复工作上下文（含 LLM 相关性判断） |
| `status` | 查看快照状态（workspace + principles） |
| `clear` | 清除 workspace.xml |
| `promote` | 手动触发 Principles → MEMORY.md Promotion |
| `replace` | 手动标记条目为 replaced-by |
| `remove` | 手动标记条目为 removed |

### restore 操作指令

1. 读取 workspace.xml + principles.xml（如都不存在，提示"无快照"）
2. LLM 判断相关性（HIGH / MEDIUM / LOW）
3. 按三级策略处理（Auto / Prompt / Ignore）
4. pending-decision → Agent 判断是否激活为当前 Decision
5. Principles active 条目 → 进入 v19 `<knowledge>`，replaced-by/removed 条目不恢复

### status 操作指令

1. 读取 workspace.xml + principles.xml（如不存在，输出"无快照"）
2. 输出：
   - pending-decision 状态（有/无）
   - Principles 条目数（active / replaced-by / removed 分别统计）

### clear 操作指令

1. 清除 workspace.xml
2. principles.xml 保留（Principles 生命周期 ≠ Workspace 生命周期）
3. 如需同时清除 principles.xml，使用 `clear --all`

### promote 操作指令

1. 读取 principles.xml
2. 识别 Global Scope 条目（跨项目通用，非项目级 ADR）
3. 迁移到 MEMORY.md
4. 从 principles.xml 删除已迁移条目
5. Project Scope 条目（如 `Selection 与 Document 分离`）永远留在 principles.xml

### replace 操作指令

1. 指定旧条目关键词
2. 标记 `status="replaced-by" ref="{新决策关键词}"`
3. 保留 reason（防止重新做出已废弃的决策）

### remove 操作指令

1. 指定条目关键词
2. 标记 `status="removed"`
3. 更新 reason 为废弃原因

## 保存/恢复时机

| 时机 | 操作 | 触发方式 |
|------|------|---------|
| 对话结束（Stop） | save | Hook 自动 / 手动 `/attention save` |
| 上下文压缩前（PreCompact） | save | Hook 自动 |
| 新对话开始（SessionStart） | LLM 判断 + 三级恢复 | Hook 自动 / 手动 `/attention restore` |
| 用户主动 | save/restore/status/clear/promote/replace/remove | Skill 命令 |

## 设计哲学总结

**v19 是基于 relevance-first 遗忘的工作记忆模型，workspace 层遵循同一原则：**

| 维度 | v19 | workspace |
|------|-----|-----------|
| Knowledge/Principles 遗忘 | relevance-first | relevance-first（一致） |
| 失效机制 | 无（对话内不需要） | promote / replace / remove |
| 知识来源 | 对话中产生 | principles.xml 恢复 + 对话中产生 |
| 可解释性 | 对话上下文即时可追溯 | `<reason>` + `<avoid>` 跨对话可追溯 |
| Decision 生命周期 | 存在即活跃 | 恢复为 pending-decision，Agent 决定是否激活 |
| Decision ⇔ State | 绑定 | 绑定（workspace.xml 中一致） |
| Evidence | 生命周期=Decision | 不持久化 |
| 相关性判断 | 对话内自然判断 | LLM Judgement（HIGH/MEDIUM/LOW） |
| Promotion 判定 | N/A | 作用域（Global Scope → MEMORY.md，Project Scope → 留在 principles.xml） |
| 保存方式 | N/A | workspace 覆盖，principles merge + 失效检查 |

**不引入第二套遗忘机制。**

**两个运行时问题已解决**：
1. **Principles 失效机制**：promote（迁移） / replace（替代） / remove（废弃），防止知识腐烂
2. **relevance-first 执行机制**：LLM Judgement 替代伪数值评分，语义相关性让语义模型判断

**记忆体系完整链路**：
```
MEMORY.md       ← Global Scope（跨项目通用，作用域判定 Promotion）
    ↑ Promotion
principles.xml  ← Project Scope（项目级 ADR + reason/avoid + replace/remove 失效）
    ↑ Restore
workspace.xml   ← 短期（pending-decision 驱动，覆盖保存）
    ↑ Activate
v19 Working Memory ← 实时（4 组件，relevance-first 遗忘）
```