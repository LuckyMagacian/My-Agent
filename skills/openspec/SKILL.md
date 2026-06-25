---
name: openspec
description: "OpenSpec 规范驱动开发工作流（CLI 优先模式）。将 OpenSpec 的 explore → propose → apply → verify → archive 核心工作流适配为 Claude Code 原生操作。要求项目已安装 @fission-ai/openspec CLI。当用户提到 OpenSpec、opsx、规范驱动开发、变更提案、delta spec、/opsx: 命令时自动应用。"
---

# OpenSpec 规范驱动开发

## 触发条件

| 触发词 / 关键词 | 匹配的工作流 |
| --- | --- |
| 探索、分析、调研、我想、不确定 | Explore |
| 提议、规划、新建变更、propose、`/opsx:propose` | Propose |
| 实施、执行、开发、apply、`/opsx:apply` | Apply |
| 验证、检查、verify、`/opsx:verify` | Verify |
| 归档、完成变更、archive、`/opsx:archive` | Archive |
| OpenSpec、opsx、规范驱动、delta spec | 识别为 OpenSpec 上下文，进入对应工作流 |

## 前置条件

**⚠️ OpenSpec CLI 为必需依赖。** 每次激活此 skill 时，执行以下检查：

```
1. 检查 CLI 安装：运行 `openspec --version`
   - 未安装 → 提示用户执行：npm install -g @fission-ai/openspec@latest
   - 已安装 → 继续

2. 检查项目初始化：验证项目根目录下存在 `openspec/` 目录
   - 不存在 → 提示用户执行：openspec init
   - 存在 → 继续

3. 检查 skill/command 文件：验证 `.claude/skills/openspec-*/` 存在
   - 不存在 → 提示用户执行：openspec update
   - 存在 → 继续
```

前置条件不满足时，**仅执行引导安装，不进入工作流**。

## 核心理念

OpenSpec 围绕五个核心概念构建：

```
1. Specs 是真相      — openspec/specs/ 描述系统当前行为，是唯一的权威来源
2. Change 是提案     — openspec/changes/{name}/ 是一个独立的变更单元
3. Delta 描述差异    — 用 ADDED/MODIFIED/REMOVED 描述变更，而非重写整个 spec
4. 制品递进          — proposal → specs → design → tasks → implement，每步为下一步提供上下文
5. 归档合并          — 完成后 archive 将 delta 合并回主 specs，循环闭合
```

**核心原则：先对齐再构建（Agree first, then build confidently）。**

制品递进关系（enablers, not gates — 是使能条件，不是门控条件）：

```
proposal ──► specs ──► design ──► tasks ──► implement
   why        what       how       steps      do it
```

## 目录结构

```
openspec/
├── specs/                           # 系统行为真相（按领域组织）
│   └── {domain}/
│       └── spec.md                  # 领域规范（requirements + scenarios）
└── changes/                         # 变更提案
    ├── {change-name}/               # 活跃变更
    │   ├── .openspec.yaml           # 变更元数据（可选）
    │   ├── proposal.md              # 为什么做 + 范围
    │   ├── design.md                # 技术方案
    │   ├── tasks.md                 # 实施清单
    │   └── specs/                   # Delta specs（描述变更）
    │       └── {domain}/
    │           └── spec.md
    └── archive/                     # 已归档变更
        └── YYYY-MM-DD-{change-name}/
```

**领域划分建议**：按功能区域（`auth/`、`payments/`）、按组件（`api/`、`frontend/`）或按限界上下文（`ordering/`、`fulfillment/`）组织。

## 工作流

### Explore — 探索先行

**触发**：用户不确定要做什么，需要先分析

**执行步骤**：

1. **理解意图**：确认用户想探索的方向
2. **分析代码库**：读取相关代码、现有 specs、目录结构
3. **比较方案**：列出 2-3 个可选路径，说明优劣
4. **提出建议**：推荐最佳路径，说明理由
5. **引导提议**：建议用户运行 propose 进入变更流程

**产出**：无文件产出（纯对话探索）

**注意事项**：
- Explore 是零风险思考伙伴，不创建任何制品
- 如果用户已明确知道要做什么，可跳过 Explore 直接进入 Propose

