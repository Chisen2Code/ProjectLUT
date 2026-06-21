import urllib.request, json, socket
socket.setdefaulttimeout(10)

r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping")
print("1. PING:", r.read().decode().strip())

req = urllib.request.Request(
    "http://127.0.0.1:8765/api/search",
    json.dumps({"query":"暖调电影感","top_n":5}).encode(),
    {"Content-Type":"application/json"}, method="POST")
r = urllib.request.urlopen(req)
data = json.loads(r.read().decode("utf-8"))
print()
print("2. 搜索 '暖调电影感':")
for item in data["results"]:
    print(f"   {item['score']:.3f}  {item['preset_name']}")

r = urllib.request.urlopen("http://127.0.0.1:8765/")
html = r.read().decode("utf-8")
print()
print(f"3. 首页 HTML: {len(html)} chars，包含拖拽区:{'dropZone' in html} doSearch:{'doSearch' in html} doApply:{'doApply' in html}")
print()
print("✅ 服务已就绪 — 请在浏览器打开 http://localhost:8765/")
