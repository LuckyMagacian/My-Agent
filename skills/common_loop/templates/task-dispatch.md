# 模板：task-dispatch

## 填充说明

| 占位符 | 填充者 | 填充源 | 时机 |
|--------|--------|--------|------|
| `{n}` | 主循环 | tasks.md 任务 ID | dispatch_executor 时 |
| `{日期}` | 主循环 | run_dir 路径 | dispatch_executor 时 |
| `{目标}` | 主循环 | goal.md 标题 | dispatch_executor 时 |
| `{失败原因}` | 主循环 | task.failure_reason | 重试时（attempt>1） |
| `{失败历史}` | 主循环 | task.failure_history（reports 路径列表） | 重试时（attempt>1） |
| `{task_content}` | executor（pack_task_entry） | tasks.md 中 T{n} 条目内容（描述/预期产出/完成标准/依赖） | adapter 模式转交技术域 agent 时 |

> **渲染说明**：主循环 `render` 函数替换上述占位符后，将下方模板正文发送给 executor（self 模式）或目标技术域 agent（adapter 模式）。self 模式下 `{task_content}` 行由 executor 自行读取 tasks.md 填充；adapter 模式下由 `pack_task_entry` 内联注入。

---

<!-- ============ 模板正文（render 后发送给 executor / 目标 agent） ============ -->

# 任务下发：T{n}

## 任务来源
> **模式说明**：
> - **self 模式**（executor 自执行）：executor 读取 `.ai/docs/loop-runs/{日期}-{目标}/tasks.md` 中 **T{n}** 任务条目
> - **adapter 模式**（转交技术域 agent）：executor 已用 `pack_task_entry` 将任务条目内容内联注入 `{task_content}`，被转交 agent 无需读取 tasks.md、无需了解 common_loop 格式

self 模式：读取 `.ai/docs/loop-runs/{日期}-{目标}/tasks.md` 中 **T{n}** 任务条目（含描述/预期产出/完成标准/依赖）
adapter 模式（内联内容）：{task_content}

## 执行要求
- 完成标准：以 tasks.md 中 T{n} 的「完成标准」为准
- 失败原因（重试时）：{失败原因}（逐条修正）
- 失败历史（重试时）：{失败历史}（历史 reports 路径，供参考避免重复尝试）
- 约束：组合>扩展>修改，最小改动，非局部改动提示影响范围

## 输出契约
- 产出物（代码/文档/配置）
- 执行摘要（做了什么、改了哪些文件、如何验证）
- ⚠️ 不得自述"完成"--完成由 result_reviewer 判定
