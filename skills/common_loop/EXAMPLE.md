# common_loop 使用示例

本文件通过一个端到端示例，演示 common_loop 的完整流程：**分析意图 -> 确认目标 -> 拆分任务 -> 确认任务列表 -> 循环执行 -> 目标达成检查 -> 汇报**。

示例聚焦"一次执行 + 检查通过"的主干路径，展示 executor 与 reviewer 的交互。失败重试与升级询问场景见文末「进阶场景」章节（由后续任务补充）。

> 阅读前置：先浏览 `SKILL.md` 了解 7 阶段全貌与角色定义，再对照本示例看各阶段如何落地。

---

## 示例场景

**用户原始诉求**：「给项目加个健康检查脚本，能看磁盘和内存占用就行。」

这是一个典型的"新功能开发"诉求，需拆分为多个子任务并逐个验证，适合 common_loop。

---

## ① 分析意图（内置）

主循环识别关键词信号并做三问验证。

**关键词信号识别**：
- "加个"/"脚本" -> 新功能开发信号
- 无"修复"/"报错"/"变更"关键词 -> 不命中修复/变更
- 任务类型判定：**新功能**

**三问验证**：

| 问题 | 回答 |
|------|------|
| 要解决什么问题？ | 快速查看项目运行环境的磁盘与内存占用 |
| 完成后如何验证？ | 执行脚本能输出磁盘使用率与内存占用，退出码符合规范 |
| 边界在哪？ | 仅检查磁盘与内存，不包含 CPU/网络/进程检查；不引入第三方依赖 |

**输出**：
- 任务类型：新功能
- 目标声明 draft：为项目添加健康检查脚本，输出磁盘与内存占用，退出码反映健康状态

---

## ② 确认目标 ✋

主循环通过 `AskUserQuestion` 与用户确认目标（含验收标准）。

**AskUserQuestion 交互**：

```
问题：请确认以下目标是否准确？
选项：
  A. 确认（推荐）- 目标：为项目添加 scripts/health-check.sh，
     输出磁盘使用率与内存占用；退出码 0=健康，1=告警
  B. 调整边界 - 仅磁盘或仅内存
  C. 补充验收标准
  D. 自定义
```

用户选择 **A. 确认**。

**生成 run_dir 与 goal.md**：

- run_dir：`docs/loop-runs/2026-07-28-健康检查脚本/`
- 写入 `goal.md`：

```markdown
# 目标声明

## 目标
为项目添加 scripts/health-check.sh，输出磁盘使用率与内存占用，退出码反映健康状态

## 验收标准
- [ ] scripts/health-check.sh 存在且可执行
- [ ] 执行后输出磁盘使用率与内存占用（百分比）
- [ ] 退出码规范：0=健康，1=告警（磁盘>85% 或内存>90%）
- [ ] 不引入第三方依赖（仅用 shell 内置命令）

## 边界（不做什么）
- 不检查 CPU / 网络 / 进程
- 不做持续监控，仅单次快照

## 元数据
- 任务类型：新功能
- 创建日期：2026-07-28
- run_dir：docs/loop-runs/2026-07-28-健康检查脚本/
- goal_check_round: 0
```

> **约束**：未确认不得进入拆分。goal.md 是后续目标达成检查的权威依据。

---

## ③ 拆分任务（内置）

主循环将目标拆分为 Markdown checklist，每任务含 ID/描述/预期产出/完成标准/依赖。单任务一个动作单元，禁止 TBD/占位符，完成标准必须可验证。

**拆分结果**：

- T1 创建脚本骨架与退出码规范（无依赖）
- T2 实现磁盘使用率检查（依赖 T1）
- T3 实现内存占用检查（依赖 T1）

> T2、T3 依赖 T1 但相互独立；当前版本串行执行，后续增强可并行。

**写入 tasks.md**（source of truth）：

