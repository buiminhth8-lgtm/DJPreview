# T34 Retrospective — MIDI Track Editor Final Completion & P0/P1 Audit

> 审计日期：2026-08-12（Asia/Shanghai）
> 证据约定：`CODE` / `TEST` / `BUILD` / `BROWSER` / `RUNTIME` / `NOT_VERIFIED`。
> 判定约定：`PASS` / `PARTIAL` / `FAIL` / `NOT_VERIFIED`。文档历史状态不作为本报告的通过依据。

## Audit Baseline

| 项目 | 结果 |
|---|---|
| Branch | `master` |
| 审计起始 HEAD | `8c0b7dd` (`add music-aware MIDI editor context`) |
| Working tree | 非 clean；包含 T34.10/T34-R 待验收实现与测试。审计全程未 reset/rebase、未覆盖既有修改 |
| 审计方法 | 代码与依赖审查、全量 pytest/Vitest/build、隔离 Playwright、真实浏览器 smoke、真实 FluidSynth/SoundFont 产品链 |
| 数据安全 | 自动化工程均使用临时 `PROJECTS_DIR`；未向仓库提交 MIDI/WAV/SF2/zip、`data/projects` 或测试产物 |

## Executive Summary

```text
T34-R RESULT: PASS
T34 OVERALL: COMPLETED

T34 Stage Status:
PASS 11 / PARTIAL 0 / FAIL 0 / NOT_VERIFIED 0

Critical Gates:
PASS 16 / PARTIAL 0 / FAIL 0 / NOT_VERIFIED 0

Open Issues:
P0 0 / P1 0 / P2 2 / P3 2
```

T34 的 canonical MIDI 编辑闭环已经真实成立：Generated MIDI → Editor Draft → Preview Draft →
409 conflict 防护 → Manual Save → 新 Version → WAV stale → 真实 FluidSynth 重渲染 → Restore / Bundle。
1000 notes 属于正常可编辑；3000 notes 有可测的性能下降，但未达到不可用。审计发现的 dirty-guard、
version index 并发写入与刷新后 stale 丢失风险均有回归测试并已关闭，最终无开放 P0/P1。

## Canonical Architecture Audit

| Contract | 状态 | 证据 |
|---|---|---|
| canonical time = integer MIDI ticks | PASS | `midi_editor.py` / `midi_editor_io.py` / `midiEditorTypes.ts`；读写与几何测试 |
| PPQ preserved | PASS | Editor document、write-back、reload 均保持源 MIDI `ticks_per_beat`；pytest 全量通过 |
| MusicSpec → Generated MIDI → Manual MIDI Edit | PASS | `/midi/generate` + `/midi/editor` + `/midi/edit`，真实 E2E save/reload |
| Manual Edit 不反向修改 MusicSpec | PASS | final regression 在 Save 前后 deep-equal MusicSpec；bundle roundtrip 同样校验 |
| 编辑仅存在于 Draft，Save 才写 canonical MIDI | PASS | `useMidiEditorDraft.ts` + Preview payload；Selection/Preview E2E 验证 Preview 不创建 Version |
| 单一模型/identity/conversion/save/history 实现 | PASS | TS model 仅 `midiEditorTypes.ts`，Python schema 仅 `midi_editor.py`；track/note identity、geometry、save、history 各有唯一 canonical 模块 |
| 生命周期清理 | PASS | `beforeunload`、keydown/keyup/blur 均 remove；Audio pause/src clear；RAF cancel；scratch DELETE；Project A→B Preview stop 的 BROWSER/TEST 证据 |
| path traversal | PASS | song id UUID validation + API tests；未发现任意路径读写路径 |

## Stage Matrix

