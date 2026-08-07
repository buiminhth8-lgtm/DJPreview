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

- T26（Docker 本地部署稳定化）与 T27（GitHub Actions + GHCR 发布）按用户指示明确跳过，
  相关文件（`.github/`、`docker/`、`docker-compose.*.yml`、`DEPLOYMENT.md` 等）已彻底删除。

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

## T33 收尾：移除 CI/Docker + 测试分层 + E2E + 任务队列 + 音质 ✅

- 彻底删除 Docker / GitHub Actions 相关文件（`.github/`、`docker/`、`docker-compose.*.yml`、
  `DEPLOYMENT.md`、`.env.docker.example`、`.dockerignore`），文档同步移除引用。
- 测试分层：`slow` marker（模块级 TestClient 自动标记，142 slow / 341 fast），
  `check-backend` 默认快速回归（约 11s），`-Full` / `--full` 跑全量。
- Playwright 前端 E2E：`apps/web/e2e/demo.spec.ts` + `playwright.config.ts` + `npm run e2e`
  （浏览器需在联网环境安装；本环境网络受限未执行浏览器运行）。
- 生产级任务队列：执行器抽象（`task_executor.py`：InProcess 默认 / Celery 可选），
  `celery_app.py` worker + `requirements-celery.txt` + `TASK_BACKEND=celery` 配置。
- 音质：MIDI Writer 输出 CC7 段落音量曲线 + CC11 表达；弦乐 divisi 双通道分部（基础 pan）。

## T31 风格模板驱动真实作曲差异 ✅

- 目标：同 prompt 切换 style template 后，MusicSpec / MIDI 旋律、节奏、鼓组、贝斯、和声明显不同
- 实现：
  - `style_applier`：strength≥0.5 覆盖已有同 role 轨道（instrument/pattern/register/velocity，保留 track id）；
    harmony_presets 按段落长度写入 `spec.harmony`（lo-fi / battle / rock / ambient / cinematic 各不相同）；
    `seed = stable_hash(seed + template_id + strength)`，可复现且跨模板不同
  - `melody_engine`：消费 melody track.pattern + 风格标签（lofi 稀疏 / game 高密度短音 / rock riff /
    ambient 长音 / chinese 级进），motif density/energy/pitch_shift 不再硬编码
  - `drum_engine`：消费 drums track.pattern（lofi_swing / rock_backbeat / battle_drive / ambient_minimal /
    cinematic_taiko / four_on_floor / funk_groove）
  - `bass_engine`：消费 bass track.pattern（laidback_groove / root_fifth_drive / driving_octaves / funk_groove）
  - `style_tags.normalize_style_tags`：统一识别 lofi/hiphop/rock/game/cinematic/chinese/ambient/electronic
- 测试：`tests/test_style_template_composition.py`（9）+ `tests/test_engine_patterns.py`（3）；
  全量 pytest 501 passed（fast 350 / slow 151）
- 说明：WAV 渲染不会自动重新作曲；需先生成/重新生成 MIDI。MockProvider 下即可体现风格差异。

## 鼓组乐器归一化与终止式告警修复 ✅

- 目标：消除 `UNKNOWN_INSTRUMENT_ALIAS（low_tom_percussion）` 与 `WEAK_SECTION_CADENCE（chorus）` 两个生成 warning
- 实现：
  - `instruments/registry.py`：新增 percussion / drum_percussion / toms / tom / low|mid|high_tom /
    low_tom_percussion / taiko / taiko_drums / cinematic_drums / battle_drums 别名 → `standard_drum_kit`
  - `spec_validator`：`role=drums` 的乐器自动归一化（保留 pattern），不再报未知乐器；
    WEAK_SECTION_CADENCE 接受 V/V7→I 与 IV/iv→I，末和弦非主和弦才告警
  - `cadence_engine`：chorus / final_chorus / outro 自动补终止式（长度 1 扩展为 2 和弦；
    ≥2 替换末两个）；minor 使用 harmonic minor 属和弦（A minor → E7→Am）
  - `harmony_progressions.dominant_symbols`：minor 改用 harmonic_minor（V 为大三/属七）；
    新增 `subdominant_symbols`（IV/iv）
- 测试：instrument registry（+1）、semantic validator（+5）、cadence engine（+3）；
  全量 pytest 510 passed；MockProvider 生成 API 各模板 0 warning

## T32 LM Studio / OpenAI-compatible 本地 LLM Provider ✅

- 目标：在真正调用 DeepSeek 之前，先支持 LM Studio 本地 OpenAI-compatible API 测试完整链路；
  并抽象通用 `OpenAICompatibleProvider` 复用给 Ollama / vLLM / LocalAI 等
