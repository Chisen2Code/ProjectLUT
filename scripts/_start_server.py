import os, sys
os.chdir(r'D:\WorkSpace\ProjectLUT')
sys.path.insert(0, r'D:\WorkSpace\ProjectLUT\src')

# --- run serve.py ---
with open(r'D:\WorkSpace\ProjectLUT\serve.py', encoding='utf-8') as f:
    code = f.read()
exec(compile(code, 'serve.py', 'exec'))
