---
name: attention-maintenance
description: "短期上下文维护系统 v13：最终收敛。Focus+Stage+Decision+ADR（Level）+Evidence+State（done-when）+Pending（!/?)。信息密度最优，维护成本最低。"
---

# 短期上下文维护系统 v13

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：每个条目都直接参与当前推理，不会逐渐演化成小型知识库。

## 最终结构

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<decision>
Observer 生命周期如何管理
</decision>

<adr>
[A] Selection 与 Document 分离
[B] 使用 Observer
</adr>

<evidence>
- Selection 更新不会触发 Document 更新
- NodeView 生命周期由 PM 管理
</evidence>

<state>
doing: 分析 Observer 生命周期
done-when: 明确 dispose 时机
next: 查看 Plugin 生命周期
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>

<rejected>
Selection 作为 Document 子状态
EventEmitter
</rejected>
```

---

## 组件说明

### Focus（讨论对象）

```xml
<focus>Selection Context</focus>
```

**只回答**：当前讨论什么对象？

**约束**：Decision 必须属于 Focus，否则自动切换 Focus。

---

### Stage（讨论阶段）

```xml
<stage>[exploring|deciding|implementing|validating]</stage>
```

**只回答**：当前处于什么阶段？

| 阶段 | AI 行为 |
| --- | --- |
| exploring | 分析、调研 |
| deciding | 权衡方案 |
| implementing | 写代码 |
| validating | 测试、调优 |

**价值**：Focus + Stage 是最有价值的组合之一。Stage 决定行为模式。

---

### Decision（当前选择）

```xml
<decision>
Observer 生命周期如何管理
</decision>
```

**只回答**：当前正在决定什么？

**约束**：Decision ⊂ Focus，否则自动切换 Focus。

---

### ADR（决策 + Level）

```xml
<adr>
[A] Selection 与 Document 分离
[B] 使用 Observer
</adr>
```

**只回答**：已决定什么？

**关键改进**：
- 不存储 rejected，避免膨胀
- 只保留决策结果
- Level 决定恢复优先级

### Level 分级

| Level | 说明 | 恢复优先级 |
| --- | --- | --- |
| [A] | 架构级 | 最高 |
| [B] | 模块级 | 高 |
| [C] | 实现级 | 中 |

---

### Evidence（导致 ADR 的证据）

```xml
<evidence>
- Selection 更新不会触发 Document 更新
- NodeView 生命周期由 PM 管理
</evidence>
```

**只回答**：哪些事实导致了 ADR？

### 与 Landmark 的区别

| Landmark | Evidence |
| --- | --- |
| 认知转折 | 导致 ADR 的证据 |
| 可能与 ADR 重复 | 必须是 ADR 的支撑 |

### 收敛规则

**如果删除这个事实，ADR 会变得难以解释，否则不要进入 Evidence。**

**约束**：max=5。

---

### State（当前进展 + 退出条件）

```xml
<state>
doing: 分析 Observer 生命周期
done-when: 明确 dispose 时机
next: 查看 Plugin 生命周期
</state>
```

**只回答**：正在做什么？什么时候完成？下一步？

### done-when 价值

- 形成闭环：doing → done-when → next
- 防止 AI 一直分析不知道何时结束

---

### Pending（待决 + 简化优先级）

```xml
<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

**只回答**：还有什么要处理？

### 优先级简化

| 标记 | 说明 |
| --- | --- |
| ! | 下一步必须处理 |
| ? | 后续候选 |

**改进**：不使用 P1/P2/P3 相对排序，避免频繁重排。

---

### Rejected（被否决的方案）

```xml
<rejected>
Selection 作为 Document 子状态
EventEmitter
</rejected>
```

**只回答**：哪些方案被否决了？

### 与 ADR 分离的原因

| ADR 内嵌 rejected | Rejected 独立 |
| --- | --- |
| ADR 会越来越长 | ADR 保持简洁 |
| 访问频率混在一起 | 按需读取 rejected |

**约束**：max=10，只保留关键否决。

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
  <Pending max="10"/>
  <Rejected max="10"/>
</limits>
```

---

## 状态流转

```
Stage（大阶段）
    ↓
Decision（当前决策）
    ↓
