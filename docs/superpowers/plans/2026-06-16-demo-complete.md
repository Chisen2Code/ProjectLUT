# Demo 闭环实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**目标：** `lut apply "描述" input.jpg -o output.jpg` + `app.html` GUI 双通道可用。

**架构：** parser 补 colour 读 .cube RGB → processor 负责 log→709 转换 + 3D LUT 应用 → CLI 串联 → GUI 提供浏览器交互。

**技术栈：** Python 3.11, colour-science, numpy, Pillow, HTML+JS

---

### Task 1: parser 补全 — 读 .cube RGB 数据

**文件：**
- 修改: `src/lut/parser.py:20-42` (Preset dataclass), `src/lut/parser.py:95-133` (parse_presets 循环体)
- 修改: `src/lut/parser.py:12-16` (imports)

- [ ] **Step 1: 在 Preset 加字段 + 添加读 .cube 函数**

在 Preset dataclass 中新增 `lut_data` 和 `lut_size` 字段：

```python
import numpy as np

@dataclass
class Preset:
    name: str
    filename: str
    path: Path
    color_space: Optional[str] = None
    collection: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    original_author: str = "林馆长"
    lut_data: Optional[np.ndarray] = None   # (N^3, 3) RGB 浮点
    lut_size: int = 0                        # 33
```

添加解析函数（利用 colour.read_LUT）：

```python
import colour

def read_cube_rgb(path: Path) -> tuple[np.ndarray, int]:
    """读取 .cube 文件的 3D LUT 数据"""
    lut = colour.read_LUT(str(path))
    size = lut.size  # 33
    data = np.array(lut.table)  # (35937, 3)
    return data, size
```

在 parse_presets 循环中，添加读取：

```python
try:
    lut_data, lut_size = read_cube_rgb(cube_file)
except Exception:
    lut_data, lut_size = None, 0
```

- [ ] **Step 2: 验证**

```bash
cd d:/WorkSpace/ProjectLUT && .venv/Scripts/python.exe -c "
from src.lut.parser import load_presets
p = load_presets('LUT预设1')
print(f'总计: {len(p)}')
with_rgb = sum(1 for x in p if x.lut_data is not None)
print(f'含RGB数据: {with_rgb}')
print(f'示例: {p[0].name} size={p[0].lut_size} data_shape={p[0].lut_data.shape}')
"
```

Expected: 152 presets, 152 with RGB, size=33, shape=(35937,3)

---

### Task 2: processor.py

**文件：**
- 创建: `src/lut/processor.py`

- [ ] **Step 1: 创建 processor.py**

```python
"""
LUT 处理器 — 读取图片，套 3D LUT，输出调色结果。

用法:
    from .processor import apply_lut
    apply_lut("input.jpg", preset, "output.jpg")
"""

import numpy as np
from PIL import Image

from .parser import Preset


def _log_to_709(img_rgb: np.ndarray) -> np.ndarray:
    """简单的 log → 709 技术转换（s-curve approximation）"""
    # log to linear: 2.2 gamma approximation
    linear = np.power(np.clip(img_rgb, 0, 1), 2.2)
    # linear to 709: slight contrast
    return np.clip(np.power(linear, 1 / 2.2), 0, 1)


def apply_lut(
    input_path: str,
    preset: Preset,
    output_path: str,
) -> str:
    """
    套 LUT 到图片。

    Args:
        input_path: 输入图片路径
        preset: 已解析的 Preset（含 lut_data）
        output_path: 输出路径

    Returns:
        output_path
    """
    if preset.lut_data is None:
        raise ValueError(f"预设 {preset.name} 缺少 LUT 数据")

    # 读图 → RGB 浮点 [0,1]
    img = Image.open(input_path).convert("RGB")
    img_rgb = np.array(img, dtype=np.float32) / 255.0

    # log → 709 转换
    if preset.color_space == "log":
        img_rgb = _log_to_709(img_rgb)

    # 套 3D LUT: 三线性插值
    # colour-science 的 LUT.apply() 期望 (H,W,C) 或 (3,H,W)
    import colour
    lut = colour.LUT3D(preset.lut_data.reshape(-1, 3), size=preset.lut_size)
    result = lut.apply(img_rgb)
    result = np.clip(result, 0, 1)

    # 输出
    result_img = Image.fromarray((result * 255).astype(np.uint8))
    result_img.save(output_path)
    return output_path
```

