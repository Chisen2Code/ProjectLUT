import urllib.request, json

r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping", timeout=5)
print("1. PING:", r.read().decode().strip())

req = urllib.request.Request(
    "http://127.0.0.1:8765/api/search",
    json.dumps({"query":"暖调电影感","top_n":5}).encode(),
    {"Content-Type":"application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=30)
data = json.loads(r.read().decode("utf-8"))
print()
print("2. 搜索 '暖调电影感':")
for item in data["results"]:
    print(f"   {item['score']:.3f}  {item['preset_name']}")

# 首页 HTML
r = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5)
html = r.read().decode("utf-8")
has_drag = "dropZone" in html
has_apply = "doApply" in html
has_search = "doSearch" in html
print()
print(f"3. 首页 HTML: {len(html)} chars，包含拖拽区:{has_drag} doSearch:{has_search} doApply:{has_apply}")
print()
print("✅ 全部正常 — 请在浏览器打开 http://localhost:8765/")
