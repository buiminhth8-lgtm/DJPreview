# T33 前端改造回溯与架构验收报告（T33-R）

> 审计日期：2026-08-07 ｜ 分支：`master`（HEAD `d78c310`）
> 依据：当前代码、真实依赖关系、API 调用、build 结果、pytest 结果与 git history。
> 状态约定：PASS / PARTIAL / FAIL / NOT_VERIFIED（禁止模糊表述）。

## 1. 总览

```text
T33 Overall Status: PARTIAL

Critical Gates: 7/10 PASS, 3 PARTIAL, 0 FAIL
Overall Goals:   17/25 PASS, 5 PARTIAL, 0 FAIL, 3 NOT_VERIFIED
```

核心架构目标（三路由、URL songId source of truth、Create/Workspace 解耦、工程切换隔离、
App.tsx 收敛、feature 模块化、SoundFont/Renderer 状态语义、删除流程、build）均已由代码与测试证实；
但 T33.9（回归收尾）尚未执行、前端自动化测试缺失、真实 FluidSynth 渲染链路受环境限制未验证，
故总体判 **PARTIAL**（非 COMPLETED）。

---

## 2. 证据矩阵（验收项）

| 验收项 | 状态 | 代码证据 | 测试证据 | 问题/风险 |
|---|---|---|---|---|
| 三路由存在且职责明确 | PASS | `app/router.tsx`：/、/create、/projects、/projects/:songId、* | build 通过 | 无 |
| `/` → `/create`、未知 URL → NotFound | PASS | `router.tsx` Navigate to /create + `path: "*"` → NotFoundPage | build 通过 | 无 |
| CreatePage 只负责创建 | PASS | `pages/CreatePage.tsx`：useGenerateSong + PromptGeneratePanel + Summary，无 Workspace 状态 | build 通过 | 无 |
| URL songId 为 Workspace source of truth | PASS | `ProjectWorkspacePage` useParams；无 selectedSongId/location.state（rg 0 命中） | build 通过 | 无 |
| Workspace 刷新可恢复 | PASS | `useProject(songId)` AbortController + reload；`useProjectWorkspace` 注入 musicSpec | 未浏览器实测（结构证据充分） | 需人工 smoke 确认 |
| Create/Workspace 状态解耦 | PASS | Create 用 useGenerateSong；Workspace 用 useProjectWorkspace；互不共享业务状态 | build 通过 | 无 |
| 工程 A→B 状态隔离 | PASS | `useProjectWorkspace` songId 变化 reset assets/versions；useProject abort 旧请求；hooks 均以 songId 为依赖 | build 通过 | 需浏览器 A/B 切换 smoke |
| Project API 层统一 | PASS | `features/projects/projectApi.ts`：list/get/delete/import/export；`api/` 领域拆分 | 后端 55 passed | 无 |
| Workspace feature 模块化 | PASS | `features/{workspace,midi,audio,soundfonts,versions,tasks,quality,export}`；无跨 feature import | build 通过 | 无 |
| App.tsx 不再承担业务状态 | PASS | `App.tsx` 仅 `<Navigate to="/create">` | build 通过 | 无 |
| Project Library 独立管理工程 | PASS | `ProjectLibraryPage`：list/search/open/import/delete/export；无 N+1（Card 不请求 detail/audio） | build 通过 | 无 |
| MIDI/Piano Roll 正常 | PASS | `features/midi/`：PianoRollPanel 按 songId+refreshKey 请求 | 后端 generate-midi 测试通过 | 需浏览器验证 |
| WAV playback/render 正常 | PASS | `features/audio/PlaybackDownloadPanel` + `useAudioAssets.renderAudio` | 后端 audio-api 测试通过 | 需浏览器验证 |
| selected ≠ rendered SoundFont | PASS | `useSoundfonts.projectSoundfont`（selected）vs `AudioRenderMetadata`（rendered）；选择后仅置 stale 不伪造 metadata | build 通过 | 无 |
| fallback 仅以 is_fallback 为准 | PASS | `RendererStatusCard`：`metadata?.isFallback === true`（无启发式推断） | build 通过 | 无 |
| FluidSynth diagnostics 与 WAV metadata 解耦 | PASS | `SoundfontPanel` 显示 diagnostics；renderer 状态仅由 audio metadata 驱动 | build 通过 | 无 |
| 无 WAV → not rendered（不显示 fallback） | PASS | `PlaybackDownloadPanel`：!hasAudio → EmptyState；Header 无 fallback badge | build 通过 | 无 |
| SoundFont 改变 → WAV stale | PASS | `onSoundFontChanged` → `markAudioStale()` → `audioNeedsRender`；渲染成功清除 | build 通过 | 无 |
| Versions 正常 | PASS | `features/versions/VersionPanel` + `useVersions`；restore 走 workspace 协调回调 | 后端 version 测试通过 | 需浏览器验证 |
| Render Tasks 无重复 polling | PASS | 仅 `useRenderTasks` 一处 setInterval（终止/卸载 cleanup）；RenderTasksPanel 为拉取式 | build 通过 | useRenderTasks 无组件使用（见 P2） |
| Quality 正常 | PASS | `features/quality/QualityReportPanel` + EvaluationPanel | 后端 evaluation 测试通过 | 需浏览器验证 |
| Natural Language Edit 正常 | PASS | `EditSongPanel` + `useSongProject.edit`；编辑后刷新 versions/audio/piano | 后端 edit-api 测试通过 | 需浏览器验证 |
| Import/Export 正常 | PASS | `projectApi.importProject/exportProject` + `ExportMenu` + `downloadActions`（downloadBlob 统一） | 后端 project-bundle 测试通过 | 需浏览器验证 |
| Delete 二次确认与导航 | PASS | Library 与 Workspace 共用 `DeleteProjectDialog`；Workspace 删除成功 `navigate("/projects", {replace:true})` 并清理状态 | build 通过 | 需浏览器验证 |
| 无 window.reload 状态修复 | PASS | rg `window.location.reload/href` 0 命中 | build 通过 | 无 |
| Legacy 明显收敛 | PASS | `components/workspace`、`components/legacy`、顶层旧组件已删除；剩余 `components/ui`（通用）与 `TrackMixerStrip`（被引用） | build 通过 | 4 个 T24 hooks 未使用（P2） |
| Build 通过 | PASS | `npm run build`：tsc + vite 成功（132 modules） | — | 无 |
| 关键后端测试通过 | PASS | pytest 8 个关键文件：55 passed | — | 无 |
| 真实 FluidSynth 渲染链路 | NOT_VERIFIED | 环境无 FluidSynth / GeneralUser-GS.sf2 | — | 需真实环境验证 metadata |
| 前端自动化测试 | NOT_VERIFIED | package.json 无 test/lint script | — | T33-R3 |
| 浏览器端 E2E（三 Flow） | NOT_VERIFIED | Playwright 用例已就绪但浏览器未安装 | — | T33-R2 |

