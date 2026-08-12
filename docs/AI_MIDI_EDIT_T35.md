# T35 — AI-assisted MIDI Editing 架构与 Contract 冻结

> 状态：T35 started；T35.0 Architecture Scan completed；T35.1 next  
> 日期：2026-08-12  
> 范围：SCAN + DESIGN + FREEZE CONTRACT。本文不实现 API、Plan runtime、Transformer、Proposal runtime、
> AI MIDI UI、Prompt、Apply 或 Proposal Preview。  
> 编号说明：仓库历史路线图已使用过“T35 生成链路日志”。本文的 T35 是接续 T34 MIDI Track Editor
> 的 **AI MIDI Editor 子序列**；状态文档统一写作 “T35 AI-assisted MIDI Editing”，避免与历史任务混淆。

## 0. Executive Summary

T35 不建立第二套 MIDI Editor，也不让 LLM 直接编辑 MIDI。最终链路冻结为：

```text
User Instruction
        ↓
validated MidiEditScope + T34 session Draft
        ↓
backend AiMidiEditContext
        ↓
existing LLMProvider.generate_structured
        ↓
MidiEditPlan
        ↓
non-LLM Plan Validation
        ↓
packages/music_core deterministic Transformer
        ↓
AiMidiEditProposal
        ↓
T34 scratch Preview（Draft 不变）
        ↓
Frontend Apply（一次 History step）
        ↓
T34 Draft / Undo / Dirty
        ↓
existing POST /midi/edit
        ↓
New Version + canonical output.mid + WAV stale
```

核心权限边界：

- LLM 只选择 allowlist operation 及其参数，不生成 MIDI binary，不返回 Track ID，不拥有 Scope。
- Backend Planner 复用现有 Provider factory、结构化输出、Pydantic parse/repair 与调用日志，不新增 LLM Client。
- Scope、Plan semantic validation、Transformer、stale check 均为非 LLM 代码。
- Transformer 不调用 LLM；Proposal 生成不修改 Draft、Project、Version、MIDI 或 WAV。
- Apply 才修改 session Draft；Save 才修改 canonical MIDI 并创建 Version。
- User Scope 永远高于 Prompt。Prompt injection 不能扩大 Track、Note 或 tick 权限。

## 1. Existing AI Architecture

### 1.1 已存在并可复用

真实代码边界如下：

| 能力 | 当前文件 | T35 决策 |
| --- | --- | --- |
| Provider 抽象 | `packages/llm/base.py` | 复用 `LLMProvider.generate_structured` |
| Provider 工厂 | `packages/llm/factory.py` | 复用；支持 mock/deepseek/lmstudio/gemini/openai_compatible |
| OpenAI-compatible 实现 | `packages/llm/openai_compatible_provider.py` | 复用 HTTP、timeout、response format、repair、日志 |
| Structured parse | `packages/llm/structured_call.py` | 复用 JSON 提取与 Pydantic validation |
| Prompt Registry | `packages/llm/prompt_registry.py` | T35.5 注册一个新 Planner prompt |
| Mock | `packages/llm/mock_provider.py` | T35.5 扩展 generic structured branch；不新增 Provider |
| LLM 错误 | `packages/llm/structured_call.py`、`services/api/errors.py` | 复用并补 T35 domain code |
| 生成 Planner | `packages/music_core/planner/music_planner.py` | 仅证明 Provider orchestration 模式；不复用其 MusicSpec 语义 |

`OpenAICompatibleProvider.generate_structured` 已完成：

1. system/user prompt 组装；
2. Chat Completions 调用和 Provider timeout；
3. 可配置 `response_format`；
4. JSON extraction；
5. Pydantic model validation；
6. 最多两次 JSON repair；
7. provider/model/request_id/token/finish_reason/raw debug path 等日志；
8. `LLMConfigurationError`、`LLMAPIError`、`LLMOutputError`。

T35 Planner 必须通过 `get_llm_provider().generate_structured(...)` 调用。禁止另写 httpx/fetch
客户端，禁止在 Frontend 保存 Provider Key。

### 1.2 不能作为 T35 Transformer 复用的旧链路

当前自然语言编辑 route 是 `POST /api/v1/songs/{song_id}/edit`：

```text
MusicSpec
→ provider.generate_music_edit
→ MusicEditSpec
→ apply_music_edit
→ create_version
→ regenerate MIDI
→ optional render
```

它与 T35 的差异是实质性的：

- 编辑对象是 `MusicSpec`，不是 T34 未保存 MIDI Draft。
- `packages/music_core/editing/edit_engine.py` 对未知或失败 operation 采用 warning + skip；
  T35 要求非法 Plan 整体拒绝。
- 旧 route 会立即创建 Version、重生成 MIDI，并可渲染 WAV；T35 Proposal 禁止这些副作用。
- 旧 `MusicEditSpec` 的 target/operation 语义不能表达稳定 Note ID 与 tick scope。

`arrangement_optimizer.py` 和 `regeneration_engine.py` 也都是确定性 MusicSpec 修改器；
它们不调用 LLM、不处理 session Draft，不能充当 T35 Transformer。T35 只复用它们体现的
“copy → validate → return report”测试思想。

### 1.3 Mock 与结构化输出的实际缺口

`MockProvider.generate_structured` 当前只支持 `MusicSpec`。T35.5 应在同一 MockProvider 中增加
`MidiEditPlan` 的确定性规则分支，使默认 `LLM_PROVIDER=mock` 可跑完整 Proposal 流程。
这不是新 Provider，也不改变 factory。

### 1.4 LLM 内容日志边界

现有实现默认只记录 request/response 摘要；只有运维显式启用
`LLM_DEBUG_LOG_CONTENT` / `LLM_DEBUG_SAVE_RAW_RESPONSE` 才保存内容。T35 不把完整 prompt、
Context、LLM raw response 写入 Project 或 Version。运维 debug 仍遵循现有显式开关，并应使用
部署侧保留期和访问控制。