| Stage | Status | Evidence | Missing | Severity |
|---|---|---|---|---|
| T34.0 Architecture | PASS | `CODE` `docs/MIDI_EDITOR_T34.md` contract 与当前 source of truth、tick、draft/save/version/preview 边界逐项一致；依赖审查无重复实现 | 无 | none |
| T34.1 Read Model/API | PASS | `CODE` `services/api/schemas/midi_editor.py`, `packages/music_core/midi/midi_editor_io.py`; `TEST` read API、重叠 note、velocity=0、drum、稳定 ID；`BROWSER` direct reload | 无 | none |
| T34.2 Save + Version | PASS | `CODE` `/midi/edit` + track write-back + version transaction；`TEST` save/preservation/409/concurrent same-base；`BROWSER` save vN+1/reload | 无 | none |
| T34.3 Editor Shell | PASS | `CODE` `MidiEditor`, selector/timeline/keyboard/viewport；`BUILD` 141 modules；`BROWSER` 5-track真实工程 | 无 | none |
| T34.4 CRUD + Snap | PASS | `TEST` add/delete/move/resize/velocity/snap；`BROWSER` Bass selection flow + Drum Add/Move/Resize/Delete/Velocity/Save/reload | 无 | none |
| T34.5 Zoom/Pan/Fit/Lock | PASS | `TEST` viewport limits/coordinates/lock；`BROWSER` H 195%、V zoom、scrollLeft/scrollTop>0 后 CRUD，lock mutation blocked | 无 | none |
| T34.6 Undo/Redo/Dirty/Save | PASS | `TEST` per-track history/dirty/rebase/save；`BROWSER` Undo/Redo、SPA/regenerate/restore/native beforeunload guards、one-save boundary | 无 | none |
| T34.7 Preview/Transport | PASS | `TEST` current/all Draft payload、scratch isolation、cleanup lifecycle；`BROWSER` Play/Seek/Loop/Stop、Project switch stop；`RUNTIME` scratch render | 无 | none |
| T34.8 Advanced Selection | PASS | `TEST` Set selection、box、batch history、clipboard/channel；`BROWSER` box/Ctrl+A/batch move/delete/velocity/copy/paste/duplicate/Undo | 无 | none |
| T34.9 AI-aware Piano Roll | PASS | `TEST` scale/chord/section/drum/bass context；`BROWSER` A(C major)→B(D minor)、GM rows、toggle、Save 后 MusicSpec 不变 | 无 | none |
| T34.10 Final Integration | PASS | `TEST` frontend 149/backend 697/build；`BROWSER` 6 T34 suites；`RUNTIME` FluidSynth 2.4.7；500/1000/3000 performance；legacy/bundle roundtrip | 无 | none |

统计：**PASS 11 / PARTIAL 0 / FAIL 0 / NOT_VERIFIED 0**。

## Critical Gates

| Gate | Status | Evidence |
|---|---|---|
| G1 MIDI 稳定读取为 MidiEditorDocument | PASS | Read API pytest + generated/legacy/imported Editor read + browser reload |
| G2 Track ID / Note ID / Tick / PPQ 稳定 | PASS | deterministic identity/FIFO pairing tests；integer tick schema；write/reload tests |
| G3 Note CRUD + Snap 正确 | PASS | geometry/draft tests + Bass/Drum browser CRUD |
| G4 Zoom/Pan 后坐标正确 | PASS | zoom-scroll geometry unit tests + Drum H/V zoom、双向 scroll 后 Add/Move/Resize；Selection E2E box/move |
| G5 Undo/Redo + Dirty 不丢数据 | PASS | per-track history tests + browser Undo/Redo/Discard/guards |
| G6 Save 新建 Version，旧 Version 不覆盖 | PASS | save/version tests + browser count +1/restore old/new |
| G7 baseVersionId / 409 conflict | PASS | API 409 + same-base concurrent 200/409；browser old Draft retained/current unchanged |
| G8 Preview 当前 Draft且正确 cleanup | PASS | payload contains draft IDs/velocity；Stop/unmount/project switch cleanup tests/browser |
| G9 Project/Version/Regenerate 不串状态 | PASS | keyed editor + reset；A→B→A、restore、regenerate guard E2E |
| G10 Manual Save → WAV stale | PASS | persisted server `audio_needs_render`; refresh remains stale; metadata not forged |
| G11 Re-render metadata 真实 | PASS | real FluidSynth 2.4.7 + GeneralUser-GS；non-fallback metadata and WAV SHA change |
| G12 Restore 恢复旧 MIDI | PASS | restore asset tests + browser vN↔vN+1、Editor/selection/history reset |
| G13 Drum channel/pitch/semantic | PASS | channel 9 read/save tests、GM label tests、真实 Drum CRUD/Preview/Save/reload E2E |
| G14 Multi-select/batch 不破坏 History | PASS | batch unit tests + browser uniform delta/one Undo/copy-paste IDs |
| G15 AI overlays 不修改 MIDI/MusicSpec | PASS | zero-save overlay E2E + Save 前后 MusicSpec deep equality |
| G16 Legacy Project / bundle 未破坏 | PASS | legacy layout migration/restore + manual-edit `.aimusic.zip` export/import/read |