### Propose — 创建变更提案

**触发**：用户明确要新建变更

**执行步骤**：

1. **确定变更名称**：使用 kebab-case（如 `add-dark-mode`、`fix-auth-bug`）
2. **创建变更目录**：`openspec/changes/{change-name}/`
3. **生成 proposal.md**：Intent + Scope + Approach（见制品格式）
4. **生成 delta specs**：`specs/{domain}/spec.md`（见 Delta Specs 规范）
5. **生成 design.md**：Technical Approach + Architecture Decisions + File Changes
6. **生成 tasks.md**：分组 + 层级编号 + checkbox 清单
7. **等待用户确认**：展示变更概要，等待确认后再进入 Apply

**产出**：

```
openspec/changes/{change-name}/
├── proposal.md
├── specs/{domain}/spec.md
├── design.md
└── tasks.md
```

**⚠️ 强制规则：Propose 完成后必须等待用户确认，收到确认后方可进入 Apply。**

**注意事项**：
- 变更名称避免泛化词（`update`、`changes`、`wip`），使用描述性名称
- Delta specs 只描述变更部分，不重写整个 spec
- Tasks 使用层级编号（1.1、1.2），每个 task 小到一次会话可完成

### Apply — 实施变更

**触发**：用户确认提案，要求开始实施

**执行步骤**：

1. **读取 tasks.md**：获取待完成清单
2. **识别未完成项**：找到所有 `- [ ]` 标记
3. **逐项实施**：按编号顺序，每次完成一个 task
4. **勾选完成**：将 `- [ ]` 更新为 `- [x]`
5. **处理发现**：实施中发现设计问题 → 更新 design.md 后继续；范围变化 → 更新 proposal.md 后继续
6. **完成报告**：所有 tasks 完成后，输出实施总结

**产出**：代码文件 + 更新后的 `tasks.md`

**注意事项**：
- 可中断恢复：下次 Apply 从第一个未完成 task 继续
- 实施中发现问题应更新制品，而非忽略或绕过
- 并行变更：通过指定 change name 区分不同变更

### Verify — 验证实现

**触发**：用户要求验证实现是否匹配规范

**执行步骤**：

1. **完整性检查（Completeness）**：
   - tasks.md 中所有 task 已勾选
   - 每个 requirement 有对应代码实现
   - 每个 scenario 已覆盖

2. **正确性检查（Correctness）**：
   - 实现匹配 spec 的意图
   - Edge case 场景已处理
   - 错误状态与 spec 定义一致

3. **一致性检查（Coherence）**：
   - design.md 的决策在代码中有体现
   - 命名约定与 design 一致
   - 模式使用与设计对齐

4. **输出报告**：按 CRITICAL / WARNING / SUGGESTION 三级分类

**产出**：验证报告（文本输出）

**注意事项**：
- Verify 不阻塞 Archive，但 WARNING 和 CRITICAL 应引起重视
- 建议在 Archive 前运行 Verify

### Archive — 归档变更

**触发**：变更完成，用户要求归档

**执行步骤**：

1. **检查任务完成状态**：验证 tasks.md 中所有 task 已勾选，未完成则警告
2. **合并 delta specs**：
   - 读取 `changes/{name}/specs/{domain}/spec.md`
   - 解析 ADDED / MODIFIED / REMOVED 章节
   - 合并到 `openspec/specs/{domain}/spec.md`
3. **移动至归档**：将变更目录移动到 `changes/archive/YYYY-MM-DD-{name}/`
4. **确认完成**：输出归档摘要

**产出**：

```
openspec/specs/{domain}/spec.md       # 已更新（合并了 delta）
openspec/changes/archive/YYYY-MM-DD-{name}/  # 保留完整上下文
```

**注意事项**：
- Archive 不阻塞于未完成的 tasks，但会警告
- 归档保留所有制品（proposal、design、tasks、delta specs）作为审计记录
- 合并 delta 时，ADDED 追加到主 spec，MODIFIED 替换已有 requirement，REMOVED 删除已有 requirement

## Delta Specs 规范

Delta specs 描述**变更部分**，而非重写整个 spec。三种操作：

