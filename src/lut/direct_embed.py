"""
直接向量嵌入与检索

绕过 LightRAG 管道，直接用 bge-m3 嵌入 LUT 预设标签，
numpy 余弦相似度检索。适用于短标签语义匹配场景。
"""

import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np

from .parser import load_presets, presets_to_texts

# _time alias — avoid collision with `time` module used for sleep() above
_time = time


OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "bge-m3:latest"
STORE_DIR = Path(".lut_vectors")
# 进程内缓存 —— 避免每次调用都重新读文件
_cached_vectors = None
_cached_texts = None
_cached_ids = None  # 预设唯一 ID（= name，平行于 texts）
_cached_vectors_norm = None  # 预计算 L2 范数后的向量 (n, 1024)


def get_stats() -> dict:
    """从 JSON 搜索日志聚合统计"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs = sorted(_LOG_DIR.glob("*.json"))
    total = len(logs)
    query_count = {}
    total_ms = 0
    for f in logs:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            q = data.get("query", "")
            query_count[q] = query_count.get(q, 0) + 1
            total_ms += data.get("duration_ms", 0)
        except Exception:
            pass
    top = sorted(query_count.items(), key=lambda x: -x[1])[:10]
    avg_ms = round(total_ms / total, 1) if total > 0 else 0
    return {
        "total": total,
        "top_queries": [(q, c) for q, c in top],
        "avg_ms": avg_ms,
    }


def get_history(n: int = 20) -> list[dict]:
    """返回最近 n 条搜索记录（从 JSON 读取）"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs = sorted(_LOG_DIR.glob("*.json"), reverse=True)[:n]
    result = []
    for f in logs:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            result.append({
                "query": data.get("query", ""),
                "count": data.get("top_count", 0),
                "ms": data.get("duration_ms", 0),
                "at": data.get("timestamp", ""),
            })
        except Exception:
            pass
    return result


def _embed_batch(texts: list[str], batch_size: int = 1) -> np.ndarray:
    """调用 Ollama bge-m3 分批嵌入，返回 (n, dim) 数组"""
    all_embeddings = []
    total = len(texts)
    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(3):
            try:
                body = json.dumps({"model": EMBED_MODEL, "input": batch}).encode()
                req = urllib.request.Request(OLLAMA_EMBED_URL, body, {"Content-Type": "application/json"})
                resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
                embeds = resp["embeddings"]
                break
            except Exception:
                if attempt == 2:
                    raise
                import time as _time_module
                _time_module.sleep(5)
        all_embeddings.extend(embeds)
        print(f"  嵌入 {min(i + len(batch), total)}/{total}")
    return np.array(all_embeddings, dtype=np.float32)


def build_index(presets_dir: str = "LUT预设1", force: bool = False):
    """构建向量索引，保存到 .lut_vectors/"""
    global _cached_vectors, _cached_texts, _cached_ids, _cached_vectors_norm
    vectors_file = STORE_DIR / "vectors.npy"
    texts_file = STORE_DIR / "texts.txt"

    if not force and vectors_file.exists() and texts_file.exists():
        # 确保缓存已加载
        if _cached_vectors is None:
            _cached_vectors = np.load(vectors_file).astype(np.float32)
            texts = texts_file.read_text(encoding="utf-8").split("\n")
            _cached_texts = texts
            ids_file = STORE_DIR / "ids.txt"
            if ids_file.exists():
                _cached_ids = ids_file.read_text(encoding="utf-8").split("\n")
            else:
                _cached_ids = [t.split(" — ")[0] for t in texts]
            norms = np.linalg.norm(_cached_vectors, axis=1, keepdims=True) + 1e-8
            _cached_vectors_norm = _cached_vectors / norms
        return

    STORE_DIR.mkdir(exist_ok=True)

    presets = load_presets(presets_dir)
    texts = presets_to_texts(presets)
    ids = [p.id for p in presets]
    print(f"嵌入 {len(texts)} 个预设...")

    vectors = _embed_batch(texts)
    np.save(vectors_file, vectors)
    texts_file.write_text("\n".join(texts), encoding="utf-8")
    (STORE_DIR / "ids.txt").write_text("\n".join(ids), encoding="utf-8")

    # 更新缓存
    _cached_vectors = vectors
    _cached_texts = texts
    _cached_ids = ids
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8
    _cached_vectors_norm = vectors / norms

    print(f"索引完成: {vectors.shape[0]} 个向量, {vectors.shape[1]} 维")


