"""启动脚本 — 把所有输出写到 log 文件，避免管道缓冲阻塞 HTTP 服务。"""
import sys, os
from pathlib import Path

os.chdir(Path(__file__).parent)

log_path = Path("_serve.log")
log_file = open(log_path, "w", encoding="utf-8", buffering=1)
sys.stdout = log_file
sys.stderr = log_file

exec(open("serve.py", encoding="utf-8").read())
