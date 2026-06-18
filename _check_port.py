import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(("127.0.0.1", 8765))
    print("PORT 8765 IS OPEN")
    s.close()
except Exception as e:
    print("PORT 8765 CLOSED:", e)
