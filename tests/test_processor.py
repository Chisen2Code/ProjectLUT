"""processor.py 验收测试"""
import numpy as np
from pathlib import Path
from PIL import Image
from lut.parser import load_presets
from lut.processor import apply_lut

PRESETS = load_presets()
TEST_DIR = Path("tests")


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


def test_apply_709_preset():
    """709 LUT 套用后尺寸不变，像素值有效"""
    # Make a test image
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    test_in = str(TEST_DIR / "test_in.jpg")
    img.save(test_in)

    p = [x for x in PRESETS if x.color_space == "709"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(test_in, p, out)

    result = Image.open(out)
    assert result.size == img.size
    arr = np.array(result)
    assert arr.min() >= 0 and arr.max() <= 255
    result.close()
    Path(out).unlink()
    Path(test_in).unlink()


def test_apply_log_preset():
    """log LUT 套用（含转换）后尺寸不变"""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    test_in = str(TEST_DIR / "test_log_in.jpg")
    img.save(test_in)

    p = [x for x in PRESETS if x.color_space == "log"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(test_in, p, out)

    result = Image.open(out)
    assert result.size == img.size
    result.close()
    Path(out).unlink()
    Path(test_in).unlink()