## 2. Existing MIDI Editor Integration Points

### 2.1 T34 已冻结能力

| 能力 | 真实实现 | T35 接入 |
| --- | --- | --- |
| Document | `MidiEditorDocument`；song/version/PPQ/BPM/meter/tracks | Context identity 与音乐时间 |
| Note | id/pitch/startTick/durationTick/velocity/channel | Proposal before/after canonical shape |
| Track identity | MusicSpec track.id；外部轨为 `ext_*` | 所有 T35 scope 单轨 |
| Draft | `useMidiEditorDraft.ts` 的 `draftNotesByTrack` | Proposal 输入与 Apply 目标 |
| History | per-track snapshot，limit 80 | Apply 必须成为一个 snapshot step |
| Selection | `selectedTrackId` + `Set<string> selectedNoteIds` | selected_notes/track scope |
| Lock | `lockedTrackIds` | Generate/Preview 可用，Apply 禁止 |
| Dirty | saved/draft deep comparison | Proposal/Preview/Reject 不变；Apply 后变更 |
| Preview | `POST /midi/preview` + scratch WAV | Proposal Preview 直接复用 |
| Save | `POST /midi/edit`，单轨完整 notes | 不建立第二套保存 |
| Conflict | `base_version_id` + 409 `VERSION_CONFLICT` | 继续作为最终 Save gate |
| Version | `create_version` + current pointer | T35.9 扩展 provenance |
| WAV | MIDI Save 后由 Workspace 标 stale | 行为不变 |

当前 Draft **没有** `draftRevision`，也没有一次性“用完整 next notes 替换目标轨”的公开 mutation。
这是 T35.1/T35.6 要补的最小扩展，不是另建 Draft。

### 2.2 Proposal 如何进入现有 Draft

Frontend 先用纯函数 `materializeProposal(currentTrackNotes, proposal)`：

1. 检查 Proposal identity 与当前 editor identity；
2. 检查 `beforeNotes` 与当前 scope notes 逐字段一致；
3. 将 deleted 移除、modified 替换、added 追加；
4. 验证 scope 外 Note 逐字段未变；
5. 生成目标轨完整 `nextTrackNotes`；
6. 调用未来的 `draft.replaceTrackNotes(trackId, nextTrackNotes, metadata)` 一次。

`replaceTrackNotes` 在 hook 内只记录一个 before snapshot、只清一次 redo、只产生一个
`draftRevision` 增量，所以 **一次 Apply = 一个 Undo step**。不得用多个现有
`moveNotes/setNotesVelocity/deleteNotes` 串联模拟 Apply。

### 2.3 Proposal 如何在不 Apply 时 Preview

复用 `buildMidiPreviewTracks` 与现有 `POST /midi/preview`：

- 先在内存中 materialize Proposal 的目标轨完整 notes，但不调用 Draft mutation。
- Current Track Preview 只提交该临时目标轨。
- All Tracks Preview 使用 Proposal 临时目标轨 + 其他轨当前 Draft。
- scratch MIDI/WAV 仍只在 OS temp；Stop/end/unmount 清理。
- 不新增 Proposal Preview backend endpoint，不写 `output.mid` / `output.wav` / metadata / Version。

## 3. T35 Data Flow

### 3.1 最终写路径

```text
Frontend capture identity + scope + scoped Draft
→ POST /songs/{song_id}/midi/ai/proposals
→ Backend loads authoritative current Version/MusicSpec/MIDI track metadata
→ validate request Scope
→ build compact planner payload
→ existing LLMProvider.generate_structured(response_model=MidiEditPlan)
→ strict PlanValidator
→ deterministic transform(scoped notes, plan, scope, seed)
→ diff + Proposal response
→ Frontend Preview OR Reject OR Apply
→ Apply uses T34 Draft/History only
→ user explicitly Save
→ existing T34 Save/Version path
```

### 3.2 禁止的捷径

- LLM → MIDI bytes：禁止。
- LLM → Draft mutation：禁止。
- Proposal API → Project/Version/MIDI/WAV write：禁止。
- Transformer → LLM/Provider/network/filesystem：禁止。
- Apply → backend Project write：禁止。
- AI Apply → automatic Save/Version/Render：禁止。

## 4. AiMidiEditContext

### 4.1 API request 与内部 Context 分离

Frontend 不发送可冒充权威 MusicSpec 的 key/chord/role。请求只携带用户输入、editor identity、
Scope 和该 Scope 的 Draft notes；Backend 从当前 Project/MusicSpec/MIDI document 补权威字段。

未来 `services/api/schemas/ai_midi_edit.py`：

```python
class GenerateAiMidiEditProposalRequest(BaseModel):
    instruction: str                  # 1..1000 chars
    base_version_id: str              # non-null
    editor_session_id: UUID
    draft_revision: int               # >= 0
    scope_revision: int               # >= 0
    scope: MidiEditScope
    draft_notes: list[MidiEditorNote] # authorized notes only, max 3000
```

内部 `AiMidiEditContext`：

```python
class AiMidiEditContext(BaseModel):
    song_id: str
    base_version_id: str
    editor_session_id: UUID
    draft_revision: int
    scope_revision: int
    scope_fingerprint: str
    scope: MidiEditScope

    track_id: str
    track_role: str | None
    instrument: str | None
    is_drum: bool
    channel_summary: list[int]

    ppq: int
    tempo_bpm: int | None
    time_signature: tuple[int, int]
    total_ticks: int
    scoped_notes: list[MidiEditorNote]

    key: str | None
    mode: str | None
    scale: str | None
    section: AiMidiSectionContext | None
    chords: list[AiMidiChordContext]
```

### 4.2 字段真实来源

