# T33：前端页面路由拆分与工程工作台重构——现状扫描与迁移计划

> 阶段：T33.0（仅扫描与规划，不做实际重构）
> 目标架构：`/create`（创作）、`/projects`（工程库）、`/projects/:songId`（工程工作台）
> 本文档基于 2026-08-07 的代码实际扫描结果编写。

> 更新（T33.6 Completed）：已完成工作台功能模块拆分与共享组件抽取，
> `components/workspace`、`components/legacy` 与顶层旧组件已删除，页面直接组合 features。

> 更新（T33.7 Completed）：SoundFont / Renderer 状态前端整合完成。
> 核心原则：`selected SoundFont ≠ rendered SoundFont`、`FluidSynth available ≠ 当前 WAV 使用 FluidSynth`、
> `fallback 状态以后端 audio metadata（is_fallback）为准`。

> 更新（T33.8 Completed）：工程导入导出 / 删除 / 二次确认流程整合完成。

## 工程级操作边界（T33.8）

- **导入**：`/projects` 的 `ImportProjectButton` 与 Workspace 的 `ProjectImportExportPanel`
  均走 `projectApi.importProject(file)`；上传中禁用重复选择、失败保留页面并显示 backend message；
  成功后使用后端真实 songId 跳转 `/projects/:songId`（不从文件名推导）。
- **导出**：`features/export/ExportMenu.tsx` 统一入口（导出工程 / MIDI / WAV / Stems），
  无对应资产时禁用；`features/export/downloadActions.ts` 统一 Blob 下载
  （MIDI→midiApi、WAV→audioApi、Stems→downloadStems、工程→projectApi），文件名优先后端
  Content-Disposition，否则 `{安全化标题}.ext`。
- **删除**：`/projects`（ProjectCard）与 `/projects/:songId`（工程导入导出面板）共用
  `DeleteProjectDialog` 二次确认；删除中禁用重复提交；失败保持 Dialog 并显示错误。
- **删除后行为**：Workspace 删除成功 → 清理工作区状态（assets/versions/project）→
  `navigate("/projects", { replace: true })`；Library 删除成功 → 从本地列表移除。
- **Blob 下载**：统一 `shared/utils/download.ts` 的 `downloadBlob`
  （createObjectURL → click → revokeObjectURL），无泄漏。

## SoundFont / Renderer 状态模型（T33.7）

- **环境能力（A）**：`useSoundfonts` 的 diagnostics（FluidSynth 可用性 / 扫描结果）只回答“能不能”，
  不参与当前 WAV 状态判断。
- **工程配置（B）**：`projectSoundfont`（selected SoundFont）回答“下一次渲染准备用什么”。
- **当前 WAV 实际渲染（C）**：`AudioRenderMetadata`（renderer / is_fallback / fallback_reason /
  soundfont_id / soundfont_name）回答“正在试听的 WAV 实际用了什么”，以后端返回为准。
- **WAV stale（D）**：`useAudioAssets.audioNeedsRender` + `markAudioStale()`；仅在会话内标记
  “需要重新渲染”，不伪造后端 metadata。SoundFont 选择成功、MIDI 重新生成后触发；渲染成功后清除。
- **RendererStatusCard**：fallback 唯一判断依据为 `metadata.isFallback === true`；
  无 WAV 显示“尚未渲染/暂无音频”，不显示 fallback。

## 模块地图（T33.6 最终）

```text
ProjectWorkspacePage
│
├─ features/workspace    （布局 / 头部 / 曲式轨道概览 / MusicSpec 检查 / 生成控制台 / 编辑 / 重生成 / 参考）
├─ features/midi         （MIDI 元数据 / 生成 / 下载 / Piano Roll / 曲式和声 / 轨道乐器）
├─ features/audio        （WAV 预览 / 渲染按钮 / RendererStatus / 混音器 / Stems / 播放下载）
├─ features/soundfonts   （音源列表 / 选择 / 扫描 / 项目绑定）
├─ features/versions     （版本列表 / 详情 / diff / restore）
├─ features/tasks        （异步渲染任务列表 / 状态 / 进度）
├─ features/quality      （质量报告 / 自动优化 / 批量评估）
└─ features/export       （工程导入导出）
```

### Feature Ownership

- `features/workspace/`：workspace layout / header / project overview / MusicSpec inspector / 轨道概览 /
  workspace tab state；不承载 MIDI/WAV/SoundFont/Version/Task API。
- `features/midi/`：MIDI 元数据、生成、下载、Piano Roll、track note 可视化。
- `features/audio/`：WAV 元数据、播放、渲染、renderer metadata、fallback 状态、下载、混音、Stems。
- `features/soundfonts/`：SoundFont 列表、选择、扫描、项目绑定（诊断为全局 `useSoundfonts` 单一来源）。
- `features/versions/`：版本列表、当前版本、restore、diff、metadata。
- `features/tasks/`：渲染任务列表、轮询、进度、状态。
- `features/quality/`：quality score、warnings、errors、report、自动优化、评估。
- `features/export/`：工程导入导出入口（下载协调；API 仍属 projectApi）。
- `shared/components/`：真正跨业务通用的 primitive（JsonPreview；ui primitives 暂留 `components/ui`）。

### 跨 Feature 刷新策略（T33.6）

```text
操作                    刷新
MIDI regenerated       → MIDI / Piano Roll / Audio stale（回调由 ProjectWorkspacePage 协调）
Audio rendered         → Audio / Project summary / Tasks
SoundFont changed      → SoundFont / Audio stale
Version restored       → Project / MIDI / Audio / Versions / Quality
Natural language edit  → Project / Versions / MIDI / Audio（按实际结果）/ Quality
```

