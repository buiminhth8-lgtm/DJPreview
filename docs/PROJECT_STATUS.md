# 项目状态（Project Status）

## 当前版本状态

- 阶段 1-6 已完成：MusicSpec / MIDI / WAV / 修改与版本 / 混音与导出 / 风格、参考、工程 IO、评估
- 修复任务：T01-T11 已完成（工程导入 / 前端依赖 / 质量门禁 / 文档 / 版本详情与 diff / auto_render /
  统一错误响应 / API Response Model / MusicSpec 语义校验 / LLM Provider 产品化）
- T12 第一步完成：目录式版本资产结构（versions/vN/）+ 旧结构懒迁移 + 根目录兼容镜像
- T13 完成：恢复版本时复制完整版本资产并清理缺失资产，不重新生成 MIDI / WAV
- T15 完成：Evaluation Runner `render_audio` 语义修复（false 不渲染 / true 渲染 WAV + 逐 case 音频状态）
- T16 完成：MIDI Parser 与 Fallback Renderer 支持同音高重叠音符（list + FIFO，velocity=0 按 note_off）
- T17 完成：统一乐器注册表（canonical id / alias / 0-based GM program），MIDI Writer / Mix / Mock / Style 统一接入
- T18 完成：旋律质量增强（motif / question-answer / 段落变奏 / chorus lift / outro recall）
- T19 完成：和声质量增强（功能和声 / 终止式 / 扩展和弦 / 段落感知 progression）
- T20 完成：鼓组 groove 增强（风格 groove / 段落强度 / fill / crash / swing / velocity accent / ghost note）
- T21 完成：贝斯 groove 增强（风格 bassline / 段落强度 / root-fifth-octave / passing-approach / kick 对齐）
- T22 完成：弦乐/Pad 编曲增强（chord voicing / 平滑 voice leading / 段落层次 / build-up / layer lift / thinning）
- T23 完成：前端 API 层按领域拆分（client / types / 10 个领域模块 / index / musicApi 兼容层）
- T24 完成：前端 App 状态拆分到 hooks（8 个领域 hook + hooks/index.ts，App.tsx 业务逻辑收敛）
- T25 完成：前端工作台布局拆分（components/workspace/ 12 个组件 + 布局样式，App.tsx 变组合层）
- T26/T27（Docker / GHCR）按用户指示跳过；T28 完成：示例工程与演示脚本（8 个 demo prompt + 演示文档/讲稿 + smoke 脚本）
- T29 完成：SoundFont / 音源管理（扫描 / 稳定 id / 默认策略 / 项目级选择 / renderer 接入 / API / 前端面板 / 文档）
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
pytest -q：432 passed（2026-08-04 实测，LLM_PROVIDER=mock、AUDIO_RENDERER=fallback）
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
- Evaluation trait 打分语义仍较粗（如 `has_track_role2` 与 `has_track_role` 重复），后续可细化。
- MIDI Parser / Fallback Renderer 重叠音符问题已修复；未关闭 note_on 仍按“丢弃”处理（后续可按轨道末 tick 收尾）。
- 乐器命名与 GM Program 映射已统一（T17）；后续新增音色时需先注册到 `packages/music_core/instruments/registry.py`。
- 旋律/和声/节奏分析指标为轻量辅助，未并入 QualityReport。
- 后续可做：更细的弦乐真实分部、CC11/CC7 expression 自动化、混音母带等。
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
