# MIDI Track Editor 技术扫描与数据模型设计（T34.0）

> 阶段：T34.0（仅扫描与设计，不实现编辑功能）
> 主题：MIDI Track Editor —— 从 AI 生成到手工增删改 Note 的完整链路
> 本文档基于 `9aa7acc`（2026-08）代码实际扫描结果编写。

---

## 1. Current MIDI Architecture（当前 MIDI 架构）

### 1.1 生成链路（真实实现）

```text
MusicSpec (data/projects/{song_id}/music_spec.json)
  → packages/music_core/composer/music_composer.compose_music(spec)
  → CompositionResult
      ├─ bpm / ticks_per_beat=480 / total_bars / beats_per_bar
      └─ tracks: list[TrackEvents]
          ├─ track_id   (来自 MusicSpec TrackSpec.id，稳定字符串，如 "melody"/"bass_1"/
          │              divisi 派生 "xxx_divisa_a")
          ├─ name / role / instrument / channel / program / pan / cc_curve / cc11
          └─ notes: list[NoteEvent]  (pitch, start_beat:float, duration_beats:float,
                                      velocity, channel, is_drum)
  → packages/music_core/midi/midi_writer.write_midi(composition, output.mid)
      - tpb = composition.ticks_per_beat or 480
      - tick = round(beat * tpb)   ← 关键：beat→tick 用 int(round(...))
      - track 0: set_tempo + time_signature
      - 每轨: track_name / program_change / CC10 pan / CC11 expr / note_on/note_off / CC7 curve
      - drums (channel 9) 不写 program
  → save_midi_file(song_id, output.mid)  (写 data/projects/{song_id}/output.mid + metadata.json)
```

### 1.2 读取链路（真实实现）

```text
data/projects/{song_id}/output.mid
  → packages/music_core/analysis/midi_parser.parse_midi_to_notes(output.mid)
  → ParsedMidi
      ├─ ticks_per_beat / bpm / total_beats / total_bars
      └─ tracks: list[ParsedTrack]
          ├─ track_index (MIDI 轨道索引，不稳定) / track_name / channel
          └─ notes: list[ParsedNote] (pitch, pitch_name, start_beat:float,
                                      duration_beats:float, velocity, is_drum)
  → packages/music_core/analysis/piano_roll.build_piano_roll_data(parsed, spec, max_notes=5000)
  → JSON (ticks_per_beat, bpm, beats_per_bar, total_bars, total_notes, truncated, sections, tracks)
  → GET /api/v1/songs/{song_id}/piano-roll
  → apps/web/src/features/midi/PianoRoll.tsx（SVG 渲染）
```

### 1.3 关键事实

- **No JSON sidecar**：Note 数据不另存 JSON，`output.mid` 是唯一落盘资产（+ 各版本目录内副本）。
- **时间单位是 float beat**：`NoteEvent.start_beat` / `duration_beats`；`ParsedNote` 也换算回 beat
  （`round(start_tick / tpb, 4)`）。
- **track_id 是稳定字符串**：来自 `MusicSpec.tracks[].id`，write_midi 写入 `track_name`。
- **drums**：`DRUM_CHANNEL = 9`；`is_drum = (channel == 9)`；不写 program；pitch 即 GM 鼓音色号
  （kick=36, snare=38, closed_hihat=42…）。
- **PPQ**：固定 480（`DEFAULT_TICKS_PER_BEAT`），parser 保留文件实际 tpb。
- **truncation**：piano-roll 默认 `max_notes=5000`，超过标记 `truncated`。
- **track role 推断**：`_role_for_track` 用 `track_name` 与 `MusicSpec.tracks[].id` 前缀匹配。

---

## 2. Current Piano Roll Data Flow（当前 Piano Roll 数据流）

```text
ProjectWorkspacePage
  → features/workspace/useProjectWorkspace → songId (URL)
  → features/midi/PianoRollPanel.tsx（容器：songId / refreshKey 守卫）
  → features/midi/PianoRoll.tsx（SVG 渲染）
      useEffect → getPianoRoll(songId) [analysisApi]
      → PianoRollData {
          ticks_per_beat, bpm, beats_per_bar, total_bars, total_notes, truncated,
          sections[], tracks[] { track_index, track_name, role, min_pitch, max_pitch,
                                 notes[] { pitch, pitch_name, start_beat, duration_beats,
                                           velocity, is_drum } }
        }
  → 渲染：SVG rect（x = start_beat * px_per_beat, y = (maxPitch - pitch) * px_per_pitch）
```

- 当前 PianoRoll **只读**：无选中、无拖拽、无缩放/平移、无 playhead。
- 当前 Note 无 ID（React key = `track_index-ni`）。
- 当前 Track 前端标识 = `track_index`（渲染 key）+ `role`/`track_name`（筛选下拉）。

---

## 3. Canonical Editor Data Model（编辑模型）

### 3.1 设计原则

- **时间用 integer tick**（canonical），不使用 float beat：避免 `round(beat*tpb)` 往返精度丢失、
  便于 snap/undo/diff、符合 DAW 惯例。
- **Track 用稳定 id**（来自 MusicSpec track.id），绝不依赖 MIDI 轨道索引。
- **Note 用编辑器生命周期内稳定的 id**（加载时生成 UUID），不持久化（见 Sidecar 决策）。
- 字段以当前代码真实可用为准，不堆未用字段。

### 3.2 推荐模型（TS 形态）

```ts
// features/midi/editor/midiEditorTypes.ts（规划）
export interface MidiEditorNote {
  id: string;          // 加载时生成（crypto.randomUUID()），仅编辑器会话内稳定
  pitch: number;       // 0..127
  startTick: number;   // >= 0
  durationTick: number; // > 0
  velocity: number;    // 1..127
  channel: number;     // 0..15
  isDrum: boolean;     // 派生：channel === 9
}

export interface MidiEditorTrack {
  trackId: string;      // MusicSpec.track.id（稳定）
  name: string;
  role: string | null;
  instrument: string;
  channel: number;
  isDrum: boolean;
  program: number | null;
  pan: number | null;
  cc11: number | null;
  ccCurve: Array<{ beat: number; value: number }> | null;
  notes: MidiEditorNote[];
}

export interface MidiEditorDocument {
  songId: string;
  versionId: string;    // 当前版本（baseVersionId）
  ticksPerBeat: number; // PPQ（读取保留 / 生成 480）
  bpm: number;
  beatsPerBar: number;
  totalBars: number;
  tracks: MidiEditorTrack[];
}
```

