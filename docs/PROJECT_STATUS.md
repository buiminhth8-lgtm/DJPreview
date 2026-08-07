# 项目状态（Project Status）

> 最近一次实测：2026-08-06（分支 `master`）。以下状态均以代码与测试实际结果为准，
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
- T33.6：前端工作台功能模块拆分（ProjectWorkspacePage 只做组合；MIDI/Audio/SoundFonts/Versions/
  Tasks/Quality/Export 归入对应 feature；`components/workspace`、`components/legacy` 与顶层旧组件已删除；
  修复全部跨目录 import 断链；build 通过）
- T32：LM Studio / OpenAI-compatible 本地 LLM Provider
  （`OpenAICompatibleProvider` 基类：`POST /chat/completions`、base_url 去尾部斜杠、API Key 占位、
  `/models` 检查、HTTP 错误转清晰 provider error；`DeepSeekProvider` 重构继承基类并保持
  `DEEPSEEK_*` 兼容；新增 `LMStudioProvider`（`LMSTUDIO_*`）；工厂支持 mock / deepseek /
  lmstudio / openai_compatible，默认 mock；JSON 工具增强：markdown 代码块 / 前后文本 /
  JSONC 注释与尾随逗号清洗 / BOM；`scripts/test_llm_provider.py` 本地健康检查脚本；
  `demo_t28_smoke.py` 支持 `--provider`）
- T33：多 LLM 环境配置文件按需加载
  （新增 `packages/music_core/config/env_loader.py`：`.env` → profile（.mock.env / .lmstudio.env /
  .deepseek.env）→ `LLM_ENV_FILE` → 系统环境变量（最高优先级）；未知 profile 报错、缺失文件
  warning、API Key 不进入日志；`services/api/main.py` 启动时加载；新增 `scripts/run_with_env.py`
  （passthrough 命令执行 + `--print-env` 打码展示）；`scripts/test_llm_provider.py` 支持 `--profile`；
  新增 `.mock.env.example` / `.lmstudio.env.example` / `.deepseek.env.example`；`.gitignore`
  忽略真实 env、保留 example）
- T34：Gemini OpenAI-compatible Provider

  （新增 `GeminiProvider`（`packages/llm/gemini_provider.py`），复用 `OpenAICompatibleProvider` 基类：
  `GEMINI_*` 环境变量（API_KEY / BASE_URL / MODEL / TIMEOUT / TEMPERATURE / MAX_TOKENS /
  REASONING_EFFORT / USE_RESPONSE_FORMAT）；base_url 尾部斜杠拼接去重避免双斜杠；
  请求含 `Authorization: Bearer`、`reasoning_effort`（空则不发）、`response_format`（可配置）；
  response_format 被拒（HTTP 400/422/404）自动 fallback 到普通 chat completions；
  `LLMAPIError` 增加 `status_code`；基类新增 `retrieve_model`；factory 支持 gemini；
  env_loader 新增 `gemini -> .gemini.env`；新增 `.gemini.env.example`、`.gitignore` 忽略
  `.gemini.env`；`scripts/test_llm_provider.py` 支持 `--profile gemini` / `--list-models` /
  `--retrieve-model`；新增 `scripts/start-backend-gemini.ps1`）
- T35：生成链路日志与前端调试信息面板
  （新增 `RequestIdMiddleware`（纯 ASGI，`X-Request-ID` 请求头优先，响应头 + JSON 响应体注入
  request_id）；统一错误结构 `{success, request_id, error_code, message, details,
  error:{code, message, stage, provider, status_code, details}}`，错误码 / 阶段扩充
  （UNKNOWN_PROVIDER / LLM_HTTP_ERROR / LLM_TIMEOUT / LLM_INVALID_RESPONSE / JSON_PARSE_ERROR /
  MUSIC_SPEC_VALIDATION_ERROR 等）；`services/api/logging_config.py`（`LOG_LEVEL` 控制，
  `LLM_DEBUG_LOG_CONTENT` 控制 raw preview）；`packages/llm/trace.py` contextvar 传递 request_id；
  LLM call logger 增强（request_id / http_status / content_chars / json_parse /
  raw_response_preview，文件名含 provider + request_id）；生成接口响应新增 request_id /
  warnings（结构化）/ debug（provider / model / llm_duration_ms / validation_warning_count）；
  前端 `client.ts` 结构化错误解析（code / stage / requestId / provider / rawBodyPreview，
  网络错误 vs HTTP 错误 vs JSON 解析错误区分）、新增 `GenerationDebugPanel`（默认折叠、
  出错自动展开、复制 request_id / 错误摘要、warnings / debug / raw preview 展示）；
  新增 `test_request_id_middleware.py` / `test_api_error_response.py` / `test_llm_call_logging.py`）
