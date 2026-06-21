# CLAUDE.md — ProjectLUT

调色 LUT 语义检索与 RAG 知识库。**Demo：一句话 → 匹配 LUT → 套到图片。**

## 文件管理底线

**本项目所有文件必须位于 `ProjectLUT/` 目录内**，不得散落到 `d:\WorkSpace` 根目录。包括但不限于：截图、日志、临时脚本、测试产出。违者立即移动或删除。

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
src/lut/       parser | direct_embed | processor | cli | rerank
tests/         45 tests (parser 6 + embed 5 + processor 7 + rerank 16)
docs/          architecture | color-pipeline | reference/ | superpowers/
scripts/       运维脚本 (16 个)
serve.py       GUI API 服务 (端口 8765, ThreadingHTTPServer)
app.html       浏览器 GUI
data/search_log/  JSON 搜索日志 + query_vector 持久化
pyproject.toml hatchling + lut 入口
LUT预设1/      152 个 .cube LUT 文件
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
| 语义检索 | ✅ bge-m3 + numpy 余弦相似度，~5s（含嵌入） |
| 动态截断 | ✅ 0.3 底线 + 0.15 陡降 + 6 上限 |
| 规则纠偏 | ✅ contrast/saturation/tone 字段过滤，6 意图方向 |
| 图片调色 | ✅ sRGB/Log 双管线 + Cineon 编码 + 高光衰减 |
| 搜索日志 | ✅ JSON 持久化 + query_vector + 点击回传 |
| 预览网格 | ✅ 流式加载（3 并发），60px 缩略图 |
| CLI | ✅ 6 条命令 (search/apply/index/list/stats/history) |
| GUI | ✅ serve.py + app.html |
| 测试 | ✅ ~46（auto-detected, do not pin in CI） |

## 架构概览

```
用户输入 ─→ embed_query(bge-m3) ─→ 余弦 vs vectors.npy(152)
                                       │
                                  dynamic_cut(6)
                                       │
                                  rule_filter(6意图)
                                       │
                                  log_search_json + 返回前端
                                       │
                                  用户选 preset + 上传图片
                                       │
                                  apply_lut
                                    ├── srgb → 直接查表 + 高光衰减
                                    └── log_cinema → sRGB→Linear→Log→LUT→Linear→sRGB + 高光衰减
```

## 已知短板

| 方面 | 问题 | 状态 |
|------|------|------|
| Log 曲线精度 | Cineon 通用近似，特定摄影机 Log（Arri/S-Log/C-Log）不匹配 | ⬜ 待 Preset.log_curve |
| 黑白 LUT | 库中无真正黑白/去色预设 | ⬜ 待入库或内置去色 |
| search_log 分析 | 数据已采集，未做用户画像和近义词聚合 | ⬜ 待分析层 |
| 视频适配 | OpenCV 逐帧套 LUT 思路已明确 | ⬜ 待实现 |
| 代理干扰 | Windows HTTPS_PROXY 导致 bash/curl 断联，仅 Playwright 可用 | ⬜ 环境问题 |
| bge-m3 批量嵌入 | 连续 120+ 文本后 HTTP 500，已加退避但未根治 | ⬜ 待排查 |

## MVP 路线图

| 阶段 | 子项 | 状态 |
|------|------|------|
| **0. 语义检索** | bge-m3 + numpy 余弦相似度 | ✅ |
| | dynamic_cut 复合截断 | ✅ |
| | rule_filter 规则纠偏 | ✅ |
| **1. 图片调色** | sRGB 直查管线 | ✅ |
| | Log 管线（Cineon） | ✅ 有精度短板 |
| | 高光衰减 + GIF 拦截 | ✅ |
| **2. 搜索分析** | JSON 日志 + query_vector | ✅ |
| | 点击回传 clicked_preset_id | ✅ |
| | 用户画像 / 近义词聚合 | ⬜ |
| **3. 预览体验** | ⚡ 状态条 + 动态结果列表 | ✅ |
| | 百图预览网格（流式加载） | ✅ |
| **4. 视频适配** | 规划阶段 | ⬜ |
| **5. 论文 RAG** | LightRAG + MinerU | ⬜ |
| **6. Blender MCP** | Blender Python API | ⬜ |

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

