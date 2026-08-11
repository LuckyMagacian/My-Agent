---
name: common-loop
description: "通用多轮 agent loop 编排规范（v3 吸收 workmode）。分析意图->确认目标->拆分任务->确认任务列表->循环(外层 6 轮重试×内层 N 轮质量收敛)->目标达成检查->汇报。完全自包含，零外部 skill 依赖。"
---

# common_loop：通用多轮 agent loop（v3 吸收 workmode）

## 1. 概述

### 1.1 定位
common_loop 是**完全自包含**的通用多轮 agent loop 编排规范（v3）。所有规则内化，零外部 skill 依赖，分享 `skills/common_loop/` + 2 个 subagent 即可独立运行。

### 1.2 设计原则
- **完全自包含**：意图分析/任务拆分/检查规则/失败处理/目标达成/质量收敛/防膨胀全部内置，不引用任何外部 skill
- **可分享**：无项目内 skill 依赖，可整体移植
- **规则有出处但已内化**：v3 吸收的 workmode 机制（评分收敛/零增量/同根因熔断/减法轮/优先级阶梯）已内化为本 skill 自有规则，非运行时依赖
- **双层循环**：外层 6 轮重试（处理阻断/路由错误）+ 内层 N 轮质量收敛（处理单次产出的多轮逼近）

