import urllib.request, json, time
try:
    resp = urllib.request.urlopen("http://localhost:8765/api/ping", timeout=5).read()
    print("PING:", resp.decode())
except Exception as e:
    print("PING FAIL:", e)
    raise SystemExit(1)

t0 = time.perf_counter()
req = urllib.request.Request(
    "http://localhost:8765/api/search",
    json.dumps({"query": "冷色调胶片感", "top_n": 5}).encode(),
    {"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
print(f"SEARCH ({time.perf_counter() - t0:.2f}s):")
for r in resp["results"]:
    print(f"  {r['score']:.3f}  {r['preset_name']}")
