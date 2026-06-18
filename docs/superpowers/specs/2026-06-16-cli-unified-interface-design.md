# CLI 统一接口设计

> 日期: 2026-06-16 | 状态: 已审批

## 目标

统一 `src/lut/` 模块，提供 `lut` CLI 命令行入口，默认走 direct bge-m3 嵌入方案，LightRAG 方案保留备用。

## 架构

```
CLI (cli.py)
 │
 ├─ 默认路径 ──→ direct_embed.py ──→ bge-m3 + numpy ──→ Top-N LUT
 │
 └─ RAG 路径 ──→ embedder.py ──→ LightRAG (论文 RAG 阶段启用)
```

## CLI 接口

```bash
lut index                           # 构建向量索引
lut search "冷色调胶片感"            # 搜索（默认 Top-5）
lut search "冷色调胶片感" -n 10     # 指定 Top-N
lut search "冷色调胶片感" -s        # 简洁模式，仅名称
lut list                            # 列出全部预设名称
```

## 文件变动

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/lut/cli.py` | 新建 | argparse CLI，调 direct_embed |
| `pyproject.toml` | 修改 | 注册 `lut` console_scripts 入口 |
| `CLAUDE.md` | 修改 | 更新状态，反映 direct_embed 为主路径 |
| `src/lut/direct_embed.py` | 修改 | 给 `build_index()` 加 `force` 参数已支持，无需改动 |
| `src/lut/embedder.py` | 不动 | 保留备用 |
| `src/lut/matcher.py` | 不动 | 保留备用 |
| `docs/architecture.md` | 不动 | 架构图不变 |

## 验证标准

- [ ] `lut index` 构建成功，`.lut_vectors/` 目录生成
- [ ] `lut search "富士胶片风格"` 返回富士 3513/CN/ASTIA
- [ ] `lut list | wc -l` = 152
- [ ] `lut search "冷色调胶片感" -s` 无分数显示

## 不在此范围

- LightRAG 论文 RAG 暴露为 CLI 子命令（将来再加）
- .cube 内部色彩数据解析（留到 parser 升级阶段）
- 视频/blender MCP/AceTone（后续阶段）