```markdown
# 任务清单：为项目添加健康检查脚本

## 目标声明
为项目添加 scripts/health-check.sh，输出磁盘使用率与内存占用，退出码反映健康状态

## 任务列表
- [ ] T1 创建脚本骨架与退出码规范
  - 预期产出：scripts/health-check.sh 文件，含 shebang、参数解析骨架、退出码常量定义
  - 完成标准：文件存在且 `bash scripts/health-check.sh` 退出码为 0；`test -x scripts/health-check.sh` 通过
  - 依赖：[]
  - 状态：pending
- [ ] T2 实现磁盘使用率检查
  - 预期产出：scripts/health-check.sh 中新增 disk_usage 函数，调用 df 输出磁盘使用率
  - 完成标准：`bash scripts/health-check.sh` 输出含 "Disk: NN%"；磁盘>85% 时退出码为 1
  - 依赖：[T1]
  - 状态：pending
- [ ] T3 实现内存占用检查
  - 预期产出：scripts/health-check.sh 中新增 mem_usage 函数，调用 free 输出内存占用
  - 完成标准：`bash scripts/health-check.sh` 输出含 "Memory: NN%"；内存>90% 时退出码为 1
  - 依赖：[T1]
  - 状态：pending
```

**同步 TodoWrite**（运行态镜像）：

```
[ ] T1 创建脚本骨架与退出码规范
[ ] T2 实现磁盘使用率检查
[ ] T3 实现内存占用检查
```

---

## ④ 确认任务列表 ✋

主循环通过 `AskUserQuestion` 确认任务列表。

```
问题：任务列表如下，是否确认？
  T1 创建脚本骨架与退出码规范
  T2 实现磁盘使用率检查（依赖 T1）
  T3 实现内存占用检查（依赖 T1）
选项：
  A. 确认（推荐）- 按 T1->T2->T3 串行执行
  B. 调整拆分 - 增删或合并任务
  C. 调整依赖
  D. 自定义
```

用户选择 **A. 确认**。

> **约束**：未确认不得进入执行。

---

## ⑤ 循环执行（全自动，串行）

对每个 pending 任务（`next_pending`：依赖全 completed 的首个 pending）依次执行：状态 in_progress -> classify_domain -> dispatch_executor -> 状态 reviewing -> dispatch_reviewer -> 完成判定。

下面以 **T1** 完整演示一次"执行 + 检查通过"的交互。T2、T3 流程相同，仅任务内容不同。

### T1 执行调度

**next_pending 判定**：T1 依赖为空，T1 为 next_pending。

**状态变更**：T1 pending -> in_progress（同步 TodoWrite）

**classify_domain 判定**：
- 任务类型：shell 脚本（通用任务）
- 技术域 agent 探测：无专用 shell agent -> 降级 **self**
- target = self

**dispatch_executor**（self 模式）：主循环渲染 `task-dispatch.md` 模板，下发 prompt 给 common_executor。

> 模板渲染说明：self 模式下 `{task_content}` 由 executor 自行读取 tasks.md 填充；adapter 模式下由 `pack_task_entry` 内联注入。本例为 self 模式。

**渲染后的下发 prompt**（基于 `templates/task-dispatch.md`）：

```markdown
# 任务下发：T1

## 任务来源
> self 模式：读取 `docs/loop-runs/2026-07-28-健康检查脚本/tasks.md` 中 **T1** 任务条目（含描述/预期产出/完成标准/依赖）

## 执行要求
- 完成标准：以 tasks.md 中 T1 的「完成标准」为准
  - 文件存在且 `bash scripts/health-check.sh` 退出码为 0
  - `test -x scripts/health-check.sh` 通过
- 失败原因（重试时）：（首次执行，无）
- 失败历史（重试时）：（首次执行，无）
- 约束：组合>扩展>修改，最小改动，非局部改动提示影响范围

## 输出契约
- 产出物（代码/文档/配置）
- 执行摘要（做了什么、改了哪些文件、如何验证）
- ⚠️ 不得自述"完成"--完成由 result_reviewer 判定
```

### T1 executor 执行产出

common_executor 读取 tasks.md 中 T1 条目，直接执行（self 模式），产出脚本并返回执行摘要。

**产出物**：`scripts/health-check.sh`