统计：**PASS 16 / PARTIAL 0 / FAIL 0 / NOT_VERIFIED 0**。

## E2E Evidence

- **Flow A — Generate → Edit → Save：PASS。** `/create` 真实生成并进入 Workspace；Bass 的 CRUD/Snap/
  Velocity/Undo/Redo 由交互测试与 Chromium flows 共同覆盖；Save 只发一次请求，Version +1，重新 GET
  读到修改，MusicSpec 不变，旧版本仍可恢复。
- **Flow B — Preview Draft：PASS。** 未保存 Draft ID/velocity 出现在 Preview request；Current/All、Seek、
  Loop、Stop 均通过；Version/MIDI/formal WAV/renderer metadata 不被 Preview 改写，scratch 被清理。
- **Flow C — Advanced Editing：PASS。** 真实 box selection、Ctrl+A、统一 delta batch move、batch delete/
  velocity、copy/paste/duplicate；新 note ID 为 `draft:*`，一次批量 mutation 为一个 Undo step。
- **Flow D — Save → stale → render：PASS。** Save 后服务端与刷新后的 UI 都保持 stale；旧 renderer/
  SoundFont metadata 保留。真实产品链重新渲染后 WAV SHA-256 改变，stale=false，metadata 为
  `renderer=fluidsynth`, `is_fallback=false`, `soundfont_name=GeneralUser-GS`。
- **Flow E — Version Conflict：PASS。** vN Draft 与并发 vN+1 冲突返回 409；vN+1 未覆盖，Draft 保留，
  用户可 reload。并发 same-base API 测试只产生一个 v2（200 + 409）。
- **Flow F — Version Restore：PASS。** vN / manual vN+1 双向 restore；MIDI/Editor notes 恢复，draft/history/
  selection 清零，Preview 与 AI context 随 current document 重建。
- **Flow G — Project Isolation：PASS。** A 的 Draft/selection/history/lock/zoom/playhead/loop/preview/context
  不进入 B；切换后 A Preview 停止，返回 A 只加载 canonical saved state。
- **Dirty Guard：PASS。** SPA project navigation、Regenerate MIDI、AI Edit、Partial Regenerate、
  Auto Optimize、Apply Mix、Restore Version 与 browser refresh/close
  (`beforeunload.defaultPrevented=true`) 均不静默丢 Draft；track switch 保留 per-track Draft。

## Automated Tests

```text
Frontend unit: npm test
  PASS — 26 files / 149 tests

Frontend build: npm run build
  PASS — tsc + Vite, 141 modules transformed

Frontend lint:
  NOT_APPLICABLE — package.json 不存在 lint script，未伪造执行结果

Backend full: pytest -q
  PASS — 697 passed, 1 warning
  Warning: Starlette TestClient/httpx deprecation warning；非 T34 regression

T34 Playwright final isolated suite:
  PASS — 6/6
  midi-editor-final-regression
  midi-editor-music-context
  midi-editor-performance
  midi-editor-preview
  midi-editor-selection
  midi-editor-drum-crud
```

测试未 skip、未删除 assertion、未放宽产品 contract、未 mock Save/Version/MIDI 核心边界。

## Browser / Runtime Evidence