后端对应 Pydantic 模型（`services/api/schemas/midi_edit.py`，规划）：`MidiEditorDocumentOut` /
`MidiEditorTrackOut` / `MidiNoteOut`；保存请求见 §9。

---

## 4. Time / PPQ Strategy（时间与 PPQ 策略）

### 4.1 时间模型

- **Canonical 时间单位：integer tick**。
- 换算公式（由 PPQ 与 BPM 推导）：
  - `tick = round(beat * ppq)`
  - `beat = tick / ppq`
  - `bar = floor(tick / (ppq * beatsPerBar))`；`beatInBar = floor((tick % (ppq*beatsPerBar)) / ppq)`
  - snap：`snappedTick = round(tick / snapTicks) * snapTicks`（snap 单位：1/4、1/8、1/16、1/32 拍 →
    `snapTicks = ppq / (snapDivisor)`）。
- 当前系统 NoteEvent/ParsedNote 用 float beat；编辑器只在**边界**转换（读取 beat→tick、
  写回 tick→beat），编辑会话内部一律 tick。

### 4.2 PPQ 策略

- **读取已有 MIDI**：保留文件实际 `ticks_per_beat`（parser 已支持）。
- **生成新 MIDI**：项目标准 `DEFAULT_TICKS_PER_BEAT = 480`。
- T34 不改全系统 PPQ。legacy 行为保持（写入时 `int(round(beat * tpb))`）。

---

## 5. Track Identity（轨道标识）

### 5.1 现状

- `MusicSpec.tracks[].id` 是稳定字符串（`melody`/`bass_1`/divisi 派生）。
- composer `TrackEvents.track_id = track.id`；write_midi 把 track_id 写入 `track_name`。
- parser / piano_roll 通过 `track_name` 前缀匹配回 role。

### 5.2 T34 策略

- **主标识 = MusicSpec track.id**（= MIDI `track_name`）。前端选择 Bass 后，保存时传
  `track_id`，后端用它定位 MIDI 轨道。
- 定位 MIDI 轨道：按 `track_name == track_id` 匹配（fallback：按 channel + role 推断）。
- 兜底：若某 MIDI 轨道名与任何 track.id 都不匹配（手动导入的 MIDI），编辑器在读取时为该轨道
  生成一个会话内 `editorTrackId`（如 `external_0`），保存时按**轨道索引**回写并记录映射。

---

## 6. Note Identity（音符标识）

### 6.1 方案评估

| 方案 | 优点 | 缺点 |
|---|---|---|
| UUID（加载时生成） | 简单、无并发 ID 碰撞；便于 selection/undo 引用 | 每次加载变化（会话级） |
| deterministic hash (pitch+start+track) | 可跨加载稳定 | 同位置多音符冲突；编辑后 hash 变 |
| persistent sidecar ID | 跨加载/版本 diff 稳定 | 引入 sidecar 复杂度（§19） |

### 6.2 T34 决策

- **编辑器加载时为每个 Note 生成 `crypto.randomUUID()`**（会话内稳定）。
- 不作为持久化身份；save 时不依赖 Note ID，而是发送**当前轨道完整 Note 列表**（见 §9/§10）。
- 因此不需要 sidecar 保存 Note ID。Undo/Redo/Selection 都在编辑器内存中以该 ID 引用。

---

## 7. Drum Model（鼓组模型）

- 底层保持 **pitch + channel**：鼓 Note 仍在 channel 9（`DRUM_CHANNEL`），pitch = GM 鼓音色号。
- `MidiEditorTrack.isDrum = (channel === 9)`；Note 上的 `isDrum` 派生。
- 编辑器 UI（T34.8）把 pitch 映射为鼓名：`36→Kick, 38→Snare, 42→Closed Hat…`
  （`DRUM_NOTES` 常量已存在）。T34.0 只定义模型，不实现鼓 UI。

---

## 8. Read Architecture（读取架构）

- **新增编辑器专用读取**：复用现有 parser，但返回 tick 语义。
- 建议新增 endpoint：`GET /api/v1/songs/{song_id}/midi/editor`
  → 返回 `MidiEditorDocument`（含 PPQ/BPM/beatsPerBar/totalBars/tracks/notes，tick 单位）。
  - 复用 `parse_midi_to_notes` + `build` 的 role/track_name 推断；把 `start_beat`→`startTick`
    （`round(beat*ppq)`），`duration_beats`→`durationTick`。
  - 保留现有 `piano-roll` endpoint 不动（只读展示仍用）。
- 前端 `features/midi/editor/useMidiEditor.ts` 加载 `MidiEditorDocument`；loading/error 处理。

---

## 9. Save Architecture（保存架构）

### 9.1 两种方案

| 维度 | A. 保存整个 document | B. 只保存被编辑 Track |
|---|---|---|
| 数据安全 | 全量覆盖，易丢并发修改 | 只碰目标轨，其他轨保持 |
| 并发 | 弱（后写全赢） | 仍需 baseVersionId 防冲突 |
| payload | 大（全曲 notes） | 小（单轨 notes） |
| 版本 | 简单 | 简单 |
| 实现复杂度 | 低 | 略高（需合并回 MIDI） |

### 9.2 T34 决策（MVP）

- **方案 B：只提交被编辑的 Track**。
- 请求：
  ```json
  POST /api/v1/songs/{song_id}/midi/edit
  {
    "track_id": "bass_1",
    "base_version_id": "v4",
    "notes": [
      { "pitch": 40, "start_tick": 1920, "duration_tick": 480, "velocity": 90, "channel": 2 }
    ]
  }
  ```
- 后端处理：`track_id` → 在**当前版本 MIDI** 中定位轨道 → 用请求 notes 替换该轨 note 事件 →
  保留 tempo/ts/program/pan/cc/其他轨 → 写新 `output.mid` → `save_midi_file` → 创建新版本
  （见 §11）→ 返回新版本 + assets。
- 前端行为：Save 成功 → 编辑器 draft 提交 → 全局刷新（versions/assets）+ `markAudioStale()`。

---

## 10. MIDI Round-trip Strategy（写回策略）

- **核心**：修改单轨后，读取当前版本 `output.mid` → 替换目标轨 note 事件 → 保留其他所有内容
  → 写新 `output.mid`。