- song/version：`MidiEditorDocument` 与 Version index。
- PPQ/meter/BPM：当前 `output.mid` 解析结果；BPM 缺失时保留 null，不臆造。
- track role/instrument：当前 MusicSpec 对应 Track；`ext_*` 可为 null。
- isDrum/channel：当前 MidiEditor Track/Notes。
- key/mode/scale：当前 `MusicSpec.tonality`。
- section：当前 `MusicSpec.form`，`start_bar` 为 1-based，换算使用真实 PPQ/meter。
- chords：当前 `MusicSpec.harmony`，仅发 Scope 相交小节，遵循现有一小节一个和弦循环语义。
- scoped notes：当前 Frontend session Draft；这是唯一非 Project-canonical 的输入。

不发送 `MusicSpec.prompt`、其他轨完整 notes、版本历史、文件路径、音频 metadata、API Key。

### 4.3 LLM-visible planner payload

完整 `AiMidiEditContext` 给非 LLM Validator/Transformer；传给 LLM 的 payload 再压缩：

- notes ≤128：发送全部 scoped notes。
- notes >128：发送 count/range/density/pitch/velocity/duration 统计，以及按时间均匀抽取的
  128 个确定性样本；不随机采样。
- chords 最多 64 个、sections 最多 16 个，只保留 Scope 相交项。
- user payload UTF-8 JSON 上限 64 KiB；超限返回 413，绝不静默截断 instruction 或 Scope identity。

LLM 不需要完整 3000 notes 才能选择全体变换参数；Transformer 仍对完整 scoped notes 执行。

## 5. Scope Model

### 5.1 Discriminated union

`MidiEditScope` 放在未来 `packages/music_core/midi_editing/models.py`，使用
`type` discriminator 与 `extra="forbid"`：

| type | 必填 | 禁止/为空 | Note membership |
| --- | --- | --- | --- |
| `selected_notes` | `track_id`、非空唯一 `note_ids` | section/start/end | 请求 notes ID 必须与 note_ids 集合完全相等 |
| `track` | `track_id` | note_ids/section/start/end | 请求 notes 是目标轨当前完整 Draft |
| `section` | `track_id`、`section_id`、`start_tick`、`end_tick` | note_ids | Backend 从 MusicSpec 重算边界并要求完全一致 |
| `tick_range` | `track_id`、`start_tick`、`end_tick` | note_ids/section | notes 为 startTick 落在半开区间 [start,end) 的目标轨 Draft |

共同约束：

- 第一版每个 Proposal 只允许一个 Track；`track_id` 非空。
- `0 <= start_tick < end_tick <= total_ticks`。
- `note_ids` 去重、最多 3000。
- Note ID 唯一；每个请求 note 都通过 T34 `MidiEditorNote` validation。
- section/tick_range 以 Note 的 `startTick` 判 membership；跨边界 sustain 不因此取得额外 Note 权限。
- Scope canonical JSON 按固定字段顺序、noteIds 字典序排序，SHA-256 得到 `scopeFingerprint`。

### 5.2 User Scope > LLM Instruction

`MidiEditPlan` **没有 trackId、noteIds、startTick、endTick 字段**。Transformer 的 target notes
只来自已验证 Scope。即便 instruction 是“删除整首歌的鼓”，当 Scope 是 Bass selected notes 时：

- LLM 只能返回 allowlist operation；
- non-LLM Validator 不能把 Scope 扩成 drums/whole song；
- Transformer 只能收到 Bass 被选 Note；
- Scope 外 notes 在 diff gate 必须 bit-for-bit/field-for-field 相等。

Prompt 仅影响 operation 选择，不授予权限。

## 6. Draft Revision / Stale Model

### 6.1 draftRevision

T35.1 在现有 `useMidiEditorDraft` 增加 session-global、单调递增的 `draftRevision`：

- document/session 创建时从 0 开始；
- 每个**实际改变 Draft 的逻辑操作**增加 1；
- drag 在第一次有效 pointer mutation 时增加一次，后续 pointermove 与 commit 不再增加；
- batch operation、AI Apply 各增加一次；
- undo、redo、discard、rebase 在实际改变状态时各增加一次；
- 无效操作/no-op 不增加；
- 使用 ref 先同步递增，再 setState，避免网络请求读取 stale React closure。

document 变化时仅重置数字会产生碰撞，所以同时生成新的 `editorSessionId` UUID。

### 6.2 Scope identity

`scopeRevision` 是 editor session 内单调递增值。selected track、selected note set、section 或
tick range 每次变化都增加，即使用户切走后又切回同样值。`scopeFingerprint` 验证 Scope 内容；
`scopeRevision` 防止 away-and-back 复用旧 Proposal。

### 6.3 request/response identity

Proposal 原样回显：

```text
songId
baseVersionId
editorSessionId
baseDraftRevision
baseScopeRevision
scopeFingerprint
trackId
```

Apply 和 Proposal Preview 前必须全部满足：

```text
current.songId              == proposal.songId
current.document.versionId  == proposal.baseVersionId
current.editorSessionId     == proposal.editorSessionId
current.draftRevision       == proposal.baseDraftRevision
current.scopeRevision       == proposal.baseScopeRevision
current.scopeFingerprint    == proposal.scopeFingerprint
current.selectedTrackId     == proposal.trackId
current scoped beforeNotes  == proposal.beforeNotes
```

任一失败即 `STALE_PROPOSAL`，Apply 禁用；不提供“强制应用”。

### 6.4 Version 与并发

Backend 在 LLM 调用前验证 current version = `baseVersionId`，在返回 Proposal 前再次读取 current
version。期间任何 Restore/Regenerate/Save 导致版本变化，整个结果丢弃并返回 409
`VERSION_CONFLICT`。Backend 无法观察浏览器 Draft revision，因此 Draft/scope stale 由 response
identity + Frontend gate 完成。

Project/document switch 时 AbortController 取消请求、generation token 使迟到 response 失效、
Proposal state 立即清空。不得把 A 工程 Proposal 带入 B 工程。

## 7. MidiEditPlan

### 7.1 Schema

Plan domain schema 放在 `packages/music_core/midi_editing/models.py`：

```python
class MidiEditPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    summary: str = Field(min_length=1, max_length=200)
    operations: list[MidiEditOperation] = Field(min_length=1, max_length=8)
```

