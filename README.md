# AI Music MVP

自然语言生成音乐的 MVP 工程。

- **第一阶段**：基础工程、MusicSpec v0.1 / MusicEditSpec v0.1 协议、LLM 适配层（MockProvider / DeepSeekProvider）、一句话生成 MusicSpec、项目 JSON 保存与读取。
- **第二阶段**：MusicSpec → 编曲数据 → 标准 MIDI 文件（多轨，含旋律 / 和弦伴奏 / 贝斯 / 鼓组 / Pad 铺底），确定性 seed 复现，MIDI 生成与下载 API。
- **第三阶段**：MIDI → WAV 音频渲染（FluidSynth + SoundFont，无 FluidSynth 时 fallback 合成），在线试听、下载 MIDI/WAV、基础轨道与段落展示。

> 当前阶段不实现自然语言修改、版本管理、AI 人声、歌词演唱、音色克隆、VST 插件、专业混音母带、DAW 集成与实时多人协作。

## 一、第三阶段新增能力

- `packages/renderer` 音频渲染抽象层：`AudioRenderer` 协议 + `AudioRenderResult`
- `FluidSynthRenderer`：调用系统 `fluidsynth` 命令 + SoundFont 渲染，无 shell 注入风险
- `FallbackRenderer`：无 FluidSynth 时用 mido + numpy 合成可试听 WAV（开发兜底）
- Renderer Factory：`AUDIO_RENDERER=auto / fluidsynth / fallback`，auto 优先 FluidSynth、不可用时自动降级
- 新 API：`audio/render`、`audio/stream`、`audio/download`、`assets`、`generate-with-audio`
- 音频 metadata：`data/projects/{song_id}/audio_metadata.json`
- 前端：AudioPlayer、MusicSummary、SectionTimeline、TrackList 组件，支持试听与下载

## 二、MIDI → WAV 渲染流程

```text
output.mid
   │
   ├─ FluidSynthRenderer（系统 fluidsynth + SoundFont，音质好）
   │     fluidsynth -ni soundfont.sf2 input.mid -F output.wav -r 44100 -g 0.6
   │
   └─ FallbackRenderer（无 FluidSynth 时的开发兜底）
         mido 解析音符 → numpy 三角波合成 → wave 写 16-bit WAV
              │
              ▼
        output.wav + audio_metadata.json
              │
              ▼
   /audio/stream（试听） /audio/download（下载）
```

## 三、FluidSynth 安装与 SoundFont 配置

Ubuntu / Debian：

```bash
sudo apt-get update
sudo apt-get install -y fluidsynth fluid-soundfont-gm
```

常见 SoundFont 路径：

- `/usr/share/sounds/sf2/FluidR3_GM.sf2`
- `/usr/share/sounds/sf2/FluidR3_GS.sf2`
- `/usr/share/soundfonts/default.sf2`

Windows / macOS 用户通过环境变量指定：

```env
AUDIO_RENDERER=auto
FLUIDSYNTH_BIN=fluidsynth
SOUNDFONT_PATH=C:\path\to\your.sf2
```

### Fallback renderer 说明

- `AUDIO_RENDERER=fallback` 或 auto 降级时使用
- 不依赖外部程序，CI / pytest 可直接运行
- 使用三角波合成，能听出音高与旋律，但**不是正式音质**
- 正式音质请安装 FluidSynth + SoundFont，并将 `AUDIO_RENDERER` 设为 `auto` 或 `fluidsynth`

## 四、项目结构（第三阶段新增）

```text
packages/renderer/
├── base.py                # AudioRenderer Protocol
├── audio_metadata.py      # AudioRenderResult + get_wav_duration_seconds
├── fluidsynth_renderer.py # FluidSynth 渲染器
├── fallback_renderer.py   # 开发兜底渲染器
└── factory.py             # get_audio_renderer()

apps/web/src/components/
├── AudioPlayer.tsx        # 播放/暂停/进度 + 下载
├── MusicSummary.tsx       # 标题/BPM/拍号/调性/小节/风格/情绪/seed
├── SectionTimeline.tsx    # 段落卡片（name/小节范围/energy）
└── TrackList.tsx          # 轨道表格
```

