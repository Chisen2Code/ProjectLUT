# 色彩管线设计

> 为什么 sRGB 图片套 Log LUT 会炸、以及怎么修。

## 问题现象

套用影视/摄影类 Log LUT 后，JPG/PNG 成品图出现大面积高光橙色饱和溢出。冷白/电影感预设实际输出偏暖橙，与标题描述完全不符。

## 根因分析

### 基础认知：两类 LUT

| LUT 类型 | 目标输入 | 来源 | 在库数量 |
|----------|---------|------|---------|
| **sRGB 专用** | sRGB 成品图（JPG/PNG/GIF） | 709/Rec709 目录 | 68 |
| **Log 影视** | 摄影机 Log 素材（RAW/EXR/Log片段） | log 目录 | 74 (+10 未知) |

### 当前代码 bug

`processor.py` 的 `_log_to_709()` 对 Log 类 LUT 做了：

```python
linear = np.power(clip(img, 0, 1), 2.2)   # 模拟「去伽马」
result = np.power(linear, 1/2.2)            # 模拟「加伽马」
```

这只是一个 2.2 伽马的粗糙回环，**不是真正的色彩空间转换**。正确管线应该是：

```
sRGB 成品图 → 去 sRGB 伽马 → 线性光 → 编码为 Log C 空间 → 3D LUT 查表 → 解码 Log → 线性光 → 加 sRGB 伽马 → 输出
```

缺少中间两步（线性→Log 编码 + Log→线性解码），导致 Log LUT 把 sRGB 像素当 Log 值处理，产生严重的色相偏移和饱和溢出。

### 溢橙的视觉机制

- Log 编码值集中在低区，高区变化平缓
- sRGB 的高光部分（>0.8）在 Log 域中差距被压缩
- Log LUT 对「高区」的映射通常设计为向暖色偏移（模拟胶片乳剂的肩部暖化）
- 当 sRGB 高光被错误当作 Log 高光处理，暖化偏移被极端放大
- 结果：R 通道大量裁切到 255，G 通道偏高，形成橙黄色溢出

## 修复方案

### 核心管线

```
sRGB(in) → _srgb_to_linear() [正确分段 EOTF]
           → _linear_to_log() [Cineon 风格编码]
             → _apply_lut3d_fast() [3D LUT 三线性插值]
             → _log_to_linear() [Cineon 解码]
           → _linear_to_srgb() [正确分段 OETF]
         → _luma_attenuation() [高光橙色保护]
         → sRGB(out)
```

| 阶段 | 函数 | 数学原理 |
|------|------|---------|
| sRGB → Linear | `_srgb_to_linear` | IEC 61966-2-1 分段 EOTF |
| Linear → Log | `_linear_to_log` | Cineon-style: `log10(1+x*1023)/log10(1024)` |
| Log → Linear | `_log_to_linear` | 逆 Cineon: `(10^(x*log10(1024))-1)/1023` |
| Linear → sRGB | `_linear_to_srgb` | IEC 61966-2-1 分段 OETF |

### Log 曲线选择说明

当前方案采用 **Cineon 风格**对数曲线作为通用默认。原因：

1. 林馆长 LUT 库来自国内影视社群，绝大多数基于 DaVinci Resolve 制作，默认 Log 编码接近 Cineon
2. Cineon 曲线数学简单（单条对数公式），无需分段，纯 numpy 实现
3. 对于 Arri LogC / Sony S-Log / Canon C-Log 等精确曲线，本方案是近似而非精确

后续扩展路径：在 `Preset` 中增加 `log_curve` 字段（`"cineon"` / `"arri"` / `"slog"` / `"clog"`），可配置不同曲线。

### 高光衰减策略

像素亮度 > 0.85 时，按比例降低 R/G 通道：

| 通道 | 最大衰减 | 原理 |
|------|---------|------|
| R | 40% | 橙色主要来自 R，最需要抑制 |
| G | 25% | 辅助抑制，保护绿色调 |
| B | 0% | 冷色不衰减 |

衰减因子随亮度线性增长：`luma ∈ [0.85, 1.0]` → `factor ∈ [0, 1]`。

### GIF 拦截

影视 Log LUT 对 GIF 直接拒绝（8 位索引色面板天生调色失真，输出无意义）。

## 验证策略

采用调研确认的**轻量验证组合**（~25 行纯 numpy，零依赖）：

### 裁切检测

```python
clipped_r = (output[..., 0] >= 252).mean()
assert clipped_r < 0.01  # R 通道裁切像素 < 1%
```

溢橙的本质是 R 通道大量裁切到 255，此检测直接命中。

### 色彩丰富度比值

Hasler & Susstrunk (2003) M3 指标，完全在 RGB 空间计算：

```python
def colorfulness(im):
    rg = np.abs(im[..., 0] - im[..., 1])
    yb = np.abs(0.5*(im[..., 0] + im[..., 1]) - im[..., 2])
    return np.sqrt(rg.std()**2 + yb.std()**2) + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2)

ratio = colorfulness(output) / colorfulness(input)
assert ratio < 1.5  # 饱和度上涨不超过 50%
```

溢橙使 R/G 差异暴增 → rg 项标准偏差剧烈上升 → ratio 爆表。可准确区分「正常调色」和「饱和溢出」。

## 参考

- [IEC 61966-2-1:1999 sRGB 标准](https://webstore.iec.ch/publication/6169)
- [Hasler & Susstrunk, "Measuring colorfulness in natural images", 2003](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/5008/1/Measuring-colorfulness-in-natural-images/10.1117/12.477378.short)
- [Cineon Log 编码详解](https://www.oscars.org/science-technology/sci-tech-projects/cineon)