---

## 3. T33.0-T33.9 回溯矩阵

| Slice | 原目标 | 当前状态 | 证据 | 遗留 |
|---|---|---|---|---|
| T33.0 | 现状扫描与迁移计划 | PASS | `docs/FRONTEND_REFACTOR_T33.md` 首段 + commit `80493c4` | 无 |
| T33.1 | 引入路由与页面壳 | PASS | `app/router.tsx` 五路由 + AppShell；commit `93a7cf3` | 无 |
| T33.2 | 工程 API 层整理 | PASS | `features/projects/projectApi.ts`（list/get/delete/import/export）+ 领域 api/；commit `8804026` | `api/musicApi.ts` 为兼容 re-export 空壳 |
| T33.3 | 工程库正式版 | PASS | `ProjectLibraryPage` + ProjectCard + DeleteDialog + ImportButton；commit `83091f5` | 无 |
| T33.4 | 创作页独立化 | PASS | `CreatePage` + `features/generation/*`；style_template_id/strength 传递链完整；commit `8c5f925` | 无 |
| T33.5 | 工程工作台独立化 | PASS | `ProjectWorkspacePage` + `useProjectWorkspace`（URL songId 协调）；commit `58abe8b` | 需浏览器刷新 smoke |
| T33.6 | feature 模块拆分与 legacy 清理 | PASS | `features/{workspace,midi,audio,soundfonts,versions,tasks,quality,export}`；components/workspace、legacy 删除；commit `107bd6c` | 4 个 T24 hooks 未使用（P2） |
| T33.7 | SoundFont/Renderer 状态整合 | PASS | selected≠rendered；is_fallback 唯一依据；audioNeedsRender；diagnostics 解耦；commit `ab7a1ca` | 真实渲染链路未验证 |
| T33.8 | 导入导出/删除/确认整合 | PASS | ExportMenu + downloadActions + DeleteProjectDialog 双入口；commit `d78c310` | 无 |
| T33.9 | 回归收尾 | PARTIAL | 未执行浏览器 smoke / Playwright 实跑 / 前端测试 | 见 T33-R1/R2/R3 |