## 五、后端安装与启动

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

> 提示：如果 Windows 上 8000 端口被系统保留（报 WinError 10013），可换端口启动（如 `--port 9000`），并同步设置前端 `VITE_API_BASE_URL`。

## 六、前端安装与启动

```bash
cd apps/web
npm install
npm run dev
```

打开 http://localhost:5173。后端地址默认 `http://localhost:8000`，可通过 `VITE_API_BASE_URL` 覆盖（详见 [apps/web/README.md](apps/web/README.md)）。

## 七、API 示例

### 1. 生成 MusicSpec

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"生成一段忧郁空灵的钢琴配乐，D小调，速度较慢"}'
```

### 2. 生成 MIDI

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/midi/generate
curl -L http://localhost:8000/api/v1/songs/{song_id}/midi/download -o output.mid
```

### 3. 渲染 WAV

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/audio/render
```

返回：

```json
{
  "song_id": "xxx",
  "audio_file": "output.wav",
  "stream_url": "/api/v1/songs/xxx/audio/stream",
  "download_url": "/api/v1/songs/xxx/audio/download",
  "metadata": {
    "audio_file": "output.wav",
    "renderer": "fallback",
    "sample_rate": 44100,
    "duration_seconds": 48.2,
    "file_size": 4250000,
    "generator_version": "stage-3-audio-v0.1",
    "warnings": []
  }
}
```

> 若项目尚未生成 MIDI，`audio/render` 会先自动生成 MIDI 再渲染。

### 4. 下载 / 试听 WAV

```bash
curl -L http://localhost:8000/api/v1/songs/{song_id}/audio/download -o output.wav
```

浏览器试听：

```text
http://localhost:8000/api/v1/songs/{song_id}/audio/stream
```

### 5. 项目资源状态

```bash
curl http://localhost:8000/api/v1/songs/{song_id}/assets
```

返回 `has_music_spec` / `has_midi` / `has_audio` 及对应资源链接。

### 6. 一步生成 MusicSpec + MIDI + WAV

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate-with-audio \
  -H "Content-Type: application/json" \
  -d '{"prompt":"生成一段忧郁空灵的钢琴配乐"}'
```

## 八、环境变量

```env
# 音频渲染（第三阶段）
AUDIO_RENDERER=auto          # auto / fluidsynth / fallback
FLUIDSYNTH_BIN=fluidsynth
SOUNDFONT_PATH=              # 留空自动查找常见路径
AUDIO_SAMPLE_RATE=44100
AUDIO_GAIN=0.6
```

## 九、测试

```bash
cd ai-music-mvp
pytest
```

覆盖：第一阶段协议/MockProvider/API、第二阶段乐理/编曲/MIDI Writer/MIDI API、第三阶段 Fallback 渲染器（合法 WAV、时长>0）与音频 API（render/stream/download/assets、404、自动生成 MIDI）。测试强制 `AUDIO_RENDERER=fallback`，不依赖系统 FluidSynth。

## 十、当前不支持（第三阶段范围外）

- 自然语言修改音乐、MusicEditSpec 真正执行
- 多版本管理
- AI 人声、歌词演唱、音色克隆、VST 插件宿主
- 专业混音母带、DAW 深度集成、实时多人协作

## 十一、第四阶段计划

1. MusicEditSpec 应用 + 版本管理
2. 专业混音：轨道音量/声像/均衡
3. 更多渲染后端（如 MIDI.js、服务器端合成器集群）
4. 音频可视化：波形、频谱、段落高亮联动
5. AI 人声 / 歌词演唱（可选）
6. 工程化：Docker、CI、生产部署
