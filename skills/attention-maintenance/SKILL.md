---
name: attention-maintenance
description: "短期上下文维护系统 v12：极简形态。Focus+Stage+Decision+ADR（内嵌 rejected）+Landmark（纯事实）+State。信息密度最优。"
---

# 短期上下文维护系统 v12

## 设计目标

**适用于**：单项目 + 几十轮对话 + 复杂软件设计（持续数周）

**核心理念**：信息密度最优，恢复成本最低。

## 最终结构

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<active-decision>
  Observer 生命周期如何管理
</active-decision>

<adr>
  - Selection 与 Document 分离
    rejected: Selection 作为 Document 子状态

  - 使用 Observer
    rejected: EventEmitter
</adr>

<landmarks>
  - Selection 更新不会触发 Document 更新
  - NodeView 生命周期由 PM 管理
</landmarks>

<current-state>
  doing: 分析 Observer 生命周期
  next: 查看 Plugin 生命周期
</current-state>

<pending>
  - Selection 缓存策略
  - 多 Selection 支持
</pending>
```

---

## 组件说明

### Focus（讨论对象）

```xml
<focus>Selection Context</focus>
```

**只回答**：当前讨论什么对象？

---

### Stage（讨论阶段）

```xml
<stage>[exploring|deciding|implementing|validating]</stage>
```

**只回答**：当前处于什么阶段？

| 阶段 | 说明 | AI 行为 |
| --- | --- | --- |
| exploring | 探索问题 | 分析、调研、收集信息 |
| deciding | 讨论决策 | 权衡方案、对比优劣 |
| implementing | 实现方案 | 写代码、构建功能 |
| validating | 验证效果 | 测试、调优、修复 |

**价值**：防止 AI 漂移。用户说"给出代码"时，若 Stage=exploring，AI 应继续分析而非写代码。

---

### Active Decision（当前选择）

```xml
<active-decision>
  Observer 生命周期如何管理
</active-decision>
```

**只回答**：当前正在决定什么？

**简化**：只记录问题本身，选项在对话中讨论。

---

### ADR（决策 + 关键否决）

```xml
<adr>
  <record id="001">
    <decision>Selection 与 Document 分离</decision>
    <rejected>
      - Selection 作为 Document 子状态
    </rejected>
  </record>

  <record id="002">
    <decision>使用 Observer</decision>
    <rejected>
      - EventEmitter
    </rejected>
  </record>
</adr>
```

**只回答**：已决定什么？否决了什么？

**关键改进**：
- ADR 与 Trace 合并，避免人工关联
- 只保留关键否决，不保留完整推理过程
- 恢复成本最低

---

### Landmarks（事实发现）

```xml
<landmarks>
  - Selection 更新不会触发 Document 更新
  - NodeView 生命周期由 PM 管理
  - Observer 导致内存泄漏
</landmarks>
```

**只回答**：发现了什么事实？

**关键改进**：
- 只记录 observation，不记录 impact
- impact 是推理，不是事实
- 推理过程最容易膨胀

---

### Current State（当前进展）

```xml
<current-state>
  doing: 分析 Observer 生命周期
  next: 查看 Plugin 生命周期
  blocked: 不确定 GC 时机
</current-state>
```

**只回答**：正在做什么？下一步？

**简化**：
- doing + next 覆盖 80% 场景
- blocked 可选，无阻塞时为空

---

### Pending（待决问题）

```xml
<pending>
  - Selection 缓存策略
  - 多 Selection 支持
</pending>
```

**只回答**：还有哪些问题待解决？

---

## 删除的内容

| 删除 | 原因 |
| --- | --- |
| Trace 独立层 | 合并到 ADR，避免关联丢失 |
| Landmark impact | 推理过程会膨胀 |
| Context Checkpoint 存储 | 改为按需生成，不维护 |
| State evidence | blocked 已说明阻碍 |
| ADR scope | 信息密度优先，scope 按需添加 |
| Decision authority | 单人项目不需要 |
| Goal / Identity | Focus 已覆盖方向 |

---

## Context Checkpoint（按需生成）

**不存储**，需要恢复时生成：

```
checkpoint = summarize(focus, stage, decision, adr, landmark)
```

生成示例：

```xml
<!-- 按需生成，不存储 -->
<context-checkpoint>
  <focus>Selection Context</focus>
  <stage>deciding</stage>
  <decision>Observer 生命周期如何管理</decision>
  <adr>
    - Selection 与 Document 分离
    - 使用 Observer
  </adr>
  <landmarks>
    - Selection 更新不触发 Document 更新
  </landmarks>
