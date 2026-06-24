---
name: attention-maintenance
description: "短期上下文维护系统 v19：工作记忆模型。Decision（问题）+Knowledge（结论）+Evidence（来源标记：constraint/fact/test/hypothesis）+State（doing/until）。4 组件最小充分集。"
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
```

**注意**：没有"Next"环节。Decision 消失后，新 Decision 由对话上下文自然产生。

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

<!-- Decision 消失，Evidence 自动清空 -->
<evidence>
</evidence>

<state>
doing: 分析缓存需求
until: 明确缓存策略
</state>
```

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
3. **Knowledge 只存最终结论**：不记录 Level/superseded/rejected
4. **Knowledge Freshness**：relevance-first，删除与当前 Decision 最不相关的条目
5. **Evidence 来源标记**：constraint/fact/test/hypothesis，区分推理权重
6. **Evidence 自动清空**：Decision 消失 → Evidence = ∅
7. **confidence 不存储**：从 Evidence 类型组合推导
8. **结论进入 Knowledge**：不留在 State.result
9. **不存 Next**：未来目标由对话上下文自然产生

---

## 注意事项

1. **只保留核心记忆**：删除所有推导信息
2. **Decision 无状态属性**：存在即活跃，消失即结束
3. **Decision/State 职责分离**：Decision 是问题，State.doing 是动作
4. **Evidence 自动遗忘**：决策结束自动清空
5. **Evidence 来源标记**：constraint > fact > test > hypothesis
6. **Knowledge 不膨胀**：max=8，relevance-first 遗忘
7. **confidence 不存储**：从 Evidence 推导，避免派生信息失真
8. **不存 Next**：未来目标属于计划，不是工作记忆

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