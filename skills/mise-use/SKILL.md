---
name: mise-use
description: "mise 开发工具版本管理器与任务运行器使用指南。当用户涉及开发工具版本管理（node/python/ruby/go 等）、项目环境配置（.mise.toml）、任务定义与执行、mise 命令使用问题时自动应用。"
---

# mise 使用指南

mise 是开发工具版本管理器 + 任务运行器，替代 asdf/nvm/pyenv/rbenv/direnv/task 等工具。

**核心能力**：Dev Tools（多版本管理） + Environments（环境变量/别名/密钥） + Tasks（项目任务）

## 触发条件

| 场景 | 示例 |
|------|------|
| 安装/切换工具版本 | "安装 node 20"、"切换 python 版本" |
| 项目环境配置 | "配置 .mise.toml"、"项目级工具管理" |
| 任务定义与执行 | "定义构建任务"、"运行 lint" |
| 版本冲突排查 | "工具版本不对"、"which 命令指向错误" |
| 环境变量管理 | "设置项目环境变量" |

## 一、环境安装与切换

### 1.1 安装环境（mise use）

```bash
mise use node@20                 # 安装并写入当前目录 mise.toml
mise use -g node@20              # 安装并写入全局配置
mise use --env local node@20     # 写入 mise.local.toml（不提交 Git）
mise use --pin node@20           # 写入精确版本（如 20.11.0）
mise use --fuzzy node@20         # 写入模糊版本（如 20）
mise use --remove node           # 从配置中移除工具
```

**`mise use` vs `mise install`**：

| 命令 | 写入配置 | 激活 | 适用场景 |
|------|---------|------|---------|
| `mise use` | ✅ | ✅ | 日常使用，推荐 |
| `mise install` | ❌ | ❌ | 仅下载，不改变环境 |

### 1.2 切换环境

```bash
# 临时切换（仅当前 shell）
mise shell node@20               # 切换当前 shell 的 node 版本
mise x node@20 -- node app.js    # 一次性使用指定版本执行命令

# 永久切换（写入配置）
mise use node@18                 # 项目级切换
mise use -g node@18              # 全局切换

# 环境配置切换
mise -E staging run deploy       # 加载 mise.staging.toml 环境
mise en /path/to/project         # 进入目录并激活该目录环境
```

### 1.3 多环境配置

```bash
# 按环境创建配置文件
mise.toml                        # 默认环境
mise.staging.toml                # staging 环境
mise.production.toml             # production 环境

# 使用指定环境
mise -E staging run deploy
mise -E production run deploy
```

### 1.4 查询当前环境

```bash
mise current                     # 所有工具的当前活跃版本
mise current node                # 指定工具的当前版本
mise ls --current                # 仅当前配置中的版本
mise which node                  # 可执行文件路径
mise where node@20               # 安装目录
mise config ls                   # 配置文件加载顺序
```

## 二、配置文件

### 2.1 文件优先级（高→低）

| 文件 | 作用 | 是否提交 Git |
|------|------|-------------|
| `mise.local.toml` | 本地配置，敏感信息 | ❌ |
| `mise.toml` | 项目主配置 | ✅ |
| `mise/config.toml` | 子目录配置 | ✅ |
| `.config/mise/conf.d/*.toml` | 配置片段 | ✅ |
| `~/.config/mise/config.toml` | 全局用户配置 | - |

### 2.2 mise.toml 结构

```toml
[tools]
node = "20"                          # 模糊版本
python = "3.12"
"go" = "1.21"                        # 引号格式（版本含点）
"npm:prettier" = "3"                 # npm 后端
"pipx:black" = "latest"              # pipx 后端
"cargo:ripgrep" = "latest"           # cargo 后端
"github:BurntSushi/ripgrep" = "latest"  # GitHub 后端

[env]
NODE_ENV = "development"
API_URL = "localhost:3000"

[tasks.build]
description = "Build the project"
run = "cargo build"
depends = ["clean"]                  # 任务依赖

[tasks.test]
run = "pytest"
dir = "tests"                        # 执行目录

[tasks.lint]
run = ["eslint .", "prettier --check ."]  # 多命令
```

### 2.3 工具选项

```toml
[tools."http:my-tool"]
version = "1.0.0"
os = ["linux", "macos"]              # 限制操作系统
depends = ["python"]                 # 安装依赖
postinstall = "corepack enable"      # 安装后执行
```

### 2.4 File Tasks（脚本任务）

优于 TOML 内定义：支持语法高亮和 lint。

```bash
# mise-tasks/build
#!/usr/bin/env bash
#MISE description="Build the CLI"
cargo build
```

## 三、任务执行

