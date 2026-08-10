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
