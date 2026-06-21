import urllib.request, json, time, sys

# 最多等 90 秒，每秒 ping 一次
for i in range(90):
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping", timeout=2)
        print(f"[{i+1}s] /api/ping OK:", r.read().decode())
        break
    except Exception as e:
        if i < 3 or i % 10 == 9:
            print(f"[{i+1}s] 等待服务就绪... ({e})")
        time.sleep(1)
else:
    print("服务未就绪，超时")
    sys.exit(1)

print()
print("--- GET / (app.html) ---")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5)
    body = r.read().decode("utf-8")
    print(f"status: {r.status}, length: {len(body)}")
    has_doctype = "<!DOCTYPE" in body
    has_search = "doSearch" in body
    has_apply = "doApply" in body
    print(f"has HTML: {has_doctype}, has doSearch(): {has_search}, has doApply(): {has_apply}")
except Exception as e:
    print("FAIL:", e)

print()
print("--- POST /api/search (暖调电影感) ---")
try:
    req = urllib.request.Request(
        "http://127.0.0.1:8765/api/search",
        json.dumps({"query": "暖调电影感", "top_n": 3}).encode(),
        {"Content-Type": "application/json"}, method="POST")
    r = urllib.request.urlopen(req, timeout=30)
    data = json.loads(r.read().decode("utf-8"))
    for item in data["results"]:
        print(f"  {item['score']:.3f}  {item['preset_name']}")
    print(f"({data.get('ms')}ms)")
except Exception as e:
    print("FAIL:", e)

print()
print("✅ 端到端验证完成")
