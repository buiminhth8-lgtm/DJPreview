# 项目状态（Project Status）

> 最近一次实测：2026-08-12（分支 `master`）。以下状态均以代码与测试实际结果为准，
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
- T33.7：SoundFont / Renderer 状态前端整合（selected ≠ rendered SoundFont；fallback 仅以
  audio metadata `is_fallback` 为准；WAV stale 标记在 SoundFont/MIDI 变化后置位、渲染成功后清除；
  RendererStatusCard 不再用 renderer/quality 推断 fallback；FluidSynth diagnostics 与当前 WAV 解耦）
- T33.8：工程导入导出 / 删除 / 二次确认流程整合（ExportMenu 统一导出、downloadBlob 统一下载、
  Workspace 删除二次确认 + 成功后清理状态并回 /projects；Library 与 Workspace 删除共用同一 Dialog）
- T33-R（审计）：T33 整体判 **PARTIAL**（Critical Gates 10/10 通过，架构目标达成；浏览器端三 Flow、
  真实 FluidSynth 渲染链路与前端自动化测试未验证/未执行，T33.9 待办）。
  详见 [docs/T33_RETROSPECTIVE.md](docs/T33_RETROSPECTIVE.md)
- T33-R1（浏览器回归）：三条主流程真实浏览器验证 **PASS**（Playwright 11 passed；含路由、刷新恢复、
  A/B 隔离、编辑/版本、删除生命周期、SoundFont UI 语义）；修复自然语言编辑失效的 P1 bug
  （handleApplyEdit 异步 state 读取问题）。详见 [docs/T33_RETROSPECTIVE.md](docs/T33_RETROSPECTIVE.md)
- T33-R4（真实渲染验收）：FluidSynth 2.4.7 + GeneralUser-GS.sf2 真实链路 **PASS**
  （renderer=fluidsynth、is_fallback=false、soundfont_name=GeneralUser-GS；同步与异步任务均 succeeded；
  Workspace 无 fallback warning、刷新保持；后端 46 passed）。详见 [docs/T33_RETROSPECTIVE.md](docs/T33_RETROSPECTIVE.md)
- T33-R3（前端自动化测试）：Vitest + Testing Library 引入，**13 个关键状态用例 PASS**
  （fallback 语义、selected≠rendered、audio stale、删除防重复、Blob revoke、songId 隔离）；
  修复 downloadBlob 异常路径未 revoke 的小 bug。详见 [docs/T33_RETROSPECTIVE.md](docs/T33_RETROSPECTIVE.md)
- T33-R2（Legacy 清理）：删除 5 个无引用 hooks（useMixer/useQuality/useEvaluation/useReferenceMidi/
  useRenderTasks）与 `api/musicApi.ts` 兼容壳（10 处 import 迁往领域 API）；
  TrackMixerStrip 移至 features/audio；无循环依赖；build + 13 passed。
- T33-R-Final（最终复审）：**T33 前端改造整体 COMPLETED**（架构 Critical Gates 10/10、
  Goal 25/25、Flow A/B/C PASS、Playwright 12 passed、Vitest 13 passed、后端关键 76 passed、
  真实 FluidSynth 渲染 PASS）。详见 [docs/T33_RETROSPECTIVE.md](docs/T33_RETROSPECTIVE.md)
- T33-UI1：工程库批量选择/删除（checkbox、全选当前结果、indeterminate、BatchDeleteDialog 二次确认、
  Promise.allSettled 部分失败处理）；Workspace 完整 song_id + 复制；宽屏主体
  `min(1680px, 100vw-48px)` 与统一 padding/gap；无重复 Header；build + 18 前端测试 + E2E 11 passed。
- T34.0 started / completed：MIDI Track Editor 技术扫描与数据模型设计（设计阶段）。设计详见
  [docs/MIDI_EDITOR_T34.md](docs/MIDI_EDITOR_T34.md)。
