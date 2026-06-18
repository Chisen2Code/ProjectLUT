# LUT Embedder 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**目标：** 串联 parser.py → LightRAG → bge-m3，将 152 个 LUT 预设向量化入库并支持语义查询。

**架构：** embedder.py 初始化 LightRAG(Ollama qwen3:4b + bge-m3)，调用 parser.load_presets() 获取 Preset 列表，批量 ainsert() 嵌入。matcher.py 封装查询接口。

**技术栈：** Python 3.11, LightRAG 1.5.3, Ollama (qwen3:4b + bge-m3), NanoVectorDB, NetworkX

---

### Task 1: 修复 parser.py 未使用的 import

**文件：** `src/lut/parser.py:13`

- [ ] **Step 1: 删除 `field` import**

```python
# 改前
from dataclasses import dataclass, field

# 改后
from dataclasses import dataclass
```

- [ ] **Step 2: 验证 parser 仍可运行**

```bash
.venv/Scripts/python.exe src/lut/parser.py LUT预设1
```
Expected: 解析完成: 152 个 LUT 预设

---

### Task 2: 写 embedder.py

**文件：** `src/lut/embedder.py`

- [ ] **Step 1: 创建文件**

```python
"""
LUT 预设嵌入管道

使用 LightRAG + Ollama bge-m3 将 parser 输出的 Preset 列表向量化，
存储到 .lightrag_lut_data/ 目录，构建知识图谱 + 向量索引。
"""

import asyncio
from pathlib import Path

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

from .parser import load_presets, presets_to_texts

WORKING_DIR = ".lightrag_lut_data"
OLLAMA_HOST = "http://localhost:11434"


def create_embedder() -> LightRAG:
    """创建配置好的 LightRAG 实例（Ollama qwen3:4b + bge-m3）"""
    return LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name="qwen3:4b",
        llm_model_kwargs={
            "host": OLLAMA_HOST,
            "options": {"num_ctx": 4096, "temperature": 0.3},
        },
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts, embed_model="bge-m3:latest", host=OLLAMA_HOST
            ),
        ),
    )


async def embed_all(presets_dir: str = "LUT预设1") -> LightRAG:
    """
    加载所有 LUT 预设并向量化入库。

    Args:
        presets_dir: LUT 预设根目录

    Returns:
        已完成索引的 LightRAG 实例
    """
    presets = load_presets(presets_dir)
    texts = presets_to_texts(presets)
    print(f"加载 {len(presets)} 个预设，准备向量化...")

    rag = create_embedder()
    await rag.initialize_storages()
    await rag.ainsert(texts)
    print(f"向量化完成: {len(presets)} 个预设已入库")
    return rag


def main():
    """CLI 入口：一键嵌入"""
    asyncio.run(embed_all())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行嵌入脚本（本项目暂不初始化 git，跳过 commit 步骤）**

```bash
.venv/Scripts/python.exe src/lut/embedder.py
```
Expected: 加载 152 个预设 → 向量化完成

> 注意：f'{i} 首次运行约需 10-20 分钟（152 × LLM 实体提取 + bge-m3 嵌入）。后续增量插入仅处理新增项。

---

### Task 3: 写 matcher.py

**文件：** `src/lut/matcher.py`

- [ ] **Step 1: 创建文件**

```python
"""
LUT 语义匹配器

基于 LightRAG 知识图谱 + 向量索引，接收自然语言描述，返回最匹配的 LUT 预设名称。
"""

import asyncio

from lightrag import LightRAG, QueryParam

from .embedder import create_embedder


async def match_luts(
    query: str,
    top_n: int = 5,
    mode: str = "hybrid",
) -> str:
    """
    语义匹配 LUT 预设。

    Args:
        query: 自然语言描述，如"冷色调胶片感"
        top_n: 返回结果数
        mode: 查询模式 (naive|local|global|hybrid|mix)

    Returns:
        LightRAG 查询结果文本
    """
    rag = create_embedder()
    result = await rag.aquery(
        query,
        param=QueryParam(mode=mode),
    )
    return result


def match(query: str, top_n: int = 5, mode: str = "hybrid") -> str:
    """同步封装"""
    return asyncio.run(match_luts(query, top_n, mode))


def main():
    """CLI 入口：交互查询"""
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "冷色调胶片感"
    print(f"查询: {query}\n")
    result = match(query)
    print(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 matcher 可 import（不查询，embedder 跑完后再测）**

```bash
.venv/Scripts/python.exe -c "from src.lut.matcher import match; print('import OK')"
```
Expected: import OK

---

### Task 4: 端到端验证

- [ ] **Step 1: 验证 embedder 产物存在**

```bash
ls .lightrag_lut_data/vdb_chunks.json .lightrag_lut_data/graph_chunk_entity_relation.graphml
```
Expected: 两个文件均存在

- [ ] **Step 2: 查询"冷色调胶片感"**

```bash
.venv/Scripts/python.exe src/lut/matcher.py 冷色调胶片感
```
Expected: 返回含 cold / 柯达5213 相关的 LUT 名称

- [ ] **Step 3: 查询"富士胶片风格"**

```bash
.venv/Scripts/python.exe src/lut/matcher.py 富士胶片风格
```
Expected: 返回含 富士3513 / 富士CN 的 LUT

- [ ] **Step 4: 查询"动漫明亮"**

```bash
.venv/Scripts/python.exe src/lut/matcher.py 动漫明亮
```
Expected: 返回含 动漫风 的 LUT

---

### Task 5: 更新文档

**文件：** `CLAUDE.md`

- [ ] **Step 1: 更新项目状态**

将 CLAUDE.md 中 `src/lut/` 状态从"待填充"改为"✅ embedder/matcher 已完成"，LightRAG 状态改为"✅ 152 LUT 已向量化"。
