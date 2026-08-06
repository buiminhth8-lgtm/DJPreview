# Frontend Workspace Redesign

> T38 系列阶段文档。T38-A 完成前端结构审计与改版方案，不进行大规模重构。

## 1. Goal

当前前端首次打开页面时，只显示标题、说明、输入框与「生成 MusicSpec」按钮；
只有点击生成成功后才显示其余功能模块。目标是把所有核心功能模块**常驻显示**，
在无数据时展示 Empty State，在操作条件不足时按钮 disabled 并提示原因，并采用
**从上到下的瀑布流工作台布局**。

本阶段（T38-A）只做结构审计与方案规划，不重构 App.tsx、不改 hooks / API client /
CSS 主题、不改后端、不删除现有功能。

## 2. Current State Audit

### 2.1 Entry Points

| 文件 | 职责 | 结论 |
|---|---|---|
| `apps/web/src/main.tsx` | ReactDOM 挂载 `<App />` + 引入 `styles.css` | 极简，无需改动 |
| `apps/web/src/App.tsx` | 组合 `useSongProject` / `useStyles` / `useAudioAssets` / `useVersions` + 跨模块回调，渲染 `<WorkspaceLayout>` | **状态较重**：承载生成 / MIDI / WAV / 版本 / 混音 / 优化 / 重生成 / 参考 / 导入等全部编排回调 |

**App.tsx 是否过重**：是。它持有 4 个 hooks 实例 + `pianoRefreshKey` + `lastDiff` +
`styleStrength`，并串联约 12 个跨模块回调（`onGenerate` / `onRestore` / `onMixApplied` /
`onOptimized` / `onRegenerated` / `onImported` 等）。T38-C 应把瀑布流骨架下沉，
但 App.tsx 仍作为顶层组合层保留。

**App.tsx 是否直接渲染所有工作台模块**：不直接渲染。它只渲染 `<WorkspaceLayout>`，
具体面板由 `WorkspaceLayout` 根据 `hasSong` 条件渲染。

### 2.2 Workspace Components

`apps/web/src/components/workspace/`（实际文件，未编造）：

| 组件文件 | 组件 | 当前是否渲染 | 是否被条件隐藏 | 需要的 props |
|---|---|---|---|---|
| `WorkspaceLayout.tsx` | WorkspaceLayout | 总是 | 骨架 | songProject/audioAssets/versions/styles + 全部回调 |
| `WorkspaceHeader.tsx` | WorkspaceHeader | 总是 | 无 | songId/currentVersionId/hasMidi/hasAudio/error |
| `GeneratePanel.tsx` | GeneratePanel | 总是 | 无 | prompt/loading/style/validation/回调 |
| `GenerationDebugPanel.tsx` | GenerationDebugPanel | 总是 | 仅 idle+无日志时 return null | generation 状态/log/requestId/debug/warnings/error |
| `EditPanel.tsx` | EditPanel | 条件 | **有 song && spec** | value/loading/diff/回调 |
| `ProjectPanel.tsx` | ProjectPanel | 条件 | **有 song && spec** | songId/onImported/onError |
| `PlayerPanel.tsx` | PlayerPanel | 条件 | **有 song && spec** | songId/midiResult/audioResult/URL/回调 |
| `VersionPanel.tsx` | VersionPanel | 条件 | **有 song && spec** | versions/currentVersionId/loading/回调 |
| `MixerPanel.tsx` | MixerPanel | 条件 | **有 song && spec** | songId/refreshKey/onApplied/onError |
| `AnalysisPanel.tsx` | AnalysisPanel | 条件 | **有 song && spec** | songId/spec/refreshKey/onOptimized/onError |
| `ReferencePanel.tsx` | ReferencePanel | 条件 | **有 song && spec** | styleTemplateId/styleStrength/onGenerated/onError |
| `EvaluationPanel.tsx` | EvaluationPanel | 条件 | **有 song && spec** | onError |
| `SoundfontPanel.tsx` | SoundfontPanel | 嵌套于 PlayerPanel | 随 PlayerPanel 隐藏 | songId/onError |
| `RenderTasksPanel.tsx` | RenderTasksPanel | 嵌套于 PlayerPanel | 随 PlayerPanel 隐藏 | songId/onAssetsChanged/onError |
| `StatusMessage.tsx` | StatusMessage | 总是 | 无 error 时 return null | error |

