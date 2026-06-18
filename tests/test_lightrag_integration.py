"""
LightRAG + Ollama 集成验证

验证 LightRAG 能否在本项目现有基础设施（Ollama + bge-m3 + qwen3:4b）上正常运行。
此测试确认基础检索通路的可用性，为后续 src/lut/embedder.py 提供参考基线。
"""

import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc


WORKING_DIR = "d:/WorkSpace/ProjectLUT/.lightrag_test_data"
OLLAMA_HOST = "http://localhost:11434"


def create_rag():
    """创建 LightRAG 实例，使用本地 Ollama 模型"""
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


async def _smoke_test():
    """基础冒烟测试：初始化存储 → 插入 LUT 数据 → 查询 → 验证"""
    rag = create_rag()
    await rag.initialize_storages()
    await rag.ainsert([
        "cold低饱和冷709 — 冷色调低饱和，适用REC709",
        "柯达5213-709 — 柯达胶片模拟，中性偏冷，REC709",
        "warm暖调709 — 暖色调金色高光，REC709",
    ])
    result = await rag.aquery(
        "冷色调胶片感适合什么LUT?",
        param=QueryParam(mode="naive"),
    )
    assert result is not None and len(result) > 0, "查询应返回非空结果"
    print(f"[OK] LightRAG + Ollama 通路验证成功")
    print(f"  查询: '冷色调胶片感' → 返回: {result[:200]}...")


if __name__ == "__main__":
    asyncio.run(_smoke_test())