- T35-Fix：LLM 原始响应调试日志
  （新增 `packages/llm/llm_debug.py`：`LLM_DEBUG_LOG_CONTENT` / `LLM_DEBUG_LOG_MAX_CHARS` /
  `LLM_DEBUG_SAVE_RAW_RESPONSE` / `LLM_DEBUG_RAW_RESPONSE_DIR` / `LLM_DEBUG_LOG_FULL_CONTENT`；
  `save_raw_response` 保存完整 upstream response + message content 到
  `data/llm_calls/<ts>_<provider>_<request_id>_raw_response.json` 与 `_message_content.txt`
  （递归 mask api_key / authorization / Bearer）；`LLMChatResult` 记录 finish_reason / usage /
  raw_response；`llm.call.success` / `json.parse.failed` 日志包含 finish_reason / usage token /
  raw_response_path / message_content_path；finish_reason=length 给截断 hint、stop 但 JSON
  非法给明确提示；`LLMOutputError.debug_info` 透传诊断字段，API error `error.details` 返回
  raw_response_path / message_content_path / finish_reason / content_chars / hint；
  前端调试面板展示 raw saved 路径 / finish_reason / hint）
- T36：LLM 乐器别名归一化与 GM 映射修复
  （扩展 `packages/music_core/instruments/registry.py` 别名表：brass/epic_brass/horns → brass_section、
  electric_guitar_distorted/distortion guitar/heavy_guitar → distortion_guitar、strings/string ensemble/
  orchestral_strings → string_ensemble_1、heavy_drums/rock_drums/battle_drums → standard_drum_kit、
  synth_bass/sub_bass → synth_bass_1、grand piano/cinematic_piano → acoustic_grand_piano 等；
  `normalize_instrument_name` 支持 role 参数（drums→standard_drum_kit / bass→electric_bass_finger）与
  复数/大小写/空格/横线归一化；新增 `canonical_instrument_name`；新增
  `packages/music_core/normalization/instrument_normalizer.py`（`normalize_music_spec` 在语义校验前修正
  track.instrument，保留 id/role/pattern/register/velocity，记录 instrument.normalized 日志）；
  `music_planner.generate_music_spec_from_prompt` 在 validate 前调用 normalize；
  validator 基于 canonical 判断 unknown，真正未知乐器仍 warning 且带建议；
  System prompt 更新为优先使用 canonical 乐器名）