- [ ] **Step 2: 验证**

```bash
.venv/Scripts/python.exe -c "
from src.lut.parser import load_presets
from src.lut.processor import apply_lut
p = [x for x in load_presets() if x.color_space == '709'][0]
print(f'Test: {p.name}')
apply_lut('tests/test_709_sample.png', p, '/tmp/test_apply.png')
print('OK')
"
```

---

### Task 3: CLI apply 子命令

**文件：**
- 修改: `src/lut/cli.py`

- [ ] **Step 1: 添加 apply 子命令**

在 `main()` 的 subparsers 中添加：

```python
p_apply = sub.add_parser("apply", help="套 LUT 到图片")
p_apply.add_argument("query", type=str, help="搜索描述或预设名称")
p_apply.add_argument("input", type=str, help="输入图片路径")
p_apply.add_argument("-o", "--output", type=str, default=None, help="输出路径")
p_apply.add_argument("-n", type=int, default=1, help="使用第 N 个匹配结果 (默认第1个)")
```

Handler 函数：

```python
def cmd_apply(args):
    """套 LUT 到图片"""
    from .direct_embed import build_index, search
    from .parser import load_presets
    from .processor import apply_lut
    
    build_index()
    results = search(args.query, top_n=args.n)
    if not results:
        print("未找到匹配的预设")
        return
    
    text, score = results[args.n - 1]
    name = text.split(" — ")[0]
    
    presets = load_presets()
    preset = next((p for p in presets if p.name == name), None)
    if preset is None:
        print(f"预设 '{name}' 未找到")
        return
    
    output = args.output or f"{Path(args.input).stem}_{name}.jpg"
    apply_lut(args.input, preset, output)
    print(f"已输出: {output}")
```

在 cmds 字典加 `"apply": cmd_apply`，在 imports 顶部加 `from pathlib import Path`。

- [ ] **Step 2: 验证**

```bash
.venv/Scripts/lut.exe apply "冷色调胶片感" tests/test_709_sample.png -o /tmp/test_cli.jpg
```
Expected: `已输出: /tmp/test_cli.jpg`

---

### Task 4: 测试验收

**文件：**
- 创建: `tests/test_processor.py`

- [ ] **Step 1: 创建测试文件**

```python
"""processor.py 验收测试"""
import numpy as np
from pathlib import Path
from src.lut.parser import load_presets
from src.lut.processor import apply_lut

PRESETS = load_presets()
TEST_DIR = Path("tests")

def test_all_152_readable():
    """所有 .cube 可解析 RGB"""
    assert len(PRESETS) == 152
    for p in PRESETS:
        assert p.lut_data is not None, f"{p.name} 无 RGB 数据"
        assert p.lut_size == 33

def test_color_space_counts():
    """色彩空间统计正确"""
    log_count = sum(1 for p in PRESETS if p.color_space == "log")
    rec709_count = sum(1 for p in PRESETS if p.color_space == "709")
    assert log_count == 74
    assert rec709_count == 68

def test_apply_709_preset(test_image):
    """709 LUT 套用后尺寸不变，像素值有效"""
    p = [x for x in PRESETS if x.color_space == "709"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(str(test_image), p, out)
    from PIL import Image
    img = Image.open(out)
    original = Image.open(test_image)
    assert img.size == original.size
    arr = np.array(img)
    assert arr.min() >= 0 and arr.max() <= 255
    Path(out).unlink()  # cleanup

def test_apply_log_preset(test_image):
    """log LUT 套用（含转换）后尺寸不变"""
    p = [x for x in PRESETS if x.color_space == "log"][0]
    out = str(TEST_DIR / f"test_apply_{p.name}.jpg")
    apply_lut(str(test_image), p, out)
    from PIL import Image
    img = Image.open(out)
    original = Image.open(test_image)
    assert img.size == original.size
    Path(out).unlink()
```

- [ ] **Step 2: 运行测试**

```bash
.venv/Scripts/pip.exe install pytest pillow -q --proxy=""
.venv/Scripts/pytest tests/test_processor.py -v
```

