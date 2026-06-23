---
name: attention-maintenance
description: "短期上下文维护系统 v14：工作记忆模型。Focus+Stage+Decision（active）+ADR（active/superseded）+Evidence（滑动窗口）+State（result）+Pending（!/?)。"
---

# 短期上下文维护系统 v14

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：真正的"工作记忆（Working Memory）"模型，而非压缩过的项目档案系统。

## 最终结构

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<decision active>
Observer 生命周期如何管理
</decision>

<adr>
[A active] 使用 Observer
[A superseded] EventEmitter
[B active] Selection 与 Document 分离
</adr>

<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>

<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
done-when: 明确 dispose 时机
next: Selection 缓存策略
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

---

## 组件说明

### Focus（讨论对象）

```xml
<focus>Selection Context</focus>
```

**只回答**：当前讨论什么对象？

**自动推导**：当 Decision 能唯一确定 Focus 时，Focus 可省略。只有多主题并行时才保留。

---

### Stage（讨论阶段）

```xml
<stage>[exploring|deciding|implementing|validating]</stage>
```

**只回答**：当前处于什么阶段？

---

### Decision（当前选择 + 状态）

```xml
<decision active>
Observer 生命周期如何管理
</decision>
```

**只回答**：当前正在决定什么？

### 状态标记

| 标记 | 说明 |
| --- | --- |
| active | 当前活跃 |
| resolved | 已解决 |

**恢复时优先读取 active**。

---

### ADR（决策 + 状态 + 关联）

```xml
<adr>
[A active] 使用 Observer
[A superseded] EventEmitter
[B active] Selection 与 Document 分离
</adr>
```

**只回答**：已决定什么？什么被替代了？

### 状态标记

| 标记 | 说明 | 恢复时行为 |
| --- | --- | --- |
| active | 当前有效 | 优先读取 |
| superseded | 已被替代 | 仅作历史参考 |

### 与 Rejected 的合并

| v13 Rejected 独立 | v14 合并回 ADR |
| --- | --- |
| 关联断裂 | **关联清晰** |
| 无法知道对应哪个 ADR | **与决策放在一起** |

**关键改进**：EventEmitter 写在 ADR 下，关联不断裂。

---

### Evidence（滑动窗口）

```xml
<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>
```

**只回答**：支撑当前 Active Decision 的事实是什么？

### 滑动窗口规则

**Evidence 只支撑当前 Active Decision，不累计历史。**

| v13 | v14 |
| --- | --- |
| 支撑所有 ADR | **只支撑 Active Decision** |
| 会逐渐膨胀 | **滑动窗口，自动清理** |

**约束**：max=5。

---

### State（当前进展 + 结果）

```xml
<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
done-when: 明确 dispose 时机
next: Selection 缓存策略
</state>
```

**只回答**：正在做什么？得到什么结果？何时完成？下一步？

### result 价值

- doing → result → done-when 形成完整闭环
- 记录"做了什么得到什么"，不会断开

---

### Pending（待决 + 严格限制）

```xml
<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

**只回答**：下一步做什么？还有什么候选？

### 严格限制

| 标记 | max | 说明 |
| --- | --- | --- |
| ! | 1 | 下一步唯一 |
| ? | 5 | 候选列表 |

**防止退化成任务列表**。

---

## Freshness（新鲜度）

### 核心问题

短期上下文最大问题：旧状态仍然存在，但忘记清理。

### 解决方案

所有组件增加状态标记：

| 组件 | 状态标记 |
| --- | --- |
| Decision | active / resolved |
| ADR | active / superseded |
| Evidence | 滑动窗口（只支撑 Active Decision） |

**恢复时优先读取 active，忽略 resolved/superseded。**

---

## 条目限制

```xml
<limits>
  <!-- 单例 -->
  <Focus max="1"/>
  <Stage max="1"/>
  <Decision max="1"/>
  <State max="1"/>

  <!-- 队列 -->
  <ADR max="15"/>
  <Evidence max="5"/>
  <Pending !="1" ?="5"/>
</limits>
```

---

## 状态流转

```
Stage（大阶段）
    ↓
Decision (active)
    ↓
State
    ├─ doing
    ├─ result
    ├─ done-when
    └─ next
    ↓
done-when 满足
    ↓
Decision (resolved)
    ↓
Pending[!]
    ↓
新 Decision (active)
    ↓
Evidence 滑动窗口更新
```

---

## 对比：v13 vs v14

| 项目 | v13 | v14 |
| --- | --- | --- |
| Decision 状态 | 无 | **active / resolved** |
| ADR 状态 | 无 | **active / superseded** |
| Rejected | 独立，关联断裂 | **合并回 ADR** |
| Evidence | 支撑所有 ADR | **滑动窗口，只支撑 Active Decision** |
| State result | 无 | **新增，记录结果** |
| Pending 限制 | 无 | **! max=1, ? max=5** |
| Focus | 必须 | **可省略，自动推导** |

---

## 使用示例

### 完整示例

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<decision active>
Observer 生命周期如何管理
</decision>

<adr>
[A active] 使用 Observer
[A superseded] EventEmitter
[B active] Selection 与 Document 分离
[B superseded] Selection 作为 Document 子状态
</adr>

<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>

<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
done-when: 明确 dispose 时机
next: Selection 缓存策略
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

### 决策完成后

```xml
<decision resolved>
Observer 生命周期如何管理
</decision>

<adr>
[A active] 使用 Observer
</adr>

<state>
doing: Selection 缓存策略设计
done-when: 确定缓存策略
next: 实现缓存逻辑
</state>

<pending>
! 实现缓存逻辑
? 多 Selection 支持
</pending>

<!-- Evidence 滑动更新 -->
<evidence>
- Selection 访问频率高
- 缓存命中率高
</evidence>
```

---

## 执行原则

1. **Decision 状态**：active → resolved
2. **ADR 状态**：active → superseded
3. **Evidence 滑动窗口**：只支撑 Active Decision
4. **State 记录结果**：doing → result → done-when
5. **Pending 严格限制**：! max=1
6. **恢复优先级**：active > resolved/superseded

---

## 注意事项

1. **Freshness 是关键**：优先读取 active，忽略旧状态
2. **Evidence 滑动窗口**：不累计历史，只支撑当前
3. **result 闭环**：记录结果，防止断开
4. **ADR 关联清晰**：superseded 写在 ADR 下
5. **Pending 严格限制**：! max=1，防止任务列表化

---

## 总结

v14 是工作记忆模型的最终形态：

| 组件 | 只回答 | 关键改进 |
| --- | --- | --- |
| Focus | 讨论对象 | 可省略，自动推导 |
| Stage | 大阶段 | 决定行为模式 |
| Decision | 当前选择 | **active / resolved** |
| ADR | 决策 + 否决 | **active / superseded，关联清晰** |
| Evidence | 当前证据 | **滑动窗口，不累计** |
| State | 进展 + 结果 | **result 闭环** |
| Pending | 待决问题 | **! max=1, ? max=5** |

**真正的"工作记忆（Working Memory）"模型，而非压缩过的项目档案系统。**