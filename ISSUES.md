# ISSUES — 架构级 Bug 与待决策

> 记录影响整体方向的 Bug、技术债务和待定决策。

## 待解决

### [Bug] GUI 文件上传在浏览器中无效
- **现象**: 点击上传/拖入均不触发
- **诊断**: hidden/display:none 导致 click() 失效，可见 input 仍不生效
- **提议**: 尝试 `<label for="upload">` 原生绑定替代 JS click()
- **状态**: ⬜

### [决策] 运维脚本泛滥
- ~10 个 `_*.py` 临时脚本滞留根目录，归入 `scripts/` 或删除
- **状态**: ⬜

## 已解决 ✅

- [x] LightRAG 分块丢弃短文本 → 换 direct_embed
- [x] AnythingLLM 嵌入器不生效 → 降级备用
- [x] LightRAG v1.5 `initialize_storages()` 缺失
- [x] TDD 被跳过 → 补齐 15 tests
- [x] GitHub 大文件推送拒绝 → `--orphan` 清历史
