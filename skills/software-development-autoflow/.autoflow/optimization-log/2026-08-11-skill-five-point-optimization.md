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
| 5（追加） | 设计阶段增加测试用例设计，需基于需求 + API 契约 | 当前设计阶段无测试用例设计产物 |
| 6（追加） | 测试阶段需要增加对前置阶段生成的测试用例的使用；增加设计接口集成测试（可能依赖数据库、登录 token、测试域名） | 当前测试阶段自行设计测试用例，未消费设计阶段产物；接口集成测试依赖项（数据库/登录 token/测试域名）需明确处置 |

### 1.2 关键决策（已与用户确认）

- **阶段目录编号形式**：重命名为 `101-requirements / 201-design / 301-development / 401-testing`
- **docs 软链接目标**：每阶段定稿时另生成 `final/<阶段名>-final.md`，`docs/` 软链接到该文件

> **§1.2 决策修订备注（v0.8.10 修复）**：`docs/` 软链接目标的本条决策在迭代过程中被修正——经用户后续追加意见"不应仅对需求阶段的最终交付物命名 final；去除 final 目录与名称前后缀；所有阶段交付物应平权对待；各个阶段交付物均需要软链接挂载到 docs"——本节原"final 目录与 final 前后缀"被 §2.2「应用 1 设计原则」推翻。最终采纳方案为 **§2.2 应用 1 设计原则**：不创建 `final/` 子目录、移除 `final` 前后缀、各阶段交付物按原模板原路径落盘、`docs/` 下软链接平权挂载各阶段所有正式交付物。本条决策轨迹属历史留痕，实际执行已采纳 §2.2 口径。

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

### 2.6 应用 5（追加）：设计阶段增加测试用例设计（基于需求 + API 契约）

**设计目标**：在设计阶段产出独立的「测试用例设计」产物，作为下游测试阶段的输入——避免测试阶段从零设计用例，同时保证测试用例对需求条目（REQ-NNN）与 API 接口（API-NNN）的双向覆盖。

**产物位置**：`stages/201-design/test-cases.md`（独立产物，与 §4.4~§4.5 架构/详细方案平权）。

**模板结构**（§4.8 新增）：

1. **总览**：测试用例总数 + 按需求条目 REQ-NNN 分布（覆盖核对表）+ 按 API 接口 API-NNN 分布（接口覆盖核对表）；
2. **用例分类**：
   - **单元测试用例**（按需）：覆盖纯函数、工具方法、状态机分支等；
   - **接口契约测试用例**：每接口（API-NNN）必含；正例 + 异常例 + 边界条件；用例 ID `TC-NNN`（顺序编号、唯一、不复用）；
   - **接口集成测试用例**（接口级联 / 多接口协作场景）：用例 ID `TI-NNN`（独立编号空间）；**前置条件**（数据库 schema / 登录 token / 测试域名等依赖，见应用 6）；
   - **端到端（E2E）测试用例**（如涉及）：用例 ID `TE-NNN`（独立编号空间）；
3. **需求覆盖核对表**：REQ-NNN ↔ TC/TI/TE 双向映射；未覆盖条目显式标注理由（如纯静态页无测试必要）；
4. **接口覆盖核对表**：API-NNN ↔ TC/TI 双向映射；未覆盖接口显式标注理由；
5. **依赖声明**（关键）：测试运行所需外部依赖清单——数据库（类型/schema/迁移路径）、登录 token（获取方式/有效期）、测试域名（环境变量/桩服务）、第三方 mock 列表、测试 fixture 路径；
6. **可执行性确认**：每个用例含可执行的核验方式（测试框架名 + 命令 + 预期结果模板）；不可自动化用例显式标注「人工核验」+ 操作步骤 + 预期结果；
7. **未决项**（如有）：遗留的待测试阶段确认事项。

**与现有设计产物的关系**：

- 测试用例设计实例（`instance-testcases`）作为设计阶段新实例，并入依赖链（§5.3 修订）：API 契约定稿后启动（与前端/后端实例并行或串行——由 §5.3 修订裁定）；
- 阶段定稿时 `test-cases.md` 与其他设计产物平权软链接到 `<req-id>/docs/test-cases.md`；
- 不替代测试阶段的测试代码编写（§5.4 测试运行入口问询 + 测试代码实现）——只承担"用例设计"职责，代码实现归测试阶段。

**受影响组件**：

