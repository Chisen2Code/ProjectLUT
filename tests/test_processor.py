"""processor.py 验收测试 — 裁切检测 + 色彩丰富度比值"""
import numpy as np
from pathlib import Path
from PIL import Image
from lut.parser import load_presets
from lut.processor import apply_lut

PRESETS = load_presets()
TEST_DIR = Path("tests")


# ── 色彩验证辅助函数（轻量方案） ──────────────────────────────

def _clipping_ratio(img: np.ndarray, channel: int = 0, threshold: int = 252) -> float:
    """R 通道裁切比例 —— 直接检测溢橙"""
    return float((img[..., channel] >= threshold).mean())


def _colorfulness(img: np.ndarray) -> float:
    """Hasler & Susstrunk M3 色彩丰富度指标（完全 RGB 域）"""
    rg = np.abs(img[..., 0].astype(np.float64) - img[..., 1].astype(np.float64))
    yb = np.abs(0.5 * (img[..., 0].astype(np.float64) + img[..., 1].astype(np.float64))
                - img[..., 2].astype(np.float64))
    return float(np.sqrt(rg.std()**2 + yb.std()**2) + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2))


def _validate_color_output(before: np.ndarray, after: np.ndarray,
                           max_clip_r: float = 0.03, max_cf_ratio: float = 1.5) -> dict:
    """色彩验证综合判断 — 聚焦 R 通道裁切（溢橙信号）

    溢橙判据：
      - R 通道裁切比例 < max_clip_r（R 到 255 说明橙/红色饱和溢出）
      - 色彩丰富度比值 < max_cf_ratio（饱和度暴增说明异常）
    """
    clip_r = _clipping_ratio(after, channel=0)
    clip_g = _clipping_ratio(after, channel=1)
    clip_b = _clipping_ratio(after, channel=2)
    cf_before = _colorfulness(before)
    cf_after = _colorfulness(after)
    cf_ratio = cf_after / cf_before if cf_before > 0 else 0.0
    ok = clip_r < max_clip_r and cf_ratio < max_cf_ratio
    return {
        "pass": ok,
        "clip_r": clip_r, "clip_g": clip_g, "clip_b": clip_b,
        "cf_before": cf_before, "cf_after": cf_after, "cf_ratio": cf_ratio,
    }


# ── 测试用例 ────────────────────────────────────────────────

def test_all_152_readable():
    """所有 .cube 可解析 RGB"""
    assert len(PRESETS) == 152
    for p in PRESETS:
        assert p.lut_data is not None, f"{p.name} 无 RGB 数据"
        assert p.lut_size == 33, f"{p.name} size={p.lut_size}"


def test_color_space_counts():
    """色彩空间统计正确"""
    log_count = sum(1 for p in PRESETS if p.color_space == "log")
    rec709_count = sum(1 for p in PRESETS if p.color_space == "709")
    assert log_count == 74, f"log={log_count}"
    assert rec709_count == 68, f"709={rec709_count}"


def test_lut_type_counts():
    """lut_type 分类正确"""
    srgb = sum(1 for p in PRESETS if p.lut_type == "srgb")
    log = sum(1 for p in PRESETS if p.lut_type == "log_cinema")
    assert srgb == 78, f"srgb={srgb}"   # 68 (709) + 10 (None)
    assert log == 74, f"log_cinema={log}"


def test_apply_709_preset():
    """709 LUT 套用后无溢橙"""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img)
    test_in = str(TEST_DIR / "test_in.jpg")
    pil_img.save(test_in)

    p = [x for x in PRESETS if x.color_space == "709"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(test_in, p, out)

    result = np.array(Image.open(out))
    assert result.shape == (100, 100, 3)

    v = _validate_color_output(img.astype(np.float64), result.astype(np.float64))
    assert v["pass"], (
        f"709 LUT 溢橙: clip_r={v['clip_r']:.4f}, "
        f"cf_ratio={v['cf_ratio']:.3f}"
    )
    Path(out).unlink()
    Path(test_in).unlink()


def test_apply_log_preset():
    """Log LUT 套用后溢橙已修复（新管线验证）"""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    pil_img = Image.fromarray(img)
    test_in = str(TEST_DIR / "test_log_in.jpg")
    pil_img.save(test_in)

    p = [x for x in PRESETS if x.color_space == "log"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(test_in, p, out)

    result = np.array(Image.open(out))
    assert result.shape == (100, 100, 3)

    v = _validate_color_output(img.astype(np.float64), result.astype(np.float64))
    assert v["pass"], (
        f"Log LUT 溢橙: clip_r={v['clip_r']:.4f}, "
        f"cf_ratio={v['cf_ratio']:.3f}"
    )
    print(f"  [log] clip_r={v['clip_r']:.4f}, cf_ratio={v['cf_ratio']:.3f}")
    Path(out).unlink()
    Path(test_in).unlink()


def test_log_gif_rejected():
    """Log LUT + .gif 抛 ValueError"""
    img = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
    test_in = str(TEST_DIR / "test_gif_in.png")
    img.save(test_in)

    p = [x for x in PRESETS if x.color_space == "log"][0]
    import pytest
    with pytest.raises(ValueError, match="不适用于 GIF"):
        apply_lut(test_in, p, str(TEST_DIR / "out.gif"))
    Path(test_in).unlink()


def test_attenuation_highlights():
    """纯白输入经衰减后 R < 1.0"""
    from lut.processor import _luma_attenuation
    white = np.ones((10, 10, 3), dtype=np.float32)
    result = _luma_attenuation(white)
    assert result[0, 0, 0] < 1.0     # R 衰减
    assert result[0, 0, 1] < 1.0     # G 衰减
    assert result[0, 0, 2] == 1.0    # B 不动
