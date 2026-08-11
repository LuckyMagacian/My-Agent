# 方案优化文档 —— software-development-autoflow skill 五点优化

> 文档属性：方案优化
> 日期：2026-08-11
> 优化对象：`.autoflow/skills/software-development-autoflow/`
> 范围：skill 组件（SKILL.md、references/ 七份组件、changelog/、.autoflow/ 归档结构）

---

## 1. 背景与现状

### 1.1 五点优化诉求（用户原话整理）

| 编号 | 诉求 | 当前差距 |
|---|---|---|
| 0 | 阶段目录编号 需求-101 设计-201 开发-301 测试-401 | 阶段目录名为 `requirements/design/development/testing`，无编号 |
| 1 | 需求级目录下增加 `docs/`，通过软链接连接各阶段最终交付的正式文档 | 当前 `docs/`（skill 根）声明为"设计草稿，交付即删"；需求级无 `docs/`；阶段定稿产物（executor-deliverable.md）无"正式文档"概念 |
| 2 | 无论何种场景（外部已注入正式需求稿 / 模板）均需生成正式需求稿 | §5.0 允许"提供已有需求稿时按分析澄清、非必要不新增"——可能未生成独立阶段定稿产物 |
| 3 | 无论如何都要分离架构设计与详细设计 | §4.4/§4.5 架构设计与详细设计在同一文档文件内两段；§5.1 允许外部模板合并组织 |
| 4 | 设计阶段优先 PlantUML 绘图，允许降级 mermaid | 当前 design-stage §5 流程图为 mermaid，未声明 PlantUML 优先级 |

### 1.2 关键决策（已与用户确认）

- **阶段目录编号形式**：重命名为 `101-requirements / 201-design / 301-development / 401-testing`
- **docs 软链接目标**：每阶段定稿时另生成 `final/<阶段名>-final.md`，`docs/` 软链接到该文件

---

## 2. 优化方案

### 2.1 应用 0：阶段目录重命名（编号绑定阶段名）

| 原路径 | 新路径 |
|---|---|
| `.autoflow/<req-id>/stages/requirements/` | `.autoflow/<req-id>/stages/101-requirements/` |
| `.autoflow/<req-id>/stages/design/` | `.autoflow/<req-id>/stages/201-design/` |
| `.autoflow/<req-id>/stages/development/` | `.autoflow/<req-id>/stages/301-development/` |
| `.autoflow/<req-id>/stages/testing/` | `.autoflow/<req-id>/stages/401-testing/` |

实例目录命名规则不变（`instance-<产物标识>` / `instance-<task-id>` / `instance-<req-id>`）。

**受影响组件**：

- `context-system.md` §4 目录布局树（路径与注释）
- `design-stage.md` §3 归档约定
- `development-stage.md` §3 归档约定
- `testing-stage.md` §3 归档约定
- `requirements-stage.md`（§5.2/§5.4 隐式引用 stage-context.json 路径，文件级引用不变，仅确认无阶段目录名硬编码）

### 2.2 应用 1：需求级 `docs/` 软链接目录（平权挂载各阶段交付物）

**设计原则（用户决策）**：

- **不创建 `final/` 子目录**——`final` 前后缀移除
- **不强制汇总为单一文件**——各阶段定稿产物按各阶段原模板原路径落盘
- **所有阶段交付物平权对待**——`docs/` 下软链接挂载各阶段所有正式交付物，不区分"哪个更重要"

**新增归档结构**（在每个需求目录 `.autoflow/<req-id>/` 下）：

