"""规则层语义纠偏 — 关键词意图检测 + 字段过滤"""


def rule_filter(results: list, query: str, preset_cache: dict) -> list:
    """基于 query 意图关键词过滤 Preset 列表

    results: [(preset_id, score, index), ...]
    query: 用户原始输入
    preset_cache: {preset_id: Preset, ...}

    返回过滤后的列表，最多 3 条
    """
    intent = {
        "low_contrast": any(w in query for w in ["低对比", "对比度低", "柔", "淡"]),
        "high_contrast": any(w in query for w in ["高对比", "对比度高", "清晰"]),
        "low_saturation": any(w in query for w in ["低饱和", "饱和度低", "淡雅"]),
        "high_saturation": any(w in query for w in ["高饱和", "饱和度高", "鲜艳", "饱和度高一"]),
        "warm": any(w in query for w in ["暖", "温暖"]),
        "cold": any(w in query for w in ["冷", "冷白"]),
    }

    filtered = []
    for item in results:
        if len(item) == 3:
            pid, score, idx = item
        else:
            pid, score = item
            idx = 0
        p = preset_cache.get(pid)
        if not p:
            filtered.append(item)
            continue
        cs = getattr(p, "contrast", None)
        sat = getattr(p, "saturation", None)
        tn = getattr(p, "tone", None)
        # 方向排除：用户要低→排除高；用户要高→排除低
        if intent["low_contrast"] and cs == "high":
            continue
        if intent["high_contrast"] and cs == "low":
            continue
        if intent["low_saturation"] and sat == "high":
            continue
        if intent["high_saturation"] and sat == "low":
            continue
        if intent["warm"] and tn == "cold":
            continue
        if intent["cold"] and tn == "warm":
            continue
        filtered.append(item)

    return filtered[:3]
