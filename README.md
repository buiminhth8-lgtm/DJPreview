# AI Music MVP

自然语言生成音乐的 MVP 工程。

- **第一阶段**：基础工程、MusicSpec v0.1 / MusicEditSpec v0.1 协议、LLM 适配层（MockProvider / DeepSeekProvider）、一句话生成 MusicSpec、项目 JSON 保存与读取。
- **第二阶段**：MusicSpec → 编曲数据 → 标准 MIDI 文件（多轨），确定性 seed 复现，MIDI 生成与下载 API。
- **第三阶段**：MIDI → WAV 音频渲染（FluidSynth + SoundFont，无 FluidSynth 时 fallback 合成），在线试听、下载 MIDI/WAV、基础轨道与段落展示。
- **第四阶段**：自然语言修改（MusicEditSpec 真正执行）+ 版本管理（v1 自动初始化、每次修改生成新版本、历史版本恢复、根目录资源同步）。
- **第五阶段**：轨道级混音（MixSpec / TrackMixSpec）、钢琴卷帘可视化、编曲质量检查、保守自动优化、分轨 MIDI/WAV stems 导出与打包。

> 当前阶段不实现 AI 人声、歌词演唱、音色克隆、VST 插件、专业混音母带、DAW 深度集成与实时多人协作。

## 一、第五阶段新增能力

- `MixSpec / TrackMixSpec`：每轨 volume / pan / mute / solo / enabled / velocity_scale，可从 MusicSpec 自动初始化并同步
- `MixEngine`：`create_default_mix_spec` / `sync_mix_spec_with_music_spec` / `apply_mix_to_composition` / `update_track_mix`
  - volume / velocity_scale / master_volume 缩放 velocity（1-127）
  - mute / enabled=false 不输出；solo 优先；全部静音时保留 melody 并返回 warning
  - pan 写入 MIDI Control Change 10（-1 → 0，0 → 64，1 → 127）
- MIDI Writer 扩展：pan CC、track_name、可选只写指定轨道（分轨导出）
- `midi_splitter`：按轨道拆分单轨 MIDI
- `stem_renderer`：分轨 MIDI → WAV → `stems.zip` + `stems_metadata.json`
- `midi_parser`：mido 解析（note_on velocity=0 视为 note_off、channel 9 标记 is_drum、beat 时间）
- `piano_roll`：前端友好的钢琴卷帘 JSON（段落、轨道、音符、截断保护）
- `quality_checker`：结构 / 轨道 / 音域 / 密度 / 和声 / 混音诊断，评分 0-100，保存 `quality_report.json`
- `arrangement_optimizer`：保守规则优化（补 melody/harmony/pad、五声音阶、chorus energy、velocity），创建新版本
- 新 API：`/mix`、`/mix/apply`、`/piano-roll`、`/quality/check`、`/quality/report`、`/quality/optimize`、`/stems/export`、`/stems/download`、`/stems/{track_id}/{kind}/download`
- 前端：MixerPanel、PianoRoll（SVG）、QualityReport、StemExportPanel、ArrangementInspector

## 二、MixSpec / TrackMixSpec 说明

```json
{
  "version": "0.1",
  "song_id": "...",
  "version_id": "...",
  "master_volume": 1.0,
  "tracks": [
    {
      "track_id": "piano",
      "role": "harmony",
      "volume": 0.8,
      "pan": -0.2,
      "mute": false,
      "solo": false,
      "enabled": true,
      "velocity_scale": 1.0,
      "program": 0,
      "instrument": "piano"
    }
  ]
}
```

- 单独保存为 `mix_spec.json`（版本目录 + 项目根目录同步），不塞入 MusicSpec
- MusicSpec 增删轨道后，`sync_mix_spec_with_music_spec` 自动同步

## 三、轨道音量、声像、静音、独奏说明

- **volume / velocity_scale / master_volume**：MIDI 无音频音量概念，MVP 通过缩放 velocity 近似（1-127 截断）
- **mute / enabled**：对应轨道不输出 NoteEvent（不删除 MusicSpec 中的 track）
- **solo**：任意轨道 solo 时只输出 solo 轨道，优先级高于 mute
- **pan**：写入 MIDI Control Change 10（0-127）
- 所有轨道被静音时，保留 melody（或第一条可用轨道）保证输出非空，并返回 warning

## 四、分轨导出说明

```text
data/projects/{song_id}/versions/{version_id}/stems/
├── midi/melody.mid ...（每轨一个单轨 MIDI）
├── wav/melody.wav ...（每轨渲染 WAV）
├── stems.zip
└── stems_metadata.json
```

