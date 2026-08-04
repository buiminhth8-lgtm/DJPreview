# AI Music MVP

自然语言生成音乐的 MVP 工程。

- **第一阶段**：基础工程、MusicSpec v0.1 / MusicEditSpec v0.1 协议、LLM 适配层（MockProvider / DeepSeekProvider）、一句话生成 MusicSpec、项目 JSON 保存与读取。
- **第二阶段**：MusicSpec → 编曲数据 → 标准 MIDI 文件（多轨，含旋律 / 和弦伴奏 / 贝斯 / 鼓组 / Pad 铺底），支持确定性 seed 复现，并提供 MIDI 生成与下载 API。

> 当前阶段不实现 WAV 渲染、FluidSynth / SoundFont、网页音频播放器、自然语言修改、版本管理、AI 人声与 VST。

## 一、第二阶段新增能力

- MusicSpec → `CompositionResult` 编曲数据 → 标准 `.mid` 文件
- 自动生成主旋律、和弦伴奏、贝斯、鼓组、Pad / Strings 铺底轨道
- 乐理基础：音高转换、音阶（major / minor / dorian / pentatonic 等）、和弦解析（三和弦 / 七和弦 / sus）
- 和声引擎：把 `harmony` 和弦进行逐小节映射，缺和弦时按调自动补默认进行
- 节奏模板：block_chords / arpeggio / broken_chords / sustained_pad / pop / rock / lo-fi / electronic / cinematic
- 分段 energy 控制：高能量段落密度与力度提升，尾奏减弱
- 确定性生成：同一个 `seed` 生成结果完全可复现
- 轻度人性化：音符时间 / 力度 / 时值做可复现的微小变化
- 项目存储：`data/projects/{song_id}/output.mid` + `metadata.json`
- 新 API：生成 MIDI、下载 MIDI、一步生成 MusicSpec + MIDI

## 二、MIDI 生成流程

```text
MusicSpec ──> BarHarmony（逐小节和弦）
      │
      ├── MelodyEngine    → 主旋律（调式音阶 + 和弦音）
      ├── ArrangementEngine → harmony / pad / strings 伴奏
      ├── BassEngine      → 贝斯（根音 + 五度，强拍根音）
      ├── DrumEngine      → GM 鼓组（channel 9）
      │
      └── Humanizer（轻度人性化，seed 可复现）
              │
              ▼
      CompositionResult ──> MIDI Writer（mido）──> output.mid
```

## 三、项目结构（新增部分）

```text
packages/music_core/
├── theory/               # 乐理基础：pitch / scales / chords
├── harmony/              # 和声引擎：BarHarmony / build_bar_harmony
├── rhythm/               # 节奏模板（beat 为单位）
├── arrangement/          # 伴奏引擎（harmony / pad / strings）
├── melody/               # 旋律引擎
├── bass/                 # 贝斯引擎
├── drums/                # 鼓组引擎
├── humanize/             # 人性化
├── midi/                 # midi_constants / midi_writer
└── composer/             # events（NoteEvent 等）/ music_composer

services/api/
├── routes/songs.py       # 新增 MIDI 生成 / 下载 / 一步生成接口
└── storage/project_store.py  # 新增 save_midi_file / get_midi_path / project_has_midi
```

## 四、后端安装与启动

要求：Python 3.11+

```bash
cd ai-music-mvp
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
```

启动后端：

```bash
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

打开 http://localhost:8000/docs 查看交互式 API 文档。

> 提示：如果 Windows 上 8000 端口被系统保留（报 WinError 10013），可换端口启动，例如 `--port 9000`，并同步设置前端 `VITE_API_BASE_URL`。

## 五、生成 MusicSpec

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"生成一段忧郁空灵的钢琴配乐，D小调，速度较慢"}'
```

返回 `song_id` 与 `music_spec`，MusicSpec 保存在 `data/projects/{song_id}/music_spec.json`。

## 六、生成 MIDI

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/midi/generate
```

返回：

```json
{
  "song_id": "xxx",
  "midi_file": "output.mid",
  "download_url": "/api/v1/songs/xxx/midi/download",
  "summary": { "tracks": 5, "bars": 32, "bpm": 72 }
}
```

MIDI 文件保存在 `data/projects/{song_id}/output.mid`，同目录 `metadata.json` 记录生成时间与生成器版本。

## 七、下载 MIDI

```bash
curl -L http://localhost:8000/api/v1/songs/{song_id}/midi/download -o output.mid
```

未生成 MIDI 时返回 404 并提示先调用生成接口。

### 一步生成 MusicSpec + MIDI（可选接口）

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate-with-midi \
  -H "Content-Type: application/json" \
  -d '{"prompt":"生成一段忧郁空灵的钢琴配乐"}'
```

## 八、前端使用方式

```bash
cd apps/web
npm install
npm run dev
```

打开 http://localhost:5173：

1. 输入一句话，点击“生成 MusicSpec”；
2. 生成后点击“生成 MIDI”；
3. 成功后显示“下载 output.mid”链接以及轨道数 / 小节数 / BPM 摘要。

后端地址默认 `http://localhost:8000`，可通过 `VITE_API_BASE_URL` 覆盖。前端只提供下载，不实现音频播放。

## 九、MockProvider 与 DeepSeekProvider

默认 `LLM_PROVIDER=mock`，无需任何密钥即可跑通 MusicSpec 与 MIDI 全流程。MockProvider 规则：

- 包含「忧郁 / 悲伤 / 雨夜」→ D 小调，72 BPM
- 包含「欢快 / 明亮」→ C 大调，120 BPM
- 包含「中国风」→ pentatonic 调式
- 默认 32 小节：intro 4 / verse 8 / chorus 16 / outro 4
- 默认轨道：melody / piano / bass / drums / pad

使用 DeepSeek 时在 `.env` 配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 十、测试

```bash
cd ai-music-mvp
pytest -v
```

覆盖：

- 第一阶段：MusicSpec / MusicEditSpec 协议、MockProvider 规则、生成/查询 API
- 第二阶段：乐理（音高 / 音阶 / 和弦）、和声引擎、总作曲器（确定性）、MIDI Writer（mido 可打开、多轨）、MIDI 生成/下载 API、404 处理

## 十一、当前不支持（第二阶段范围外）

- WAV 渲染、FluidSynth、SoundFont
- 网页音频播放器、轨道音量控制 UI
- 自然语言修改音乐、版本管理
- AI 人声、歌词演唱、VST 插件

## 十二、第三阶段计划

1. MusicEditSpec 应用：修改指令 → 重新编曲并保存版本
2. WAV 渲染：基于 SoundFont / 合成器把 MIDI 渲染为音频
3. 网页播放器：Web 端播放与波形展示
4. 版本管理与对比
5. 更多 LLM Provider（OpenAI / Ollama / 本地模型）
6. 工程化：Docker、CI、生产部署
