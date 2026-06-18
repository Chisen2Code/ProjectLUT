import urllib.request, json

print("--- /api/ping ---")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping", timeout=5)
    print(r.read().decode("utf-8"))
except Exception as e:
    print("FAIL:", e)

print("\n--- /api/search ---")
req = urllib.request.Request(
    "http://127.0.0.1:8765/api/search",
    json.dumps({"query": "冷色调胶片感", "top_n": 3}).encode(),
    {"Content-Type": "application/json"},
    method="POST",
)
try:
    r = urllib.request.urlopen(req, timeout=30)
    data = json.loads(r.read().decode("utf-8"))
    for item in data["results"]:
        print(f"  {item['score']:.3f}  {item['preset_name']}")
    print(f"({data.get('ms')}ms)")
except Exception as e:
    print("FAIL:", e)

print("\n--- GET / ---")
try:
    r = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5)
    body = r.read().decode("utf-8")
    print("status:", r.status)
    print("first 300 chars:", body[:300])
except Exception as e:
    print("FAIL:", e)