- 优先级：P1
- 依赖：T11
- 实现：
  - `packages/llm/openai_compatible_provider.py`：通用基类，统一 `POST {base_url}/chat/completions`
    （base_url 去尾部 `/`、支持 `/v1` 结尾、API Key 允许占位、timeout 可配置、HTTP 错误转清晰
    provider error、`/models` 检查），结构化输出 / 修复 / 重试 / 日志全部复用
  - `packages/llm/deepseek_provider.py`：重构为继承 `OpenAICompatibleProvider`，`DEEPSEEK_*`
    环境变量与默认值完全兼容（base_url / model / timeout / require_api_key）
  - `packages/llm/lmstudio_provider.py`：新增 `LMStudioProvider`（`LMSTUDIO_BASE_URL` /
    `LMSTUDIO_API_KEY`（默认占位 `lm-studio`）/ `LMSTUDIO_MODEL` / `LMSTUDIO_TIMEOUT_SECONDS`）
  - `packages/llm/factory.py`：支持 mock / deepseek / lmstudio / openai_compatible，默认 mock
  - `packages/llm/json_utils.py`：JSONC 行/块注释与尾随逗号清洗（字符串感知）、BOM 处理、
    错误信息带原文片段；markdown 代码块 / 前后解释文本提取保留
  - `scripts/test_llm_provider.py`：本地健康检查（配置摘要隐藏 API Key、/models、/chat/completions、
    JSON 提取、可选 --generate-spec / --generate-midi / --render-audio；失败 exit 1）
  - `scripts/demo_t28_smoke.py`：新增 `--provider`（默认 mock；lmstudio 跑 1 个案例；
    deepseek 仅显式选择；不污染系统环境）
- 验收：`LLM_PROVIDER=lmstudio` 可识别；factory 四档均返回正确 provider；未知 provider 报清晰错误；
  DeepSeekProvider 不被破坏；MockProvider 默认行为不变；API Key 不进入日志；全部单测使用
  mock httpx transport，不真实连接本地/线上服务
- 测试：新增 `test_openai_compatible_provider.py` / `test_lmstudio_provider.py` /
  `test_provider_factory.py` / `test_llm_provider_script.py`，更新 `test_llm_json_utils.py`；
  全量 pytest 550 passed（fast 393 / slow 157）

## T33 多 LLM 环境配置文件按需加载 ✅

- 目标：按需加载不同 LLM Provider 配置，方便在 MockProvider / LM Studio / DeepSeek 之间切换
- 优先级：P1
- 依赖：T32
- 实现：
  - `packages/music_core/config/env_loader.py`：统一 env loader，加载优先级
    `.env`（通用默认）→ profile file（.mock.env / .lmstudio.env / .deepseek.env）→
    `LLM_ENV_FILE`（优先于 profile file）→ 系统环境变量（最高，不被覆盖）；
    未知 profile 抛清晰错误、缺失文件 warning、.env 缺失不崩溃、日志不输出 API Key
  - `services/api/main.py`：启动时调用 `load_env`，打印 profile 与加载文件摘要（无 key）
  - `scripts/run_with_env.py`：`--profile <name> -- <command>` passthrough 执行，
    `--print-env` 只打印加载后的环境（敏感值打码）
  - `scripts/test_llm_provider.py`：新增 `--profile` 支持
  - 新增 `.mock.env.example` / `.lmstudio.env.example` / `.deepseek.env.example`；
    更新 `.env.example`（说明通用配置与 profile 关系）
  - `.gitignore`：忽略 `.env` / `.env.*` / `.mock.env` / `.lmstudio.env` / `.deepseek.env` /
    `*.local.env`，保留 example 可提交
- 验收：`.env` 兼容保留；`.mock.env` / `.lmstudio.env` / `.deepseek.env` 可加载；
  `LLM_ENV_PROFILE` / `LLM_ENV_FILE` 生效；系统环境变量最高优先级；真实 env 不进入 Git、
  example 可提交；MockProvider 默认可用；DeepSeek 仅显式 profile 使用
- 测试：新增 `test_env_loader.py`、`test_run_with_env.py`，更新 `test_provider_factory.py` /
  `test_llm_provider_script.py`；全量 pytest 572 passed（fast 415 / slow 157）

## T34 Gemini OpenAI-compatible Provider ✅

