# LUT 嵌入管道设计

> 日期: 2026-06-16 | 状态: 待用户审阅

## 目标

将 `LUT预设1/` 下 152 个 .cube LUT 预设通过 LightRAG + bge-m3 向量化入库，支持"一句话描述 → Top-N 匹配 LUT 名称"。

## 输入

- `LUT预设1/` — 152 个 .cube 文件（目录名和文件名已去"林馆长"前缀）
- Ollama 本地服务：bge-m3:latest (嵌入) + qwen3:4b (实体提取)

## 输出

- `.lightrag_lut_data/` — LightRAG 工作目录
  - `vdb_chunks.json` — NanoVectorDB 向量存储 (1024 维)
  - `vdb_entities.json` — 实体向量
  - `graph_chunk_entity_relation.graphml` — 知识图谱
  - `kv_store_full_docs.json` — 原始文档
- 查询返回：匹配的 LUT 名称 + 简要说明

## 架构

```
parser.py                    embedder.py
─────────                    ───────────
152 .cube 文件               LightRAG 实例
    │                            │
    ▼                            │  llm_model_func → Ollama qwen3:4b
Preset × 152                     │  embedding_func → Ollama bge-m3 (1024-dim)
    │                            │
    ▼                            ▼
to_search_text() ────────→  rag.ainsert(texts)
                                 │
                                 ▼
                          知识图谱 + 向量索引
                                 │
用户输入 ────────────────→  rag.aquery(mode="hybrid")
                                 │
                                 ▼
                          Top-N LUT 名称
```

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 嵌入文本 | Preset.to_search_text() = "名称 — 色彩空间 — 类别" | 含上下文比纯名称检索更准确 |
| 查询模式 | hybrid | 向量粗筛 + 图谱精排 |
| 存储位置 | `.lightrag_lut_data/` | 与测试数据 `.lightrag_test_data/` 隔离 |
| LLM | qwen3:4b | 已本地可用，8B 量级在实体提取中够用 |
| 嵌入模型 | bge-m3 (1024-dim) | 已本地可用，中文多语言最佳 |

## 验证标准

- [ ] 152 个 LUT 全部入库，parser 和 embedder 串联无报错
- [ ] "冷色调胶片感" 返回含 cold/柯达5213 的 LUT
- [ ] "富士胶片风格" 返回含 富士3513/富士CN 的 LUT
- [ ] "动漫明亮" 返回含 动漫风 的 LUT
- [ ] 查询耗时 < 5 秒（hybrid 模式含 LLM 调用）

## 文件清单

| 文件 | 职责 |
|------|------|
| `src/lut/parser.py` | ✅ 已写，输出 Preset 列表 |
| `src/lut/embedder.py` | 待写：创建 LightRAG 实例，批量插入 152 个预设 |
| `src/lut/matcher.py` | 待写：查询接口封装 |
| `tests/test_lightrag_integration.py` | ✅ 冒烟测试已验证通路 |

## 不在此范围

- MinerU 文档解析（PDF/图片留到论文 RAG 阶段再用）
- VL 模型图像匹配（留到视频适配阶段）
- CLI 入口（parser + embedder 跑通后补）
