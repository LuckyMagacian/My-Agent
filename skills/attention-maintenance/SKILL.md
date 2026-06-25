---
name: attention-maintenance
description: "短期上下文维护系统 v19 + persistence：工作记忆模型。Decision（问题）+Knowledge（结论）+Evidence（来源标记：constraint/fact/test/hypothesis）+State（doing/until）。4 组件最小充分集 + 跨对话持久化快照。"
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

---

# attention-persistence：脱离内存的短期记忆模块

## 设计目标

**解决**：v19 工作记忆纯对话内维护，对话结束即消失，下次对话需重新建立上下文。

**定位**：v19 的独立外挂层，不修改 v19 的 4 组件结构。类比 CPU L1 cache（v19）与磁盘 swap（persistence）。

**原则**：
- 持久化的是"工作记忆快照"，不是项目档案
- 恢复的记忆是"建议"，Claude 有权拒绝不相关的恢复
- 不改变 v19 的任何规则（max 限制、生命周期、relevance-first）

## 持久化范围

| 组件 | 持久化策略 | 理由 |
|------|-----------|------|
| Knowledge | 全量持久化 | 跨对话最有价值，是推理前提 |
| Decision | 条件持久化（未解决时） | Decision 已消失 = 问题已解决，无需持久化 |
| State | 条件持久化（与 Decision 绑定） | Decision 不存在时 State 无持久化价值 |
| Evidence | 不持久化，保留摘要 | Evidence 生命周期=Decision 生命周期，跨对话后来源标记可能失效 |

## 存储位置

```
skills/attention-maintenance/persistence/
  snapshot.xml                    # 当前工作记忆快照
  archive/                        # 历史快照归档（保留最近 5 个）
    2026-06-25T19-30-00.xml
```

## snapshot.xml 格式

```xml
<?xml version="1.0" encoding="UTF-8"?>
<attention-snapshot version="1.0">
  <meta>
    <saved-at>2026-06-25T19:30:00+08:00</saved-at>
    <session-id>abc123</session-id>
    <decision-active>true</decision-active>
    <knowledge-count>4</knowledge-count>
  </meta>

  <!-- Decision: 只在未解决时存在 -->
  <decision>
  Observer 生命周期如何管理
  </decision>

  <!-- Knowledge: 全量持久化，每条带 saved-at 用于衰减计算 -->
  <knowledge>
  <item saved-at="2026-06-25T10:00:00+08:00">Selection 与 Document 分离</item>
  <item saved-at="2026-06-25T14:00:00+08:00">使用 Observer</item>
  <item saved-at="2026-06-25T16:00:00+08:00">Plugin.destroy 作为 dispose 时机</item>
  <item saved-at="2026-06-25T18:00:00+08:00">使用 WeakMap 作为缓存</item>
  </knowledge>

  <!-- State: 与 Decision 绑定，Decision 存在时才有 -->
  <state>
  doing: 验证 Plugin.destroy 覆盖范围
  until: 覆盖所有销毁路径
  </state>

  <!-- Evidence 摘要: 仅供参考，不参与 v19 Evidence 机制，不占 max=5 位置 -->
  <evidence-summary count="3">
  [constraint] 必须兼容 Tiptap Extension API
  [fact] Plugin 有 destroy 生命周期
  [hypothesis] Observer 导致泄漏
  </evidence-summary>
</attention-snapshot>
```

### Decision 已解决时的快照

```xml
<?xml version="1.0" encoding="UTF-8"?>
<attention-snapshot version="1.0">
  <meta>
    <saved-at>2026-06-25T20:00:00+08:00</saved-at>
    <session-id>def456</session-id>
    <decision-active>false</decision-active>
    <knowledge-count>5</knowledge-count>
  </meta>

  <!-- Decision 不存在：问题已解决 -->

  <knowledge>
  <item saved-at="2026-06-25T10:00:00+08:00">Selection 与 Document 分离</item>
  <item saved-at="2026-06-25T14:00:00+08:00">使用 Observer</item>
  <item saved-at="2026-06-25T16:00:00+08:00">Plugin.destroy 作为 dispose 时机</item>
  <item saved-at="2026-06-25T18:00:00+08:00">使用 WeakMap 作为缓存</item>
  <item saved-at="2026-06-25T20:00:00+08:00">Observer 需在 Plugin.destroy 中清理</item>
  </knowledge>

  <!-- State 不持久化：Decision 已解决 -->

  <!-- Evidence 摘要为空：Decision 消失后 Evidence 自动清空 -->
  <evidence-summary count="0">
  </evidence-summary>
</attention-snapshot>
```

## 衰减规则

| Knowledge 条目年龄 | 状态 | 恢复行为 |
|---|---|---|
| < 24h | fresh | 正常注入 v19 Knowledge |
| 24h - 72h | stale | 注入时标注 `[stale]`，Claude 自行判断是否保留 |
| > 72h | expired | 不注入，从快照中删除 |