- 目标：通过 Gemini OpenAI-compatible endpoint 调用 Gemini API；优先复用 `OpenAICompatibleProvider`
- 优先级：P1
- 依赖：T32 / T33
- 实现：
  - `packages/llm/gemini_provider.py`：`GeminiProvider(OpenAICompatibleProvider)`，读取 `GEMINI_API_KEY` /
    `GEMINI_BASE_URL`（默认 `https://generativelanguage.googleapis.com/v1beta/openai/`）/
    `GEMINI_MODEL`（默认 `gemini-3.5-flash`）/ `GEMINI_TIMEOUT_SECONDS` / `GEMINI_TEMPERATURE` /
    `GEMINI_MAX_TOKENS` / `GEMINI_REASONING_EFFORT`（none/minimal/low/medium/high，空则不发送）/
    `GEMINI_USE_RESPONSE_FORMAT`（默认 true）
  - 请求：`POST {base_url}/chat/completions`，base_url 去尾部斜杠避免双斜杠；
    `Authorization: Bearer GEMINI_API_KEY`；body 含 temperature / max_tokens / reasoning_effort / response_format
  - response_format fallback：服务返回 HTTP 400/422/404 时自动去掉 response_format 重试，
    再走现有 JSON extract / repair / MusicSpec validation；`LLMAPIError` 增加 `status_code`
  - 基类 `OpenAICompatibleProvider` 新增 `retrieve_model`（`GET /models/{model}`）
  - `factory` 支持 gemini；`env_loader` 新增 `gemini -> .gemini.env`；
    新增 `.gemini.env.example`；`.gitignore` 忽略 `.gemini.env`、保留 example
  - `scripts/test_llm_provider.py` 支持 `--profile gemini` / `--list-models` / `--retrieve-model`
  - 新增 `scripts/start-backend-gemini.ps1`
- 验收：`LLM_PROVIDER=gemini` 可用；`.gemini.env` 可加载；base_url 无双斜杠；
  Bearer 鉴权；reasoning_effort 可配置；response_format 可配置且失败可 fallback；
  Gemini 输出仍经过 JSON extract / repair / validation；支持 models list / retrieve；
  API Key 不进入日志；Mock / LM Studio / DeepSeek 不被破坏
- 测试：新增 `test_gemini_provider.py`，更新 factory / env_loader / script / openai_compatible 测试；
  全量 pytest 596 passed（fast 439 / slow 157）

## T35 生成链路日志与前端调试信息面板 ✅

- 目标：生成 MusicSpec 链路的可观测性——request_id 追踪、结构化错误、阶段日志、
  前端调试面板
- 优先级：P1
- 依赖：T32 / T33 / T34
- 实现：
  - `services/api/middleware/request_id.py`：纯 ASGI RequestIdMiddleware，`X-Request-ID`
    请求头优先，写 scope.state + contextvar，响应头与 JSON 响应体注入 request_id
  - `services/api/main.py`：注册中间件；HTTPException handler 展开统一错误结构
    `{success, request_id, error_code, message, details, error:{code,message,stage,provider,status_code,details}}`；
    新增兜底 500 handler（traceback 记录不返回前端）
  - `services/api/errors.py`：扩充错误码与阶段（UNKNOWN_PROVIDER / LLM_HTTP_ERROR /
    LLM_TIMEOUT / LLM_INVALID_RESPONSE / JSON_PARSE_ERROR / MUSIC_SPEC_VALIDATION_ERROR；
    request_validation / provider_selection / llm_call / llm_response_parse / json_repair /
    music_spec_validation 等）
  - `services/api/logging_config.py`：`LOG_LEVEL` 控制日志级别；`LLM_DEBUG_LOG_CONTENT`
    控制 raw response preview
  - `packages/llm/trace.py`：request_id contextvar + 阶段日志 helper（`[request_id=...]`）
  - `packages/llm/openai_compatible_provider.py`：generate_structured 记录 llm.call.start /
    success / json.parse / repair 阶段；call log 增加 request_id / http_status / content_chars /
    json_parse / raw_response_preview；`_loggable_request` / `_loggable_response` 默认不含完整内容
  - `packages/llm/call_logger.py` + `models.py`：日志文件命名含 provider + request_id；
    记录新增字段
  - 生成接口（songs.py）：response 增加 request_id / warnings（WarningItem）/ debug
    （GenerationDebug）；LLM 异常映射为带 stage 的错误
  - 前端 `client.ts`：结构化错误解析（ApiRequestError 含 code/stage/provider/requestId/
    details/rawBodyPreview；网络 vs HTTP vs JSON 解析错误区分）
  - 前端新增 `components/workspace/GenerationDebugPanel.tsx`：默认折叠、出错自动展开、
    复制 request_id / 错误摘要、warnings / debug / raw preview 展示
