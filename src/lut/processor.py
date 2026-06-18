"""
LUT 处理器 — 读取图片，套 3D LUT，输出调色结果。
纯 numpy + Pillow 实现，无需 colour-science。

性能优化:
- 进程内缓存 LUT 的 (r,g,b,channeltable_4d_rgb，避免重复 reshape/transpose
- 图片最大边限制 1600，加速
- 直接在 LUT 应用时统一 float32 + numpy 广播计算
"""
import time
import numpy as np
from PIL import Image

from .parser import load_presets, Preset

# LUT table 进程内缓存
_LUT_CACHE = {}  # preset_name -> table_4d_rgb


def _get_cached_lut(preset: Preset) -> np.ndarray:
    """获取预设的 table_4d_rgb（缓存加速多次调用）"""
    if preset.name in _LUT_CACHE:
        return _LUT_CACHE[preset.name]

    if preset.lut_data is None:
        raise ValueError(f"预设 {preset.name} 缺少 LUT 数据")
    s = preset.lut_size
    # .cube 数据顺序: r 最快 → g → b
    table_bgr = preset.lut_data.reshape(s, s, s, 3)  # [b, g, r, channel]
    table_rgb = np.ascontiguousarray(table_bgr.transpose(2, 1, 0, 3), dtype=np.float32)
    _LUT_CACHE[preset.name] = table_rgb
    return table_rgb


def _log_to_709(img_rgb: np.ndarray) -> np.ndarray:
    """log → 709 gamma approximation（直接用 float32 优化）"""
    linear = np.power(np.clip(img_rgb, 0.0, 1.0, dtype=np.float32), 2.2)
    return np.power(linear, 1 / 2.2, dtype=np.float32)


def _apply_lut3d_fast(img_rgb: np.ndarray, table_4d_rgb: np.ndarray) -> np.ndarray:
    """
    快速 3D LUT 三线性插值 —— numpy 广播优化。
    输入: img_rgb (H, W, 3) float32 [0,1]
           table_4d_rgb (S, S, S, 3) float32
    返回: (H, W, 3) float32 [0,1]
    """
    s = table_4d_rgb.shape[0]
    # 映射到 [0, s-1] 浮点坐标
    scaled = np.clip(img_rgb, 0.0, 1.0) * (s - 1)
    idx_floor = np.floor(scaled).astype(np.int32)
    frac = (scaled - idx_floor).astype(np.float32)
    idx_ceil = np.minimum(idx_floor + 1, s - 1)

    # 取8个角点值: shape (H, W, 3)
    r0, r1 = idx_floor[..., 0], idx_ceil[..., 0]
    g0, g1 = idx_floor[..., 1], idx_ceil[..., 1]
    b0, b1 = idx_floor[..., 2], idx_ceil[..., 2]

    fr = frac[..., 0:1]  # (H, W, 1)
    fg = frac[..., 1:2]
    fb = frac[..., 2:3]

    # 广播插值: 在 r 方向
    c00 = table_4d_rgb[r0, g0, b0] * (1 - fr) + table_4d_rgb[r1, g0, b0] * fr
    c10 = table_4d_rgb[r0, g1, b0] * (1 - fr) + table_4d_rgb[r1, g1, b0] * fr
    c01 = table_4d_rgb[r0, g0, b1] * (1 - fr) + table_4d_rgb[r1, g0, b1] * fr
    c11 = table_4d_rgb[r0, g1, b1] * (1 - fr) + table_4d_rgb[r1, g1, b1] * fr
    # g 方向
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    # b 方向
    result = c0 * (1 - fb) + c1 * fb
    return result


MAX_SIDE = 1600  # 图片最大边，超过则等比缩小加速


def _resize_if_needed(img: Image.Image) -> Image.Image:
    """大图等比缩小，最大边 MAX_SIDE"""
    w, h = img.size
    if max(w, h) <= MAX_SIDE:
        return img
    scale = MAX_SIDE / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)


def apply_lut(input_path: str, preset: Preset, output_path: str) -> str:
    """
    套 LUT 到图片。
    """
    table_rgb = _get_cached_lut(preset)

    img = Image.open(input_path).convert("RGB")
    img = _resize_if_needed(img)
    img_rgb = np.asarray(img, dtype=np.float32) / 255.0

    if preset.color_space == "log":
        img_rgb = _log_to_709(img_rgb)

    t0 = time.perf_counter()
    result = _apply_lut3d_fast(img_rgb, table_rgb)
    result = np.clip(result, 0.0, 1.0)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    result_img = Image.fromarray((result * 255).astype(np.uint8))
    result_img.save(output_path)
    print(f"  LUT 应用: {elapsed_ms}ms, 尺寸={img.size}")
    return output_path


# 启动时预加载常用LUT — 缓存全部 152 个预设，大幅提速
def preload_all_luts():
    presets = load_presets()
    for p in presets:
        try:
            _get_cached_lut(p)
        except Exception:
            pass
    print(f"[LUT] 已缓存 {len(_LUT_CACHE)} 个 LUT table")
