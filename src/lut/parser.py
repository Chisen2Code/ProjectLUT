"""
.cube LUT 文件解析器

.cube 文件本身只有色彩转换数据（33³ RGB 浮点三元组），预设的语义信息
全部编码在目录结构和文件名中。本模块负责：

1. 遍历 LUT 预设目录，提取所有 .cube 文件路径
2. 从路径中解析：预设名称、色彩空间(log/709)、所属合集、风格类别
3. 返回标准化的 Preset 数据结构
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

# ── 数据模型 ──────────────────────────────────────────────


@dataclass
class Preset:
    """单个 LUT 预设的结构化描述"""

    name: str  # 干净名称（同时也是唯一标识 id）
    filename: str  # 原始文件名（含 .cube）
    path: Path  # 绝对路径
    id: str = ""  # 唯一标识，默认用 name
    color_space: Optional[str] = None  # "log" | "709" | None(未知)
    collection: Optional[str] = None  # 所属合集
    category: Optional[str] = None  # 风格类别
    sub_category: Optional[str] = None  # 子类别
    original_author: str = "林馆长"  # 原作者
    lut_data: Optional[np.ndarray] = None  # (35937, 3) RGB float
    lut_size: int = 0                       # 33
    lut_type: Optional[str] = None          # "srgb" | "log_cinema" | None
    domain_min: Optional[tuple[float, float, float]] = None
    domain_max: Optional[tuple[float, float, float]] = None
    contrast: Optional[str] = None     # "low" | "mid" | "high"
    saturation: Optional[str] = None   # "low" | "mid" | "high"
    tone: Optional[str] = None         # "warm" | "cold" | "neutral"

    def to_search_text(self) -> str:
        """生成用于向量嵌入的搜索文本"""
        parts = [self.name]
        if self.category:
            parts.append(self.category)
        if self.sub_category:
            parts.append(self.sub_category)
        if self.color_space:
            parts.append(self.color_space.upper())
        return " — ".join(parts)


# ── 解析逻辑 ──────────────────────────────────────────────


def infer_color_space(dirname: str) -> Optional[str]:
    """从目录名推断色彩空间"""
    d = dirname.lower()
    if "log" in d and "709" not in d:
        return "log"
    if "709" in d or "rec709" in d:
        return "709"
    return None


def infer_category(dirname: str) -> Optional[str]:
    """从目录名推断风格类别"""
    mapping = {
        "电影": "电影感",
        "胶片": "胶片系列",
        "vintage": "复古VINTAGE",
        "阿勒泰": "阿勒泰系列",
        "cine": "CINE系列",
        "fake5207": "FAKE5207&淡雅",
        "淡雅": "FAKE5207&淡雅",
        "人像": "人像系列",
        "繁花": "繁花仿色",
        "富士": "富士改款",
        "柯达": "柯达系列",
        "nikon": "柯达系列",
    }
    for k, v in mapping.items():
        if k in dirname.lower():
            return v
    return None


def infer_contrast(name: str, category: Optional[str]) -> str:
    """从预设名称和类别推断对比度"""
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["低对比", "淡", "柔", "matte", "fade", "paste", "低饱和"]):
        return "low"
    if any(k in text for k in ["高对比", "强对比", "crush", "硬"]):
        return "high"
    return "mid"


def infer_saturation(name: str, category: Optional[str]) -> str:
    """从预设名称和类别推断饱和度"""
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["低饱和", "淡雅", "fade", "matte", "clean"]):
        return "low"
    if any(k in text for k in ["高饱和", "鲜艳"]):
        return "high"
    return "mid"


def infer_tone(name: str, category: Optional[str]) -> str:
    """从预设名称和类别推断色温"""
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["暖", "温暖", "warm"]):
        return "warm"
    if any(k in text for k in ["冷", "冷白", "cool"]):
        return "cold"
    if any(k in text for k in ["中性", "自然", "标准", "standard"]):
        return "neutral"
    return "neutral"


def read_cube_rgb(path: Path) -> tuple:
    """读取 .cube 文件的 3D LUT 数据（纯 numpy 实现，无需 colour-science）

    返回 (data, size, domain_min, domain_max)
    data: (N,3) float32 or None
    size: int (33 等)
    domain_min/domain_max: tuple(float,float,float) or None
    """
    try:
        size = 0
        rows = []
        domain_min = domain_max = None
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                ul = line.upper()
                if ul.startswith("TITLE"):
                    continue
                if ul.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[1])
                    continue
                if ul.startswith("DOMAIN_MIN"):
                    parts = line.split()
                    if len(parts) >= 4:
                        domain_min = (float(parts[1]), float(parts[2]), float(parts[3]))
                    continue
                if ul.startswith("DOMAIN_MAX"):
                    parts = line.split()
                    if len(parts) >= 4:
                        domain_max = (float(parts[1]), float(parts[2]), float(parts[3]))
                    continue
                if ul.startswith("DOMAIN"):
                    continue
                # 数据行：3 个浮点数
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
        if size == 0 or len(rows) < size ** 3:
            return None, 0, None, None
        data = np.array(rows[: size ** 3], dtype=np.float32)
        return data, size, domain_min, domain_max
    except Exception:
        return None, 0, None, None


def parse_presets(root_dir: str | Path) -> List[Preset]:
    """
    解析 LUT 预设目录，返回所有预设的结构化列表。

    Args:
        root_dir: LUT预设1/ 目录路径

    Returns:
        按名称排序的 Preset 列表
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"LUT 预设目录不存在: {root_dir}")

    presets = []
    for cube_file in sorted(root.rglob("*.cube")):
        filename = cube_file.name
        name = Path(filename).stem  # 文件名去 .cube 即为预设名称
        lut_data, lut_size, domain_min, domain_max = read_cube_rgb(cube_file)

        # 解析路径层级
        parts = cube_file.relative_to(root).parts
        # parts[0] = 顶级合集目录，parts[1:-1] = 子目录，parts[-1] = 文件名

        collection = parts[0] if len(parts) > 0 else None

        # 从所有路径层级推断色彩空间和类别
        color_space = None
        category = None
        sub_category = None

        for part in parts[:-1]:  # 忽略文件名部分
            cs = infer_color_space(part)
            if cs:
                color_space = cs
            cat = infer_category(part)
            if cat and not category:
                category = cat
            elif cat and category:
                sub_category = cat

        # 目录名（去数字前缀）作为 fallback category
        dir_names = [re.sub(r"^\d+\.\s*", "", p) for p in parts[:-1]]

        # lut_type 推导：color_space → 两类 LUT
        if color_space == "log":
            lut_type = "log_cinema"
        else:
            lut_type = "srgb"  # "709" 或 None 都保守视为 sRGB 可用

        # 规则层 metadata
        cat_for_infer = category or (dir_names[-1] if dir_names else None)
        contrast = infer_contrast(name, cat_for_infer)
        saturation = infer_saturation(name, cat_for_infer)
        tone = infer_tone(name, cat_for_infer)

        presets.append(Preset(
            id=name,
            name=name,
            filename=filename,
            path=cube_file,
            color_space=color_space,
            collection=collection,
            category=category or (dir_names[-1] if dir_names else None),
            sub_category=sub_category,
            lut_data=lut_data,
            lut_size=lut_size,
            lut_type=lut_type,
            domain_min=domain_min,
            domain_max=domain_max,
            contrast=contrast,
            saturation=saturation,
            tone=tone,
        ))

    return sorted(presets, key=lambda p: p.name)


# ── 快捷函数 ──────────────────────────────────────────────


def load_presets(root_dir: str | Path = "LUT预设1") -> List[Preset]:
    """加载 LUT预设1/ 下所有预设（便捷入口）"""
    return parse_presets(root_dir)


def presets_to_texts(presets: List[Preset]) -> List[str]:
    """将预设列表转为向量嵌入用的文本列表"""
    return [p.to_search_text() for p in presets]


# ── CLI 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "LUT预设1"
    presets = load_presets(root)
    print(f"解析完成: {len(presets)} 个 LUT 预设\n")

    # 统计
    from collections import Counter

    cs = Counter(p.color_space for p in presets)
    cat = Counter(p.category for p in presets)
    print(f"色彩空间: {dict(cs)}")
    print(f"风格类别: {dict(cat)}\n")

    # 示例输出
    for p in presets[:5]:
        print(f"  {p.name:30s} | {p.color_space or '?':>4s} | {p.category or '?'}")
    print(f"  ... 共 {len(presets)} 个")