- `context-system.md` §4 目录布局树：增 `test-cases.md` 行（201-design 阶段目录下）+ docs 软链接行；
- `design-stage.md` §3 输出：增测试用例设计产物行；§4 模板增 §4.8；§5.3 依赖链：增 test-cases 实例（启动条件：API 契约定稿；适用判定：恒执行）；§5.4 任务拆解客观自检项增"测试用例覆盖"核对（每 REQ-NNN 至少被一个 TC/TI/TE 关联）；§7.4 阶段级确认对象增测试用例设计产物

### 2.7 应用 6（追加）：测试阶段消费设计阶段测试用例 + 增加接口集成测试

**修改 `testing-stage.md`**：

**A. 测试阶段消费设计阶段测试用例**（强制读取，非可选）：

- §3 输入与输出——输入①增「设计阶段测试用例设计产物（`stages/201-design/test-cases.md`）」（设计阶段定稿产物，与验收标准并列作为入口必备）；
- §4.1 测试报告——第 4 段"测试覆盖说明"改写：覆盖来源同时含**设计阶段测试用例**（按 TC/TI/TE 编号引用）与**测试阶段新增用例**（覆盖设计阶段未涉及或调整的条目）；
- §4.4 测试实例交付物——第 1 段"测试代码清单"增引用对应设计用例 ID（TC-NNN / TI-NNN / TE-NNN）；第 2 段"核验设计"增"用例来源标注"（设计阶段用例 / 测试阶段新增用例）；
- §5 执行流程：测试阶段实例化前置条件增"设计阶段测试用例设计产物已定稿"——未满足时不得启动测试阶段，由 Main Agent 退回上游补充（或升级人工——比照 §5 入口条件升级规则）；
- **职责划分**：测试阶段**不重做用例设计**——按设计阶段已设计的用例执行核验；如执行中发现用例本身有误（缺漏、矛盾、不可执行），按 §7.3 迭代期阻断级疑问升级人工（来源标注 = 人工裁定·迭代期·设计用例缺陷），裁定结论登记验收核验记录人工裁定段并受 §7.4 强制确认约束；如需新增用例覆盖设计未涉及场景，由测试阶段自行增补（用例 ID 沿用 `TC-NNN` 续编 / `TI-NNN` / `TE-NNN`，在 §4.1 测试报告"测试覆盖说明"段标注来源 = 测试阶段新增）。

**B. 接口集成测试（核心：依赖项处置）**：

- §4.2 测试阶段产物增「接口集成测试记录」`integration-test-record.md`（阶段层文件，阶段定稿时由 Main Agent 落盘到 `stages/401-testing/integration-test-record.md` + 软链接到 `<req-id>/docs/integration-test-record.md`），结构固定：
  1. **依赖项就绪核验**：逐项核验设计阶段测试用例 §5 声明的依赖项——
     - **数据库**（类型 + schema 迁移状态 + 数据种子装载命令）；
     - **登录 token**（获取方式——直接登录 / mock 用户 / 测试环境预置；有效期；刷新机制）；
     - **测试域名**（DNS / 路由 / Hosts 配置；SSL 证书状态）；
     - **第三方 mock 服务**（端口、启动命令、健康检查）；
  2. **集成测试用例执行记录**：每用例（TI-NNN）逐条记录——执行命令、运行结果（通过 / 失败 / 阻塞）、证据（运行日志路径或运行输出摘要）、关联需求条目 ID + API 接口 ID；
  3. **依赖故障登记**：核验失败或执行阻塞时按故障类别登记——数据库未就绪 / token 失效 / 测试域名不可达 / 第三方 mock 不可用；每条故障标注：影响范围（哪些 TI-NNN 阻塞）、升级方向（设计用例缺陷 / 工程实现缺陷 / 基础设施缺陷）、处置路径（按 §5 升级规则——基础设施缺陷退回上游「工程环境就绪」问询，工程实现缺陷按缺陷回退 §7.2 处置）；
  4. **测试环境声明**：本次集成测试实际使用的环境快照——数据库版本/连接串、token 凭据来源（脱敏）、测试域名、mock 端口；
  5. **遗留风险**（如有）：依赖项就绪核验的已知短板（如测试域名 SSL 过期未续），逐条标注风险等级与是否阻断交付。
- §5 入口准备（§5.1 + §5.2 之间）增"测试基础就绪核验"段——`integration-test-record.md` 的依赖项就绪核验由 Main Agent 在测试运行入口问询（§5.2）**之前**完成：
  1. **数据库**——探查优先（沿用工程既有测试数据库，验证 schema 迁移可执行 + 数据种子装载），无既有设施时按工程语言惯例建立最小测试数据库（命令可客观执行并输出结果），探查无法确定时向用户问询（问询上界与停滞规则比照 §5.2）；
  2. **登录 token**——探查优先（沿用既有测试 token / 自动登录脚本），无可用机制时向用户问询获取方式（直接登录账号 / mock 账号凭据 / 测试环境预置 token）；
  3. **测试域名**——探查优先（沿用既有测试域名 / hosts 配置），无可用配置时向用户问询（测试域名 / 桩服务 / 本地启动回环地址）；
  4. **第三方 mock**——按工程既有测试基础设施惯例建立或探查；