- 验收：request_id 贯通响应头 + 响应体 + 错误 + 后端日志；错误含 code/stage；
  前端不再只显示 Failed to fetch；API key 不泄露；Mock 流程不受影响
- 测试：新增 `test_request_id_middleware.py` / `test_api_error_response.py` /
  `test_llm_call_logging.py`，更新 generate_song_api / error_response 测试；
  全量 pytest 611 passed（fast 444 / slow 167）

## T35-Fix LLM 原始响应调试日志 ✅

- 目标：Gemini / LM Studio / DeepSeek 返回 200 OK 但 JSON parse 失败时，用户能查看完整
  原始响应并判断截断 / markdown 包裹 / 非法字符等原因
- 优先级：P1
- 依赖：T35
- 实现：
  - `packages/llm/llm_debug.py`：调试 env（LLM_DEBUG_LOG_CONTENT / LLM_DEBUG_LOG_MAX_CHARS /
    LLM_DEBUG_SAVE_RAW_RESPONSE / LLM_DEBUG_RAW_RESPONSE_DIR / LLM_DEBUG_LOG_FULL_CONTENT）；
    `save_raw_response` 保存 `data/llm_calls/<ts>_<provider>_<request_id>_raw_response.json` +
    `_message_content.txt`，递归 mask api_key / authorization / Bearer；保存失败只 warning
  - `LLMChatResult`：content / http_status / finish_reason / usage / raw_response /
    response_format 状态 / reasoning_effort
  - `llm.call.success` 日志记录 provider / model / base_url / http_status / duration_ms /
    content_chars / finish_reason / prompt_tokens / completion_tokens / total_tokens /
    response_format_enabled / reasoning_effort / raw_response_path / message_content_path
  - `json.parse.failed` 日志附带 raw_response_path / message_content_path / finish_reason /
    content_chars；finish_reason=length 给出截断 hint；stop 但 JSON 非法给出明确提示；
    `LLM_DEBUG_LOG_CONTENT` / `LLM_DEBUG_LOG_FULL_CONTENT` 控制 preview / full content 打印
  - Gemini response_format fallback 记录 `llm.response_format.fallback`
  - `LLMOutputError.debug_info` 透传诊断字段；API error `error.details` 返回
    raw_response_path / message_content_path / finish_reason / content_chars / hint
  - 前端 `GenerationDebugPanel` 展示 raw saved 路径 / finish_reason / content_chars / hint
- 验收：200 OK + JSON parse failed 时 console 能看到 raw_response_path /
  message_content_path / finish_reason / content_chars / usage；保存文件完整且不含 API key；
  API error debug 与前端可显示路径；Mock / LM Studio / Gemini / DeepSeek 不被破坏
- 测试：更新 `test_llm_call_logging.py`（raw 保存 / mask / finish_reason hint / usage）、
  `test_api_error_response.py`（error.details 透传路径）

## T36 LLM 乐器别名归一化与 GM 映射修复 ✅

- 目标：修复 Gemini 等 LLM 输出的自然语言乐器名（brass / electric_guitar_distorted 等）
  无法识别导致的 unknown instrument warning 与 MIDI 默认音色 fallback
- 优先级：P1
- 依赖：T17 / T35
- 实现：
  - 扩展 `instruments/registry.py` 别名表（brass/epic_brass/horns → brass_section、
    electric_guitar_distorted/distortion guitar/heavy_guitar → distortion_guitar、
    strings/string ensemble/orchestral_strings → string_ensemble_1、heavy_drums/rock_drums/
    battle_drums → standard_drum_kit、synth_bass/sub_bass → synth_bass_1、grand piano/
    cinematic_piano → acoustic_grand_piano、pad/warm pad → pad_2_warm 等）
  - `normalize_instrument_name(name, role=None)`：role-aware（drums→standard_drum_kit /
    bass→electric_bass_finger）、复数（strings/drums/horns/violins）、大小写/空格/横线
  - 新增 `canonical_instrument_name`；`normalize_music_spec`（
    `normalization/instrument_normalizer.py`）在语义校验前修正 track.instrument，
    保留 id/role/pattern/register/velocity，记录 instrument.normalized 日志
  - `music_planner.generate_music_spec_from_prompt` 在 validate 前调用 normalize
  - validator 基于 canonical 判断 unknown（brass / electric_guitar_distorted /
    low_tom_percussion 不再 warning），真正未知乐器仍 warning 且建议 canonical
  - System prompt 更新为优先使用 canonical 乐器名