### 1.3 形态
- **common_loop SKILL.md**（本文件）：编排规范 + 内化规则集
- **common_executor subagent**：5 段交付物（标题/正文/变更说明/摘要/未落实项声明），含零增量论证
- **result_reviewer subagent**：评分+收敛建议+根因标签+零增量审计+简洁性审视
- **templates/**：task-dispatch / review-check / failure-analysis / goal-check / **arbiter-record**（v3 新增）
- **arbiter 角色**：由主循环（Main Agent）兼任，受独立性约束（见 §3.3）

### 1.4 核心思想
意图分析 -> 确认目标 -> 拆分任务 -> 确认任务列表 -> 循环(外层执行->内层质量收敛) -> 目标达成检查 -> 汇报

## 2. 适用场景

### 2.1 适用
- 任务需拆分为多个子任务，子任务间有顺序或依赖关系
- 每个子任务需多轮质量逼近（v3 新增）
- 每个子任务完成需验证（非信任执行者自述）
- 子任务可能失败并需重试或调整
- 目标达成需整体评估（含跨任务集成点）

### 2.2 不适用
- 单文件少量修改、文案/配置微调、纯探索性调试（直接执行）

## 3. 角色定义

| 角色 | 载体 | 职责 |
|------|------|------|
| 主循环 | 本 SKILL.md（Claude 遵循） | 意图分析、任务拆分、路由判定、状态机驱动、**arbiter 仲裁**、目标达成检查、汇报、恢复检测 |
| common_executor | subagent | 5 段交付物（标题/正文/变更说明/摘要/未落实项声明），含零增量论证；自身执行优先，复杂技术域转交 |
| result_reviewer | subagent | 任务级（评分+收敛建议+根因标签+零增量审计+简洁性审视）+ 目标级（三维集成评估+Rework） |
| arbiter | **主循环兼任**（v3 新增） | 内层质量轮的仲裁决策（收敛判定/整合意见/减法轮宣布/优先级阶梯裁决） |

### 3.1 独立性原则
- executor 与 reviewer 互不可见对方的推理过程，评估只看产物本身
- reviewer 之间上下文隔离（本版本默认单视角，多视角由任务分发方注入）
- **arbiter 受约束**：不得越权评估（见 §3.3）

### 3.2 角色能力要求与降级

| 角色 | 能力要求 | 降级 |
|------|---------|------|
| executor | 通用内容生产能力 | 主循环可兼任（独立性偏差，仲裁记录标注） |
| reviewer | 独立内容评估能力 | **不可降级**——必须由独立 subagent 担任 |
| arbiter | 全局视野 + 报告解读 + 裁决留痕 | 主循环本职，不可降级 |

### 3.3 主循环仲裁约束（v3 新增）
主循环虽具全局视野，仲裁时仍受约束：
1. **以报告为准**：整合结论必须基于 reviewer 报告，不得以自身判断替代
2. **不越权评估**：Main Agent 若发现报告未提及的问题，不得直接计入结论；纳入整合意见回传 executor 修正
3. **裁决留痕**：每次仲裁产出仲裁记录（arbiter-record.md），落盘可追溯
4. **不得单方判定交付**：交付权归 reviewer；仅 reviewer 建议收敛 + 满足其他收敛条件时，主循环方可宣告完成

## 4. 核心流程（7 阶段）

### ① 分析意图（内置）
- 关键词信号识别任务类型（新功能/变更/修复/分析/优化），多类命中优先级：修复>变更>新功能>优化>分析
- 三问验证产出可验证目标：要解决什么问题？完成后如何验证？边界在哪？
- 输出：任务类型 + 目标声明 draft

### ② 确认目标 ✋
- AskUserQuestion 与用户确认目标（含验收标准）
- 生成 run_dir：`run_dir/{YYYY-MM-DD}-{slug}/`（slug = slugify(目标标题)[:20]，保留中文/字母/数字）
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

### ⑤ 循环执行（外层 6 轮重试 × 内层 N 轮质量收敛，v3）

**当前版本仅支持串行执行**，并行执行为后续增强。

对每个 pending 任务（next_pending：依赖全 completed 的首个 pending）：

**外层（每 attempt）**：
1. 状态 -> in_progress
2. 主循环 classify_domain 判定 target（含目标存在性探测，不存在降级 self）
3. dispatch_executor（self 模式引导读取 tasks.md / adapter 模式内联任务条目）
4. 状态 -> reviewing，进入内层质量收敛

**内层（每 quality_round，1..N 默认 3）**：
1. **执行**：dispatch_executor 产出 5 段交付物（标题/正文/变更说明/摘要/未落实项声明）
2. **评估**：dispatch_reviewer（单视角默认）产出评分+收敛建议+问题清单+根因标签+零增量审计+简洁性审视
3. **仲裁**：主循环作为 arbiter 按 §6 收敛判定核验，产出 arbiter-record.md
4. **判定**：
   - 收敛 → attempt 通过，状态 -> completed
   - 未收敛 + q_round < N → 整合意见回传 executor，开启下一 quality_round
   - 未收敛 + q_round == N → 内层耗尽，attempt 失败，进入外层失败处理
5. 每次状态变更同步 TodoWrite

**外层失败处理**（attempt 失败后）：
- attempt < 3 → 下次 attempt（quality_round 重置为 0）
- attempt == 3 → run_failure_analysis(round=1) → 阻断？blocked；非阻断？下次 attempt
- 3 < attempt < 6 → 下次 attempt
- attempt == 6 → run_failure_analysis(round=2) → blocked 升级询问

### ⑥ 目标达成检查
- dispatch_reviewer_goal_check（goal-check 模板，三维：Completeness/Correctness/Consistency，聚焦跨任务集成点 + v3 质量评分摘要）
- **Rework 处理**：已完成任务因集成问题需回滚 -> completed->pending（quality_round 重置为 0，issue-log 转只读归档 `issue-log-restart.md`）
  - rework_round 计数，上限 2；超限（>2）强制走 goal_check 升级询问
- **未达成处理**：goal_check_round++（持久化到 goal.md）
  - 首次未达成（round=1）：按 gap_type 自动回退
    - task_omission（任务遗漏）-> 补充任务回 ④ 确认
    - goal_unreachable（目标不可达）-> 回 ② 重新确认目标
    - **integration_break**（v3 新增，集成断裂）-> 触发 Rework
  - 二次未达成（round>=2）：升级询问（4 选项）

### ⑦ 汇报 ✋
- 写入 final-report.md（完成标志，供恢复检测）
- AskUserQuestion 汇报（目标达成情况、关键变更、遗留问题）
- 选项：确认完成 / 补充任务（回②） / 开新 loop

## 5. 任务状态机

```
pending ──> in_progress ──> reviewing ──> completed
   │            │              │
   │            │              └──未通过──> in_progress（内层重试，q_round++）
   │            │                       │
   │            │                       └──内层耗尽 (q_round==N)──> attempt 失败
   │            │                                                       │
   │            │                                                       ↓
   │            │                              attempt 失败处理 (§5.5)
   │            │
   │            └──dispatch_error(self也失败)──> blocked ──> ✋升级询问
   │
   └──(级联)──> blocked/skipped
```

**v3 扩展字段**（tasks.md 任务条目内）：
```markdown
### T2: 修复登录接口
- 状态: in_progress
- 外层 attempt: 1/6
- 内层 quality_round: 2/3
- 最近评分: 6.5
- 内层路径: inner/T2/
```

**终态分两类**：
- **调度终态**（execute_loop 不再自动调度）：completed / blocked / skipped / aborted
- **任务终态**（不可转换）：completed / skipped / aborted（blocked 可经用户操作转为 skipped/pending/aborted）

**升级询问响应矩阵**（blocked 时 ask_user_escalate）：

| 选项 | task.status | attempt | 下游处置 | loop 动作 |
|------|------------|---------|---------|----------|
| 跳过 | skipped | 归零 | cascade_skip | 继续 loop |
| 调整任务 | pending | 归零 | cascade_unblock | 回 ④ 确认 |
| 中止 | aborted | - | 全部未完成 -> aborted | abort_cleanup -> TERMINATED |
| 人工介入 | blocked（保持） | 保持 | cascade_blocked | TERMINATED（暂停） |

**中止收尾**（abort_cleanup）：未完成任务标 aborted + 生成 partial-report.md + 保留 tasks.md 为恢复锚点。

## 6. 收敛判定（v3 新增）

> 收敛判定**替换原 Pass/Fail**，由主循环作为 arbiter 在每次内层质量轮末执行。

### 6.1 收敛条件（全部满足）

| 条件 | 默认规则 |
|------|---------|
| reviewer 收敛建议 | 「建议收敛」 |
| 评分 | ≥ 阈值（默认 8/10） |
| 阻断级问题 | = 0 |
| 问题台账 | 阻断/重要级已闭合（见 §8） |
| 收敛加速 | 无重要级问题 OR 已评分承载 |

### 6.2 整合结论三态

- **✅ 确认收敛** → 任务 completed
- **❌ 整合意见**（未收敛）→ q_round < N 时进入下一 quality_round；q_round == N 时 attempt 失败
- **⚠️ 升级人工** → 内层耗尽 + 权衡项无法裁决

### 6.3 收敛加速
- 当存在「重要」级问题时，整合意见仅回传「阻断」级 + 「重要」级，「建议」级暂不纳入
- 当不存在「重要」级问题时，整合意见仅回传「阻断」级
- 收敛条件满足时即确认，不因「建议」级未解决而继续迭代
- 「重要」级问题通过拉低评分间接阻止收敛，不作独立前置条件

### 6.4 评分标度

| 维度 | 分值 | 关注 |
|------|------|------|
| 正确性 | 5 | 满足任务目标与约束；逻辑/数据/引用正确 |
| 完整性 | 3 | 任务要求齐全；边界/异常/必要说明补全 |
| 一致性 | 2 | 内部自洽 1 + 与上游对齐 1（无上游时与上游对齐自动满分） |
| **总评** | **10** | - |

> 评分锚点：9-10 可交付 / 7-8 需修重要问题（< 8 不建议收敛）/ 5-6 核心未解 / 3-4 基础正确性破坏 / 1-2 不可用

## 7. 防膨胀机制（v3 新增）

### 7.1 零增量检验
- executor 在变更说明 §3.1「新增项（行为定义项）」每条必须附零增量论证：「删除该条款后是否损失行为定义？」+ 理由
- arbiter 复核：删后仍能完成验收标准 → 论证不成立 → 拒绝纳入本轮
- 减法轮内的新增（含已论证）→ 直接拒绝
- 任务指令/整合意见要求的新增必须以等价删除置换（按 §7.4 阶梯判定等价性），无法置换的升级人工

### 7.2 同根因复发熔断
- 同一根因标签问题跨 quality_round 第 2 次出现 → 整合意见**禁止新增守卫/例外/兜底条款**
- 必须改用**模型级修复方向**：消维度、改派生、并机制、压缩语义等从源头消除
- 熔断判定与修复方向选择写入 arbiter-record.md（依据引用 issue-log.md 对应条目）
- 与「重复问题反思」边界：后者针对同一位置连续未解决（治标/治本反思），本条针对同根因在新位置再现（禁止再加补丁）

### 7.3 减法轮触发
满足任一条件时宣布下一 quality_round 为减法轮（**条件④优先于停滞检测升级路径**）：
1. 连续 2 轮新增行为定义项数 > 删除/合并项数（被动清理不计）
2. 同根因复发熔断已触发
3. 外层 attempt 阻断（attempt==3/6 阻断分析触发时）
4. 评分停滞 + 交付物持续增长（停滞 + 条件①同时满足）

**减法轮约束**：
- 修订仅限删除、合并、简化
- 不得新增任何条款
- 删除/合并项逐条附零增量论证
- 减法轮计入迭代轮次
- 宣布必须写入下一轮整合意见首部
- 结束后未收敛按常规规则继续，至迭代上限或停滞升级人工

### 7.4 优先级阶梯（冲突裁决）

| 优先级 | 类别 | 裁决规则 |
|--------|------|---------|
| ① | 正确性与安全 | 一票优先，不权衡，必须满足 |
| ② | 需求与验收合规 | 以需求规格为准；若不可行产出澄清项 |
| ③ | 技术可行性与质量 | 满足①②前提下，成本更低/风险更小优先 |
| ④ | 体验与优化项 | 记录为建议，不阻断收敛 |

同优先级、各有代价的冲突 → 标记为权衡项：
- **可自动采纳**（留痕）：仅涉及单视角内部、≤ 2 处独立段落、不改变对外结构
- **升级人工**：不满足自动采纳条件

## 8. 问题台账（v3 新增）

### 8.1 文件位置
`run_dir/inner/T{n}/issue-log.md` —— 跨 quality_round 持久（同一 attempt 内）

### 8.2 字段定义

| 字段 | 说明 |
|------|------|
| ID | T{n}-R{attempt}Q{q_round}-{seq} |
| 级别 | 阻断 / 重要 / 建议 |
| 根因标签 | 复用或新建（粒度：可用同一类修复方向消除的一组问题） |
| 发现轮次 | q_round 编号 |
| 闭合状态 | 已闭合（位置+证据）/ 未闭合 / 留待后续轮次 / 评分承载+轮次引用（仅重要级） |

### 8.3 持久化规则
- 跨 quality_round 追加更新（arbiter 每轮更新一次）
- **重要级允许「评分承载」状态收敛**（评估者评分已反映该问题且维持收敛建议时）
- 「留待后续轮次」仅限建议级；阻断级与未评分的「重要」级不得以此放行
- 外层 attempt 切换时台账**不重置**（跨 attempt 累积）；仅在 Rework（goal-check 触发 completed->pending）时转只读归档为 `issue-log-restart.md`，新建台账

## 9. 失败处理状态机（两阶段重试 + 阻断性分析）

```
执行 -> 内层质量收敛未通过
  ├─ q_round < N -> 内层下一轮，quality_round++
  └─ q_round == N -> attempt 失败
        ├─ attempt < 3 -> 下次 attempt（quality_round 重置为 0）
        ├─ attempt == 3 -> run_failure_analysis(round=1)
        │     ├─ 阻断性 -> blocked -> ✋升级询问
        │     └─ 非阻断性 -> 第 2 阶段重试
        │           ├─ attempt < 6 -> 重试
        │           └─ attempt == 6 -> run_failure_analysis(round=2) -> blocked
```

- **attempt 语义**：前增（初始 0，每轮执行前 +=1），总计 6 轮上限
- **dispatch_error**：非 self 失败 -> force_self=True 降级（不增 attempt）；self 也失败 -> blocked + 升级
- **阻断性分析 8 维度**（failure-analysis 模板）：缺失依赖/技术不可行/需求矛盾/反复失败同因/验证合理性/路由错误 + **v3 新增**：根因标签熔断 / 内层耗尽
- round=2（attempt==6）无论阻断与否 -> blocked 升级

## 10. 内化规则集

### 10.1 意图分析器
关键词信号 + 三问验证（见 §4 ①）

### 10.2 任务拆分器
Markdown checklist + 单任务一动作 + 禁止占位符 + 含完成标准（见 §4 ③）

### 10.3 检查 Gate（五步 + 防膨胀审视，v3）
- 5 步：IDENTIFY → RUN → READ → VERIFY → 声明-证据对照
- **v3 防膨胀审视**：零增量审计 + 简洁性审视 + 根因标签标注（见 review-check.md）
- 不信任 executor 自述，独立验证 VCS diff + 验证命令

### 10.4 失败处理器
两阶段重试 + 阻断性分析（见 §9）

### 10.5 目标达成评估
三维（Completeness/Correctness/Consistency）+ 跨任务集成点 + v3 质量评分摘要（见 goal-check.md）

### 10.6 问题严重级别（v3）

| 级别 | 含义 | 对收敛的影响 |
|------|------|-------------|
| 阻断 | 正确性/安全/基础一致性破坏，交付物不可用 | 必须清零才可收敛 |
| 重要 | 影响质量但不阻断基本可用 | 通过拉低评分间接阻止收敛（每 2-3 个约 -1 分） |
| 建议 | 优化项、非关键体验 | 不阻止收敛 |

## 11. 数据格式

### 11.1 goal.md
（同 v2）

### 11.2 tasks.md（v3 扩展字段）
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
  - 外层 attempt: 0/6
  - 内层 quality_round: 0/3
  - 最近评分: -
  - 内层路径: inner/T1/
  - 失败原因：{重试时}
  - 失败历史：{reports 路径列表}
```

### 11.3 内层产物目录（v3 新增）
```
run_dir/inner/
├── T1/
│   ├── issue-log.md                            # 跨 quality_round 持久
│   ├── r1-q1-deliverable.md                    # 5 段交付物
│   ├── r1-q1-summary.md                        # 摘要独立文件
│   ├── r1-q1-review.md                         # reviewer 评估报告
│   ├── r1-q1-arbiter.md                        # arbiter 仲裁记录
│   ├── r1-q2-deliverable.md
│   ├── r1-q2-summary.md
│   ├── r1-q2-review.md
│   ├── r1-q2-arbiter.md
│   └── r1-summary.md                           # attempt 结束时内层总结
├── T2/
│   └── ...
```

### 11.4 外层报告（保留 v2 路径）
路径：`run_dir/reports/T{n}-r{m}.md`（外层 attempt 末产出，含内层总结引用）

### 11.5 仲裁记录（v3 新增）
路径：`run_dir/inner/T{n}/r{attempt}-q{q_round}-arbiter.md`
模板：`templates/arbiter-record.md`

### 11.6 TodoWrite 同步
tasks.md 为 source of truth，TodoWrite 为运行态镜像，每次状态变更同步

## 12. 恢复机制（不依赖 attention-maintenance）

### 12.1 恢复检测
入口 detect_unfinished_runs 扫描 `run_dir/`：
- 有 tasks.md 但无 final-report.md 且无 partial-report.md -> 未完成
- 有 partial-report.md -> 已中止
- 有 final-report.md -> 已完成，不恢复

### 12.2 状态重建
reconstruct_state：从 tasks.md 读取任务状态 + 内层 attempt/quality_round + goal.md 读取 goal_check_round；in_progress/reviewing 重置为 pending（attempt 是局部变量，恢复后从 0 重新计数，失败历史保留）；内层 issue-log.md 保留完整

### 12.3 恢复流程
resume_run：展示进度 -> AskUserQuestion 确认 -> 从 next_pending 恢复执行（内层从 quality_round=0 重新开始）

## 13. 自包含边界声明

| 项 | 是否依赖 | 说明 |
|----|---------|------|
| 意图分析/任务拆分/检查Gate/失败处理/目标达成/质量收敛/防膨胀 | ❌ 不依赖 | 全部内置 |
| 技术域 subagent（Neo/Echo 等） | ⚠️ 可选 | classify_domain 探测，不存在降级 self |
| 工作记忆（attention-maintenance） | ⚠️ 可选 | 使用方维护，common_loop 不依赖 |
| 评分/收敛/防膨胀/仲裁机制 | ❌ 不依赖 | v3 全部内化；与 autoflow work-mode 同源但已内化，不运行时引用 |
| AskUserQuestion / Agent / Write / TodoWrite | ✅ 依赖 | 宿主环境原生工具 |

**分享边界**：分享 `skills/common_loop/` + `common_executor.agent.md` + `result_reviewer.agent.md` 即可独立运行。

## 14. 可选增强（非依赖）

- **工作记忆维护**（如 attention-maintenance）：使用方全局规则要求时启用，提供跨对话 Decision/State 维护
- **技术域 subagent**：使用方具备 Neo/Echo/Ops 等时，executor 路由增强；否则全自执行
- **多视角评估**（v3 可注入）：任务分发方通过模式参数注入视角集合，默认单视角

## 15. 版本演进

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1 | 2026-07-28 初版 | 7 阶段编排 + 6 轮重试 |
| v2 | 2026-07-28 完全自包含 | 零外部 skill 依赖；跨会话恢复 |
| **v3** | **2026-08-11 吸收 workmode** | **双层循环（外层 6×内层 3）+ 评分收敛 + 防膨胀（零增量/熔断/减法轮/优先级阶梯）+ 问题台账 + arbiter 角色 + 5 段交付物** |