```
.autoflow/<req-id>/
├── state.json
├── requirement-context.json
├── docs/                                    # 【新增】需求级快速访问入口（软链接集合）
│   ├── requirements.md                      → ../stages/101-requirements/requirements.md
│   ├── ui-design.md                         → ../stages/201-design/ui-design.md
│   ├── api-contract.md                      → ../stages/201-design/api-contract.md
│   ├── frontend-architecture.md             → ../stages/201-design/frontend-architecture.md
│   ├── frontend-detailed-design.md          → ../stages/201-design/frontend-detailed-design.md
│   ├── backend-architecture.md              → ../stages/201-design/backend-architecture.md
│   ├── backend-detailed-design.md           → ../stages/201-design/backend-detailed-design.md
│   ├── task-tsk-001.md                      → ../stages/301-development/tsk-001.md
│   ├── task-tsk-002.md                      → ../stages/301-development/tsk-002.md
│   ├── ...                                  （每任务一份软链接）
│   ├── testing-report.md                    → ../stages/401-testing/testing-report.md
│   └── defects.md                           → ../stages/401-testing/defects.md
└── stages/
    ├── 101-requirements/
    │   ├── requirements.md                  # 阶段定稿正式需求稿（按 §4 模板）
    │   ├── stage-context.json
    │   ├── clarification-log.md
    │   ├── current-state-analysis.md
    │   └── instance-1/
    ├── 201-design/
    │   ├── ui-design.md                     # 各实例定稿产物
    │   ├── api-contract.md
    │   ├── frontend-architecture.md
    │   ├── frontend-detailed-design.md
    │   ├── backend-architecture.md
    │   ├── backend-detailed-design.md
    │   └── instance-*/                       # work-mode 实例目录
    ├── 301-development/
    │   ├── tsk-001.md                       # 每任务一份交付物
    │   ├── tsk-002.md
    │   ├── ...                               （不强制 task-manifest.json 之外汇总）
    │   ├── task-manifest.json
    │   ├── build-gate-record.md
    │   └── instance-tsk-001/                  # work-mode 实例目录
    └── 401-testing/
        ├── testing-report.md                 # 测试报告
        ├── defects.md                        # 缺陷清单
        ├── acceptance-verification.md        # 验收核验记录
        └── instance-req-001/
```

**机制**：

- 阶段定稿时由 Main Agent 整理阶段正式交付物至 `stages/<阶段目录>/` 下，**文件名遵循各阶段细则原模板**（如 `requirements.md` / `ui-design.md` / `api-contract.md` / `frontend-architecture.md` / `tsk-NNN.md` / `testing-report.md`）
- `docs/` 下的软链接在阶段定稿登记时由 Main Agent 创建；阶段未启动时软链接不创建（不预创建空文件）
- 软链接命名规则：与阶段目录下交付物同名，扩展名同（`.md`）
- 软链接路径解析结果："零依赖"——单独打开 `docs/requirements.md` 即可阅读，与在阶段目录内打开等价

**与 skill 根 `docs/` 的关系**：

- skill 根目录 `docs/` 的**「设计草稿（评估期间临时存放，交付即删）」机制废止**——本批优化同步从所有组件文档中移除该机制引用（评估迭代期已过，组件全部交付，无新草稿产生；`context-system.md` §4 目录布局树中的 `docs/` 行从"设计草稿（交付即删）"改为"已废止"；`SKILL.md` §11 与早期设计草图相关的历史叙述段保留（属已发生事实的留痕，不属机制引用））
- 需求级 `<req-id>/docs/` 是**需求隔离域内**的快速访问入口，软链接指向各阶段交付物
- 两者职责完全分离：skill 根 `docs/` 不再承载任何运行时机制；需求级 `docs/` 不污染 skill 自身目录结构

**受影响组件**：

- `context-system.md` §4 目录布局树：增需求级 `docs/` 行（软链接集合）；移除或重定义 skill 根 `docs/` 草稿行；§11 一致性规则：增"软链接一致性"原则（链接目标存在性核验）
- `requirements-stage.md` §3 输出：定稿产物为 `requirements.md`（不再用 `final` 后缀）；§7.4：定稿时由 Main Agent 创建 docs 软链接
- `design-stage.md` §3 输出：定稿产物为各实例交付物（按 §4 拆分后命名）；§7.4：定稿时为各交付物创建 docs 软链接
- `development-stage.md` §3 输出：定稿产物为 `tsk-NNN.md` 等；§7.4：定稿时为各任务交付物创建 docs 软链接
- `testing-stage.md` §3 输出：定稿产物为 `testing-report.md` / `defects.md` / `acceptance-verification.md`；§7.4：定稿时为各产物创建 docs 软链接

### 2.3 应用 2：需求阶段必须产出正式需求稿

**修改 `requirements-stage.md` §5.0**：

