"""
CLI 入口 — lut 命令

用法:
    lut index               构建向量索引
    lut search <query>      语义检索 LUT 预设
    lut list                列出全部预设名称
"""

import argparse
import sys
from pathlib import Path

from .direct_embed import build_index, search, get_stats, get_history
from .parser import load_presets


def cmd_index(args):
    """构建向量索引"""
    build_index(force=True)
    print("索引构建完成 — .lut_vectors/")


def cmd_search(args):
    """语义检索"""
    # 确保索引存在
    build_index()
    results = search(args.query, top_n=args.n)
    for text, score, _ in results:
        if args.short:
            # 仅输出预设名称（第一部分）
            name = text.split(" — ")[0]
            print(name)
        else:
            print(f"{score:.4f}  {text}")


def cmd_list(args):
    """列出所有预设"""
    presets = load_presets()
    for p in presets:
        print(p.name)


def cmd_stats(args):
    s = get_stats()
    print(f"总搜索次数: {s['total']}")
    print(f"\n热门查询 Top-10:")
    for q, cnt in s["top_queries"]:
        print(f"  {cnt:4d}  {q}")


def cmd_stats_cold(args):
    s = get_stats(cold_threshold=args.t)
    print(f"结果数 ≤ {args.t} 的查询 ({len(s['cold_queries'])} 条):")
    for q, cnt in s["cold_queries"]:
        print(f"  [{cnt}结果] {q}")


def cmd_history(args):
    rows = get_history(args.n)
    for r in rows:
        print(f"{r['at']}  [{r['count']}条结果, {r['ms']}ms]  {r['query']}")


def cmd_apply(args):
    """套 LUT 到图片"""
    from .direct_embed import build_index, search
    from .parser import load_presets
    from .processor import apply_lut

    build_index()
    results = search(args.query, top_n=args.n)
    if not results:
        print("未找到匹配的预设")
        return

    text, score, _ = results[args.n - 1]
    name = text.split(" — ")[0]

    presets = load_presets()
    preset = next((p for p in presets if p.name == name), None)
    if preset is None:
        print(f"预设 '{name}' 未找到")
        return

    output = args.output or f"{Path(args.input).stem}_{name}.jpg"
    apply_lut(args.input, preset, output)
    print(f"已输出: {output}")


def main():
    parser = argparse.ArgumentParser(
        prog="lut",
        description="LUT 调色预设语义检索工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # index
    sub.add_parser("index", help="构建向量索引")

    # search
    p_search = sub.add_parser("search", help="语义检索 LUT 预设")
    p_search.add_argument("query", type=str, help="搜索描述，如'冷色调胶片感'")
    p_search.add_argument("-n", type=int, default=5, help="返回数量 (默认5)")
    p_search.add_argument("-s", "--short", action="store_true", help="简洁模式，仅显示预设名称")

    # list
    sub.add_parser("list", help="列出全部预设名称")

    # apply
    p_apply = sub.add_parser("apply", help="套 LUT 到图片")
    p_apply.add_argument("query", type=str, help="搜索描述或预设名称")
    p_apply.add_argument("input", type=str, help="输入图片路径")
    p_apply.add_argument("-o", "--output", type=str, default=None, help="输出路径（默认自动命名）")
    p_apply.add_argument("-n", type=int, default=1, help="使用第N个匹配结果")

    # stats
    sub.add_parser("stats", help="搜索统计概览")
    p_stats_cold = sub.add_parser("stats-cold", help="未命中查询")
    p_stats_cold.add_argument("-t", type=int, default=0, help="结果数阈值 (默认0=无结果)")

    # history
    p_history = sub.add_parser("history", help="最近搜索记录")
    p_history.add_argument("-n", type=int, default=20, help="显示条数 (默认20)")

    args = parser.parse_args()
    cmds = {"index": cmd_index, "search": cmd_search, "list": cmd_list,
            "stats": cmd_stats, "stats-cold": cmd_stats_cold, "history": cmd_history,
            "apply": cmd_apply}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
