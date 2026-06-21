# Search Analytics v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搜索日志固化为 JSON、动态截断、点击追踪、百图预览

**Architecture:** direct_embed.py 中新增 JSON 日志函数和动态截断算法，serve.py 拓展 API 端点，app.html 增强状态显示和预览网格

**Tech Stack:** Python 3.11 + numpy + JSON 文件存储

---

## File Map

| 文件 | 职责 |
|------|------|
| `src/lut/direct_embed.py` | `dynamic_cut()`, `log_search_json()`, `log_click()`, 更新 `search()` 返回 index |
| `serve.py` | `/api/search` 返回 search_id+count, `/api/click`, `/api/preview/{index}` |
| `app.html` | ⚡状态条, 点击回传 search_id, 预览网格 |
| `tests/test_direct_embed.py` | 动态截断测试集、JSON 日志测试集 |
| `docs/superpowers/specs/2026-06-21-search-analytics-v2-design.md` | 设计文档 |

---

### Task 1: 动态截断 `dynamic_cut()` 函数

**Files:**
- Modify: `src/lut/direct_embed.py` (末尾新增函数)
- Test: `tests/test_direct_embed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_direct_embed.py — 尾部追加

from lut.direct_embed import dynamic_cut

def test_dynamic_cut_normal():
    """正常梯度：陡降前都保留"""
    scores = [(f"p{i}", s) for i, s in enumerate([0.62, 0.55, 0.48, 0.42, 0.35, 0.31, 0.18, 0.12])]
    result = dynamic_cut(scores)
    assert len(result) == 6
    assert result[-1][0] == "p5"  # 0.31

def test_dynamic_cut_steep():
    """陡降：0.55→0.25, 截断在第二个"""
    scores = [(f"p{i}", s) for i, s in enumerate([0.62, 0.55, 0.25, 0.12])]
    result = dynamic_cut(scores)
    assert len(result) == 2

def test_dynamic_cut_below_min():
    """全低于 0.3 → 空"""
    scores = [(f"p{i}", s) for i, s in enumerate([0.25, 0.12])]
    result = dynamic_cut(scores)
    assert result == []

def test_dynamic_cut_single():
    """单结果"""
    scores = [("p0", 0.62)]
    result = dynamic_cut(scores)
    assert len(result) == 1

def test_dynamic_cut_empty():
    """空输入"""
    result = dynamic_cut([])
    assert result == []

def test_dynamic_cut_max_cap():
    """超过上限只取 10 个"""
    scores = [(f"p{i}", 0.9 - i*0.02) for i in range(15)]
    result = dynamic_cut(scores, max_count=10)
    assert len(result) == 10

def test_dynamic_cut_edge_drop():
    """陡降恰好等于 threshold，不截断"""
    scores = [(f"p{i}", s) for i, s in enumerate([0.50, 0.36])]  # 0.50-0.36=0.14 < 0.15
    result = dynamic_cut(scores, drop_threshold=0.15)
    assert len(result) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_dynamic_cut_normal -v
```
Expected: FAIL (ImportError: dynamic_cut not defined)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lut/direct_embed.py — 末尾追加

