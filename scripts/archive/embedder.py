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

# 支持两种运行方式: `python src/lut/embedder.py` 和 `python -m src.lut.embedder`
try:
    from .parser import load_presets, presets_to_texts
except ImportError:
    from parser import load_presets, presets_to_texts

WORKING_DIR = ".lightrag_lut_data"
OLLAMA_HOST = "http://localhost:11434"


def create_embedder() -> LightRAG:
    """创建配置好的 LightRAG 实例（Ollama qwen3:8b + bge-m3）"""
    return LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name="qwen3:8b",
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
