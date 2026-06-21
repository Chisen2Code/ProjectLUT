"""极简版 serve —— 单独启动以便测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import cgi, json, tempfile, time, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler

from lut.direct_embed import build_index, search, get_stats
from lut.parser import load_presets
from lut.processor import apply_lut, preload_all_luts

_preset_cache = {}

print("[warm] 构建向量索引...")
build_index()
print("[warmup] 加载预设...")
presets = load_presets()
for p in presets:
    _preset_cache[p.name] = p
print(f"[warmup] 共 {len(presets)} 个预设")
print("[warmup] 预载 LUT tables...")
preload_all_luts()
print("[warmup] 完成 ✓ 监听 8765")

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        print("  ", a[0])

    def do_GET(self):
        if self.path in ("/", "/index.html", "/app.html"):
            with open("app.html", "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/api/ping":
            self._send_json({"ok": True, "presets": len(_preset_cache)})
        elif self.path == "/api/stats":
            self._send_json(get_stats())
        else:
            fpath = self.path.lstrip("/")
            p = Path(fpath)
            if p.is_file():
                data = p.read_bytes()
                ct = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/api/search":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            query = body.get("query", "")
            top_n = int(body.get("top_n", 5))
            t0 = time.perf_counter()
            results = search(query, top_n=top_n)
            elapsed = int((time.perf_counter() - t0) * 1000)
            self._send_json({
                "results": [{
                    "name": r[0],
                    "preset_name": r[0].split(" — ")[0],
                    "score": float(r[1])
                } for r in results],
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
            if not img_bytes or not preset_name:
                self._send_json({"error": "缺少参数"})
                return
            preset = _preset_cache.get(preset_name)
            if preset is None:
                self._send_json({"error": f"未找到预设: {preset_name}"})
                return
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(img_bytes); tmp_in = f.name
            tmp_out = tempfile.mktemp(suffix=".jpg")
            try:
                t0 = time.perf_counter()
                apply_lut(tmp_in, preset, tmp_out)
                elapsed = int((time.perf_counter() - t0) * 1000)
                print(f"  [apply] {preset_name} → {elapsed}ms")
                out_bytes = Path(tmp_out).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("X-Elapsed-Ms", str(elapsed))
                self.send_header("Content-Length", str(len(out_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(out_bytes)
            finally:
                Path(tmp_in).unlink(missing_ok=True)
                Path(tmp_out).unlink(missing_ok=True)
        else:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("0.0.0.0", 8765), H).serve_forever()