```bash
#!/usr/bin/env bash
# 健康检查脚本：输出磁盘使用率与内存占用
# 退出码：0=健康，1=告警（磁盘>85% 或内存>90%）

set -euo pipefail

# 退出码常量
HEALTHY=0
WARNING=1

# 告警阈值
DISK_THRESHOLD=85
MEM_THRESHOLD=90

# 参数解析骨架
usage() {
  echo "Usage: $0 [--disk-threshold N] [--mem-threshold N]"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --disk-threshold) DISK_THRESHOLD="$2"; shift 2 ;;
    --mem-threshold)  MEM_THRESHOLD="$2";  shift 2 ;;
    -h|--help)        usage ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

# 检查函数占位（T2/T3 实现）
main() {
  exit "$HEALTHY"
}

main "$@"
```

**执行摘要**（executor 返回，不自述完成）：

```
产出物：scripts/health-check.sh（新建）
做了什么：
  - 创建脚本骨架，含 shebang、set -euo pipefail
  - 定义退出码常量（HEALTHY=0 / WARNING=1）与告警阈值
  - 实现参数解析骨架（--disk-threshold / --mem-threshold / -h）
  - 预留 main 入口，T2/T3 将在此填充检查逻辑
建议如何验证：
  - test -x scripts/health-check.sh
  - bash scripts/health-check.sh; echo "exit=$?"
  - bash scripts/health-check.sh -h
```

### T1 reviewer 检查

**状态变更**：T1 in_progress -> reviewing（同步 TodoWrite）

**dispatch_reviewer**（任务级检查）：主循环渲染 `review-check.md` 模板，下发 prompt 给 result_reviewer。`{附}` 为 executor 执行摘要。

**渲染后的下发 prompt**（基于 `templates/review-check.md`）：

```markdown
# 结果检查：T1 第 1 轮

## 检查对象
- 任务预期：读取 tasks.md 中 T1（预期产出 + 完成标准）
- executor 产出摘要：{上述执行摘要}
- VCS diff：执行 `git diff` 获取
- 验证命令：IDENTIFY 阶段确定

## 检查 Gate（五步，必须执行）
1. IDENTIFY：哪些命令能证明完成标准满足？
2. RUN：完整执行验证命令（不跳过、不缩短）
3. READ：查看完整输出 + 退出码 + 失败数
4. VERIFY：输出是否支撑完成声明？（对照完成标准逐条）
5. 声明：仅在本轮验证证据支撑时才声明通过

## 危险词清单
should / probably / seems / Done / Great / works / fixed
应该 / 大概 / 可能 / 完成 / 搞定 / 没问题 / 差不多
（出现在 executor 自述时视为未提供证据，不得据此声明通过）

## 输出（写入 reports/T1-r1.md）
- 结论：✅ 通过 / ❌ 未通过
- 证据：验证命令输出摘要 + diff 摘要
- 原因（未通过时）：具体问题，逐条
- 建议（未通过时）：修正方向，可执行
```

**reviewer 独立执行五步 Gate**（不信任 executor 自述）：

```
1. IDENTIFY：完成标准为"文件存在且可执行 + bash 执行退出码 0"
   验证命令：
   - test -x scripts/health-check.sh && echo "PASS" || echo "FAIL"
   - bash scripts/health-check.sh; echo "exit=$?"
   - git diff --stat scripts/health-check.sh

2. RUN：完整执行上述命令
   $ test -x scripts/health-check.sh && echo "PASS" || echo "FAIL"
   PASS
   $ bash scripts/health-check.sh; echo "exit=$?"
   exit=0
   $ git diff --stat
   scripts/health-check.sh | 35 ++++++++++++++++++++++++++++++++++

3. READ：输出完整，退出码 0，无失败信息
   - test -x: PASS
   - bash 执行: exit=0
   - git diff: 新增 35 行

4. VERIFY：逐条对照完成标准
   - "文件存在且 bash 执行退出码为 0" -> 退出码 0，✅
   - "test -x 通过" -> PASS，✅

5. 声明：证据支撑，声明通过
```

**reviewer 写入 `reports/T1-r1.md`**：

```markdown
# 检查报告：T1 第 1 轮

## 结论
✅ 通过

## 证据
- `test -x scripts/health-check.sh` -> PASS（文件存在且可执行）
- `bash scripts/health-check.sh; echo "exit=$?"` -> exit=0（退出码符合 HEALTHY）
- `git diff --stat` -> 新增 scripts/health-check.sh 35 行

## 完成标准对照
| 完成标准 | 验证结果 |
|---------|---------|
| 文件存在且 bash 执行退出码为 0 | ✅ exit=0 |
| test -x 通过 | ✅ PASS |

## 说明
executor 自述中未出现危险词（should/probably/完成 等），产出与 diff 一致。
T2/T3 将在 main 中填充检查逻辑，当前骨架退出码 0 符合预期。
```