| 操作 | 含义 | Archive 时处理 |
| --- | --- | --- |
| `## ADDED Requirements` | 新增行为 | 追加到主 spec |
| `## MODIFIED Requirements` | 修改行为 | 替换已有 requirement |
| `## REMOVED Requirements` | 移除行为 | 从主 spec 删除 |

### Delta Spec 格式

```markdown
# Delta for {Domain}

## ADDED Requirements

### Requirement: {Requirement Name}
The system SHALL/MUST/SHOULD {behavior description}.

#### Scenario: {Scenario Name}
- GIVEN {precondition}
- WHEN {action}
- THEN {expected result}
- AND {additional result}

## MODIFIED Requirements

### Requirement: {Existing Requirement Name}
The system MUST {new behavior}.
(Previously: {old behavior})

#### Scenario: {Scenario Name}
- GIVEN {precondition}
- WHEN {action}
- THEN {expected result}

## REMOVED Requirements

### Requirement: {Deprecated Requirement Name}
(Reason for removal.)
```

### 规范关键字（RFC 2119）

| 关键字 | 含义 |
| --- | --- |
| SHALL / MUST | 绝对要求 |
| SHOULD | 推荐，但可存在例外 |
| MAY | 可选 |

### Delta 而非全量的优势

- **清晰**：只看变更部分，无需对比整个 spec
- **无冲突**：多个 change 可并行修改不同 requirement
- **审查友好**：审查者聚焦变更，而非未变化的上下文
- **适配存量项目**：无需先文档化整个系统即可开始

## 制品格式模板

### proposal.md

```markdown
# Proposal: {Change Name}

## Intent
{为什么做这个变更，解决什么问题}

## Scope
In scope:
- {范围内项 1}
- {范围内项 2}

Out of scope:
- {范围外项 1}（{原因}）

## Approach
{高层技术方案概述}
```

### design.md

````markdown
# Design: {Change Name}

## Technical Approach
{技术方案详细描述}

## Architecture Decisions

### Decision: {决策标题}
{决策内容}

Using {选择} because:
- {理由 1}
- {理由 2}

## Data Flow
```
{数据流图}
```

## File Changes
- `path/to/new-file.tsx` (new)
- `path/to/existing-file.ts` (modified)
````

### tasks.md

```markdown
# Tasks

## 1. {分组标题}
- [ ] 1.1 {任务描述}
- [ ] 1.2 {任务描述}

## 2. {分组标题}
- [ ] 2.1 {任务描述}
- [ ] 2.2 {任务描述}
```

**Task 编写原则**：
- 分组归类相关 task
- 层级编号（1.1、1.2）
- 每个 task 小到一次会话可完成
- 完成后将 `- [ ]` 更新为 `- [x]`

### spec.md（主 Specs）

```markdown
# {Domain} Specification

## Purpose
{领域的高层描述}

## Requirements

### Requirement: {Requirement Name}
The system SHALL {behavior}.

#### Scenario: {Scenario Name}
- GIVEN {precondition}
- WHEN {action}
- THEN {expected result}
- AND {additional result}
```

**Spec 是行为契约，不是实现计划**：
- ✅ 可观察的行为、输入/输出/错误条件、外部约束
- ❌ 内部类/函数名、库/框架选择、逐步实现细节

## 与 software-development-workflow 的协作

两者在不同维度互补，可独立使用也可组合使用。

### 维度对比

| 维度 | OpenSpec | software-development-workflow |
| --- | --- | --- |
| 核心定位 | **变更管理结构** — 管理变更的生命周期 | **开发流程策略** — 决定走哪种开发模式 |
| 提供什么 | change folder + delta specs + archive 循环 | 需求开发/变更/修复/分析/优化 五种模式 |
| 文档容器 | `openspec/changes/{name}/` | `docs/requirements/` `docs/design/` 等 |
| 流程控制 | explore → propose → apply → verify → archive | 文档先行 → 用户确认 → 按文档编码 |
| 核心价值 | Delta 描述差异，适合存量项目迭代 | 文档先行，适合从零到一的规范开发 |
| Specs 作用 | 行为契约 + 自动合并 | 无对应概念（文档是执行依据） |

