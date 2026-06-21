# Rule Rerank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在搜索管道中插入规则过滤层，用 Preset 的 contrast/saturation/tone 字段排除意图不匹配的结果

**Architecture:** parser.py 中 Preset 新增 metadata 字段 + 关键词推断函数；serve.py search handler 中 dynamic_cut 后插入 rule_filter

**Tech Stack:** Python 3.11 + numpy

---

## File Map

| 文件 | 职责 |
|------|------|
| `src/lut/parser.py` | Preset 新增 contrast/saturation/tone 字段 + infer_* 函数 |
| `src/lut/rerank.py` | `rule_filter()` 函数（独立模块，方便测试） |
| `serve.py` | search handler 中插入 rule_filter 调用 |
| `tests/test_rerank.py` | 新测试文件 |

---

### Task 1: parser.py — Preset 新增字段 + 关键词推断

**Files:**
- Modify: `src/lut/parser.py`
- Test: `tests/test_rerank.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_rerank.py

from lut.parser import infer_contrast, infer_saturation, infer_tone, load_presets

def test_infer_contrast_low():
    assert infer_contrast("淡雅cold", "FAKE5207&淡雅") == "low"
    assert infer_contrast("film matte", "电影感") == "low"

def test_infer_contrast_high():
    assert infer_contrast("人像绿调（高对比）", "人像系列") == "high"
    assert infer_contrast("CINE crush", "CINE系列") == "high"

def test_infer_contrast_mid():
    assert infer_contrast("WARM暖调", "电影感") == "mid"

def test_infer_saturation_low():
    assert infer_saturation("低饱和冷", "电影感") == "low"
    assert infer_saturation("淡雅cold", "FAKE5207&淡雅") == "low"

def test_infer_saturation_mid():
    assert infer_saturation("WARM暖调", "电影感") == "mid"

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
    """所有 152 个预设都有 contrast/saturation/tone 字段"""
    presets = load_presets()
    assert len(presets) == 152
    for p in presets:
        assert p.contrast in ("low", "mid", "high")
        assert p.saturation in ("low", "mid", "high")
        assert p.tone in ("warm", "cold", "neutral")
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_rerank.py::test_infer_contrast_low -v
```
Expected: FAIL (ImportError: infer_contrast not defined)

- [ ] **Step 3: parser.py 追加字段和推断函数**

在 `Preset` dataclass 末尾追加：

```python
    contrast: Optional[str] = None   # "low" | "mid" | "high"
    saturation: Optional[str] = None  # "low" | "mid" | "high"
    tone: Optional[str] = None        # "warm" | "cold" | "neutral"
```

在 `parse_presets()` 中、`presets.append(Preset(...))` 前追加：

```python
    contrast = infer_contrast(name, category)
    saturation = infer_saturation(name, category)
    tone = infer_tone(name, category)
```

在 Preset 调用中追加三个字段。

在 `infer_category()` 函数后、`read_cube_rgb()` 前追加三个推断函数：

```python
def infer_contrast(name: str, category: Optional[str]) -> str:
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["低对比", "淡", "柔", "matte", "fade", "paste", "低饱和"]):
        return "low"
    if any(k in text for k in ["高对比", "强对比", "crush", "硬"]):
        return "high"
    return "mid"


def infer_saturation(name: str, category: Optional[str]) -> str:
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["低饱和", "淡雅", "fade", "matte", "clean"]):
        return "low"
    if any(k in text for k in ["高饱和", "鲜艳"]):
        return "high"
    return "mid"


def infer_tone(name: str, category: Optional[str]) -> str:
    text = (name + " " + (category or "")).lower()
    if any(k in text for k in ["暖", "温暖", "warm"]):
        return "warm"
    if any(k in text for k in ["冷", "冷白", "cool"]):
        return "cold"
    if any(k in text for k in ["中性", "自然", "标准", "standard"]):
        return "neutral"
    return "neutral"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_rerank.py -v
```
Expected: 10 PASS

- [ ] **Step 5: 运行全测试集验证 0 回归**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add src/lut/parser.py tests/test_rerank.py && git commit -m "feat: add contrast/saturation/tone metadata to Preset with keyword inference"
```

---

### Task 2: rerank.py — rule_filter 函数

**Files:**
- Create: `src/lut/rerank.py`
- Test: `tests/test_rerank.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_rerank.py — 尾部追加

