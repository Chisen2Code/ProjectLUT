# CLI 统一接口实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**目标：** 提供 `lut index | search | list` 三条子命令，默认走 direct_embed 方案。

**架构：** argparse 解析 → direct_embed.build_index() / search() → 终端输出。

**技术栈：** Python 3.11, argparse, hatchling console_scripts

---

### Task 1: 写 cli.py

**文件：** `src/lut/cli.py`

- [ ] **Step 1: 创建 cli.py**

```python
"""
CLI 入口 — lut 命令

用法:
    lut index               构建向量索引
    lut search <query>      语义检索 LUT 预设
    lut list                列出全部预设名称
"""

import argparse
import sys

from .direct_embed import build_index, search
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
    for text, score in results:
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

    args = parser.parse_args()
    cmds = {"index": cmd_index, "search": cmd_search, "list": cmd_list}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证可 import**

```bash
cd d:/WorkSpace/ProjectLUT && .venv/Scripts/python.exe -c "from src.lut.cli import main; print('OK')"
```
Expected: `OK`

---

### Task 2: 注册 CLI 入口

**文件：** `pyproject.toml`

- [ ] **Step 1: 添加 [project.scripts]**

在 `[project.optional-dependencies]` 段后添加：

```toml
[project.scripts]
lut = "src.lut.cli:main"
```

完整文件变为：
```toml
[project]
name = "projectlut"
version = "0.1.0"
description = "LUT 调色预设语义检索 — 一句话套用预设"
requires-python = ">=3.11"
dependencies = [
    "numpy>=2.4",
    "opencv-python>=4.13",
    "colour-science>=0.4",
    "Pillow>=12",
    "scipy>=1.17",
    "matplotlib>=3.10",
    "scikit-image>=0.26",
    "imageio>=2.37",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov",
]

[project.scripts]
lut = "src.lut.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

- [ ] **Step 2: 安装可编辑包，使 lut 命令可用**

```bash
cd d:/WorkSpace/ProjectLUT && .venv/Scripts/pip.exe install -e . --proxy="" 2>&1 | tail -3
```
Expected: `Successfully installed projectlut-0.1.0`

- [ ] **Step 3: 验证 lut 命令可用**

```bash
.venv/Scripts/lut.exe --help
```
Expected: 显示 usage 和子命令列表

---

### Task 3: 端到端验证

- [ ] **Step 1: 验证 lut list**

```bash
cd d:/WorkSpace/ProjectLUT && .venv/Scripts/python.exe -m src.lut.cli list 2>&1 | head -5
```
Expected:
```
2383柯达胶片
3513富士胶片
3513蓝709
5213-2
CINE-LITE电影感
```

- [ ] **Step 2: 验证 lut search**

```bash
.venv/Scripts/python.exe -m src.lut.cli search "富士胶片风格" -s
```
Expected: 输出含 "富士" 的预设名称

- [ ] **Step 3: 验证 lut index (重建)**

```bash
.venv/Scripts/python.exe -m src.lut.cli index
```
Expected: `索引构建完成`

---

### Task 4: 更新文档

**文件：** `CLAUDE.md`

- [ ] **Step 1: 更新项目目录**

将 `src/lut/cli.py # 命令行入口` 从"待填充"改为"✅ 已完成"

- [ ] **Step 2: 更新当前状态**

在"当前状态"下补充：
```
| CLI | ✅ `lut search|index|list` 三条命令可用 |
```

- [ ] **Step 3: 更新短期计划**

将第 6 项"写 cli.py"标记为 ✅ 完成
