# 代码阅读引导

> 按什么顺序读、每段代码看什么、读完应该理解什么。

## 阅读路径

```
① parser.py      → 数据模型，152 个 LUT 怎么变成 Preset 对象
② direct_embed.py → 核心：向量检索 + 搜索日志
③ processor.py   → 调色管线：sRGB/Log 双路 + 高光衰减
④ rerank.py      → 规则层语义纠偏
⑤ serve.py       → HTTP API 路由 + 预热
⑥ app.html       → 前端 JavaScript 逻辑
```

---

## ① parser.py — 数据模型

**入口：** `load_presets()` → `parse_presets()`

**重点：**
```python
@dataclass
class Preset:
    id: str                    # 唯一标识（= 文件名去后缀）
    name: str                  # 预设名
    path: Path                 # .cube 文件路径
    color_space: str | None    # "log" | "709"
    lut_type: str | None       # "srgb" | "log_cinema"
    lut_data: ndarray          # (35937, 3) float32 RGB
    lut_size: int              # 33
    contrast/saturation/tone   # "low"|"mid"|"high" / "warm"|"cold"|"neutral"
    ...
```

**关键函数：**
- `read_cube_rgb(path)` → 读 .cube 文件的 33³ RGB 网格
- `infer_color_space()` → 从目录名判断 log/709
- `infer_contrast/saturation/tone()` → 关键词引导元数据

**读完应理解：** 152 个 .cube 文件被解析成 152 个 Preset 对象，每个 Preset 包含 LUT 数据、路径元数据和风格元数据。

---

## ② direct_embed.py — 检索引擎

**核心路径：**
```
build_index()  →  嵌入 152 个预设名 → 存 vectors.npy + ids.txt
search(query)  →  bge-m3(query) → 余弦 vs vectors.npy → 返回 (id, score, index)
```

**数据文件（.lut_vectors/）：**
| 文件 | 内容 |
|------|------|
| `vectors.npy` | (152, 1024) float32，bge-m3 嵌入 |
| `ids.txt` | 152 行，每行一个 preset_id（= name） |
| `texts.txt` | 152 行，搜索文本（name + category + color_space） |

**搜索日志（data/search_log/）：**
```json
{
  "id": "2026-06-21_001",
  "query": "冷淡",
  "query_vector": [0.023, -0.451, ...],
  "top_results": [{"preset_id": "冷白", "score": 0.53, "index": 58}],
  "clicked_preset_id": "冷白",
  "duration_ms": 4320
}
```

**读完应理解：** 从用户输入到向量匹配再到日志落盘的全部数据流。注意 `search()` 只返回原始相似度结果，不做截断和纠偏。

---

## ③ processor.py — 调色管线

**双管线：**

```
用户图片 → sRGB 图片
         │
    ┌────┴────┐
    │ srgb    │ log_cinema
    │         │
    ▼         ▼
直接查表    sRGB→Linear→Log→LUT→Linear→sRGB
    │         │
    └────┬────┘
         ▼
   高光衰减（luma > 0.85 降 R/G）
         ▼
    输出 JPEG
```

**关键函数：**
- `apply_lut(input_path, preset, output_path)` → 主入口
- `_srgb_to_linear()` / `_linear_to_srgb()` → 正确分段 sRGB EOTF/OETF
- `_linear_to_log()` / `_log_to_linear()` → Cineon 风格编码
- `_luma_attenuation()` → 高光保护
- `_apply_lut3d_fast()` → 33³ 三线性插值 (numpy 广播)

**读完应理解：** `lut_type` 决定走哪条管线，为什么 Log LUT 需要完整的色彩空间转换，`_luma_attenuation` 怎么防止溢橙。

---

## ④ rerank.py — 规则纠偏

**一句话：** 在 bge-m3 召回后，用关键词匹配检测用户意图，排除不匹配的预设。

```python
def rule_filter(results, query, preset_cache):
    # 检测 query 意图
    intent["low_contrast"] = "低对比" in query or "对比度低" in query ...
    intent["high_saturation"] = "高饱和" in query or "饱和度高" in query ...
    # 排除不匹配
    for pid, score in results:
        if intent["low_contrast"] and preset.contrast == "high": continue
        if intent["high_saturation"] and preset.saturation == "low": continue
    return filtered[:3]
```

**读完应理解：** 这个模块是纯规则的，零 LLM 调用，仅做字符串匹配 + 字段比较。它解决了 bge-m3 不理解否定修饰的问题。

---

## ⑤ serve.py — HTTP API

**路由表：**

| 路径 | 方法 | 功能 |
|------|------|------|
| `/api/ping` | GET | 健康检查 |
| `/api/stats` | GET | 搜索统计 |
| `/api/search` | POST | 语义搜索 |
| `/api/apply` | POST | 上传图片 + 套 LUT |
| `/api/click` | POST | 回传点击 |
| `/api/preview/{index}` | GET | 生成缩略图 |

**关键管道（search handler）：**
```
search(query, top_n=30)
  → dynamic_cut(max_count=6, min_score=0.4)
  → rule_filter(query, preset_cache)
  → log_search_json(query_vec, ...)
  → 返回 { results, count, ms, search_id }
```

**读完应理解：** 各 API 之间的数据依赖关系，`_preset_cache` 和 `_sorted_presets` 的初始化时机，warmup 做了什么。

---

## ⑥ app.html — 前端逻辑

**JS 函数：**

| 函数 | 触发 | 调用 API |
|------|------|---------|
| `doSearch()` | 点击搜索 / Enter | `POST /api/search` |
| `doApply()` | 点击应用 | `POST /api/apply` |
| `loadStats()` | 页面加载 | `GET /api/stats` |
| `loadNext()` | 搜索完成后 | `GET /api/preview/{index}` |

**读完应理解：** 搜索→选择→应用的完整交互链路。`API_BASE` 的作用（file:// vs http:// ）。预览网格的流式加载如何用 3 路并发控制。

---

## 架构总览

```
用户输入 → bge-m3 嵌入 → 余弦匹配 → dynamic_cut → rule_filter → 日志
                                                              ↓
                                                    前端展示结果 + 预览
                                                              ↓
                                                    上传图片 → apply_lut → JPEG
```

## 数据流

```
vectors.npy  ←  build_index()  ←  presets_to_texts()  ←  parser.py
     ↓
search()  →  dynamic_cut()  →  rule_filter()  →  log_search_json()
     ↓
serve.py search handler
     ↓
前端结果列表 + 预览网格
     ↓
用户选择 + apply_lut() → processor.py → JPEG
```
