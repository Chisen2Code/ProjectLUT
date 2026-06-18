"""direct_embed.py 单元测试"""
import numpy as np
from pathlib import Path
from lut.direct_embed import build_index, search, get_stats, get_history, log_search


def test_build_index_creates_files():
    """build_index 生成 vectors.npy 和 texts.txt"""
    build_index()
    assert (Path(".lut_vectors") / "vectors.npy").exists()
    assert (Path(".lut_vectors") / "texts.txt").exists()


def test_search_returns_top5():
    """search 返回 5 个结果，含分数"""
    results = search("冷色调胶片感")
    assert len(results) == 5
    for text, score in results:
        assert isinstance(text, str) and len(text) > 0
        assert 0.0 <= score <= 1.0


def test_search_finds_fuji():
    """搜索'富士'应返回含富士的 LUT"""
    results = search("富士胶片风格")
    texts = [r[0] for r in results]
    assert any("富士" in t for t in texts), f"未找到富士: {texts}"


def test_log_search_and_stats():
    """log_search 写入后 get_stats 可读取"""
    log_search("test query", [("test LUT", 0.99)], 100)
    stats = get_stats()
    assert stats["total"] >= 1


def test_get_history():
    """get_history 返回记录列表"""
    rows = get_history(5)
    assert isinstance(rows, list)
    if len(rows) > 0:
        assert "query" in rows[0]
        assert "at" in rows[0]
