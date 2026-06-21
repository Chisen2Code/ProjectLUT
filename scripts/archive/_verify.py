import urllib.request, json

r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping", timeout=5)
print("PING:", r.read().decode())

req = urllib.request.Request(
    "http://127.0.0.1:8765/api/search",
    json.dumps({"query":"冷色调胶片感","top_n":5}).encode(),
    {"Content-Type":"application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=30)
data = json.loads(r.read().decode("utf-8"))
for item in data["results"]:
    print(f"  {item['score']:.3f}  {item['preset_name']}")
print("OK")
