# LightRAG 功能模块架构

> 提炼自 [GitHub README](https://github.com/HKUDS/LightRAG) 及 `docs/` 目录
> 版本: v1.5.3 | 提炼日期: 2026-06-16

## 模块全景图

```
                          LightRAG 架构
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐         ┌──────▼──────┐       ┌──────▼──────┐
   │ 输入层  │         │   处理引擎   │       │   查询层    │
   └────┬────┘         └──────┬──────┘       └──────┬──────┘
        │                     │                     │
   · SDK API              · 文档分块            · 5 种查询模式
   · REST API             · 实体-关系抽取       · Reranker
   · WebUI                · 向量嵌入            · 引用溯源
        │                 · 图谱构建               │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
         │ LLM 层  │    │ 存储层    │   │ 多模态层  │
         └─────────┘    └───────────┘   └───────────┘
         4 种角色        4 类存储后端     MinerU/Docling
         多Provider      PostgreSQL      Native解析器
         Ollama/OpenAI   MongoDB         图片/表格/公式
         Anthropic等     OpenSearch
                         Neo4j/Milvus等
```

---

## 一、输入层

### SDK (Python)

```python
from lightrag import LightRAG
rag = LightRAG(working_dir="./data", ...)
await rag.ainsert("文本内容")         # 插入文本
await rag.ainsert(["doc1", "doc2"])   # 批量插入
await rag.ainsert(open("file.txt").read())  # 文件内容
```

### REST API + WebUI

```bash
lightrag-server  # 启动服务，端口 9621
```

提供完整 REST API 和浏览器界面，支持可视化图谱。

---

## 二、处理引擎（管道）

### 文档分块 (Chunking)

| 策略 | 描述 |
|------|------|
| Fix | 固定大小切分 |
| Recursive | 递归语义切分 |
| Vector | 基于向量相似度的智能切分 |
| Paragraph | 按段落边界切分（保留语义完整性） |

### 实体-关系抽取

LLM 从文本中提取实体和关系，构建知识图谱节点和边。

```
输入文本 → LLM(EXTRACT角色) → {
    entities: [{name, type, description}, ...],
    relations: [{source, target, description}, ...]
}
```

- `ENTITY_EXTRACTION_USE_JSON=true` → JSON 格式输出，更稳定
- `SUMMARY_LANGUAGE=Chinese` → 实体名称和摘要用中文

### 向量嵌入

bge-m3 (1024-dim) 对三种内容做嵌入：
- 文本块 (text chunks)
- 实体 (entities)
- 关系 (relationships)

**约束：嵌入模型必须在索引前确定，查询阶段必须用同一模型。**

### 知识图谱构建

NetworkX 图存储（默认），支持 Neo4j 迁移。

---

## 三、LLM 层 — 四角色独立配置

| 角色 | 用途 | 推荐模型大小 |
|------|------|-------------|
| **EXTRACT** | 实体-关系抽取 | 中等（qwen3:4b 可用） |
| **QUERY** | 查询回答生成 | 较大（Qwen3-30B-A3B） |
| **KEYWORDS** | 关键词提取与过滤 | 小（1.5B 即可） |
| **VLM** | 视觉-语言分析（图片/表格） | 视觉模型 |

每角色可独立配置 Provider、model、host、async、timeout。

```bash
# 环境变量示例
EXTRACT_LLM_MODEL=qwen3:4b
QUERY_LLM_MODEL=qwen3:8b
KEYWORDS_LLM_MODEL=qwen3:1.5b
VLM_LLM_MODEL=qwen3-vl:8b
```

---

## 四、存储层

### 四类存储

| 存储 | 默认 | 生产替代 |
|------|------|---------|
| KV_STORAGE | JSON文件 (JsonKVStorage) | PostgreSQL / MongoDB |
| VECTOR_STORAGE | NanoVectorDB (JSON) | Milvus / Qdrant / PGVector |
| GRAPH_STORAGE | NetworkX (GraphML) | Neo4j / Memgraph |
| DOC_STATUS | JSON文件 | PostgreSQL / MongoDB |

### 单后端统一方案

PostgreSQL / MongoDB / OpenSearch 可统一替代全部四类存储。

---

## 五、查询层

### 五种查询模式

```
local   → 知识图谱：实体级精准检索
global  → 知识图谱：全图遍历，跨实体关系推理
hybrid  → local + global 融合
naive   → 纯向量相似度（不用 KG）
mix     → local + global + naive 三者融合（默认）
```

### Reranker

```bash
RERANK_BINDING=ollama
RERANK_MODEL=bge-reranker-v2-m3
```
启用后检索质量显著提升，额外耗时 1-2 秒。

### 引用溯源

查询结果自动附带源文档引用和追踪信息。

---

## 六、多模态层（v1.5+ 已含 RAG-Anything）

### 文档解析引擎

| 引擎 | 覆盖格式 | 部署 |
|------|---------|------|
| Native | DOCX（原生） | 无需额外服务 |
| MinerU | PDF/图片/表格/公式 | `mineru-api` 本地服务 |
| Docling | PDF/Office | Python 库 |

### 配置

```bash
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
VLM_PROCESS_ENABLE=true
```

---

## 七、配置速查

### 本项目 (ProjectLUT) 当前配置

| 参数 | 值 |
|------|-----|
| LLM | Ollama qwen3:4b |
| Embedding | Ollama bge-m3:latest (1024-dim) |
| 存储 | 默认文件化 (开发阶段) |
| 查询模式 | hybrid (local+global) |
| 多模态 | 不需要（纯文本 LUT 名称） |

### 关键环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_BINDING` | LLM 提供商 | ollama |
| `LLM_MODEL` | LLM 模型名 | - |
| `EMBEDDING_BINDING` | 嵌入提供商 | ollama |
| `EMBEDDING_MODEL` | 嵌入模型名 | - |
| `EMBEDDING_DIM` | 嵌入维度 | 1024 |
| `MAX_ASYNC_LLM` | LLM 最大并发 | 4 |
| `MAX_PARALLEL_INSERT` | 并行插入文件数 | 1 |
| `EMBEDDING_BATCH_NUM` | 嵌入批量大小 | 10 |
| `ENTITY_EXTRACTION_USE_JSON` | JSON格式抽取 | false |
| `ENABLE_LLM_CACHE` | 查询结果缓存 | true |

---

## 参考资料

- [GitHub](https://github.com/HKUDS/LightRAG)
- [PyPI](https://pypi.org/project/lightrag-hku/)
- [论文](https://arxiv.org/abs/2410.05779)
- [原版 README 中文摘要](lightrag-readme-cn.md)