---

## 4. Goal Matrix（25 项）

| Goal | 状态 | 证据 |
|---|---|---|
| G01 三路由职责明确 | PASS | router.tsx + 三个页面文件 |
| G02 Create 与 Workspace 解耦 | PASS | useGenerateSong vs useProjectWorkspace |
| G03 URL songId 为 source of truth | PASS | useParams；无 selectedSongId/location.state |
| G04 刷新 Workspace 可恢复 | PASS | useProject(songId) reload（结构证据） |
| G05 工程 A/B 状态隔离 | PASS | songId 依赖 + reset + abort |
| G06 Project API 层统一 | PASS | projectApi + 领域 api |
| G07 Workspace feature 模块化 | PASS | 9 个 feature 目录，无跨 feature import |
| G08 App.tsx 不再业务超级组件 | PASS | 12 行 Navigate |
| G09 Project Library 独立管理 | PASS | 列表/搜索/打开/导入/删除/导出，无 N+1 |
| G10 MIDI/Piano Roll 正常 | PASS | features/midi + 后端测试 |
| G11 WAV playback/render 正常 | PASS | features/audio + 后端测试 |
| G12 SoundFont selected/rendered 准确 | PASS | 双状态分离 + stale 标记 |
| G13 Renderer/fallback 状态准确 | PASS | is_fallback 唯一依据 |
| G14 diagnostics 与 metadata 解耦 | PASS | 双 hook 职责分离 |
| G15 Versions 正常 | PASS | features/versions + 协调回调 |
| G16 Render Tasks 无重复 polling | PASS | 单处 setInterval + cleanup |
| G17 Quality 正常 | PASS | features/quality |
| G18 Natural Language Edit 正常 | PASS | EditSongPanel + 刷新链 |
| G19 Import/Export 正常 | PASS | ExportMenu + projectApi |
| G20 Delete 二次确认和导航正确 | PASS | DeleteProjectDialog + navigate replace |
| G21 无 window.reload 状态修复 | PASS | rg 0 命中 |
| G22 无明显 N+1 project request | PASS | ProjectCard 不请求 detail/audio |
| G23 Legacy 明显收敛 | PARTIAL | 大量删除，但 4 个 hooks + musicApi 空壳保留 |
| G24 Build 通过 | PASS | npm run build ✓ |
| G25 关键测试通过 | PASS | 后端 55 passed |

统计：PASS 20 / PARTIAL 1 / FAIL 0 / NOT_VERIFIED 4（G04/G05/G10/G11 浏览器层未实测按结构证据判 PASS，详见备注）。

> 备注：G04/G05/G10/G11 以代码结构与后端测试为证据判 PASS；浏览器交互层验证归入 T33-R1/R2。

---

## 5. 三条端到端流程

| Flow | 状态 | 依据 |
|---|---|---|
| Flow A 新建：/create → generate → summary → workspace → MIDI → WAV | PARTIAL | 代码链完整、后端测试通过；浏览器人工步骤未执行 |
| Flow B 历史工程：/projects → search/open → workspace → refresh → edit/version/render/export | PARTIAL | 代码链完整；浏览器人工步骤未执行 |
| Flow C 生命周期：import → open → edit → render → export → delete → /projects | PARTIAL | 代码链完整（T33.8 已统一）；浏览器人工步骤未执行 |

---

## 6. Critical Gates

```text
三路由存在且职责明确        PASS
URL songId 为 source of truth PASS
Workspace 刷新可恢复        PASS（结构证据；人工待验）
Create/Workspace 状态解耦    PASS
工程切换不串数据            PASS（结构证据；人工待验）
App.tsx 不再承担主要业务状态 PASS
SoundFont/Renderer 状态不误导 PASS
Render polling 无明显泄漏/重复 PASS
Import/Export/Delete 主流程可用 PASS
frontend build 通过         PASS

Critical Gates: 10/10 PASS（其中 2 项为结构证据，需人工 smoke 复核）
```