### 协作模式

#### 模式 A：独立使用（默认）

- **OpenSpec 独立**：项目已有 OpenSpec CLI，使用 explore → propose → apply → verify → archive 全流程
- **sdw 独立**：项目未引入 OpenSpec，使用 sdw 的五种模式（需求开发/变更/修复/分析/优化）

#### 模式 B：OpenSpec 为主，sdw 辅助

**适用场景**：项目已采用 OpenSpec，但需要 sdw 的模式判断能力

```
用户发起任务
  ↓
sdw 模式判断（三问验证）→ 确定走哪种模式
  ↓
OpenSpec explore → 确认方向
  ↓
OpenSpec propose → 创建变更提案（制品放入 openspec/changes/）
  ↓
OpenSpec apply → 按文档实施
  ↓
OpenSpec verify → 验证实现
  ↓
OpenSpec archive → 归档
```

**映射关系**：

| sdw 模式 | OpenSpec 操作 | 制品映射 |
| --- | --- | --- |
| 完整需求开发 | propose（scope=新模块） | proposal.md ≈ 需求说明书，design.md ≈ 设计说明书，tasks.md ≈ 详细设计 |
| 功能变更 | propose（scope=现有模块修改） | proposal.md ≈ 变更计划，delta specs 描述变更差异 |
| 问题修复 | propose（scope=bug fix） | proposal.md ≈ 问题分析文档，delta specs 描述修复后的行为变化 |
| 技术分析 | explore（只读） | 无制品产出，纯对话分析 |
| 方案优化 | explore + propose | explore 输出方案对比，propose 创建选中的方案 |

#### 模式 C：sdw 为主，OpenSpec 辅助

**适用场景**：项目以 sdw 为主流程，但需要 OpenSpec 的 delta specs 和变更追踪能力

```
用户发起任务
  ↓
sdw 模式判断 → 确定走哪种模式
  ↓
sdw 执行流程（文档先行）
  ↓
OpenSpec sync → 将 sdw 产出的文档同步到 openspec/specs/ 作为行为真相
  ↓
（下次变更时，OpenSpec 的 delta specs 基于 openspec/specs/ 描述差异）
```

**文档同步映射**：

| sdw 文档 | OpenSpec spec 对应 |
| --- | --- |
| `docs/requirements/{主题}-需求说明书.md` | `openspec/specs/{domain}/spec.md` 的 Requirements |
| `docs/design/{主题}-设计说明书.md` | `openspec/changes/{name}/design.md` |
| `docs/changes/{主题}.md` | `openspec/changes/{name}/proposal.md` + delta specs |
| `docs/bugs/{问题}.md` | `openspec/changes/fix-{bug}/proposal.md` + delta specs |

### 协作决策

```
项目是否已安装 OpenSpec CLI？
  ├── 是 → 项目是否已使用 sdw？
  │       ├── 是 → 使用模式 B（OpenSpec 为主，sdw 辅助模式判断）
  │       └── 否 → 使用 OpenSpec 独立流程
  └── 否 → 使用 sdw 独立流程
```

## 与 attention-maintenance 的协作

attention-maintenance 维护**短期工作记忆**（Decision/Knowledge/Evidence/State），OpenSpec 管理**变更持久化结构**（specs/changes/archive）。两者分别解决"对话中的注意力保持"和"跨对话的知识沉淀"。

### 维度对比

| 维度 | attention-maintenance | OpenSpec |
| --- | --- | --- |
| 时间跨度 | 单次对话会话内 | 跨对话会话 |
| 生命周期 | Decision 消失 → Evidence 清空 | Archive → specs 永久保留 |
| 核心问题 | 当前在解决什么？推理依据？ | 系统当前行为是什么？变更差异？ |
| 信息密度 | 极简（4 组件，Knowledge≤8, Evidence≤5） | 完整（proposal+design+tasks+delta） |
| 存储位置 | 对话上下文中（非文件） | `openspec/` 目录（文件） |

### 协作方式：工作记忆 ↔ 持久化结构

**核心原则**：attention-maintenance 管推理过程，OpenSpec 管推理结论的沉淀。

