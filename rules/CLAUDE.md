# 必须遵守的规则

## 交流规范
- 使用简体中文交流，专业术语保留英语，若无法使用简体中文则回退英语
- 简洁明了沟通，不要有过多描述性语句
- 不要读取整个文件，使用 grep 或指定行范围查找

## 核心工作流 Skills（必须遵循）

### 开发流程
- **所有编程任务**必须遵循 `software-development-workflow` 的四种模式之一：
  - 完整需求开发：新增独立模块/页面/服务
  - 功能变更：已有项目中的小范围改动
  - 问题修复：修复已有功能的异常/Bug
  - 技术分析：理解现有代码（只读，不修改）

### 设计与实现流程
- **创建功能/组件/修改行为前**：必须先使用 `brainstorming` 探索设计，获得用户批准后才能继续
- **有设计/需求后、编码前**：必须使用 `writing-plans` 制定详细实施计划
- **执行计划时**：使用 `executing-plans` 按步骤执行

### 质量保障
- **声称完成前**：必须使用 `verification-before-completion`，先运行验证命令再声明结果
- **全程使用** `attention-maintenance` 维持任务注意力，每 10 轮检查一次任务锚点

## 问题修复规则
- 在分析任何代码错误（尤其是框架报错）时，**禁止直接给出猜测**
- 必须遵循 `software-development-workflow` 中的问题修复流程：问题分析 → 影响范围 → 制定方案 → 用户确认 → 实施修复

## 技术场景 Skills（按需触发）
- React/Next.js 代码：参考 `react-best-practices`
- React Native/Expo 代码：参考 `react-native-skills`
- 页面过渡动画：参考 `react-view-transitions`
- HTTP 请求/网络操作：参考 `http-retry-handler`
- UI/UX 原型设计：参考 `prototype-prompt-generator`
- 创建新 Skill：参考 `writing-skills`