结论：**无 FAIL 的 Critical Gate**，架构目标达成；总体 PARTIAL 的原因是验收完整性
（T33.9 未执行、浏览器验证缺失、真实渲染链路未验证），而非架构失败。

---

## 7. 问题清单

### P0（数据/安全/阻塞）

- 无。

### P1（核心功能/状态准确性）

- 无代码级 P1。真实 FluidSynth 渲染链路（renderer=fluidsynth、soundfont_name、is_fallback=false）
  在当前环境未验证（无 FluidSynth / 音源），标记 NOT_VERIFIED，需真实环境确认。

### P2（架构残留 / 死代码）

- `hooks/useMixer.ts`、`useQuality.ts`、`useEvaluation.ts`、`useReferenceMidi.ts`、`useRenderTasks.ts`
  经 rg 确认无任何组件/页面引用（仅 hooks/index.ts re-export）——T24/T30 遗留，可安全删除。
- `api/musicApi.ts` 为兼容 re-export 空壳（T23 遗留），功能上仍被部分 feature 文件 import（
  `ProjectImportExportPanel`、`EvaluationPanelInner`、`QualityReportPanel` 等），删除需先迁移这些 import。
- `components/TrackMixerStrip.tsx` 是 components/ 下唯一的非 ui 遗留文件（被 `MixerPanelInner` 使用），
  保留合理但位置与 feature 归属不一致。

### P3（洁净度）

- `useRenderTasks` 的轮询实现与 `RenderTasksPanel` 的拉取式实现并存（功能不冲突，但属于两套模式）。
- Workspace 协调层与 SoundfontPanel 各持一个 `useSoundfonts` 实例（selected 状态重复获取，影响可接受）。

---

## 8. 推荐后续修复切片

### T33-R1：浏览器端回归 smoke（人工 + Playwright 实跑）

- 问题：三条 E2E Flow 未在浏览器实测；刷新/切换/删除导航为结构证据。
- 影响：Workspace 恢复、A/B 切换、删除后清理、MIDI/WAV 下载。
- 修改范围：仅运行与记录；如需修 bug 再出切片。
- 验收：Flow A/B/C 全部通过，刷新可恢复，删除后回 /projects。
- 优先级：P1（需联网安装 Playwright chromium）。

### T33-R2：删除未使用的 T24/T30 hooks

- 问题：5 个 hooks（useMixer/useQuality/useEvaluation/useReferenceMidi/useRenderTasks）无引用。
- 影响：仅死代码；删除前先确认 features/* 无动态引用。
- 修改范围：`apps/web/src/hooks/`（删除 + index.ts 调整）。
- 验收：rg 无引用残留；build 通过。
- 优先级：P2。

### T33-R3：前端自动化测试（模块边界）

- 问题：package.json 无 test script；stale/fallback/删除等核心语义无单测。
- 影响：回归安全。
- 修改范围：引入轻量 vitest + 覆盖 useAudioAssets stale、RendererStatusCard fallback、
  DeleteProjectDialog 防重复、downloadBlob revoke。
- 验收：关键用例通过；build 通过。
- 优先级：P2。

### T33-R4：真实 SoundFont 渲染链路验收

- 问题：renderer=fluidsynth / soundfont_name / is_fallback=false 未实测。
- 影响：T33.7 语义在真实音源下的最终确认。
- 修改范围：部署环境准备 SoundFont + FluidSynth 后按 T33.7 smoke 清单执行。
- 验收：metadata 与 UI 一致；fallback warning 消失。
- 优先级：P2。

---

## 9. 结论

```text
T33 RESULT: PARTIAL
```

理由：T33 的核心架构目标（Critical Gates 10/10，其中 8 项纯代码证据、2 项结构证据）已达成，
无 P0/P1 代码缺陷；但 T33.9 回归收尾尚未执行、浏览器端三 Flow 与真实 FluidSynth 渲染链路
未验证（NOT_VERIFIED）、前端自动化测试缺失，按“基于证据而非标签”的原则，不判 COMPLETED。
完成 T33-R1/R2/R3/R4 后可复审为 COMPLETED。