复用自 `components/` 根的内部组件：`ArrangementInspector`（摘要/段落/轨道/PianoRoll/质量）、
`ProjectIOPanel`、`MixerPanel`(inner)、`ReferenceMidiPanel`、`EvaluationPanel`(inner)、
`StemExportPanel`、`AudioPlayer`、`TrackList`、`SectionTimeline`、`PianoRoll`、
`QualityReport`、`MusicSummary`、`TrackMixerStrip`、`StyleTemplatePanel`、`RegenerationPanel`。

### 2.3 Conditional Rendering Findings

**核心位置**：`apps/web/src/components/workspace/WorkspaceLayout.tsx`

```tsx
const hasSong = Boolean(songId && spec);
// 左列（生成列）
<GeneratePanel ... />                       // 常驻
<GenerationDebugPanel ... />                // 常驻（idle 时空渲染）
{hasSong && songId && spec && (<>           // ← 隐藏 EditPanel + ProjectPanel
  <EditPanel ... />
  <ProjectPanel ... />
</>)}
// 右列（播放列）
{hasSong && songId && spec && (<>           // ← 隐藏 PlayerPanel / VersionPanel / MixerPanel / AnalysisPanel
  <PlayerPanel ... />                        //   （其中内含 SoundfontPanel / RenderTasksPanel / StemExport）
  <VersionPanel ... />
  <MixerPanel ... />
  <AnalysisPanel ... />
</>)}
{hasSong && songId && spec && (<>           // ← 隐藏 Regeneration / Reference / Evaluation
  <RegenerationPanel ... />
  <ReferencePanel ... />
  <EvaluationPanel ... />
</>)}
```

**首次打开时被隐藏的模块**：

| 模块 | 隐藏条件 | 建议 |
|---|---|---|
| 播放与下载（PlayerPanel，含 Stems/SoundFont/异步任务） | 无 song && spec | **常驻**，Empty State |
| 混音器（MixerPanel） | 无 song && spec | **常驻**，Empty State |
| 版本管理（VersionPanel） | 无 song && spec | **常驻**，Empty State |
| 编曲检查（AnalysisPanel：摘要/段落/轨道/PianoRoll/质量） | 无 song && spec | **常驻**，Empty State |
| 自然语言修改（EditPanel） | 无 song && spec | **常驻**，Disabled |
| 工程导入导出（ProjectPanel） | 无 song && spec | **常驻**（导入始终可用） |
| 局部重生成（RegenerationPanel） | 无 song && spec | 常驻，Disabled |
| 参考 MIDI（ReferencePanel） | 无 song && spec | **常驻**（可先分析） |
| 批量评估（EvaluationPanel） | 无 song && spec | **常驻**（不依赖 song_id） |
| 顶部状态栏（WorkspaceHeader） | 仅 songId 时显示状态 chips | 常驻，无工程时显示提示 |

**不隐藏的模块**：GeneratePanel、GenerationDebugPanel、WorkspaceHeader（标题区）、StatusMessage。

### 2.4 Hooks and State Sources

`apps/web/src/hooks/`（实际文件）：

