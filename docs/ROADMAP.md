# 路线图（Roadmap）

> 状态说明：✅ 已完成；🔄 进行中；⬜ 未开始。每个任务只记录目标、优先级、依赖、验收标准。

## T01 修复 `.aimusic.zip` 工程导入失败 ✅

- 目标：工程导入路径安全判断跨平台兼容，修复 Linux/macOS 误判越界
- 优先级：P0
- 依赖：无
- 验收标准：合法 zip 正常导入；`../evil.txt` 等 zip slip 被拒绝；专项与全量 pytest 通过

## T02 前端依赖与构建修复 ✅

- 目标：`npm ci` / `npm run build` 可稳定通过，依赖真实可安装
- 优先级：P0
- 依赖：无
- 验收标准：engines 兼容 npm 10+；vite 使用 registry 可安装稳定版；锁文件与 package.json 匹配

## T03 建立基础质量门禁 ✅

- 目标：push / PR 自动验证后端 pytest 与前端构建，并提供本地检查脚本
- 优先级：P0
- 依赖：T02
- 验收标准：CI 文件存在；`scripts/check-all.ps1` / `.sh` 可用；本地全量检查通过

## T04 更新 README 与 Review 状态 ✅

- 目标：README / 项目状态 / 路线图 / Review 摘要与代码状态一致
- 优先级：P0
- 依赖：T01-T03
- 验收标准：README 覆盖启动/测试/能力/限制；docs 三份文档存在且无虚假状态

## T05 补齐版本详情 API ✅

- 目标：`GET /songs/{song_id}/versions/{version_id}` 返回 metadata / music_spec / edit_spec / is_current / assets
- 优先级：P1
- 依赖：T03
- 验收标准：接口返回齐全；404/400 处理；pytest 覆盖

## T06 补齐版本 Diff API ✅

- 目标：`GET /songs/{song_id}/versions/{version_id}/diff` 返回与当前版本的字段级 diff
- 优先级：P1
- 依赖：T05
- 验收标准：diff 方向（old=指定版本，new=当前版本）正确；pytest 覆盖

## T07 `EditSongRequest` 增加 `auto_render` ✅

- 目标：自然语言修改后可选择是否自动重渲染 MIDI/WAV
- 优先级：P1
- 依赖：T04
- 验收标准：请求支持 `auto_render`；默认行为兼容现有接口

## T08 统一 API 错误响应格式 ✅

- 目标：所有错误统一为结构化响应（code / message / detail）
- 优先级：P1
- 依赖：T04
- 验收标准：异常处理器统一；pytest 校验关键错误响应结构

## T09 API Response Model 明确化 ✅

- 目标：消除裸 dict 响应，全部接口使用 Pydantic response_model
- 优先级：P1
- 依赖：T08
- 验收标准：OpenAPI 中无裸 dict 响应；前端类型与后端一致

## T10 MusicSpec 语义校验增强 ✅

- 目标：语义校验（track/section 唯一、重叠、harmony 引用、chord 可解析、key/mode 合法性）接入 API 报告
- 优先级：P1
- 依赖：T09
- 验收标准：生成/一步生成响应附带 `validation`；非法 MusicSpec 在 MIDI 生成时返回 `400 MUSIC_SPEC_VALIDATION_FAILED`
- 实现：`spec_validator.validate_music_spec_semantics` 返回 `ValidationResult{valid, errors[], warnings[]}`，
  覆盖 track/section 唯一性、段落重叠与越界、harmony/enabled_sections 引用、和弦可解析、key/mode/拍号合法性；
  前端 `musicApi.ts` 同步 `ValidationIssue / ValidationResult` 类型；`tests/test_semantic_validator.py` 覆盖

## T11 DeepSeek / LLM Provider 产品化 ✅