- T38 Frontend Workspace Redesign
  - T38-A completed：前端结构审计与改版方案（新增 `docs/FRONTEND_WORKSPACE_REDESIGN.md`：
    入口/组件/hooks/API/条件渲染审计、目标瀑布流布局、Empty State / Disabled State 规划、
    数据依赖矩阵、T38-B ~ T38-J 切片、风险与缓解）
  - T38-B completed：UI primitives 与工作台设计变量（新增 `apps/web/src/components/ui/`：
    SectionCard / PanelHeader / EmptyState / StatusBadge / ActionButton / ButtonRow /
    KeyValueGrid / InlineNotice / LoadingState / ErrorState + index barrel；新增
    `apps/web/src/styles/design-tokens.css`（`--workspace-*` tokens）与
    `apps/web/src/styles/workspace-ui.css`（`ui-*` 类名，含 768px 响应式）；
    组件不依赖业务数据、未接入现有页面）
  - T38-C completed：持久化瀑布流工作台骨架（新增 `WorkspaceDashboard` 总容器：
    首次打开页面所有核心模块入口常驻显示，无 song/spec 时 Empty State，有 song 时接入现有
    真实面板；新增 `WorkspaceSectionPlaceholder`（SectionCard+EmptyState+StatusBadge）、
    `ProjectOverviewPanel`（轻量工程概览，纯 props）；改造 `WorkspaceHeader`（AI Music Studio
    + Provider/Model/状态 badges）；新增 `styles/workspace-layout.css`（瀑布流 + 响应式）；
    `App.tsx` 改渲染 WorkspaceDashboard，保留全部 hooks/handlers）
  - T38-D completed：生成控制台与项目概览（新增 `GenerateConsole`：prompt 输入、Provider/Model/
    response_format 徽章、生成 MusicSpec / MIDI / WAV / 完整歌曲按钮（带 disabled 原因）、
    风格模板保留、错误 InlineNotice；升级 `ProjectOverviewPanel`：标题/风格/BPM/调性/拍号/长度/
    段落数/轨道数/Warnings/song_id/版本/MIDI/WAV/request_id，安全读取字段；`workspace-hero-grid`
    双列 1.35fr/0.65fr，900px 单列；生成 MusicSpec 功能保留）
  - T38-E completed：播放、下载、MusicSpec、warnings、debug 面板常驻化（新增 `PlaybackDownloadPanel`
    （播放器/下载按钮 disabled 原因/Empty State）、`MusicSpecPanel`（摘要+JSON）、`WarningsPanel`
    （字符串+结构化 warning）、`JsonPreview`（滚动+复制）；升级 `GenerationDebugPanel` 常驻显示
    （空态/request_id/provider/model/error/raw path）；`styles/workspace-results.css`；下载按钮无资产
    disabled 并提示；无 song_id/asset 不触发无效请求）
  - T38-F completed：曲式/和声、轨道/乐器、Piano Roll 面板常驻化（新增 `FormHarmonyPanel`
    （form timeline + harmony progression + orphan warning）、`SectionTimeline`（workspace 版）、
    `HarmonyProgressionView`（chord chips + section warnings）、`TrackInstrumentPanel`（轨道表 +
    track warnings + instrument normalization 建议）、`PianoRollPanel`（无 songId/无 MIDI 时 Empty State
    且不请求 piano-roll endpoint，有 MIDI 才挂载真实 PianoRoll）；「编曲质量」保留为独立段
    （QualityReportPanel + 自动优化）；`styles/workspace-structure.css`）
  - T38-G completed：混音器、Stems、版本管理、自然语言编辑面板常驻化（升级 `MixerPanel`：无工程/
    无 tracks Empty State、有 songId+tracks 才挂真实混音器；新增 `StemsPanel`：无 MIDI/WAV 导出 disabled
    并提示原因、导出后分轨表 + stems.zip；升级 `VersionPanel`：无工程 Empty State、列表 + 详情/Diff/
    恢复（window.confirm 确认）；新增 `EditSongPanel`：无工程 Empty State、应用修改 / 应用并重新渲染
    （autoRender）；    `useSongProject.edit` 增加 autoRender 参数、`App.handleApplyEdit` 透传；
    `styles/workspace-editing.css`）
  - T38-H completed：SoundFont、工程导入导出、任务日志面板常驻化（新增 `SoundfontPanel`：
    无工程扫描可用、应用/选择音源需 song_id 且带原因、无音源 Empty State；新增
    `ProjectImportExportPanel`：导入始终可用、导出工程/下载 MIDI/WAV/Stems 无资产 disabled、
    导入失败提示；升级 `RenderTasksPanel`：无工程 Empty State、有工程才 listSongTasks、
    任务卡片（状态 badges/进度/错误/result JSON）、刷新按钮、`TaskStatusList` 只读列表；
    `styles/workspace-utilities.css`；与 GenerationDebugPanel（LLM 调试）职责区分）
  - T38-I completed：整体 UI 美化与响应式优化（design-tokens 补充 elevated/surface-hover/
    primary-soft/accent-soft；`workspace-dashboard` 全屏渐变背景 + `workspace-dashboard-inner`
    居中 1280px；Header 桌面横向/移动堆叠 + 渐变标题 + aria；SectionCard 玻璃拟态；
    新增 `workspace-responsive.css`：表格/JSON/Debug/任务/Piano Roll 溢出处理 + 760/600/480
    断点；WorkspaceDashboard 外层结构调整；未改 hooks/API/后端）
  - T38-J completed：前端回归测试与文档同步（条件渲染审计：17 个核心模块顶层常驻；
    移除 T38-C 遗留「更多操作」重复区块（PlayerPanel 已被持久化面板覆盖）；无效 API 请求
    审计：hooks 均带 song_id guard、无 `/songs/null|undefined|//` 风险；disabledReason /
    Empty / Loading / Error State 审计通过；新增 `docs/FRONTEND_WORKSPACE_QA.md` 手工 QA
    清单（项目无 Vitest/RTL，仅 Playwright E2E，未新增测试框架））
  - T38 系列状态：T38-A ~ T38-J 全部 completed（前端工作台常驻瀑布流改版完成）