</context-checkpoint>
```

---

## 条目限制

```xml
<limits>
  <!-- 单例 -->
  <Focus max="1"/>
  <Stage max="1"/>
  <Active-Decision max="1"/>
  <Current-State max="1"/>

  <!-- 队列 -->
  <ADR max="30"/>
  <Landmarks max="10"/>
  <Pending max="10"/>
</limits>
```

---

## 对比：v11.5 vs v12

| 项目 | v11.5 | v12 |
| --- | --- |
| ADR + Trace | 分离，需人工关联 | **合并，内嵌 rejected** |
| Landmark | observation + impact | **只保留 observation** |
| Current State | doing/blocked/evidence/next | **doing/next/blocked(可选)** |
| Stage | 删除 | **恢复，单字段** |
| Context Checkpoint | 存储 | **按需生成，不存储** |
| Decision authority | ai/user | **删除** |
| ADR scope | architecture/module | **删除，按需添加** |
| Goal / Identity | 保留 | **删除** |

---

## 信息密度对比

### v11.5

```xml
<focus><subject>Selection Context</subject></focus>

<active-decision>
  <question>Observer 生命周期</question>
  <authority>ai</authority>
  <options>...</options>
</active-decision>

<adr>
  <record><scope>architecture</scope><decision>...</decision></record>
</adr>

<trace>
  <item><rejected-option>...</rejected-option><reason>...</reason></item>
</trace>

<landmarks>
  <landmark><observation>...</observation><impact>...</impact></landmark>
</landmarks>

<current-state>
  <doing>...</doing><blocked>...</blocked><evidence>...</evidence><next>...</next>
</current-state>

<context-checkpoint>...</context-checkpoint>
```

### v12

```xml
<focus>Selection Context</focus>
<stage>deciding</stage>
<active-decision>Observer 生命周期如何管理</active-decision>

<adr>
  - Selection 与 Document 分离
    rejected: Selection 作为 Document 子状态
</adr>

<landmarks>
  - Selection 更新不触发 Document 更新
</landmarks>

<current-state>
  doing: 分析 Observer 生命周期
  next: 查看 Plugin 生命周期
</current-state>
```

**信息密度提升约 50%**。

---

## 使用示例

### 完整示例

```xml
<focus>Selection Context</focus>

<stage>deciding</stage>

<active-decision>
  Observer 生命周期如何管理
</active-decision>

<adr>
  - Selection 与 Document 分离
    rejected: Selection 作为 Document 子状态

  - 使用 Observer
    rejected: EventEmitter
</adr>

<landmarks>
  - Selection 更新不会触发 Document 更新
  - NodeView 生命周期由 PM 管理
  - Observer 导致内存泄漏
</landmarks>

<current-state>
  doing: 分析 Observer 生命周期
  next: 查看 Plugin 生命周期
</current-state>

<pending>
  - Selection 缓存策略
  - 多 Selection 支持
</pending>
```

### 上下文恢复流程

```
1. 读取 Focus: 当前讨论 Selection Context
2. 读取 Stage: 当前在 deciding 阶段
3. 读取 Active Decision: 当前决定 Observer 生命周期
4. 读取 ADR: 已决定 Selection 分离、使用 Observer
5. 读取 Landmarks: 发现 Selection 不触发 Document 更新
6. 恢复完成
```

---

## 执行原则

1. **Focus 单例**：永远只有一个讨论对象
2. **Stage 防漂移**：exploring/deciding/validating 时行为不同
3. **ADR 内嵌 rejected**：避免关联丢失
4. **Landmark 纯事实**：不记录推理过程
5. **State 极简**：doing + next + blocked(可选)
6. **Checkpoint 按需生成**：不存储，不维护

---

## 注意事项

1. **Stage 比 State 重要**：Stage 决定行为模式
2. **ADR 内嵌 rejected**：否决和决策放一起，避免关联丢失
3. **Landmark 不含推理**：只记录事实发现
4. **信息密度优先**：删除 XML 噪音（如 `<subject>`）
5. **Checkpoint 不存储**：需要时生成

---

## 总结

v12 是信息密度最优的极简形态：

| 组件 | 只回答 |
| --- | --- |
| Focus | 讨论对象 |
| Stage | 讨论阶段 |
| Active Decision | 当前选择 |
| ADR | 决策 + 否决 |
| Landmarks | 事实发现 |
| State | 当前进展 |

**符合大模型有限上下文窗口下的信息密度优化原则。**