- **BROWSER PASS — Playwright Chromium/Desktop Chrome profile。** 六条 T34 suite 真实驱动页面与本地 API；
  覆盖 direct project refresh、Bass/Drum edit、zoom/pan、selection、Undo/Redo、Preview/Loop/Stop、Save、
  Version conflict/restore、dirty guards、A→B isolation。
- **BROWSER PASS — Codex in-app Chromium 可见 smoke。** 创建/生成、直接 URL reload（Editor 约 243ms
  可见）、Bass 114 notes、Drums 593 notes、H zoom 244%、V zoom/scroll、Undo/Redo、Preview/Loop/Stop、
  save v2、restore v1、Project A→B 均人工观察通过。
- **RUNTIME PASS — Real FluidSynth。** `C:\ProgramData\chocolatey\bin\fluidsynth.EXE`, runtime 2.4.7；
  `GeneralUser-GS.sf2` 32,319,396 bytes、valid=true。产品 `/audio/render` 两次均为 FluidSynth 非 fallback；
  manual edit 后 stale=true，重渲染后 false；WAV SHA 从
  `c1d849dec1469002a4775434a55aa8f8b446a1219ccd0233f49b0c7b0d4fab8c` 变为
  `f8adf6c62ac14d5a4d8d6d50814a81a0508b4348a316ef8601409166bac264b8`。

## Performance

环境：隔离 Playwright Chromium，程序化构造单 Bass track 500/1000/3000 notes；单位 ms。测量包含
浏览器/React/locator 等端到端开销，因此不与早期“纯 render <100/150/300ms”微基准直接等价；本次以真实
编辑是否可用为 gate，并记录所有原始数值。

| Notes | Initial | Zoom | Pan | Single edit | Select all | Batch velocity | Batch move | Undo | Preview | 结论 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 500 | 755.5 | 288.7 | 23.1 | 208.7 | 76.5 | 39.9 | 377.1 | 77.6 | — | usable |
| 1000 | 705.4 | 444.7 | 34.6 | 290.0 | 117.7 | 65.1 | 467.7 | 127.2 | — | usable |
| 3000 | 1015.2 | 948.1 | 79.0 | 610.7 | 250.9 | 139.7 | 864.0 | 298.7 | 180.6 | degraded but usable |

1000 notes 未达到“明显不可用”的 P1 门槛。3000 notes 的 zoom/batch move 约 0.8–1.0s，记录为
P2 性能/渲染策略优化候选；当前无需为 MVP 强制迁移 Canvas。

## Resolved Audit Blockers

以下缺陷在最终判定前已关闭，不计入 open P0/P1 数字，但保留审计轨迹：

### T34R-RESOLVED-01 — Version index 并发读写与 same-base Save 竞态

- **Severity at discovery：P0 candidate。** 并发读可能观察到空 `versions/index.json`；两个同 base Save
  的 check/write 若不原子，可能绕过冲突并互相覆盖。
- **Evidence：** 隔离 E2E 捕获过 JSON decode failure；新增并发 read/write 与 same-base 200/409 测试。
- **Root cause：** index 直接覆盖写，base check 与 create/save 不在同一事务。
- **Fix：** atomic replace + per-project striped `RLock` + `version_transaction` 包住 base check、MIDI write、
  create version 与 current update。
- **Regression：** 全量 697 passed；并发 save 只产生一个新 Version，结果 `[200, 409]`。

### T34R-RESOLVED-02 — Dirty Draft 可被部分 Workspace mutation/SPA navigation 静默丢弃

- **Severity at discovery：P1。** Editor 内只有 browser beforeunload/Discard，外层 project navigation、
  regenerate、restore 等 mutation 尚未统一读取 dirty。
- **Fix：** `onDirtyChange` 上提至 Workspace/Page；React Router blocker + mutation guard；discard 后 keyed
  remount；generate/regenerate/AI edit/partial regeneration/auto optimize/apply mix/restore 共用防护。
- **Regression：** final Playwright 覆盖 Continue Editing/Discard 两路，mutation 前 request count=0，
  browser beforeunload 可取消。

### T34R-RESOLVED-03 — 刷新后旧 WAV 被误标为 current

- **Severity at discovery：P1。** stale 原先只存在 React session；manual save 后刷新会把旧 WAV badge
  重新显示为“有”。
