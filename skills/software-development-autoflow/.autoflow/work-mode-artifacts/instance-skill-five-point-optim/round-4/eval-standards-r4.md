# 执行阶段 r4 轮评估标准修订说明（eval-standards-r4）

> 实例：instance-skill-five-point-optim ｜ 轮次：执行阶段第 4 轮（r4）
> 基线快照：round-4/baseline-r4.txt（`git status --porcelain` + `git diff HEAD -- <10 文件>` 全文 + changelog/2026-08-12.md 全量）
> 用户约定：**subagent 严格只分析不写文件**——评估结论在 subagent 最终消息中返回，全部落盘由 Main Agent 完成；允许并行评估；本轮结束即止（沿用「不自动触发下一轮」约束）

## 1. 本轮背景

- r3 轮评估未收敛（governance 9.1 / convergence 9.3 / executability 9.0 / robustness 8.8 / maintainability 8.5），仲裁回传 1 条重要级整合意见（J-5，见 arbitration-r3.md）：2026-08-12 修复批次机制修订未升版 + version-evolution §4 版本总账对当日 7 条目零指针；
- 执行者已按整合意见完成**一轮修复**（J-5 全部 4 点修改方向：testing-stage v1.3→v1.4 机制修订升版 + §2.4 七处引用侧同步 + §4 总账延展 2026-08-12 指针 + changelog 条目 8-12 留痕），台账 R3-1 已标注闭合；
- **本轮任务**：在修复后的 10 文件上重新执行一轮完整五视角评估，验证 J-5 修复闭合性并发现遗留/新引入问题。**本轮结束即止，不自动触发下一轮**。

## 2. 基线说明（重要）

- 五点优化批次改动（原 10 文件 +395/-55）已于评估前被提交（git commit `3bb6c06`「增加测试用例设计；集成测试」）；
- 因此 `git diff HEAD` 仅含**历轮修复增量**（10 文件 +58/-27）：testing-stage.md（v1.3→v1.4 升版 + J-1 机制条款）、SKILL.md（v1.0.13→v1.0.14 + 登记表/对齐基准）、requirements-stage.md / design-stage.md（对齐基准行）、context-system.md（§12 关系表两行）、version-evolution.md（对齐基准 + §4 总账延展）、cross-reference-index.md（末次校验行）、optimization-log（J-4 六处标注）、issue-log.md（r2/r3 台账）、changelog/2026-08-11.md（条目 24 笔误）；
- **评估对象 = 工作区现行 10 文件全量内容**（= 已提交批次 + 修复增量）+ **新增 changelog/2026-08-12.md**（修复留痕产物，含条目 8-12；纳入 governance/maintainability 追溯链核验范围，不计入 10 文件评分基数）。

## 3. 已应用修复清单（供各视角核验）

| ID | 修复内容 | 文件 |
| --- | --- | --- |
| J-5-1 | testing-stage 机制修订升版 v1.3 → v1.4（§2.1 修订走 Z 增；changelog 条目 4 口径「机制修订，不升版」→ 升版声明；条目 2 机制条款一并纳入升版批次） | testing-stage 头部、changelog/2026-08-12.md 条目 8 |
| J-5-2 | §2.4 七处引用侧同步：引用方组件头部「对齐基准」行（requirements/design）、SKILL.md §2 登记表 testing-stage 行 + 头部版本与对齐基准（SKILL.md 例外升号 v1.0.14）、context-system §12 关系表 testing-stage / SKILL.md 两行、交叉引用索引「末次校验」版本集（2026-08-12）、changelog 当日条目口径 | SKILL.md、requirements-stage、design-stage、context-system、cross-reference-index、changelog/2026-08-12.md 条目 9-11 |
| J-5-3 | §4 总账延展 2026-08-12 指针：SKILL 行条目 9；testing 行条目 1、2、4、8、10（其中 8 为升版）；context 行条目 10；requirements 行条目 1、10；design 行条目 3；development 行条目 1；方案优化文档行条目 7；本文行/changelog 目录行不累积自身指针（沿 2026-08-11 条目 24 先例） | version-evolution §4、changelog/2026-08-12.md 条目 12 |
| J-5-4 | 复核其余组件（work-mode/development-stage）批次中无实际变更，无需升号 | —（r3 已核验，r4 复核） |

## 4. 评估标准与输出要求（同 r1/r2/r3）

- 各视角维度分解、评分锚定、取材边界沿用 round-1/eval-standards-r1.md §2/§3/§4，不作变更；
- 五段结构输出（视角 ID 与轮次 / 总评分及维度分解 / 收敛建议及依据 / 逐条问题（级别+位置+原文摘录+期望标准+修改方向）/ 无问题维度标注「通过」）；
- 末尾「修复闭合核验」小节：J-5 与本视角相关条目闭合状态（已闭合 / 未闭合 / 部分闭合 + 理由）+ 修复引入新问题检查；
- 每条问题必须附**原文摘录**证据；评分 1–10（一位小数）；评分 ≥ 8 且无阻断级才可「建议收敛」；
- 历轮遗留建议级（S2-2~S2-8、S3-1~S3-4）如实核查现状，不强制闭合。

## 5. subagent 输出格式（只分析不写文件）

- 每个视角 subagent 在**最终消息**中返回：视角 ID / 总评分及维度分解 / 收敛建议 / 逐条问题（级别+位置+原文摘录+期望标准+修改方向）/ 修复闭合核验小节；
- **禁止任何文件写入**（含工作区与临时文件）；落盘由 Main Agent 依据最终消息完成；
- 若 subagent 派发中断（如会话中断取消），由 Main Agent 直接评估落盘，格式不变。