- T34.1 completed：Editable MIDI Note Model + Read API。新增后端
  `services/api/schemas/midi_editor.py`（MidiEditorDocument/Track/Note，tick 语义 +
  pitch/start/duration/velocity/channel 校验）、`packages/music_core/midi/midi_editor_io.py`
  （只读适配：保留文件 PPQ、稳定 track_id=MusicSpec track.id、deterministic note_id=
  sha1(track|ch|pitch|start|occurrence)、FIFO 配对重叠同音、note_on velocity=0 当 note_off、
  单轨 10000 notes 上限）、`GET /songs/{id}/midi/editor`（404 project/midi_not_found；
  不自动生成 MIDI）。前端新增 `features/midi/editor/`：`midiEditorTypes.ts`、
  `midiEditorApi.ts`（snake→camel 归一化 + AbortSignal）、`useMidiEditorDocument.ts`
  （songId 缺失不发请求/变化重载/防竞态/unmount 取消）。设计变更：Note ID 由会话级 UUID 改为
  deterministic（T34.1 §8 要求跨读取稳定）。测试：后端 `test_midi_editor_api.py` 11 passed、
  MIDI/version 回归 31 passed；前端 Vitest 23 passed（含 5 个 editor 测试）；npm build 通过。
  真实 composer MIDI smoke：5 tracks（melody/harmony/bass/drums/pad）、drums ch9、tick 正确、
  track/note ID 跨读取稳定（1241 notes）。现有 PianoRoll 未改动。
- T34.2 completed（随 T34.6 集成关闭）：`POST /midi/edit` 写回目标 Track、保留其他 Track/meta/PPQ，
  创建 `manual_midi_edit` 新 Version，并以 `base_version_id` + 409 防止旧 Draft 覆盖 current。
- T34.3 completed：MIDI Editor Shell + Track Selector + Read-only Piano Roll。新增
  `features/midi/editor/`：`MidiEditor.tsx`（顶层组合 + 默认轨道规则 + 空/loading/error）、
  `TrackSelector.tsx`（canonical track.id + role 辅助 + notes 计数）、`TimelineHeader.tsx`
  （bar 编号，PPQ+meter）、`PianoKeyboard.tsx`（C/octave 标注）、`PianoRollViewport.tsx`
  （tick→x / pitch→y / note.id key / 点击高亮）、`midiEditorLayout.ts`（纯函数坐标/PPQ）。
  `PianoRollPanel` 在 hasMidi 时挂载 MidiEditor（保留无 MIDI EmptyState + 生成按钮），
  旧 `PianoRoll.tsx` 不再被引用。默认轨道 = 第一个有 Notes 的轨道；切换本地 O(1)；
  songId/refreshKey 变化 reload + 重选轨道 + 清空选择；无 MIDI → EmptyState、loading/error
  正确处理；空轨道可选择；不实现编辑/缩放/undo。测试：Vitest 44 passed（含 13 个新 editor/
  坐标测试：4/4 与 3/4、tick→px、pitch→row、默认选择、轨道切换、空轨、note.id、songId 隔离）；
  npm build 通过（133 modules）。真实电子工程 smoke：5 tracks、bass pitch 36-52、drums ch9、
  bass 114 notes 定位正确。T34.4 next（Note CRUD + Snap）。
- T34.4 completed：Note CRUD + Snap + Draft Editing。新增 `useMidiEditorDraft.ts`
  （draftNotesByTrack 每轨道独立 session draft；immutable；document 变化重置；
  add/delete/move/resize/setVelocity + 边界 clamp + temp id `draft:uuid`）与
  `midiEditorGeometry.ts`（snap 纯函数 getSnapTicks/snapTick/snapResizeEnd + pointer 坐标
  toGridRelative + midiPitchToNoteName）。PianoRollViewport 升级为可编辑：双击添加、拖主体
  move（startTick/pitch）、右边缘 resize（durationTick）、网格 subdivision、Pointer Events +
  setPointerCapture、drag threshold、commit-on-pointerup；MidiEditor 增加 Snap 工具栏
  （1/1-1/32+Off）与 Velocity 编辑（clamp 1..127）+ Delete/Backspace 键盘守卫（输入框不误删）。
  Draft 不调用 Save/Version/Render API。测试：Vitest 69 passed（snap 换算含 960/1200 PPQ、
  add/delete/move/resize/velocity、边界 clamp、scroll 坐标、轨道隔离、document reload 重置、
  键盘守卫、拖拽交互）；npm build 通过（135 modules）。代码审计确认编辑器无 save/version/
  render 调用；真实工程只读 smoke 稳定。T34.5 next（Zoom/Pan/Fit/Lock）。