- T39-A completed：渲染器状态显示与音色质量提示。后端 `AudioMetadata` schema 扩展
  `renderer_label` / `quality`（preview/basic/soundfont/unknown）/ `renderer_warnings`（结构化：
  FALLBACK_RENDERER_QUALITY / SOUNDFONT_NOT_SELECTED / RENDERER_UNKNOWN）/ `soundfont_id` /
  `soundfont_name` / `soundfont_path`；渲染时按 renderer+soundfont 写入（fallback→quality=preview +
  FALLBACK_RENDERER_QUALITY 警告，fluidsynth+soundfont→quality=soundfont）。新增
  `packages/renderer/renderer_metadata.py`。前端新增 `RendererStatusCard` 组件并在
  PlaybackDownloadPanel（WAV 渲染后显示渲染器/音质/SoundFont + fallback 提示）、
  ProjectOverviewPanel（Renderer/Quality/SoundFont 摘要）、GenerationDebugPanel（renderer 明细）
  展示；`useAudioAssets` 暴露 `audioRenderMetadata`；类型 `AudioRenderMetadata` 新增。
   后端测试：`tests/test_audio_api.py` 新增 metadata 质量字段与旧 metadata 兼容测试（通过）。
   未改渲染核心逻辑 / MIDI composer / MusicSpec schema；未提交真实 SoundFont。
- T39-B completed：SoundFont 渲染链路诊断与修复（soundfont selection 贯通 + FluidSynth 渲染增强）。
  新增 `packages/renderer/fluidsynth_check.py`（`detect_fluidsynth()`：FLUIDSYNTH_BIN/FLUIDSYNTH_PATH/
  PATH/`--version`，捕获 not found/权限/超时/非零退出；`validate_soundfont_file()`：存在/可读/后缀/
  `.sf2` RIFF 头）。`_render_audio_for` 重构为「读项目选择 → 校验文件 → 检测 FluidSynth → 优先
  FluidSynth，失败才回退」并写入结构化 `is_fallback` / `fallback_reason`
  （no_soundfont_selected / soundfont_file_missing / soundfont_not_found / fluidsynth_unavailable /
  fluidsynth_render_failed / renderer_not_configured）与 `fluidsynth` 状态；`AudioMetadata` schema 扩展
  `is_fallback` / `fallback_reason` / `fluidsynth`；FluidSynthRenderer 复用 `detect_fluidsynth`。
  新增诊断 API `GET /api/v1/soundfonts/diagnostics`（目录/文件校验/FluidSynth/renderer_backends）。
  前端：RendererStatusCard 仅当 `is_fallback=true` 显示 fallback 提示并展示 fallback_reason；
  SoundfontPanel 显示 FluidSynth 可用状态与诊断错误；`useSoundfonts` 暴露 `diagnostics`；
  types 新增 `FallbackReason` / `FluidsynthStatus` / `SoundfontDiagnosticsResponse`。
  新增 `tests/test_render_chain_diagnostics.py`（13 项：检测/校验/各 fallback_reason/FluidSynth 成功/
  失败回退/异步任务一致/诊断 API）。全量 pytest 657 passed；未提交真实 SoundFont。
- T39-C completed：修复 Windows/Chocolatey 下 FluidSynth 版本检测误判。`detect_fluidsynth` 改为
  按 `-V` → `--version` 顺序尝试（Windows 下 `--version` 可能报 `Unknown switch '-'`，不代表不可用），
  每个检测命令 3s timeout，返回 `version_arg` / `version_check_errors`；不使用会进入交互 console 的
  `-version`；`FLUIDSYNTH_BIN=fluidsynth` 裸命令名用 `shutil.which` 解析。渲染命令改为**选项前置**
  （`-ni -F <wav> -r <sr> -g <gain> <sf> <midi>`）——实测 Windows 下 midi 放在 `-F` 前会卡住，
  选项前置可正常非交互渲染并退出；timeout 60s。诊断 API 返回 `version_arg` / `version_check_errors`。
  新增测试 7 项（-V/--version 各种组合、裸命令名解析、timeout、命令选项前置/含 -ni/不含 shell）。
  本机实测：`-V` 成功（2.4.7）→ 同步/异步渲染均 `renderer=fluidsynth`、`is_fallback=false`、无 warning。
  全量 pytest 664 passed；未提交真实 SoundFont。
