# 模板：goal-check

## 填充说明

| 占位符 | 填充者 | 填充源 | 时机 |
|--------|--------|--------|------|
| （无占位符） | reviewer | goal.md + tasks.md | dispatch_reviewer_goal_check 时 |

> **渲染说明**：本模板无占位符，reviewer 直接读取 goal.md（目标 + 验收标准 + 边界）与 tasks.md（全部任务状态），执行三维评估后将结果反馈主循环。

---

<!-- ============ 模板正文（render 后发送给 result_reviewer） ============ -->

# 目标达成检查

## 检查对象
- 目标声明：读取 goal.md（目标 + 验收标准 + 边界）
- 任务清单：读取 tasks.md（应全部 completed）

## 三维评估

### 1. Completeness（完整性）
- 目标声明的每一条验收标准是否都有对应任务且已完成？
- 是否有遗漏的工作项？

### 2. Correctness（正确性，聚焦跨任务集成点）
- 接口契约一致：跨任务 API 签名/类型/字段是否匹配？
- 端到端流程：从输入到输出，数据流是否贯穿所有任务无断裂？
- 数据流衔接：上游任务产出与下游任务输入是否对接？

### 3. Consistency（一致性）
- 任务间是否一致（接口/数据/约定无冲突）？
- 命名/风格/约定是否统一？

## Rework 判断
若三维评估发现已 completed 的任务存在集成问题：
- 将该任务 status 从 completed 回滚为 pending（状态机支持 completed->pending）
- 记录回滚原因，重新进入执行循环

## 输出
- 结论：✅ 达成 / ❌ 未达成
- gap_type（未达成时）：task_omission（任务遗漏）/ goal_unreachable（目标不可达）
- 证据：{端到端验证结果 + 集成点检查结果}
- 缺口（未达成时）：{需补充的任务列表，回 split_tasks}
- Rework 任务（若有）：{需回滚的 completed 任务及原因}