- 当前：提供已有需求稿时"分析澄清、非必要不新增"——可能未生成独立阶段定稿
- 修改后：**无论是否注入外部稿，阶段必须产出 `requirements-final.md` 作为正式需求稿**
- 处置：
  - 未注入外部稿：按 §4 可交付需求稿模板（内置）生成
  - 注入外部稿：以原稿为输入，按 §4 模板**重新组织并转化**——条目编号化（REQ-NNN）、三分类判定、约束段提取、歧义点进澄清流程、原稿作为引用登记入澄清记录"输入引用"段
  - 注入外部模板：按模板组织正文结构，但强制要素（条目 ID、条目类型、优先级、验收标准、约束段、未决项来源标注）缺失时以独立小节补齐（与现有"模板优先 + 强制要素补齐"规则一致）
- 不论上述哪种路径，最终交付的"正式需求稿"均为阶段定稿产物 `requirements-final.md`，由 §5.3 初始稿 + §5.5 迭代细化 + §7.4 人工确认定稿

**受影响组件**：

- `requirements-stage.md` §3 输出、§5.0 外部输入问询、§5.3 生成初始需求稿

### 2.4 应用 3：设计阶段分离架构设计与详细设计

**修改 `design-stage.md` §4 + §5**：

- 当前 §4.4 前端方案 + §4.5 后端方案：架构设计 + 详细设计在同一文档内两段
- 修改后：**架构设计与详细设计为两份独立文档**

新的产物结构：

| 阶段实例 | 架构设计文档 | 详细设计文档 |
|---|---|---|
| `instance-frontend` | `frontend-architecture.md` | `frontend-detailed-design.md` |
| `instance-backend` | `backend-architecture.md` | `backend-detailed-design.md` |

§4 模板拆为：

- §4.4 架构设计模板（原 §4.4 第 1 段，技术选型、模块划分、API 映射、非功能指标承接）
- §4.5 详细设计模板（原 §4.4 第 2 段，逐模块结构、时序、异常、回归边界落实）

**外部模板注入时同样分离**：

- §5.1 外部输入问询段：补充"无论外部模板是否将架构与详细合并组织，阶段定稿必须拆分为两份独立文档；模板可决定每份文档的内部结构，但不能跨过文档级分离"
- 强制要素（与 API 契约接口 ID 级对齐、非功能指标引用、回归边界落实方案）在缺失的文档中以独立小节补齐

**定稿汇总**：

- `design-final.md` 聚合全部 4 份（UI + API + 前端架构 + 前端详细 + 后端架构 + 后端详细），按"架构在前、详细在后"组织
- 或更轻量：定稿产物为"设计包清单 + 各文档链接摘要"，不强制汇总为单一文件——**采纳此方案**，避免大文件无意义聚合

**受影响组件**：

- `design-stage.md` §3 输出、§4 模板拆分、§5 流程、§7.4 阶段级确认对象

### 2.5 应用 4：设计阶段优先 PlantUML 绘图

**修改 `design-stage.md` §5 执行流程图**：

- 当前：流程图为 mermaid
- 修改后：
  - 默认 PlantUML（依赖 `plantuml` skill），代码块标注 ` ```plantuml `
  - 降级路径：PlantUML 不可用（skill 未加载 / 调用失败）时降级为 mermaid，代码块标注 ` ```mermaid `
  - 选择口径写在图注：PlantUML 表达力更强（尤其时序图、组件图、部署图）；mermaid 用于流程图与甘特图场景
- §5 流程图以外的**设计产物内嵌图**（架构图、时序图、组件图、部署图）：同样执行"PlantUML 优先 / mermaid 降级"规则——写入 §4 模板说明

**不受影响**：

- `SKILL.md` §4 流水线全景图：当前为 mermaid，作为顶层调度图保留 mermaid（PlantUML 优先规则限定于设计阶段产物）
- `context-system.md` §3 总体结构图、`work-mode.md` §4 工作循环图：均保留 mermaid（组件图非设计产物）

**受影响组件**：

- `design-stage.md` §5 流程图代码块改写 + §4 模板说明增"图表规范"段

---

## 3. 版本号与引用侧同步

按 `version-evolution.md` §2.2 / §2.4：

### 3.1 版本号升版

