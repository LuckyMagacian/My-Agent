# 本地翻译模型服务

pdf-translator 支持通过本地部署的 **Hy-MT2-7B** 翻译模型完成翻译，无需依赖外部 API。

模型管理使用 skill 内置脚本 [model_service.sh](model_service.sh)。

## 模型信息

| 项目 | 值 |
|------|-----|
| 模型 | Tencent-Hunyuan Hy-MT2-7B (GGUF) |
| 推理引擎 | llama.cpp (`llama-server`) |
| 精度 | **Q6_K**（默认，推荐） |
| API 协议 | OpenAI 兼容 (`/v1/chat/completions`) |
| 监听地址 | `http://127.0.0.1:9000` |
| 上下文长度 | 8192 tokens |
| GPU 加速 | Metal (Apple Silicon) + Flash Attention |

## 精度选择

| 别名 | 文件名 | 质量 | 速度 |
|------|--------|------|------|
| `Q4` | `Hy-MT2-7B-Q4_K_M.gguf` | 良好 | 最快 |
| `Q6` | `HY-MT2-7B-Q6_K.gguf` | **推荐** | 快 |
| `Q8` | `HY-MT2-7B-Q8_0.gguf` | 最佳 | 较慢 |

## 模型管理

使用 skill 内置的 `model_service.sh` 管理模型服务生命周期。

### 启动服务（默认 Q6 精度）

```bash
skills/pdf-translator/model_service.sh start
```

启动后自动：
- 加载 Q6_K 精度模型
- 启动 Metal GPU 全卸载 + Flash Attention
- 监听 `http://127.0.0.1:9000`
- 健康检查（最长等待 30s）

### 指定精度启动

```bash
# Q4 精度（更快，质量略低）
skills/pdf-translator/model_service.sh start -m Q4

# Q6 精度（默认，推荐）
skills/pdf-translator/model_service.sh start -m Q6

# Q8 精度（最佳质量，最慢）
skills/pdf-translator/model_service.sh start -m Q8
```

### 自定义参数

```bash
# 指定端口
skills/pdf-translator/model_service.sh start -p 9001

# 外网访问
skills/pdf-translator/model_service.sh start --host 0.0.0.0

# 增大上下文
skills/pdf-translator/model_service.sh start -c 16384

# 纯 CPU 模式
skills/pdf-translator/model_service.sh start -n 0

# 自定义模型目录
skills/pdf-translator/model_service.sh start --model-dir /path/to/models
```

### 查看状态

```bash
skills/pdf-translator/model_service.sh status
# ● 运行中  PID=12345  监听=127.0.0.1:9000
#   /health: ok
```

### 停止服务

```bash
skills/pdf-translator/model_service.sh stop
```

### 重启服务

```bash
skills/pdf-translator/model_service.sh restart -m Q6
```

### 查看日志

```bash
skills/pdf-translator/model_service.sh log
```

## 与 pdf-translator 集成

### 配置开关

`config.json` 中 `local_model.enabled` 控制是否使用本地模型：

```json
{
  "local_model": {
    "enabled": true,
    "base_url": "http://127.0.0.1:9000/v1",
    "model": "hy-mt2-7b",
    "api_key": "not-needed"
  }
}
```

- `enabled: true` → 使用本地模型，自动覆盖 `base_url`/`model`/`api_key`
- `enabled: false` → 使用远程 API（deepseek 等）

### 环境变量切换

```bash
# 强制启用本地模型
LOCAL_MODEL=1 uv run skills/pdf-translator/pdf_translate.py input.pdf

# 强制使用远程 API
LOCAL_MODEL=0 uv run skills/pdf-translator/pdf_translate.py input.pdf
```

### 完整使用流程

```bash
# 1. 启动本地模型（如未启动）
skills/pdf-translator/model_service.sh start

# 2. 确认模型就绪
skills/pdf-translator/model_service.sh status

# 3. 运行翻译（自动使用本地模型）
uv run skills/pdf-translator/pdf_translate.py document.pdf --output document.zh.pdf
```

## 前置条件

- macOS + Apple Silicon（Metal GPU 加速）
- `llama.cpp` 已安装：`brew install llama.cpp`
- 模型文件已下载至 `~/models/Tencent-Hunyuan--Hy-MT2-7B-GGUF/snapshots/master/`

## 排错

| 问题 | 解决 |
|------|------|
| `llama-server: command not found` | `brew install llama.cpp` |
| 模型文件不存在 | 检查模型目录，或通过 `--model-dir` 指定 |
| 端口被占用 | `lsof -i :9000` 查看占用进程，或换端口 `-p 9001` |
| 30s 内未就绪 | 查看日志 `model_service.sh log`，模型首次加载需 warm-up |
| 翻译质量不佳 | 尝试 Q8 精度：`model_service.sh restart -m Q8` |
| 内存不足 | 降级到 Q4：`model_service.sh restart -m Q4` |