| Hook | 提供数据 | loading/error | 依赖组件 | 首次打开默认 |
|---|---|---|---|---|
| `useSongProject` | songId/musicSpec/prompt/editInstruction/validation + T35 generation 状态（status/log/requestId/debug/warnings/errorInfo） | loadingSpec/loadingEdit/error | GeneratePanel/GenerationDebugPanel/EditPanel/Header | 全空 / idle |
| `useAudioAssets` | assets/midiResult/audioResult/下载 URL | loadingMidi/loadingAudio/loadingAssets/error | PlayerPanel | null |
| `useVersions` | versions/currentVersionId/selectedVersionId/detail/diff | loadingVersions/restoringVersion/error | VersionPanel | null |
| `useMixer` | mix/tracks | loading/error | MixerPanel | null（`if (!songId) return null`）|
| `useQuality` | qualityReport/optimizeReport | loading/error | AnalysisPanel | null |
| `useEvaluation` | cases/report/runId | loading/error | EvaluationPanel | 空 |
| `useReferenceMidi` | analysis/result | loading/error | ReferencePanel | null |
| `useStyles` | style list / selectedStyleId | loading/error | GeneratePanel/ReferencePanel | 默认模板 |
| `useSoundfonts` | soundfonts/projectSoundfont | loading/error | SoundfontPanel | 空列表 |
| `useRenderTasks` | task/status/progress | polling | RenderTasksPanel | null |

**关键结论**：所有依赖 song_id 的 hooks（useMixer/useQuality/useRenderTasks/useSoundfonts/
useAudioAssets/useVersions）均有 `if (!songId) return null` 守卫，**不会在无工程时发起无效请求**。
这为“常驻渲染”提供了前提：面板常驻但内部 hooks 在无 song_id 时静默返回空。

### 2.5 API Layer

`apps/web/src/api/`（实际文件）：`client.ts`、`types.ts` + 领域文件
`songApi` / `versionApi` / `audioApi` / `mixApi` / `analysisApi` / `referenceApi` /
`evaluationApi` / `projectApi` / `styleApi` / `soundfontApi` / `taskApi` / `musicApi`(兼容 re-export)。