- 目标：真实 LLM 接入稳定（JSON 校验、重试、超时、降级）
- 优先级：P1
- 依赖：T10
- 验收标准：Prompt Registry 管理 prompt；`generate_structured` 统一入口；JSON 提取 + Pydantic 校验 + 二次修复；
  LLM 调用日志（不含 API Key）；mock httpx 测试通过；失败返回 `LLM_PROVIDER_ERROR`；MockProvider 行为不变
- 实现：`prompt_registry`（含 `music_spec_generator` / `music_editor` / `json_repair`）、`json_utils`、
  `structured_call`、`call_logger`、`models`；DeepSeekProvider 重构为结构化调用并接入 project_id 日志；
  新增 `tests/test_prompt_registry.py`、`tests/test_llm_json_utils.py`、`tests/test_deepseek_provider.py`、
  `tests/test_llm_call_logger.py`、`tests/test_llm_provider.py`

## T12 版本资产目录式重构 ✅（第一步完成）

- 目标：每版本独立资产目录（spec / midi / wav / mix / quality）
- 优先级：P1
- 依赖：T05-T06
- 验收标准：新项目创建目录式版本（versions/vN/）；旧 vN.json 懒迁移；根目录保留当前版本兼容镜像；
  MIDI / WAV / Mix / Quality / Stems 资产同步到版本目录；现有版本 API 不破坏
- 实现：`packages/music_core/versioning/`（version_migration / version_assets / version_models）；
  `project_store` 新项目 v1 + 编辑 vN 目录式写入；`save_midi_file` / `save_audio_metadata` 自动同步当前版本资产；
  `versions/index.json` 升级 schema_version=2 并写入 path/index/kind/prompt；
  根目录写入 `current.json` / `current_version_id.txt` 兼容指针
- 说明：完整 restore 历史资产同步留到 T13；`.aimusic.zip` 适配新结构留到 T14

## T13 版本资产恢复重构 ✅

- 目标：restore 基于新版本目录恢复并同步根目录资源
- 优先级：P1
- 依赖：T12
- 验收标准：恢复时从 `versions/vN/` 复制完整资产（music_spec / midi / wav / mix / quality / stems），
  缺失资产清理根目录旧镜像，不重新生成 MIDI / WAV；恢复后 assets 与版本一致
- 实现：`version_assets.restore_version_assets_to_current`（restored / removed / missing_optional 摘要）；
  `project_store.restore_version` 返回 (music_spec, summary) 并更新版本指针；
  restore 路由移除 `_regenerate_audio_for`，返回 `restore_summary`；`AssetsResponse` 增加 has_mix / has_quality_report / has_stems

## T14 工程导入导出适配新版本结构 ✅

- 目标：`.aimusic.zip` 导入导出适配 T12 目录式版本结构（bundle_version=2）
- 实现：`project_bundle.export_project_bundle` 导出 manifest.json（bundle_format=aimusic / bundle_version=2 /
  current_version_id / versions[] / assets[]）与完整 `versions/vN/` 版本资产（version_metadata / music_spec /
  edit_spec / diff / MIDI / WAV / audio_metadata / mix / quality / stems / soundfont 配置）；
  `project_importer.import_project_bundle` 生成新 song_id、跨平台 zip slip 防护、自动迁移旧版
  （format_version=0.1 / versions/vN.json）、以当前版本目录修复根目录镜像（不重新生成 MIDI/WAV）、
  失败清理半成品目录
- 验收：roundtrip / 版本数量与 current_version_id 一致 / 根目录镜像一致 / 旧版兼容 / zip slip 拒绝 / 不覆盖已有项目

## T15 Evaluation Runner 语义修复 ✅

- 目标：修正 `render_audio` 参数语义（false 不渲染、true 渲染 WAV）并完善报告音频字段
- 优先级：P1
- 依赖：T10
- 验收标准：`render_audio=false` 不调用渲染器；`render_audio=true` 使用 renderer factory 渲染 WAV；
  每个 case 记录 audio_rendered / audio_path / renderer / render_error；单个 case 渲染失败不影响整体报告
