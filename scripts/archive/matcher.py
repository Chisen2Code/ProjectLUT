"""
LUT 语义匹配器

基于 LightRAG 知识图谱 + 向量索引，接收自然语言描述，返回最匹配的 LUT 预设名称。
"""

import asyncio

from lightrag import LightRAG, QueryParam

# 支持两种运行方式: `python src/lut/matcher.py` 和 `python -m src.lut.matcher`
try:
    from .embedder import create_embedder
except ImportError:
    from embedder import create_embedder


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
    await rag.initialize_storages()
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
