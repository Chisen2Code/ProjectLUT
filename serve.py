"""ProjectLUT HTTP 服务

API:
  GET  /                  → app.html
  GET  /api/ping          → 健康检查
  GET  /api/stats         → 统计
  POST /api/search        → {"query":"...","top_n":5} → Top-N 匹配
  POST /api/apply         → multipart: preset_name + image → 返回 JPEG
"""
import sys
from pathlib import Path

# 将 src/ 加入 Python 路径，使 lut 模块可导入
sys.path.insert(0, str(Path(__file__).parent / "src"))

import cgi
import io
import json
import tempfile
import time
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from PIL import Image as PILImage

from lut.direct_embed import build_index, search, get_stats, get_cached_preset_names, embed_query, dynamic_cut, log_search_json, log_click
from lut.parser import load_presets
from lut.processor import apply_lut, preload_all_luts
from lut.rerank import rule_filter

# preset_id → Preset 对象缓存
_preset_cache = {}

# 按 ID 排序的预设列表（供预览 index 查找用）
_sorted_presets: list = []

# 最近一次上传的图片缓存（供缩略图端点使用）
_LAST_IMAGE_PATH = Path(tempfile.gettempdir()) / "projectlut_last_input.jpg"


class Handler(BaseHTTPRequestHandler):
    # 静默日志
    def log_message(self, format, *args):
        print(f"  [{self.log_date_time_string()}] {args[0]}")

    def do_GET(self):
        if self.path in ("/", "/index.html", "/app.html"):
            self.serve_file("app.html", "text/html; charset=utf-8")
        elif self.path == "/api/ping":
            self.send_json({"ok": True})
        elif self.path == "/api/stats":
            self.send_json(get_stats())
        elif self.path.startswith("/api/preview/"):
            parts = self.path.split("/")
            if len(parts) < 4 or not parts[3].isdigit():
                self.send_error(400, "invalid index")
                return
            preset_index = int(parts[3])

            if not _LAST_IMAGE_PATH.exists():
                self.send_error(400, "请先上传图片")
                return

            if preset_index < 0 or preset_index >= len(_sorted_presets):
                self.send_error(404, "index out of range")
                return
            preset = _sorted_presets[preset_index]
            if preset is None:
                self.send_error(404, "preset not found")
                return

            # 生成缩略图
            tmp_out = tempfile.mktemp(suffix=".jpg")
            try:
                apply_lut(str(_LAST_IMAGE_PATH), preset, tmp_out)
                img = PILImage.open(tmp_out)
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
        else:
            # 静态文件
            fpath = self.path.lstrip("/")
            if Path(fpath).is_file():
                self.serve_file(fpath)
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        if self.path == "/api/search":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                query = body.get("query", "")
                t0 = time.perf_counter()

                query_vec = embed_query(query)
                raw_results = search(query, top_n=30)
                ms = int((time.perf_counter() - t0) * 1000)

                cut = dynamic_cut([(pid, s) for pid, s, _ in raw_results], max_count=6, min_score=0.4)
                cut = rule_filter(cut, query, _preset_cache)
                pid_to_idx = {pid: idx for pid, _, idx in raw_results}
                top = [(pid, s, pid_to_idx[pid]) for pid, s in cut]

                sid = log_search_json(query, query_vec, top, ms)

                self.send_json({
                    "results": [{"preset_id": pid, "score": s, "index": idx} for pid, s, idx in top],
                    "count": len(top),
                    "ms": ms,
                    "search_id": sid,
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json({"error": str(e)})
        elif self.path == "/api/click":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                sid = body.get("search_id", "")
                pid = body.get("preset_id", "")
                ok = log_click(sid, pid) if sid and pid else False
                self.send_json({"ok": ok})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)})
        elif self.path == "/api/apply":
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST",
                         "CONTENT_TYPE": self.headers.get("Content-Type")}
            )
            preset_id = form.getfirst("preset_id", "")
            search_id = form.getfirst("search_id", "")
            img_item = form["image"]
            img_bytes = img_item.file.read() if isinstance(img_item, cgi.FieldStorage) and hasattr(img_item, "file") else b""
            if img_bytes:
                _LAST_IMAGE_PATH.write_bytes(img_bytes)

            if not img_bytes:
                self.send_error(400, "未上传图片")
                return
            if not preset_id:
                self.send_error(400, "未指定预设")
                return

            # 查找预设（唯一真相 = preset_id）
            preset = _preset_cache.get(preset_id)
            if preset is None:
                self.send_error(404, f"未找到预设: {preset_id}")
                return

            # 临时文件处理
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(img_bytes)
                tmp_in = f.name
            tmp_out = tempfile.mktemp(suffix=".jpg")

            try:
                t0 = time.perf_counter()
                apply_lut(tmp_in, preset, tmp_out)
                elapsed = int((time.perf_counter() - t0) * 1000)
                print(f"  [apply] {preset_id} → {elapsed}ms")

                # 点击回传
                if search_id and preset_id:
                    try:
                        log_click(search_id, preset_id)
                    except Exception:
                        pass

                out_bytes = Path(tmp_out).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(out_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(out_bytes)
            finally:
                Path(tmp_in).unlink(missing_ok=True)
                Path(tmp_out).unlink(missing_ok=True)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_error(self, code: int, msg: str):
        body = json.dumps({"error": msg}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, path, content_type=None):
        p = Path(path)
        if not p.exists() or not p.is_file():
            self.send_response(404)
            self.end_headers()
            return
        if content_type is None:
            content_type = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if "text" in content_type or "javascript" in content_type or "json" in content_type else ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _warmup():
    """启动预热：构建索引 + 预载全部 LUT"""
    global _sorted_presets
    print("[warm] 构建向量索引...")
    build_index()

    print("[warmup] 加载预设...")
    presets = load_presets()
    if not presets:
        raise RuntimeError("未加载到任何预设，请检查 LUT预设1/ 目录")
    for p in presets:
        _preset_cache[p.id] = p
    _sorted_presets = sorted(presets, key=lambda p: p.id)
    print(f"[warmup] 共 {len(presets)} 个预设")

    print("[warmup] 预载 LUT tables...")
    preload_all_luts()
    print("[warmup] 完成 [OK]")


if __name__ == "__main__":
    _warmup()
    print("\n  ProjectLUT -> http://localhost:8765")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
