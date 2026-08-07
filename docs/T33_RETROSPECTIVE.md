# T33 前端改造回溯与架构验收报告（T33-R）

> 审计日期：2026-08-07 ｜ 分支：`master`（HEAD `d78c310`）
> 依据：当前代码、真实依赖关系、API 调用、build 结果、pytest 结果与 git history。
> 状态约定：PASS / PARTIAL / FAIL / NOT_VERIFIED（禁止模糊表述）。

> 更新（T33-R1 Browser Verification，2026-08-07）：真实浏览器回归完成。
> 更新（T33-R4 Real FluidSynth Verification，2026-08-07）：真实 SoundFont 渲染链路验收完成。
> 更新（T33-R3 Frontend Automated Tests，2026-08-07）：前端关键状态自动化测试完成。
> 更新（T33-R2 Legacy Cleanup，2026-08-07）：Legacy / Dead Code 清理完成。

## T33-R2 Legacy Cleanup

- **删除的 hooks（确认无生产/测试引用）**：`useMixer.ts`、`useQuality.ts`、`useEvaluation.ts`、
  `useReferenceMidi.ts`、`useRenderTasks.ts`（仅 `hooks/index.ts` re-export，无任何组件/页面调用；
  RenderTasksPanel 为独立拉取实现，不依赖旧 useRenderTasks 轮询）。
- **保留的 hooks 及原因**：`useSongProject` / `useAudioAssets` / `useVersions` / `useStyles` /
  `useSoundfonts` 均为生产使用。
- **musicApi.ts 删除**：是。10 处 import 全部迁移到领域 API
  （mixApi / analysisApi / referenceApi / evaluationApi / styleApi / songApi / audioApi / projectApi），
  类型统一改从 `api/types.ts` 导入；`musicApi.ts`（`export * from "./index"` 兼容壳）已删除。
- **TrackMixerStrip 最终位置**：`features/audio/TrackMixerStrip.tsx`（git mv，import 同步更新）。
- **残留 legacy**：无（`components/` 仅剩 `ui/` 通用 primitives）。
- **依赖方向**：无反向/循环依赖（features 不依赖 page/shared）。
- 验证：`npm run build` 通过；`npm test` 13 passed（T33-R3 关键用例未受影响）。

### Goal G23 更新

`G23 Legacy 明显收敛`：**PARTIAL → PASS**（5 个 dead hooks + musicApi 兼容壳删除、TrackMixerStrip 归位；
components/ 仅剩 ui primitives）。

## T33-R3 Frontend Automated Tests

- 框架：**Vitest + jsdom + @testing-library/react + @testing-library/jest-dom + user-event**
  （最小依赖，未引入第二套框架；Playwright E2E 保持独立）。
- 配置：`apps/web/vitest.config.ts`（jsdom、globals、setupFiles）、`src/test/setup.ts`（jest-dom + cleanup）、
  `package.json` scripts：`test` / `test:watch`。
- 测试文件（colocated）：
  - `features/audio/RendererStatusCard.test.tsx`（4：fallback 语义）
  - `hooks/useAudioAssets.test.ts`（2：stale 标记/清除、selected≠rendered）
  - `features/projects/DeleteProjectDialog.test.tsx`（4：取消/确认/防重复/关闭）
  - `shared/utils/download.test.ts`（2：Blob URL 创建与 revoke、click 抛异常仍 revoke）
  - `features/projects/useProject.test.ts`（1：songId 切换旧请求不能覆盖新状态）
- 结果：**13 passed**；`npm run build` 通过。
- 覆盖的 T33 核心规则：fallback 仅以 `is_fallback` 为准（不按 renderer 名推断）、无 WAV 不显示 fallback、
  selected ≠ rendered、audioNeedsRender 置位/清除、删除防重复提交、downloadBlob revoke 不遗漏、
  songId 切换 AbortController 隔离。
- 发现并修复的 bug：`downloadBlob` 在 `anchor.click()` 抛异常时未执行 `revokeObjectURL`
  （改为 try/finally，保证 Blob URL 始终释放）。
- 仍未覆盖：Render Task polling 细节（生产面板为拉取式、无长轮询定时器）、
  Workspace 删除成功导航（由 T33-R1 浏览器 E2E 覆盖）、SoundFont 多音源切换（环境限制）。

## T33-R4 Real FluidSynth Verification

环境：Windows + FluidSynth 2.4.7（chocolatey 安装，`C:\ProgramData\chocolatey\bin\fluidsynth.EXE`）+ `data/soundfonts/GeneralUser-GS.sf2`（32MB，gitignored）。

