# 执行阶段 r6 轮评估标准（eval-standards-r6）——减法轮

> 实例：instance-skill-five-point-optim ｜ 轮次：执行阶段第 6 轮（r6，减法轮）
> 基线快照：round-6/baseline-r6.txt（`git status --porcelain` + `git diff HEAD --stat`）
> 用户约定：subagent 严格只分析不写文件（历史 4 轮 40441 不可用，沿用 Main Agent 直评回退路径）；本轮结束即止（不自动触发下一轮）

## 1. 本轮背景与触发

- r5 轮评估未收敛（governance 9.4 / convergence 8.8 / executability 9.0 / robustness 8.9 / maintainability 8.9），仲裁回传重要级 J-7（08-10 批次台账延展漏登，同根因第四现）；用户指令「修复 J-7 + 根因分析（为何反复出现、是否过度设计）」；
- 根因分析（round-5/root-cause-analysis-r5.md）结论：**过度设计部分成立**——§4 总账逐条目登记粒度超出人工维护可靠边界（交叉引用索引行按日粗粒度指针 3 次延展 0 错误 vs 逐条目枚举行 4 次错误）；同根因第 4 现触发 work-mode §6 熔断（禁止加守卫，强制模型级修复或减法轮简化）；
- 用户决策：**发起减法轮（独立评估轮次）** + **追溯重写**（§4 总账历史 13 行统一重写为按日粒度指针）；
- 执行者已按减法方案完成一轮机制修订：version-evolution v1.0 → v1.1（Y 增）+ §2.3/§4 登记粒度规约修订 + §4 总账 13 行追溯重写 + §2.4 七处引用侧同步 + changelog 条目 16 留痕 + 台账 r6 登记；
- **本轮任务**：在减法方案实施后的文件上执行一轮完整五视角评估，验证①减法是否达成简化目标、②追溯链是否保持完整（changelog 明细未动、总账指针与明细一致）、③是否引入新问题。**本轮结束即止，不自动触发下一轮**。

## 2. 基线说明（重要）

- 五点优化批次原改动已提交（commit `3bb6c06`）；`git diff HEAD` 含历轮修复增量（r1~r6 累积）；r6 本轮增量集中在：references/version-evolution.md（机制修订 + 总账追溯重写）、SKILL.md（v1.0.15 引用侧同步）、references/context-system.md（§12 关系表）、references/cross-reference-index.md（末次校验行）、changelog/2026-08-12.md（条目 16 留痕）、issue-log.md（r6 登记）；
- **评估对象 = 工作区现行文件全量内容 + changelog/2026-08-12.md（含条目 1-16；纳入 governance/maintainability 追溯链核验范围）**；
- **减法轮特性**：本轮核心评估对象是 version-evolution §2.3/§4 修订后的登记规约与重写后的总账——五视角均须核验「简化目标达成度」与「追溯链无损」两项。

## 3. 已应用减法方案（供各视角核验）

| 项 | 内容 | 文件 |
| --- | --- | --- |
| ① 登记粒度规约 | §2.3 记录粒度修订：「指针按日登记（changelog/<日期>.md），当日批次为最小登记单位，不枚举条目号、不复述细节」；§4 引言同口径 + 建立事件/末次校验类事件保留事件标注 | version-evolution §2.3/§4 |
| ② 总账追溯重写 | §4 总账 13 行逐条目指针全部替换为「changelog/<日期>.md：当日批次」按日指针（建立事件行保留「建立事件」、交叉引用索引行保留「末次校验行更新」）；迁出前版本、仅元数据标注等条目级细节交还 changelog 明细 | version-evolution §4 |
| ③ 升版 | version-evolution v1.0 → v1.1（机制修订 Y 增）；本文行自登记随本升版批次（沿条目 12 先例） | version-evolution 头部/§4 |
| ④ 引用侧同步（§2.4） | SKILL.md v1.0.14 → v1.0.15（头部版本行 + 对齐基准 version-evolution v1.0→v1.1 + §2 登记表）；context-system §12 关系表 version-evolution 行 v1.0→v1.1；cross-reference-index 末次校验行版本集更新；changelog 条目 16 | SKILL.md / context-system / cross-reference-index / changelog |
| ⑤ 留痕 | changelog 新增 r6 触发段 + 条目 16（声明范围与依据）；issue-log r6 轮追加登记 | changelog/2026-08-12.md / issue-log.md |

## 4. 评估标准与输出要求（同 r1~r5，叠加减法轮专项）

- 各视角维度分解、评分锚定、取材边界沿用 round-1/eval-standards-r1.md §2/§3/§4，不作变更；
- 五段结构输出（视角 ID 与轮次 / 总评分及维度分解 / 收敛建议及依据 / 逐条问题（级别+位置+原文摘录+期望标准+修改方向）/ 无问题维度标注「通过」）；
- 末尾「减法方案核验」小节：本视角对 ①简化目标达成度（总账是否真正变简、决策点是否减少）②追溯链无损（总账↔changelog 对账是否一致、§2.4 七处同步是否落地、SKILL.md/context-system/cross-reference-index 版本列是否对齐）③新问题引入 的判定 + 理由；
- 每条问题必须附**原文摘录**证据；评分 1–10（一位小数）；评分 ≥ 8 且无阻断级才可「建议收敛」；
- 历轮遗留建议级（S2-2~S2-8、S3-1~S3-4）如实核查现状，不强制闭合；r5 重要级 R5-1（J-7）闭合状态复核。

## 5. subagent 输出格式（只分析不写文件）

- 每个视角 subagent 在**最终消息**中返回：视角 ID / 总评分及维度分解 / 收敛建议 / 逐条问题 / 减法方案核验小节；
- **禁止任何文件写入**；落盘由 Main Agent 依据最终消息完成；
- 若 subagent 派发中断（40441 等历史形态），由 Main Agent 直接评估落盘，格式不变。
