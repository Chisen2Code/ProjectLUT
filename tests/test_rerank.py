"""rerank.py + parser metadata 单元测试"""
from lut.parser import infer_contrast, infer_saturation, infer_tone, load_presets
from lut.rerank import rule_filter


# ── 关键词推断测试 ───────────────────────────────────────

def test_infer_contrast_low():
    assert infer_contrast("淡雅cold", "FAKE5207&淡雅") == "low"
    assert infer_contrast("film matte", "电影感") == "low"


def test_infer_contrast_high():
    assert infer_contrast("人像绿调（高对比）", "人像系列") == "high"


def test_infer_contrast_mid():
    assert infer_contrast("WARM暖调", "电影感") == "mid"


def test_infer_saturation_low():
    assert infer_saturation("低饱和冷", "电影感") == "low"
    assert infer_saturation("淡雅cold", "FAKE5207&淡雅") == "low"


def test_infer_saturation_high():
    assert infer_saturation("高饱和鲜艳", "电影感") == "high"


def test_infer_saturation_mid():
    assert infer_saturation("中性标准", "标准") == "mid"


def test_infer_tone_warm():
    assert infer_tone("暖调", "电影感") == "warm"
    assert infer_tone("WARM暖", "电影感") == "warm"


def test_infer_tone_cold():
    assert infer_tone("冷白", "人像系列") == "cold"
    assert infer_tone("cold冷白", "电影感") == "cold"


def test_infer_tone_neutral():
    assert infer_tone("中性标准", "标准") == "neutral"
    assert infer_tone("standard", "标准") == "neutral"


def test_preset_has_metadata():
    """所有 152 个预设都有对比度/饱和度/色温字段"""
    presets = load_presets()
    assert len(presets) == 152
    for p in presets:
        assert p.contrast in ("low", "mid", "high"), f"{p.name} contrast={p.contrast}"
        assert p.saturation in ("low", "mid", "high"), f"{p.name} saturation={p.saturation}"
        assert p.tone in ("warm", "cold", "neutral"), f"{p.name} tone={p.tone}"


# ── 规则过滤测试 ──────────────────────────────────────────

def _mock_preset(contrast="mid", saturation="mid", tone="neutral"):
    """创建模拟 Preset 对象"""
    return type("MockPreset", (object,), {
        "contrast": contrast,
        "saturation": saturation,
        "tone": tone,
    })()


def test_rule_filter_exclude_high_contrast():
    fake = {"p1": _mock_preset("high"), "p2": _mock_preset("low")}
    results = [("p1", 0.5), ("p2", 0.4)]
    out = rule_filter(results, "对比度低一点", fake)
    assert len(out) == 1
    assert out[0][0] == "p2"


def test_rule_filter_no_intent():
    fake = {"p1": _mock_preset("high")}
    out = rule_filter([("p1", 0.5)], "电影感胶片", fake)
    assert len(out) == 1


def test_rule_filter_limit_3():
    fake = {f"p{i}": _mock_preset() for i in range(5)}
    results = [(f"p{i}", 0.5 - i * 0.01) for i in range(5)]
    out = rule_filter(results, "冷淡", fake)
    assert len(out) == 3


def test_rule_filter_missing_preset():
    out = rule_filter([("unknown", 0.5)], "冷淡", {})
    assert len(out) == 1


def test_rule_filter_exclude_warm():
    """搜冷排除暖色调"""
    fake = {"p1": _mock_preset(tone="warm"), "p2": _mock_preset(tone="cold")}
    out = rule_filter([("p1", 0.5), ("p2", 0.4)], "冷色调", fake)
    assert len(out) == 1
    assert out[0][0] == "p2"