---

### Task 5: app.html GUI

**文件：**
- 创建: `app.html`

- [ ] **Step 1: 创建单页 HTML GUI**

HTML 页面包含：
- 左侧：图片上传区（拖拽 + 点击）
- 右侧：调色预览区（canvas 显示）
- 中间：文本输入 + 下拉预设选择 + 应用按钮
- 底部：下载按钮

通信方式：由于纯前端无后端，两种方案：
  A. 浏览器内置 Python HTTP 端点（Gradio 式）
  B. 纯前端 JavaScript 调 Python WebSocket/HTTP Bridge

**推荐方案：** 浏览器页面上传图片 → JS fetch 到本地 Python 微服务 → 返回处理后图片

在项目根目录另写一个 `serve.py`（最小 Flask/FastAPI 或不依赖框架的 http.server）作为本地 API server。app.html 通过 fetch 调 `localhost:8765/api/apply`。

app.html 结构：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>ProjectLUT · 一句话调色</title>
  <style>
    body { font-family: system-ui; max-width: 900px; margin: 40px auto; }
    .container { display:flex; gap:20px; }
    .panel { flex:1; border:2px dashed #ccc; border-radius:8px; min-height:300px;
             display:flex; align-items:center; justify-content:center; }
    input, select, button { font-size:16px; padding:8px 16px; margin:8px 0; }
    #preview { max-width:100%; display:none; }
  </style>
</head>
<body>
  <h1>ProjectLUT · 一句话调色</h1>
  <div class="container">
    <div class="panel" id="drop-zone">
      <p>拖入图片或点击上传</p>
      <input type="file" id="upload" accept="image/*" hidden>
    </div>
    <div class="panel">
      <img id="preview">
      <p id="preview-placeholder">调色结果预览</p>
    </div>
  </div>
  <div>
    <input type="text" id="query" placeholder="描述你想要的调色风格..." style="width:60%">
    <select id="preset-select"></select>
    <button id="apply-btn">套用并预览</button>
    <button id="download-btn" disabled>下载结果</button>
  </div>
  <script src="app.js"></script>
</body>
</html>
```

JS 逻辑（app.js）：
```javascript
const API = 'http://localhost:8765';

document.getElementById('apply-btn').addEventListener('click', async () => {
  const query = document.getElementById('query').value;
  const file = document.getElementById('upload').files[0];
  if (!file || !query) return;
  
  const form = new FormData();
  form.append('image', file);
  form.append('query', query);
  
  const resp = await fetch(API + '/api/apply', { method: 'POST', body: form });
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  document.getElementById('preview').src = url;
  document.getElementById('preview').style.display = 'block';
  document.getElementById('download-btn').disabled = false;
  document.getElementById('download-btn').onclick = () => {
    const a = document.createElement('a');
    a.href = url; a.download = 'result.jpg'; a.click();
  };
});
```

同时创建 `serve.py`（最小 HTTP server）：

```python
"""ProjectLUT 本地 API Server"""
import io, json, cgi
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from src.lut.direct_embed import build_index, search
from src.lut.parser import load_presets
from src.lut.processor import apply_lut

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/apply':
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                     environ={'REQUEST_METHOD':'POST'})
            img_data = form['image'].file.read()
            query = form['query'].value
            
            # save temp input
            tmp_in = Path('/tmp/plut_input.jpg')
            tmp_in.write_bytes(img_data)
            
            # search + apply
            build_index()
            results = search(query, top_n=1)
            name = results[0][0].split(' — ')[0] if results else None
            presets = load_presets()
            preset = next((p for p in presets if p.name == name), None)
            
            tmp_out = Path('/tmp/plut_output.jpg')
            apply_lut(str(tmp_in), preset, str(tmp_out))
            
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(tmp_out.read_bytes())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    print('ProjectLUT API server at http://localhost:8765')
    HTTPServer(('localhost', 8765), Handler).serve_forever()
```

- [ ] **Step 2: 启动 server 验证**

```bash
.venv/Scripts/python.exe serve.py &
# 浏览器打开 app.html
# 上传图片 → 输入描述 → 点击套用 → 预览结果 → 下载
```
