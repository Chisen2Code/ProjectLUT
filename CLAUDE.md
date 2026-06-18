# CLAUDE.md — ProjectLUT

调色 LUT 语义检索与 RAG 知识库。**Demo：一句话 → 匹配 LUT → 套到图片。**

## 快速开始

```bash
pip install -e .
lut index                          # 首次建索引
lut search "冷色调胶片感"           # 语义检索
lut apply "冷色调胶片感" a.jpg -o b.jpg  # 套 LUT
python serve.py                    # GUI 服务端 → 浏览器 app.html
```

## 项目目录

```
src/lut/       parser | direct_embed | processor | cli | embedder | matcher
tests/         15 tests (parser 6 + direct_embed 5 + processor 4)
docs/          architecture | reference/ (LightRAG/LUT调研) | superpowers/ (specs+plans)
               search-analytics-design.md
serve.py       GUI API 服务 (端口 8765)
app.html       浏览器 GUI
_serve.*       服务日志/pid/err
_probe/_verify/_e2e/_check/_test_*  运维与验证脚本 (~10 个)
_start.ps1     PowerShell 启动脚本
test_upload.html  上传隔离测试页
pyproject.toml    hatchling + lut 入口
```

## 本地 AI 基础设施

| 组件 | 模型 | 角色 |
|------|------|------|
| Ollama 0.17.1 | `bge-m3:latest` | 嵌入 (1024-dim) |
| | `qwen3:4b` | LLM |
| | `qwen3-vl-*` (×2) | 视觉 (预留) |
| AnythingLLM 1.12.1 | — | 备用，不作为核心依赖 |
| Obsidian | — | 知识沉淀 (`Documents/Obsidian Vault/`) |

## 技术架构

参见 [docs/architecture.md](docs/architecture.md)

**核心：** bge-m3 嵌入 152 个 LUT 预设名 → numpy 余弦相似度 → Top-N 匹配。
LightRAG 保留给论文 RAG 阶段，Demo 不用。

## 当前状态

| 层 | |
|----|----|
| 语义检索 | ✅ bge-m3 + numpy，<1s |
| 图片调色 | ✅ colour-science 3D LUT + log→709 |
| CLI | ✅ 6 条命令 (search/apply/index/list/stats/history) |
| GUI | ✅ serve.py + app.html |
| 测试 | ✅ 15/15 |
| Git | ✅ 10+ commits，待 push |

## MVP 路线图

| 阶段 | 状态 | 依赖 |
|------|------|------|
| 0. 语义检索 | ✅ | bge-m3 + numpy |
| 1. 图片调色 | ✅ | colour-science |
| 2. 视频适配 | ⬜ | OpenCV + GPU 纹理 |
| 3. Blender MCP | ⬜ | Blender Python API |
| 4. 论文 RAG | ⬜ | LightRAG + MinerU |
| 5. AceTone tokenizer | ⬜ | 待调研 |

## 进度日志

### Session #1 (2026-06-09~10): 基础设施搭建 + LightRAG 集成

**产出：** parser.py, embedder.py, matcher.py, LightRAG 中文摘要 + 功能模块文档, Git 仓库初始化

**API 问题：**

| 问题 | 现象 | 根因 | 解决 |
|------|------|------|------|
| pip 代理阻断 | `pip install` 报错 | pip 全局代理 `127.0.0.1:7897` 不可用 | 清华镜像 + `--proxy=""` |
| Prisma 迁移失败 | AnythingLLM 无法启动 | 数据库损坏 + 权限 | 干净重装（仅当前用户） |
| `NoneType` async context mgr | LightRAG query() 报错 | v1.5 需先调 `initialize_storages()` | 在 `match_luts()` 补调用 |
| GBK 编码乱码 | bash 中文显示乱码 | Windows 终端默认 GBK | Python `open(encoding='utf-8')` 写文件再读 |

### Session #2 (2026-06-10): direct_embed 方案 + CLI

**产出：** direct_embed.py (bge-m3+numpy), cli.py (`lut search|index|list`), pyproject.toml 注册入口

**关键发现：** LightRAG 将 152 个短标签合并为 4 个文本块，大部分 LUT 未入库。"富士"搜不到不是 bge-m3 不准，是分块逻辑丢弃了数据。结论：短标签场景不需要 LightRAG。

### Session #3 (2026-06-16): Demo 闭环 — parser RGB + processor + 测试 + GUI

**产出：** parser 补充 `read_cube_rgb()` (152 个 33³ RGB), processor.py (log→709 + 3D LUT), `lut apply|stats|history`, serve.py+app.html, tests (15 全通), search-analytics 设计文档

**查询验证：** 冷色调 ✅ 动漫 ✅ 富士 ✅（全部 0.5+ 余弦相似度）

### Session #4 (2026-06-16~17): TDD 流程反思

**事件：** Demo 实现阶段 parser/cli/direct_embed 三个模块未测试即验收。writing-plans 要求 TDD，执行时被跳过。

**根因（用户诊断）：**
1. 子 agent 上下文丢失 TDD — 任务描述未嵌入测试要求
2. 「先实现后补测」被默认为可接受的策略
3. Demo 被 Agent 判定为探索原型，自动豁免 TDD
4. 配置文本须统一口径，不可一处强调快速 demo、一处强制 TDD

**是否用户指令造成歧义：** 否。用户从未说"跳过测试"，反明确"关键模块亲手把控"。责任在 Agent。

**修正：** 已补齐 15 tests，全部通过。

### Session #5 (2026-06-17): 前端 WEBUI 修复与完善

**产出：** 可用的浏览器 GUI（`app.html`），暗色主题，拖拽+点击双路上传。

**修复内容：**
1. `app.html` 多次迭代 — `hidden`/`display:none` 导致文件选择器无效 → 最终用可见 `<input type="file">` + 拖拽区 click + drop 三保险
2. serve.py 进程管理 — 会话中后台进程多次被回收，最终用 `run_in_background` + `Start-Process` 双方案稳定
3. 统计框 — 右上角显示检索次数/上次耗时，`/api/stats` 端点
4. 下载按钮 — `URL.createObjectURL` + `body.appendChild(a)` 避免浏览器拦截


## Python 环境

```bash
source d:/WorkSpace/ProjectLUT/.venv/Scripts/activate
pip install -r requirements.txt
pip install lightrag-hku
```