### T1 完成判定（五步 Gate）

主循环读取 `reports/T1-r1.md`，执行完成判定：
- 结论：✅ 通过
- 证据充分：命令输出 + diff 支撑
- 无危险词问题

**判定**：通过 -> T1 状态 reviewing -> **completed**（同步 TodoWrite）

```
[x] T1 创建脚本骨架与退出码规范
[ ] T2 实现磁盘使用率检查
[ ] T3 实现内存占用检查
```

### T2 / T3 执行（流程同 T1）

- **T2**：next_pending（依赖 T1 已 completed）-> in_progress -> self 执行 -> reviewing -> reviewer 检查（reports/T2-r1.md）-> completed
- **T3**：next_pending（依赖 T1 已 completed）-> in_progress -> self 执行 -> reviewing -> reviewer 检查（reports/T3-r1.md）-> completed

> T2/T3 的 executor 在 main 中分别填充 `disk_usage` 与 `mem_usage` 函数，reviewer 验证输出含 "Disk: NN%" / "Memory: NN%" 及阈值告警逻辑。流程与 T1 完全一致，此处不重复展开。

全部任务 completed 后，进入阶段 ⑥。

---

## ⑥ 目标达成检查

全部任务 completed 后，主循环执行 `dispatch_reviewer_goal_check`（目标级检查），使用 `goal-check.md` 模板。

**渲染后的下发 prompt**（基于 `templates/goal-check.md`，无占位符）：

```markdown
# 目标达成检查

## 检查对象
- 目标声明：读取 goal.md（目标 + 验收标准 + 边界）
- 任务清单：读取 tasks.md（应全部 completed）

## 三维评估
### 1. Completeness（完整性）
- 每条验收标准是否都有对应任务且已完成？
- 是否有遗漏的工作项？

### 2. Correctness（正确性，聚焦跨任务集成点）
- 接口契约一致：跨任务 API 签名/类型/字段是否匹配？
- 端到端流程：从输入到输出，数据流是否贯穿所有任务无断裂？
- 数据流衔接：上游任务产出与下游任务输入是否对接？

### 3. Consistency（一致性）
- 任务间是否一致（接口/数据/约定无冲突）？

## Rework 判断
若已 completed 任务存在集成问题：回滚 completed->pending，重新进入执行循环。

## 输出
- 结论：✅ 达成 / ❌ 未达成
- gap_type（未达成时）：task_omission / goal_unreachable
- 证据：端到端验证结果 + 集成点检查结果
- 缺口（未达成时）：需补充的任务列表
- Rework 任务（若有）：需回滚的 completed 任务及原因
```

**reviewer 三维评估**：

```
1. Completeness
   - "脚本存在且可执行" -> T1 已完成，✅
   - "输出磁盘使用率与内存占用" -> T2 输出 Disk、T3 输出 Memory，✅
   - "退出码规范" -> T1 定义常量，T2/T3 接入阈值判定，✅
   - "不引入第三方依赖" -> 仅用 df/free/test，✅
   - 无遗漏工作项

2. Correctness（跨任务集成点）
   - 接口契约：T2/T3 均在 T1 的 main 中调用，函数签名一致，✅
   - 端到端：bash scripts/health-check.sh -> main -> disk_usage + mem_usage -> 输出 + 退出码，✅
   - 数据流：T1 的阈值常量被 T2/T3 引用，衔接正确，✅

3. Consistency
   - 命名风格统一（disk_usage / mem_usage / HEALTHY / WARNING），✅
   - 退出码约定一致（0/1），✅

Rework 判断：无集成问题，无需回滚
```

**目标达成结论**：✅ 达成

> 若未达成：首次（goal_check_round=1）按 gap_type 自动回退（task_omission -> 补充任务回 ④；goal_unreachable -> 回 ②）；二次及以上升级询问。详见 `SKILL.md` §6 与文末进阶场景。

---

## ⑦ 汇报 ✋

主循环写入 `final-report.md`（完成标志，供恢复检测识别为已完成），并通过 `AskUserQuestion` 汇报。