- 实现要点（`packages/music_core/midi/midi_editor_io.py`，规划）：
  - 用 mido 解析当前 MIDI：逐轨保留 `track_name / program_change / CC10 / CC11 / CC7 / set_tempo /
    time_signature / end_of_track`。
  - 目标轨：丢弃其 note_on/note_off（同一 channel+note 的 FIFO 配对），用请求 notes 重新生成
    note_on/note_off（tick 直接写入，不再 `round(beat*tpb)`）。
  - 其他轨：原样保留全部 message。
  - 写回时保持 tpb 不变。
- 明确保留（当前 writer 实际写的）：set_tempo、time_signature、track_name、program_change、
  CC10 pan、CC11 expr、CC7 volume curve。这些在手动编辑后必须不丢失。

---

## 11. Version Integration（版本集成）

### 11.1 现状

- `create_version(song_id, music_spec, instruction, edit_spec)`：vN+1，写
  `version_metadata.json / music_spec.json / edit_spec.json / diff.json`，更新 current pointer，
  并把根目录资产复制进版本目录（`_sync_current_version_assets` → `copy_current_assets_to_version`
  → 复制 `output.mid / output.wav / audio_metadata.json / ...`）。
- `restore_version`：把版本目录资产复制回根目录（`restore_version_assets_to_current`），并
  更新 current pointer。MIDI/WAV 一并恢复。
- 自然语言编辑（`edit_song`）：新 spec → `create_version` → `_generate_midi_for` → 可选
  `_render_audio_for`。

### 11.2 T34 决策

- Manual MIDI Edit 保存 = 创建**新版本** vN+1，`kind="manual_midi_edit"`。
  - `music_spec` 不变（§14）。
  - `version_metadata.json` 追加：`source="manual_midi_edit"`、`track_id`、`track_role`。
  - 可选（MVP 不强制）：`added_notes/deleted_notes/modified_notes` 计数；建议加计数（成本低、
    便于版本列表展示），但不做逐音符 diff 存储。
  - instruction 默认 `"Manual MIDI edit: {track_role}"`，可带用户备注。
- Restore 天然兼容：恢复版本即恢复该版本 `output.mid`；编辑器 reload 该 MIDI。
- 前端协调：save 成功 → `refreshVersions()` + `reloadProject()` + `markAudioStale()`。

---

## 12. WAV Stale Integration（WAV 过期集成）

- **复用 T33.7 状态**：`useAudioAssets.markAudioStale()` 已存在并接入
  `useProjectWorkspace.handleMidiRegenerated/handleSoundFontChanged`。
- Manual MIDI Save 成功后：前端调用 `markAudioStale()`。
- 语义（不破坏既有规则）：
  - `selectedSoundFont` 不变；`renderedSoundFont`（`audio_metadata.soundfont_name`）不变。
  - `renderer / is_fallback / fallback_reason` 不变（它们只代表真实 WAV）。
  - 旧 WAV 仍可试听；UI 提示「MIDI 已修改，WAV 可能不是最新，请重新渲染」。
  - **不删除 / 不伪造旧 audio_metadata**。
- 重新渲染（`render_audio`）成功后 stale 清除 + metadata 更新（现有逻辑）。

---

## 13. Draft / Dirty Model（草稿与脏状态）

```text
savedNotes    = 最近一次成功 Save 后的轨道 notes
draftNotes    = 编辑器当前 notes（drag/resize/velocity 修改后的临时态）
dirty         = draftNotes !== savedNotes（deep compare by pitch/startTick/durationTick/velocity）
selectedNoteIds = Set<string>
```

- 交互：每次修改只改 `draftNotes`（内存），**不请求 API**。
- Save：提交 `draftNotes` 给后端；成功后 `savedNotes = draftNotes`。
- Discard / 切换 Track / 关闭：恢复 `savedNotes` 并提示未保存。
- 工程 A→B 切换：卸载编辑器并清空 draft（不提交）。

---

## 14. Undo / Redo Strategy（撤销重做）

- 方案比较：
  - **Snapshot history**：每次操作存全量轨道 notes 快照。简单可靠，轨内 note 数通常 < 几百，
    内存可接受。
  - **Command history**：Add/Delete/Move/Resize/Velocity 命令对象。更精细但实现复杂。
  - **Patch history**：增量 patch。中等复杂。
- **T34 决策：Snapshot history（轨道级）**。`useMidiHistory` 维护
  `Array<MidiEditorNote[]>` 栈（limit 如 50），`undo/redo` 直接替换 `draftNotes`。
  理由：MVP 简单可靠，轨道粒度足够（单轨编辑），避免命令系统的边界 bug。
- 数据模型已适配：操作都作用于 `MidiEditorNote[]`，可整体入栈。

---

## 15. Preview Architecture（试听架构）

### 15.1 方案评估

| 方案 | 延迟 | SoundFont 一致性 | 复杂度 | 离线 |
|---|---|---|---|---|
| A. Frontend WebAudio synth | 低 | 不一致（简音色） | 中 | 可 |
| B. Draft → 临时 MIDI → 后端 preview | 高（服务往返） | 一致 | 低-中 | 否 |
| C. Draft → 浏览器 MIDI 播放 | 低 | 系统音色 | 中 | 部分 |

### 15.2 T34 MVP 决策

- **方案 B：Draft → 临时 MIDI → 后端渲染 scratch preview**。
  - `POST /api/v1/songs/{song_id}/midi/preview`（body 同 save 的 notes，或整轨）→ 后端用**当前
    版本 MIDI + 请求轨道替换**写临时 MIDI → 用现有 renderer（当前 SoundFont 策略）渲染到
    scratch 路径（不写版本、不改 audio_metadata、不创建任务）→ 返回 `stream_url`。
  - 前端 `useMidiPlayback` 播放该 URL；`audio` 元素用普通 `<audio>`，不改任何 renderer 状态。
  - 延迟可接受：T34.7 才实现，且只在用户点播放时触发（非每次 mousemove）。
- **边界**：Preview 绝不修改 `renderer / is_fallback / fallback_reason / soundfont_name`；
  那些字段只代表真实已渲染 WAV。
- 可选增强（后续）：note 点击即时 WebAudio 短音（方案 A 局部），但非 MVP 门槛。

---

## 16. Frontend Architecture（前端架构）

基于 `features/midi/` 扩展 `features/midi/editor/`：

