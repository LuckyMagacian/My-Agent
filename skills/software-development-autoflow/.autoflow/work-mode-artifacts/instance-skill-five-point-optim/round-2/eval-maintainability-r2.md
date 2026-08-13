# maintainability（可维护性与演进能力）评估报告 —— r2 轮

## 1. 视角 ID 与轮次

**视角**：maintainability（可维护性与演进能力）｜**轮次**：执行阶段第 2 轮（r2）
**评估对象**：修复后的被评 10 文件（round-2/baseline-r2.txt，+395/-55）｜**核验重点**：I-1 修复及其版本号三角一致性、r1 遗留建议级问题 S-10~S-13 现状、修复引入的新问题

## 2. 总评分及维度分解

**总评分：7.8 / 10**

| 维度 | 分值 | 锚定依据（一句） |
| --- | --- | --- |
| M1 版本演进留痕 | 7.5 | 升版本表与 changelog 条目编号接续（19~40）完整可溯，但 §4 总账指针逐行错位（7 个组件/目录行中 5 行含错指针，且本批新增 2 处），I-1 修复亦未留痕 changelog。 |
| M2 跨组件同步 | 8.0 | I-1 修复后版本三角（头部对齐基准 ↔ SKILL.md §2 登记表 ↔ context-system §12 关系表 ↔ version-evolution §4 版本范围 ↔ cross-reference-index 末次校验）全量一致、无残留旧版本号；唯一缺口为交叉引用索引分组行未登记新增 §4.8/§3 引用（S-11）。 |
| M3 单一事实来源 | 7.8 | 新增机制（test-cases.md / integration-test-record.md / 测试基础就绪核验）均在唯一权威组件定义、无重复定义、无双重定义；但优化日志中已废止 final 机制的残留表述多处未清理（S-12）。 |
| M4 可追溯性 | 7.8 | 优化日志 §1.2 决策修订备注留痕完整、产物命名与编号空间惯例一致；但 I-1 修复无 changelog 留痕、testing-stage §4.5 一处锚点引用（§4.8 第 2 项 vs 第 3 项）不精确，追溯链存在两处缺口。 |

（四个维度均存在建议级问题，无「通过」维度。）

## 3. 收敛建议及依据

**不建议收敛。**

依据：① 总评分 7.8 < 收敛阈值 8；② 本视角核验的 6 条重要级问题（I-1~I-6）内容层全部闭合、无阻断级/重要级遗留，但建议级问题仍存 6 条——S-10 未闭合且本批新增 2 处错误指针（加重）、S-11/S-12/S-13 未闭合、I-1 修复未留痕 changelog（新问题）、testing-stage §4.5 锚点小误（新发现）；③ 遗留问题集中于演进留痕完整性与单一事实来源，属 maintainability 核心维度，建议纳入下一整改轮后重评。

## 4. 逐条问题

### 4.1 【建议级】S-10 未闭合且本批新增两处错误指针：version-evolution §4 总账指针与 changelog 条目逐行对不齐

**位置**：references/version-evolution.md §4 版本总账（L86-100）；changelog/2026-08-11.md L44/L79

**原文摘录**（version-evolution.md L90、L94、L88、L91、L93、L99）：
> | context-system | v1.0 → v2.3.7 | …；changelog/2026-08-11.md：【当日新增】条目 17、23、35 |
> | testing-stage | v0.1 → v1.3 | …；changelog/2026-08-11.md：【当日新增】条目 21、25、30 |
> | SKILL.md | v0.1 → v1.0.13 | …；changelog/2026-08-11.md：【当日新增】条目 2、16、22、26、34 |
> | requirements-stage | v0.2 → v0.8.10 | …；changelog/2026-08-11.md：【当日新增】条目 18、27 |
> | development-stage | v0.1 → v1.3 | …；changelog/2026-08-11.md：【当日新增】条目 20、29（仅头部对齐基准行同步，纯元数据不升版） |
> | 优化事务留痕目录（`.autoflow/optimization-log/`） | 无版本号 | changelog/2026-08-11.md：【当日新增】条目 22（建立事件） |

