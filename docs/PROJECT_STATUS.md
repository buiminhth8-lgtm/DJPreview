# 项目状态（Project Status）

> 最近一次实测：2026-08-05（分支 `master`）。以下状态均以代码与测试实际结果为准，
> 不保留已完成的“待办”描述。

## Completed（已完成）

### 核心产品能力（阶段 1-6）

- MusicSpec / MusicEditSpec（Pydantic v2），MockProvider 无 API Key 可跑通全流程
- DeepSeekProvider（OpenAI-compatible Chat Completions）+ Prompt Registry + 结构化调用 + JSON 修复 + 调用日志（自动剔除 API Key）
- MusicSpec → 多轨标准 MIDI（旋律 / 和弦 / 贝斯 / 鼓 / Pad / 弦乐，GM 注册表统一）
- MIDI → WAV（FluidSynth / FallbackRenderer；无 FluidSynth 时 fallback 可用）
- 自然语言修改（MusicEditSpec 执行，`auto_render` 可选）
- 版本管理：v1 初始化、目录式 `versions/vN/`、列表 / 详情 / diff / restore（完整资产复制、不重新渲染）
- `.aimusic.zip` 工程导入导出：bundle_version=2、目录式版本资产、旧版兼容、跨平台 zip slip 防护、导入生成新 song_id
- MixSpec 混音（volume / pan / mute / solo / velocity_scale）、MIDI CC10 pan
- Piano Roll 数据 API、分轨 MIDI / WAV / stems.zip 导出
- Quality Report（结构 / 轨道 / 音域 / 密度 / 和声 / 混音）+ 保守自动优化（创建新版本）
- 风格模板库（8 个）、Reference MIDI 高层特征分析、Evaluation Runner（8 个内置用例，`render_audio` 语义明确）
- MusicSpec 语义校验（errors / warnings，接入生成与 MIDI 生成接口）
- 统一 T08 错误响应结构 + API Response Model 明确化

### 修复与工程任务

- T01：`.aimusic.zip` 导入 zip slip 跨平台修复
- T02：前端依赖可安装（engines 兼容、锁文件匹配）
- T03：基础质量门禁（CI + 本地脚本）
- T05 / T06：版本详情 API / 版本 diff API
- T07：`EditSongRequest.auto_render`
- T10：MusicSpec 语义校验增强
- T11：DeepSeek / LLM Provider 产品化
- T12 / T13：版本资产目录式结构 + 完整资产恢复
- T14：`.aimusic.zip` 适配目录式版本（bundle_version=2）
- T15：Evaluation Runner `render_audio` 语义修复
- T16：MIDI Parser / Fallback Renderer 重叠音符修复
- T17：乐器命名与 GM Program 映射统一
- T18-T22：旋律 / 和声 / 鼓组 / 贝斯 / 弦乐-Pad 音乐质量增强
- T23 / T24 / T25：前端 API 层拆分、hooks 状态拆分、Workspace 组件化
- T28：示例工程与演示脚本（8 个 demo prompt、演示指南、现场讲稿、smoke 脚本、走查脚本）
- T29：SoundFont / 音源管理（扫描、项目级选择、renderer 接入、API、前端面板、文档）
- T30：渲染任务异步化与进度反馈（进程内任务执行器、任务持久化、同曲串行锁、取消接口、旧同步接口兼容）
- T31：前端链路冒烟脚本
- T32：前端依赖安全收尾（vite 7.3.6、esbuild 0.28.1，`npm audit` 0 漏洞）
- T33：彻底移除 Docker / GitHub Actions 相关文件；测试分层（slow marker + 快速回归脚本）；
  Playwright 前端 E2E；生产可选 Celery/Redis 任务后端；表达自动化（CC7/CC11）与弦乐 divisi 分部

## Partially Completed / Needs Verification（部分完成或需验证）

- 音频渲染质量：fallback 渲染器为开发兜底（正弦/三角波），音色保真有限；真实音源依赖用户自备 SoundFont + FluidSynth。
- 音乐分析指标（旋律 / 和声 / 节奏 / 编曲）为轻量辅助，未并入 QualityReport 评分模型。
- Evaluation trait 打分语义仍较粗（如 `has_track_role2` 与 `has_track_role` 有重复），后续可细化。
- MIDI Parser 对文件末尾仍未关闭的 `note_on` 按“丢弃”处理，未做按轨道末 tick 收尾。

## Skipped / Optional（跳过或可选，未纳入验收）

- **T26（Docker 本地部署稳定化）与 T27（GitHub Actions + GHCR 发布）按用户指示跳过，
  相关文件（`.github/`、`docker/`、`docker-compose.*.yml`、`DEPLOYMENT.md` 等）已彻底删除。**
- 本地验收以 `pytest -q` / `npm ci` / `npm run build` / `npm audit` 为准；质量门禁使用 `scripts/check-all.*`。

## Known Issues（已知问题）

### P0（阻断）

- 无。

### P1（高优先级，当前已知）

- 异步渲染任务为**进程内队列**（`ThreadPoolExecutor`）：服务重启会中断 `queued / running` 任务
  （重启后标记 failed），暂未引入 Redis / Celery / MQ，跨进程 / 多实例不支持。
  （已提供可插拔 Celery 后端，默认不启用，需要 Redis + worker。）
- 未关闭的 `note_on` 在 MIDI 文件末尾仍按丢弃处理（不崩溃，但音符可能截断）。
- 轻量分析指标未并入 QualityReport 评分。

### P2（后续）

- 音乐生成质量精细调参（旋律动机、和声进行、能量曲线的更多参数暴露）。
- 更细的弦乐真实分部、CC11/CC7 expression 自动化、混音母带实验。
- 前端 Playwright 演示测试（当前只有后端 pytest 与前端 build 门禁）。

## 当前测试与构建结果（2026-08-05 实测）

```text
后端：pytest -q → 483 passed（LLM_PROVIDER=mock、AUDIO_RENDERER=fallback）
快速回归：pytest -m "not slow" → 341 passed（约 11s）
慢速集成：pytest -m slow → 142 passed
前端：npm ci → passed（vite 7.3.6）
前端：npm run build → passed（tsc 无错误）
前端：npm audit → 0 vulnerabilities
前端 E2E：Playwright 用例已就绪（浏览器需在联网环境 `npx playwright install chromium` 后运行）
```

> 说明：allow-scripts 对 esbuild postinstall 的提示为 npm 安装策略警告，非安全漏洞；
> 构建已验证 esbuild 二进制可用（`trustedDependencies` 机制兼容）。

## Next Recommended Tasks（推荐下一步）

1. 文档 / 测试分层：拆分慢速集成测试，缩短全量回归时间。
2. Playwright 前端演示测试：从 prompt 到播放 / 编辑 / 版本 / 混音 / 导出的端到端覆盖。
3. 生产级任务队列：Redis / Celery 替换进程内队列，支持多实例与任务恢复。
4. 音乐质量与音色：真实 SoundFont 渲染体验优化、弦乐分部细化。
5. 如未来需要 CI/CD，可重新引入 GitHub Actions / Docker（当前已彻底移除，避免死文档）；
   在联网环境安装 Playwright 浏览器并跑通 `npm run e2e`。

## 最近一次状态更新时间

2026-08-05
