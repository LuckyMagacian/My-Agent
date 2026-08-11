#!/bin/bash
#
# model_service.sh - 启动/管理 Hy-MT2-7B (llama.cpp) 本地翻译模型服务
#
# 为 pdf-translator 提供 OpenAI 兼容翻译 API。
# 默认 Q6_K 精度，Metal GPU 全卸载 + Flash Attention。
#
# 用法: model_service.sh <命令> [选项]
#   start      启动服务
#   stop       停止服务
#   restart    重启服务
#   status     查看运行状态
#   log        跟踪日志 (tail -f)
#   -h|--help  显示帮助
#
# 选项 (仅对 start/restart 生效):
#   -p, --port PORT       端口号        (默认: 9000)
#   --host HOST           监听地址       (默认: 127.0.0.1)
#   -n, --ngl N           GPU 层数      (默认: 99)
#   -c, --ctx N           上下文长度     (默认: 8192)
#   -t, --threads N       线程数        (默认: 8)
#   -m, --model SPEC      精度: Q4/Q6/Q8 或文件名 (默认: Q6)
#   --model-dir PATH      模型目录       (默认: $HOME/models/Tencent-Hunyuan--Hy-MT2-7B-GGUF/snapshots/master)
#   --run-dir PATH        运行目录       (默认: $HOME/.local/run/hy-mt2)

set -uo pipefail

# ---- 定位脚本目录 ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- 默认配置 ----
MODEL_DIR="${HOME}/models/Tencent-Hunyuan--Hy-MT2-7B-GGUF/snapshots/master"
DEFAULT_MODEL="Q6"   # 精度别名 Q4/Q6/Q8, 也可传文件名
HOST="127.0.0.1"
PORT=9000
NGL=99
CTX=8192
THREADS=8
ALIAS="hy-mt2-7b"

RUN_DIR="${HOME}/.local/run/hy-mt2"
PIDFILE="${RUN_DIR}/hy-mt2.pid"
LOGFILE="${RUN_DIR}/hy-mt2.log"

show_help() {
    cat <<EOF
model_service.sh - 启动/管理 Hy-MT2-7B (llama.cpp) 翻译服务

用法: model_service.sh <命令> [选项]

命令:
  start     启动服务
  stop      停止服务
  restart   重启服务
  status    查看运行状态
  log       跟踪日志 (tail -f)
  -h|--help 显示本帮助

选项 (仅对 start/restart 生效):
  -p, --port PORT      端口号       (默认: $PORT)
  --host HOST          监听地址      (默认: $HOST; 外部访问用 0.0.0.0)
  -n, --ngl N          GPU 层数     (默认: $NGL; 纯 CPU 用 0)
  -c, --ctx N          上下文长度    (默认: $CTX)
  -t, --threads N      线程数       (默认: $THREADS)
  -m, --model SPEC     精度: Q4/Q6/Q8 或文件名 (默认: $DEFAULT_MODEL)
  --model-dir PATH     模型目录      (默认: $MODEL_DIR)
  --run-dir PATH       运行目录      (默认: $RUN_DIR)

精度选择:
  Q4  Hy-MT2-7B-Q4_K_M.gguf  良好质量，最快
  Q6  HY-MT2-7B-Q6_K.gguf    推荐，质量与速度平衡
  Q8  HY-MT2-7B-Q8_0.gguf    最佳质量，较慢

示例:
  model_service.sh start
  model_service.sh start -m Q6
  model_service.sh start -p 9001 --host 0.0.0.0
  model_service.sh restart -m Q8
  model_service.sh stop
  model_service.sh status
EOF
}

ensure_run_dir() { mkdir -p "$RUN_DIR"; }

# 精度别名 -> 文件名 (大小写不敏感, 兼容 bash 3.2)
resolve_model_file() {
    local out
    shopt -s nocasematch
    case "$1" in
        Q4|Q4_K_M) out="Hy-MT2-7B-Q4_K_M.gguf" ;;
        Q6|Q6_K)   out="HY-MT2-7B-Q6_K.gguf" ;;
        Q8|Q8_0)   out="HY-MT2-7B-Q8_0.gguf" ;;
        *)         out="$1" ;;
    esac
    shopt -u nocasematch
    echo "$out"
}

is_running() {
    [[ -f "$PIDFILE" ]] || return 1
    local pid; pid=$(cat "$PIDFILE" 2>/dev/null) || return 1
    [[ -n "$pid" ]] || return 1
    kill -0 "$pid" 2>/dev/null
}

resolve_llama_server() {
    if command -v llama-server >/dev/null 2>&1; then
        echo llama-server
    elif [[ -x /opt/homebrew/bin/llama-server ]]; then
        echo /opt/homebrew/bin/llama-server
    else
        return 1
    fi
}

