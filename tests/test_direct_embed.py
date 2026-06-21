"""direct_embed.py 单元测试"""
import numpy as np
from pathlib import Path
from lut.direct_embed import build_index, search, get_stats, get_history


def test_build_index_creates_files():
    """build_index 生成索引文件（含 ids.txt）"""
    build_index()
    assert (Path(".lut_vectors") / "vectors.npy").exists()
    assert (Path(".lut_vectors") / "texts.txt").exists()
    assert (Path(".lut_vectors") / "ids.txt").exists()


def test_search_returns_top5():
    """search 返回 N 个结果，含 preset_id + 分数 + index"""
    results = search("冷色调胶片感", top_n=5)
    assert len(results) == 5
    for pid, score, idx in results:
        assert isinstance(pid, str) and len(pid) > 0
        assert 0.0 <= score <= 1.0
        assert isinstance(idx, int)
        assert 0 <= idx <= 151


def test_search_finds_fuji():
    """搜索'富士'应返回含富士的 LUT"""
    results = search("富士胶片风格")
    pids = [r[0] for r in results]
    assert any("富士" in pid for pid in pids), f"未找到富士: {pids}"


def test_search_returns_index():
    """search 返回结果含 index 字段"""
    results = search("冷淡", top_n=10)
    assert len(results) > 0
    for pid, score, idx in results:
        assert isinstance(idx, int)
        assert 0 <= idx <= 151


def test_get_stats_returns_dict():
    """get_stats 从 JSON 日志读取统计"""
    stats = get_stats()
    assert "total" in stats
    assert "top_queries" in stats
    assert isinstance(stats["total"], int)
    assert stats["total"] >= 0


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


# ── JSON search log ──────────────────────────────────────


import json
from pathlib import Path
from lut.direct_embed import log_search_json, log_click

LOG_DIR = Path("data/search_log")


def test_log_search_json_creates_file():
    """log_search_json 创建 JSON 文件"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    sid = log_search_json(
        query="冷淡",
        query_vector=[0.1, 0.2, 0.3],
        top_results=[("p1", 0.5, 23), ("p2", 0.4, 67)],
        duration_ms=3
    )
    assert sid is not None
    files = list(LOG_DIR.glob(f"{sid.split('_')[0]}_*.json"))
    assert len(files) >= 1
    with open(LOG_DIR / f"{sid}.json", encoding="utf-8") as f:
        data = json.load(f)
    assert data["query"] == "冷淡"
    assert data["query_vector"] == [0.1, 0.2, 0.3]
    assert data["top_count"] == 2
    assert data["top_results"][0]["index"] == 23
    assert data["top_results"][0]["preset_id"] == "p1"
    assert data["clicked_preset_id"] is None


def test_log_click_updates_file():
    """log_click 补写 clicked_preset_id"""
    sid = log_search_json("test", [0.5], [("p", 0.9, 42)], 1)
    log_click(sid, "p-42")
    with open(LOG_DIR / f"{sid}.json", encoding="utf-8") as f:
        data = json.load(f)
    assert data["clicked_preset_id"] == "p-42"


def test_log_click_unknown_id():
    """不存在的 search_id 不崩溃"""
    result = log_click("nonexistent_000", "unknown")
    assert result is False


def teardown_cleanup():
    """清理测试产生的日志文件"""
    import os
    for f in LOG_DIR.glob("*.json"):
        try:
            content = f.read_text(encoding="utf-8")
            if "test" in content or "nonexistent" in content:
                f.unlink()
        except Exception:
            pass
