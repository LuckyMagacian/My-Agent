# 执行阶段 r7 轮评估标准（eval-standards-r7）——r6 收敛后复核轮（仅核心组件）

> 实例：instance-skill-five-point-optim ｜ 轮次：执行阶段第 7 轮（r7）
> 基线快照：round-7/baseline-r7.txt（`git status --porcelain` + `git diff HEAD --stat`）
> 用户约定（2026-08-12 更新）：**允许并行派发只读 subagent 任务**（取消历史「并发性能问题」串行约定）；**subagent 一律不得写工作空间文件，写操作移交 Main Agent**（永久规则，落盘由 Main Agent 依据 subagent 最终消息完成）；本轮结束即止（不自动触发下一轮）；**评估范围仅核心组件**（SKILL.md + references/ 全量，不纳入 changelog/、.autoflow/ 留痕与台账的追溯链核验）

## 1. 本轮背景与触发

- r6 减法轮（version-evolution v1.0→v1.1：§2.3/§4 总账登记粒度简化为按日指针 + 13 行追溯重写 + §2.4 七处引用侧同步）经五视角评估**收敛**（governance 9.5 / convergence 9.0 / executability 9.1 / robustness 9.1 / maintainability 9.3），无重要级/阻断级问题回传；历轮遗留建议级 11 条（S2-2~S2-8、S3-1~S3-4）保持未闭合登记；
- 用户指令：**使用独立 subagent 评估当前工作空间中改动后的 autoflow skill**——发起 r7 复核轮，对 r1~r6 历轮累积修复 + 减法轮实施后的现行核心组件执行一轮完整五视角评估；
- 用户选定范围：**仅核心组件**（SKILL.md + references/ 全量），changelog/、.autoflow/（optimization-log、issue-log、轮次产物）、.qoder/ 不纳入追溯链核验范围；
- **本轮任务**：在现行核心组件文件上执行一轮完整五视角评估，验证①r6 减法轮后核心组件内部自洽（登记规约 ↔ 总账 ↔ 各组件头部/登记表/关系表/末次校验版本集），②历轮修复后核心组件间一致性（不跨 changelog），③是否引入新问题。**本轮结束即止，不自动触发下一轮**。

## 2. 基线说明（重要）

- 五点优化批次原改动已提交（commit `3bb6c06`）；`git diff HEAD` 含历轮修复增量（r1~r7 累积）；
- **评估对象 = 核心组件现行文件全量内容**（共 11 文件）：

| # | 文件 | 现行版本（锚点） |
| --- | --- | --- |
| 1 | `SKILL.md` | v1.0.15 |
| 2 | `references/work-mode.md` | v1.9 |
| 3 | `references/context-system.md` | v2.3.7 |
| 4 | `references/requirements-stage.md` | v0.8.10 |
| 5 | `references/design-stage.md` | v0.9.5 |
| 6 | `references/development-stage.md` | v1.3 |
| 7 | `references/testing-stage.md` | v1.4 |
| 8 | `references/version-evolution.md` | v1.1 |
| 9 | `references/cross-reference-index.md` | 无版本号（末次校验 2026-08-12） |
| 10 | `references/execution-checklist.md` | 无版本号（工具文件） |
| 11 | `references/convergence-checklist.md` | 无版本号（工具文件） |

- **明确排除**：`changelog/`、`.autoflow/`（optimization-log、issue-log、round-N/ 产物）、`.qoder/`——不得用于追溯链核验（changelog↔总账对账、优化日志留痕核验等均不执行）；总账行指向 changelog 的指针仅作核心组件内部格式/口径自洽性观察，不与其明细文件对账；
- **版本锚点**（SKILL.md §2 登记表 + 各组件头部 + cross-reference-index 末次校验三处互证，作为一致性核验基准）：work-mode v1.9 ｜ context-system v2.3.7 ｜ requirements-stage v0.8.10 ｜ design-stage v0.9.5 ｜ development-stage v1.3 ｜ testing-stage v1.4 ｜ version-evolution v1.1 ｜ SKILL.md v1.0.15。

## 3. 本轮专项核验要点（叠加于五视角通用标准）

1. **减法轮复核**：version-evolution §2.3/§4 按日指针登记规约在核心组件内部的自洽性——总账 13 行（对象 / 版本范围 / 明细指针三列）与各组件头部现行版本、SKILL.md §2 登记表、context-system §12 关系表、cross-reference-index 末次校验版本集是否对齐；总账行指针格式（changelog/<日期>.md：当日批次 / 建立事件 / 末次校验行更新）是否符合 §4 引言声明口径；
2. **历轮修复复核**：r1~r6 各重要级修复（R-1~R-5、R2-1~R2-4、R3-1、R4-1、R5-1、R6-1）在核心组件内的落地状态与残留检查——如 testing-stage §4.5 执行归属/测试代码实现归属/失败 TI 重跑时机/下游标记字段、§5.4 任务指令注入、design-stage §4.8 锚点、version-evolution 总账格式等；
3. **新问题引入**：减法轮追溯重写与历轮修复是否引入新的不一致、悬空引用或语义漂移。

## 4. 评估标准与输出要求

- 各视角维度分解、评分锚定沿用 round-1/eval-standards-r1.md §2/§3/§4，按本轮范围作如下裁剪：
  - governance：六项跨组件一致性核验裁剪为**四项在范围内**（①登记对齐——组件头部现行版本 ↔ §2 登记表 ↔ 末次校验版本集三角一致；②基准行对齐——各组件头部「对齐基准」行与组件实际现行版本一致；③布局与软链接——context-system §4 目录布局树与四份阶段细则 §3 归档约定跨组件一致；④机制引用面——细则机制引用面与 work-mode v1.9 一致）；原第 4 项（changelog↔总账对账）、第 5 项（优化日志留痕）**移出范围**；
  - maintainability：M1 版本演进留痕限于核心组件内部自洽（头部版本行 ↔ §2 登记表 ↔ §12 关系表 ↔ 末次校验版本集 ↔ 总账版本范围），不核验 changelog 明细；M2 跨组件同步核验核心组件内六处（头部对齐基准、登记表、目录布局树、关系表、末次校验、交叉引用分组），changelog 处移出；
  - convergence / executability / robustness：维度分解沿用 r1 标准（C1~C4 / E1~E4 / R1~R4），取材仅限核心组件；
- 五段结构输出（视角 ID 与轮次 / 总评分及维度分解 / 收敛建议及依据 / 逐条问题（级别+位置+原文摘录+期望标准+修改方向）/ 无问题维度标注「通过」）；
- 每条问题必须附**原文摘录**证据；评分 1–10（一位小数）；评分 ≥ 8 且无阻断级才可「建议收敛」；
- 历轮遗留建议级（S2-2~S2-8、S3-1~S3-4）在核心组件范围内的现状如实核查（涉及 testing-stage / design-stage 等），不强制闭合；r6 闭合项（R5-1、R6-1）闭合状态在核心组件范围内复核。

## 5. subagent 派发协议（并行只读）

- **并行派发**：五视角（governance / convergence / executability / robustness / maintainability）一次性并行派发（用户 2026-08-12 指令：允许并行派发只读任务；历史「并发性能问题」记录已移除）；
- 每个视角 subagent 在**最终消息**中返回：视角 ID / 总评分及维度分解 / 收敛建议 / 逐条问题（含原文摘录证据）/ 无问题维度标注；
- **subagent 禁止任何文件写入（永久规则）**；落盘由 Main Agent 依据最终消息完成；
- 若个别 subagent 派发中断，由 Main Agent 直接评估该视角落盘，格式不变，并在交付物中标注回退。