def _load_index():
    """懒加载索引到内存"""
    global _cached_vectors, _cached_texts, _cached_ids, _cached_vectors_norm
    if _cached_vectors is None or _cached_texts is None:
        vectors_file = STORE_DIR / "vectors.npy"
        texts_file = STORE_DIR / "texts.txt"
        ids_file = STORE_DIR / "ids.txt"
        if not (vectors_file.exists() and texts_file.exists()):
            raise RuntimeError("尚未构建向量索引 —— 请先调用 build_index()")
        _cached_vectors = np.load(vectors_file).astype(np.float32)
        texts = texts_file.read_text(encoding="utf-8").split("\n")
        _cached_texts = texts
        # 加载 ID（向后兼容：无 ids.txt 则从 texts 提取）
        if ids_file.exists():
            _cached_ids = ids_file.read_text(encoding="utf-8").split("\n")
        else:
            _cached_ids = [t.split(" — ")[0] for t in texts]
        norms = np.linalg.norm(_cached_vectors, axis=1, keepdims=True) + 1e-8
        _cached_vectors_norm = _cached_vectors / norms
    return _cached_vectors, _cached_texts, _cached_ids, _cached_vectors_norm


def get_cached_preset_names() -> list[str]:
    """返回预设 ID 列表"""
    _, _, ids, _ = _load_index()
    return ids[:]


def search(query: str, top_n: int = 30) -> list[tuple[str, float, int]]:
    """余弦相似度检索，返回 [(preset_id, 相似度, 索引), ...]"""
    _t0 = _time.perf_counter()
    _, _, ids, v_norm = _load_index()

    # Ollama 嵌入（带容错）
    try:
        body = json.dumps({"model": EMBED_MODEL, "input": [query]}).encode()
        req = urllib.request.Request(OLLAMA_EMBED_URL, body, {"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req).read())
        q_vec = np.array(resp["embeddings"][0], dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f"embedding API 调用失败: {e}")
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-8)

    # 单次矩阵点积 —— 152 个余弦相似度
    scores = np.dot(v_norm, q_norm)

    if len(scores) == 0:
        return []

    # 部分排序比全 argsort 更快
    if top_n >= len(scores):
        top_idx = np.argsort(-scores)
    else:
        top_idx = np.argpartition(-scores, top_n - 1)[:top_n]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

    results = [(ids[i], float(scores[i]), int(i)) for i in top_idx]
    return results


def dynamic_cut(results, min_score: float = 0.3,
                max_count: int = 10, drop_threshold: float = 0.15):
    """动态截断：绝对阈值 + 陡降检测 + 上限"""
    if not results:
        return []

    sorted_r = sorted(results, key=lambda x: x[1], reverse=True)
    filtered = [item for item in sorted_r if item[1] >= min_score]

    if not filtered:
        return []

    cut_idx = len(filtered)
    for i in range(1, len(filtered)):
        if filtered[i-1][1] - filtered[i][1] > drop_threshold:
            cut_idx = i
            break

    return filtered[:min(cut_idx, max_count)]


# ── JSON 搜索日志 ────────────────────────────────────────

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
    """写搜索日志 JSON 文件，返回 search_id

    top_results: [(preset_id, score, index), ...]
    """
    sid = _next_search_id()
    data = {
        "id": sid,
        "query": query,
        "query_vector": query_vector,
        "top_count": len(top_results),
        "top_results": [
            {"preset_id": pid, "score": s, "index": idx}
            for pid, s, idx in top_results
        ],
        "clicked_preset_id": None,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
    }
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_LOG_DIR / f"{sid}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return sid


def log_click(search_id: str, preset_id: str) -> bool:
    """补写 search_id 对应日志的 clicked_preset_id"""
    fpath = _LOG_DIR / f"{search_id}.json"
    if not fpath.exists():
        return False
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["clicked_preset_id"] = preset_id
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def embed_query(query: str) -> list[float]:
    """返回 query 的 bge-m3 嵌入向量"""
    body = json.dumps({"model": EMBED_MODEL, "input": [query]}).encode()
    req = urllib.request.Request(OLLAMA_EMBED_URL, body,
                                 {"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["embeddings"][0]


# ── CLI ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        build_index(force=True)
    elif len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        build_index()  # build once if not exists
        for text, score, _ in search(query):
            print(f"{score:.4f}  {text}")
    else:
        # 交互模式
        build_index()
        while True:
            try:
                q = input("\n查询> ")
                if not q:
                    break
                for text, score, _ in search(q):
                    print(f"  {score:.4f}  {text}")
            except (EOFError, KeyboardInterrupt):
                break