- T34.5 completed：MIDI Editor Viewport（Zoom/Pan/Fit/Track Lock）。新增 `useMidiViewport.ts`
  （pixelsPerTick H zoom 0.25x-4x、rowHeight V zoom 6-28、scrollLeft/Top、fitTrack、resetZoom；
  只改视觉映射不改 canonical tick/pitch）。PianoRollViewport 升级：Ctrl+Wheel H zoom、
  Shift+Wheel 横滚、Space+Drag pan（优先于 add/move/resize）、locked 阻止 Add/Delete/Move/Resize
  handler、scroll 回调；MidiEditor 增加 zoom 工具栏（H/V +/-、百分比、Fit）、每轨道 Lock
  （lockedTrackIds，保留 Draft、Velocity input disabled）、Space 键 pan。document/songId 变化
  清除 lock/selection/zoom。测试：Vitest 80 passed（zoom limits/percent/fit/empty fit/单 note
  有界、lock 阻止 delete/velocity 且保留 draft、既有 CRUD/坐标/隔离回归）；npm build 通过
  （136 modules）。  无 save/version/render 调用。T34.6 next（Undo/Redo/Dirty/Save）。
- T34.6 completed：Undo/Redo + Dirty + Save + Version Integration。后端补齐 T34.2 Save API
  （`POST /midi/edit`）：`write_midi_editor_track`（替换目标轨 note 保留他轨/meta/PPQ）、
  `MidiEditorSaveRequest/Response`、创建新版本 kind=manual_midi_edit、base_version_id 校验
  409 VERSION_CONFLICT（errors.py 新增 code）。前端：`useMidiEditorDraft` 内置 per-track
  undo/redo（快照栈 80；recordBefore+commitEdit 保证一次拖拽=一次 undo）、dirty 深度比较、
  discard/rebase；`MidiEditor` 增加 Undo/Redo 按钮+快捷键（Ctrl+Z/Shift+Z/Y，输入框守卫）、
  Dirty 指示、Save/Discard（二次确认）、409 冲突弹窗、Save 失败保留 Draft、beforeunload（仅
  dirty）；`saveMidiEditorTrack` client；`onMidiSaved` 经 PianoRollPanel/WorkspaceDashboard →
  ProjectWorkspacePage `markAudioStale()` + refresh assets/versions。Save 后 reload document
  （canonical notes 替换 temp IDs、history 清空、dirty=false）。不自动 Render WAV；
  renderer/SoundFont/is_fallback 保持真实。测试：后端 7 passed + MIDI/version 回归 34 passed；
  前端 Vitest 89 passed（history/dirty/save 语义）；npm build 通过（136 modules）。
  T34.7 next（Preview/Transport/Loop）。
- T34.7 completed：MIDI Editor Preview / Transport / Playhead / Seek / Loop。严格复用 T34.0
  后端 scratch 路线：`POST /midi/preview` 接收当前 Editor Session 轨道快照，Current Track 清空
  其他轨 note，All Tracks 合并各轨 draft/saved；临时 MIDI/WAV 只写 OS temp，复用项目当前
  SoundFont/FluidSynth→fallback 选择，不写 output.wav/audio_metadata、不创建版本。前端新增
  `useMidiPlayback`（HTMLAudioElement allNotesOff + generation cleanup + RAF）、`midiPlayback` 纯函数
  （Draft selection/tick↔seconds/loop validation）、Play/Stop/Current-All、bar loop 输入、Timeline
  click-to-seek、Timeline/Roll playhead 与 loop overlay。Save/refreshKey/document change/unmount 前统一
  Stop；locked Track 仍可 Preview；播放中编辑不热更新，Stop→Play 使用最新 Draft。性能：NoteLayer
  与 dirty 深比较 memoize，Preview 无 per-note timer；500/1000/3000 notes smoke 通过。验证：后端
  Preview+Save 12 passed、MIDI/Version/Regenerate 扩展回归 49 passed；前端 Vitest 107 passed；
  npm build 通过（138 modules）；真实 Chromium
  E2E 1 passed（未保存 Bass Draft、Current/All、Stop、Seek、Loop、Lock、无 Save/Version/Render、
  Version/MIDI/WAV 状态不变）。
  2026-08-11 在 T34.9 semantic timeline 合入后再次复验：Seek smoke 改为点击 canonical bar row，避免
  Section marker 的专用定位语义干扰；真实页面 + Playwright 1 passed，Vitest 145、后端 56、build 141 modules。