**写入 final-report.md**：

```markdown
# 最终汇报：健康检查脚本

## 目标达成情况
✅ 达成 - scripts/health-check.sh 已完成，全部验收标准满足

## 关键变更
- 新增 scripts/health-check.sh（磁盘 + 内存检查，退出码 0/1）
- 无第三方依赖，仅用 df/free/test

## 验收标准核对
- [x] scripts/health-check.sh 存在且可执行
- [x] 执行后输出磁盘使用率与内存占用
- [x] 退出码规范：0=健康，1=告警
- [x] 不引入第三方依赖

## 遗留问题
无
```

**AskUserQuestion 汇报**：

```
问题：目标已达成，如何处理？
选项：
  A. 确认完成（推荐）- 结束本次 loop
  B. 补充任务 - 回 ② 重新确认目标
  C. 开新 loop - 启动新的 common_loop 实例
  D. 自定义
```

用户选择 **A. 确认完成** -> loop 结束（TERMINATED）。

---

## 流程总览图

```
用户诉求
   │
   ▼
①分析意图（关键词信号 + 三问验证）
   │
   ▼
②确认目标 ✋ ──── AskUserQuestion ──── 写 goal.md
   │
   ▼
③拆分任务 ──── 写 tasks.md + TodoWrite
   │
   ▼
④确认任务列表 ✋ ──── AskUserQuestion
   │
   ▼
⑤循环执行（串行，每个 pending 任务）
   │  ┌─ T1: in_progress -> dispatch_executor(self) -> reviewing -> dispatch_reviewer -> Gate 通过 -> completed
   │  ├─ T2: in_progress -> dispatch_executor(self) -> reviewing -> dispatch_reviewer -> Gate 通过 -> completed
   │  └─ T3: in_progress -> dispatch_executor(self) -> reviewing -> dispatch_reviewer -> Gate 通过 -> completed
   │
   ▼
⑥目标达成检查 ──── dispatch_reviewer_goal_check（三维评估）── ✅ 达成
   │
   ▼
⑦汇报 ✋ ──── 写 final-report.md + AskUserQuestion ──── 确认完成 -> TERMINATED
```

---

## 关键交互要点

### executor 与 reviewer 的职责分离

| 维度 | common_executor | result_reviewer |
|------|----------------|-----------------|
| 职责 | 产出可被验证的成果 | 独立验证成果是否满足完成标准 |
| 自述 | 不自述"完成"，只输出执行摘要 | 不信任 executor 自述，只看证据 |
| 证据 | 建议验证方式 | 自行运行命令 + git diff |
| 状态 | 不修改 tasks.md 状态 | 不修改 tasks.md 状态，只写 reports/ |

### 模板使用对照

| 阶段 | 模板 | 填充者 | 产出 |
|------|------|--------|------|
| ⑤ dispatch_executor | `task-dispatch.md` | 主循环填 `{n}`/`{日期}`/`{目标}`/`{失败原因}`/`{失败历史}` | 下发给 executor 的 prompt |
| ⑤ dispatch_reviewer | `review-check.md` | 主循环填 `{n}`/`{m}`/`{附}` | 下发给 reviewer 的 prompt |
| ⑥ goal_check | `goal-check.md` | 无占位符，reviewer 读 goal.md + tasks.md | 下发给 reviewer 的 prompt |
| 失败处理 | `failure-analysis.md` | 主循环填 `{n}`/`{round}`/`{历史}` | 下发给 failure analyzer 的 prompt |

### 状态机流转（本示例）

```
T1: pending -> in_progress -> reviewing -> completed
T2: pending -> in_progress -> reviewing -> completed
T3: pending -> in_progress -> reviewing -> completed
```

本示例为 happy path，全部一次通过。当 reviewer 判定未通过时，进入失败处理状态机（两阶段重试 + 阻断性分析），详见下一章。

---

## 进阶场景（失败重试与升级询问）

承接主干示例。当 reviewer 判定**未通过**时，进入失败处理状态机：两阶段重试（attempt 1-3 / 4-6）+ 阻断性分析（6 维度）+ 升级询问（4 选项）。本节以 **T2（实现磁盘使用率检查）** 反复失败为例，演示完整流程。

