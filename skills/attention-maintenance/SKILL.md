---
name: attention-maintenance
description: "必须在每一次执行代码修改、分析报错日志、或长对话产生后“持续激活”。每当用户说“继续”、“下一步”或提供新代码时，必须强制加载此技能"
---

# 注意力维持系统

## 触发条件

| 条件 | 说明 |
| --- | --- |
| 对话轮次 | 超过10轮交互后自动激活 |
| 任务复杂度 | 涉及多文件修改或多步骤操作 |
| 用户反馈 | 用户指出AI偏离主题或重复行为 |
| 长时间任务 | 预计执行时间超过5分钟的任务 |

## 核心机制

### 1. 任务锚点（Task Anchor）

使用 `<task-anchor>` XML标签维持核心目标，在每次复杂操作前输出：

```xml
<task-anchor>
  <original-request>用户原始请求的精确表述</original-request>
  <core-objective>任务的核心目标（一句话）</core-objective>
  <checklist>
    - [ ] 待完成项1
    - [ ] 待完成项2
    - [x] 已完成项1
  </checklist>
  <current-focus>当前正在处理的部分</current-focus>
</task-anchor>
```

**触发时机**：
- 连续3次工具调用后
- 切换任务方向时
- 遇到错误需要调整策略时
- 用户指出偏离主题时

### 2. 注意力分散检测

检测以下模式并主动纠正：

| 模式 | 检测信号 | 纠正动作 |
| --- | --- | --- |
| 循环重复 | 连续2次输出结构相似的内容 | 立即停止，重新确认任务 |
| 过度探索 | 连续3次只读操作无输出 | 总结发现，询问用户方向 |
| 偏离主题 | 工作内容与原始请求无关联 | 回顾任务锚点，重新对齐 |
| 完美主义 | 反复优化已完成的部分 | 评估改进必要性，必要时询问用户 |

### 3. 上下文维护

定期（每5轮）执行上下文检查，使用 `<context-snapshot>` 标签：

```xml
<context-snapshot>
  <user-goal>用户目标的一句话描述</user-goal>
  <current-phase>当前所处的工作阶段</current-phase>
  <key-decisions>
    - 决策1：原因
    - 决策2：原因
  </key-decisions>
  <next-action>即将执行的下一个动作</next-action>
</context-snapshot>
```

### 4. 进展同步

在以下时机主动向用户同步进展：

- 完成一个主要步骤后
- 遇到需要用户决策的分支时
- 发现与预期不符的情况时
- 预计还需较多工作时

## 执行规则

1. **任务锚点必须包含checklist**：将任务分解为可勾选的步骤，每完成一步立即标记 `[x]`
2. **核心目标用XML标签包裹**：始终在 `<task-anchor>` 中维护 `<core-objective>`，防止目标漂移
3. **先确认后执行**：不确定时先问用户，不要假设
4. **增量输出**：每完成一步就输出结果，不要积攒大量修改
5. **错误优先**：遇到错误立即处理，不要继续执行后续步骤
6. **保持简洁**：输出聚焦于结果，减少过程描述

## 与其他Skill的协作

- 与 `software-development-workflow` 配合：在开发流程的每个阶段检查点应用注意力维持
- 与 `brainstorming` 配合：在创意探索中防止过度发散
- 与 `executing-plans` 配合：在执行计划时保持对目标的追踪

## 使用示例

**任务开始时**：
```xml
<task-anchor>
  <original-request>为用户登录功能添加验证码</original-request>
  <core-objective>实现登录验证码的生成、发送、验证流程</core-objective>
  <checklist>
    - [ ] 设计验证码数据模型
    - [ ] 实现验证码生成接口
    - [ ] 实现短信发送服务
    - [ ] 实现验证码验证逻辑
    - [ ] 添加前端输入组件
  </checklist>
  <current-focus>待开始</current-focus>
</task-anchor>
```

**任务进行中（更新checklist）**：
```xml
<task-anchor>
  <original-request>为用户登录功能添加验证码</original-request>
  <core-objective>实现登录验证码的生成、发送、验证流程</core-objective>
  <checklist>
    - [x] 设计验证码数据模型
    - [x] 实现验证码生成接口
    - [ ] 实现短信发送服务
    - [ ] 实现验证码验证逻辑
    - [ ] 添加前端输入组件
  </checklist>
  <current-focus>实现短信发送服务</current-focus>
</task-anchor>
```

## 自检清单

在声称任务完成前，确认：

- [ ] `<task-anchor>` 中的 checklist 所有项已标记 `[x]`
- [ ] `<core-objective>` 与用户原始请求一致
- [ ] 没有遗留的TODO或未处理的错误
- [ ] 修改经过了基本验证（类型检查、语法检查等）