- T34.8 completed：Advanced Selection & Batch Editing。当前轨 selection 升级为 `Set<string>`；支持
  单击替换、Ctrl/Cmd toggle、Shift 追加、Zoom/Scroll-safe Box Selection、Ctrl/Cmd+A、Esc；Batch
  Delete/Move/Velocity、内部 Copy/Paste、Duplicate 均接入现有 per-track Draft/History，一次批量操作
  只有一个 Undo step。Batch Move 使用 anchor 单次 Snap + 全组统一 tick/semitone delta 和 boundary
  clamp；Paste 对齐 snapped playhead、生成新 temp IDs、强制目标 channel，拒绝 drum↔pitched 不安全粘贴。
  Locked Track 允许 Select/Box/Copy/Zoom/Pan/Preview，阻止所有 Note mutation。100/500-note 性能路径
  使用 Set/Map 单次扫描。验证：Vitest 126 passed；build 139 modules；后端边界 40 passed；真实 Chromium
  Bass 全流程 1 passed（Preview 最新 Draft、Save 只请求一次、Version +1、WAV stale）。
  2026-08-12 跨阶段复验：真实页面 4-note Box/Move/Undo/Redo 与隔离 Playwright 全链路均通过；当前全量
  Vitest 145、后端边界 56、build 141 modules，T34.9/T34.7 后续变更未破坏 Selection/Draft/Save 边界。
- T34.9 completed：AI-aware Piano Roll。新增直接派生自真实 MusicSpec 的只读
  `MidiEditorMusicContext`；Scale root/in/out highlighting（兼容 c-major/d-natural-minor 等真实词汇）、
  一小节一个和弦的 tick overlay、1-based section markers 与非 4/4 映射、Scale/Chords/Sections session
  toggles。鼓轨使用 canonical GM 36–51 semantic rows（Kick/Snare/Hat/Crash/Ride 等）且保持原 pitch；
  canonical Bass role 增加 O(n log n) overlap guidance，只提示不修复。Project/Version/Restore/Regenerate
  context 隔离，不进入 Draft/History/Save/Version/WAV/renderer。验证：Vitest 145 passed；build 141 modules；
  后端边界 56 passed；真实 Chromium T34.9 A/B 语义隔离 1 passed + T34.8 全链路回归 1 passed。
  2026-08-12 增强 smoke：真实页面验证 C major / 4 Sections / 32 Chords 的 Zoom、playhead 与 marker seek
  canonical 对齐，以及 GM drum labels；隔离 E2E 验证 A(C major) → B(D minor)、Bass warning → Undo、
  toggle 零保存、单次 Save 后 Version +1 且 MusicSpec 不变。E2E editor-ready helper 不再在慢加载时自动
  Regenerate，避免覆盖已准备的 canonical MIDI 或引入额外版本副作用。
- T34.10 / T34-R completed：**MIDI Track Editor MVP 整体关闭，T34 OVERALL = COMPLETED**。
  - Stage 11/11 PASS，Critical Gates 16/16 PASS，open P0=0 / P1=0 / P2=2 / P3=2。
  - 修复并回归 dirty guard 全路径（含 Auto Optimize/Apply Mix）、Version index atomic write + same-base
    transaction、刷新后 WAV stale 持久语义；Manual Save 后旧 renderer/SoundFont metadata 不伪造，
    成功 re-render 才清 stale。
  - 前端 26 files / 149 tests，build 141 modules；后端全量 697 passed（1 warning）；隔离 Chromium
    T34 final 6 passed；可见真浏览器 direct refresh/Bass/Drum/Preview/Restore/A→B smoke PASS。
  - 真实 FluidSynth 2.4.7 + GeneralUser-GS.sf2 产品链 PASS：manual edit 后 WAV hash 改变，
    `renderer=fluidsynth` / `is_fallback=false` / stale=false。
  - 500/1000 notes usable；3000 notes degraded but usable（P2）。详细证据见
    [docs/T34_RETROSPECTIVE.md](docs/T34_RETROSPECTIVE.md)。
- T35 AI-assisted MIDI Editing started；T35.0 Architecture Scan completed（仅扫描/设计/Contract 冻结，
  未实现 T35.1+ 产品代码）。已冻结 Backend Planner + existing LLMProvider、music_core deterministic
  Transformer、Frontend T34 Draft Apply 的 Hybrid 边界；四种 Scope、draftRevision/editorSession/scopeRevision
  stale gate、11 个初始 operation、stateless Proposal、T34 scratch Preview、single-step Undo、existing Save/
  Version/WAV stale 与 bounded provenance 合同。设计详见
  [docs/AI_MIDI_EDIT_T35.md](docs/AI_MIDI_EDIT_T35.md)。Baseline 验证：前端 26 files / 149 passed，
  build 141 modules；后端 697 passed / 1 个既有 deprecation warning。T35.1 Context & Scope next。