```
对话内推理（attention-maintenance）       跨对话持久化（OpenSpec）
┌─────────────────────────┐            ┌─────────────────────────┐
│ <decision>              │            │ openspec/changes/{name}/│
│ 如何实现暗黑模式切换     │            │ proposal.md             │
│ </decision>             │   沉淀     │ design.md               │
│                         │ ────────►  │ tasks.md                │
│ <knowledge>             │            │ specs/ui/spec.md        │
│ CSS variables 方案      │            │                         │
│ 系统偏好检测可行        │            │ openspec/specs/          │
│ </knowledge>            │   载入     │ ui/spec.md              │
│                         │ ◄────────  │                         │
│ <evidence>              │            │                         │
│ [constraint] 无新依赖   │            │                         │
│ [fact] 浏览器支持       │            │                         │
│ </evidence>             │            │                         │
└─────────────────────────┘            └─────────────────────────┘
```

### 各工作流中的协作映射

| OpenSpec 工作流 | attention-maintenance 角色 | 协作动作 |
| --- | --- | --- |
| **Explore** | Decision=探索方向，Evidence 收集方案对比证据 | Explore 结论 → 准备 Propose 时，Knowledge 中的结论融入 proposal.md |
| **Propose** | Decision=变更范围/方案选择，Evidence 收集约束和事实 | Knowledge 结论 → 写入 proposal.md 的 Intent/Scope；Evidence 中的 constraint → 写入 design.md 的 Architecture Decisions |
| **Apply** | Decision=当前 task 的实现问题，State.doing=正在实现的 task | State.doing 与 tasks.md 的当前 checkbox 对齐；Knowledge 中实现相关的结论 → 指导编码 |
| **Verify** | Decision=验证中发现的问题，Evidence 收集验证证据 | Verify 的 CRITICAL/WARNING → 新 Decision + Evidence 驱动修复 |
| **Archive** | Decision 消失（变更完成），Evidence 清空 | Knowledge 中的最终结论已沉淀在 specs/ 中，无需人工迁移 |

### 关键规则

1. **Decision 对齐变更**：OpenSpec 活跃变更期间，`<decision>` 应与当前变更的核心问题对齐
2. **Knowledge 与 Specs 互补**：Knowledge 存推理前提（为什么选 A 不选 B），specs 存行为契约（系统应该怎样）。两者不重复
3. **State.doing 与 tasks.md 对齐**：`State.doing` 应与 `tasks.md` 中当前正在实施的 task 一致
4. **Archive 触发清空**：Archive 完成后，Decision 消失 + Evidence 清空，Knowledge 保留与下一变更相关的条目
5. **新对话载入**：新对话开始时，从 `openspec/specs/` 和活跃 `changes/` 的制品中提取关键信息填入 Knowledge

## 检查清单

### Explore
- [ ] 已理解用户意图
- [ ] 已分析相关代码和现有 specs
- [ ] 已列出可选方案并比较优劣
- [ ] 已给出推荐路径及理由

### Propose
- [ ] 变更名称为 kebab-case 且具描述性
- [ ] proposal.md 包含 Intent + Scope + Approach
- [ ] Delta specs 使用 ADDED/MODIFIED/REMOVED 格式
- [ ] design.md 包含技术方案 + 架构决策 + 文件变更
- [ ] tasks.md 使用层级编号 + checkbox
- [ ] 已等待用户确认

### Apply
- [ ] 按 tasks.md 顺序逐项实施
- [ ] 每个 task 完成后勾选 `- [x]`
- [ ] 实施中发现问题已更新制品
- [ ] 所有 tasks 完成后输出总结

### Verify
- [ ] 完整性：所有 tasks 已完成，所有 requirements 有实现
- [ ] 正确性：实现匹配 spec 意图，edge case 已处理
- [ ] 一致性：design 决策在代码中有体现
- [ ] 报告按 CRITICAL / WARNING / SUGGESTION 分类

### Archive
- [ ] 检查 tasks 完成状态（未完成则警告）
- [ ] Delta specs 已合并到主 specs
- [ ] 变更已移动至 `changes/archive/YYYY-MM-DD-{name}/`
- [ ] 归档摘要已输出
