"""pdf-translator 配置：加载与打印。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """加载配置：环境变量优先 > config.json > 内置默认。"""
    cfg: dict[str, Any] = {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "THUDM/GLM-4-9B-0414",
        "api_key": "",
        "target_lang": "zh",
        "batch_size": 20,
        "max_chars_per_batch": 6000,
        "max_output_tokens": 8192,
        "context_overlap": 1,
    }
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 读取配置失败 {path}: {e}", file=sys.stderr)
    # 环境变量覆盖
    if os.getenv("OPENAI_API_KEY"):
        cfg["api_key"] = os.environ["OPENAI_API_KEY"]
    if os.getenv("OPENAI_BASE_URL"):
        cfg["base_url"] = os.environ["OPENAI_BASE_URL"]
    if os.getenv("OPENAI_MODEL"):
        cfg["model"] = os.environ["OPENAI_MODEL"]
    if os.getenv("TARGET_LANG"):
        cfg["target_lang"] = os.environ["TARGET_LANG"]
    return cfg


def _print_config(config: dict) -> None:
    """打印生效配置（不打印 apikey）。"""
    print(
        f"[info] 配置: model={config.get('model')} "
        f"base_url={config.get('base_url')} lang={config.get('target_lang')}",
        flush=True,
    )