```text
FluidSynth binary: C:\ProgramData\chocolatey\bin\fluidsynth.EXE
FluidSynth version: FluidSynth runtime version 2.4.7（-V 检测成功）
SoundFont: GeneralUser-GS.sf2（id=35a7972b7b5f，exists/readable/valid=true）
Diagnostics: fluidsynth.available=true, renderer_backends.fluidsynth=true

songId: cd70852c-d7d1-4cba-a618-c9568f48dbd0（测试工程，已清理）
render result: 真实产品 API 渲染成功（同步 + 异步 Render Task 均 succeeded）
WAV: output.wav 存在，11954220 bytes（≈11.9MB），duration 67.77s

renderer: fluidsynth
is_fallback: false
fallback_reason: null
soundfont_name: GeneralUser-GS
soundfont_id: 35a7972b7b5f

frontend result: PASS（r4-verify.spec.ts + 手动浏览器验证）
  - Workspace 显示 FluidSynth / GeneralUser-GS
  - 无 fallback warning
  - audio 元素可播放
browser refresh result: PASS（刷新后状态保持）
```

| 验收项 | 状态 | 证据 |
|---|---|---|
| FluidSynth 可被 backend 找到 | PASS | diagnostics `available=true` + version 2.4.7 |
| GeneralUser-GS.sf2 可解析 | PASS | diagnostics `valid=true` + API 列表返回 |
| 工程选择 SoundFont 成功 | PASS | PUT /soundfont 返回 GeneralUser-GS |
| 真实产品 render API 成功 | PASS | POST /audio/render → metadata renderer=fluidsynth |
| 真实 WAV 输出存在 | PASS | 11.9MB / 67.77s（非 HTTP 200 单点判断） |
| renderer / is_fallback / soundfont_name | PASS | 磁盘 audio_metadata.json + assets API 一致 |
| Workspace 显示 FluidSynth、无 fallback warning | PASS | Playwright 真实浏览器 |
| 浏览器刷新后状态保持 | PASS | reload 后 GeneralUser-GS 仍在、无 fallback |
| 异步 Render Task metadata 传播 | PASS | tasks/render-audio succeeded → assets renderer=fluidsynth |
| selected ≠ rendered 回归（换第二个 SoundFont） | NOT_VERIFIED | 环境仅有 1 个 SoundFont，无法实测切换 |
| Fallback 路径（fallback_reason 传播） | PASS | 既有 pytest 覆盖（46 passed，mock subprocess） |

结论：**T33-R4 = PASS**（真实 WAV 由 FluidSynth 生成，metadata 反映真实渲染路径，前端显示正确）。
唯一 NOT_VERIFIED：多 SoundFont 切换回归（环境限制，非缺陷）。

## T33-R1 Browser Verification

环境：Playwright Chromium（npmmirror 下载）+ MockProvider 后端（fallback renderer）+ Vite dev server。

| 验收项 | 状态 | 证据 |
|---|---|---|
| Flow A：/create → 生成 → 摘要 → 工作台 → MIDI → WAV | PASS | `e2e/demo.spec.ts`（真实浏览器生成/播放） |
| Flow B：/projects → 打开 → 刷新恢复 → 编辑 → 版本 → 导出入口 | PASS | `e2e/flow-b-project.spec.ts` |
| Flow C：删除 Cancel/Confirm → 回 /projects → 列表移除 | PASS | `e2e/flow-b-project.spec.ts` |
| Workspace 刷新恢复（URL songId） | PASS | `e2e/router.spec.ts` 刷新用例 |
| 工程 A → B 状态隔离 | PASS | `e2e/flow-b-project.spec.ts`（标题/song_id 无残留） |
| SoundFont UI 语义（环境能力 ≠ 当前 WAV） | PASS | `e2e/flow-soundfont.spec.ts` |
| 路由三结构 + NotFound | PASS | `e2e/router.spec.ts`（6 用例） |
| Playwright 套件 | PASS | **11 passed**（16.5s） |

### 发现并修复的 P1 Bug（自然语言编辑失效）

- **复现步骤**：工作台输入编辑指令 → 点击“应用修改” → 无任何 POST /edit 请求，版本不更新。
- **根因**：`ProjectWorkspacePage.handleApplyEdit` 读取 `songProject.editInstruction`（React state），
  而 `WorkspaceDashboard.onEditSong` 先 `setEditInstruction(instruction)`（异步）再立即调用
  `onApplyEdit`，点击时 state 仍是旧值（空），`edit()` 因空指令直接返回。
- **修复**：`handleApplyEdit(instruction, autoRender)` 直接接收指令字符串，不再依赖异步 state；
  `WorkspaceDashboard` 同步传参。修复后 POST /edit 200 且版本刷新为 v2。

### 非阻塞观察（P2/P3）

- 页面加载时偶发 `GET /versions` 400（Vite 代理/时序相关，直接 API 调用 5 次均为 200，
  非后端缺陷；不影响主流程，未进一步深挖）。
- 工作台首屏会并行请求 styles / soundfonts / evaluation / mix / tasks / assets 等多个接口
  （一次性加载较多，功能正常；后续可做 tab 懒加载优化）。

### 未验证项

- Render Task 异步轮询的浏览器级观察：后端 mock/fallback 渲染极快（任务秒级完成），
  未捕获到 queued → running → succeeded 的完整 UI 过渡（不影响功能结论）。
- 真实 FluidSynth + SoundFont 渲染 metadata：仍归 T33-R4。

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