### Session #6 (2026-06-18~19): 色彩管线修复

**产出：** 完整的 sRGB→Linear→Log→3D LUT→Linear→sRGB 管线，高光衰减，GIF 拦截，轻量色彩验证。

**改动：**
1. `parser.py` — Preset 新增 `lut_type`（srgb/log_cinema）、`domain_min/max` 字段；`read_cube_rgb()` 补 DOMAIN header 解析
2. `processor.py` — 删除 `_log_to_709()`，新增 5 个函数：
   - `_srgb_to_linear()` / `_linear_to_srgb()`：正确分段 sRGB EOTF/OETF
   - `_linear_to_log()` / `_log_to_linear()`：Cineon 风格 log 编解码
   - `_luma_attenuation()`：亮度 >0.85 时衰减 R/G 通道 ≥25%
3. `tests/test_processor.py` — 改用裁切检测 + Hasler-Susstrunk 色彩丰富度比值验证，新增 3 个测试
4. `docs/color-pipeline.md` — 管线设计文档

**关键决策：** log 曲线采用 Cineon 通用默认，不假设特定摄影机 Log 曲线。后续可扩展为可配置。

**验证：** 18/18 tests ✅，裁切检测和色彩丰富度比值可在 CI 中自动拦截溢橙回归。

### Session #7 (2026-06-19~20): 语义搜索走查 + 「黑白」搜索定位

**事件：** 用户搜「黑白」的结果与 Agent 主观推理不一致，要求排查根因。

**排查结论：**
1. bge-m3 搜索管道工作正常 —「黑白」无精确匹配，回退到字级别「白」→ 人像冷白 / cold冷白 / 漂白等
2. **Agent 错误**：未跑实际管道，而是凭「默片时代 = 黑白电影」推理回答，实际套图验证该 LUT 输出是蓝青暗调，非黑白
3. 库缺口：152 个预设无一真正黑白/去色 LUT

**修复：** 无代码改动，属认知流程修正 — Agent 回答前必须先跑实际管道验证，不能凭字面推理。
**修正：** `app.html` 加 `API_BASE` 动态检测 `file://` 协议，支持直接双击打开。

### Session #8 (2026-06-20~21): 搜索分析 v2 — JSON 日志 + 动态截断 + 预览网格

**事件：** 引入搜索分析 v2（JSON 日志固化、动态截断、点击追踪、百图预览网格），但风格管线稳定性下降。

**新增功能：**
1. `data/search_log/*.json` — 搜索日志固化，query_vector 持久化，`clicked_index` 回写
2. `dynamic_cut()` — 复合截断（0.3 底线 + 0.15 陡降 + 10 上限）
3. `⚡ Nms · 共 M 个匹配` — 前端状态条
4. 百图预览网格 — 流式加载（3 并发），点击等价选中预设
5. `/api/click` — 点击回传端点
6. `/api/preview/{index}` — 200px 缩略图端点

**问题：** 搜索 API 在 curl/bash 下因 HTTPS_PROXY 环境变量阻塞导致空响应；Playwright 直连正常（29/29 tests ✅）。上传的测试图容量过小（1.8KB）且内容简单。

**教训：** 核心管线稳定性 > 新功能。新的 try/except 已补，但验证手段应统一为 Playwright 而非受代理干扰的 curl。

### Session #9 (2026-06-21): 标识体系重构 + 缺陷修复

**事件：** preset 标识体系不统一（name/text/index 三套混用），导致 apply 失效、预览错位、索引不对齐。全面重构为 `preset_id` 单一真相。