跨 feature 通信一律通过 `ProjectWorkspacePage` 的 props / callbacks 协调，不引入 Event Bus、
不新增全局 store；feature 之间不互相 import。

---

## 1. 当前前端总体结构

### 1.1 目录结构（实际）

```text
apps/web/src/
├─ main.tsx                  # ReactDOM 挂载 + 全部样式导入
├─ App.tsx                   # 顶层组合：所有状态与回调，渲染 WorkspaceDashboard
├─ vite-env.d.ts
├─ styles/
│  ├─ styles.css             # 全局基础样式（旧）
│  ├─ design-tokens.css      # 设计变量（T38-B）
│  ├─ workspace-ui.css       # UI primitives 样式（T38-B）
│  ├─ workspace-layout.css   # 瀑布流/Header/断点（T38-C/I）
│  ├─ workspace-results.css  # 播放/调试/质量样式（T38-E）
│  ├─ workspace-structure.css# 曲式/轨道/PianoRoll 样式（T38-F）
│  ├─ workspace-editing.css  # 混音/编辑/版本样式（T38-G）
│  ├─ workspace-utilities.css# SoundFont/导入导出样式（T38-H）
│  └─ workspace-responsive.css# 响应式/溢出（T38-I）
├─ api/
│  ├─ client.ts              # fetch client + ApiRequestError + requestId 解析
│  ├─ types.ts               # 全部 API 类型（592 行，单一文件）
│  ├─ index.ts               # 统一导出
│  ├─ songApi.ts             # generate/get/edit/regenerate
│  ├─ audioApi.ts            # MIDI/WAV/assets/stems（11 个函数）
│  ├─ versionApi.ts          # 版本列表/详情/diff/恢复
│  ├─ mixApi.ts              # 混音
│  ├─ soundfontApi.ts        # 音源列表/扫描/诊断/项目音源
│  ├─ taskApi.ts             # 异步渲染任务
│  ├─ analysisApi.ts         # 分析
│  ├─ referenceApi.ts        # 参考 MIDI
│  ├─ evaluationApi.ts       # 评估
│  ├─ styleApi.ts            # 风格模板
│  ├─ projectApi.ts          # 导入导出
│  └─ musicApi.ts            # 仅 re-export（遗留空壳，历史命名）
├─ hooks/
│  ├─ index.ts               # 统一导出
│  ├─ useSongProject.ts      # 核心：songId/spec/prompt/生成/编辑/调试
│  ├─ useAudioAssets.ts      # MIDI/WAV/assets 状态
│  ├─ useVersions.ts         # 版本
│  ├─ useMixer.ts            # 混音
│  ├─ useQuality.ts          # 质量
│  ├─ useEvaluation.ts       # 评估
│  ├─ useReferenceMidi.ts    # 参考
│  ├─ useStyles.ts           # 风格
│  ├─ useSoundfonts.ts       # 音源（含 diagnostics）
│  └─ useRenderTasks.ts      # 任务轮询
├─ components/
│  ├─ ui/                    # T38-B primitives（11 个，真正通用）
│  ├─ workspace/             # 33 个组件：T38-D~H 常驻面板 + 旧面板
│  └─ (顶层 16 个组件)       # 旧一代组件（部分被 workspace 引用）
└─ pages/ features/ shared/ app/   # 不存在
```

### 1.2 当前结构的主要问题（基于实际代码）