| API 文件 | 主要函数 | 后端 endpoint | 结构化错误 | request_id/warnings/debug |
|---|---|---|---|---|
| songApi | generateMusicSpec / getSong / editSong / regenerateSong | /songs/generate, /songs/{id}, /songs/{id}/edit, /songs/{id}/regenerate | ✅ | ✅（generate 响应含 request_id/warnings/debug）|
| audioApi | generateMidi / renderAudio / getAssets / exportStems / download* | /songs/{id}/midi/generate, /audio/render, /assets, /stems/export | ✅ | ⚠️（assets 无 debug，错误含 request_id）|
| versionApi | getVersions / getVersion / getVersionDiff / restoreVersion | /songs/{id}/versions* | ✅ | ⚠️ |
| mixApi | getMix / updateMix / applyMix | /songs/{id}/mix* | ✅ | ⚠️ |
| analysisApi | getPianoRoll / checkQuality / getQualityReport / optimizeArrangement | /songs/{id}/piano-roll, /quality/* | ✅ | ⚠️ |
| referenceApi | analyzeReferenceMidi / generateFromReference | /reference/analyze, /songs/generate-from-reference | ✅ | ⚠️ |
| evaluationApi | listEvalCases / runEvaluation | /evaluation/cases, /evaluation/run | ✅ | ⚠️ |
| projectApi | exportProjectUrl / getProjectExportUrl / importProject | /songs/{id}/project/export, /projects/import | ✅ | ⚠️ |
| styleApi | listStyles / getStyle | /styles* | ✅ | ⚠️ |
| soundfontApi | listSoundfonts / scanSoundfonts / get/setProjectSoundfont | /soundfonts*, /songs/{id}/soundfont | ✅ | ⚠️ |
| taskApi | startMidiRenderTask / startAudioRenderTask / startStemsExportTask / getTask / listSongTasks / cancelTask | /songs/{id}/tasks*, /tasks/{id} | ✅ | ⚠️ |
| client | apiFetch / apiDownloadBlob / ApiRequestError / parseApiError / resolveUrl | — | ✅（结构化 code/stage/requestId/provider）| ✅（读取 X-Request-ID）|

## 3. Target Layout（目标瀑布流顺序）

```
1. 顶部状态栏 / Provider / 当前工程          （WorkspaceHeader）
2. 生成控制台 + 当前工程概览                  （GeneratePanel）
3. 播放与下载                                （PlayerPanel：MIDI / WAV / 分轨 / 音源 / 异步任务）
4. MusicSpec 预览 / Warnings / Debug        （GenerationDebugPanel + MusicSummary 内嵌）
5. 曲式与和声                                （SectionTimeline 内嵌于 AnalysisPanel）
6. 轨道与乐器                                （TrackList 内嵌于 AnalysisPanel）
7. Piano Roll                               （PianoRoll 内嵌于 AnalysisPanel）
8. 混音器                                    （MixerPanel）
9. Stems / 分轨导出                          （StemExportPanel，常驻独立段）
10. 版本管理                                  （VersionPanel）
11. 自然语言修改                              （EditPanel）
12. SoundFont / 音源管理                      （SoundfontPanel，常驻独立段）
13. 工程导入导出                              （ProjectPanel）
14. 任务与调试日志                            （RenderTasksPanel + GenerationDebugPanel）
```

> 说明：当前许多子段（曲式和声 / 轨道 / PianoRoll / 质量）聚合在 `AnalysisPanel`
> 内部的 `ArrangementInspector` 中，T38-F 负责拆分常驻化；SoundFont / 分轨 / 异步任务
> 目前聚合在 `PlayerPanel` 的 `<details>` 内，T38-E / T38-H 拆出独立瀑布流段。

## 4. Persistent Section Model（常驻显示模型）

- **常驻段（Always visible）**：Generate Console、Playback & Download、MusicSpec/Warnings/Debug、
  Form & Harmony、Track & Instruments、Piano Roll、Mixer、Stems、Versions、Edit Song、
  SoundFont、Import/Export、Debug Logs。
- **实现方式**：`WorkspaceLayout` 去掉 `hasSong && songId && spec` 外层包裹，每个面板
  独立接收 `songId: string | null` / `spec: MusicSpec | null`，内部自行渲染 Empty State 或 Disabled。
- **请求安全**：依赖 hooks 已有 `if (!songId) return null` 守卫，常驻渲染不会触发无效请求。
- **嵌套折叠保留**：`<details>` 折叠保留给长内容（分轨/音源/异步任务/raw debug），
  但段本身常驻显示标题。

## 5. Empty State Plan

| 模块 | Empty State 文案 |
|---|---|
| 播放与下载 | 暂无可播放音频。生成 MIDI 后可渲染 WAV，渲染完成后可播放和下载。 |
| MusicSpec | 暂无 MusicSpec。输入音乐描述并点击生成，或导入 .aimusic.zip 工程。 |
| 曲式与和声 | 暂无曲式与和声。生成 MusicSpec 后将在这里显示段落、起止小节和和弦进行。 |
| 轨道与乐器 | 暂无轨道。生成 MusicSpec 后将在这里显示 melody、harmony、bass、drums 等编曲轨道。 |
| Piano Roll | 暂无 MIDI。生成 MIDI 后可查看音符分布。 |
| 混音器 | 暂无可混音轨道。生成 MusicSpec 后将显示轨道音量、声像、静音和独奏控制。 |
| Stems / 分轨 | 暂无分轨资产。生成 MIDI/WAV 后可将各轨道导出为独立 MIDI 与 WAV。 |
| 版本管理 | 暂无版本。生成 MusicSpec 后将自动初始化 v1 版本。 |
| 自然语言修改 | 暂无工程可修改。生成或导入工程后可输入修改指令。 |
| SoundFont | 未找到音源。将 .sf2 / .sf3 放入 data/soundfonts/ 后重新扫描（已有文案）。 |
| 工程导入导出 | 可以导入 .aimusic.zip 工程。生成或导入工程后可导出当前工程。 |
| 调试日志 | 暂无调试日志。点击生成后这里会显示请求状态、request_id 与错误阶段。 |
| 参考 MIDI | 可上传参考 MIDI 分析特征并生成新工程，不依赖当前工程。 |
| 批量评估 | 可运行内置评估用例，不依赖当前工程。 |

## 6. Disabled State Plan

| 操作 | disabled 条件 | 原因文案 |
|---|---|---|
| 生成 MusicSpec | prompt 为空 | 请输入音乐描述 |
| 生成 MIDI | 无 song_id / MusicSpec | 请先生成 MusicSpec |
| 渲染 WAV | 无 MIDI 资产 | 请先生成 MIDI |
| 下载 MIDI | 无 MIDI 资产 | 当前工程暂无 MIDI |
| 下载 WAV | 无 WAV 资产 | 当前工程暂无音频 |
| 导出工程 | 无 song_id | 请先生成或导入工程 |
| 应用自然语言修改 | 无 song_id 或修改文本为空 | 请先生成工程并输入修改指令 |
| 应用 SoundFont 到工程 | 无 song_id 或未选择音源 | 请先生成工程并选择音源 |
| 混音器保存/应用 | 无 song_id / 无 mix | 请先生成工程（无混音轨道） |
| 版本恢复 | 无 versions | 当前工程暂无历史版本 |
| Piano Roll 刷新 | 无 MIDI | 请先生成 MIDI |
| 异步渲染任务（MIDI/WAV/stems） | 无 song_id 或任务进行中 | 请先生成工程 / 任务渲染中 |

## 7. Data Dependency Matrix

| Section | Always visible | Required data | Empty state | Disabled actions | Current component | Future slice |
|---|---:|---|---|---|---|---|
| Generate Console | Yes | prompt/provider | N/A | Generate disabled when prompt empty | GeneratePanel | T38-D |
| Playback & Download | Yes | midi/wav assets | No audio yet | Download disabled without assets | PlayerPanel | T38-E |
| MusicSpec | Yes | musicSpec | No MusicSpec yet | N/A | AnalysisPanel→MusicSummary | T38-E |
| Form & Harmony | Yes | musicSpec.form/harmony | No form yet | N/A | AnalysisPanel→SectionTimeline | T38-F |
| Track & Instruments | Yes | musicSpec.tracks | No tracks yet | N/A | AnalysisPanel→TrackList | T38-F |
| Piano Roll | Yes | midi/pianoRoll | No MIDI yet | Refresh disabled without MIDI | AnalysisPanel→PianoRoll | T38-F |
| Mixer | Yes | tracks/mix | No tracks yet | Save disabled without project | MixerPanel | T38-G |
| Stems | Yes | midi/wav/stems | No stems yet | Export disabled without assets | StemExportPanel | T38-G |
| Versions | Yes | song_id/versions | No versions yet | Restore disabled without versions | VersionPanel | T38-G |
| Edit Song | Yes | song_id/edit text | No project yet | Apply disabled without project/text | EditPanel | T38-G |
| SoundFont | Yes | soundfonts/song_id | Can scan | Apply disabled without song | SoundfontPanel | T38-H |
| Import/Export | Yes | song_id/assets | Can import | Export disabled without project | ProjectPanel | T38-H |
| Debug Logs | Yes | request/debug state | No logs yet | Copy disabled without logs | GenerationDebugPanel | T38-H |
| Reference MIDI | Yes | none | Can upload | N/A | ReferencePanel | T38-G |
| Evaluation | Yes | none | Can run | N/A | EvaluationPanel | T38-G |

## 8. Implementation Slices

### T38-B：UI 基础组件与设计变量
- 目标：建立 EmptyState / DisabledButton / SectionCard 等基础组件与 CSS 变量，作为后续切片的公共基础。
- 修改范围：`apps/web/src/components/ui/`（若不存在则新建）、`styles.css` 变量。
- 风险点：新增组件命名与现有 `.panel`/`.muted-note` 样式冲突。
- 验收标准：基础组件可在任意面板复用；`npm run build` 通过。
- 建议 commit message：`feat(frontend): add ui primitives and design variables`

#### T38-B 已落地（完成）

已新增 UI primitives（`apps/web/src/components/ui/`，不依赖业务数据，均可独立复用）：

- `SectionCard.tsx` — 工作台模块统一卡片容器（title/description/eyebrow/badge/actions/compact/muted）
- `PanelHeader.tsx` — 模块头部（title/description/eyebrow/badge/actions），可被 SectionCard 复用
- `EmptyState.tsx` — 无数据占位（半透明内框 + 虚线边框 + 图标 + 可选 action）
- `StatusBadge.tsx` — 状态徽章（neutral/success/warning/danger/info/primary）
- `ActionButton.tsx` — 带 loading 与 disabledReason（title 提示）的按钮（primary/secondary/ghost/danger/success）
- `ButtonRow.tsx` — 按钮排列（left/right/between + wrap）
- `KeyValueGrid.tsx` — 键值网格（2/3/4 列，空值显示 fallback）
- `InlineNotice.tsx` — 内联提示（info/success/warning/danger）
- `LoadingState.tsx` — 加载占位（CSS spinner，无第三方库）
- `ErrorState.tsx` — API 错误展示（title/message/code/requestId/action）
- `index.ts` — barrel export 统一导出

新增设计变量与样式：

- `apps/web/src/styles/design-tokens.css` — `--workspace-*` 设计 token（背景/表面/文本/品牌色/
  状态色/圆角/间距/阴影），与现有 `styles.css` 的 `:root` 变量不冲突
- `apps/web/src/styles/workspace-ui.css` — 全部 `ui-*` 类名（section-card/panel-header/empty-state/
  status-badge/action-button/button-row/key-value-grid/inline-notice/loading-state/error-state + 768px 响应式）
- `main.tsx` 引入两个新 CSS 文件

本阶段未接入现有页面（方案 A），后续 T38-C 将基于这些组件实现瀑布流骨架。

### T38-C：重构 Workspace 瀑布流骨架
- 目标：把 `WorkspaceLayout` 从双列 grid 改为单列瀑布流（保留右侧分析聚合可选），
  所有段常驻渲染。
- 修改范围：`WorkspaceLayout.tsx`、`styles.css`（.workspace-grid → .workspace-flow）。
- 风险点：页面变长；需响应式与折叠策略；App.tsx 回调数量不变。
- 验收标准：首次打开显示所有段；生成前均为 Empty/Disabled；`npm run build` 通过。
- 建议 commit message：`refactor(frontend): render all sections persistently in flow layout`

#### T38-C 已落地（完成）

已新增工作台瀑布流骨架：

- `apps/web/src/components/workspace/WorkspaceDashboard.tsx` — 新的工作台总容器：
  首次打开页面时所有核心模块入口常驻显示；无 song/spec 时各模块显示 Empty State；
  有 song/spec 时接入现有真实面板（保留全部既有功能）；不直接发 API 请求。
- `apps/web/src/components/workspace/WorkspaceSectionPlaceholder.tsx` — 统一常驻占位卡片
  （内部复用 T38-B 的 SectionCard + EmptyState + StatusBadge）。
- `apps/web/src/components/workspace/ProjectOverviewPanel.tsx` — 当前工程轻量概览
  （纯 props，不发请求；有 musicSpec 显示标题/风格/BPM/调性/拍号/长度/段落数/轨道数/warnings 数；
  无 musicSpec 显示 Empty State）。
- `apps/web/src/components/workspace/WorkspaceHeader.tsx` — 改造为 AI Music Studio 头部：
  显示 Provider（前端暂不感知，标「当前环境 / 未知」）、Model（未知）、工程状态
  （未生成 / song_id / 版本 / MIDI / WAV）与状态 badges。
- `apps/web/src/styles/workspace-layout.css` — 瀑布流布局（1180px 居中、hero 双列、瀑布流单列、
  768px 全部单列）。
- `App.tsx` 改为渲染 `WorkspaceDashboard`（仅替换 JSX 布局，保留全部 hooks / handlers）。

瀑布流顺序：Header → 生成控制台 + 工程概览 → 播放与下载 → MusicSpec/Warnings/Debug →
编曲检查（曲式/轨道/Piano Roll/质量）→ 混音器 → Stems → 版本管理 → 自然语言修改 →
SoundFont → 工程导入导出 → 任务与调试日志 → 局部重生成 → 参考 MIDI → 批量评估。

当前为真实组件（有 song 时接入）：GeneratePanel / ProjectOverviewPanel / PlayerPanel /
GenerationDebugPanel / AnalysisPanel / MixerPanel / VersionPanel / EditPanel / ProjectPanel /
RenderTasksPanel / RegenerationPanel / ReferencePanel / EvaluationPanel。
当前为 Empty State 占位：Stems / SoundFont（有工程后仍在 PlayerPanel 内，独立段后续拆分）。

后续 T38-D 将基于这些组件继续拆分各段实现。

### T38-D：生成控制台与项目概览改造
- 目标：Generate Console + 项目概览（song_id/版本/资产 chips）常驻并完善 Empty/Disabled。
- 修改范围：`GeneratePanel.tsx`、`WorkspaceHeader.tsx`。
- 风险点：生成成功后的联动刷新（资产/版本）不能丢。
- 验收标准：无工程时 Generate 禁用并提示；生成后概览更新。
- 建议 commit message：`feat(frontend): persistent generate console and project overview`

#### T38-D 已落地（完成）

- 新增 `apps/web/src/components/workspace/GenerateConsole.tsx`：生成控制台
  - prompt 输入区（多行 textarea，placeholder 示例）
  - Provider / Model / response_format 状态徽章（前端暂不感知 provider/model，显示「未知」）
  - 按钮：生成 MusicSpec（真实）、生成 MIDI（真实，无 MusicSpec 时禁用）、渲染 WAV（真实，无 MIDI 时禁用）、生成完整歌曲（可选预留）
  - 每个按钮带 disabledReason（如「请输入音乐描述」「请先生成 MusicSpec」「请先生成 MIDI」）
  - 保留风格模板选择（StyleTemplatePanel，可选 props 接入）
  - 错误时 InlineNotice 显示「生成失败」摘要
- 升级 `apps/web/src/components/workspace/ProjectOverviewPanel.tsx`：工程概览
  - 无 MusicSpec：Empty State「尚未生成工程」
  - 有 MusicSpec：标题 / 风格 / BPM / 调性 / 拍号 / 长度 / 段落数 / 轨道数 / Warnings / song_id / 当前版本 / MIDI 状态 / WAV 状态 / 最近 request_id（KeyValueGrid + StatusBadge）
  - 安全读取 musicSpec 字段，缺失显示 —，不崩溃
- `WorkspaceDashboard` 首屏接入：`workspace-hero-grid` 左侧 `GenerateConsole`（1.35fr）、右侧 `ProjectOverviewPanel`（0.65fr），900px 以下单列
- CSS：`workspace-layout.css` 增加 `.generate-console` 系列（textarea / provider / status / actions）与 hero 列宽

后续 T38-E 将基于这些组件接入播放/下载/MusicSpec/Debug 段。

### T38-E：播放、下载、MusicSpec、Warnings、Debug 常驻化
- 目标：PlayerPanel / MusicSummary / GenerationDebugPanel 常驻；Stems/SoundFont/异步任务
  拆出独立段（或保留 details 折叠但标题常驻）。
- 修改范围：`PlayerPanel.tsx`、`AnalysisPanel.tsx`（拆分 MusicSummary）、`GenerationDebugPanel.tsx`。
- 风险点：MIDI/WAV 请求只在有 song_id 时发出（hooks 已守卫）。
- 验收标准：无资产时显示 Empty State，下载按钮 disabled。
- 建议 commit message：`feat(frontend): persistent playback/musicspec/debug sections`

### T38-F：曲式和声、轨道乐器、Piano Roll 常驻化
- 目标：从 `ArrangementInspector` 拆出 SectionTimeline / TrackList / PianoRoll 为独立段。
- 修改范围：`ArrangementInspector.tsx`、新增/调整 section 组件。
- 风险点：Piano Roll 无 MIDI 时不能请求 piano-roll endpoint（hooks 已守卫）。
- 验收标准：无 spec 时显示 Empty State；有 spec 后显示段落/轨道。
- 建议 commit message：`feat(frontend): persistent form/track/piano-roll sections`

### T38-G：混音器、Stems、版本管理、自然语言修改常驻化
- 目标：Mixer / StemExport / VersionPanel / EditPanel / Reference / Evaluation 常驻。
- 修改范围：对应 panel 组件 + hooks 空态支持。
- 风险点：混音器无 mix 时不能请求；版本恢复需 song_id。
- 验收标准：无工程时各操作 disabled 并提示原因。
- 建议 commit message：`feat(frontend): persistent mixer/stems/versions/edit sections`

### T38-H：SoundFont、工程导入导出、任务日志常驻化
- 目标：SoundfontPanel（可无工程扫描）、ProjectPanel（导入始终可用/导出需 song）、
  RenderTasksPanel、Debug Logs 常驻。
- 修改范围：对应 panel 组件。
- 风险点：导入/导出可用性区分；Debug 长文本限高。
- 验收标准：无工程时可扫描音源、可导入工程；导出 disabled。
- 建议 commit message：`feat(frontend): persistent soundfont/io/tasks/debug sections`

### T38-I：整体 UI 美化与响应式优化
- 目标：瀑布流响应式（窄屏单列）、折叠策略、Empty/Disabled 视觉统一。
- 修改范围：`styles.css`。
- 风险点：样式改动影响既有功能视觉，需回归。
- 验收标准：桌面/移动布局正确；`npm run build` 通过。
- 建议 commit message：`style(frontend): polish flow layout and responsive`

### T38-J：前端回归测试与文档同步
- 目标：Playwright E2E 覆盖常驻空态/禁用态；同步 README / PROJECT_STATUS。
- 修改范围：`apps/web/e2e/`、`README.md`、`docs/PROJECT_STATUS.md`。
- 风险点：E2E 需后端 mock 运行。
- 验收标准：关键链路回归通过；文档与实现一致。
- 建议 commit message：`test(frontend): e2e for persistent workspace + docs sync`

## 9. Risks and Mitigations

1. **App.tsx 状态过重**：直接大改可能破坏生成链路 → T38-C 只改布局骨架，App.tsx 保留为组合层。
2. **模块依赖 song_id**：常驻显示必须支持 null → 所有相关 hooks 已有 `if (!songId) return null` 守卫。
3. **hooks 无工程时发无效请求**：已确认 useMixer/useQuality/useRenderTasks/useSoundfonts/
   useAudioAssets/useVersions 均有 songId 守卫；T38 需保持。
4. **导入导出可用性区分**：导入始终可用，导出需 song_id → ProjectPanel 分两个按钮状态。
5. **SoundFont 扫描可无工程，应用需 song**：扫描/列表不依赖 song；选择音源时禁用。
6. **Piano Roll 依赖 MIDI**：无 MIDI 时不请求 piano-roll endpoint（hooks 守卫）。
7. **混音器依赖 tracks/mix**：无工程时不请求 mix endpoint（hooks 守卫）。
8. **Debug 面板长文本**：GenerationDebugPanel 已限制 raw preview ≤2000 字符；T38-H 再限高。
9. **瀑布流常驻后页面更长**：需要响应式与折叠策略（details 折叠保留）。
10. **不应为常驻触发大量无效 API 请求**：保持 hooks 的 songId 守卫，避免首屏请求风暴。

## 10. Acceptance Criteria（T38-A 完成）

- [x] 已创建/更新 `docs/FRONTEND_WORKSPACE_REDESIGN.md`。
- [x] 文档真实反映当前前端代码结构（入口/组件/hooks/API/条件渲染）。
- [x] 文档列出当前 workspace 组件、hooks 与 API 数据来源。
- [x] 文档列出关键条件渲染问题与目标瀑布流布局顺序。
- [x] 文档明确每个模块是否常驻显示、Empty State、Disabled State。
- [x] 文档包含数据依赖矩阵与 T38-B ~ T38-J 后续切片。
- [x] 本阶段未大规模修改前端业务逻辑；`npm run build` 通过。
