---
name: common-loop
description: "通用多轮 agent loop 编排规范。分析意图->确认目标->拆分任务->确认任务列表->循环(executor执行->reviewer检查->判定->重试)->目标达成检查->汇报。完全自包含，零外部 skill 依赖，可独立分享。"
---

# common_loop：通用多轮 agent loop

## 1. 概述

### 1.1 定位
common_loop 是**完全自包含**的通用多轮 agent loop 编排规范。所有规则内化，零外部 skill 依赖，分享 `skills/common_loop/` + 2 个 subagent 即可独立运行。

### 1.2 设计原则
- **完全自包含**：意图分析/任务拆分/检查规则/失败处理/目标达成全部内置，不引用任何外部 skill
- **可分享**：无项目内 skill 依赖，可整体移植
- **规则有出处但已内化**：部分规则设计参考了成熟实践，但已内化为 common_loop 自有规则，非运行时依赖

### 1.3 形态
- **common_loop SKILL.md**（本文件）：编排规范 + 内化规则集
- **common_executor subagent**：统一执行入口（自身执行优先，复杂技术域转交）
- **result_reviewer subagent**：独立检查者（任务级 + 目标级）
- **templates/**：内化规则的可执行模板

### 1.4 核心思想
意图分析 -> 确认目标 -> 拆分任务 -> 确认任务列表 -> 循环(执行->检查->判定->重试) -> 目标达成检查 -> 汇报

## 2. 适用场景

### 2.1 适用
- 任务需拆分为多个子任务，子任务间有顺序或依赖关系
- 每个子任务完成需验证（非信任执行者自述）
- 子任务可能失败并需重试或调整
- 目标达成需整体评估

### 2.2 不适用
- 单文件少量修改、文案/配置微调、纯探索性调试（直接执行）

## 3. 角色定义

| 角色 | 载体 | 职责 |
|------|------|------|
| 主循环 | 本 SKILL.md（Claude 遵循） | 意图分析、任务拆分、路由判定、状态机驱动、目标达成检查、汇报、恢复检测 |
| common_executor | subagent | 接收单任务执行产出；自身执行优先，复杂技术域转交 |
| result_reviewer | subagent | 独立检查执行结果（任务级 + 目标级），不信任 executor 自述 |

## 4. 核心流程（7 阶段）

### ① 分析意图（内置）
- 关键词信号识别任务类型（新功能/变更/修复/分析/优化），多类命中优先级：修复>变更>新功能>优化>分析
- 三问验证产出可验证目标：要解决什么问题？完成后如何验证？边界在哪？
- 输出：任务类型 + 目标声明 draft

### ② 确认目标 ✋
- AskUserQuestion 与用户确认目标（含验收标准）
- 生成 run_dir：`docs/loop-runs/{YYYY-MM-DD}-{slug}/`（slug = slugify(目标标题)[:20]，保留中文/字母/数字）
- 写入 goal.md（目标 + 验收标准 + 边界 + 元数据 goal_check_round:0）
- **恢复检测**：入口先 detect_unfinished_runs，有未完成实例则提示恢复
- 约束：未确认不得进入拆分

### ③ 拆分任务（内置）
- Markdown checklist，每任务含：ID/描述/预期产出/完成标准/依赖
- 单任务一个动作单元，禁止 TBD/占位符
- 完成标准必须可验证（命令/输出/diff）
- 写入 tasks.md（持久化 source of truth）+ TodoWrite（运行态镜像）

### ④ 确认任务列表 ✋
- AskUserQuestion 确认任务列表
- 约束：未确认不得进入执行

### ⑤ 循环执行（全自动，串行）
对每个 pending 任务（next_pending：依赖全 completed 的首个 pending）：
1. 状态 -> in_progress
2. 主循环 classify_domain 判定 target（含目标存在性探测，不存在降级 self）
3. dispatch_executor（self 模式引导读取 tasks.md / adapter 模式内联任务条目）
4. 状态 -> reviewing，dispatch_reviewer（产出 reports/T{n}-r{m}.md）
5. 完成判定（五步 Gate）：通过 -> completed；未通过 -> 触发 §6 失败处理
6. 每次状态变更同步 TodoWrite
- **当前版本仅支持串行执行**，并行执行为后续增强

### ⑥ 目标达成检查
- dispatch_reviewer_goal_check（goal-check 模板，三维：Completeness/Correctness/Consistency，聚焦跨任务集成点）
- **Rework 处理**：已完成任务因集成问题需回滚 -> completed->pending -> EXECUTE_LOOP
  - rework_round 计数，上限 2；超限（>2）强制走 goal_check 升级询问
- **未达成处理**：goal_check_round++（持久化到 goal.md）
  - 首次未达成（round=1）：按 gap_type 自动回退
    - task_omission（任务遗漏）-> 补充任务回 ④ 确认
    - goal_unreachable（目标不可达）-> 回 ② 重新确认目标
  - 二次未达成（round>=2）：升级询问（4 选项）
    - 重新确认目标(回②) / 重新拆分任务(回③) / 中止 / 人工介入
    - 选择重做时重置 goal_check_round=0 + rework_round=0（持久化到 goal.md）

### ⑦ 汇报 ✋
- 写入 final-report.md（完成标志，供恢复检测）
- AskUserQuestion 汇报（目标达成情况、关键变更、遗留问题）
- 选项：确认完成 / 补充任务（回②） / 开新 loop

## 5. 任务状态机

```
pending ──> in_progress ──> reviewing ──> completed
   │            │              │
   │            │              └──未通过──> in_progress（重试，见 §6）
   │            │
   │            └──dispatch_error(self也失败)──> blocked ──> ✋升级询问
   │
   └──(级联)──> blocked/skipped
```

**终态分两类**：
- **调度终态**（execute_loop 不再自动调度）：completed / blocked / skipped / aborted
- **任务终态**（不可转换）：completed / skipped / aborted（blocked 可经用户操作转为 skipped/pending/aborted）

**升级询问响应矩阵**（blocked 时 ask_user_escalate）：

| 选项 | task.status | attempt | 下游处置 | loop 动作 |
|------|------------|---------|---------|----------|
| 跳过 | skipped | 归零（局部变量） | cascade_skip 联动跳过 | 继续 loop |
| 调整任务 | pending | 归零 | cascade_unblock 恢复下游 | 回 ④ 确认 |
| 中止 | aborted | - | 全部未完成 -> aborted | abort_cleanup -> TERMINATED |
| 人工介入 | blocked（保持） | 保持 | cascade_blocked 级联 | TERMINATED（暂停） |

**中止收尾**（abort_cleanup）：未完成任务标 aborted + 生成 partial-report.md + 保留 tasks.md 为恢复锚点。

## 6. 失败处理状态机（两阶段重试 + 阻断性分析）

```
执行 -> reviewer 检查未通过
  ├─ attempt < 3 -> 重试（失败原因+历史回传 executor），attempt++
  └─ attempt == 3 -> run_failure_analysis(round=1)
        ├─ 阻断性 -> blocked -> ✋升级询问
        └─ 非阻断性 -> 第 2 阶段重试
              ├─ attempt < 6 -> 重试，attempt++
              └─ attempt == 6 -> run_failure_analysis(round=2) -> blocked -> ✋升级询问
```

- **attempt 语义**：前增（初始 0，每轮执行前 +=1），每轮 = 一次 dispatch_executor + 一次 dispatch_reviewer，总计 6 轮上限
- **dispatch_error**：非 self 失败 -> force_self=True 降级（不增 attempt）；self 也失败 -> blocked + ask_user_escalate
- **阻断性分析 6 维度**（failure-analysis 模板）：缺失依赖/技术不可行/需求矛盾/反复失败同因/验证合理性/路由错误
- round=2（attempt==6）无论阻断与否 -> blocked 升级（不再重试）

## 7. 内化规则集

### 7.1 意图分析器
关键词信号 + 三问验证（见 §4 ①）

### 7.2 任务拆分器
Markdown checklist + 单任务一动作 + 禁止占位符 + 含完成标准（见 §4 ③）

### 7.3 检查 Gate（五步，不信任 executor 自述）
1. **IDENTIFY**：哪些命令证明完成标准（测试/lint/类型检查/构建/运行）
2. **RUN**：完整执行（不跳过、不缩短）
3. **READ**：完整输出 + 退出码 + 失败数
4. **VERIFY**：逐条对照完成标准
5. **声明**：证据支撑才声明通过

**声明-证据对照**：测试需 0 failures（非"should pass"）；bug 修复需原症状测试通过；agent 委派需检查 VCS diff 而非相信报告。
**危险词清单**：should/probably/seems/Done/Great 等不接受为证据。
**修复类任务 Red-Green**：IDENTIFY 原症状复现命令，RUN 先验证修复前失败、再验证修复后通过。

### 7.4 失败处理器
两阶段重试 + 阻断性分析（见 §6）

### 7.5 目标达成评估
三维（Completeness/Correctness/Consistency），聚焦跨任务集成点（接口契约/端到端/数据流），含 Rework 判断。

## 8. 数据格式

### 8.1 goal.md
```markdown
# 目标声明
## 目标
{一句话目标}
## 验收标准
- [ ] {可验证标准}
## 边界（不做什么）
- {排除项}
## 元数据
- 任务类型：{修复/变更/新功能/优化/分析}
- 创建日期：{YYYY-MM-DD}
- run_dir：docs/loop-runs/{date}-{slug}/
- goal_check_round: 0
```

### 8.2 tasks.md
```markdown
# 任务清单：{目标}
## 目标声明
{确认后的可验证目标}
## 任务列表
- [ ] T1 {任务描述}
  - 预期产出：...
  - 完成标准：...
  - 依赖：[]
  - 状态：pending
  - 失败原因：{重试时}
  - 失败历史：{reports 路径列表}
```

### 8.3 检查报告（每轮独立文件）
路径：`docs/loop-runs/{date}-{slug}/reports/T{n}-r{m}.md`，含结论/证据/原因/建议。

### 8.4 TodoWrite 同步
tasks.md 为 source of truth，TodoWrite 为运行态镜像，每次状态变更同步（blocked/skipped/aborted 以 completed+前缀标记）。

## 9. 恢复机制（不依赖 attention-maintenance）

### 9.1 恢复检测
入口 detect_unfinished_runs 扫描 `docs/loop-runs/`：
- 有 tasks.md 但无 final-report.md 且无 partial-report.md -> 未完成
- 有 partial-report.md -> 已中止
- 有 final-report.md -> 已完成，不恢复

### 9.2 状态重建
reconstruct_state：从 tasks.md 读取任务状态 + goal.md 读取 goal_check_round；in_progress/reviewing 重置为 pending（attempt 是局部变量，恢复后从 0 重新计数，失败历史保留）。

### 9.3 恢复流程
resume_run：展示进度 -> AskUserQuestion 确认 -> 从 next_pending 恢复执行。

## 10. 自包含边界声明

| 项 | 是否依赖 | 说明 |
|----|---------|------|
| 意图分析/任务拆分/检查Gate/失败处理/目标达成 | ❌ 不依赖 | 全部内置 |
| 技术域 subagent（Neo/Echo 等） | ⚠️ 可选 | classify_domain 探测，不存在降级 self |
| 工作记忆（attention-maintenance） | ⚠️ 可选 | 使用方维护，common_loop 不依赖 |
| AskUserQuestion / Agent / Write / TodoWrite | ✅ 依赖 | 宿主环境原生工具 |

**分享边界**：分享 `skills/common_loop/` + `common_executor.agent.md` + `result_reviewer.agent.md` 即可独立运行。

## 11. 可选增强（非依赖）

- **工作记忆维护**（如 attention-maintenance）：使用方全局规则要求时启用，提供跨对话 Decision/State 维护
- **技术域 subagent**：使用方具备 Neo/Echo/Ops 等时，executor 路由增强；否则全自执行
