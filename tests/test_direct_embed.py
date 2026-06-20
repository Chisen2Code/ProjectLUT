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


# ── dynamic_cut ─────────────────────────────────────────


from lut.direct_embed import dynamic_cut


def test_dynamic_cut_normal():
    scores = [(f"p{i}", s) for i, s in enumerate([0.62, 0.55, 0.48, 0.42, 0.35, 0.31, 0.18, 0.12])]
    result = dynamic_cut(scores)
    assert len(result) == 6
    assert result[-1][0] == "p5"


def test_dynamic_cut_steep():
    scores = [(f"p{i}", s) for i, s in enumerate([0.62, 0.55, 0.25, 0.12])]
    result = dynamic_cut(scores)
    assert len(result) == 2


def test_dynamic_cut_below_min():
    scores = [(f"p{i}", s) for i, s in enumerate([0.25, 0.12])]
    result = dynamic_cut(scores)
    assert result == []


def test_dynamic_cut_single():
    scores = [("p0", 0.62)]
    result = dynamic_cut(scores)
    assert len(result) == 1


def test_dynamic_cut_empty():
    result = dynamic_cut([])
    assert result == []


def test_dynamic_cut_max_cap():
    scores = [(f"p{i}", 0.9 - i*0.02) for i in range(15)]
    result = dynamic_cut(scores, max_count=10)
    assert len(result) == 10


def test_dynamic_cut_edge_drop():
    scores = [(f"p{i}", s) for i, s in enumerate([0.50, 0.36])]
    result = dynamic_cut(scores, drop_threshold=0.15)
    assert len(result) == 2