`MidiEditOperation` 是按 `type` discriminator 的 Pydantic union，每种 operation 有独立参数模型，
全部 `extra="forbid"`。Plan 不含 Scope、不含任意 function/tool 名、不含 executable content。
operations 按数组顺序执行。

### 7.2 两层 validation

1. **Structured validation**：JSON/Pydantic 类型、必填字段、静态范围、未知字段/operation；
   可复用现有 JSON repair 获得 schema-valid JSON。
2. **Semantic PlanValidator**：基于 Context 检查 PPQ 动态范围、drum 限制、Scope 适用性、
   operation 组合、最大规模。失败时整体拒绝，不删除、不改写、不“尽力执行”其余 operations。

JSON repair 只修复格式/模式，不允许 semantic validator 自动替换 operation。

### 7.3 明确禁止

Plan 出现以下内容均因 unknown field/type 被拒绝：

- Python/JavaScript/shell；
- filesystem path/URL；
- MIDI bytes/base64；
- backend route/function；
- project/version/save/render 指令；
- trackId/noteIds 或扩大 Scope 的声明。

## 8. Operation Allowlist

所有 operation 可用于四种 Scope；实际 Note 集永远由 Scope 固定。pitch operation 对 drum track
整体拒绝。数值取整统一使用 `round-half-away-from-zero`，禁止依赖 Python bankers-round。

| type | 参数与合法范围 | 确定性语义 | 额外 validation |
| --- | --- | --- | --- |
| `transpose` | `semitones: int [-24,24]`，不能 0 | pitch += semitones，饱和到 0..127 并 warning | drum 禁止 |
| `octave_shift` | `octaves: int [-2,2]`，不能 0 | 调用 transpose(octaves*12) | drum 禁止 |
| `velocity_set` | `value: int [1,127]` | 所有 target velocity=value | 结果全相同可成为 no-op |
| `velocity_delta` | `delta: int [-64,64]`，不能 0 | velocity += delta，饱和 1..127 | 无 |
| `velocity_scale` | `factor: float [0.25,2.0]`，不能 1 | velocity=round(v*factor)，饱和 1..127 | finite number |
| `duration_scale` | `factor: float [0.25,4.0]`，不能 1 | duration=round(d*factor)，最少 1 tick | section/range 的新 duration 不越过 endTick；必要时 clamp+warning |
| `staccato` | `ratio: float [0.10,0.95]` | duration=max(1,round(d*ratio)) | 不移动 start |
| `legato` | `overlap_ticks: int [0,1920]`，默认 0 | 同 channel、同一 onset chord 共享下一 distinct onset；延长至 next onset+overlap；最后 onset 不变 | overlap_ticks 还须 ≤2*PPQ；section/range 不越 endTick |
| `quantize` | `grid: 1/4\|1/8\|1/16\|1/32`；`strength: float (0,1]` 默认 1 | 最近网格，正中 tie 向后；start 向目标按 strength 插值；duration 不变 | grid 由 PPQ 精确有理数计算 |
| `shift_timing` | `delta_ticks: int`，不能 0 | start += delta；最低 0 | abs(delta) ≤4*PPQ；section/range clamp 在授权时间窗并 warning |
| `reduce_density` | `keep_ratio: float [0.10,0.95]`；`preserve_edges: bool` 默认 true | stable SHA-256(seed + canonical note tuple) 排序，保留目标数量；不依赖输入数组顺序 | 唯一使用 seed 的初始 operation |

补充规则：

- 多 operation 顺序应用；reduce_density 删除后，后续 operation 只处理剩余 Note。
- 第一版没有 add/generate/delete-all operation；Proposal 的 `added` 保留为前向兼容字段，初始恒空。
- Note ID 与 channel 永远不由 operation 修改。
- Transformer 输出按 `(startTick, pitch, channel, id)` canonical sort。
- 有效 Plan 最终产生空 diff 时不返回空 Proposal，而返回 `AI_MIDI_NO_CHANGES`。

## 9. Transformer Architecture

### 9.1 位置与接口

未来具体文件：

```text
packages/music_core/midi_editing/__init__.py
packages/music_core/midi_editing/models.py
packages/music_core/midi_editing/scope.py
packages/music_core/midi_editing/plan_validator.py
packages/music_core/midi_editing/transformer.py
packages/music_core/midi_editing/diff.py
```

核心纯函数：

```python
transform_midi_notes(
    notes: Sequence[MidiEditorNote],
    plan: MidiEditPlan,
    scope: MidiEditScope,
    *,
    ppq: int,
    total_ticks: int,
    is_drum: bool,
    seed: int,
) -> MidiTransformResult
```

`MidiEditorNote` 继续复用 T34 的 Pydantic shape；T35 不建立第二个 Note 模型。当前
`midi_editor_io.py` 已采用 music_core 导入 API schema 的仓库惯例。若未来统一 domain schema，
必须通过 re-export 保持 T34 API contract，不作为 T35 前置重构。

### 9.2 不变量

同 input canonical notes + 同 Plan + 同 Scope + 同 seed 必须 byte-for-byte 等价地得到同 result：

- pitch 0..127；
- velocity 1..127；
- startTick >=0；
- durationTick >0；
- channel 与 ID preserved；
- 仅授权 Note ID 可 modified/deleted；
- Scope 外 notes 不增、不删、不改；
- 不读时钟、环境变量、文件、网络或全局 RNG；
- 不原地修改输入；
- 任意 invariant 失败，整个 transform 失败且不返回部分结果。

Transformer 完成后由独立 diff gate 再比较 allowed IDs 与 before/after，形成双重 Scope enforcement。

### 9.3 Canonical randomness

`transformerSeed` 为 unsigned 32-bit，Backend 使用以下 canonical JSON 的 SHA-256 前 4 bytes：

```text
songId + baseVersionId + draftRevision + scopeFingerprint + normalizedInstruction
```