> 参考：`SKILL.md` §6 失败处理状态机、§5 升级响应矩阵、`templates/failure-analysis.md`。

**attempt 语义**：前增（初始 0，每轮执行前 +=1），每轮 = 一次 dispatch_executor + 一次 dispatch_reviewer，总计 6 轮上限。attempt==3 与 attempt==6 时触发阻断性分析（不额外执行）。

> 更正：attempt==3 / 6 时**仍执行一轮 dispatch_executor + dispatch_reviewer**（生成 reports/T{n}-r{3或6}.md），若未通过再触发分析。即 6 轮 = 6 次执行 + 2 次分析（在 r3、r6 失败后）。

**T2 完成标准回顾**：
- `bash scripts/health-check.sh` 输出含 "Disk: NN%"
- 磁盘 >85% 时退出码为 1

### 第 1 阶段：attempt 1→3

#### attempt=1：首次未通过

executor 填充 disk_usage 函数后，reviewer 五步 Gate 检查未通过。

**reports/T2-r1.md**（节选）：

```markdown
## 结论
❌ 未通过

## 原因
1. 输出格式不符：实际 "Disk usage: 45%"，要求 "Disk: 45%"
2. 缺失阈值判定：未实现磁盘 >85% 时退出码 1

## 建议
- 输出改为 "Disk: ${percent}%"
- main 中比较 DISK_THRESHOLD 设置退出码
```

attempt=1 < 3 -> **重试**。主循环渲染 `task-dispatch.md`，回传失败原因与历史。

**重试下发 prompt**（基于 `templates/task-dispatch.md`，节选与首次执行的差异）：

```markdown
## 执行要求
- 完成标准：以 tasks.md 中 T2 的「完成标准」为准
- 失败原因（重试时）：reports/T2-r1.md 指出输出格式不符 + 缺失阈值逻辑
- 失败历史（重试时）：reports/T2-r1.md
- 约束：组合>扩展>修改，最小改动，非局部改动提示影响范围
```

#### attempt=2：重试未通过

executor 修正格式与阈值，reviewer 检查未通过。

**reports/T2-r2.md**（节选）：

```markdown
## 原因
macOS 下 df 输出格式与 Linux 不同，percent 解析为空字符串
- `bash scripts/health-check.sh`（macOS）-> "Disk: %"，退出码 1

## 建议
使用 `df -P` 或按平台分支解析
```

attempt=2 < 3 -> **重试**，attempt++。

#### attempt=3：触发阻断性分析（round=1）

executor 修正跨平台解析，reviewer 检查仍未通过。

**reports/T2-r3.md**（节选）：

```markdown
## 原因
percent 含 "%" 后缀，`[[ "45%" > 85 ]]` 退化为字符串比较
- 磁盘=90% 时退出码仍为 0（应告警）

## 建议
剥离后缀：percent="${percent%\%}"
```

attempt==3 -> 不再重试，主循环调用 `run_failure_analysis(round=1)`，渲染 `failure-analysis.md` 模板下发 failure analyzer。

**阻断性分析输出**（基于 `templates/failure-analysis.md`）：

```markdown
# 阻断性分析：T2（第 1 轮）

## 分析对象
- 触发条件：第 3 轮检查未通过
- reviewer 报告：读取 reports/T2-r3.md
- 已尝试方案：
  - reports/T2-r1.md：输出格式不符 + 缺失阈值逻辑
  - reports/T2-r2.md：macOS df 解析失败
  - reports/T2-r3.md：percent 后缀致字符串比较

## 分析维度（逐条判断）
1. 缺失依赖：🟢 df 为系统内置，无外部依赖缺失
2. 技术不可行：🟢 跨平台 df 解析可实现
3. 需求矛盾：🟢 完成标准自洽
4. 反复失败同因：🟢 3 轮原因不同（格式 -> 解析 -> 后缀），逐步逼近
5. 验证合理性：🟢 命令可证明输出与退出码
6. 路由错误：🟢 shell 任务 self 模式正确

## 判定（round=1）
- 阻断性 / 无法实现：上述任一为 🔴 且无法绕过 -> blocked，升级询问
- 非阻断性：全部为 🟢 或可修正 -> 第 2 阶段重试
本例：全部 🟢 -> 非阻断性 -> 第 2 阶段重试

## 输出
- 结论：🟢 非阻断性
- 理由：6 维度均非阻断，失败原因逐轮收敛
- 建议：进入第 2 阶段，关注 shell 类型与比较语义
```