| # | 问题 | 证据 |
|---|---|---|
| 1 | **页面职责混合**：单页应用把「创作」「工程库」「工作台」全部叠在一个页面 | App.tsx 只渲染 `WorkspaceDashboard`，无路由 |
| 2 | **生成流程与工程编辑流程强耦合** | `useSongProject` 同时持有 prompt/songId/musicSpec/editInstruction/生成调试状态 |
| 3 | **App.tsx 承担过多状态与回调编排** | App.tsx 有 11 个 handler + 3 个本地 state，全部 props 下传 WorkspaceDashboard |
| 4 | **两套工作台并存**：新（WorkspaceDashboard，T38 系列）与旧（WorkspaceLayout + GeneratePanel/PlayerPanel/EditPanel/AnalysisPanel 等） | WorkspaceLayout 及其子组件只在自身之间引用，是死代码路径 |
| 5 | **组件集中在 workspace/** | 33 个 workspace 组件 + 16 个顶层旧组件，无 feature 分层 |
| 6 | **路由边界不清晰**：无 React Router，刷新后丢失上下文 | main.tsx 无 Router；工程状态在内存 hooks |
| 7 | **工程库/生成页/工作台概念混杂**：无工程列表页面、无独立创作页 | 工程列表仅存在于 WorkspaceDashboard 的 ProjectOverview + 导入面板局部展示 |
| 8 | **类型集中在单一 types.ts** | 592 行所有 API 类型在一个文件，无领域分组 |
| 9 | **样式按阶段切分而非按功能** | 8 个 workspace-*.css 按 T38 阶段命名 |
| 10 | **API 双命名遗留**：musicApi.ts 是空壳 re-export | `export * from "./index"`，历史文件未清理 |

---

## 2. 当前组件清单

### 2.1 workspace/ 组件（T38 系列，当前活跃）

| 当前文件 | 当前职责 | 建议目标位置 | 建议归属页面 | 迁移优先级 | 备注 |
|---|---|---|---|---|---|
| WorkspaceDashboard.tsx | 瀑布流总容器：组合全部常驻面板 | pages/ProjectWorkspacePage.tsx 内部组合 | /projects/:songId | P0 | 重构后拆为页面组合层 |
| WorkspaceHeader.tsx | 标题/Provider/badges | features/workspace/WorkspaceHeader.tsx | /projects/:songId | P0 | |
| GenerateConsole.tsx | prompt 输入/生成按钮/状态 | features/generation/PromptGeneratePanel.tsx | /create | P0 | 核心创作入口 |
| ProjectOverviewPanel.tsx | 工程摘要（含 renderer 信息） | features/projects/ProjectOverviewCard.tsx | /projects/:songId | P0 | |
| PlaybackDownloadPanel.tsx | 播放/下载 MIDI/WAV + RendererStatusCard | features/audio/AudioPreviewPanel.tsx | /projects/:songId | P0 | 并入 AudioPreviewPanel |
| MusicSpecPanel.tsx | MusicSpec 摘要/JSON | features/workspace/MusicSpecInspector.tsx | /projects/:songId | P0 | |
| WarningsPanel.tsx | 校验警告 | features/workspace/WarningsPanel.tsx | /projects/:songId | P1 | |
| GenerationDebugPanel.tsx | 生成调试日志 | features/generation/GenerationDebugPanel.tsx | /projects/:songId | P1 | |
| FormHarmonyPanel.tsx | 曲式与和声 | features/midi/FormHarmonyPanel.tsx | /projects/:songId | P0 | |
| TrackInstrumentPanel.tsx | 轨道与乐器 | features/midi/TrackListPanel.tsx | /projects/:songId | P0 | |
| PianoRollPanel.tsx | Piano Roll 容器 | features/midi/PianoRollPanel.tsx | /projects/:songId | P0 | |
| MixerPanel.tsx | 混音器 | features/audio/MixerPanel.tsx | /projects/:songId | P1 | |
| StemsPanel.tsx | Stems 导出 | features/export/StemsPanel.tsx | /projects/:songId | P1 | |
| VersionPanel.tsx | 版本管理 | features/versions/VersionPanel.tsx | /projects/:songId | P0 | |
| EditSongPanel.tsx | 自然语言修改 | features/workspace/NaturalLanguageEditPanel.tsx | /projects/:songId | P0 | |
| SoundfontPanel.tsx | 音源管理（含 FluidSynth 状态） | features/soundfonts/SoundfontPanel.tsx | /projects/:songId | P0 | |
| ProjectImportExportPanel.tsx | 导入导出 | features/export/ProjectImportExportPanel.tsx | /projects/:songId + /projects | P0 | 导出在工作台，导入也在工程库 |
| RenderTasksPanel.tsx | 异步任务列表 | features/tasks/RenderTasksPanel.tsx | /projects/:songId | P0 | |
| RendererStatusCard.tsx | 渲染器/音质状态 | features/audio/RendererStatusCard.tsx | /projects/:songId | P0 | T39 |
| JsonPreview.tsx | JSON 预览 | shared/components/JsonPreview.tsx | 通用 | P2 | |
| SectionTimeline.tsx | 段落时间线 | features/midi/SectionTimeline.tsx | /projects/:songId | P1 | |
| HarmonyProgressionView.tsx | 和声进行视图 | features/midi/HarmonyProgressionView.tsx | /projects/:songId | P2 | |
| StatusMessage.tsx | 错误/状态提示 | shared/components/StatusMessage.tsx | 通用 | P2 | |
| WorkspaceSectionPlaceholder.tsx | 占位 | shared/components/WorkspaceSectionPlaceholder.tsx | 通用 | P2 | |
| GeneratePanel.tsx | 旧生成面板（死代码） | 暂不迁移 | - | Keep | WorkspaceLayout 独有，建议删除 |
| PlayerPanel.tsx | 旧播放面板（死代码，含旧音频组件） | 暂不迁移 | - | Keep | WorkspaceLayout 独有，建议删除 |
| EditPanel.tsx | 旧编辑面板（死代码） | 暂不迁移 | - | Keep | WorkspaceLayout 独有 |
| VersionPanel（旧）→ EditPanel 内旧版 | 旧版本面板 | 暂不迁移 | - | Keep | 已由新版 VersionPanel 取代 |
| AnalysisPanel.tsx | 旧分析面板（死代码） | 暂不迁移 | - | Keep | WorkspaceLayout 独有 |
| ProjectPanel.tsx | 旧工程面板（死代码） | 暂不迁移 | - | Keep | 已由 ProjectOverview + ImportExport 取代 |
| ReferencePanel.tsx | 参考 MIDI | features/midi/ReferencePanel.tsx | /projects/:songId | P2 | |
| EvaluationPanel.tsx | 批量评估 | features/quality/EvaluationPanel.tsx | /projects/:songId | P2 | |

### 2.2 components/ 顶层旧组件（16 个）

| 当前文件 | 当前职责 | 建议目标位置 | 建议归属页面 | 迁移优先级 | 备注 |
|---|---|---|---|---|---|
| AudioPlayer.tsx | audio 播放器 | features/audio/AudioPlayer.tsx | /projects/:songId | P1 | |
| PianoRoll.tsx | Piano Roll 渲染器 | features/midi/PianoRollViewer.tsx | /projects/:songId | P0 | |
| TrackList.tsx | 轨道列表 | features/midi/TrackListPanel.tsx | /projects/:songId | P1 | |
| TrackMixerStrip.tsx | 单轨混音条 | features/audio/TrackMixerStrip.tsx | /projects/:songId | P1 | |
| SectionTimeline.tsx（顶层） | 段落时间线 | features/midi/SectionTimeline.tsx | /projects/:songId | P2 | 与 workspace 版重复 |
| MusicSummary.tsx | MusicSpec 摘要 | features/workspace/MusicSpecInspector.tsx | /projects/:songId | P2 | |
| ArrangementInspector.tsx | 编曲检查 | features/midi/ArrangementInspector.tsx | /projects/:songId | P2 | |
| MixerPanel.tsx（顶层） | 混音（旧版） | features/audio/MixerPanel.tsx | /projects/:songId | P2 | 与 workspace 版重复 |
| QualityReport.tsx | 质量报告 | features/quality/QualityReportPanel.tsx | /projects/:songId | P1 | |
| EvaluationPanel.tsx（顶层） | 评估 | features/quality/EvaluationPanel.tsx | /projects/:songId | P2 | |
| ReferenceMidiPanel.tsx | 参考 MIDI | features/midi/ReferencePanel.tsx | /projects/:songId | P2 | |
| RegenerationPanel.tsx | 局部重生成 | features/generation/RegenerationPanel.tsx | /projects/:songId | P1 | |
| StyleTemplatePanel.tsx | 风格模板选择 | features/generation/StyleTemplateSelector.tsx | /create | P0 | 创作页核心 |
| StemExportPanel.tsx | Stems 导出 | features/export/StemsPanel.tsx | /projects/:songId | P2 | |
| ProjectIOPanel.tsx | 导入导出（旧） | features/export/ProjectImportExportPanel.tsx | /projects | P2 | |
| ProjectPanel.tsx（旧） | 旧工程面板 | 暂不迁移 | - | Keep | 死代码 |

### 2.3 ui/ primitives（11 个，真正通用）

| 当前文件 | 建议目标位置 | 迁移优先级 |
|---|---|---|
| ActionButton.tsx / ButtonRow.tsx / EmptyState.tsx / ErrorState.tsx / InlineNotice.tsx / KeyValueGrid.tsx / LoadingState.tsx / PanelHeader.tsx / SectionCard.tsx / StatusBadge.tsx | shared/components/ui/ | P0（直接搬） |

---

## 3. 当前 hooks 清单

| 当前 hook | 当前职责 | 使用位置 | 建议目标位置 | 是否需要拆分 | 备注 |
|---|---|---|---|---|---|
| useSongProject | songId/spec/prompt/editInstruction/生成调试/error | App.tsx | features/projects/useProject(songId) + features/generation/useGenerateSong() | **是，拆成两个** | 生成状态与工程状态耦合（见 §5） |
| useAudioAssets | MIDI/WAV/assets/下载 URL | App.tsx | features/audio/useAudioPreview(songId) + features/midi/useMidiData(songId) | 建议拆分 | 播放/下载与 MIDI 生成可分离 |
| useVersions | 版本列表/详情/diff/恢复 | App.tsx | features/versions/useVersions(songId) | 否 | 已按 songId 参数化，改名保留 |
| useMixer | 混音读取/更新/应用 | App.tsx → 工作台 | features/audio/useMixer(songId) | 否 | |
| useQuality | 质量/优化 | 工作台 | features/quality/useQualityReport(songId) | 否 | |
| useEvaluation | 评估用例/批量评估 | 工作台 | features/quality/useEvaluation(songId) | 否 | |
| useReferenceMidi | 参考 MIDI 分析/生成 | 工作台 | features/midi/useReferenceMidi(songId) | 否 | |
| useStyles | 风格模板列表/选中 | App.tsx | features/generation/useStyles() | 否 | |
| useSoundfonts | 音源列表/扫描/诊断/项目音源 | SoundfontPanel | features/soundfonts/useSoundfonts(songId) | 否 | 已含 T39 diagnostics |
| useRenderTasks | 异步任务启动/轮询 | 工作台 | features/tasks/useRenderTasks(songId) | 否 | |

### 目标 hooks 命名映射

| 目标 hook | 来源 | 动作 |
|---|---|---|
| useGenerateSong() | useSongProject 的 generate/prompt/样式部分 | 从 useSongProject 拆分 |
| useProjects() | 无（需新增） | 新增：工程列表/搜索/删除 API 封装 |
| useProject(songId) | useSongProject 的 loadSong/musicSpec 部分 | 从 useSongProject 拆分 |
| useProjectWorkspace(songId) | App.tsx 的编排逻辑 | 新增组合层（可组合上述 hooks） |
| useSoundfonts(songId) | 已存在 | 复用 |
| useRenderTasks(songId) | 已存在 | 复用 |
| useVersions(songId) | 已存在 | 复用（改名可选） |
| useAudioPreview(songId) | useAudioAssets 的播放/下载部分 | 拆分 |
| useMidiData(songId) | useAudioAssets 的 MIDI 生成 + PianoRoll 数据 | 拆分/新增 |
| useQualityReport(songId) | 已存在 useQuality | 复用 |

---

## 4. 当前 API 调用清单

| 当前 API 文件/函数 | 后端接口（前缀 /api/v1） | 当前使用位置 | 建议归属 feature | 是否需要统一封装 | 备注 |
|---|---|---|---|---|---|
| songApi.generateMusicSpec | POST /songs/generate | useSongProject | features/generation | 否 | |
| songApi.getSong | GET /songs/{id} | useSongProject | features/projects | 否 | |
| songApi.editSong | POST /songs/{id}/edit | useSongProject | features/workspace | 否 | |
| songApi.regenerateSong | POST /songs/{id}/regenerate | RegenerationPanel | features/generation | 否 | |
| audioApi.*（11 函数） | MIDI/WAV/assets/stems/download | useAudioAssets / 面板 | features/audio + features/midi | 否 | 建议按 audio/midi 分组 |
| versionApi.* | GET/POST /versions | useVersions | features/versions | 否 | |
| mixApi.* | GET/PUT /mix | useMixer | features/audio | 否 | |
| soundfontApi.*（5 函数） | /soundfonts + /songs/{id}/soundfont + diagnostics | useSoundfonts | features/soundfonts | 否 | 含 T39 diagnostics |
| taskApi.*（6 函数） | /tasks + /songs/{id}/tasks | useRenderTasks | features/tasks | 否 | |
| analysisApi.* | 分析接口 | 工作台 | features/midi | 否 | |
| referenceApi.* | 参考 MIDI | useReferenceMidi | features/midi | 否 | |
| evaluationApi.* | 评估 | useEvaluation | features/quality | 否 | |
| styleApi.* | 风格模板 | useStyles | features/generation | 否 | |
| projectApi.* | 导入导出 | ProjectImportExportPanel | features/export + features/projects | 否 | 工程列表接口缺失 |

### API 层现状结论

1. **组件内直接 fetch**：未发现（全部经 api/ 层）✓
2. **重复封装**：`musicApi.ts` 是空壳 re-export（历史命名残留）；`api/index.ts` 与 `hooks/index.ts` 有双导出，无重复逻辑
3. **错误处理**：统一（`client.ts` 的 `ApiRequestError` + `hooks/error.ts` 的 `getErrorMessage`）✓
4. **返回类型**：基本明确；`types.ts` 592 行单文件，建议按 feature 拆分
5. **命名一致性**：`songApi`（新）vs `musicApi`（旧空壳）并存；后端概念 song/project 混用（`getSong`/`loadSong` 但 UI 叫「工程」）
6. **缺失**：工程列表/搜索/删除 API（/projects 页面需要新增前端封装，后端接口视 T33.2 决定）

---

## 5. 当前页面状态清单

| 状态 | 当前所在位置 | 当前问题 | 建议迁移到 | 备注 |
|---|---|---|---|---|
| prompt 输入 | useSongProject.prompt | 生成页状态与工作台状态同 hook | features/generation/useGenerateSong() | 生成后应清空或保留会话级 |
| styleStrength | App.tsx 本地 state | 顶级组件承担 | features/generation/useGenerateSong() | |
| songId | useSongProject.songId | **全局漂移**：刷新丢失、无 URL 绑定 | URL（/projects/:songId） | 核心迁移点 |
| musicSpec | useSongProject.musicSpec | 切换工程靠手动 setMusicSpec | features/projects/useProject(songId) | |
| MIDI 状态 | useAudioAssets（midiResult/midiUrl） | 与 assets 混合 | features/midi/useMidiData(songId) | |
| WAV/audio 状态 | useAudioAssets（audioResult/streamUrl） | 与 MIDI 混合 | features/audio/useAudioPreview(songId) | |
| SoundFont 状态 | useSoundfonts | 独立，健康 | features/soundfonts/useSoundfonts(songId) | |
| 版本状态 | useVersions | 独立，健康 | features/versions/useVersions(songId) | |
| 任务状态 | useRenderTasks | 独立，健康 | features/tasks/useRenderTasks(songId) | |
| 生成调试状态 | useSongProject（T35 字段） | 生成专用却住在工程 hook | features/generation/useGenerateSong() | |
| error/loading | 各 hook 各自持有 | 重复但可接受 | 各 feature hook 内 | 无需全局 |
| pianoRefreshKey | App.tsx 本地 state | 手动刷新 PianoRoll 的 hack | 移除或改由 songId 派生 | T33.6 |
| lastDiff | App.tsx 本地 state | 编辑 diff 展示 | features/workspace 内 | |

### 关键判断

- **prompt 状态与当前工程状态耦合**：是（useSongProject 同时持有两者）——需拆分
- **songId 状态全局漂移**：是（内存 state，无 URL 绑定，刷新即丢）
- **切换工程后旧数据残留**：是（App.tsx 的 loadProject 手动 reset 三个 hook，易漏）
- **刷新后无法恢复工程上下文**：是（无路由、无持久化）
- **生成页状态污染工作台状态**：是（生成成功后 songId 直接成为工作台上下文，无明确「进入工作台」动作）

---

## 6. 新架构迁移目标

```text
apps/web/src/
├─ app/
│  ├─ App.tsx            # 路由 + 全局 provider
│  ├─ router.tsx         # createBrowserRouter / Routes 定义
│  └─ layout/
│     └─ AppLayout.tsx   # 公共导航壳（Header 链接：创作 / 工程库）
│
├─ pages/
│  ├─ CreatePage.tsx          # 组合生成 feature
│  ├─ ProjectLibraryPage.tsx  # 工程库 + 搜索 + 导入 + 删除
│  └─ ProjectWorkspacePage.tsx# 以 songId 为核心的工作台
│
├─ features/
│  ├─ generation/    # PromptGeneratePanel / StyleTemplateSelector / GenerateConsole / Debug
│  ├─ projects/      # useProject(songId) / useProjects() / 概览卡
│  ├─ workspace/     # 工作台编排 useProjectWorkspace + 通用面板
│  ├─ midi/          # PianoRoll / TrackList / FormHarmony / Reference
│  ├─ audio/         # AudioPreview / Mixer / RendererStatusCard
│  ├─ soundfonts/    # SoundfontPanel / useSoundfonts
│  ├─ versions/      # VersionPanel / useVersions
│  ├─ tasks/         # RenderTasksPanel / useRenderTasks
│  ├─ quality/       # QualityReport / Evaluation
│  └─ export/        # ImportExport / Stems
│
├─ shared/
│  ├─ components/    # ui/ primitives + JsonPreview + StatusMessage 等
│  ├─ hooks/         # 通用 hook（error 等）
│  ├─ types/         # 按 feature 拆分的类型
│  ├─ utils/         # format/helpers
│  └─ constants/     # 常量
│
└─ api/
   ├─ httpClient.ts  # fetch client + ApiRequestError（现 client.ts）
   └─ errors.ts      # 错误解析（现 hooks/error.ts 可上移）
```

原则：
- **pages 只组合页面**：无业务逻辑，只放 feature 组件与页面级 loading/error
- **features 承担业务模块**：组件 + 专属 hook + 专属 API 封装按领域聚合
- **shared 放真正通用组件**：无业务耦合的 primitives 与工具
- **api 放底层 HTTP client 与统一错误处理**

---

## 7. 页面职责规划

### 7.1 `/create`（创作页）

包含：
- `PromptGeneratePanel`（来自 GenerateConsole：prompt 输入/生成按钮/状态）
- `StyleTemplateSelector`（来自 StyleTemplatePanel + useStyles）
- `GenerationOptions`（styleStrength 等参数）
- `GeneratedProjectSummary`（生成成功后的摘要 + 最近工程）
- `RecentProjectsPanel`（最近生成的工程入口，跳转工作台）
- `SoundFontQuickStatus`（FluidSynth/音源可用性一句话提示，来自 RendererStatusCard 精简版）

不包含：
- 深度 Piano Roll
- 版本 diff
- stems 详情
- 工程恢复
- 复杂 MIDI 编辑

### 7.2 `/projects`（工程库页）

包含：
- `ProjectLibraryPanel`（工程列表）
- `ProjectCard`（单工程卡片：标题/BPM/调性/资产状态）
- `ProjectSearchBar`（搜索过滤）
- `ProjectStatusBadges`（MIDI/WAV/SoundFont/quality 状态角标）
- `ImportProjectButton`（导入 .aimusic.zip，可无工程执行）
- `DeleteProjectDialog`（删除二次确认）

不包含：
- 自然语言修改
- MIDI 深度编辑
- 复杂版本对比

### 7.3 `/projects/:songId`（工程工作台页）

以 `songId` 为唯一核心上下文（来自 URL），包含：
- `WorkspaceHeader`
- `MusicSpecInspector`（来自 MusicSpecPanel/ProjectOverviewPanel 合并）
- `TrackListPanel`（来自 TrackInstrumentPanel）
- `AudioPreviewPanel`（来自 PlaybackDownloadPanel + AudioPlayer + RendererStatusCard）
- `PianoRollPanel`
- `SoundFontPanel`
- `VersionPanel`
- `RenderTasksPanel`
- `QualityReportPanel`
- `ExportMenu`（导入导出/Stems）
- `NaturalLanguageEditPanel`（来自 EditSongPanel）

---

## 8. 迁移顺序建议

### T33.1 引入路由与页面壳（已完成）

- 状态：**Completed**（commit `8d0c34d` 前后，见 git log）
- 目标：引入 React Router（react-router-dom@6.30.4 + createBrowserRouter），建立 AppShell + 三页面壳
- 输入：T33.0 本文档；输出：路由可导航、页面壳可渲染、`/projects/:songId` 刷新可恢复
- 实际落地：
  - `app/router.tsx`：`/` → `/create`、`/create`、`/projects`、`/projects/:songId`、`*` → NotFound
  - `app/layout/AppShell.tsx`：顶部导航（创作/工程库，NavLink active 态）+ Outlet，无业务状态
  - `pages/CreatePage.tsx`：复用 `LegacyCreateContent`（GenerateConsole + 概览 + 调试）
  - `pages/ProjectLibraryPage.tsx`：页面壳 + EmptyState（列表能力留 T33.3）
  - `pages/ProjectWorkspacePage.tsx`：`useParams<{songId}>` → `LegacyWorkspaceContent`，URL 缺失显示 ErrorState
  - `pages/NotFoundPage.tsx`：最小错误页
  - `components/legacy/LegacyWorkspaceContent.tsx`：原 App 工作台状态/回调原样保留，接收 songId 并在变化时 loadSong + 刷新资产/版本
  - `components/legacy/LegacyCreateContent.tsx`：生成控制台 + 概览，生成成功后 navigate `/projects/:songId`
  - `App.tsx`：降级为兼容层（`Navigate to /create`），main.tsx 改挂 `RouterProvider`
  - `styles/app-shell.css`：最小导航/页面壳样式
  - e2e：新增 `router.spec.ts`（5 用例），`demo.spec.ts` 适配新路由
- 风险说明：e2e 浏览器在本机下载超时未跑（chromium 未安装成功），build 通过；`/projects/:songId` 直接打开与刷新已验证可服务（SPA fallback 由 dev server 提供，生产需 Nginx `try_files`）

### T33.2 工程 API 层整理（已完成）

- 状态：**Completed**
- 目标：把工程/song/project 生命周期 API 统一为稳定入口，消除散落 fetch 与重复封装
- 实际落地：
  - **后端 unblocker（最小补充，低风险）**：新增 `GET /api/v1/projects`（工程列表，倒序）与
    `DELETE /api/v1/songs/{song_id}`（删除工程）。storage 新增 `list_project_ids` /
    `delete_project` / `get_project_summary` / `_read_current_version_id`；schema 新增
    `ProjectSummaryItem` / `ProjectListResponse`。新增 `tests/test_project_list_api.py`（5 用例）。
    未改变任何既有 API 行为；全量 pytest 669 passed。
  - **前端工程生命周期统一入口**：`features/projects/projectTypes.ts`（camelCase 映射，Project ==
    后端 song project）+ `features/projects/projectApi.ts`（`listProjects` / `getProject` /
    `deleteProject` / `importProject` / `exportProject`，均支持 AbortSignal）+ `index.ts`
  - **hooks**：`features/projects/useProjects.ts`（projects/isLoading/error/reload/removeProject，
    AbortController 防竞态）；`features/projects/useProject.ts`（songId 缺失不发请求、变化重载、
    notFound/404、unmount 取消）
  - **httpClient**：复用现有 `api/client.ts`（`apiFetch`/`requestJson`/`apiDownloadBlob`/
    `ApiRequestError`），新增 AbortSignal 透传与 `ABORTED` code；`requestJson` 支持 FormData
  - **下载抽象**：`shared/utils/download.ts`（`downloadBlob` + `filenameFromContentDisposition`）
  - **页面最小接入**：`ProjectLibraryPage` 用 `useProjects()` 渲染最小列表（标题/日期/版本/
    资产 badges/进入工作台；无搜索筛选删除 UI）；`ProjectWorkspacePage` 保持 LegacyWorkspaceContent
    （已有独立加载，避免重复请求，hook 接口留 T33.5 接入）
- 命名：前端 Project == 后端 song project（`/api/v1/songs/*`），仅在 projectApi 边界做
  snake_case → camelCase 映射
- 遗留 legacy：`api/projectApi.ts`（仅 import/export，被旧面板使用）→ T33.6 合并到新入口；
  `musicApi.ts` 空壳 re-export 待 T33.6 清理
- 散落 fetch：无（全部经 api 层）

### T33.3 工程库页 ProjectLibraryPage（已完成）

- 状态：**Completed**
- 目标：把 /projects 从页面壳升级为正式工程库
- 实际落地：
  - 新增组件（`features/projects/`）：`ProjectCard`（标题/创建时间/版本/songId 截断/状态
    badges/打开/导出/删除；点击打开工作台，SPA 导航）、`ProjectStatusBadges`（仅真实字段：
    MIDI/WAV/质量/Fallback/FluidSynth/SF）、`DeleteProjectDialog`（role=dialog + aria-modal，
    二次确认，删除中禁用，失败保持打开并显示错误）、`ImportProjectButton`（.zip/.aimusic.zip
    + FormData 导入，idle/importing/error 状态）、`ProjectLibraryPanel`（客户端搜索 title/
    songId + 状态筛选 全部/有WAV/有MIDI/Fallback + 刷新 + 过滤空态「清除搜索/清除筛选」）
  - `ProjectLibraryPage` 重写：组合 useProjects + Panel + Dialog + Import；Header actions
    （+新建音乐 /projects → /create、导入）；删除流程：点击删除 → Dialog 确认 →
    `useProjects.removeProject` → 成功后本地移除并关闭；导入成功 → reload + navigate 新工程
  - `shared/utils/date.ts`：`formatDateTime`（Intl，无 dayjs）
  - `styles/app-shell.css`：grid（auto-fill minmax(280px,1fr)，窄屏 1 列）、toolbar、dialog
  - 无 N+1：卡片只用 ProjectSummary 字段，无 per-card 请求
- 后端：无修改（T33.2 的 list/delete 已就绪）；导入/导出 round-trip 实测通过
  （export→import 得到新 songId）
- 数据流：`ProjectLibraryPage → useProjects → projectApi → client → backend`；
  删除：`DeleteProjectDialog → useProjects.removeProject → projectApi.deleteProject`；
  导入：`ImportProjectButton → projectApi.importProject → navigate(/projects/:songId)`
- 遗留：删除失败细分（404 视为已删除等）可后续优化；导出按钮已提供（T33.8 可增强）；
  搜索/筛选为客户端实现，量大时再做服务端

### T33.4 创作页 CreatePage（已完成）

- 状态：**Completed**
- 目标：把「一句话生成音乐」流程从旧 App/Workspace 状态中独立出来，形成真正的 /create 创作页
- 实际落地：
  - 新增 `features/generation/`：`useGenerateSong.ts`（prompt/styleTemplateId/styleStrength 状态
    只属于 CreatePage；防重复提交 inFlightRef；AbortController 防 unmount 旧请求；失败保留表单；
    再次生成创建新工程）、`generationApi.ts`（复用 songApi.generateMusicSpec，把响应规范化为
    `GeneratedProjectSummary`，页面不判断 snake_case）、`generationTypes.ts`（GenerateSongInput /
    GeneratedProjectSummary）、`PromptGeneratePanel.tsx`（textarea + StyleTemplateSelector +
    生成按钮 + loading/error）、`StyleTemplateSelector.tsx`（模板选择 + 强度滑杆，模板加载失败
    不阻塞基础生成）、`GeneratedProjectSummary.tsx`（标题/songId/BPM/调性/拍号/风格/段落/轨道/
    warnings + 「进入工程工作台」按钮）
  - `CreatePage.tsx` 重写：组合 useGenerateSong + useStyles + PromptGeneratePanel +
    GeneratedProjectSummary；**生成成功后不自动跳转**，用户确认摘要后点击进入工作台
  - `songApi.generateMusicSpec` 增加 AbortSignal 透传
  - `styles/app-shell.css`：创作页布局（最大 860px 居中、生成面板、响应式单列）
  - T31 回归确认：payload 链路 `PromptGeneratePanel → useGenerateSong → generationApi →
    songApi.generateMusicSpec(prompt, style_template_id, style_strength)` 实测通过
    （后端返回 style_template.id 与请求一致）
- 遗留 legacy：`components/legacy/LegacyCreateContent.tsx` 已无引用（仍保留文件，T33.6 删除）；
  Workspace 内 GenerateConsole 仍存在（Workspace 保留生成能力，T33.6 再决定是否移除）；
  App.tsx 的 create 状态已随 LegacyCreateContent 停用（T33.5 再清理 Workspace 侧）
- 数据流：`CreatePage → useGenerateSong → generationApi → songApi → client → backend`；
  进入工作台：`navigate(/projects/:songId)`（Workspace 通过 URL 自加载，不依赖 CreatePage 内存）

### T33.5 工程工作台页 ProjectWorkspacePage（已完成）

- 状态：**Completed**
- 目标：把「针对一个具体工程」的功能集中到 /projects/:songId，形成独立工作台
- 实际落地：
  - 新增 `features/workspace/useProjectWorkspace.ts`：协调层——`useProject(songId)`（页面级
    loading/404/error/reload）+ 业务 hooks（useSongProject/useAudioAssets/useVersions/useStyles）
    组合；**避免重复 getSong**（useProject 详情注入 useSongProject.setSongId/setMusicSpec）；
    切换 songId 立即清理旧资产；refs 防 stale closure；songId 变化 effect 依赖保证重绑后刷新
  - 新增 `features/workspace/WorkspaceHeader.tsx`：← 工程库 + 工程标题 + songId 简写 + 版本 +
    MIDI/WAV/FluidSynth/Fallback/SoundFont badges + error（仅真实 metadata）
  - `ProjectWorkspacePage.tsx` 重写：URL songId → useProjectWorkspace；四态处理
    （missing ID / 404「工程不存在或已被删除」/ loading「正在加载工程…」/ error「工程加载失败」
    + 重新加载）；工作台组合 WorkspaceDashboard + 全部回调（生成/编辑/恢复/优化/重生成/导入）
  - 状态归属：MIDI/audio/versions/soundfont/tasks 各自 hook（useAudioAssets/useVersions/
    useSoundfonts/useRenderTasks 已存在，复用）；页面只做协调
  - 刷新恢复：useProject 从 URL 加载，assets/versions 自动刷新
  - 检查通过：无 selectedSongId、无 window.location.reload/href、无组件内直接 fetch
- 遗留 legacy（T33.6）：`components/legacy/LegacyWorkspaceContent.tsx`（已不再被页面引用，
  保留文件）；App.tsx 兼容层（Navigate /create）；Workspace 内 GenerateConsole 去留；
  workspace 面板按 feature 目录进一步拆分；useSongProject 生成态/工程态深拆
- 数据流：`ProjectWorkspacePage → useProjectWorkspace(songId) → useProject → projectApi →
  backend`；业务 hooks 各自绑定 songId

### T33.6 工作台功能模块拆分
- 目标：把 workspace/ 面板按 feature 目录搬移，删除 legacy 死代码
- 输入：T33.5 后的工作台；输出：features/* 干净分组
- 风险：跨文件 import 链断裂——批量搬移 + tsc 校验 + 逐个验证

### T33.6 工作台功能模块拆分
- 目标：把 workspace/ 面板按 feature 目录搬移，删除旧 WorkspaceLayout 死代码
- 输入：T33.5 后的组件；输出：features/* 干净分组
- 风险：跨文件 import 链断裂——批量搬移 + tsc 校验 + 逐个验证

### T33.7 SoundFont / Renderer 状态前端整合
- 目标：把 T39 的 renderer 状态（RendererStatusCard/诊断）整合进各页面状态体系
- 输入：soundfontApi diagnostics + useSoundfonts；输出：创建页 QuickStatus、工作台完整状态
- 风险：warning 误报——以 is_fallback 为准（T39-B 已固化）

### T33.8 导入导出 / 删除 / 二次确认流程
- 目标：统一导入（/projects 与 /create 可用）、导出、删除确认交互
- 输入：ProjectImportExportPanel + DeleteProjectDialog；输出：统一流程组件
- 风险：误删工程——必须确认对话框 + 禁用危险默认

### T33.9 前端回归、文档与收尾
- 目标：全量回归（生成→工作台→版本→SoundFont→渲染→导出）、清理死代码、更新文档
- 输入：T33.1~8 成果；输出：T33 完成
- 风险：回归范围大——按 QA 清单（FRONTEND_WORKSPACE_QA.md）逐项验证

---

## 9. 风险清单

| 风险 | 控制建议 |
|---|---|
| 路由切换后状态丢失 | 页面级状态只依赖 songId/prompt 等可序列化输入；跨页面共享用 URL query 或轻量 context |
| 刷新 /projects/:songId 无法恢复 | songId 进 URL；页面加载时用 getSong(songId) 重建（useProject 初始化逻辑） |
| 旧组件强依赖 App 顶层状态 | 先做 useSongProject 拆分（生成态/工程态分离），再迁移组件；保持 props 接口稳定 |
| API 返回类型不统一 | T33.2 统一类型组织；`ApiRequestError` 已统一，检查各 hook 的 error 透传 |
| 工程删除误触 | DeleteProjectDialog 二次确认 + 删除按钮非默认样式 + 后端删除接口确认（若存在） |
| SoundFont / renderer warning 误报 | 只信 `is_fallback` 字段（T39-B/C 已保证），前端不自行推断 |
| 生成页与工作台互相污染 | useGenerateSong 与 useProject 完全分离；生成完成只产出 songId，跳转后由 URL 恢复 |
| 过度抽象导致组件复杂 | 先搬不抽象；只在出现 2+ 处重复时再提取 shared |
| 两套工作台并存（旧死代码） | T33.6 删除 WorkspaceLayout 及其专属组件（GeneratePanel/PlayerPanel/EditPanel/AnalysisPanel/ProjectPanel） |
| 样式按阶段命名难维护 | T33.9 前不重命名；后续可按 feature 合并样式文件 |

---

## 10. 暂不处理项

本任务（T33.0）及 T33 系列规划阶段明确不处理：

1. 不引入 React Router 重构（T33.0 只做文档；T33.1 才动手）
2. 不搬迁组件（T33.0 不动代码）
3. 不重写 App.tsx
4. 不改后端 API
5. 不改 MIDI 编辑逻辑
6. 不改 SoundFont 渲染逻辑
7. 不改样式体系
8. 不新增复杂状态管理库（Redux/Zustand 不引入；如需要轻量 context 即可）
9. 不删除现有组件（T33.6 才清理死代码）
10. 不新增测试框架（项目无 Vitest/RTL，保持现状）

> 本任务（T33.0）仅新增本文档，不修改任何业务代码。
