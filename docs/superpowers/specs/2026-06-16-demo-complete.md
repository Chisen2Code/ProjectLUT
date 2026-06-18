# Demo 闭环设计

> 状态: 已审批 | 日期: 2026-06-16

## 目标

完成 `lut apply "描述" input.jpg -o output.jpg` 全链路。

## 五个环节

| # | 环节 | 文件 | 说明 |
|---|------|------|------|
| 1 | parser 补全 | `src/lut/parser.py` | 读 .cube RGB → `Preset.lut_data` (35937×3), `Preset.lut_size` (33) |
| 2 | processor | `src/lut/processor.py` | log→709 转换 + `colour.write_LUT()` / `colour.apply()` |
| 3 | CLI apply | `src/lut/cli.py` | `lut apply "query" input.jpg [-o output.jpg]` |
| 4 | 测试验收 | `tests/` | 示例图片 + 覆盖测试 |
| 5 | GUI | `app.html` | 浏览器单页面：选图 → 描述 → 预览 → 下载 |

## 测试预设抽样

覆盖色彩空间（log/709）、类别、合集三轴：

| 预设 | 空间 | 类别 |
|------|------|------|
| cold低饱和冷709 | 709 | 电影感 |
| 柯达2383-709 | 709 | 柯达系列 |
| 富士3513-709 | 709 | 胶片系列 |
| 动漫风709 | 709 | Apple专用 |
| 默片时代709 | 709 | iPhone合集3 |
| cine4电影感墨绿 | log | Apple专用(log) |
| 柯达5213 | log | 柯达系列 |
| FAKE理光负片 | log | FAKE5207&淡雅 |
| N-cine1复古暖调 | log | CINE系列 |
| 爆改富士cn | log | 富士改款 |

测试文件结构：
```
tests/
├── 测试样例1.jpg              # 原始测试图片（用户提供）
├── 测试样例1-cold低饱和冷709/  # 输出: 套该预设的结果
├── 测试样例1-柯达2383-709/
├── 测试样例1-富士3513-709/
└── ...
```

## 验证标准

- [ ] 152 个 .cube 全部可解析，`lut_size=33`, `lut_data` 形状 (35937, 3)
- [ ] parser 正确标注 log (74个) / 709 (68个)
- [ ] processor 对 709 LUT 直接套用，输出尺寸不变
- [ ] processor 对 log LUT 自动做 log→709 转换后套用
- [ ] `lut apply "冷色调胶片感" test.jpg` 成功输出
- [ ] `lut apply "富士胶片风格" test.jpg` 成功输出
- [ ] GUI 文件上传 + 描述输入 + 预览生效

## 不在此范围

- 视频处理
- Blender MCP
- AceTone tokenizer
- GUI 打包为独立应用