seed 由服务器决定并写入 Proposal，LLM 不能指定。除 `reduce_density` 外 operation 不消费 seed。
stable Note score 使用：

```text
sha256(seed | id | pitch | startTick | durationTick | velocity | channel)
```

因此重试相同请求且得到相同 Plan 时，Transformer 输出完全一致。`proposalId` 和 LLM 本身可以不同，
不影响给定 Plan/seed 的确定性。

## 10. Proposal Contract

未来 `services/api/schemas/ai_midi_edit.py`：

```python
class AiMidiEditProposal(BaseModel):
    proposal_id: UUID
    song_id: str
    base_version_id: str
    editor_session_id: UUID
    base_draft_revision: int
    base_scope_revision: int
    scope_fingerprint: str
    track_id: str
    track_role: str | None
    scope: MidiEditScope
    transformer_seed: int
    planner_provider: str
    planner_model: str | None
    prompt_version: str
    plan: MidiEditPlan
    before_notes: list[MidiEditorNote]
    after_notes: list[MidiEditorNote]
    added: list[MidiEditorNote]
    deleted: list[MidiEditorNote]
    modified: list[MidiNoteModification]
    warnings: list[str]
    created_at: datetime
```

`MidiNoteModification` 包含 `note_id`、`before`、`after`、排序后的 `changed_fields`。
`beforeNotes/afterNotes` 是 **Scope note set**，不是整首 MIDI；track scope 时才等于整轨。

Proposal：

- 不是 Draft；
- 不是 Version；
- 不是 canonical MIDI；
- 不作为 Project asset；
- 不在 Backend 数据库/磁盘持久化；
- 只存于当前 Frontend editor session 内存，刷新即丢失；
- 生成时 dirty、Version、MIDI/WAV hash 与 metadata 均不变。

## 11. Preview / Apply / Reject

### 11.1 Preview

- 对非 stale Proposal 调用纯函数 materialize；
- 复用 T34 scratch preview API；
- 不修改 Draft/History/Dirty；
- locked Track 允许 Preview；
- stale Proposal 禁止 Preview，要求重新生成，避免播放与当前上下文不一致的结果。

### 11.2 Apply

- 必须通过完整 stale predicate、beforeNotes equality、Scope diff gate；
- locked Track 返回 Frontend domain error `TRACK_LOCKED`；
- Stop 当前 preview 后一次调用 `replaceTrackNotes`；
- 一次 Apply = 一次 Undo step = `draftRevision + 1`；
- Apply 后正常由现有 dirty comparison 得到 dirty=true；
- 不自动 Save、Version、Render。

### 11.3 Reject

- 清空当前 Proposal 与 preview scratch；
- Draft/History/Dirty/draftRevision 不变；
- 不调用 backend write API。

## 12. LLM Planner Architecture

### 12.1 部署决定

Planner 放 Backend，orchestration 放
`services/api/services/ai_midi_edit_service.py`：

- Provider keys 和配置已经只在 Backend；
- generic structured output、repair、logging 可直接复用；
- Pydantic schema/semantic validation 与 Transformer 同为 Python；
- 服务端能加载权威 Project/Version/MusicSpec，阻止前端伪造 role/section；
- Frontend 只发送 Scope Draft，不发送 Provider credentials。

Transformer 放 `packages/music_core/midi_editing/transformer.py`，因为它是可独立测试、无 FastAPI/LLM
依赖的音乐 domain 纯函数。UI、Proposal lifecycle、Draft Apply 留 Frontend，因未保存 Draft 只存在浏览器。
最终是 Hybrid，但权限与转换在 Backend。

### 12.2 Planner service 步骤

1. 校验 project/current Version/track；
2. 校验 Scope 与 draft notes；
3. 构建权威 Context 与 compact planner payload；
4. 从 `PromptRegistry` 读取 `ai_midi_edit_planner`；
5. 调用现有 `generate_structured(response_model=MidiEditPlan, task_name="plan_midi_edit")`；
6. 严格 semantic validate；
7. 计算 transformer seed；
8. 执行纯 Transformer；
9. diff + Scope invariant；
10. 再查 current Version；
11. 返回 stateless Proposal。

T35.5 新增 `prompts/ai_midi_edit_planner.md` 和 registry entry；T35.0 不创建 Prompt。

## 13. API Proposal

### 13.1 Generate Proposal

`POST /api/v1/songs/{song_id}/midi/ai/proposals`

Request 是 `GenerateAiMidiEditProposalRequest`；path `song_id` 必须等于 Context identity，
body 不重复 song ID。Response 200 为 `AiMidiEditProposal`。该 API 是无状态计算，不创建可读取的
Proposal resource，因此初版不提供 GET/DELETE proposal route。

### 13.2 Preview

不新增 API。Frontend 将 Proposal materialize 为 T34 track snapshot，继续调用：

`POST /api/v1/songs/{song_id}/midi/preview`

并复用现有 stream/cleanup route。

### 13.3 Apply

不新增 backend Apply route。Apply 只改 Frontend T34 Draft。最终显式 Save 继续调用：

`POST /api/v1/songs/{song_id}/midi/edit`

### 13.4 Backend concrete file map

后续实现的具体落点冻结为：

```text
services/api/schemas/ai_midi_edit.py
  API request/response、Context、Proposal、provenance transport schema

services/api/services/__init__.py
services/api/services/ai_midi_edit_context.py
  T35.1 authoritative Context builder 与 planner payload compaction

services/api/services/ai_midi_edit_service.py
  T35.4/5 orchestration：version pre/post check、Provider、Transformer、Proposal

services/api/routes/ai_midi_edit.py
  POST /songs/{song_id}/midi/ai/proposals

services/api/main.py
  include ai_midi_edit router

services/api/errors.py
  T35 domain error code/stage

packages/music_core/midi_editing/
  models.py / scope.py / plan_validator.py / transformer.py / diff.py

prompts/ai_midi_edit_planner.md
packages/llm/prompt_registry.py
packages/llm/mock_provider.py
  T35.5 only：Prompt 注册与 existing Provider/Mock structured reuse
```

