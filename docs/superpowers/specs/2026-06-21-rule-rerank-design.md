# 规则层语义纠偏 — 设计文档

## 概述

bge-m3 嵌入不理解否定修饰（「对比度低一点」匹配到「高对比」），在搜索管道中插入纯规则过滤层，不做 LLM 调用。

## 架构

```
用户 query
    │
    ▼
bge-m3 search → dynamic_cut → top-6
    │                           │
    │                    规则过滤（意图检测 + 排除）
    │                           │
    │                    返回 top-3
```

规则层零外部依赖（无 Ollama 调用），只有字符串匹配和字段比较。

## Preset 新增字段

`parser.py` — `Preset` dataclass 追加：

```python
contrast: Optional[str] = None    # "low" | "mid" | "high"
saturation: Optional[str] = None  # "low" | "mid" | "high"
tone: Optional[str] = None        # "warm" | "cold" | "neutral"
```

## 关键词引导初始化

`parser.py` — 新增三个推断函数，在 `parse_presets()` 中调用：

### `infer_contrast(name, category)`

| 关键词 | 判定 |
|--------|------|
| 低对比、淡、柔、matte、fade、paste、低饱和 | `"low"` |
| 高对比、强对比、crush、cinema、硬 | `"high"` |
| 无匹配 | `"mid"` |

### `infer_saturation(name, category)`

| 关键词 | 判定 |
|--------|------|
| 低饱和、淡雅、fade、matte、clean | `"low"` |
| 高饱和、鲜艳、饱和 | `"high"` |
| 无匹配 | `"mid"` |

### `infer_tone(name, category)`

| 关键词 | 判定 |
|--------|------|
| 暖、温馨、温暖、warm | `"warm"` |
| 冷、冷白、cool、冷调 | `"cold"` |
| 中性、自然、标准 | `"neutral"` |
| 无匹配 | `"neutral"` |

## 规则过滤函数

`serve.py` — 新增 `rule_filter(results, query, preset_cache)`：

```python
def rule_filter(results, query, preset_cache):
    intent = {
        "low_contrast": any(w in query for w in ["低对比", "对比度低", "柔", "淡"]),
        "low_saturation": any(w in query for w in ["低饱和", "饱和度低", "淡雅"]),
        "warm": any(w in query for w in ["暖", "温暖"]),
        "cold": any(w in query for w in ["冷", "冷白"]),
    }

    filtered = []
    for pid, score, idx in results:
        p = preset_cache.get(pid)
        if not p:
            filtered.append((pid, score, idx))
            continue
        if intent["low_contrast"] and p.contrast == "high":
            continue
        if intent["low_saturation"] and p.saturation == "high":
            continue
        if intent["warm"] and p.tone == "cold":
            continue
        if intent["cold"] and p.tone == "warm":
            continue
        filtered.append((pid, score, idx))

    return filtered[:3]
```

规则写死、无配置、无外部依赖。后续需扩展意图时加关键词即可。

## 管道插入点

在 `serve.py` search handler 中，`dynamic_cut()` 之后、`log_search_json()` 之前：

```python
cut = dynamic_cut(...)
cut = rule_filter(cut, query, _preset_cache)  # ← 插入
sid = log_search_json(query, query_vec, cut, ms)
```

## 测试

`tests/test_processor.py` 或新建 `tests/test_rerank.py`：

| 测试 | 验证 |
|------|------|
| `test_infer_contrast_low` | "淡雅cold" → contrast=low |
| `test_infer_contrast_high` | "高对比CINE" → contrast=high |
| `test_rule_filter_exclude_high` | "低对比" query 排除 high_contrast 预设 |
| `test_rule_filter_no_match` | 无意图关键词时全部通过 |
| `test_rule_filter_limit` | 超过 3 个取前 3 |

## 不动

- `direct_embed.py` 无改动
- `app.html` 无改动
- 无新依赖
- 无 LLM 调用

## 验证

```bash
# 搜索「对比度低一点」不应再返回「高对比」类 LUT
curl -s --connect-timeout 15 -X POST http://localhost:8765/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"对比度低一点"}'
# 期望：top 无「高对比」相关结果
```
