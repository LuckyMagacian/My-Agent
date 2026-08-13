# 执行阶段 r8 轮评估标准（eval-standards-r8）——R7 重要级问题修复核验轮

> 实例：instance-skill-five-point-optim ｜ 轮次：执行阶段第 8 轮（r8）
> 基线快照：round-8/baseline-r8.txt（`git status --porcelain` + `git diff HEAD --stat`）
> 用户约定：**允许并行派发只读 subagent 任务**；**subagent 一律不得写工作空间文件，写操作移交 Main Agent**（永久规则，落盘由 Main Agent 依据 subagent 最终消息完成）；**评估范围仅核心组件**（SKILL.md + references/ 全量，不纳入 changelog/、.autoflow/ 留痕与台账的追溯链核验）

## 1. 本轮背景与触发

- r7 复核轮经五视角评估收敛（governance 9.0 / convergence 8.6 / executability 8.9 / robustness 8.5 / maintainability 9.75；按 §6.2 重要级评分承载覆盖宣布收敛），新发现 4 类重要级问题（R7-1~R7-4）及建议级约 15 条（R7-5~R7-19）；
- R7-1~R7-4 已于 2026-08-13 由 Main Agent 完成修正——全部为**机械章节号修正与索引补齐**，不改机制语义：
  - R7-1：《设计阶段》§4.6→§4.7 锚点悬空（5 处跨 3 文件）
  - R7-2：需求阶段章节号悬空引用（§3.2→§5.2 等，6 处跨 2 文件）
  - R7-3：work-mode §9.1「7 类参数」→「八类参数」（2 处跨 2 文件）
  - R7-4：SKILL.md §9 补「测试基础就绪核验问询」与「figma 就绪校验升级」两行介入点索引
- 用户指令（2026-08-13）：**重新执行一轮评估**——对 R7 修复后的核心组件执行 r8 评估，验证修复闭合状态，检查是否引入新问题；
- **本轮任务**：在 R7 修复后的现行核心组件上执行一轮完整五视角评估，验证①R7-1~R7-4 修复闭合，②核心组件间一致性保持，③是否因修复引入新问题。**本轮结束即止，不自动触发下一轮**。

## 2. 基线说明

- R7 修复增量在现行工作目录（未提交）；`git diff HEAD` 含 r1~r8 累积修改；
- **评估对象 = 核心组件现行文件全量内容**（共 11 文件）：

| # | 文件 | 现行版本（锚点） |
| --- | --- | --- |
| 1 | `SKILL.md` | v1.0.15（§9 已补两行） |
| 2 | `references/work-mode.md` | v1.9（§9.1 已改为「八类参数」） |
| 3 | `references/context-system.md` | v2.3.7（§5.2/§8.1/§8.4 章节号已修正） |
| 4 | `references/requirements-stage.md` | v0.8.10 |
| 5 | `references/design-stage.md` | v0.9.5 |
| 6 | `references/development-stage.md` | v1.3（§5.2/§7.2 锚点已修正） |
| 7 | `references/testing-stage.md` | v1.4 |
| 8 | `references/version-evolution.md` | v1.1 |
| 9 | `references/cross-reference-index.md` | 无版本号（末次校验 2026-08-13；索引 L17/L38 已同步） |
| 10 | `references/execution-checklist.md` | 无版本号（工具文件；§4 锚点已修正） |
| 11 | `references/convergence-checklist.md` | 无版本号（工具文件） |

- **明确排除**：`changelog/`、`.autoflow/`（optimization-log、issue-log、round-N/ 产物）、`.qoder/`——不得用于追溯链核验；
- **版本锚点**（SKILL.md §2 登记表 + 各组件头部 + cross-reference-index 末次校验三处互证）：work-mode v1.9 ｜ context-system v2.3.7 ｜ requirements-stage v0.8.10 ｜ design-stage v0.9.5 ｜ development-stage v1.3 ｜ testing-stage v1.4 ｜ version-evolution v1.1 ｜ SKILL.md v1.0.15。

## 3. 本轮专项核验要点（叠加于五视角通用标准）

1. **R7 修复复核**：
   - R7-1：context-system L196/L439、development-stage L135/L237、execution-checklist L41 是否已从 §4.6 修正为 §4.7；
   - R7-2：context-system L185/L195/L233（§3.2→§5.2）、L312（§3.5→§5.5）、L282/L309（§5.4→§7.4）是否已修正；cross-reference-index L38 索引是否已同步；
   - R7-3：work-mode L294 是否已从「7 类参数」改为「八类参数」；cross-reference-index L17 索引是否已同步；
   - R7-4：SKILL.md §9 是否已包含「测试基础就绪核验问询」和「figma 就绪校验升级」两行；
2. **历轮修复残留复核**：r1~r6 + r7 历轮修复在核心组件内的落地状态与残留——历史已闭合项（R-1~R-5、R2-1~R2-4、R3-1、R4-1、R5-1、R6-1、R7-1~R7-4）不出现回归；
3. **核心组件内部一致性**：各组件头部「对齐基准」行与组件实际现行版本一致；机制引用面与 work-mode v1.9 一致；跨组件引用锚点有效；
4. **新问题引入**：修复是否引入新的不一致、悬空引用或语义漂移。

## 4. 评估标准与输出要求

- 各视角维度分解、评分锚定沿用 round-1/eval-standards-r1.md §2/§3/§4，按本轮范围作下列裁剪：
  - governance：六项跨组件一致性核验裁剪为**四项在范围内**（①登记对齐、②基准行对齐、③布局与软链接、④机制引用面），与 r7 相同；
  - maintainability：M1 版本演进留痕限于核心组件内部自洽；M2 跨组件同步核验核心组件内六处，与 r7 相同；
  - convergence / executability / robustness：维度分解沿用 r1 标准，取材仅限核心组件；
- 五段结构输出（视角 ID 与轮次 / 总评分及维度分解 / 收敛建议及依据 / 逐条问题（级别+位置+原文摘录+期望标准+修改方向）/ 无问题维度标注「通过」）；
- 每条问题必须附**原文摘录**证据；评分 1–10（一位小数）；评分 ≥ 8 且无阻断级才可「建议收敛」；
- 历轮遗留建议级（S2-2~S2-8、S3-1~S3-4、R7-5~R7-19）在核心组件范围内的现状如实核查，不强制闭合。

## 5. subagent 派发协议（并行只读）

- **并行派发**：五视角（governance / convergence / executability / robustness / maintainability）一次性并行派发；
- 每个视角 subagent 在**最终消息**中返回：视角 ID / 总评分及维度分解 / 收敛建议 / 逐条问题（含原文摘录证据）/ 无问题维度标注；
- **subagent 禁止任何文件写入（永久规则）**；落盘由 Main Agent 依据最终消息完成；
- 若个别 subagent 派发中断，由 Main Agent 直接评估该视角落盘，格式不变，并在交付物中标注回退。