from lut.rerank import rule_filter

def test_rule_filter_exclude_high_contrast():
    """低对比意图排除高对比预设"""
    fake_cache = {
        "p1": type("obj", (object,), {"contrast": "high", "saturation": "mid", "tone": "neutral"})(),
        "p2": type("obj", (object,), {"contrast": "low", "saturation": "mid", "tone": "neutral"})(),
    }
    results = [("p1", 0.5, 0), ("p2", 0.4, 1)]
    filtered = rule_filter(results, "对比度低一点", fake_cache)
    assert len(filtered) == 1
    assert filtered[0][0] == "p2"

def test_rule_filter_no_intent():
    """无意图关键词时不排除"""
    fake_cache = {
        "p1": type("obj", (object,), {"contrast": "high", "saturation": "mid", "tone": "neutral"})(),
    }
    filtered = rule_filter([("p1", 0.5, 0)], "电影感胶片", fake_cache)
    assert len(filtered) == 1

def test_rule_filter_limit_3():
    """超过 3 个取前 3"""
    fake_cache = {}
    for i in range(5):
        fake_cache[f"p{i}"] = type("obj", (object,), {"contrast": "mid", "saturation": "mid", "tone": "neutral"})()
    results = [(f"p{i}", 0.5 - i*0.01, i) for i in range(5)]
    filtered = rule_filter(results, "冷淡", fake_cache)
    assert len(filtered) == 3

def test_rule_filter_missing_preset():
    """cache 找不到的预设不崩溃，直接保留"""
    filtered = rule_filter([("unknown", 0.5, 0)], "冷淡", {"other": None})
    assert len(filtered) == 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_rerank.py::test_rule_filter_exclude_high_contrast -v
```
Expected: FAIL (ImportError)

- [ ] **Step 3: 创建 src/lut/rerank.py**

```python
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
    for pid, score, idx in results:
        p = preset_cache.get(pid)
        if not p:
            filtered.append((pid, score, idx))
            continue
        if intent["low_contrast"] and getattr(p, "contrast", None) == "high":
            continue
        if intent["low_saturation"] and getattr(p, "saturation", None) == "high":
            continue
        if intent["warm"] and getattr(p, "tone", None) == "cold":
            continue
        if intent["cold"] and getattr(p, "tone", None) == "warm":
            continue
        filtered.append((pid, score, idx))

    return filtered[:3]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_rerank.py::test_rule_filter_exclude_high_contrast tests/test_rerank.py::test_rule_filter_no_intent tests/test_rerank.py::test_rule_filter_limit_3 tests/test_rerank.py::test_rule_filter_missing_preset -v
```
Expected: 4 PASS

- [ ] **Step 5: 全测试通过**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add src/lut/rerank.py tests/test_rerank.py && git commit -m "feat: add rule_filter for intent-based preset exclusion"
```

---

### Task 3: serve.py — search handler 插入 rule_filter

**Files:**
- Modify: `serve.py`

- [ ] **Step 1: 修改 serve.py**

在 import 块追加：

```python
from lut.rerank import rule_filter
```

在 search handler 中、`dynamic_cut` 之后、`log_search_json` 之前插入：

```python
                cut = dynamic_cut([(pid, s) for pid, s, _ in raw_results], max_count=6, min_score=0.4)
                cut = rule_filter(cut, query, _preset_cache)  # ← 插入
```

- [ ] **Step 2: 语法检查**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -c "import serve"
```
Expected: no errors

- [ ] **Step 3: 全测试通过**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add serve.py && git commit -m "feat: wire rule_filter into search pipeline"
```

---

## Self-Review

- [ ] **Spec coverage**: 
  - Preset 新字段 contrast/saturation/tone ✅ (Task 1)
  - 关键词推断函数 ✅ (Task 1)
  - rule_filter 函数 ✅ (Task 2)
  - 搜索管道插入 ✅ (Task 3)
  - top-3 限制 ✅ (Task 2)
- [ ] **Placeholder check**: 无 TBD/TODO
- [ ] **Type consistency**: contrast/saturation/tone 都是 str | None，infer_* 返回 str，rule_filter 用 getattr 防御