- 问询达上限 / 停滞 / 不可达 → 升级人工（裁定选项：① 补齐后续流；② 终止本阶段；裁定登记验收核验记录人工裁定段并受 §7.4 强制确认约束）。

**C. 阶段定稿产物扩展**：

- 阶段定稿产物（§3 输出）由 3 份扩展为 4 份——`testing-report.md` / `defects.md` / `acceptance-verification.md` / `integration-test-record.md`（新增）；
- §4 模板增 §4.5「接口集成测试记录模板」（如上 B 节所述）；
- §7.4 阶段级确认对象增「接口集成测试记录 + 依赖项就绪核验结论」。

**受影响组件**：

- `context-system.md` §4 目录布局树：增 `test-cases.md` 行（201-design）+ `integration-test-record.md` 行（401-testing）+ 对应 docs 软链接行；
- `design-stage.md` §3 输出 + §4.8 新增模板 + §5.3 依赖链 + §5.4 任务拆解客观自检项 + §7.4 阶段级确认对象（应用 5）；
- `testing-stage.md` §3 输入与输出 + §4.1 测试报告 + §4.2 缺陷清单 + §4.4 测试实例交付物 + §4.5 新增「接口集成测试记录模板」+ §5.1 就绪核验扩展（数据库/token/域名/mock）+ §7.4 阶段级确认对象（应用 6 全部三项）

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

### 3.4 应用 5+6 追加后版本号变更

| 组件 | 现版本 | 新版本 | 升版理由 |
|---|---|---|---|
| context-system.md | v2.3.5 | v2.3.6 | 目录布局树增 `test-cases.md` + `integration-test-record.md` + 对应 docs 软链接行 |
| design-stage.md | v0.9.2 | v0.9.3 | §3 输出增 test-cases 产物；§4 模板增 §4.8 测试用例设计模板；§5.3 依赖链增 test-cases 实例；§5.4 任务拆解客观自检项增"测试用例覆盖"核对；§7.4 阶段级确认对象增 test-cases 产物 |
| testing-stage.md | v1.1 | v1.2 | §3 输入与输出增 test-cases.md 入口必备；§4.1 测试报告覆盖来源含设计阶段用例；§4.4 测试实例交付物引用设计用例 ID；§5 入口就绪核验扩"数据库/token/测试域名/mock"四项；新增 §4.5「接口集成测试记录模板」；§7.4 阶段级确认对象增 integration-test-record.md |

### 3.5 changelog 追加条目

在 changelog/2026-08-11.md 当日新增条目段追加应用 5+6 的留痕条目（条目号 19~21，编号接续上批条目 18）。

---

## 4. 受影响文档与文件清单

| 文件 | 修改内容 |
|---|---|
| SKILL.md | §2 登记表版本列；§9 索引如有相关项；§10 启动参数（如有相关项） |
| references/context-system.md | §4 目录布局树；§11 一致性规则增软链接一致性；§12 关系表 |
| references/requirements-stage.md | §3 输出；§4 模板（增 final 产物）；§5.0 外部输入问询；§5.3 初始稿；§7.4 阶段级确认 |
| references/design-stage.md | §3 输出增 test-cases 产物行；§4.8 新增测试用例设计模板（应用 5）；§5.3 依赖链增 test-cases 实例；§5.4 任务拆解客观自检项增"测试用例覆盖"核对；§7.4 阶段级确认对象增 test-cases 产物 |
| references/development-stage.md | §3 输出增 final；§3 归档约定路径；§7.4 |
| references/testing-stage.md | §3 输入与输出（增 test-cases 入口必备 + integration-test-record 产物）；§4.1 测试报告覆盖来源说明；§4.4 测试实例交付物引用设计用例 ID；新增 §4.5 接口集成测试记录模板；§5.1+§5.2 之间新增"测试基础就绪核验"段（数据库/token/测试域名/mock 四项）；§7.4 阶段级确认对象增 integration-test-record |
| references/cross-reference-index.md | 末次校验行 |
| references/version-evolution.md | §4 总账指针行 |
| changelog/2026-08-11.md | 当日新增条目段（追加应用 5+6 条目） |
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