测试落点：

```text
tests/test_ai_midi_edit_scope.py
tests/test_ai_midi_edit_context.py
tests/test_midi_edit_plan.py
tests/test_midi_edit_transformer.py
tests/test_ai_midi_edit_proposal.py
tests/test_ai_midi_edit_api.py
```

route 独立于已很大的 `songs.py`，但仍挂在同一 `/api/v1/songs/{song_id}` URL namespace。
domain Transformer 不依赖 FastAPI、storage 或 Provider；service 是唯一 orchestration layer。

## 14. Frontend Architecture

未来文件放在现有 editor feature 内，不创建第二套页面：

```text
apps/web/src/features/midi/editor/ai/
  AiMidiEditPanel.tsx
  aiMidiEditApi.ts
  aiMidiEditTypes.ts
  aiMidiEditProposal.ts
  useAiMidiEdit.ts
  *.test.ts(x)
```

职责：

- `AiMidiEditPanel`：instruction、Scope selector、Generate、Plan/Diff、Preview/Apply/Reject、stale/error。
- `aiMidiEditApi`：snake↔camel mapping、AbortSignal、只暴露 generate proposal。
- `aiMidiEditTypes`：Frontend contract 映射；复用 `MidiEditorNote`。
- `aiMidiEditProposal`：identity predicate、before equality、materialize、Scope diff 的纯函数。
- `useAiMidiEdit`：request generation token、AbortController、Proposal lifecycle；不持有第二份 Draft。
- `MidiEditor.tsx`：提供 selected Track/Notes、section context、lock 与 T34 Draft callbacks，只做组合。

`useMidiEditorDraft.ts` 的正式扩展：

- 返回 `editorSessionId`、`draftRevision`；
- 增加 `replaceTrackNotes` 原子 mutation；
- 后续为 provenance 将 History entry 从裸 notes snapshot 扩成 notes + provenance lineage，
  对外 Undo/Redo 语义保持不变。

## 15. Version Provenance

### 15.1 保存路径

```text
Proposal → Apply to Draft → user Save → existing MIDI write/version transaction → WAV stale
```

T35 不建立 AI Save API。T35.9 给 `MidiEditorSaveRequest` 增加可选
`provenance: list[AiMidiEditProvenance]`（max 16），并给 Version metadata 增加同名可选字段。
没有 provenance 的手工 Save 保持兼容。

每个 provenance event：

```json
{
  "source": "ai_midi_edit",
  "proposal_id": "...",
  "track_role": "bass",
  "scope_type": "selected_notes",
  "instruction_summary": "将所选贝斯音降低一个八度",
  "operation_types": ["octave_shift"],
  "plan_schema_version": "1.0",
  "provider": "mock",
  "model": null
}
```

- `instruction_summary` 最长 200 字，由 Proposal Plan summary 提供。
- 完整 raw instruction、完整 Context、完整 Plan response 不写 Version/Project。
- Apply provenance 与 notes 一起进入 per-track history lineage；Undo 恢复之前 lineage，Redo 恢复之后
  lineage，避免“AI Apply 已撤销但 Save 仍声称使用 AI”的错误。
- Save 成功/rebase 清空该轨 pending provenance。
- Version `kind` 保持兼容的 `edit`；来源由 `provenance[].source` 精确表达。

## 16. Failure Model

所有失败都保留现有 Draft。Proposal API 没有 Project write，Frontend 失败时也不调用 Draft mutation。

| 场景 | HTTP / domain | Frontend 行为 | Draft |
| --- | --- | --- | --- |
| LLM timeout | 504 `LLM_TIMEOUT` | 显示可重试；保留旧非 stale Proposal或无 Proposal | 保留 |
| Provider unavailable/config | 502 `LLM_PROVIDER_ERROR` | 显示 Provider 原因，不 fallback 到另一个 Provider | 保留 |
| upstream HTTP | 502；鉴权等细节放 `LLM_HTTP_ERROR` details，不向客户端透传 secret | 显示错误 | 保留 |
| invalid structured output | 502 `LLM_INVALID_RESPONSE` | 不显示/Apply 部分 Plan | 保留 |
| unknown operation/field | 502 `AI_MIDI_INVALID_PLAN` | 整 Plan 拒绝 | 保留 |
| invalid parameter/组合 | 502 `AI_MIDI_INVALID_PLAN` | 整 Plan 拒绝 | 保留 |
| empty/oversized plan | 502 `AI_MIDI_INVALID_PLAN` | 提示改写 instruction | 保留 |
| valid plan but no diff | 422 `AI_MIDI_NO_CHANGES` | 提示没有可应用变化 | 保留 |
| request context > limits | 413 `AI_MIDI_CONTEXT_TOO_LARGE` | 建议 selected_notes/section/range | 保留 |
| malformed scope/note IDs | 422 FastAPI validation 或 `AI_MIDI_INVALID_SCOPE` | 修正 Scope 后重试 | 保留 |
| hallucinated Track | 404 `AI_MIDI_TRACK_NOT_FOUND`；若来自 LLM unknown field 则 invalid plan | 清 Proposal | 保留 |
| scope violation in transform/diff | 500 `AI_MIDI_SCOPE_VIOLATION`，记录安全事件 | 禁止 Apply/Preview | 保留 |
| version changed during request | 409 `VERSION_CONFLICT` | reload 或保留 Draft 查看；Proposal 不生成 | 保留 |
| stale Draft/Track/Scope | Frontend `STALE_PROPOSAL` | 标 stale，Apply/Preview disabled，重新生成 | 保留 |
| project switch | Frontend abort + clear | 旧 response 丢弃 | 各项目隔离 |
| locked Track | Frontend `TRACK_LOCKED` on Apply | Generate/Preview 可用，Apply disabled | 保留 |
| preview renderer failure | 现有 500 `RENDER_FAILED` | Proposal 仍可查看/Reject；可稍后重试 Preview | 保留 |

