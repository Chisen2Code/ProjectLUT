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
import json
import tempfile
import time
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler

from lut.direct_embed import build_index, search, get_stats, get_cached_preset_names
from lut.parser import load_presets
from lut.processor import apply_lut, preload_all_luts

# 预设名 → Preset 对象缓存
_preset_cache = {}


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
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            query = body.get("query", "")
            top_n = int(body.get("top_n", 5))
            t0 = time.perf_counter()
            results = search(query, top_n=top_n)
            elapsed = int((time.perf_counter() - t0) * 1000)
            self.send_json({
                "results": [{"name": r[0], "preset_name": r[0].split(" — ")[0],
                           "score": float(r[1])} for r in results],
                "ms": elapsed,
            })
        elif self.path == "/api/apply":
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST",
                         "CONTENT_TYPE": self.headers.get("Content-Type")}
            )
            preset_name = form.getfirst("preset_name", "")
            img_item = form["image"]
            img_bytes = img_item.file.read() if isinstance(img_item, cgi.FieldStorage) and hasattr(img_item, "file") else b""

            if not img_bytes:
                self.send_json({"error": "未上传图片"})
                return
            if not preset_name:
                self.send_json({"error": "未指定预设"})
                return

            # 查找预设
            preset = _preset_cache.get(preset_name)
            if preset is None:
                self.send_json({"error": f"未找到预设: {preset_name}"})
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
                print(f"  [apply] {preset_name} → {elapsed}ms")

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
    print("[warm] 构建向量索引...")
    build_index()

    print("[warmup] 加载预设...")
    presets = load_presets()
    for p in presets:
        _preset_cache[p.name] = p
    print(f"[warmup] 共 {len(presets)} 个预设")

    print("[warmup] 预载 LUT tables...")
    preload_all_luts()
    print("[warmup] 完成 ✓")


if __name__ == "__main__":
    _warmup()
    print("\n🚀 ProjectLUT → http://localhost:8765")
    HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
