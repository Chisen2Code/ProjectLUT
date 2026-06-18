# LightRAG README 中文摘要

> 来源: https://github.com/HKUDS/LightRAG
> 提取日期: 2026-06-16 | 版本: v1.5.3

## 项目定位

LightRAG 是港大数据智能实验室(HKUDS)开发的轻量级 RAG 框架，使用**双层架构**同时管理知识图谱(KG)和向量嵌入。它是 Microsoft GraphRAG 的高效替代品。

## 核心特性

1. **深度上下文理解** — 图结构索引捕获实体间的复杂语义依赖
2. **检索全面性** — 双层检索机制融合具体事实与抽象概念
3. **极致效率** — 不依赖社区报告或多跳推理，大幅减少 LLM 调用
4. **动态数据适应** — 增量更新，新数据合并到现有图，无需重建全局索引

## 五种查询模式

| 模式 | 用途 |
|------|------|
| local | 精确匹配局部上下文和特定实体 |
| global | 宏观主题、跨文档推理、实体关系链 |
| hybrid | local + global 融合 |
| naive | 传统向量相似度检索（不用知识图谱） |
| mix | local + global + naive 全融合（默认，精度最高） |

## 四类存储后端

| 存储类型 | 用途 | 默认实现 |
|---------|------|---------|
| KV_STORAGE | LLM缓存、分块结果、抽取结果 | JSON文件 |
| VECTOR_STORAGE | 向量嵌入 | NanoVectorDB |
| GRAPH_STORAGE | 知识图谱 | NetworkX |
| DOC_STATUS_STORAGE | 文档列表 | JSON文件 |

生产环境可用 PostgreSQL/MongoDB/OpenSearch 统一替代全部四类。

## LLM 角色化配置（v1.5+）

四种独立角色：EXTRACT（抽取）、QUERY（查询）、KEYWORDS（关键词）、VLM（视觉）

## 多模态处理（v1.5+）

- 解析引擎：MinerU / Docling / Native
- 支持 PDF、Office、图片、表格、公式

## 安装

```bash
# SDK
pip install lightrag-hku

# 完整 API 服务
uv tool install "lightrag-hku[api]"
```

## 环境变量

```bash
# LLM
LLM_BINDING=ollama
LLM_MODEL=qwen3:4b
LLM_BINDING_HOST=http://localhost:11434

# Embedding
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_DIM=1024
EMBEDDING_BINDING_HOST=http://localhost:11434

# 存储（默认文件化，无需额外配置）
# 生产可切换: LIGHTRAG_GRAPH_STORAGE=Neo4JStorage 等

# 文档处理
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
VLM_PROCESS_ENABLE=true

# 并发优化
MAX_ASYNC_LLM=8
MAX_PARALLEL_INSERT=3
EMBEDDING_FUNC_MAX_ASYNC=16
EMBEDDING_BATCH_NUM=32
```
