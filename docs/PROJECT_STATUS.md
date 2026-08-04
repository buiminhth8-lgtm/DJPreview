# 项目状态（Project Status）

## 当前版本状态

- 阶段 1-6 已完成：MusicSpec / MIDI / WAV / 修改与版本 / 混音与导出 / 风格、参考、工程 IO、评估
- 修复任务：T01-T11 已完成（工程导入 / 前端依赖 / 质量门禁 / 文档 / 版本详情与 diff / auto_render /
  统一错误响应 / API Response Model / MusicSpec 语义校验 / LLM Provider 产品化）
- T12 第一步完成：目录式版本资产结构（versions/vN/）+ 旧结构懒迁移 + 根目录兼容镜像
- T13 完成：恢复版本时复制完整版本资产并清理缺失资产，不重新生成 MIDI / WAV
- 当前分支：`master`

## 已完成功能

1. 自然语言生成 MusicSpec（MockProvider / DeepSeekProvider）
2. MusicSpec → 多轨 MIDI
3. MIDI → WAV（FluidSynth / fallback）
4. 前端试听与下载
5. 自然语言修改（MusicEditSpec 执行）
6. 版本管理（初始化 / 建版本 / 恢复 / 详情 / diff）
7. MixSpec 轨道混音（volume / pan / mute / solo / velocity_scale）
8. Piano Roll 数据与可视化
9. 分轨 MIDI / WAV / stems.zip 导出
10. Quality Report 与保守自动优化
11. 风格模板库（8 个模板）
12. 参考 MIDI 分析（高层特征）与基于参考生成
13. `.aimusic.zip` 工程导入导出（跨平台防 zip slip）
14. Evaluation Runner（8 个内置用例）
15. 基础质量门禁（CI + 本地脚本）

## 当前测试结果

```text
pytest -q：279 passed（2026-08-04 实测，LLM_PROVIDER=mock、AUDIO_RENDERER=fallback）
```

## 当前前端构建结果

```text
npm ci：passed
npm run build：passed（Vite 5.4.21，tsc 无错误）
```

## 已知问题

### P0（阻断）

- 无。

### P1（高优先级）

- `EditSongRequest` 尚不支持 `auto_render`（修改后需手动渲染音频）。
- API 错误响应格式不统一（部分 400 返回 `detail` 字符串，部分结构不同）。
- API 响应模型未完全明确化（部分接口返回裸 dict）。
- MusicSpec 语义校验库已实现（`check_music_spec` 返回 errors/warnings），但尚未接入生成/编辑 API 的对外报告。
- 版本资产目录式结构第一步已完成（新项目 v1/vN 目录 + 旧结构懒迁移）。
- `.aimusic.zip` 适配新版本结构待 T14。
- MIDI Parser 与 Fallback Renderer 在重叠音符（同音同轨 note_on 未闭合）场景可能异常。
- 乐器命名与 GM Program 映射存在别名不统一。
- Evaluation Runner 的 trait 打分语义较粗（如 `has_track_role2` 与 `has_track_role` 重复）。

### P2（后续）

- 音乐生成质量增强（旋律动机、和声进行、能量曲线精细调参）
- 前端工作台重构（更清晰的区域划分、状态管理）
- Docker / GHCR 部署稳定性验证（当前环境网络无法拉取 Docker Hub 基础镜像，未完成镜像构建验证）
- SoundFont / 音源管理与选择
- 渲染任务异步化与进度反馈

## 推荐下一步任务

1. T07：`EditSongRequest` 增加 `auto_render`
2. T08：统一 API 错误响应格式
3. T09：API Response Model 明确化
4. T10：MusicSpec 语义校验接入 API 报告
5. T11：DeepSeek / LLM Provider 产品化
6. T12：版本资产目录式重构
7. T15-T17：Evaluation / MIDI Parser / 乐器映射修复
8. T18-T22：音乐质量增强

## 最近一次状态更新时间

2026-08-04