对账结果（changelog 实际条目：16=交叉引用索引、17=version-evolution、18=优化日志目录建立、19=design v0.9.3、20=testing v1.2、21=context v2.3.6、22=SKILL v1.0.11、23=交叉引用索引、25=优化日志附录更新、27=requirements v0.8.10、29=dev 仅元数据、30=testing v1.3、31/35/38=context、34=SKILL v1.0.13、36=design v0.9.5、37=优化日志笔误修订）：
- **本批新增错误指针**：context 行"23"（baseline diff `-条目 17 → +条目 17、23、35`）——23 为交叉引用索引条目，context 自身 v2.3.6 条目为 21；该错源自 changelog 条目 24 自身笔误（L44"context-system 行 v1.0→v2.3.6、增本 changelog 条目 23 指针"）并传入总账；testing 行"25"（`-条目 21 → +条目 21、25、30`）——25 为优化日志条目，testing v1.2 条目为 20；
- **既有错位（未修复）**：SKILL 行"16"（应为 15，SKILL v1.0.10 条目）、context 行"17"（version-evolution 自身条目，应为 10）、requirements 行"18"（优化日志建立条目，应为 11）、development 行"20"（testing 条目，应为 13）、testing 行"21"（context 条目，应为 14）；优化事务留痕目录行"条目 22（建立事件）"（建立事件为条目 18），且 changelog 条目 40（L79）声称"方案优化文档行增本 changelog 条目 37 指针"，总账内并无"方案优化文档"行。

**期望标准**：version-evolution §2.3"总账一行一组件/事件，指针直指明细节"、§5.2"发现不一致时……修订另一方对齐"——总账指针须与 changelog 逐行对账一致；design 行含"24"（version-evolution 自身条目）而其余行不含同类总账条目，行间口径亦不统一。

**修改方向**：逐行修正指针（SKILL: 2、15、22、26、34；context-system: 10、21、31、35、38；requirements-stage: 3、11、27；design-stage: 4、12、19、28、36；development-stage: 5、13、29；testing-stage: 6、14、20、30；优化事务留痕目录: 18 建立、25、37），并同步修正 changelog 条目 24 的"条目 23"笔误。

### 4.2 【建议级】I-1 修复未在 changelog 留痕，追溯链断裂（修复引入的新问题）

**位置**：changelog/2026-08-11.md L52/L54/L55 ↔ requirements-stage.md L6、development-stage.md L6、testing-stage.md L8

**原文摘录**（changelog 条目 27/29/30）：
> 27. …头部增「对齐基准」行——`work-mode.md` v1.9；`context-system.md` v2.3.6；`design-stage.md` v0.9.4；`development-stage.md` v1.3；`testing-stage.md` v1.3（v0.8.10 评估修复 T-2…）
> 29. …头部对齐基准行同步——`context-system.md` v2.3.5→v2.3.6、`design-stage.md` v0.9.2→v0.9.4、`requirements-stage.md` v0.8.9→v0.8.10…
> 30. …头部对齐基准行同步（requirements-stage v0.8.10、design-stage v0.9.4）

I-1 修复后的现行文件（requirements-stage.md L6）：
> > 对齐基准：`work-mode.md` v1.9；`context-system.md` v2.3.7；`design-stage.md` v0.9.5；`development-stage.md` v1.3；`testing-stage.md` v1.3

三处头部修正（context v2.3.6→v2.3.7、design v0.9.4→v0.9.5）无任何 changelog 条目（条目 40 之后无追加），changelog 记录的对齐基准状态与文件实际状态不一致。

**期望标准**：version-evolution §2.4 引用侧同步义务第 1/7 项——对齐基准变更须同批记 changelog 当日条目；changelog 为版本细节唯一权威，任何组件变更（含仅元数据修正）须留痕方可溯。

**修改方向**：追加 changelog 条目（显式标注「仅元数据」）：requirements-stage / development-stage / testing-stage 头部对齐基准行修正 context-system v2.3.6→v2.3.7、design-stage v0.9.4→v0.9.5（r1 评估修复 I-1）。

### 4.3 【建议级】S-11 未闭合：交叉引用索引未登记应用 5+6 新增的 §4.8 / §3 引用

**位置**：references/cross-reference-index.md 《设计阶段》分组（L43-49）、《测试阶段》分组（L58-62）