主循环读取结论：**非阻断性** -> 进入第 2 阶段重试（不 blocked，不升级）。

### 第 2 阶段：attempt 4→6

#### attempt=4：未通过

**reports/T2-r4.md**（节选）：

```markdown
## 原因
set -euo pipefail 下，未加引号的 `[[ 90 > 85 ]]` 触发异常被 set -e 吞掉
- 磁盘=90% 时告警分支静默失败，退出码仍为 0

## 建议
使用算术比较 `(( percent > DISK_THRESHOLD ))`
```

attempt=4 < 6 -> **重试**，attempt++。

#### attempt=5：未通过

**reports/T2-r5.md**（节选）：

```markdown
## 原因
边界条件：磁盘=85.5% 时 percent 取整为 85，未告警（应告警）
- 取整方式为截断，需改为四舍五入

## 建议
percent 取整改为四舍五入，或阈值语义改为 >= 85
```

attempt=5 < 6 -> **重试**，attempt++。

#### attempt=6：触发阻断性分析（round=2）-> blocked

**reports/T2-r6.md**（节选）：

```markdown
## 原因
取整改为四舍五入后，不同平台 df 的 Used 列格式差异导致 awk 取列错误
- macOS：`df -P` 第 5 列为 "45%"
- Linux（CI）：`df -P` 第 5 列为 "45"（无百分号），awk 取列偏移

## 建议
统一用 `df -P | awk 'NR==2{gsub(/%/,"",$5); print $5}'` 显式去后缀
```

attempt==6（已达上限）-> 主循环调用 `run_failure_analysis(round=2)`。**round=2 无论阻断与否 -> blocked**，分析用于告知升级理由。

**阻断性分析输出**（节选）：

```markdown
# 阻断性分析：T2（第 2 轮）

## 分析对象
- 触发条件：第 6 轮检查未通过（已达上限）
- reviewer 报告：读取 reports/T2-r6.md
- 已尝试方案：
  - reports/T2-r1.md：输出格式不符 + 缺失阈值逻辑
  - reports/T2-r2.md：macOS df 解析失败
  - reports/T2-r3.md：percent 后缀致字符串比较
  - reports/T2-r4.md：set -euo pipefail 静默失败
  - reports/T2-r5.md：边界取整问题
  - reports/T2-r6.md：awk 取列平台差异

## 分析维度
1. 缺失依赖：🟢
2. 技术不可行：🟢（跨平台解析技术可行）
3. 需求矛盾：🟢
4. 反复失败同因：🔴 6 轮失败均围绕"df 解析 + 阈值比较"的 shell 健壮性问题，
   虽具体原因不同但根因（shell 跨平台健壮性）未收敛
5. 验证合理性：🟢
6. 路由错误：🟢

## 判定（round=2）
已达上限（attempt==6）-> blocked，升级询问（不再重试）

## 输出
- 结论：🔴 阻断性（已达上限 + 反复失败同因）
- 理由：6 轮未收敛，shell 跨平台健壮性问题反复出现
- 建议：升级询问，考虑调整任务（拆分跨平台解析与阈值逻辑）或人工介入
```

主循环：T2 状态 reviewing -> **blocked**（同步 TodoWrite，attempt 保持）。

```
[x] T1 创建脚本骨架与退出码规范
[B] T2 实现磁盘使用率检查（blocked）
[ ] T3 实现内存占用检查（依赖 T1）
```

### 升级询问（4 选项响应矩阵）

blocked 后，主循环调用 `ask_user_escalate`，通过 `AskUserQuestion` 呈现 4 选项。

**AskUserQuestion 交互**：

```
问题：T2 已 blocked（6 轮未通过，反复失败同因），如何处理？
选项：
  A. 跳过 - T2 标 skipped，下游依赖 T2 的任务级联跳过，继续 loop
  B. 调整任务（推荐）- T2 回 pending，attempt 归零，回 ④ 重新确认任务列表
  C. 中止 - T2 标 aborted，全部未完成任务标 aborted，生成 partial-report.md
  D. 人工介入 - T2 保持 blocked，下游级联 blocked，暂停 loop
```

