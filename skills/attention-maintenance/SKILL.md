---
name: attention-maintenance
description: "短期上下文维护系统 v15：工作记忆模型。Decision（active/resolved + stage）+ADR（active）+Evidence（生命周期绑定Decision）+State（result+confidence）+Pending（!/?)。"
---

# 短期上下文维护系统 v15

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：真正的"工作记忆（Working Memory）"模型，而非压缩过的项目档案系统。

## 最终结构

```xml
<decision active stage="deciding">
Observer 生命周期如何管理
</decision>

<adr>
[A] 使用 Observer
[B] Selection 与 Document 分离
</adr>

<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>

<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
confidence: medium
done-when: 验证所有销毁路径
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

---

## 组件说明

### Decision（当前问题 + 阶段）

```xml
<decision active stage="deciding">
Observer 生命周期如何管理
</decision>
```

**只回答**：当前正在决定什么？处于什么阶段？

**属性**：
- `active`：当前活跃
- `resolved`：已解决
- `stage`：deciding / implementing / validating

**stage 含义**：
| stage | 含义 | 行为模式 |
| --- | --- | --- |
| deciding | 正在分析、设计方案 | 探索式，允许多次迭代 |
| implementing | 正在实现 | 执行式，按方案推进 |
| validating | 正在验证 | 验证式,检查实现结果 |

**恢复时优先读取 active**。

---

### ADR（最终决策）

```xml
<adr>
[A] 使用 Observer
[B] Selection 与 Document 分离
</adr>
```

**只回答**：已决定什么？

**关键改变**：
- 只记录最终决策
- 不记录 superseded（候选方案）
- 不记录 rejected（被拒绝方案）

**原因**：
- ADR = Accepted Decision，不是 Decision History
- 短期上下文最怕膨胀
- 恢复时先看最终决定，而非历史竞争者

---

### Evidence（当前证据）

```xml
<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>
```

**只回答**：支撑当前 Active Decision 的事实是什么？

**生命周期规则**：
```
Evidence 生命周期 = Active Decision 生命周期

Decision resolved → Evidence = ∅
```

**隐式规则**（不显式存储 TTL）：
- Agent 知道：决策结束后，Evidence 自动清空
- 不需要人工维护滑动窗口
- 真正的"自动遗忘"

**约束**：max=5

---

### State（当前进展 + 结果 + 置信度）

```xml
<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
confidence: medium
done-when: 验证所有销毁路径
</state>
```

**只回答**：正在做什么？得到什么结果？有多大把握？何时完成？

**confidence 含义**：
| 值 | 定义 | 示例 |
| --- | --- | --- |
| low | 推测，缺乏证据，尚未验证 | "可能是内存泄漏" |
| medium | 有证据支撑，但尚未完成验证 | "Plugin.destroy 可能是时机，需验证覆盖路径" |
| high | 已验证，可作为后续工作前提 | "已验证 Plugin.destroy 覆盖所有销毁路径" |

**confidence 的价值**：
- 恢复时立刻知道：这是已验证结论，还是暂时推断
- 防止"把猜测当结论"
- low/medium 的 result 需要进一步验证

---

### Pending（待决问题）

```xml
<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

**只回答**：下一步做什么？还有什么候选？

**严格限制**：
| 标记 | max | 说明 |
| --- | --- | --- |
| ! | 1 | 下一步唯一 |
| ? | 5 | 候选列表 |

**防止退化成任务列表**。

---

## 被删除的组件

### Focus（讨论对象）

**删除原因**：
- Decision 已隐含 Focus
- 单主题时，Focus 完全冗余
- 多主题并行时，可通过 Decision 内容区分

**恢复策略**：
- 从 Decision 内容推导 Focus
- 例如："Observer 生命周期如何管理" → Focus = Selection Context

---

### Stage（独立组件）

**删除原因**：
- 合并到 Decision 的 stage 属性
- 减少一个顶层组件
- State 与 Decision 绑定更紧密

---

### State.next

**删除原因**：
- 与 Pending.! 重复
- 由 Pending.! 统一表达"下一步"

---

### ADR.superseded

**删除原因**：
- ADR 只记录最终决策
- superseded 是候选方案历史，不是架构决策
- 短期上下文不应承载历史

---

## 条目限制

