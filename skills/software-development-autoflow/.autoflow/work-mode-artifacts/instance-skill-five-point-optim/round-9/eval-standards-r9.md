# r9 评估标准（eval-standards-r9）—— R8 修复核验轮

> 实例：instance-skill-five-point-optim ｜ 轮次：r9（R8-1/R8-2 重要级问题修复核验轮）
> 基线快照：round-9/baseline-r9.txt ｜ 派发协议：五视角 CodeReview subagent 并行只读，落盘由 Main Agent 完成

## 1. 评估范围

核心组件 11 文件全量（SKILL.md + references/）：SKILL.md、work-mode、context-system、requirements-stage、design-stage、development-stage、testing-stage、version-evolution、cross-reference-index、execution-checklist、convergence-checklist。changelog/ 仅作留痕闭环核验（不评内容）；.autoflow/、.qoder/ 排除追溯核验。

## 2. 版本锚点（r9 现行）

SKILL.md **v1.0.16** / work-mode v1.9 / context-system v2.3.7 / requirements-stage v0.8.10 / design-stage v0.9.5 / development-stage v1.3 / testing-stage v1.4 / version-evolution v1.1。全链一致核验点：头部版本 8/8 ＝ §2 登记表 ＝ §12 关系表版本行 ＝ 索引末次校验版本集 ＝ 总账版本范围。

## 3. R8 修复闭合核验点（五视角逐项核验）

### 3.1 R8-1（重要级闭合核验）
- context-system L194「《需求阶段》§4 第 4 项引用制」、L219「§4 第 3 项」、L281「§4 第 2 项条目 ID 跨轮持久」——语义与 requirements-stage §4 第 4/3/2 项（L59/L58/L53）一致；
- 全库无《需求阶段》§6 残留（changelog/索引描述性提及不计）；
- cross-reference-index L38 context-system 行回验：§4（5）计数含 L124/L220 补登、§5.2（4）含目录树 L127、§6 条目移除、语义注记与原文一致、免责注已移除。

### 3.2 R8-2（重要级闭合核验）
- 索引 L6 末次校验行 = 2026-08-13，版本集含 SKILL.md v1.0.16，批次说明覆盖 R7+r8；
- 《测试阶段》组 SKILL.md 行含 §5.1.5（1）；《设计阶段》组 SKILL.md 行含 §4.1（1）、§5.1（3）——与 SKILL.md §9 两行新增（L191/L201）及 §10 L219 实况一致；
- version-evolution §4 总账：SKILL/work-mode/context-system/development-stage 行含 08-13 指针、交叉引用索引行含「末次校验行更新」、执行检查清单行含当日批次；SKILL 行版本范围 v1.0.16；
- changelog/2026-08-13.md 存在且 10 条目与变更实况对账一致。

### 3.3 SKILL.md 补办升号（v1.0.15→v1.0.16）核验
- §2.2「SKILL.md 例外每次变更均升号」合规性：R7-4 §9 补行（新增登记行）须升号，本次已补办；
- §2.4 七处引用侧同步完整性：① 对齐基准行（version-evolution L6）② §2 登记表（N/A——SKILL.md 不在自身登记表）③ §4 目录树（N/A 无版本）④ §12 关系表 SKILL.md 行（v1.0.16 + 注记）⑤ 索引末次校验版本集 ⑥ 索引分组行（N/A 无 SKILL.md 被引方组）⑦ changelog 当日条目；
- 无 v1.0.15 残余（§12 历史注记与 changelog 描述性提及不计）。

## 4. 历轮闭合项回归核验（零回归要求）

R-1~R-5、R2-1~R2-4、R3-1、R4-1、R5-1、R6-1、R7-1~R7-4、R8-1、R8-2、S2-1、S2-4 全部应保持闭合（R8-1/R8-2 为本次核验主对象；其余逐项抽查证据位）。

## 5. 遗留问题状态（不强制闭合）

- R8-3（索引 L48「§4.7（1）」应为（2））、R8-5（context-system L91 目录树注释「两份」应为三份）：未闭合；
- R8-4：部分闭合（L38 行已随 R8-1 回验修正；L37 行 §5.4 缺失、design-stage→《测试阶段》§3 未登记仍存）；
- R7-5~R7-19 及 S2-2/S2-3/S3-4 残余：未闭合，与台账一致无漂移。

## 6. 收敛判定口径（work-mode §6.1）

全部视角建议收敛 + 全部评分 ≥ 8 + 无阻断级问题 + 判定基于本轮报告 + 台账核验（重要级均须「已闭合」或「评分承载 + 轮次引用」）。§6.3 同根因复发熔断：引用锚点漂移/索引未同步标签已触发——本轮如再检出同类问题，修复方向必须为模型级（禁止守卫条款），且连续复发将触发减法轮/升级人工路径评估。

## 7. 输出要求（subagent 最终消息结构）

① 视角 ID 与轮次；② 总评分（1-10）+ 维度分解表；③ 收敛建议及依据；④ 逐条问题（级别、位置、原文摘录、期望标准、修改方向）；⑤ 通过项标注（逐项核验结论）。subagent 只读分析、不得写任何文件。
