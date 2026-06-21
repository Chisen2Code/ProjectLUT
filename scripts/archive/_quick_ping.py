import urllib.request
try:
    r = urllib.request.urlopen("http://127.0.0.1:8765/api/ping", timeout=3)
    print("PING OK:", r.read().decode())
except Exception as e:
    print("PING FAIL:", e)
