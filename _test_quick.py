"""快速验证"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

t0 = time.perf_counter()
from lut.parser import load_presets
presets = load_presets()
print(f"load_presets: {len(presets)} in {time.perf_counter() - t0:.1f}s")

t0 = time.perf_counter()
from lut.processor import preload_all_luts
preload_all_luts()
print(f"preload_all_luts: {time.perf_counter() - t0:.1f}s")

import json, urllib.request
t0 = time.perf_counter()
body = json.dumps({"model": "bge-m3:latest", "input": ["冷色调胶片感", "动漫明亮", "富士胶片风格", "复古vintage", "柯达2383-709"]}).encode()
req = urllib.request.Request("http://localhost:11434/api/embed", body, {"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
print(f"embed 5 texts: {len(resp.get('embeddings', []))} vectors in {time.perf_counter() - t0:.2f}s")

# 构建或加载索引
t0 = time.perf_counter()
from lut.direct_embed import build_index
build_index()
print(f"build_index (cached or built): {time.perf_counter() - t0:.1f}s")