```text
features/midi/editor/
├─ MidiEditor.tsx            # 主容器：装配 toolbar/track selector/viewport/inspector
├─ MidiEditorToolbar.tsx     # undo/redo/snap/zoom/fit/播放
├─ TrackSelector.tsx         # 选择要编辑的轨道
├─ TimelineHeader.tsx        # bar/beat 标尺 + playhead
├─ PianoRollViewport.tsx     # 可滚动/缩放的 SVG viewport
├─ PianoKeyboard.tsx         # 左侧琴键
├─ NoteLayer.tsx             # 渲染 notes + 选择高亮
├─ NoteInspector.tsx         # 选中 Note 属性（pitch/start/duration/velocity）
├─ useMidiEditor.ts          # 加载 document + 当前轨道 + draft/dirty
├─ useMidiHistory.ts         # undo/redo 快照栈
├─ useMidiViewport.ts        # zoom/pan/fit
├─ useMidiPlayback.ts        # preview 播放
└─ midiEditorTypes.ts        # §3 模型
```

- 入口：`features/midi/PianoRollPanel.tsx` 增加「编辑」模式按钮，切换到 `MidiEditor`；
  只读模式保留现有 `PianoRoll.tsx`。
- 不创建空文件（T34.3 才建）。

---

## 17. API Proposal（接口规划，T34.1/T34.2 实现）

| 方法 | 路由 | 请求 | 响应 | 错误 |
|---|---|---|---|---|
| GET | `/api/v1/songs/{song_id}/midi/editor` | - | `MidiEditorDocument`（tick 语义） | 404 project_not_found；404 midi_not_found |
| POST | `/api/v1/songs/{song_id}/midi/edit` | `{track_id, base_version_id, notes[]}` | `{version_id, music_spec, assets, warnings}` | 404 project/track/midi；409 version_conflict；422 invalid_note |
| POST | `/api/v1/songs/{song_id}/midi/preview` | `{track_id, notes[]}` | `{stream_url, warning?}` | 404 midi/track；422 invalid_note |

错误格式遵循现有 `ApiRequestError` / `errors.py` 契约（`error.code/message/details`）。

- 409 触发条件：请求 `base_version_id != 当前 current_version_id` → `version_conflict`，
  message 含当前版本；前端提示「工程已更新到 vN，请刷新后再编辑」。
- 422 校验：pitch 0..127、velocity 1..127、startTick>=0、durationTick>0、channel 0..15、
  轨道存在、notes 数上限（如 10000）、无 NaN、track_id 合法。

---

## 18. Legacy Compatibility（旧工程兼容）

- **Sidecar 决策 = NO**（见 §19），因此旧工程无额外数据依赖。
- 旧工程打开：编辑器从 `output.mid` + `music_spec.json` 完全重建（无需任何新文件）。
- 旧 bundle 导入（`.aimusic.zip`）：现有 bundle 已含 `versions/vN/output.mid`，导入后编辑器
  可直接读当前版本 MIDI。无需改 bundle。
- 无 MIDI 的工程（仅 MusicSpec）：编辑器显示 Empty State「先生成 MIDI」。

---

## 19. Sidecar 决策

**Sidecar：NO（MVP 不需要 `midi_editor.json`）**

理由：
1. 编辑器所需的全部数据（notes/tempo/ts/PPQ/track identity）都可从 `.mid + music_spec.json`
   重建；Note ID 是会话级的，不需要持久化。
2. Save 发送完整轨道 notes，后端合并回 MIDI；版本恢复直接恢复 `output.mid`——不需要 sidecar
   保证正确性。
3. 避免 bundle/import/legacy 三处都要迁移 sidecar，显著降低复杂度与兼容风险。
4. 未来若需要跨加载 Note ID 稳定 / 版本间音符级 diff，再评估 sidecar（记录为已知取舍）。

---

## 20. Project Bundle（工程打包）

- 当前 `.aimusic.zip` 含 `versions/vN/output.mid / music_spec.json / audio_metadata.json` 等。
- T34 不加 sidecar → bundle **无需改动**；导出/导入天然携带手动编辑后的 MIDI。
- legacy import：无新文件依赖，直接可用。

---

## 21. WAV Stale Integration（详见 §12）与 Restore Version

- Restore 后：`restore_version_assets_to_current` 恢复该版本 `output.mid / output.wav /
  audio_metadata.json` → 前端 reload 编辑器（读回该版本 MIDI）、draft 清空、
  `markAudioStale()` 按真实 metadata 重新计算（若恢复的 WAV 存在且 metadata 匹配，则不算 stale）。
- 前端：`handleVersionRestored` 触发 `reloadProject + refreshVersions + reloadMidiEditor + refreshAudio`。

---

## 22. Performance Budget（性能预算）

| 指标 | 目标（T34.10 验证） |
|---|---|
| 500 Notes 渲染 | < 100ms，60fps 交互 |
| 1000 Notes 渲染 | < 150ms，60fps 交互 |
| 3000 Notes 渲染 | < 300ms，30fps 交互可接受 |
| 选择/拖拽/缩放/平移 | 交互时无明显卡顿（>=30fps） |

- 当前 composer 典型规模：几轨 × 几十到几百 note（~200-1500 note），在 SVG 预算内。
- Piano Roll 渲染策略：**继续 SVG**（viewport 只渲染可视窗口内的 note），仅在 3000+ note
  明显不达标时才评估 Canvas（T34.10 决定）。
- 现有 `PianoRollData.truncated`（5000 上限）与编辑器读取分离：编辑器读取**不截断**（或
  单轨上限 10000），保证编辑完整。

---

## 23. Frontend Architecture（前端架构）（§16 已覆盖）

## 24. API Proposal（接口规划）（§17 已覆盖）

## 25. Risk Matrix（风险矩阵）

