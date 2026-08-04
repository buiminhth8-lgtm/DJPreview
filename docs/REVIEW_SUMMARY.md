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

- 错误响应格式与部分响应模型尚未完全统一。
- `EditSongRequest` 缺 `auto_render`，修改后渲染链路不完整。
- 语义校验库已实现但未接入 API 对外报告。
- 版本资产仍是“根目录文件 + 快照”并存，缺少统一目录结构。
- MIDI Parser / Fallback 在重叠音符场景有边界问题；乐器名与 GM program 映射有别名不一致。
- Evaluation Runner 的 trait 语义有重复与粗糙点。
- Docker 镜像构建因当前网络无法拉取 Docker Hub 基础镜像，尚未完成端到端验证。

## P0 问题

- 无（当前无阻断性缺陷；`.aimusic.zip` 导入、前端构建、后端全量测试均通过）。

## P1 问题

- API 错误响应 / 响应模型统一（T08 / T09）
- `EditSongRequest.auto_render`（T07）
- MusicSpec 语义校验 API 化（T10）
- 版本资产目录式重构（T12-T14）
- DeepSeek / LLM 产品化（T11）
- Docker / GHCR 部署稳定化（T26-T27）

## 不建议马上做的方向

- 音频转 MIDI 高精度扒谱（依赖复杂算法，MVP 阶段收益低）
- AI 人声 / 歌词演唱 / 音色克隆 / VST 宿主（大工程、超出当前产品边界）
- 专业混音母带与 DAW 深度集成（当前 fallback 渲染只是开发兜底）
- 大型模型训练（成本高，先验证产品与数据闭环）

## 当前推荐开发原则

```text
先修稳定性，再补 API，一致化版本资产，最后提升音乐质量。
```