```xml
<limits>
  <!-- 单例 -->
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
Decision (active, stage=deciding)
    ↓
State.confidence = low/medium
    ↓
收集 Evidence
    ↓
State.confidence → high
    ↓
State.done-when 满足
    ↓
Decision (resolved)
    ↓
Evidence = ∅（自动清空）
    ↓
Pending[!]
    ↓
新 Decision (active)
```

---

## 对比：v14 vs v15

| 项目 | v14 | v15 |
| --- | --- | --- |
| Focus | 必须 | **删除，由 Decision 推导** |
| Stage | 独立组件 | **合并到 Decision.stage** |
| Decision | active/resolved | **active/resolved + stage** |
| ADR | active/superseded | **只保留 active** |
| Evidence | 滑动窗口 | **生命周期绑定 Decision** |
| State.next | 存在 | **删除，由 Pending.! 统一** |
| State.confidence | 无 | **新增：low/medium/high** |
| Rejected | 合并到 ADR | **不存储，生命周期=Decision** |

---

## 使用示例

### 完整示例（决策中）

```xml
<decision active stage="deciding">
Observer 生命周期如何管理
</decision>

<adr>
[A] 使用 Observer
[B] Selection 与 Document 分离
</adr>

<evidence>
- Observer 导致泄漏
- Plugin 有 destroy 生命周期
</evidence>

<state>
doing: 分析 Observer 生命周期
result: Plugin.destroy 可作为 dispose 时机
confidence: medium
done-when: 验证所有销毁路径
</state>

<pending>
! Selection 缓存策略
? 多 Selection 支持
</pending>
```

---

### 决策完成后

```xml
<decision resolved stage="deciding">
Observer 生命周期如何管理
</decision>

<adr>
[A] 使用 Observer
[B] Selection 与 Document 分离
[C] Plugin.destroy 作为 dispose 时机
</adr>

<!-- Evidence 自动清空 -->
<evidence>
</evidence>

<state>
doing: Selection 缓存策略设计
result:
confidence: low
done-when: 确定缓存策略
</state>

<pending>
! 实现缓存逻辑
? 多 Selection 支持
</pending>
```

---

### 实现阶段

```xml
<decision active stage="implementing">
实现 Selection 缓存逻辑
</decision>

<adr>
[A] 使用 Observer
[B] Selection 与 Document 分离
[C] Plugin.destroy 作为 dispose 时机
[D] 使用 WeakMap 作为缓存
</adr>

<evidence>
- WeakMap 自动清理引用
- Selection 对象生命周期可控
</evidence>

<state>
doing: 实现 WeakMap 缓存
result: 基础结构已搭建
confidence: medium
done-when: 缓存命中率测试通过
</state>

<pending>
! 编写单元测试
? 缓存淘汰策略
</pending>
```

---

## 执行原则

1. **Decision 状态**：active → resolved
2. **Decision stage**：deciding → implementing → validating
3. **ADR 只存最终决策**：不记录 superseded/rejected
4. **Evidence 自动清空**：Decision resolved → Evidence = ∅
5. **State.confidence**：low → medium → high
6. **Pending 严格限制**：! max=1
7. **恢复优先级**：active > resolved

---

## 注意事项

1. **Focus 不存储**：从 Decision 内容推导
2. **Evidence 自动遗忘**：决策结束自动清空，无需人工维护
3. **ADR 不膨胀**：只记录最终决策，不记录候选方案
4. **confidence 是关键**：防止"把猜测当结论"
5. **Pending 严格限制**：! max=1，防止任务列表化

---

## 总结

v15 是工作记忆模型的收敛形态：

| 组件 | 只回答 | 关键改进 |
| --- | --- | --- |
| Decision | 当前问题 + 阶段 | **合并 Stage** |
| ADR | 最终决策 | **删除 superseded** |
| Evidence | 当前证据 | **生命周期绑定 Decision** |
| State | 进展 + 结果 + 置信度 | **新增 confidence** |
| Pending | 待决问题 | **! max=1, ? max=5** |

**特点**：
- Focus 被推导，不存储
- Stage 合并到 Decision
- ADR 只存最终决定
- Evidence 随 Decision 自动过期
- 删除 superseded
- 删除 next（由 Pending.! 表示）
- 增加 confidence

**更接近认知科学中的 Working Memory**：

```
当前问题
    ↓
当前证据
    ↓
当前结论
    ↓
下一问题
```

而非项目历史。