**stale 标注示例**：
```xml
<restored-knowledge>
Selection 与 Document 分离
使用 Observer
[stale] 使用 WeakMap 作为缓存
</restored-knowledge>
```

**清理规则**：
- 每次 save 时：检查 Knowledge 条目年龄，expired 条目从快照中删除
- 每次 restore 时：如果整个快照 > 72h 且无 Decision，删除整个快照文件
- archive 保留最近 5 个，更早的自动删除

## 恢复注入格式

新对话开始时，将快照内容注入上下文：

```
[attention-persistence] 上次对话工作记忆快照（保存于 {saved-at}）：

<restored-decision>
{decision 内容}
</restored-decision>

<restored-knowledge>
{knowledge 条目，stale 条目标注 [stale]}
</restored-knowledge>

<restored-state>
doing: {state.doing}
until: {state.until}
</restored-state>

<restored-evidence-summary>
上次推理证据（仅供参考，不作为当前 Evidence）：
{evidence 摘要}
</restored-evidence-summary>

请根据当前对话上下文决定是否采纳以上恢复的记忆。stale 条目可能已过时，请验证后决定是否保留。
```

## 恢复后的 v19 行为

1. **Knowledge 恢复**：恢复的条目进入 `<knowledge>` 区域，受 max=8 约束，与新生成条目统一受 relevance-first 规则管理
2. **Decision 恢复**：恢复的 Decision 进入 `<decision>` 区域，新对话可替换
3. **State 恢复**：恢复的 State 进入 `<state>` 区域，Decision 被替换时 State 自然失效
4. **Evidence 不恢复**：`<evidence>` 区域从空开始，按 v19 原有规则收集
5. **恢复的记忆是"建议"**：Claude 有权根据新对话上下文拒绝不相关的恢复

## Skill 命令

通过 Skill tool 触发，args 传入命令名：

| 命令 | 行为 |
|------|------|
| `save` | 手动保存当前工作记忆快照到 snapshot.xml |
| `restore` | 手动从 snapshot.xml 恢复工作记忆 |
| `status` | 查看持久化状态（上次保存时间、快照年龄、Knowledge 条目数） |
| `clear` | 清除持久化快照（snapshot.xml 移入 archive） |

### save 操作指令

1. 读取当前 v19 工作记忆状态（Decision/Knowledge/Evidence/State）
2. 判断是否有有意义的状态（Decision 存在 或 Knowledge 非空）
3. 如果无有意义状态，跳过保存
4. 如果旧 snapshot.xml 存在，将其移入 archive/（按 saved-at 时间戳命名）
5. 清理 archive/ 中超过 5 个的旧快照
6. 写入新 snapshot.xml：
   - Knowledge 条目：保留已有的 saved-at，新增条目使用当前时间
   - Decision：只在未解决时写入
   - State：只在 Decision 存在时写入
   - Evidence：只写入 evidence-summary
7. 清理 expired Knowledge 条目（> 72h）

### restore 操作指令

1. 读取 snapshot.xml
2. 检查快照年龄：如果 > 72h 且无 Decision，删除快照并提示"快照已过期"
3. 对 Knowledge 条目计算衰减状态（fresh/stale/expired）
4. 删除 expired 条目并更新 snapshot.xml
5. 按恢复注入格式输出到对话上下文
6. Claude 自行决定是否采纳恢复的记忆

### status 操作指令

1. 读取 snapshot.xml（如不存在，输出"无持久化快照"）
2. 输出：
   - 上次保存时间
   - 快照年龄
   - Decision 状态（活跃/已解决）
   - Knowledge 条目数及各条目状态（fresh/stale/expired）
   - archive 中快照数

### clear 操作指令

1. 将 snapshot.xml 移入 archive/
2. 输出"已清除持久化快照"

## 与 MEMORY.md 协作

- attention-persistence **不写入** MEMORY.md
- MEMORY.md **不包含**工作记忆快照
- 两者互补：MEMORY.md = 长期知识沉淀，snapshot.xml = 短期工作状态
- **Knowledge 沉淀规则**：Knowledge 条目跨 3+ 次对话仍 relevant → 建议用户沉淀到 MEMORY.md
- 已沉淀到 MEMORY.md 的 Knowledge 条目不再从快照恢复（避免重复）

## 保存/恢复时机

| 时机 | 操作 | 触发方式 |
|------|------|---------|
| 对话结束（Stop） | save | Hook 自动 / 手动 `/attention save` |
| 上下文压缩前（PreCompact） | save | Hook 自动 |
| 新对话开始（SessionStart） | restore | Hook 自动 / 手动 `/attention restore` |
| 用户主动 | save/restore/status/clear | Skill 命令 |