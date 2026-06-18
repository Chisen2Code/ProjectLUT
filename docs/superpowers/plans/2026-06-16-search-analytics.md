# 搜索统计实现计划

**目标：** search_log SQLite 表 + lut stats/history CLI 子命令

**架构：** direct_embed.search() 写 log → cli.py 新增 stats/history 子命令

**技术栈：** Python 3.11, sqlite3 (stdlib), argparse

---

### Task 1: 加搜索日志写入

**文件：** `src/lut/direct_embed.py`

- `log_search(query, results, duration_ms)` → 写 SQLite
- `get_stats()` → 返回 dict {total_queries, top_terms, cold_presets}
- `get_history(n=20)` → 返回最近 n 条记录

### Task 2: 加 CLI 子命令

**文件：** `src/lut/cli.py`

- `lut stats` → 总览仪表盘
- `lut stats --cold` → 从未被命中的预设
- `lut history` → 最近 20 条

### Task 3: 端到端验证

- 搜 3 次不同的词 → `lut stats` 显示 3 次 → `lut history` 显示记录 → `lut stats --cold` 显示未被命中的