State（当前步骤）
    ├─ doing
    ├─ done-when
    └─ next
    ↓
done-when 满足 → next
    ↓
next 完成 → Pending[!]
    ↓
Pending[!] → 新 Decision
```

---

## 约束规则

### 1. Decision ⊂ Focus

Decision 必须属于当前 Focus，否则自动切换 Focus。

### 2. Evidence 必须支撑 ADR

如果删除 Evidence，ADR 应该变得难以解释。

### 3. Rejected 独立读取

先读 ADR，如果讨论重开，再读 Rejected。

### 4. State 形成闭环

doing → done-when → next。

---

## 对比：v12.5 vs v13

| 项目 | v12.5 | v13 |
| --- | --- | --- |
| Landmark | 认知转折，可能与 ADR 重复 | **改为 Evidence，必须支撑 ADR** |
| ADR rejected | 内嵌，ADR 会膨胀 | **独立为 Rejected** |
| Pending 优先级 | P1/P2/P3 相对排序 | **!/ ? 简化** |
| ADR max | 15 | **15** |
| Evidence max | 5（原 Landmark） | **5** |
| Rejected max | 无 | **10** |

---

## 信息密度对比

### v12.5

```xml
<adr>
[A] Selection 与 Document 分离
    rejected: Selection 作为 Document 子状态

[B] 使用 Observer
    rejected: EventEmitter
</adr>

<landmarks>
- Selection 更新不会触发 Document 更新
</landmarks>
```

### v13

```xml
<adr>
[A] Selection 与 Document 分离
[B] 使用 Observer
</adr>

<evidence>
- Selection 更新不会触发 Document 更新
</evidence>

<rejected>
Selection 作为 Document 子状态
EventEmitter
</rejected>
```

**改进**：
- ADR 保持简洁
- Evidence 必须支撑 ADR
- Rejected 按需读取

---

## 使用示例

### 完整示例

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<decision>
Observer 生命周期如何管理
</decision>

<adr>
[A] Selection 与 Document 分离
[B] 使用 Observer
[C] SelectionContext 命名
</adr>

<evidence>
- Selection 更新不会触发 Document 更新
- NodeView 生命周期由 PM 管理
</evidence>

<state>
doing: 分析 Observer 生命周期
done-when: 明确 dispose 时机
next: 查看 Plugin 生命周期
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>

<rejected>
Selection 作为 Document 子状态
EventEmitter
</rejected>
```

### 流转示例

```
Stage: deciding
Decision: Observer 生命周期如何管理
State:
  doing: 分析 Observer 生命周期
  done-when: 明确 dispose 时机
  next: 查看 Plugin 生命周期

→ done-when 满足
State.next: 查看 Plugin 生命周期

→ next 完成
Pending[!]: Selection 缓存策略
→ 新 Decision
```

---

## 执行原则

1. **Decision ⊂ Focus**：否则自动切换 Focus
2. **Evidence 必须支撑 ADR**：否则不进入
3. **ADR 保持简洁**：不存储 rejected
4. **Rejected 按需读取**：讨论重开时才看
5. **Pending 简化**：!/ ? 而非 P1/P2/P3
6. **State 形成闭环**：done-when 明确退出

---

## 注意事项

1. **Evidence ≠ Landmark**：Evidence 必须支撑 ADR
2. **Rejected 独立**：避免 ADR 膨胀
3. **Pending 用 !/?**：不使用相对排序
4. **Stage 决定行为模式**：Focus + Stage 最有价值
5. **done-when 形成闭环**：防止无限分析

---

## 总结

v13 是最终收敛形态：

| 组件 | 只回答 | 关键改进 |
| --- | --- | --- |
| Focus | 讨论对象 | Decision ⊂ Focus |
| Stage | 大阶段 | 决定行为模式 |
| Decision | 当前选择 | 必须属于 Focus |
| ADR | 已决定 | **不存 rejected，保持简洁** |
| Evidence | ADR 证据 | **必须支撑 ADR** |
| State | 当前进展 | done-when 闭环 |
| Pending | 待决问题 | **!/ ? 简化** |
| Rejected | 被否决方案 | **独立，按需读取** |

**每个条目都直接参与当前推理，不会逐渐演化成小型知识库。**