| # | 风险 | Mitigation |
|---|---|---|
| R1 | Track identity 不稳定 | 主用 MusicSpec track.id（稳定）；external 轨道会话内 editorTrackId + 索引回写 |
| R2 | Note identity 不稳定 | 会话级 UUID；save 发完整轨道 notes，不依赖 ID |
| R3 | MIDI round-trip 丢 event | 只替换目标轨 note 事件；保留全部 meta/CC/其他轨；测试覆盖 |
| R4 | PPQ/tick 错误 | 读取保留 tpb；写回同 tpb；beat↔tick 只在边界转换 |
| R5 | Drum channel 被破坏 | channel 9 轨道 isDrum，不写 program；编辑保持 channel |
| R6 | Manual Edit 与 Composer 冲突 | 不反向改 MusicSpec、不重跑 composer；每次编辑生成新版本（可回退） |
| R7 | Save 覆盖新版本 | baseVersionId + 409 version_conflict |
| R8 | Version restore 与 Editor 不一致 | restore 后强制 reload 编辑器 + 清 draft |
| R9 | WAV stale 状态错误 | 复用 markAudioStale；不伪造/删除 audio_metadata；以 is_fallback 为准 |
| R10 | Preview 被误当正式 renderer | preview 用 scratch 路径，不改任何 renderer/audio_metadata 字段 |
| R11 | 长曲目性能 | SVG 可视窗口裁剪 + note 数量上限；T34.10 压测再决定 Canvas |
| R12 | 旧项目兼容 | 无 sidecar；全部从 .mid+spec 重建 |

---

## 26. T34.1-T34.10 Plan（切片计划）

| Slice | Goal | Depends | Scope | Non-goals | Acceptance |
|---|---|---|---|---|---|
| **T34.1** Editable Note Model + Read API | 新增 `midiEditorTypes`（前后端）+ `GET /midi/editor` | T34.0 | 后端 editor 读取模型 + 前端类型；tick 语义 | 无编辑 UI | build + 单测：read 返回 tick notes |
| **T34.2** Save API + Version Integration | `POST /midi/edit` 创建 vN+1（kind=manual_midi_edit）+ MIDI 写回 + baseVersionId 409 | T34.1 | 单轨替换写回、版本创建、WAV stale 联动 | 无 UI | 单测：edit 后 MIDI 保留他轨；409；restore 恢复 |
| **T34.3** Editor Shell + Track Selector | `features/midi/editor/` 壳 + 轨道选择 + 加载 document | T34.1/2 | 编辑器容器、轨道下拉、loading/error | 编辑操作 | build + smoke：可加载并切换轨 |
| **T34.4** Note CRUD + Snap | 点击添加、删除、拖移、resize、snap | T34.3 | draft 修改、snap、选中高亮 | undo/redo | smoke：增删改 + snap |
| **T34.5** Zoom / Pan / Fit / Lock | viewport 缩放平移、fit、轨道锁 | T34.4 | SVG 可视窗口、标尺 | 播放 | smoke：缩放平移 |
| **T34.6** Undo / Redo / Dirty / Save | 快照栈、dirty 标记、save/discard | T34.4 | useMidiHistory + save 流程 | 高级选择 | 单测：undo/redo/dirty |
| **T34.7** Preview / Transport / Loop | Draft preview（§15 方案 B）+ play/loop | T34.5 | preview endpoint + 播放条 | 不影响正式 renderer | smoke：preview 播放 |
| **T34.8** Advanced Selection | 框选、多选、velocity 批量、鼓名映射 | T34.6 | 选择语义 + NoteInspector | AI | smoke |
| **T34.9** AI-aware Piano Roll | 复用生成提示辅助编辑（如“这段更密集”） | T34.8 | 轻量 AI 建议 | 不在 MVP | 可选 |
| **T34.10** Final Regression | 性能压测 + 全链路回归 + 文档 | T34.1-9 | build/test/smoke/性能 | - | 性能预算达标；功能无回归 |

---

## 27. T34.0 Final Decisions

```text
Canonical time unit:        integer tick（编辑器内部）；beat 仅在读写边界转换
PPQ strategy:               读取保留文件实际 tpb；生成/写回用项目标准 480；不改全系统 PPQ
Track ID strategy:          MusicSpec.track.id（稳定）；MIDI track_name 与之匹配；external 轨道
                            用会话内 editorTrackId + 索引回写
Note ID strategy:           加载时 crypto.randomUUID()（会话级）；save 发完整轨道 notes，不依赖 ID
Editor source of truth:     output.mid（当前版本）+ music_spec.json 重建；无 JSON note sidecar
Sidecar required:           NO（MVP）
Save granularity:           只保存被编辑的 Track（track_id + 完整 notes + base_version_id）
Version strategy:           Manual MIDI edit 保存 = 创建 vN+1（kind=manual_midi_edit，
                            music_spec 不变，metadata 记 track_id/role + 可选计数）
Version conflict strategy:   baseVersionId 与当前版本比对，不一致 → 409 version_conflict
MIDI write-back strategy:   读取当前版本 MIDI → 替换目标轨 note 事件 → 保留 tempo/ts/program/
                            pan/cc/其他轨 → 写回同 tpb
MusicSpec mutation:         Manual MIDI Edit 不反向修改 MusicSpec、不重跑 composer
WAV stale strategy:          save 成功 → markAudioStale()；保留旧 WAV 与 audio_metadata；
                            renderer/is_fallback/soundfont_name 只代表真实 WAV
Preview strategy:           方案 B：Draft → 临时 MIDI → 后端 scratch preview（不改 renderer 状态）
Piano Roll rendering:       继续 SVG（可视窗口裁剪）；3000+ note 不达标再评估 Canvas（T34.10）
Drum strategy:              channel 9 + pitch（GM 鼓音色号）+ isDrum；不写 program；鼓 UI 留 T34.8
Legacy compatibility:        无 sidecar → 旧工程/旧 bundle 直接从 .mid + spec 重建，无需迁移
```

---

## 28. 验证

- `npm run build`：PASS（143 modules）
- `pytest tests/test_midi_writer.py tests/test_midi_parser.py tests/test_versions_api.py
  tests/test_generate_midi_api.py`：28 passed
- 本阶段无代码修改（纯设计文档）。

---

## 29. 遗留 / Known Trade-offs

- Note ID 为会话级：跨加载的版本间音符 diff 不可直接按 ID 关联（可用 pitch/start 启发式）。
- preview 有服务往返延迟；MVP 接受，后续可加 note 点击即时音。
- 手动编辑 MIDI 与 MusicSpec 分离：重新生成（generate-midi）会覆盖手动编辑（回到 composer
  输出）；用户需在编辑后「保存」为版本，或用 regenerate 重建。文档明确这一行为。

---

## 30. T34.1 实现记录（Completed）

