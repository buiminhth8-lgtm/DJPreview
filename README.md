# AI Music MVP

自然语言生成音乐的 MVP 工程。

- **第一阶段**：基础工程、MusicSpec v0.1 / MusicEditSpec v0.1 协议、LLM 适配层（MockProvider / DeepSeekProvider）、一句话生成 MusicSpec、项目 JSON 保存与读取。
- **第二阶段**：MusicSpec → 编曲数据 → 标准 MIDI 文件（多轨，含旋律 / 和弦伴奏 / 贝斯 / 鼓组 / Pad 铺底），确定性 seed 复现，MIDI 生成与下载 API。
- **第三阶段**：MIDI → WAV 音频渲染（FluidSynth + SoundFont，无 FluidSynth 时 fallback 合成），在线试听、下载 MIDI/WAV、基础轨道与段落展示。
- **第四阶段**：自然语言修改（MusicEditSpec 真正执行）+ 版本管理（v1 自动初始化、每次修改生成新版本、历史版本恢复、根目录资源同步）。

> 当前阶段不实现 AI 人声、歌词演唱、音色克隆、VST 插件、专业混音母带、DAW 深度集成与实时多人协作。

## 一、第四阶段新增能力

- `apply_music_edit`：把 MusicEditSpec 应用到 MusicSpec，**不修改原始对象**（`model_copy(deep=True)`），结果始终通过校验
- 支持操作：`tempo` / `tonality` / `energy` / `velocity` / `add_instrument` / `remove_instrument` / `chinese_style` / `style` / `mood`
- `preserve` 机制：列出不可变字段，相关操作自动跳过
- 段落目标：`target.section=chorus` 时只允许段落级操作（energy / 段落内加乐器），全局操作跳过
- `diff_music_specs`：对比新旧 MusicSpec，输出字段级变化
- 版本管理：旧项目自动初始化 v1；每次 edit 生成新版本；restore 恢复历史版本并同步根目录 `music_spec.json` / `output.mid` / `output.wav`
- 新 API：`/songs/{id}/edit`、`/songs/{id}/versions`、`/songs/{id}/versions/{version_id}/restore`；`/assets` 增加 `current_version`
- 前端：修改指令输入、diff 展示、版本列表与恢复、播放器自动刷新

## 二、自然语言修改流程

```text
修改指令（如“副歌更亮一点”）
   │
   ▼
LLMProvider.generate_music_edit(instruction, spec)
   │   （MockProvider 规则解析 / DeepSeekProvider JSON 生成 + 校验）
   ▼
MusicEditSpec（target / preserve / operations）
   │
   ▼
apply_music_edit(spec, edit_spec)
   │   基于 model_copy(deep=True)，不修改原对象
   │   段落目标只改段落字段；preserve 字段跳过；最终 validate_music_spec
   ▼
新 MusicSpec
   │
   ├─ diff_music_specs(old, new) → diff 列表
   ├─ create_version() → 新版本快照 + versions/index.json 更新 + 根目录 music_spec.json 同步
   └─ 重新生成 output.mid / output.wav（保证资源一致）
```

MockProvider 支持的常见中文指令示例：

| 指令 | 解析结果 |
|------|----------|
| 整首更快一点 / 更慢一点 | tempo ±10 |
| 更亮 / 明亮 / 更暗 / 忧郁 | tonality C major / D minor |
| 副歌更亮一点 / 更激昂 | section=chorus + energy ±0.15 |
| 贝斯音量加大 / 力度 | track=bass + velocity +5 |
| 加点中国风 | chinese_style（pentatonic + 风格标签） |
| 加钢琴 / 加鼓 / 加弦乐 | add_instrument |
| 去掉鼓 / 删除贝斯 / 不要钢琴 | remove_instrument |
| 副歌加鼓 | section=chorus + add_instrument（enabled_sections=[chorus]） |

## 三、版本管理存储结构

```text
data/projects/{song_id}/
├── music_spec.json          # 当前版本快照（兼容第一至三阶段读取）
├── output.mid / output.wav / audio_metadata.json
└── versions/
    ├── index.json           # { current_version_id, versions: [meta...] }
    ├── v1.json              # 版本 1 快照（music_spec + edit_spec + meta）
    └── v2.json              # 版本 2 快照 ...
```

- 旧项目首次访问 `/versions`、`/edit` 或 `/assets` 时自动初始化 v1
- 每次 `/edit` 追加新版本并设为当前版本
- `/restore` 恢复指定版本：更新 `current_version_id`、同步根目录 `music_spec.json`，并重新生成 MIDI / WAV

## 四、API 示例

### 1. 自然语言修改

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/edit \
  -H "Content-Type: application/json" \
  -d '{"instruction":"副歌更亮一点"}'
```

返回 `version_id`、`edit_spec`、`diff`、`music_spec` 与 `assets`（含 `current_version`）。

### 2. 版本列表

```bash
curl http://localhost:8000/api/v1/songs/{song_id}/versions
```

### 3. 恢复版本

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/versions/{version_id}/restore
```

### 4. 资源状态（含当前版本）

```bash
curl http://localhost:8000/api/v1/songs/{song_id}/assets
```

## 五、前端使用流程

1. 输入一句话生成 MusicSpec，查看摘要 / 段落结构 / 轨道列表
2. 生成 MIDI 并下载
3. 渲染 WAV 并试听（播放 / 暂停 / 下载）
4. 输入自然语言修改指令 → “应用修改”：摘要与播放器自动刷新，展示 diff
5. “查看版本”：列出 v1/v2/…（指令与时间），可一键“恢复此版本”，播放器同步更新

## 六、环境变量

```env
# LLM
LLM_PROVIDER=mock
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=
DEEPSEEK_MODEL=

# 音频渲染（第三阶段）
AUDIO_RENDERER=auto          # auto / fluidsynth / fallback
FLUIDSYNTH_BIN=fluidsynth
SOUNDFONT_PATH=
AUDIO_SAMPLE_RATE=44100
AUDIO_GAIN=0.6
```

## 七、测试

```bash
cd ai-music-mvp
pytest
```

覆盖：第一至三阶段全部回归 + 第四阶段编辑引擎（不可变性 / preserve / 段落目标 / 加去乐器 / 中国风 / diff）与版本 API（v1 初始化、edit 建版本、restore 同步、assets 版本指针、404）。

## 八、当前不支持（第四阶段范围外）

- AI 人声、歌词演唱、音色克隆、VST 插件宿主
- 专业混音母带、DAW 深度集成、实时多人协作

## 九、第五阶段计划

1. 专业混音：轨道音量 / 声像 / 均衡（Web Audio API 或后端 DSP）
2. 音频可视化：波形、频谱、播放进度与段落高亮联动
3. 版本对比 UI：字段级 diff 可视化、分支 / 合并
4. 音质提升：FluidSynth 参数调优、SoundFont 选择器
5. AI 人声 / 歌词演唱（可选）
6. 工程化：Docker、CI、生产部署
