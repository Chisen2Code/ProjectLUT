"""parser.py 单元测试"""
import numpy as np
from pathlib import Path
from lut.parser import load_presets, parse_presets, read_cube_rgb, infer_color_space, infer_category, Preset


def test_load_presets_count():
    """parse_presets 返回 152 个预设"""
    presets = load_presets()
    assert len(presets) == 152


def test_infer_color_space_log():
    assert infer_color_space("iPhone 标准版合集1(log)") == "log"
    assert infer_color_space("各机型LOG") == "log"


def test_infer_color_space_709():
    assert infer_color_space("iPhone 标准版合集1(REC709)") == "709"
    assert infer_color_space("709专用（不拍灰片用这个）") == "709"


def test_infer_category():
    assert infer_category("林馆长电影感系列lut") == "电影感"
    assert infer_category("胶片各机型log灰片") == "胶片系列"
    assert infer_category("富士LUT改款") == "富士改款"


def test_read_cube_rgb_shape():
    """read_cube_rgb 返回 (35937, 3) 及 domain 信息"""
    cube_path = Path("LUT预设1/LUT全系打包/2024-VINTAGE系列lut/log灰片格式使用/gentle复古暖.cube")
    if cube_path.exists():
        data, size, domain_min, domain_max = read_cube_rgb(cube_path)
        assert size == 33
        assert data.shape == (35937, 3)
        assert data.dtype == np.float32
        assert domain_min is None  # 当前 LUT 库无 DOMAIN header
        assert domain_max is None


def test_preset_dataclass():
    """Preset 包含所有必要字段"""
    presets = load_presets()
    p = presets[0]
    assert isinstance(p.name, str) and len(p.name) > 0
    assert isinstance(p.filename, str) and p.filename.endswith(".cube")
    assert p.lut_data is not None
    assert p.lut_size == 33
    assert p.color_space in ("log", "709", None)
    assert p.lut_type in ("srgb", "log_cinema")
    assert p.domain_min is None  # 当前库无 DOMAIN header
    assert p.domain_max is None
    assert isinstance(p.id, str) and len(p.id) > 0
    assert p.id == p.name  # id == name == 文件名去后缀