def dynamic_cut(results: list[tuple[str, float]], min_score: float = 0.3,
                max_count: int = 10, drop_threshold: float = 0.15) -> list[tuple[str, float]]:
    """动态截断：绝对阈值 + 陡降检测 + 上限"""
    if not results:
        return []

    # 按 score 降序排列
    sorted_r = sorted(results, key=lambda x: x[1], reverse=True)
    # 过滤低于阈值的
    filtered = [(n, s) for n, s in sorted_r if s >= min_score]

    if not filtered:
        return []

    # 陡降检测：从第 2 个开始，如果与前一个差距 > drop_threshold 则截断
    cut_idx = len(filtered)
    for i in range(1, len(filtered)):
        if filtered[i-1][1] - filtered[i][1] > drop_threshold:
            cut_idx = i
            break

    return filtered[:min(cut_idx, max_count)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_dynamic_cut_normal tests/test_direct_embed.py::test_dynamic_cut_steep tests/test_direct_embed.py::test_dynamic_cut_below_min tests/test_direct_embed.py::test_dynamic_cut_single tests/test_direct_embed.py::test_dynamic_cut_empty tests/test_direct_embed.py::test_dynamic_cut_max_cap tests/test_direct_embed.py::test_dynamic_cut_edge_drop -v
```
Expected: All 7 PASS

- [ ] **Step 5: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add tests/test_direct_embed.py src/lut/direct_embed.py && git commit -m "feat: add dynamic_cut with adaptive threshold"
```

---

### Task 2: JSON 搜索日志 — `log_search_json()` + `log_click()`

**Files:**
- Modify: `src/lut/direct_embed.py`
- Test: `tests/test_direct_embed.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_direct_embed.py — 尾部追加

import json, os, time
from pathlib import Path
from lut.direct_embed import log_search_json, log_click

LOG_DIR = Path("data/search_log")

def test_log_search_json_creates_file():
    """log_search_json 创建 JSON 文件"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    sid = log_search_json(
        query="冷淡",
        query_vector=[0.1, 0.2, 0.3],
        top_results=[("p1", 0.5, 23), ("p2", 0.4, 67)],
        duration_ms=3
    )
    assert sid is not None
    # 验证文件存在
    files = list(LOG_DIR.glob(f"{sid.split('_')[0]}_*.json"))
    assert len(files) >= 1
    with open(LOG_DIR / f"{sid}.json") as f:
        data = json.load(f)
    assert data["query"] == "冷淡"
    assert data["query_vector"] == [0.1, 0.2, 0.3]
    assert data["top_count"] == 2
    assert data["top_results"][0]["index"] == 23
    assert data["clicked_index"] is None

def test_log_click_updates_file():
    """log_click 补写 clicked_index"""
    sid = log_search_json("test", [0.5], [("p", 0.9, 42)], 1)
    log_click(sid, 42)
    with open(LOG_DIR / f"{sid}.json") as f:
        data = json.load(f)
    assert data["clicked_index"] == 42

def test_log_click_unknown_id():
    """不存在的 search_id 不崩溃"""
    result = log_click("nonexistent_000", 0)
    assert result is False

def teardown_cleanup():
    """清理测试产生的日志文件"""
    for f in LOG_DIR.glob("*.json"):
        if "test" in f.read_text(encoding="utf-8"):
            f.unlink()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_log_search_json_creates_file -v
```
Expected: FAIL

- [ ] **Step 3: Write implementation**

```python
# src/lut/direct_embed.py — 尾部追加

import json, os, time
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path("data/search_log")
_COUNTER_FILE = _LOG_DIR / ".counter"

def _next_search_id() -> str:
    """生成自增 search_id: YYYY-MM-DD_NNN"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    seq = 1
    if _COUNTER_FILE.exists():
        prev_date, prev_seq = _COUNTER_FILE.read_text().strip().split("_")
        if prev_date == today:
            seq = int(prev_seq) + 1
        else:
            seq = 1
    _COUNTER_FILE.write_text(f"{today}_{seq:03d}")
    return f"{today}_{seq:03d}"


def log_search_json(query: str, query_vector: list, top_results: list,
                    duration_ms: int) -> str:
    """写搜索日志 JSON 文件，返回 search_id"""
    sid = _next_search_id()
    data = {
        "id": sid,
        "query": query,
        "query_vector": query_vector,
        "top_count": len(top_results),
        "top_results": [
            {"name": n, "score": s, "index": idx}
            for n, s, idx in top_results
        ],
        "clicked_index": None,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
    }
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_LOG_DIR / f"{sid}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return sid


def log_click(search_id: str, preset_index: int) -> bool:
    """补写 search_id 对应日志的 clicked_index"""
    fpath = _LOG_DIR / f"{search_id}.json"
    if not fpath.exists():
        return False
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["clicked_index"] = preset_index
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_log_search_json_creates_file tests/test_direct_embed.py::test_log_click_updates_file tests/test_direct_embed.py::test_log_click_unknown_id -v
```
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add src/lut/direct_embed.py tests/test_direct_embed.py && git commit -m "feat: JSON search log with click tracking"
```

---

### Task 3: 更新 `search()` 返回 index 和 search_id

**Files:**
- Modify: `src/lut/direct_embed.py`
- Test: `tests/test_direct_embed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_direct_embed.py — 尾部追加

from lut.direct_embed import search, _load_index

def test_search_returns_index():
    """search 返回结果含 index 字段"""
    results = search("冷淡", top_n=10)
    assert len(results) > 0
    for name, score, idx in results:
        assert isinstance(idx, int)
        assert 0 <= idx <= 151
```

- [ ] **Step 2: Verify it fails**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_search_returns_index -v
```
Expected: FAIL (current search returns 2-tuple)

- [ ] **Step 3: Modify `search()`**

Locate the current `search()` function return and text index mapping. Change to return 3-tuples `(text, score, index)`:

```python
# 在 search() 中找到这一行：
# results = [(texts[i], float(scores[i])) for i in top_idx]
# 改为：
results = [(texts[i], float(scores[i]), int(i)) for i in top_idx]
```

Also update the CLI `__main__` block to print the new tuple format (prefix an `_` to unpack 3 values).

- [ ] **Step 4: Run test to verify**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/test_direct_embed.py::test_search_returns_index -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add src/lut/direct_embed.py && git commit -m "feat: search returns index in results"
```

---

### Task 4: 更新 `/api/search` — 返回 `search_id` + `count` + 调用 `log_search_json()`

**Files:**
- Modify: `serve.py`
- Test: 手动 curl 验证

- [ ] **Step 1: 修改 serve.py 中 do_POST `/api/search`**

```python
# 替换当前 /api/search 处理块 (约第 53-65 行)
if self.path == "/api/search":
    length = int(self.headers.get("Content-Length", 0))
    body = json.loads(self.rfile.read(length))
    query = body.get("query", "")
    t0 = time.perf_counter()

    # 搜索（用较大 top_n，然后动态截断）
    raw_results = search(query, top_n=30)
    ms = int((time.perf_counter() - t0) * 1000)

    # 动态截断
    from lut.direct_embed import dynamic_cut
    cut = dynamic_cut([(n, s) for n, s, _ in raw_results])
    # 从 raw_results 中取 index
    name_to_idx = {n: idx for n, _, idx in raw_results}
    top = [(n, s, name_to_idx[n]) for n, s in cut]

    # 写日志
    from lut.direct_embed import log_search_json
    query_vec = _last_query_vec  # 需缓存
    sid = log_search_json(query, query_vec, top, ms)

    self.send_json({
        "results": [{"name": n, "score": s, "index": idx} for n, s, idx in top],
        "count": len(top),
        "ms": ms,
        "search_id": sid,
    })
```

- [ ] **Step 2: 缓存 query_vector**

在 `serve.py` 中新增全局变量：

```python
# 在 _preset_cache 附近追加
_last_query_vec = None  # 最近一次搜索的 query_vector
```

在 search() 调用后捕获向量。但 `deep_search()` 函数内部调用 Ollama 嵌入——需要暴露 query_vec。一种方式：修改 `search()` 使其同时返回 query_vector。但更简单的方案：在 serve.py 中直接调用 Ollama 嵌入。

更务实的做法：在 `direct_embed.py` 中加一个辅助函数：

```python
# direct_embed.py 末尾追加
def embed_query(query: str) -> list[float]:
    """返回 query 的 bge-m3 嵌入向量"""
    import json, urllib.request
    body = json.dumps({"model": "bge-m3:latest", "input": [query]}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", body,
                                 {"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["embeddings"][0]
```

然后在 serve.py 搜索路径中：

```python
from lut.direct_embed import embed_query
query_vec = embed_query(query)
_last_query_vec = query_vec
```

- [ ] **Step 3: 手动验证**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python serve.py &
sleep 18
curl -s -X POST http://localhost:8765/api/search -H 'Content-Type: application/json' -d '{"query":"冷淡"}' | python -m json.tool
```
Expected: 返回包含 `search_id`, `count`, `results[].index` 的 JSON

- [ ] **Step 4: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add serve.py src/lut/direct_embed.py && git commit -m "feat: api/search returns search_id+count+index"
```

---

### Task 5: 新增 `/api/click` 端点

**Files:**
- Modify: `serve.py`

- [ ] **Step 1: 在 serve.py do_POST 中添加分支**

在 `do_POST` 中，`/api/apply` 分支前插入：

```python
elif self.path == "/api/click":
    length = int(self.headers.get("Content-Length", 0))
    body = json.loads(self.rfile.read(length))
    sid = body.get("search_id", "")
    idx = body.get("preset_index", -1)
    from lut.direct_embed import log_click
    ok = log_click(sid, idx)
    self.send_json({"ok": ok})
```

- [ ] **Step 2: 手动验证**

```bash
# 先搜一次拿到 search_id
SID=$(curl -s -X POST http://localhost:8765/api/search -H 'Content-Type: application/json' -d '{"query":"冷淡"}' | python -c "import sys,json; print(json.load(sys.stdin)['search_id'])")
# 发送 click
curl -s -X POST http://localhost:8765/api/click -H 'Content-Type: application/json' -d "{\"search_id\":\"$SID\",\"preset_index\":79}"
# 验证 JSON 文件
cat data/search_log/${SID}.json | python -m json.tool
```
Expected: `clicked_index: 79`

- [ ] **Step 3: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add serve.py && git commit -m "feat: add /api/click endpoint"
```

---

### Task 6: 新增 `/api/preview/{index}` 缩略图端点

**Files:**
- Modify: `serve.py`
- Create: `tests/test_api.py` (新建)

- [ ] **Step 1: 写测试**

```python
# tests/test_api.py
import urllib.request
import json

def test_search_returns_search_id():
    """/api/search 返回 search_id"""
    body = json.dumps({"query": "冷淡"}).encode()
    req = urllib.request.Request("http://localhost:8765/api/search", body,
                                 {"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    assert "search_id" in resp
    assert "count" in resp
    assert isinstance(resp["count"], int)

def test_search_returns_index_in_results():
    """搜索结果包含 index"""
    body = json.dumps({"query": "冷淡"}).encode()
    req = urllib.request.Request("http://localhost:8765/api/search", body,
                                 {"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    for r in resp["results"]:
        assert "index" in r
        assert isinstance(r["index"], int)
```

- [ ] **Step 2: 实现预览端点**

核心问题：预览需要用上传的图片。需要让 serve.py 记住最后上传的图片文件路径。

```python
# serve.py 中 file_path 存储
_last_input_path = None  # 最后一次上传的图片临时路径
```

在 `/api/apply` 中处理上传图片时，保存一份到最后使用路径：

```python
# 在 tempfile 处理之后，tmp_in 写入之后
_last_input_path = tmp_in  # 注意在 finally 中不要删除
```

在 `do_GET` 中新增：

```python
elif self.path.startswith("/api/preview/"):
    parts = self.path.split("/")
    if len(parts) < 4 or not parts[3].isdigit():
        self.send_json({"error": "invalid index"})
        return
    preset_index = int(parts[3])

    if _last_input_path is None or not Path(_last_input_path).exists():
        self.send_json({"error": "请先上传图片"})
        return

    # 查找预设
    preset = None
    for p in _preset_cache.values():
        for name, _, idx in _last_search_results:
            if idx == preset_index and p.name == name:
                preset = p
                break
    if preset is None:
        self.send_json({"error": "未找到预设"})
        return

    tmp_out = tempfile.mktemp(suffix=".jpg")
    try:
        apply_lut(_last_input_path, preset, tmp_out)
        img = Image.open(tmp_out)
        img.thumbnail((200, 200))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        jpg_bytes = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpg_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(jpg_bytes)
    finally:
        Path(tmp_out).unlink(missing_ok=True)
```

需要新增 import：`import io, tempfile`（已有），`from PIL import Image`（已有）。

- [ ] **Step 3: 更新 upload 路径保存逻辑**

修改 `/api/apply` 中上传图片的处理，保存一份到最后使用路径：

```python
# 在 tempfile 创建 tmp_in 后
_last_input_path = tmp_in
```

注意：需要在 finally 中**不删除**最后使用的图片。重构 apply 路径——复制一份图片到持久临时路径：

```python
# 顶部新增
_LAST_IMAGE_PATH = Path(tempfile.gettempdir()) / "projectlut_last_input.jpg"

# apply 中
img_bytes = ...
_LAST_IMAGE_PATH.write_bytes(img_bytes)
tmp_in = str(_LAST_IMAGE_PATH)
```

这样最后一张图片一直保留在 temp 目录，预览端点随时可用。

- [ ] **Step 4: 手动验证**

```bash
# 上传图片（先上传，预览依赖上传的图片）
curl -s -X POST http://localhost:8765/api/apply -F "preset_name=人像冷白" -F "image=@tests/test_playwright.jpg" -o /dev/null
# 找 index
SID=$(curl -s -X POST http://localhost:8765/api/search -H 'Content-Type: application/json' -d '{"query":"冷淡"}' | python -c "import sys,json; print(json.load(sys.stdin)['search_id'])")
IDX=$(curl -s -X POST http://localhost:8765/api/search -H 'Content-Type: application/json' -d '{"query":"冷淡"}' | python -c "import sys,json; print(json.load(sys.stdin)['results'][0]['index'])")
# 拉预览
curl -s http://localhost:8765/api/preview/$IDX -o preview_test.jpg
file preview_test.jpg
```
Expected: preview_test.jpg 是 JPEG 缩略图

- [ ] **Step 5: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add serve.py tests/test_api.py && git commit -m "feat: add /api/preview/{index} thumbnail endpoint"
```

---

### Task 7: 前端 — ⚡ 状态条 + 动态结果 + 点击回传

**Files:**
- Modify: `app.html`

- [ ] **Step 1: 修改 doSearch() 状态显示**

将状态条从 `✓ N 个匹配（本地 xxx ms）` 改为：

```javascript
// 替换原有的 statusEl 更新逻辑
statusEl.textContent = `⚡ ${data.ms}ms · 共 ${data.count} 个匹配`;
```

并在搜索结果列表后增加一个 hidden input 存 search_id：

```javascript
// 在 doSearch() 的 data 处理后
window._lastSearchId = data.search_id;
```

- [ ] **Step 2: 修改结果列表渲染（动态数量，不再固定 5 个）**

结果列表渲染不变（`results.forEach` 已经支持任意数量），不需要改。

- [ ] **Step 3: 修改 doApply() 回传 click**

在 doApply() 中，FormData 追加 search_id 和 preset_index：

```javascript
// 在 doApply() 的 fd.append 后面追加
if (window._lastSearchId && window._lastClickedIndex !== undefined) {
    fd.append("search_id", window._lastSearchId);
}
```

并在选中预设时记录 index：

```javascript
// 在 li.onclick 中，选中时
li.onclick = () => {
    selectedPresetName = item.preset_name;
    window._lastClickedIndex = item.index;  // 新增
    ...
};
```

- [ ] **Step 4: 服务端 apply 接收 click 参数**

在 serve.py `/api/apply` 中，apply 完成后调用 log_click：

```python
# 在 apply_lut 成功后，try 块末尾
search_id = form.getfirst("search_id", "")
if search_id:
    from lut.direct_embed import log_click
    # 需要 preset_index，从表单获取
    preset_idx_str = form.getfirst("preset_index", "")
    if preset_idx_str:
        log_click(search_id, int(preset_idx_str))
```

前端 FormData 需要追加 preset_index：

```javascript
fd.append("preset_index", window._lastClickedIndex);
```

- [ ] **Step 5: 手动验证**

打开浏览器 `http://localhost:8765`，搜索"冷淡"，验证：
1. 状态条显示 `⚡ Nms · 共 M 个匹配` ✅
2. 结果列表显示动态数量 ✅
3. 应用后 JSON 日志文件中 clicked_index 被写入 ✅

- [ ] **Step 6: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add app.html serve.py && git commit -m "feat: frontend search analytics + click tracking"
```

---

### Task 8: 前端 — 百图预览网格

**Files:**
- Modify: `app.html`

- [ ] **Step 1: 在搜索结果列表下方添加预览网格容器**

在 `app.html` 的 `results` 和 `status` 之后、`actions` 之前插入：

```html
<div class="preview-strip" id="previewStrip" style="display:none">
  <div class="panel-title">预览</div>
  <div class="preview-grid" id="previewGrid"></div>
</div>

<style>
.preview-strip {
  margin-top: 10px;
  border-top: 1px solid #22252e;
  padding-top: 10px;
}
.preview-grid {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 4px 0;
}
.preview-grid .cell {
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  border-radius: 3px;
  border: 2px solid transparent;
  cursor: pointer;
  background: #14171d;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.1s;
}
.preview-grid .cell:hover {
  border-color: #3b82f6;
}
.preview-grid .cell.selected {
  border-color: #2563eb;
}
.preview-grid .cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-grid .cell .placeholder {
  font-size: 10px;
  color: #4b5563;
}
</style>
```

- [ ] **Step 2: 搜索完成后触发预览加载**

在 `doSearch()` 的成功分支中，`data` 处理后追加：

```javascript
const grid = document.getElementById("previewGrid");
const strip = document.getElementById("previewStrip");
grid.innerHTML = "";
strip.style.display = "block";

// 为每个结果创建格子
data.results.forEach((item, idx) => {
  const cell = document.createElement("div");
  cell.className = "cell";
  cell.dataset.index = item.index;
  cell.dataset.name = item.preset_name;
  cell.innerHTML = `<span class="placeholder">${idx+1}</span>`;
  cell.onclick = () => {
    window._lastClickedIndex = item.index;
    selectedPresetName = item.preset_name;
    // 高亮
    document.querySelectorAll(".cell").forEach(c => c.classList.remove("selected"));
    cell.classList.add("selected");
    updateApplyBtn();
  };
  grid.appendChild(cell);
});

// 逐个加载缩略图（最多并发 3 个）
const cells = grid.querySelectorAll(".cell");
let loaded = 0;
const CONCURRENCY = 3;

function loadNext() {
  if (loaded >= cells.length) return;
  const cell = cells[loaded];
  const idx = cell.dataset.index;
  loaded++;
  fetch(API_BASE + `/api/preview/${idx}?sid=${window._lastSearchId}`)
    .then(r => {
      if (!r.ok) throw new Error(r.status);
      return r.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      cell.innerHTML = `<img src="${url}" alt="preview">`;
    })
    .catch(() => {
      cell.innerHTML = `<span class="placeholder">✗</span>`;
    });
}

// 启动 N 个并发
for (let i = 0; i < CONCURRENCY; i++) loadNext();
```

- [ ] **Step 3: 手动验证**

打开浏览器 `http://localhost:8765`，上传图片 → 搜索"冷淡" → 查看预览网格是否逐个填充。

- [ ] **Step 4: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add app.html && git commit -m "feat: preview grid with streaming thumbnails"
```

---

### Task 9: 数据目录 `.gitignore` + 清理测试

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 更新 `.gitignore`**

在 `.gitignore` 末尾追加：

```
# Search log data
data/search_log/
```

- [ ] **Step 2: 运行完整测试套件确认 0 回归**

```bash
cd d:/WorkSpace/ProjectLUT && source .venv/Scripts/activate && python -m pytest tests/ -v
```
Expected: 全部 PASS（原 18 个 + 新增 N 个）

- [ ] **Step 3: Commit**

```bash
cd d:/WorkSpace/ProjectLUT && git add .gitignore && git commit -m "chore: ignore search_log data dir"
```

---

## Self-Review Checklist

- [ ] **Spec coverage** — 对照设计文档逐项：
  - JSON 搜索日志（Task 2）✅
  - query_vector 持久化（Task 2 + Task 4）✅
  - top_results[index] 替代 name（Task 3）✅
  - clicked_index 回传（Task 5 + Task 7）✅
  - 动态截断（Task 1）✅
  - ⚡ 状态条（Task 7）✅
  - 百图预览流式渲染（Task 8）✅
- [ ] **Placeholder check** — 无 TBD/TODO
- [ ] **Type consistency** — index 始终是 int（vectors.npy 位置 0-151），search_id 格式始终 YYYY-MM-DD_NNN