```bash
mise run build                      # 运行任务
mise build                          # 简写（无歧义时）
mise run lint ::: test ::: check    # 并行运行多个任务
mise tasks ls                       # 列出所有任务
mise tasks info build               # 任务详情
mise watch build                    # 监听变化自动执行
```

**任务依赖自动并行**：`depends = ["clean", "deps"]` → clean 和 deps 并行执行。

## 四、环境变量管理

```bash
mise set NODE_ENV=production        # 写入配置
mise unset NODE_ENV                 # 删除
mise config get NODE_ENV            # 获取
```

**任务内可用变量**：

| 变量 | 说明 |
|------|------|
| `MISE_CONFIG_ROOT` | 配置文件目录 |
| `MISE_PROJECT_ROOT` | 项目根目录 |
| `MISE_TASK_NAME` | 当前任务名 |
| `MISE_TASK_FILE` | 任务脚本路径 |

## 五、常用全局 Flags

| Flag | 说明 |
|------|------|
| `-C --cd <DIR>` | 改变工作目录 |
| `-E --env <ENV>` | 加载环境配置 |
| `-g --global` | 使用全局配置 |
| `-j --jobs <N>` | 并行数（默认 8） |
| `-q --quiet` | 静默输出 |
| `-v --verbose` | 详细输出 |
| `--no-config` | 不加载配置 |
| `--locked` | 要求锁文件 |

## 六、命令速查

| 命令 | 别名 | 功能 |
|------|------|------|
| `mise use` | `u` | 安装工具并写入配置 |
| `mise install` | `i` | 安装工具版本（不写入配置） |
| `mise run` | `r` | 运行任务 |
| `mise exec` | `x` | 临时执行命令 |
| `mise shell` | - | 临时切换当前 shell 版本 |
| `mise ls` | `list` | 列出已安装工具 |
| `mise current` | - | 当前活跃版本 |
| `mise which` | - | 可执行文件路径 |
| `mise where` | - | 安装目录 |
| `mise tasks` | `t` | 管理任务 |
| `mise config` | `cfg` | 管理配置 |
| `mise trust` | - | 信任配置文件 |
| `mise outdated` | - | 检查过时工具 |
| `mise doctor` | - | 诊断配置问题 |

## 七、最佳实践

### 环境切换策略

| 场景 | 推荐方式 | 说明 |
|------|---------|------|
| 项目级固定版本 | `mise use node@20` | 写入 mise.toml，团队共享 |
| 个人本地偏好 | `mise use --env local node@20` | 写入 mise.local.toml，不提交 |
| 全局默认版本 | `mise use -g node@20` | 全局配置 |
| 临时测试 | `mise shell node@21` | 仅当前 shell 生效 |
| 一次性执行 | `mise x node@20 -- node app.js` | 不改变任何配置 |

### 版本管理
- ✅ 项目用模糊版本（`node = "20"`），锁文件（`mise.lock`）固定精确版本
- ✅ 全局用精确版本（`mise use -g --pin node@20`）
- ✅ CI 使用 `--locked` 确保可复现

### 配置安全
- ✅ 首次使用项目执行 `mise trust`
- ✅ 敏感配置写入 `mise.local.toml`，加入 `.gitignore`
- ✅ 全局信任路径：`mise settings set trusted_config_paths ["~/projects"]`

### 后端选择

| 后端 | 格式 | 适用场景 |
|------|------|---------|
| core | `node = "20"` | 内置支持的主流工具 |
| npm | `"npm:prettier" = "3"` | npm 包 |
| pipx | `"pipx:black" = "latest"` | Python CLI 工具 |
| cargo | `"cargo:ripgrep" = "latest"` | Rust 工具 |
| github | `"github:user/repo" = "latest"` | GitHub release |

### 任务优化
- ✅ 优先使用 File Tasks（脚本文件），优于 TOML 内联
- ✅ 利用 `depends` 声明依赖，mise 自动并行
- ✅ 使用 `mise watch` 开发时自动重建

## 八、故障排查

```bash
mise doctor                        # 诊断整体配置
mise which node                    # 检查命令指向
mise config ls                     # 查看配置加载顺序
mise current                       # 当前活跃版本
mise ls --current                  # 配置中的版本
```

**常见问题**：

| 问题 | 原因 | 解决 |
|------|------|------|
| 版本未切换 | 未激活 shell | `eval "$(mise activate zsh)"` |
| 命令找不到 | shim 未生成 | `mise reshim` |
| 配置未加载 | 未 trust | `mise trust` |
| 版本不对 | 多层配置覆盖 | `mise config ls` 排查优先级 |
| 安装缓慢 | GitHub 限流 | `mise token github` |