> 实现与 T34.0 Final Decisions 的唯一差异：
> **Note ID 从「会话级 UUID」改为 deterministic hash（跨读取稳定）**。
> Decision changed because：T34.1 §8 要求同一未修改 MIDI 重复读取时 Note ID 稳定，
> 以便 selection / undo / diff；UUID 每次读取变化，无法满足。实现为
> sha1(track_name|channel|pitch|start_tick|occurrence)[:16]，同位置连续 note 用出现序号区分。

### 30.1 最终 API

`	ext
GET /api/v1/songs/{song_id}/midi/editor
→ MidiEditorDocument（只读）
404 project_not_found / midi_not_found（工程未生成 MIDI）
400 invalid_request（MIDI 解析失败 / 非法 song_id）
`

### 30.2 最终 Pydantic Models（services/api/schemas/midi_editor.py）

- MidiEditorDocument: song_id, version_id?, ppq(>0), bpm?, time_signature, total_bars, tracks[]
- MidiEditorTrack: id, role?, name, channel(0..15), instrument?, is_drum, notes[]
- MidiEditorNote: id, pitch(0..127), start_tick(>=0), duration_tick(>0), velocity(1..127), channel(0..15)

### 30.3 最终 TS Types（apps/web/src/features/midi/editor/midiEditorTypes.ts）

camelCase 镜像后端：MidiEditorDocument / MidiEditorTrack / MidiEditorNote。

### 30.4 Track ID 实现

- 优先 MusicSpec.tracks[].id（MIDI track_name 精确或 divisi 前缀 {id}_ 匹配）。
- 无法匹配 → ext_{track_index}（external 轨道，按 MIDI 轨道索引稳定）。

### 30.5 Note ID 实现

- deterministic：sha1(track_name|channel|pitch|start_tick|occurrence)[:16]。
- 同 (channel, pitch, start_tick) 连续 note 用出现序号区分（FIFO 配对，与现有 parser 一致）。

### 30.6 Legacy behavior

- 无 sidecar；直接从 output.mid + music_spec.json 重建 → 旧工程自动兼容。
- 无 MIDI 工程 → 404 midi_not_found（不自动生成、不伪造）。

### 30.7 Parser limitations

- 每个 track 最多 10000 notes（防滥用）。
- 未配对 note_off 忽略（不崩溃）。
- tempo 取文件首个 set_tempo；bpm = round(60M/tempo)。
- time_signature 取首个；denominator 固定 4 显示（与现有 parser 一致）。
- 非 note 事件（program_change/CC/meta）读取时保留在解析过程，但 editor document 当前不暴露；
  T34.2 写回时将以「读取当前 MIDI 保留其他事件」策略保证不丢失。

### 30.8 文件清单

- 后端：services/api/schemas/midi_editor.py（模型）、
  packages/music_core/midi/midi_editor_io.py（读取适配）、
  services/api/routes/songs.py（route）
- 前端：eatures/midi/editor/midiEditorTypes.ts、midiEditorApi.ts、
  useMidiEditorDocument.ts、index.ts、midiEditorApi.test.ts
- 测试：	ests/test_midi_editor_api.py（11 用例）

### 30.9 验证

- 
pm run build：PASS
- 
pm test：23 passed（含 5 个新 editor 测试）
- 后端：	est_midi_editor_api.py 11 passed；MIDI/version 回归 31 passed
- 真实 composer MIDI smoke：5 tracks（melody/harmony/bass/drums/pad），drums ch9 is_drum，
  tick 语义正确；track/note ID 跨两次读取稳定（1241 notes）

---

## 31. T34.3 Editor Shell（Completed）

### 31.1 Workspace integration

- /projects/:songId → WorkspaceDashboard 的 Piano Roll 区（PianoRollPanel）。
- PianoRollPanel 保留「无 MIDI → EmptyState + 生成 MIDI 按钮」逻辑；当 hasMidi 为真时，
  渲染新的只读 MidiEditor（替代旧 PianoRoll）。
- 数据流：PianoRollPanel → MidiEditor → useMidiEditorDocument(songId) → getMidiEditorDocument
  （T34.1 Read API）。

### 31.2 Component structure（features/midi/editor/）

`	ext
MidiEditor.tsx           # 顶层组合：selector + timeline + keyboard + viewport + footer
TrackSelector.tsx        # 轨道选择（canonical track.id，role 辅助显示，notes 计数）
TimelineHeader.tsx       # bar 编号（PPQ + time signature）
PianoKeyboard.tsx        # 左侧琴键（只标 C/octave）
PianoRollViewport.tsx    # 只读音符视图（tick→x, pitch→y, note.id key, 点击高亮）
midiEditorLayout.ts      # 纯函数：tickToX/tickToWidth/pitchToRow/ticksPerBar/...
`

### 31.3 Track selection semantics

- **默认轨道规则（确定性）**：若 selectedTrackId 仍存在于当前 document → 保持；否则选择
  **第一个有 Notes 的轨道**；若全部为空 → 第一个轨道。
- **切换**：仅更新本地 selectedTrackId state（O(1)），不重新 fetch document。
- songId / document 变化 → 清空 selectedNoteId + 按规则重选轨道。

### 31.4 Read-only Piano Roll

- X = startTick * pixelsPerTick；宽度 = durationTick * pixelsPerTick（canonical tick 不变）。
- Y = pitchToRow(pitch, maxPitch) * rowHeight（higher pitch 在上方；由 pitch 决定，非数组序）。
- 初始 fit：按当前 Track notes 计算 computePitchRange（min/max + 25% padding）+ computeMaxTick。
- React key / data-note-id = **note.id**（canonical）。
- 点击 note → 单选高亮 + footer 显示 pitch/bar/beat/velocity（只读，非编辑）。
- 空 Track 可选择并显示「当前轨道没有音符」。

### 31.5 PPQ / meter

- 全部经 midiEditorLayout.ts 纯函数：	icksPerBar = numerator * ppq（4/4 → 1920；3/4 → 1440），
  	ickToBar 1-based，isibleBarCount 至少 4 小节。
- time signature 来自 document（缺省 [4,4]）。

### 31.6 Empty / loading / error

- 无 MIDI（
otFound）→ EmptyState「尚未生成 MIDI，生成 MIDI 后即可查看各轨道」。
- loading → LoadingState；error → ErrorState + 重新加载；songId 变化旧数据立即失效（hook abort）。

### 31.7 Version / regenerate refresh

- efreshKey 变化（MIDI 重新生成 / 版本恢复）→ eload() 重新加载 document，并按新 document
  重选轨道、清空 note 选择。未使用 window.reload。