- 实现：`EvalResult` / `EvalReport` 增加音频字段（audio_rendered / audio_path / audio_duration_seconds /
  renderer / render_error / audio_rendered_cases / audio_failed_cases）；`eval_runner` 为每个 case 建立独立输出目录
  （`data/evaluations/{run_id}/cases/case_NNN_id/`）并按需调用 `get_audio_renderer()`；
  API 默认 `render_audio=false`；新增 `tests/test_evaluation_api.py`

## T16 MIDI Parser / Fallback Renderer 重叠音符修复 ✅

- 目标：重叠同音 note_on 正确闭合，渲染不产生异常波形
- 优先级：P2
- 依赖：无
- 验收标准：解析测试与 WAV 渲染测试通过；同音重叠不丢失；velocity=0 按 note_off；未配对/未关闭不崩溃
- 实现：parser 与 fallback renderer 的活动音符改为 `dict[(channel, note), list[(start_tick, velocity)]]`，
  note_off 按 FIFO pop(0) 配对；fallback 使用 note_on 的 velocity；新增重叠同音 / 多 channel / 边界用例测试

## T17 乐器命名与 GM Program 映射统一 ✅

- 目标：统一乐器名 → GM program 映射（单一来源）
- 优先级：P2
- 依赖：无
- 验收标准：Instrument Registry 统一 canonical id / alias / GM program；MIDI Writer 使用统一映射；
  MockProvider / Style Template 输出可解析乐器；未知乐器回退默认并在语义校验中给 warning；鼓组走 channel 9
- 实现：新增 `packages/music_core/instruments/`（gm.py / registry.py）；
  `midi_writer` / `mix_engine` 改用 `get_gm_program` / `is_drum_instrument`；
  `midi_constants.GM_PROGRAMS` 由注册表生成；MockProvider / Style Library 改用 canonical id；
  `spec_validator` 新增 `UNKNOWN_INSTRUMENT_ALIAS` warning；新增 `tests/test_instrument_registry.py`

## T18-T22 音乐质量增强（T18 旋律 ✅，T19 和声 ✅，T20 鼓组 ✅，T21 贝斯 ✅，T22 弦乐/Pad ✅）

- 目标：旋律动机、和声进行/终止式、能量曲线、节奏模板、编曲密度调优
- 优先级：P2
- 依赖：T16-T17
- 验收标准：质量报告平均分提升；可听性主观验收
- T18 已完成：melodic motif（scale degree 表达）+ question/answer phrase + 段落变奏
  （intro 稀疏 / verse 克制 / pre_chorus 张力 / chorus lift / bridge 对比 / outro 回收）+ 调内量化渲染；
  新增 `composer/melodic_theme.py`、`composer/phrase_builder.py`、`composer/section_planner.py`、
  `analysis/melody_analysis.py`，重写 `melody/melody_engine.py`；确定性与现有 MIDI 输出不受影响
- T19 已完成：功能和声（Tonic/Predominant/Dominant）+ roman numeral 转换 + authentic/half/plagal/deceptive 终止式 +
  maj7/m7/7/sus2/sus4/add9/6/dim/m7b5 和弦色彩 + 段落感知和声（verse half / pre_chorus dominant / chorus authentic /
  bridge deceptive / outro tonic）；`build_bar_harmony` 内置终止式补强；新增
  `theory/roman_numerals.py`、`composer/harmony_models.py`、`composer/harmony_progressions.py`、
  `analysis/harmony_analysis.py`；语义校验新增 `WEAK_SECTION_CADENCE` / `REPETITIVE_CHORD_PROGRESSION` warning
- T20 已完成：鼓组 groove 增强（pop / rock / lo-fi / cinematic / chinese / electronic）+ 段落强度
  （intro 稀疏 / verse 基础 / pre_chorus 推进 + fill / chorus 最强 + crash / bridge 对比 / outro 收束）+
  fill（snare / tom / hat）+ swing（lo-fi 0.62）+ velocity accent + ghost note；GM drum note + channel 9；
  新增 `theory/rhythm.py`、`composer/drum_models.py`、`composer/drum_patterns.py`、
  `composer/groove_library.py`、`analysis/rhythm_analysis.py`，重写 `drums/drum_engine.py`