- T31（风格作曲差异）：StyleApplier 覆盖已有同 role 轨道（instrument/pattern/register/velocity）、
  harmony_presets 写入 MusicSpec、template_id + strength 派生 seed；MelodyEngine 消费 style/pattern 调密度音区；
  DrumEngine / BassEngine 消费 canonical pattern（lofi_swing / rock_backbeat / battle_drive / ambient_minimal /
  laidback_groove / driving_octaves 等）；MockProvider 下不同模板生成明显不同的 MusicSpec 与 MIDI
- 修复：鼓组 / tom / percussion / taiko 类乐器别名统一归一化为 `standard_drum_kit`（MIDI 仍走 channel 9，
  不写 melodic program，pattern 保留）；chorus / outro / final_chorus 自动补明确终止式（V7/IV → 主和弦），
  minor 使用 harmonic minor V（如 A minor → E7 → Am）；validator 接受 authentic（V/V7→I）与
  plagal（IV/iv→I）终止式，真正 weak cadence 仍告警
- T33.1 completed：前端引入路由与页面壳（前端三路由重构第 1 步）。
  新增 `react-router-dom@6.30.4` + `createBrowserRouter`；`app/router.tsx`（/ → /create、
  /create、/projects、/projects/:songId、* → NotFound）、`app/layout/AppShell.tsx`（顶部导航
  + Outlet，无业务状态）、`pages/CreatePage / ProjectLibraryPage / ProjectWorkspacePage /
  NotFoundPage`；`components/legacy/LegacyCreateContent.tsx`（生成控制台 + 概览，成功后跳转
  /projects/:songId）与 `LegacyWorkspaceContent.tsx`（原 App 工作台状态原样保留，songId 来自
  URL 并可刷新恢复）；`App.tsx` 降级为兼容层（Navigate /create），`main.tsx` 挂 RouterProvider；
  新增 `styles/app-shell.css`；e2e 新增 `router.spec.ts` 5 用例、`demo.spec.ts` 适配新路由、
  playwright.config 端口同步为 49152。build 通过（133 modules）。遗留：e2e chromium 本机下载
  超时未跑；正式工程库列表留 T33.3；feature 拆分留 T33.4~T33.6。
- T33.2 completed：工程 API 层整理。后端最小 unblocker：新增 `GET /api/v1/projects`（工程列表，
  倒序）与 `DELETE /api/v1/songs/{song_id}`（删除工程）；storage 新增 `list_project_ids` /
  `delete_project` / `get_project_summary`；schema 新增 `ProjectSummaryItem` / `ProjectListResponse`；
  新增 `tests/test_project_list_api.py`（5 用例）。前端新增工程生命周期统一入口
  `features/projects/`：`projectTypes.ts`（camelCase 映射，Project == 后端 song project）、
  `projectApi.ts`（listProjects/getProject/deleteProject/importProject/exportProject，均支持
  AbortSignal）、`useProjects.ts`（列表 + removeProject + 防竞态）、`useProject.ts`（URL 刷新
  恢复 + 404/notFound + unmount 取消）；复用 `api/client.ts` 作为 httpClient（新增 AbortSignal
  透传与 ABORTED code）；新增 `shared/utils/download.ts`（downloadBlob +
  filenameFromContentDisposition）。`ProjectLibraryPage` 最小列表接入 useProjects；
  `ProjectWorkspacePage` 保持 LegacyWorkspaceContent（避免重复请求）。全量 pytest 669 passed；
  npm build 通过（136 modules）。  遗留：旧 `api/projectApi.ts`（仅 import/export）与
  `musicApi.ts` 空壳待 T33.6 合并清理；正式工程库 UI（搜索/删除确认/导入）留 T33.3/T33.8。
- T33.3 completed：工程库页 ProjectLibraryPage 正式版。/projects 升级为可用工程库：
  新增 `features/projects/` 组件 `ProjectCard`（标题/时间/版本/songId/状态 badges/打开/导出/
  删除）、`ProjectStatusBadges`（MIDI/WAV/质量/Fallback/FluidSynth/SF，仅真实字段）、
  `DeleteProjectDialog`（role=dialog + aria-modal，二次确认，删除中禁用，失败保持打开）、
  `ImportProjectButton`（.zip/.aimusic.zip + FormData，idle/importing/error）、
  `ProjectLibraryPanel`（客户端搜索 title/songId + 状态筛选 全部/有WAV/有MIDI/Fallback +
  刷新 + 过滤空态）；页面组合 useProjects + Dialog + Import，删除成功本地移除，
  导入成功 reload + navigate 新工程；`shared/utils/date.ts`（formatDateTime，Intl）；
  样式 grid auto-fill 280px / 窄屏 1 列 / dialog。无 N+1 请求；后端无修改
  （T33.2 list/delete 已就绪）；导出/导入 round-trip 实测通过。npm build 通过
  （142 modules）。遗留：删除失败细分、导出增强、服务端搜索留后续。