**原文摘录**（cross-reference-index.md L47-49）：
> | SKILL.md | §4.2（2）、§5（1）、§5.1（2）、§7.4（1） | figma MCP 服务配置… |
> | context-system.md | §4.7（1） | 任务 ID 续编由设计侧拆解完成（§5.2 重入续编口径） |
> | development-stage.md | §2（1）、§3（1）、§4.7（2） | … |

《设计阶段》被引方分组无 testing-stage/requirements-stage 行、无 §4.8 锚点；而现行组件存在多处《设计阶段》§4.8 引用（testing-stage.md L42"（《设计阶段》§4.8，**入口必备**…）"、L97/L176"《设计阶段》§4.8 第 6 段声明的依赖项"；requirements-stage.md §5.0"instance-testcases（《设计阶段》§4.8 测试用例设计）"）及 design-stage → 测试阶段引用（design-stage.md L166"本节产物是测试阶段 §3 输入②的入口必备项"）。且 changelog 条目 23（L43）声称本批"校验说明改写为「skill 七点优化批次应用 5+6 引用侧同步」"，与索引实际内容不符。

**期望标准**：索引自身结构规则（L4"组件章节结构变更或重编号时，逐行核对该组件作为被引方的全部行"）——新增出向引用须同批登记分组行。

**修改方向**：《设计阶段》分组增 testing-stage（§3、§4.5、§5.1.5）、requirements-stage（§5.0）行及 §4.8 锚点；《测试阶段》分组增 design-stage（§4.8）行。

### 4.4 【建议级】S-12 未闭合：优化日志 final 机制残留多处，与 §1.2 决策修订备注自相矛盾

**位置**：.autoflow/optimization-log/2026-08-11-skill-five-point-optimization.md L136/L141、L285、L328/L330、L348

**原文摘录**：
> L136：修改后：**无论是否注入外部稿，阶段必须产出 `requirements-final.md` 作为正式需求稿**
> L141：不论上述哪种路径，最终交付的"正式需求稿"均为阶段定稿产物 `requirements-final.md`…
> L285：| context-system.md | v2.3.4 | v2.3.5 | 目录布局树新增 docs/ + final/ + 阶段目录重命名（机制增量） |
> L328：| references/requirements-stage.md | §3 输出；§4 模板（增 final 产物）；§5.0 外部输入问询；… |
> L328：| references/development-stage.md | §3 输出增 final；§3 归档约定路径；§7.4 |
> L348：| final 文档结构差异大 | final 文档结构由"实例产物摘要 + 文档链接"聚合… |

而 L29 修订备注明言"移除 `final` 前后缀"、实际实现（requirements-stage §3 输出 `requirements.md`，无 final 后缀）亦与残留表述冲突。

**期望标准**：M3 单一事实来源——已废止机制（final 方案）的旧表述除历史留痕外应清理或显式标注"已推翻"（eval-standards-r1 §2.5 M3"已废止机制的旧引用被清理（历史留痕除外）"）。

**修改方向**：在 L136/L141/L285/L328/L330/L348 等处追加"已被 §2.2 应用 1 推翻"标注，或将 final 表述改写为 `requirements.md`。

### 4.5 【建议级】S-13 未闭合：context-system §13 锚点笔误（《设计阶段》§4.6 → 应为 §4.7）

**位置**：references/context-system.md L439

**原文摘录**：
> **步骤 2 · 设计阶段重入**（《设计阶段》§4.6 续编编号）

design-stage 现行结构：§4.6 为图表规范、§4.7 为任务拆解（"重入续编编号"段见 design-stage.md L134）；且 cross-reference-index.md L48 登记为"| context-system.md | §4.7（1） | 任务 ID 续编由设计侧拆解完成 |"——索引与正文自相矛盾。

**期望标准**：引用锚点与 design-stage 现行章节结构一致（§4.7）。

**修改方向**："《设计阶段》§4.6" → "《设计阶段》§4.7"。

### 4.6 【建议级】testing-stage §4.5「执行归属」锚点引用不精确（「核验方式」字段属 §4.8 第 3 项而非第 2 项，新发现）

**位置**：references/testing-stage.md L95

**原文摘录**：
> 执行命令与预期结果取自设计阶段 `test-cases.md` §4.8 第 2 项（接口集成测试用例）的「核验方式」字段

