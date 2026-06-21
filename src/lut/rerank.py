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
        "low_saturation": any(w in query for w in ["低饱和", "饱和度低", "淡雅"]),
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
            filtered.append((pid, score, idx) if len(item) == 3 else (pid, score))
            continue
        if intent["low_contrast"] and getattr(p, "contrast", None) == "high":
            continue
        if intent["low_saturation"] and getattr(p, "saturation", None) == "high":
            continue
        if intent["warm"] and getattr(p, "tone", None) == "cold":
            continue
        if intent["cold"] and getattr(p, "tone", None) == "warm":
            continue
        filtered.append(item)

    return filtered[:3]