- T21 已完成：贝斯 groove 增强（pop / rock / lo-fi / cinematic / chinese / electronic）+ 段落强度 +
  root/fifth/octave + 调内 passing/approach tone + 与 kick 对齐（implied 或传入 drum events）+ octave jump +
  velocity accent；贝斯走 melodic channel（非 9）、program 来自 T17 registry；
  新增 `composer/bass_models.py`、`composer/bass_patterns.py`、`analysis/bass_analysis.py`，重写 `bass/bass_engine.py`
- T22 已完成：弦乐/Pad 编曲增强（chord voicing + 平滑 voice leading + 段落层次）
  （intro 稀疏 / verse 薄铺 / pre_chorus build / chorus 加厚 + octave layer / bridge 对比 register / outro thinning）+
  sustained strings / light stab / cinematic ostinato + pad 长音为主；音区避开 bass/melody 冲突；
  新增 `composer/voicing.py`、`composer/voice_leading.py`、`arrangement/strings_engine.py`、
  `arrangement/pad_engine.py`、`analysis/arrangement_analysis.py`；composer 接入 pad/strings 专用引擎

## T23-T25 前端工作台重构（T23 ✅，T24 ✅，T25 工作台布局 ✅）

- 目标：按“生成 / 播放 / 编辑 / 混音 / 可视化 / 质量 / 导出”分区域重构，状态管理统一
- 优先级：P2
- 依赖：T08-T09
- 验收标准：tsc / build 通过；无功能回归
- T23 已完成：前端 API 层按领域拆分（client / types / song / version / audio / mix / analysis /
  reference / evaluation / project / style / index）；`client.ts` 统一 base URL、T08 错误解析、
  `apiFetch` / `apiDownloadBlob` / `ApiRequestError`；`musicApi.ts` 保留兼容 re-export，旧 import 不失效；
  UI 调用点未改；`npm run build` 通过
- T24 已完成：App 状态拆分到 hooks（useSongProject / useAudioAssets / useVersions / useMixer / useQuality /
  useEvaluation / useReferenceMidi / useStyles + hooks/index.ts）；App.tsx 保留 UI 结构，直接 API 调用移除；
  生成/编辑/MIDI/音频/版本/恢复等联动通过 hooks 编排；`npm run build` 通过
- T25 已完成：工作台布局拆分（`components/workspace/`：WorkspaceLayout / WorkspaceHeader / GeneratePanel /
  PlayerPanel / EditPanel / VersionPanel / MixerPanel / AnalysisPanel / ReferencePanel / EvaluationPanel /
  ProjectPanel / StatusMessage / index）；App.tsx 收敛为 hooks + 跨模块回调的组合层；
  styles.css 增加工作台栅格与状态样式；T26/T27 按用户指示跳过，后续进入 T28 演示

## T26-T27（已跳过）

- T26（Docker 本地部署稳定化）与 T27（GitHub Actions + GHCR 发布）按用户指示明确跳过。

## T28 示例工程与演示脚本 ✅

- 目标：稳定、可复现、可离线演示的产品 Demo 流程（MockProvider，不依赖真实 DeepSeek）
- 实现：`examples/demo_prompts.json`（8 个案例）、`docs/DEMO_T28.md`（演示指南）、
  `docs/DEMO_SCRIPT.md`（现场讲稿）、`scripts/demo_t28_smoke.py`（自动化 smoke，默认 2 案例 / --all 全跑）、
  `scripts/demo_t28_walkthrough.sh`（手工走查）、`tests/test_demo_prompts.py`、`tests/test_demo_smoke.py`

## T29 SoundFont / 音源管理增强 ✅