为便于定位，T35.2/4 将给 `ErrorStage` 增加 `AI_MIDI_CONTEXT`、`AI_MIDI_PLAN_VALIDATION`、
`AI_MIDI_TRANSFORM`、`AI_MIDI_DIFF`，但不泄露 prompt/raw response。

## 17. Security / Scope Enforcement

安全 gate 按顺序：

1. path project lookup；
2. current Version pre-check；
3. Track 必须存在于当前 MidiEditorDocument；
4. strict discriminated Scope validation；
5. request Note ID uniqueness/membership；
6. LLM Plan `extra=forbid` 且没有权限字段；
7. semantic allowlist validation；
8. Transformer 只收到 scoped notes；
9. diff gate 验证 allowed IDs；
10. current Version post-check；
11. Frontend full stale predicate；
12. Frontend beforeNotes equality + Scope diff；
13. lock gate；
14. single Draft mutation；
15. existing Save baseVersion conflict。

这些 gate 防止：

- Prompt injection 扩大权限；
- LLM 修改 Scope 外 Note；
- hallucinated Track ID；
- A Project Proposal 写入 B Project；
- 旧 Proposal 覆盖新 Draft；
- AI 自动 Save/Create Version/Render。

Prompt 中写“忽略规则”不会跳过任何非 LLM gate。

## 18. Performance / Token Budget

| 项 | 冻结上限/策略 |
| --- | --- |
| instruction | 1..1000 Unicode chars |
| request scoped notes | max 3000；再大返回 413，建议缩 Scope |
| LLM exact note sample | max 128；超出使用统计 + 时间均匀 sample |
| Plan operations | 1..8 |
| LLM-visible chords | max 64，Scope 相交 |
| LLM-visible sections | max 16，Scope 相交 |
| planner user JSON | max 64 KiB UTF-8 |
| proposal before/after | 各 max 3000 |
| Transformer | O(notes × operations)，初版最多 O(24000) 基本变换 |
| reduce_density | O(n log n) stable hash sort |
| Preview | 继续 T34 scratch；无 per-note timer |
| Proposal storage | Frontend memory only |

3000-note Track 可以作为 API/Transformer 输入，但默认不会把 3000 个 Note 全部写进 LLM prompt。
对于超过上限的轨道，用户必须选 notes/section/tick range；不得静默只变换前 N 个 Note。

## 19. Risk Matrix

| 风险 | 级别 | 证据 | 缓解 |
| --- | --- | --- | --- |
| LLM 越权 | P0 | instruction 不可信 | Plan 无 target + Scope/transform/diff 三重 gate |
| stale Proposal 覆盖新 Draft | P0 | LLM 有网络延迟 | session/version/draft/scope identity + before equality |
| Apply 多个 Undo step | P1 | 当前 hook mutation 粒度较细 | 单次 replaceTrackNotes |
| Track/Scope away-and-back | P1 | 仅比较值会碰撞 | scopeRevision 单调递增 |
| document revision 复用 | P1 | revision reset=0 会碰撞 | editorSessionId UUID |
| 旧 edit_engine 尽力执行 | P1 | 当前实现 skip unknown/failure | T35 独立 strict PlanValidator |
| 大 Track token 爆炸 | P1 | T34 支持 3000 notes | summary/sample + 64KiB + 413 |
| drum transpose 改变乐器语义 | P1 | GM drum pitch=乐器 | 初版 drum 禁止 pitch operations |
| Preview 意外写工程 | P0 | 音频渲染有正式路径 | 只复用已验收 scratch route |
| provenance 与 Undo 不一致 | P2 | 当前 history 只有 notes | provenance lineage 与 history snapshot 同步 |
| Python/TS Scope canonicalization 偏差 | P1 | 双语言实现 | 固定字段顺序 + shared fixtures |
| concurrent Version change | P0 | LLM 前后时间窗 | Backend pre/post Version check + Save 409 |
| ext track 缺 role | P2 | T34 允许 `ext_*` | role nullable；只做通用 operation |
| operator debug 保存内容 | P2 | 现有 env 可启用 raw logs | 默认关闭；不进入 Project；部署保留策略 |
| 历史 T35 编号重名 | P3 | ROADMAP 已有日志 T35 | 文档使用完整名 “T35 AI-assisted MIDI Editing” |

## 20. T35.0–T35-R Slice Contract

### T35.0 Architecture Scan — completed

- Goal：真实扫描、冻结本文所有合同。
- Dependency：T34-R completed。
- Non-goals：所有 runtime/product implementation。
- Acceptance：文档/状态/路线图、现有测试/build、commit/push。

### T35.1 Context & Scope — next

- Goal：实现 domain Scope、API request/Context builder、Frontend scope identity、
  `editorSessionId/draftRevision/scopeRevision`。
- Dependency：T35.0。
- Non-goals：LLM call、Plan、Transformer、Proposal UI、Apply。
- Acceptance：
  - 四种 Scope Pydantic/TS contract 与 canonical fingerprint fixtures；
  - User-selected membership 与 section/tick mapping tests；
  - Draft 每个逻辑 mutation revision 精确 +1，drag 只 +1；
  - project/version/document/track/note selection 隔离测试；
  - Context 只含权威音乐字段和 scoped Draft，3000-note prompt compaction 仅提供纯函数/测试，
    不调用 LLM。
- Exact files：
  - 新增 `packages/music_core/midi_editing/__init__.py`、`models.py`、`scope.py`；
  - 新增 `services/api/schemas/ai_midi_edit.py`、`services/api/services/__init__.py`、
    `services/api/services/ai_midi_edit_context.py`；
  - 新增 `apps/web/src/features/midi/editor/ai/aiMidiEditTypes.ts`、
    `aiMidiEditScope.ts` 及对应测试；
  - 修改现有 `useMidiEditorDraft.ts`/tests（session ID + revision），`MidiEditor.tsx`/tests
    （scopeRevision 与 Context capture）；不创建 route、Prompt、Transformer 或 AI Panel；
  - 新增 `tests/test_ai_midi_edit_scope.py`、`tests/test_ai_midi_edit_context.py`。

