"""Create a simple test image"""
import numpy as np
from PIL import Image

# 生成一张彩色渐变测试图 (300x200, RGB)
w, h = 400, 300
img = np.zeros((h, w, 3), dtype=np.uint8)
for y in range(h):
    for x in range(w):
        img[y, x, 0] = int(255 * x / w)        # R: 左→右
        img[y, x, 1] = int(255 * y / h)        # G: 上→下
        img[y, x, 2] = int(128 + 127 * np.sin(x / 50.0))  # B: 正弦
Image.fromarray(img).save(r"D:\WorkSpace\ProjectLUT\test_image.jpg")
print("Saved: test_image.jpg")
