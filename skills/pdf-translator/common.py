"""pdf-translator 共享工具：惰性 PyMuPDF 导入与页码范围解析。"""
from __future__ import annotations


def _get_fitz():
    """惰性导入 PyMuPDF，兼容 pymupdf / fitz 两种模块名。"""
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError:  # pragma: no cover
        import fitz  # type: ignore
    return fitz


def parse_pages(spec: str | None, total: int) -> list[int] | None:
    """解析页码范围（1-based），返回 0-based 页号列表；None 表示全部。"""
    if not spec:
        return None
    result: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            for i in range(int(a), int(b) + 1):
                if 1 <= i <= total:
                    result.append(i - 1)
        else:
            i = int(part)
            if 1 <= i <= total:
                result.append(i - 1)
    return result


def trans_text(v) -> str:
    """译文值统一取文本：兼容旧 {id: str} 与新 {id: {text, segments}}。"""
    return v["text"] if isinstance(v, dict) else v
