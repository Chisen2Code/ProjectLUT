import sys
try: import numpy; print(f"numpy {numpy.__version__} OK")
except ImportError: print("numpy MISSING")
try: from PIL import Image; import PIL; print(f"Pillow {PIL.__version__} OK")
except ImportError: print("Pillow MISSING")
try: import scipy; print(f"scipy {scipy.__version__} OK")
except ImportError: print("scipy MISSING")
print(f"Python {sys.version}")