design-stage §4.8 第 2 项为"用例分类与编号空间"（TI-NNN 定义仅含前置条件/调用序列/预期结果/清理动作），「核验方式」字段（"测试框架名（沿用工程既有）+ 运行命令 + 预期结果模板"，design-stage.md L152）定义于第 3 项「用例条目结构」。所引"第 2 项"不承载「核验方式」字段，锚点悬空于字段定义处。

**期望标准**：引用锚点精确指向字段定义处（与 S-13 同类）；I-6 修复已统一"第 6 段依赖声明/输入②"口径，本节应一并精确化。

**修改方向**：改为"《设计阶段》§4.8 第 3 项「用例条目结构」的「核验方式」字段（针对 TI-NNN 用例）"。

## 5. 修复闭合核验

### 5.1 I-1~I-6 闭合状态（与本视角相关条目）

| 条目 | 状态 | 理由 |
| --- | --- | --- |
| **I-1**（三处头部对齐基准版本号修正） | **已闭合**（内容层） | requirements-stage L6 / development-stage L6 / testing-stage L8 均已修正为 `context-system.md` v2.3.7、`design-stage.md` v0.9.5；版本号三角全量一致：头部 ↔ SKILL.md §2 登记表（L34-40）↔ context-system §12 关系表（L410-414）↔ version-evolution 头部对齐基准（L6）与 §4 版本范围（SKILL v1.0.13 / context v2.3.7 / requirements v0.8.10 / design v0.9.5 / dev v1.3 / testing v1.3）↔ cross-reference-index 末次校验（L6），无残留旧版本号。附带说明：修复未在 changelog 留痕（见 4.2，建议级新问题），不推翻内容层闭合结论。 |
| **I-2**（§7.4 强制确认锚点枚举增 §5.1.5） | **已闭合** | testing-stage §4.3（L78）与 §7.4（L326）两处枚举均已含「§5.1.5 测试基础就绪核验裁定」，且 §5.1.5 升级规则（L187-188）"裁定结论登记验收核验记录人工裁定段并受 §7.4 强制确认约束"口径一致。 |
| **I-3**（悬空引用替换为直接升级人工路径） | **已闭合** | §4.5 第 3 段（L110-112）与 §5.1.5 升级规则（L188）均已替换为直接升级人工路径（裁定选项①补齐基础设施依赖后重新进入入口判定 / ②终止本阶段），无"退回上游工程环境就绪问询"悬空引用残留。 |
| **I-4**（§5 入口条件 + §5.1 核验清单增测试用例项） | **已闭合** | §5 入口条件（L158）已含"设计阶段测试用例设计产物已定稿（`stages/201-design/test-cases.md`，§3 输入②）"；§5.1 核验清单（L170）已增"设计阶段测试用例可引用"项，与 §3 输入②（L42）口径一致。 |
| **I-5**（§4.5 头段增「执行归属」定义） | **已闭合** | §4.5「执行归属」（L95）已定义：TI-NNN 由 Main Agent 在 §5.1.5 通过后、§5.4 条目实例启动前一次性执行，成功 TI 对下游条目实例标记「集成已核验」。 |
| **I-6**（§4.8 两处引用锚点修正） | **已闭合** | design-stage §4.8「依赖引用」已改为"引自第 6 段依赖声明的具体项"（L154）、强制路径已改为"测试阶段 §3 输入②"（L166），与 testing-stage 侧引用（L42/L97/L176「§4.8 第 6 段」）相互一致，无新悬空锚点。 |

### 5.2 修复引入新问题检查

1. **I-1 修复未在 changelog 留痕**（问题 4.2，建议级）——changelog 条目 27/29/30 记录的对齐基准（v2.3.6/v0.9.4）与现行文件（v2.3.7/v0.9.5）不一致，追溯链断裂；属修复过程引入的新缺口；
2. I-1 修复未改变任何组件自身版本号（requirements 仍 v0.8.10、dev/testing 仍 v1.3），总账版本范围与文件一致，无版本号回归；
3. 修复未触碰总账与 changelog，S-10 既有错位保持原状；另核验确认本批版本演进留痕自身新增 2 处错误指针（context 行"23"、testing 行"25"，见问题 4.1）——非修复引入，属留痕过程既有缺陷的加重；
4. I-2~I-6 修复未发现新引入的跨组件不一致（§5.1.5 锚点、产物登记、docs 软链行相互对齐）。