- T33.4 completed：创作页 CreatePage 独立化与生成流程收敛。新增 `features/generation/`：
  `useGenerateSong.ts`（prompt/styleTemplateId/styleStrength 状态只属于 CreatePage；防重复提交；
  AbortController 防 unmount 旧请求；失败保留表单；再次生成创建新工程）、`generationApi.ts`
  （复用 songApi.generateMusicSpec，规范化 GeneratedProjectSummary）、`generationTypes.ts`、
  `PromptGeneratePanel.tsx`、`StyleTemplateSelector.tsx`（模板加载失败不阻塞基础生成）、
  `GeneratedProjectSummary.tsx`（BPM/调性/拍号/风格/段落/轨道/warnings + 进入工作台按钮）。
  `CreatePage.tsx` 重写：组合 useGenerateSong + 摘要，生成成功后**不自动跳转**，用户确认后点击
  进入 /projects/:songId；`songApi.generateMusicSpec` 增加 AbortSignal。T31 回归确认：
  style_template_id / style_strength 经前端链路正确传后端（实测后端返回一致）。遗留：
  LegacyCreateContent 无引用待 T33.6 删除；Workspace 内 GenerateConsole 保留（T33.6 再定）；
  App.tsx create 状态随 LegacyCreateContent 停用。npm build 通过（146 modules）。
- T33.5 completed：工程工作台页 ProjectWorkspacePage 独立化与单工程状态收敛。
  新增 `features/workspace/useProjectWorkspace.ts`（协调层：useProject 页面级 loading/404/error/
  reload + 业务 hooks 组合；useProject 详情注入 useSongProject 避免重复 getSong；切换 songId
  立即清理旧资产；refs 防 stale closure；重绑后自动刷新）与 `features/workspace/WorkspaceHeader.tsx`
  （←工程库 + 标题 + songId + 版本 + MIDI/WAV/FluidSynth/Fallback/SF badges + error，仅真实
  metadata）。`ProjectWorkspacePage.tsx` 重写：URL songId → useProjectWorkspace，四态处理
  （missing/404/loading/error + 重新加载），组合 WorkspaceDashboard 全部回调。
  MIDI/audio/versions/soundfont/tasks 状态仍由各自 hook 管理（复用）。
  `/projects/:songId` 刷新可恢复；检查无 selectedSongId、无 window.location.reload/href、
  无组件内直接 fetch。npm build 通过（148 modules）。遗留：LegacyWorkspaceContent 不再被引用
  （T33.6 删除）；App.tsx 兼容层与 Workspace 内 GenerateConsole 去留、面板按 feature 拆分、
  useSongProject 深拆留 T33.6。



## Partially Completed / Needs Verification（部分完成或需验证）

- 音频渲染质量：fallback 渲染器为开发兜底（三角波合成），音色保真有限；真实音源依赖用户自备 SoundFont + FluidSynth。
  前端「渲染器状态」已明确提示当前是否为预览级音色并引导选择 SoundFont（T39-A）；
  T39-B 后若仍 fallback 会给出结构化原因（如 `fluidsynth_unavailable` / `soundfont_file_missing`）。
- 音乐分析指标（旋律 / 和声 / 节奏 / 编曲）为轻量辅助，未并入 QualityReport 评分模型。
- Evaluation trait 打分语义仍较粗（如 `has_track_role2` 与 `has_track_role` 有重复），后续可细化。
- MIDI Parser 对文件末尾仍未关闭的 `note_on` 按“丢弃”处理，未做按轨道末 tick 收尾。
- **WAV 渲染不会自动重新作曲**：切换风格模板后需先重新生成（新 song_id / 新 MusicSpec）再生成 MIDI，
  最后渲染 WAV；直接对旧歌曲渲染 WAV 不会应用新模板。

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

## 当前测试与构建结果（2026-08-06 实测）

```text
后端：pytest -q → 642 passed（LLM_PROVIDER=mock、AUDIO_RENDERER=fallback）
快速回归：pytest -m "not slow" → 469 passed（约 22s）
慢速集成：pytest -m slow → 173 passed
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

2026-08-06