- 目标：支持选择不同 `.sf2` / `.sf3` 音源渲染 MIDI，项目级音源选择、风格默认音源 hint、前端列表展示
- 实现：`packages/music_core/audio/`（soundfont_models / soundfont_manager：扫描 data/soundfonts、assets/soundfonts、
  SOUNDFONT_DIR，稳定 id，默认策略 DEFAULT_SOUNDFONT_ID > SOUNDFONT_PATH > 首个扫描结果）；
  renderer 接入（fallback 忽略、FluidSynth 按调用传入 soundfont_path，metadata 记录 soundfont_id/name/path）；
  项目级 `soundfont.json`（restore 不覆盖，.aimusic.zip 只含 metadata 不含音源文件）；
  API `GET /soundfonts`、`POST /soundfonts/scan`、`GET/PUT /songs/{id}/soundfont`；
  style template 增加 soundfont_hint / preferred_soundfont_tags；前端 soundfontApi / useSoundfonts / SoundfontPanel；
  文档 docs/SOUNDFONTS.md；不提交真实音源（.gitignore + .gitkeep）

## T30 渲染任务异步化与进度反馈 ✅

- 目标：MIDI / WAV / stems 渲染改为异步任务，前端轮询进度，旧同步接口兼容
- 实现：`packages/music_core/tasks/`（task_models / task_store：线程安全内存存储）、
  `services/api/tasks/render_task_service.py`（ThreadPoolExecutor 执行器 + midi/audio/stems job，同 song+类型去重）、
  `services/api/routes/render_tasks.py`（render-midi / render-audio / export-stems / tasks 查询与列表）、
  前端 `taskApi.ts` / `useRenderTasks` / `RenderTasksPanel`（进度条 + 轮询 + 成功刷新资产）；
  文档 docs/RENDER_TASKS.md（含进程内队列 / 重启丢失 / 无取消等限制说明）
- 遗留问题修复：任务轻量 JSON 持久化（data/tasks/，重启后中断任务标记失败）、同曲渲染串行锁
  （同步/异步共用 per-song 可重入锁）、`DELETE /tasks/{task_id}` 取消接口（queued 立即取消 / running 检查点中止）

## T31 前端链路冒烟 ✅

- 目标：生成 → MIDI → WAV → 版本 → 异步任务进度 → assets 的端到端验证脚本
- 实现：`scripts/demo_t30_frontend_smoke.py`（后端全链路 + 可选前端 dev server 探活，纯标准库）、
  `tests/test_frontend_smoke.py`（脚本存在 / --help / 可导入）

## T32 前端依赖安全收尾 ✅

- 目标：消除 `npm audit` 中 esbuild / vite 漏洞（GHSA-67mh-4wv8-2f99），不做 `audit fix --force`
- 实现：vite `^5.4.21` → `^7.3.6`（esbuild `0.21.5` → `0.28.1`），`@vitejs/plugin-react` 保持 `^4.3.4`
  （peer 范围已支持 vite 7），`npm audit` 0 漏洞，`npm ci` / `npm run build` / `pytest -q` 全部通过
- 说明：vite 7 最低要求 Node ≥20.19 或 ≥22.12；vite 8 为后续独立任务（当前 npm 10.9.2 环境不兼容其 engine 要求）
- 遗留提示：npm 11 allow-scripts 对 esbuild postinstall 的提示为安装策略警告，非安全漏洞；
  构建已验证 esbuild 二进制可用，`trustedDependencies` 机制继续兼容

## 下一轮建议

1. 文档 / 测试分层：拆分慢速集成测试（如音频渲染 / 全链路 API），缩短全量回归时间。
2. Playwright 前端演示测试：从 prompt 一路到播放 / 编辑 / 版本 / 混音 / 导出的端到端覆盖。
3. 生产级任务队列：用 Redis / Celery 等替换进程内 `ThreadPoolExecutor`，支持多实例与任务恢复。
4. 音乐质量与音色：真实 SoundFont 渲染体验优化、弦乐分部细化、CC11/CC7 expression 实验。
5. Docker / GHCR 部署稳定化（如后续恢复 T26/T27）：当前相关文件为 experimental / optional，未纳入验收。