- **Fix：** Assets API 依据 `output.mid`/`soundfont.json` 与 `output.wav` mtime 返回持久可推导的
  `audio_needs_render`；前端每次 refresh 以服务端为准，成功 render 才清除。
- **Regression：** backend manual-save/soundfont-change tests、hook refresh test、final browser reload test；
  真实 FluidSynth 重渲染后 stale=false 且 WAV hash 改变。

## P0 Issues

**P0: 0（open）。** 支撑证据包括：save/version preservation、same-base concurrent 409、Project A/B
隔离、restore roundtrip、UUID path validation、完整 pytest 与浏览器 E2E。未发现可复现的永久数据丢失、
跨项目写入、旧版本覆盖或损坏 MIDI 成为 current。

## P1 Issues

**P1: 0（open）。** CRUD/geometry/history/dirty guards/preview cleanup/WAV stale/renderer metadata/
restore/1000-note normal editing 均有 TEST + BROWSER 或 RUNTIME 证据；审计发现的三项 blocker 已在最终
回归前关闭并列于上节。

## P2 Issues

1. **P2-01：3000-note SVG 交互退化。** 最终真实浏览器 zoom 948ms、batch move 864ms、single edit 611ms；
   仍可用，但若未来常态工程达到该规模，应增加真正的 viewport note virtualization 或评估 Canvas。
2. **P2-02：Version transaction 仅进程内。** 当前 `RLock` + atomic replace 对单 API 进程成立；如果未来
   以多 worker/多实例共享本地 projects 目录，same-base check/write 仍需要 OS file lock 或数据库事务。

## P3 Issues

1. **P3-01：旧只读 `features/midi/PianoRoll.tsx` 已无生产引用但仍保留。** 不影响当前 Editor，建议在
   后续维护清理中删除并同步移除仅为它保留的 analysis API/type surface。
2. **P3-02：Editor 内 Version Conflict / Discard 两个 Dialog 缺少 accessible name。** `role=dialog`
   与 `aria-modal` 已存在，但未像页面级 dirty dialogs 一样通过 `aria-labelledby` 关联标题；视觉与键盘按钮
   操作不受影响，建议后续补齐以改善读屏与 role/name 自动化定位。

## NOT_VERIFIED

1. **Native Microsoft Edge engine：NOT_VERIFIED。** 本次自动化使用 Playwright Chromium Desktop Chrome
   profile，人工可见 smoke 使用 Codex in-app Chromium；未另行执行 Edge channel。核心浏览器 gate 已由
   Chromium 双路径验证，因此该兼容性项不转为 PARTIAL。
2. **多 worker/多实例共享文件存储并发：NOT_VERIFIED。** 当前部署/测试为单 API 进程；该未来部署模式
   对应 P2-02，不是当前 T34 MVP 运行 contract。

`NOT_VERIFIED` 仅统计上述环境/未来部署项；T34 Stage 与 16 个当前核心 Gate 均有实际证据，故其矩阵的
NOT_VERIFIED 数仍为 0。

## Remaining Risks

- mtime stale 推导依赖文件系统时间顺序。当前 Windows/NTFS、bundle 与 restore 测试均通过；跨文件系统
  导入若保留异常未来时间戳，可能保守地继续显示 stale（不会把旧 WAV 错标为新 WAV）。
- Performance 数值受本机、Chromium、dev server 与测试定位开销影响，宜作为本次基线趋势而非硬件无关 SLA。
- 异步 render task 的进程内队列、MIDI EOF 未闭合 note、音乐质量模型等是全项目既有事项，不属于 T34
  Editor completion blocker。

## Final Verdict

```text
T34-R RESULT: PASS
T34 OVERALL: COMPLETED
P0: 0
P1: 0
T34-Fix phase required: NO
```

满足关闭规则：无 open P0/P1；16/16 Critical Gates PASS；frontend tests/build、backend full pytest、
核心 E2E、真实浏览器与真实 FluidSynth/SoundFont 链均通过。**MIDI Track Editor MVP 正式冻结。**