**响应矩阵**（对照 `SKILL.md` §5）：

| 选项 | task.status | attempt | 下游处置 | loop 动作 |
|------|------------|---------|---------|----------|
| A. 跳过 | skipped | 归零（局部变量） | cascade_skip 联动跳过 | 继续 loop |
| B. 调整任务 | pending | 归零 | cascade_unblock 恢复下游 | 回 ④ 确认 |
| C. 中止 | aborted | - | 全部未完成 -> aborted | abort_cleanup -> TERMINATED |
| D. 人工介入 | blocked（保持） | 保持 | cascade_blocked 级联 | TERMINATED（暂停） |

#### 演示路径：用户选择 B. 调整任务

主循环执行响应矩阵 B 分支：

1. T2 状态 blocked -> **pending**（attempt 归零，失败历史保留）
2. cascade_unblock：恢复下游被级联的任务（本例 T3 依赖 T1 而非 T2，无变化）
3. 回到 **④ 确认任务列表**，主循环通过 `AskUserQuestion` 与用户重新确认

```
问题：T2 调整方案，是否确认？
选项：
  A. 确认拆分（推荐）- T2 拆为 T2a（跨平台 df 解析）+ T2b（阈值比较逻辑）
  B. 原任务重试 - T2 保持原样，attempt 归零重新执行
  C. 修改完成标准 - 放宽/收紧 T2 验收
  D. 自定义
```

用户选择 **A. 确认拆分** -> tasks.md 更新（T2 拆为 T2a + T2b，失败历史保留）-> 重新进入 ⑤ 循环执行。

> 调整后 T2 的失败历史（reports/T2-r1.md ~ r6.md）保留在 tasks.md 中，executor 重试时可参考，避免重蹈覆辙。

#### 其他路径简述

- **A. 跳过**：T2 -> skipped，cascade_skip 跳过依赖 T2 的任务（本例 T3 依赖 T1 而非 T2，故 T3 不受影响，继续执行）。loop 进入 ⑥ 目标达成检查时，会因 T2 未完成而触发 task_omission 回退或升级。
- **C. 中止**：abort_cleanup 将 T2、T3 标 aborted，生成 `partial-report.md`（保留 tasks.md 为恢复锚点，用户可后续 resume_run 恢复）。
- **D. 人工介入**：T2 保持 blocked，cascade_blocked 将下游标 blocked，loop TERMINATED（暂停）。用户人工修复后可 resume_run 恢复。

### 失败处理状态机总览

```
T2 reviewer 未通过
   │
   ▼
attempt=1 ❌ ── 重试（回传失败原因+历史）
   │
   ▼
attempt=2 ❌ ── 重试
   │
   ▼
attempt=3 ❌ ── run_failure_analysis(round=1)
   │
   ├─ 阻断性 ──> blocked ──> ✋升级询问
   └─ 非阻断性（本例）──> 第 2 阶段
         │
         ▼
   attempt=4 ❌ ── 重试
         │
         ▼
   attempt=5 ❌ ── 重试
         │
         ▼
   attempt=6 ❌ ── run_failure_analysis(round=2) ──> blocked（无论阻断与否）
                                                      │
                                                      ▼
                                              ✋升级询问（4 选项）
                                              ├─ 跳过 ──> skipped + cascade_skip
                                              ├─ 调整任务 ──> pending + 回 ④
                                              ├─ 中止 ──> aborted + abort_cleanup
                                              └─ 人工介入 ──> blocked + cascade_blocked
```

### 目标未达成回退（补充）

除任务级失败外，⑥ 目标达成检查未通过时也有回退机制（详见 `SKILL.md` §4 ⑥）：

- **首次未达成（goal_check_round=1）**：按 gap_type 自动回退
  - task_omission（任务遗漏）-> 补充任务回 ④ 确认
  - goal_unreachable（目标不可达）-> 回 ② 重新确认目标
- **二次未达成（goal_check_round>=2）**：升级询问（4 选项：重新确认目标 / 重新拆分任务 / 中止 / 人工介入），选择重做时重置 goal_check_round=0 + rework_round=0（持久化到 goal.md）。
