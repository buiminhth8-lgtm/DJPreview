# Review 摘要（Review Summary）

## 项目总体评价

ai-music-mvp 是一个功能覆盖完整的 AI 音乐生成 MVP：从一句话描述到 MusicSpec、MIDI、WAV、试听、自然语言修改、版本管理、混音、分轨导出、质量检查，再到风格模板、参考 MIDI、工程导入导出与批量评估，工程闭环完整，可复现性与可测试性良好。

## 已完成 1-6 阶段主要能力

1. **第一阶段**：MusicSpec / MusicEditSpec 协议、LLM 抽象（Mock / DeepSeek）、一句话生成。
2. **第二阶段**：MusicSpec → 多轨 MIDI（旋律 / 和弦 / 贝斯 / 鼓 / pad），确定性 seed。
3. **第三阶段**：MIDI → WAV（FluidSynth / fallback）、前端试听与下载。
4. **第四阶段**：自然语言修改 + 版本管理（建版本 / 恢复 / 详情 / diff）。
5. **第五阶段**：混音（MixSpec）、分轨导出、Piano Roll、质量检查、自动优化。
6. **第六阶段**：风格模板库、Motif/Cadence/能量曲线、局部重生成、参考 MIDI 分析、`.aimusic.zip` 导入导出、Prompt Registry、批量评估。

## 当前主要问题

- 异步渲染任务为进程内队列：服务重启会中断 `queued / running` 任务，暂未引入 Redis / Celery。
- MIDI 文件末尾未关闭的 `note_on` 按丢弃处理（不崩溃，但音符可能截断）。
- 轻量音乐分析指标未并入 QualityReport 评分模型。
- Evaluation Runner 的 trait 打分语义有重复与粗糙点（如 `has_track_role2` 与 `has_track_role`）。
- Docker / GHCR（T26/T27）按用户指示跳过：仓库保留相关文件但未完成端到端验证，
  属于 experimental / optional，不纳入当前验收。

## P0 问题

- 无（当前无阻断性缺陷；`.aimusic.zip` 导入、前端构建、后端全量测试均通过）。

## P1 问题

- 生产级任务队列（替换进程内队列，支持多实例与任务恢复）
- 未关闭 note_on 的收尾策略（按轨道末 tick 闭合）
- 轻量分析指标并入 QualityReport 评分
- Evaluation trait 打分语义细化
- Docker / GHCR 部署稳定化（T26-T27，如后续恢复）

## 不建议马上做的方向

- 音频转 MIDI 高精度扒谱（依赖复杂算法，MVP 阶段收益低）
- AI 人声 / 歌词演唱 / 音色克隆 / VST 宿主（大工程、超出当前产品边界）
- 专业混音母带与 DAW 深度集成（当前 fallback 渲染只是开发兜底）
- 大型模型训练（成本高，先验证产品与数据闭环）

## 当前推荐开发原则

```text
先修稳定性与队列生产化，再补 E2E 测试，最后提升音乐质量与音色体验。
```