### 31.8 Old Piano Roll treatment

- 旧 eatures/midi/PianoRoll.tsx 不再被 PianoRollPanel 引用（T34.1 后保留文件；
  待 T34.6+ 确认无引用后删除）。旧 piano-roll endpoint 仍保留供其他只读用途。

### 31.9 Drum display

- drums 轨道正常显示 Notes（channel 9 / is_drum 正确）；pitch 行显示（36→Kick 等语义 UI 留 T34.9）。

### 31.10 Known limitations

- 无缩放/平移（T34.5）；无编辑/undo（T34.4/34.6）；无 preview（T34.7）。
- selectedTrackId 为本地 state（不写 URL / project）。

### 31.11 Files

- 新增：eatures/midi/editor/{MidiEditor,TrackSelector,TimelineHeader,PianoKeyboard,PianoRollViewport,midiEditorLayout}.tsx/ts、
  MidiEditor.test.tsx、PianoRollViewport.test.tsx、midiEditorLayout.test.ts
- 修改：eatures/midi/PianoRollPanel.tsx（挂载 MidiEditor）、
  eatures/midi/editor/index.ts、styles/workspace-structure.css（editor 样式）
- 未改：后端、Composer、MIDI writer、Version、FluidSynth、MusicSpec。

### 31.12 Verification

- 
pm test：44 passed（含 13 个新 editor/坐标测试）
- 
pm run build：PASS（133 modules）
- 真实电子工程 smoke：5 tracks（melody/piano/bass/drums/pad），bass pitch 36-52（E1-G2），
  drums ch9 is_drum，bass 114 notes tick 定位正确；dev server 路由 200

---

## 32. T34.4 Note CRUD + Snap + Draft Editing（Completed）

### 32.1 Draft architecture

- useMidiEditorDraft(document) 管理 draftNotesByTrack（每轨道独立 session draft）+ savedByTrack。
- document（songId/version/reload）变化 → draft 重置为 saved。
- 所有编辑走 immutable update（只改目标轨道 draft），**不触碰 document / saved / backend**。
- 
otesDirty(saved, draft) 判定 dirty（dirtyTracks 集合）。

### 32.2 New note defaults

- 双击空白 Grid → 新 Note：pitch = clicked row、startTick = snapped click tick、
  durationTick = snap unit、elocity = 90（DEFAULT_NEW_NOTE_VELOCITY）、channel = track.channel。
- 边界：pitch 0..127、start>=0、duration>0、velocity 1..127（clamp）。

### 32.3 Temporary Note ID

- 新 Note：draft:（session 唯一、React key 稳定、拖动期间不变）。
- 已有 Note：沿用 T34.1 canonical id。后端 Note ID contract 未改。

### 32.4 Selection / interactions

- 单选：点击 Note 高亮；点击空白取消；双击空白新增。
- 拖动 Note 主体 → Move（startTick + pitch）；右边缘 handle → Resize（durationTick）。
- Delete/Backspace 删除选中（输入框聚焦时由 isEditableTarget 守卫不误删）。
- Pointer Events + setPointerCapture（jsdom 下 guard），drag threshold 3px，
  commit-on-pointerup 语义（一次拖动=一次逻辑操作，为 T34.6 undo 铺垫）。

### 32.5 Snap model

- getSnapTicks(ppq, snap)：1/1=4*ppq、1/2=2*ppq、1/4=ppq、1/8=ppq/2、1/16=ppq/4、1/32=ppq/8；
  off=1。全部 integer（round）。
- snapTick(tick, snap, ppq)：absolute snapping（MVP）。
- Move 量化 startTick；Resize 先 snap endTick 再反推 duration；Add 量化 startTick。
- Snap off 仍保留 integer tick（不强制落 1/16 网格）。

### 32.6 Track / Project isolation

- 轨道切换：draftNotesByTrack 保留各轨道 draft（Bass→Melody→Bass 修改仍在）。
- songId/document reload：draft 重置（不清到新 version 的旧 draft）。
- 编辑只限定 selectedTrackId（Bass 修改不影响 Melody）。

### 32.7 Known limitations（T34.5/34.6+）

- Undo/Redo、Save UI、Version creation、Dirty guard、Zoom/Pan/Fit/Lock、Preview/Loop、
  Multi-select、Copy/Paste、Velocity lane、Drum semantic names（均未实现）。

### 32.8 Files

- 新增：midiEditorGeometry.ts（snap + pointer 坐标 + note name）、
  useMidiEditorDraft.ts（draft CRUD）、MidiEditor.tsx 升级（snap 工具栏 + velocity inspector +
  键盘守卫）、PianoRollViewport.tsx 升级（双击添加/拖动/resize/网格 subdivision）。
- 测试：midiEditorGeometry.test.ts、useMidiEditorDraft.test.ts、
  PianoRollViewport.interaction.test.tsx、MidiEditor.keyboard.test.tsx。
- 未改后端。

### 32.9 Verification

- 
pm test：69 passed（新增 snap/add/delete/move/resize/velocity/boundary/scroll/隔离/reload/键盘）
- 
pm run build：PASS（135 modules）
- 编辑过程中无 save/version/render 请求（代码审计确认 0 调用）；真实工程只读 smoke：bass 114 notes，
  assets/version 稳定。

---

## 33. T34.5 MIDI Editor Viewport：Zoom / Pan / Fit / Track Lock（Completed）

### 33.1 Viewport state

- useMidiViewport()：pixelsPerTick（H 缩放）、owHeight（V 缩放）、scrollLeft/scrollTop。
- canonical MIDI 数据（tick/pitch）永不被缩放修改；zoom 只影响视觉映射。
- 100% = DEFAULT_LAYOUT（pixelsPerTick=0.4、rowHeight=12）。

### 33.2 Zoom limits / anchor

- H：MIN_HORIZONTAL_ZOOM=0.25x ~ MAX_HORIZONTAL_ZOOM=4x（相对默认）。
- V：MIN_ROW_HEIGHT=6 ~ MAX_ROW_HEIGHT=28。
- 工具栏 [-]/[+]（H/V）+ 百分比/Row 显示；Ctrl/Cmd+Wheel → H zoom（以鼠标指向 tick 为 anchor，
  通过保持 scrollLeft 相对位置近似）；Shift+Wheel → 横向滚动；普通 Wheel → 纵向滚动。

