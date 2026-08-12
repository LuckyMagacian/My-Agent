# 实例上下文 —— skill 五点优化改动五视角评估

> 实例名：instance-skill-five-point-optim
> 模式依据：`references/work-mode.md`《执行者-评估者-仲裁者工作模式》v1.9
> 实例化时间：2026-08-12（会话日期口径）

## 任务指令（四要素）

- **目标**：评估当前工作区**未提交改动后的 skill**（`SKILL.md` + `references/` 七份组件 + `changelog/2026-08-11.md` + `.autoflow/optimization-log/2026-08-11-skill-five-point-optimization.md`，共 10 个文件），从五视角（架构与组件治理 / 质量收敛机制 / 实操可执行性 / 健壮性与异常处理 / 可维护性与演进能力）产出评估报告：逐视角评分（1–10）、问题清单（阻断/重要/建议三级）、优先级改进建议；评估仅留痕，**不改动任何组件文件**。
- **约束**：① 仅访问当前工作空间文档（SKILL.md、references/、changelog/、.autoflow/optimization-log/），不参考任何外部文档、不参考任何既有 skill；② 评估对象为工作区当前未提交状态（以 git diff 与文件现状为据），评估意见必须附证据（位置 + 原文摘录），无证据的意见不计入整合结论；③ 评估者之间上下文隔离、独立成文，互不可见；④ 评估者不可见执行计划（§2.3 执行阶段隔离）；⑤ 交付决定权归属评估者（§2.2），仲裁者不得单方判定交付。
- **验收标准**：① 五视角各产出一份视角评估报告（评分 + 维度分解 + 收敛建议 + 问题清单，按 §10.6 结构）；② 整合评估报告覆盖全部视角，问题逐条分级并附证据引用；③ 各视角评分均 ≥ 8 且均建议收敛时宣告收敛（未达则按 §4/§6 继续迭代或升级人工）；④ 报告含优先级改进建议清单（供后续整改轮使用）；⑤ 全部留痕落盘至 `.autoflow/work-mode-artifacts/instance-skill-five-point-optim/`，不改动任何组件文件。
- **范围**：交付物 = 整合评估报告（round-N/executor-deliverable.md）+ 各视角评估报告 + 仲裁记录 + 问题台账；不包含对组件文件的任何修改；评估依据含 git diff（`git diff` 对比 HEAD）。

## 模式参数（实例级注入）

| 参数 | 值 |
| --- | --- |
| 评估视角集合 | 五视角：`governance`（架构与组件治理）、`convergence`（质量收敛机制）、`executability`（实操可执行性）、`robustness`（健壮性与异常处理）、`maintainability`（可维护性与演进能力） |
| 收敛阈值 | 8 / 10（默认） |
| 迭代上限 | 执行阶段 10 轮；规划阶段 3 轮（默认） |
| 归档位置 | `.autoflow/work-mode-artifacts/instance-skill-five-point-optim/`（外部注入） |
| 交付物模板 | §10.4 五段结构（本实例交付物为评估报告文档，正文即评估报告全文） |
| 规划阶段开关 | 启用 |

## §9.5 前置检查结论

- 目标清晰：通过（交付结果为可判定的评估报告 + 逐视角评分）；
- 约束无冲突：通过（只读评估不改文件，与版本治理约束无冲突）；
- 验收标准可评估：通过（五条均可判定：评分、分级、证据、落盘路径）。

## 角色降级声明（§9.4）

- **执行者**：Main Agent 兼任（运行环境未提供通用内容生产型独立 Subagent）——独立性偏差，逐轮仲裁记录标注；
- **规划者**：Main Agent 兼任——独立性偏差，规划阶段仲裁记录标注；
- **评估者**：独立 Subagent（CodeReview 子代理，逐视角独立派发、上下文隔离、互不可见）——不降级。

## 评估对象清单（10 文件，工作区未提交状态）

1. `SKILL.md`（v1.0.13）
2. `references/context-system.md`（v2.3.7）
3. `references/cross-reference-index.md`（无版本号，末次校验行）
4. `references/design-stage.md`（v0.9.5）
5. `references/development-stage.md`（v1.3）
6. `references/requirements-stage.md`（v0.8.10）
7. `references/testing-stage.md`（v1.3）
8. `references/version-evolution.md`（v1.0）
9. `changelog/2026-08-11.md`
10. `.autoflow/optimization-log/2026-08-11-skill-five-point-optimization.md`

## 实例终态（定稿后补记）

（待定稿后填写）