- T35.1 Context & Scope completed：新增 `packages/music_core/midi_editing/` strict Scope domain
  （selected_notes/track/section/tick_range、extra forbid、半开 tick membership、canonical JSON +
  SHA-256 fingerprint）与 `services/api/schemas/ai_midi_edit.py` /
  `services/api/services/ai_midi_edit_context.py`（权威 Project/MusicSpec/MIDI context、scoped session
  Draft、128-note deterministic compaction、3000-note/64 KiB gates，无 LLM 调用）。前端新增
  `editor/ai/aiMidiEditTypes.ts` / `aiMidiEditScope.ts`，并在现有 Draft 增加
  editorSessionId + monotonic draftRevision，在 MidiEditor 建立 selected Track/Notes scopeRevision；
  未实现 route/Plan/Transformer/Proposal/UI/Apply。验证：T35.1 + T34 MIDI API 42 passed；前端
  27 files / 160 passed；build 142 modules；后端全量 715 passed / 1 个既有 deprecation warning。
- T35.2 MidiEditPlan completed：在 `packages/music_core/midi_editing/models.py` 实现唯一 canonical
  `MidiEditPlan` 与 11-way strict `type` discriminated operation union（ordered 1..8、extra forbid、
  静态范围/no-op/non-finite gates）；`plan_validator.py` 集中定义四种 Scope、pitched/drum applicability、
  PPQ 动态边界与稳定 domain error。Plan 完全不含 song/project/track/note/section/path/URL/route/code
  等定位或执行字段，任何未知/非法输入整 Plan fail closed。JSON Schema discriminator、required 与
  additionalProperties contract 已锁定；未接 LLM、未执行 Transform、未生成 Proposal、未新增 API/UI。
  新增 94 项 security/schema/context tests；T35.1+T35.2 相关回归 112 passed；后端全量
  809 passed / 1 个既有 deprecation warning。
- T35.3 Deterministic Transformer completed：新增 `packages/music_core/midi_editing/transformer.py`，
  实现全部 11 种 v1 operation 的独立纯 helper 与严格 ordered dispatcher；使用 exact Fraction +
  round-half-away-from-zero、SHA-256 seeded density（不触碰 global RNG）、chord/channel-aware legato、
  rational PPQ quantize，以及 T35.0 冻结的 pitch/velocity/time-window clamp warning。输入 Scope/Plan/Notes
  在 trust boundary 重验，每步执行 ID/channel/integer/range invariant gate；仅处理 resolved scoped notes，
  输入 immutable，失败 atomic，无新增 ID/Note。未接 LLM/API/Proposal/Diff/UI，未写 Project/MIDI/WAV/
  Version。新增 63 项专项测试，T35.0–T35.3 相关回归 175 passed；500/1000/3000-note smoke 约
  0.01/0.02/0.05s；后端全量 872 passed / 1 个既有 deprecation warning。T35.4 Proposal/Diff next。
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
- T34：3000+ notes 的 SVG viewport virtualization / Canvas 评估；多 worker 共享文件存储时引入
  OS file lock 或数据库 transaction。

## 当前测试与构建结果（2026-08-12 实测）

```text
后端：pytest -q → 872 passed，1 warning（LLM_PROVIDER=mock）
前端：npm test → 27 files / 160 passed
前端：npm run build → passed（tsc + Vite，142 modules）
T34 E2E：Playwright Chromium → 6 passed（final/context/performance/preview/selection/drum CRUD）
真实音频：FluidSynth 2.4.7 + GeneralUser-GS.sf2 → renderer=fluidsynth / is_fallback=false
```

> 说明：pytest warning 为 Starlette TestClient/httpx deprecation warning；不影响 T34 验收。
> 前端 package.json 无 lint script，因此未伪造 lint 结果。

## Next Recommended Tasks（推荐下一步）

1. T35.4 Proposal / Diff：基于 fixture Plan + Transformer result 实现精确 diff、no-op 与 Scope gate；
   不接真实 LLM/UI Apply。
2. P2 性能：若 3000+ notes 成为常态，增加真实 viewport virtualization 或评估 Canvas。
3. P2 部署：若启用多 worker/多实例共享文件存储，将 Version transaction 升级为 OS lock/数据库事务。
4. 生产级任务队列：Redis / Celery 替换进程内队列，支持多实例与任务恢复。
5. 音乐质量与音色：真实 SoundFont 渲染体验优化、弦乐分部细化。

## 最近一次状态更新时间

2026-08-12