### 33.3 Pan

- 普通 horizontal/vertical scrollbar；Space + Pointer Drag → pan（grid 上 is-pan cursor grab）。
- pan 模式优先于 add/move/resize；pointercancel / window blur / unmount 结束 pan。

### 33.4 Zoom/Pan 后坐标正确性

- 统一使用现有 geometry：pointer 坐标经 	oGridRelative(client, rect, scrollLeft, scrollTop,
  keyboardWidth) → 相对 grid 内容 → / layout.pixelsPerTick → snap → tick；/ rowHeight → pitch。
- 动态 layout 传入 computeViewNotes 与交互 handler，因此 zoom/scroll 下 Add/Move/Resize 坐标正确。

### 33.5 Fit Track

- itTrack(notes, ppq, meter, w, h)：计算 first/last tick 与 min/max pitch + padding；
  设置 H zoom（受 min/max 约束，避免单 note 占满屏幕）、rowHeight、scrollLeft/Top。
- Empty Track：用默认时间范围 + 通用 pitch range，不报错、无 NaN/Infinity。

### 33.6 Track Lock

- lockedTrackIds: Set<string>（editor session 内，不写 project/backend）。
- Lock 阻止：Add/Delete/Move/Resize/Velocity（handler 层，非仅 CSS）；Velocity input disabled。
- Lock 允许：Select / Zoom / Pan / Fit / Track switch / Inspector。
- Lock 保留已有 Draft（不 discard/save）。

### 33.7 Reset

- document/songId 变化 → 清 lockedTrackIds、selectedNoteId、iewport.resetZoom()。
- Space 键按 editor 局部监听，window blur 清除。

### 33.8 Files

- 新增：useMidiViewport.ts + useMidiViewport.test.ts、MidiEditor.lock.test.tsx。
- 升级：PianoRollViewport.tsx（lock/pan/zoom wheel/scroll 回调）、MidiEditor.tsx
  （viewport hook + zoom/fit/lock 工具栏 + space pan）、workspace-structure.css、index.ts。
- 未改后端 / composer / writer / version。

### 33.9 Verification

- 
pm test：80 passed（zoom limits/percent/fit/empty fit/单 note fit 有界；lock 阻止
  delete/velocity、保留 draft；既有 CRUD/坐标/隔离回归全绿）
- 
pm run build：PASS（136 modules）
- 编辑过程无 save/version/render 请求；dev server 200

---

## 34. T34.6 Undo / Redo + Dirty + Save + Version Integration（Completed）

> 注意：T34.2 的 Save API 在代码库中**原本缺失**（只有 T34.1 读取）。本阶段按 T34.0 Final
> Decisions 补齐了后端 POST /api/v1/songs/{song_id}/midi/edit（写回 + 版本 + 409）。

### 34.1 History（per-track snapshot）

- useMidiEditorDraft 内置 per-track undo/redo（快照栈，上限 80）。
- 每个逻辑操作（含一次完整 Drag）只产生一个 undo step：
  - ecordBefore 在变更前记录 before；commitEdit（pointerup）清除 pending。
  - 拖拽期间多次 moveNote/resizeNote 共享同一个 pending before → 一次 undo。
- Undo/Redo：Ctrl/Cmd+Z、Ctrl/Cmd+Shift+Z、Ctrl+Y；按钮 disabled 按栈空判定。
- 输入框聚焦时（isEditableTarget）不触发快捷键。

### 34.2 Dirty semantics

- dirty = draftNotes 与 saved baseline 不一致（深度比较）。
- Undo 回 baseline → dirty=false；Redo → dirty=true；Save → dirty=false。
- dirtyTracks: Set<trackId> 支持多轨道独立 dirty。

### 34.3 Save lifecycle

- Save 调 saveMidiEditorTrack(songId, {trackId, baseVersionId=document.versionId, notes})。
- 成功：后端创建新版本（kind=manual_midi_edit）→ reload document → draft hook 自动重置
  （canonical notes + history 清空 + dirty=false + temp IDs 被 canonical 替换）→ onSaved
  回调 → Workspace markAudioStale() + refresh assets/versions。
- 失败：Draft/dirty/history 保留，显示可重试错误。
- 409 version_conflict：不覆盖 Draft，弹窗「重新加载最新版本 / 继续查看草稿」。
- 防重复提交（saving 状态禁用）。

### 34.4 Discard

- 二次确认后 discardTrack(trackId)：draft=saved、history 清空、selection 清、dirty=false；不调后端。

### 34.5 Guards

- eforeunload：仅 dirty 时注册（浏览器原生离开保护）。
- Project/Regenerate/Restore：SPA 导航会触发 document 变化 → draft 自动重置；浏览器离开由
  beforeunload 保护。

### 34.6 Version boundary / WAV stale

- Save 是 history boundary（Save 后不可 Undo 跨版本；回旧版用 Version Restore）。
- Save 后 WAV stale（markAudioStale）；不自动 Render；renderer/SoundFont/is_fallback 保持真实。

### 34.7 Track Lock 兼容

- Locked 阻止新 note mutation；已有 dirty Draft 仍可 Save/Discard/Undo/Redo（Lock 不阻止
  Draft 管理）。

### 34.8 Files

- 后端：midi_editor_io.write_midi_editor_track（替换目标轨 note、保留他轨/meta）、
  schemas/midi_editor.py（SaveRequest/Response）、outes/songs.py（POST /midi/edit + 409 +
  版本）、errors.py（VERSION_CONFLICT）。
- 前端：midiEditorApi.ts（saveMidiEditorTrack）、useMidiEditorDraft.ts（history/dirty/
  discard/rebase）、MidiEditor.tsx（Undo/Redo/Save/Discard/conflict/dirty/beforeunload）、
  PianoRollPanel.tsx（onMidiSaved）、WorkspaceDashboard.tsx/ProjectWorkspacePage.tsx
  （onMidiSaved → markAudioStale）。
- 测试：	est_midi_editor_save_api.py（7）、useMidiEditorDraft.history.test.ts（9）。

### 34.9 Verification

- 后端：	est_midi_editor_save_api.py 7 passed；MIDI/version 回归 34 passed。
- 前端：Vitest 89 passed；npm build 通过（136 modules）。
- 真实 smoke：save→v2（≠v1）、bass pitch 36→37、stale base→409、has_audio=false、current=v2。