**重构内容：**
1. `parser.py` — Preset 新增 `id` 字段（`id=name`），dataclass 字段排序修正
2. `direct_embed.py` — `search()` 返回 `(preset_id, score, index)` 三元组；新增 `ids.txt` 持久化；Ollama 嵌入容错（重试+退避）；batch_size 降至 2；空结果防御
3. `serve.py` — `_preset_cache` 统一用 `p.id` 做 key；`send_error(code, msg)` 替代 200 错误响应；preview 用 `_sorted_presets[index]` 保证索引一致；warmup 加空预设检查；`HTTPServer` → `ThreadingHTTPServer` 解决请求排队阻塞
4. `app.html` — `selectedPresetName`→`selectedPresetId` 全局重命名修复 apply 静默失败；预览网格流式加载重写（3 路 `loadOne` 链式递归）；空结果 `?.length` 防御
5. 测试全通过 29/29

**缺陷修复：**
- apply 按钮点击后无响应：保留 `selectedPresetName` 引用导致函数提前 return
- 预览网格只加载前 3 张：`loadNext` 递归逻辑中 return 截断了后续请求
- 预览堵塞应用：单线程 `HTTPServer` 排队，改为 `ThreadingHTTPServer`
- 错误响应无法识别：`send_json` 返回 200 含 error，前端 `resp.ok` 无法区分

**Ollama 稳定性：** bge-m3 在连续嵌入约 120 个文本后返回 HTTP 500，原因未知（非内存不足）。已加入重试退避 + 短文本回退策略。

**搜索结果评估（已修复 06/21）：**
规则层 `rule_filter` 上线后，否定/程度修饰意图可在 bge-m3 召回后做字段级排除：
- 「对比度低一点」→ 排除 `contrast=high` → 不再返回高对比 LUT ✅
- 「饱和度高一些」→ 排除 `saturation=low` → 不再返回低饱和 LUT ✅
- 关键词驱动，零 LLM 调用，毫秒级
- 目前支持：low_contrast / high_contrast / low_saturation / high_saturation / warm / cold

### Session #10 (2026-06-21): 规则层语义纠偏 + 完整测试覆盖

**事件：** bge-m3 不理解否定修饰（「对比度低一点」匹配到「高对比」），引入纯规则过滤层，零 LLM 调用。

**改动：**
1. `parser.py` — Preset 新增 `contrast`/`saturation`/`tone` 三个 metadata 字段 + `infer_contrast()`/`infer_saturation()`/`infer_tone()` 关键词引导函数
2. `rerank.py` — 独立模块 `rule_filter(results, query, preset_cache)`，检测 6 个意图方向并排除不匹配预设
3. `serve.py` — search 管道中 dynamic_cut 后插入 rule_filter
4. `tests/test_rerank.py` — 16 个测试覆盖关键词推断 + 规则过滤 + 边界条件

**验证：** 44/44 tests ✅，「对比度低一点」不再返回高对比 LUT，「饱和度高一些」不再返回低饱和 LUT。

**遗留：** Log 管线使用 Cineon 通用曲线，特定摄影机 Log 空间不匹配导致部分 LUT 输出偏灰偏雾。需引入 `log_curve` 可配置字段方能根治，当前无业务人员标注，搁置。

### Session #11 (2026-06-21): 项目自查 + SQLite 弃用 + 统计面板

**文件整理：**
1. 根目录清理：`test_image.jpg`、`test_result.jpg`、`_serve.*` 删除
2. scripts 分级：`scripts/active/`（5 入口）+ `scripts/archive/`（13 历史）
3. 遗留代码归档：`embedder.py`/`matcher.py` → `scripts/archive/`
4. 过时文档归档：3 篇 LightRAG 参考 → `docs/archive/`
5. 旧 plans/specs 删除：6 个 `2026-06-16-*` 文件

**代码清理：**
1. `direct_embed.py` — `sqlite3` 依赖彻底移除，删除 `_init_db()`/`log_search()`/`_DB_PATH`，`get_stats()` 改为 JSON 文件聚合
2. `docs/architecture.md` — 重写，去掉 LightRAG/LanceDB 残留，反映当前 5 层架构

**新功能：**
1. `app.html` 左下角新增统计面板：总搜索数、平均耗时、top-6 热门 query
2. 数据来自 `/api/stats`（基于 JSON 日志聚合）


## Python 环境

```bash
source d:/WorkSpace/ProjectLUT/.venv/Scripts/activate
pip install -r requirements.txt
pip install lightrag-hku
```