do_start() {
    if is_running; then
        echo "服务已在运行 (PID $(cat "$PIDFILE"))"
        echo "如需重启: model_service.sh restart"
        return 0
    fi

    local llama_server; llama_server=$(resolve_llama_server) || {
        echo "错误: 未找到 llama-server, 请先 'brew install llama.cpp'" >&2
        exit 1
    }

    local model_file; model_file=$(resolve_model_file "$MODEL_FILE")
    local model="$MODEL_DIR/$model_file"
    if [[ ! -f "$model" ]]; then
        echo "错误: 模型文件不存在: $model" >&2
        echo "请确认模型已下载至 $MODEL_DIR，或通过 --model-dir 指定目录" >&2
        exit 1
    fi

    if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "错误: 端口 $PORT 已被占用" >&2
        exit 1
    fi

    ensure_run_dir

    echo "模型:   $model"
    echo "监听:   http://$HOST:$PORT  (GPU 层=$NGL, 上下文=$CTX, 线程=$THREADS)"
    echo "启动中..."

    nohup "$llama_server" \
        --model "$model" \
        --alias "$ALIAS" \
        --host "$HOST" --port "$PORT" \
        -ngl "$NGL" -c "$CTX" -t "$THREADS" \
        --flash-attn on \
        --jinja \
        --temp 0.7 --top-k 20 --top-p 0.6 --repeat-penalty 1.05 \
        > "$LOGFILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PIDFILE"
    echo "PID=$pid  日志: $LOGFILE"

    # 健康检查
    local check_host="$HOST"; [[ "$HOST" == "0.0.0.0" ]] && check_host="127.0.0.1"
    local i
    for ((i = 0; i < 30; i++)); do
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "错误: 进程已退出, 日志末尾:" >&2
            tail -20 "$LOGFILE" >&2
            rm -f "$PIDFILE"
            exit 1
        fi
        if curl -sf -o /dev/null "http://$check_host:$PORT/health" 2>/dev/null; then
            echo "✅ 服务就绪: http://$HOST:$PORT"
            echo "   Chat API:  http://$HOST:$PORT/v1/chat/completions"
            return 0
        fi
    done
    echo "⚠️  进程在运行但 30s 内 /health 未就绪, 请检查日志: $LOGFILE" >&2
    return 1
}

do_stop() {
    if ! is_running; then
        echo "服务未运行"
        rm -f "$PIDFILE"
        return 0
    fi
    local pid; pid=$(cat "$PIDFILE")
    echo "停止 PID=$pid ..."
    kill "$pid" 2>/dev/null || true
    local i
    for ((i = 0; i < 20; i++)); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.5
    done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "已停止"
}

do_status() {
    if is_running; then
        local pid; pid=$(cat "$PIDFILE")
        echo "● 运行中  PID=$pid  监听=$HOST:$PORT"
        local check_host="$HOST"; [[ "$HOST" == "0.0.0.0" ]] && check_host="127.0.0.1"
        if curl -sf "http://$check_host:$PORT/health" 2>/dev/null | grep -q '"status":"ok"'; then
            echo "  /health: ok"
        else
            echo "  /health: 无响应或加载中"
        fi
    else
        echo "● 未运行"
        return 3
    fi
}

do_log() {
    [[ -f "$LOGFILE" ]] || { echo "无日志文件: $LOGFILE"; exit 1; }
    tail -f "$LOGFILE"
}

# ---- 解析命令 ----
CMD="${1:-}"
[[ -n "$CMD" ]] || { show_help; exit 0; }
case "$CMD" in
    -h|--help) show_help; exit 0 ;;
    start|stop|restart|status|log) shift ;;
    *) echo "未知命令: $CMD" >&2; echo "运行 'model_service.sh -h' 查看帮助" >&2; exit 1 ;;
esac

# ---- 解析选项 ----
MODEL_FILE="$DEFAULT_MODEL"
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--port)        PORT="$2"; shift 2 ;;
        --host)           HOST="$2"; shift 2 ;;
        -n|--ngl)         NGL="$2"; shift 2 ;;
        -c|--ctx)         CTX="$2"; shift 2 ;;
        -t|--threads)     THREADS="$2"; shift 2 ;;
        -m|--model)       MODEL_FILE="$2"; shift 2 ;;
        --model-dir)      MODEL_DIR="$2"; shift 2 ;;
        --run-dir)        RUN_DIR="$2"; PIDFILE="$RUN_DIR/hy-mt2.pid"; LOGFILE="$RUN_DIR/hy-mt2.log"; shift 2 ;;
        -h|--help)        show_help; exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

case "$CMD" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_stop; do_start ;;
    status)  do_status ;;
    log)     do_log ;;
esac