未启用版本系统时兼容 `data/projects/{song_id}/stems/`。空轨道跳过并记录 warning；渲染失败不影响整体导出。

## 五、Piano Roll 可视化说明

- `GET /api/v1/songs/{song_id}/piano-roll` 返回段落、轨道、音符（beat 单位）
- 前端用 SVG 绘制：横轴 beat/bar、纵轴 pitch、段落背景、轨道颜色区分、音符 tooltip
- 音符过多时截断（默认 5000）并返回 `truncated=true`

## 六、Quality Report 说明

- 检查：结构（小节覆盖/重叠）、轨道（空轨/重复 id/缺 melody）、音域（旋律/贝斯）、密度（过空/过密/energy 不匹配）、和声（缺失/空进行）、混音（力度极端）
- 评分 0-100（error 15 / warning 8 / info 2 扣分），level：excellent / good / fair / poor
- 仅诊断，不影响生成；保存 `quality_report.json`

## 七、自动优化说明

- 保守规则优化：缺 melody/harmony 补轨道、cinematic 补 strings pad、中国风设五声音阶、chorus energy 低于 verse 时提高、整体力度过低时提升
- 不调用 LLM、不大改作品；优化后创建新版本（旧版本保留）
- 优化报告保存为 `optimize_report.json`

## 八、API 示例

```bash
# 获取 MixSpec
curl http://localhost:8000/api/v1/songs/{song_id}/mix

# 修改混音并立即重渲染
curl -X PATCH "http://localhost:8000/api/v1/songs/{song_id}/mix?apply=true" \
  -H "Content-Type: application/json" \
  -d '{"tracks":[{"track_id":"piano","volume":0.7,"pan":-0.2}]}'

# 应用混音（重新生成 MIDI/WAV）
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/mix/apply

# 钢琴卷帘数据
curl "http://localhost:8000/api/v1/songs/{song_id}/piano-roll?max_notes=5000"

# 检查质量
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/quality/check

# 读取质量报告（未生成会自动生成）
curl http://localhost:8000/api/v1/songs/{song_id}/quality/report

# 自动优化（创建新版本）
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/quality/optimize \
  -H "Content-Type: application/json" \
  -d '{"auto_render":true}'

# 导出分轨
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/stems/export

# 下载 stems.zip
curl -L http://localhost:8000/api/v1/songs/{song_id}/stems/download -o stems.zip

# 下载单轨 stem
curl -L http://localhost:8000/api/v1/songs/{song_id}/stems/melody/midi/download -o melody.mid
curl -L http://localhost:8000/api/v1/songs/{song_id}/stems/melody/wav/download -o melody.wav
```

## 九、前端使用流程

1. 输入一句话生成 MusicSpec
2. 生成 MIDI、渲染 WAV、试听与下载
3. 自然语言修改 + 版本管理（恢复）
4. **混音器**：调节每轨 volume / pan / velocity_scale / mute / solo / enabled，应用后重新渲染并刷新播放器
5. **编曲检查**：摘要、段落结构、轨道列表、钢琴卷帘、质量报告、自动优化（成功后刷新版本与播放器）
6. **分轨导出**：单轨 MIDI/WAV 下载 + stems.zip

## 十、后端安装与启动

```bash
cd ai-music-mvp
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd apps/web
npm install
npm run dev
```

## 十一、测试

```bash
cd ai-music-mvp
pytest
```

覆盖：第一至四阶段全部回归 + 第五阶段混音模型/引擎、MIDI 解析、stems 导出、质量检查与优化、混音/钢琴卷帘/stems API。前端 `tsc --noEmit` 检查。测试强制 `AUDIO_RENDERER=fallback`，不依赖系统 FluidSynth。

## 十二、当前不支持（第五阶段范围外）

- AI 人声、歌词演唱、音色克隆、VST 插件宿主
- 专业混音母带、DAW 深度集成、实时多人协作
- 音频波形级剪辑、实时音频合成引擎、商业级钢琴卷帘编辑器

## 十三、第六阶段计划

1. 音频可视化增强：波形 / 频谱 / 播放进度与段落高亮联动
2. 混音进阶：EQ、压缩、sidechain、自动化曲线
3. 钢琴卷帘编辑：拖拽移动音符、量化、力度编辑
4. 音质提升：FluidSynth 参数调优、SoundFont 选择器
5. AI 人声 / 歌词演唱（可选）
6. 工程化：Docker、CI、生产部署