- 验收：brass / electric_guitar_distorted 不再触发 unknown warning 且归一化为合法
  canonical；归一化发生在 validation 前；track 字段不丢失；MIDI 不再 fallback 默认音色；
  真正未知乐器仍 warning；Mock / Gemini / LM Studio / DeepSeek 不被破坏
- 测试：新增 `test_instrument_aliases.py`、`test_music_spec_normalization.py`，
  更新 `test_semantic_validator.py`、`test_midi_writer.py`、`test_generate_song_api.py`；
  全量 pytest 642 passed（fast 469 / slow 173）

## 下一轮建议

1. 文档 / 测试分层：拆分慢速集成测试（如音频渲染 / 全链路 API），缩短全量回归时间。
2. 在联网环境安装 Playwright 浏览器并跑通 `npm run e2e`（用例已就绪）。
3. 生产级任务队列：按需启用 `TASK_BACKEND=celery` 并验证多 worker / 重启恢复。
4. 音质与音色：真实 SoundFont 渲染体验优化、弦乐声部/音色进一步细化。
5. 如未来需要 CI/CD，可重新引入 GitHub Actions / Docker（当前已彻底移除）。

## T33 前端三路由重构（/create、/projects、/projects/:songId）

- T33.0 completed：前端现状扫描与迁移计划（docs/FRONTEND_REFACTOR_T33.md + 组件迁移 JSON）
- T33.1 completed：引入 React Router 与页面壳
  - 新增 react-router-dom@6.30.4（createBrowserRouter）
  - 路由：/ → /create、/create、/projects、/projects/:songId、* → NotFound
  - 页面：CreatePage / ProjectLibraryPage / ProjectWorkspacePage / NotFoundPage + AppShell 导航
  - 过渡组件：LegacyCreateContent（生成控制台，成功后跳转工作台）、LegacyWorkspaceContent
    （原 App 工作台，songId 来自 URL，刷新可恢复）
  - App.tsx 降级为兼容层；main.tsx 挂 RouterProvider；新增 app-shell.css
  - e2e：router.spec.ts 5 用例 + demo.spec.ts 适配；playwright 端口同步 49152
  - 遗留：e2e chromium 需在联网环境安装后运行；生产部署需 SPA history fallback（Nginx try_files）
- T33.2 completed：工程 API 层整理
  - 后端 unblocker：GET /api/v1/projects（列表）+ DELETE /api/v1/songs/{song_id}（删除）
  - 前端 features/projects/：projectTypes（camelCase）+ projectApi（list/get/delete/import/export
    + AbortSignal）+ useProjects + useProject；shared/utils/download.ts；client.ts 支持 signal
  - ProjectLibraryPage 最小列表接入；全量 pytest 669 + npm build 通过
  - 遗留：旧 api/projectApi.ts / musicApi.ts 空壳待 T33.6 合并
- T33.3 completed：工程库页正式版（/projects）
  - features/projects/：ProjectCard + ProjectStatusBadges + DeleteProjectDialog（二次确认）+
    ImportProjectButton + ProjectLibraryPanel（搜索 title/songId + 状态筛选 + 刷新）
  - 页面组合 useProjects + Dialog + Import；导入成功跳转新工程；无 N+1；后端无修改
  - npm build 通过（142 modules）
- T33.4 completed：创作页独立化（/create）
  - features/generation/：useGenerateSong + generationApi + PromptGeneratePanel +
    StyleTemplateSelector + GeneratedProjectSummary
  - CreatePage 重写：生成成功不自动跳转，摘要确认后进入 /projects/:songId；T31
    style_template_id/style_strength 链路回归确认；npm build 通过（146 modules）
- T33.5 completed：工程工作台独立化（/projects/:songId）
  - features/workspace/：useProjectWorkspace 协调层（useProject + 业务 hooks，避免重复 getSong，
    切换清理 + race 防护）+ WorkspaceHeader（←工程库/标题/版本/资产 badges）
  - ProjectWorkspacePage 重写：URL songId 四态处理，刷新可恢复；无 selectedSongId /
    window.reload / 组件内 fetch；npm build 通过（148 modules）
- T33.6 completed：工作台功能模块拆分与 shared 抽取（features/workspace、midi、audio、soundfonts、
  versions、tasks、quality、export；删除 components/workspace + components/legacy + 顶层旧组件；
  修复 features 内全部 import 断链；build 通过，详见 FRONTEND_REFACTOR_T33.md）
- T33.7-T33.9：SoundFont/Renderer 整合 → 导入导出/删除确认增强 → 回归收尾（待办）