| 组件 | 现版本 | 新版本 | 升版理由 |
|---|---|---|---|
| SKILL.md | v1.0.9 | v1.0.10 | 每次变更均升号（§2.2 例外），仅元数据 |
| context-system.md | v2.3.4 | v2.3.5 | 目录布局树新增 docs/ + final/ + 阶段目录重命名（机制增量） |
| requirements-stage.md | v0.8.8 | v0.8.9 | 强制生成正式需求稿 + 阶段目录重命名 |
| design-stage.md | v0.9.1 | v0.9.2 | 架构/详细分离 + PlantUML 优先级 + 阶段目录重命名 |
| development-stage.md | v1.2 | v1.3 | 阶段目录重命名 |
| testing-stage.md | v1.0 | v1.1 | 阶段目录重命名 |
| work-mode.md | v1.9 | 不变 | 无需修改 |
| version-evolution.md | v1.0 | 不变 | 仅元数据同步（§2.2 不升版） |
| cross-reference-index.md | 无 | 不变 | 仅末次校验更新 |

### 3.2 引用侧同步七处（§2.4）

1. 各组件头部「对齐基准」行（work-mode 保持 v1.9；其他同步新版本号）
2. SKILL.md §2 登记表对应行的版本列
3. context-system.md §4 目录布局树文件行 + 阶段目录行
4. context-system.md §12 关系表版本行
5. cross-reference-index.md 末次校验行（无条件更新）
6. cross-reference-index.md 中相关分组行（条件性：本次涉及别名引用与指针引用，需逐项核验）
7. changelog/2026-08-11.md 增当日新增条目段

### 3.3 changelog 条目

按 version-evolution.md §3.2 格式，记录五项批次的触发、采纳范围、版本号、指针。

---

## 4. 受影响文档与文件清单

| 文件 | 修改内容 |
|---|---|
| SKILL.md | §2 登记表版本列；§9 索引如有相关项；§10 启动参数（如有相关项） |
| references/context-system.md | §4 目录布局树；§11 一致性规则增软链接一致性；§12 关系表 |
| references/requirements-stage.md | §3 输出；§4 模板（增 final 产物）；§5.0 外部输入问询；§5.3 初始稿；§7.4 阶段级确认 |
| references/design-stage.md | §3 输出；§4 模板拆分（4.4 架构 / 4.5 详细）；§5 流程图改 PlantUML；§5.1 外部输入问询；§7.4 阶段级确认 |
| references/development-stage.md | §3 输出增 final；§3 归档约定路径；§7.4 |
| references/testing-stage.md | §3 输出增 final；§3 归档约定路径；§7.4 |
| references/cross-reference-index.md | 末次校验行 |
| references/version-evolution.md | §4 总账指针行 |
| changelog/2026-08-11.md | 当日新增条目段 |

---

## 5. 风险与回退

| 风险 | 缓解 |
|---|---|
| 阶段目录重命名后历史归档路径失效 | 历史归档（DONE 状态）保留原路径——只对**新启动需求**生效新路径；新启动需求 ID 含日期可辨识（YYYYMMDD-序号），断点恢复时按需求 ID 目录的实际路径处理，不依赖硬编码路径 |
| soft link 跨平台兼容性 | symlink 在 macOS/Linux 透明；Windows 需以「管理员模式」或「开发者模式」开启——本 skill 运行环境为 macOS（当前 OS 已是 Darwin），无平台障碍 |
| PlantUML skill 加载失败 | 设计阶段 §5 流程图降级为 mermaid（已设计降级路径） |
| final 文档结构差异大 | final 文档结构由"实例产物摘要 + 文档链接"聚合（不强制汇总全文），保持轻量 |

---

## 6. 执行顺序

1. 修改 `context-system.md` §4 目录布局树 + §11 + §12（最优先：所有阶段细则都依赖此约定）
2. 修改 `requirements-stage.md`（应用 2 + 应用 0）
3. 修改 `design-stage.md`（应用 3 + 应用 4 + 应用 0 + 应用 1）
4. 修改 `development-stage.md` + `testing-stage.md`（应用 0 + 应用 1 轻量改动）
5. 修改 `SKILL.md` §2 登记表
6. 修改 `cross-reference-index.md` 末次校验
7. 修改 `version-evolution.md` §4 总账
8. 增 `changelog/2026-08-11.md` 当日新增条目

---

## 7. 待用户确认

请确认以下决策（已通过 AskUserQuestion 收齐 2 项）：

- ✅ 阶段目录重命名为 `101-requirements/201-design/301-development/401-testing/`
- ✅ docs 软链接目标为 `final/<阶段名>-final.md`
- 待确认：本次优化整体方案是否通过？

通过后即按 §6 执行顺序逐一修改。