### T35.2 MidiEditPlan

- Goal：实现 operation discriminated union 与 strict PlanValidator。
- Dependency：T35.1。
- Non-goals：执行 Plan、Provider call。
- Acceptance：allowlist/range/drum/unknown field/empty/oversized/组合 tests；非法整体拒绝。

### T35.3 Deterministic Transformer

- Goal：实现 11 个初始 operation、seed 与 invariant。
- Dependency：T35.2。
- Non-goals：API/LLM/UI。
- Acceptance：golden/property tests；same input/plan/seed same output；Scope 外不变；无 input mutation。

### T35.4 Proposal / Diff

- Goal：实现 diff、Proposal builder、no-op/scope gate；使用 fixture Plan。
- Dependency：T35.3。
- Non-goals：真实 LLM、UI Apply。
- Acceptance：before/after/added/deleted/modified 精确；Proposal 构建零 Project 副作用。

### T35.5 LLM Planner

- Goal：注册 Prompt，复用 Provider generic structured call，扩展 Mock，增加 Proposal route/service。
- Dependency：T35.4。
- Non-goals：Frontend AI UI、Project apply/save。
- Acceptance：mock/deepseek-compatible contract tests；timeout/invalid output/Version pre-post errors；
  API 调用前后 Project/MIDI/WAV/Version hash 不变。

### T35.6 AI Edit UI

- Goal：Panel、API hook、Proposal Diff、Preview/Apply/Reject、single replace mutation。
- Dependency：T35.5。
- Non-goals：auto Save/Version/Render。
- Acceptance：Preview Draft 不变；Reject 不变；Apply dirty=true 且一次 Undo 恢复；locked Apply 禁止。

### T35.7 Scope / Stale Safety

- Goal：完成并对抗测试全部 identity、安全 gate、竞态。
- Dependency：T35.6。
- Non-goals：新音乐 operation。
- Acceptance：draft/version/track/project/scope 变化、away-and-back、late response、prompt injection、
  before mismatch、hallucinated ID 全部不能 Apply。

### T35.8 Musical Role-aware Editing

- Goal：基于真实 role/isDrum/scale/chords 增强 Planner hints、validation warnings 与结果评估。
- Dependency：T35.7。
- Non-goals：绕过 allowlist、自动写和声/生成新 Note。
- Acceptance：drum pitch gate、bass overlap warning、scale/chord context bounded；Scope 不变。

### T35.9 Provenance / Evaluation

- Goal：pending provenance lineage、Save request/Version metadata 扩展、离线质量 fixtures。
- Dependency：T35.8。
- Non-goals：保存 raw LLM 内容。
- Acceptance：Apply→Undo/Redo→Save provenance 准确；manual Save backward compatible；
  raw prompt/response 不在 Project；version/WAV stale 语义保持。

### T35.10 Final Integration

- Goal：完整用户 Flow、性能、真实 Provider 可选 smoke、文档。
- Dependency：T35.9。
- Non-goals：T35-R 审计结论。
- Acceptance：Track/Notes/Section/Range → Generate → Preview → Apply → Undo → Save → Version；
  mock 全自动，真实 Provider 手工 smoke；500/1000/3000 note gates。

### T35-R Final Audit

- Goal：独立复审功能、安全、无副作用、回归、遗留。
- Dependency：T35.10。
- Non-goals：以审计名义补未授权新功能。
- Acceptance：Critical Gates 全通过、P0/P1 清零或明确 blocker、全量前后端/E2E、真实证据、
  retrospective 与最终状态。

## 21. Final Decisions

| Decision | Frozen answer |
| --- | --- |
| Planner location | Backend `services/api/services/ai_midi_edit_service.py` |
| Transformer location | `packages/music_core/midi_editing/transformer.py` |
| Provider reuse | `get_llm_provider().generate_structured`；不新增 Client/Provider |
| Context source | Backend 权威 Project/MusicSpec/MIDI metadata + Frontend scoped session Draft |
| Scope types | selected_notes / track / section / tick_range，全部单 Track |
| Scope enforcement layer | request validator + Transformer input boundary + diff gate + Frontend apply gate |
| draftRevision strategy | editor session 全局单调整数；每个实际逻辑 mutation +1；drag/AI Apply 各一次 |
| Version stale strategy | Backend LLM 前后 current-version check + Frontend identity + existing Save 409 |
| Plan schema location | `packages/music_core/midi_editing/models.py` |
| Initial operation allowlist | 11 个：transpose、octave_shift、3 velocity、duration_scale、staccato、legato、quantize、shift_timing、reduce_density |
| Randomness/seed policy | 服务端 canonical SHA-256 派生 32-bit；LLM 不可指定；仅 density 使用 |
| Proposal storage | Frontend editor session memory；Backend stateless；不持久化 |
| Preview strategy | materialize transient target track + existing T34 scratch Preview |
| Apply strategy | Frontend pure validation/materialize + 一次 `replaceTrackNotes` |
| Undo integration | Apply 形成一个现有 per-track History step |
| Save strategy | 用户显式使用 existing `POST /midi/edit`；无 AI Save API |
| Version provenance | optional bounded provenance events；source=ai_midi_edit 等摘要字段 |
| Raw prompt persistence | 不写 Project/Version；仅现有 opt-in operator debug policy 可记录 |
| LLM failure behavior | 整 Plan/Proposal 失败；Draft 永远保留；不 fallback 到“尽力执行” |
| Project-switch behavior | abort、generation token 失效、清 Proposal；迟到 response 丢弃 |
| Locked-track behavior | 可 Generate/Preview；Apply disabled；不修改 Draft |

T35.0 没有产品实现 blocker。唯一结构性注意项是仓库历史任务编号重名，已通过完整任务名消歧，
不影响 T35.1 开始实施。
