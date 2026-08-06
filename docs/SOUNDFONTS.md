# SoundFont / 音源管理（T29）

## 1. 什么是 SoundFont

SoundFont（`.sf2` / `.sf3`）是采样音源包，MIDI 渲染器（如 FluidSynth）用它把
program_change / note 事件映射成真实乐器声音。没有 SoundFont 时，本项目使用
**FallbackRenderer**（正弦/三角波合成）保证演示仍可出 WAV。

## 2. 支持格式

- `.sf2`：经典 SoundFont 2
- `.sf3`：压缩 SoundFont（更小，FluidSynth 2+ 支持）
- `.sfz`（可选）：采样描述格式，视渲染器支持而定

## 3. 放置目录

把合法音源放入以下任一目录（后端启动时自动扫描）：

```text
data/soundfonts/
assets/soundfonts/
```

也可以指定 `SOUNDFONT_DIR` 指向其他目录。

> 仓库只保留 `.gitkeep`，**不内置 / 不提交真实音源**。

## 4. 环境变量

```env
# 扫描目录（可选）
SOUNDFONT_DIR=/path/to/soundfonts

# 默认音源（可选，指向具体文件）
SOUNDFONT_PATH=/path/to/FluidR3_GM.sf2

# 默认音源 id（可选，来自 GET /api/v1/soundfonts 的 id）
DEFAULT_SOUNDFONT_ID=xxxx

# 渲染器：auto / fluidsynth / fallback
AUDIO_RENDERER=auto
```

Windows PowerShell：

```powershell
$env:SOUNDFONT_DIR="D:\soundfonts"
$env:AUDIO_RENDERER="auto"
```

## 5. 如何启用 FluidSynth

1. 安装 FluidSynth（`apt install fluidsynth` / `brew install fluid-synth` / Windows 官方二进制）。
2. 准备一个合法 `.sf2`（如 FluidR3_GM，用户自行获取合法音源）。
3. 放到 `data/soundfonts/` 或设置 `SOUNDFONT_PATH`。
4. `AUDIO_RENDERER=auto`（默认）：FluidSynth 可用且找到音源时自动使用，
   否则回退 FallbackRenderer。

## 6. 没有 SoundFont 时

- `GET /api/v1/soundfonts` 返回空列表（不会 500）。
- 渲染仍可用：`AUDIO_RENDERER=fallback` 或 `auto` 回退。
- 前端音源面板会提示“将 .sf2 / .sf3 放入 data/soundfonts/”。

## 7. 版权说明

用户需自行准备合法音源。仓库不内置、不下载商业音源；
请使用有明确许可的音源（如 FluidR3 GM 类公共/免费音源）。

## 8. 常见问题

### 找不到音源

检查 `data/soundfonts/` / `assets/soundfonts/` / `SOUNDFONT_DIR` 是否存在文件，
然后调用 `POST /api/v1/soundfonts/scan` 或前端“重新扫描”。

### 渲染失败

- FluidSynth 未安装：改用 `AUDIO_RENDERER=fallback`。
- 音源损坏 / 路径错误：换一个合法 `.sf2`，或清空 `SOUNDFONT_PATH` 用默认扫描。

### 导入工程后音源 missing

`.aimusic.zip` 只包含 `soundfont.json`（音源引用），不包含真实 `.sf2`。
导入后若本地缺少对应音源，`GET /api/v1/songs/{id}/soundfont` 返回
`available=false` 与 warning；系统不崩溃，可重新选择本地音源。

## 9. 项目级音源

每个项目可保存 `data/projects/{song_id}/soundfont.json`：

```json
{
  "soundfont_id": "default",
  "soundfont_name": "Default SoundFont",
  "renderer": "auto"
}
```

设置接口：

```http
PUT /api/v1/songs/{song_id}/soundfont
{"soundfont_id": "xxx", "renderer": "auto"}
```

恢复版本不会覆盖项目级音源设置。

## 10. 渲染器状态与音质提示（T39-A）

前端「渲染器状态」模块会显示当前 WAV 使用的渲染器 / 音质 / SoundFont：

- **fallback**：quality=preview，显示「当前使用简易 fallback renderer，音色为预览级合成，bass、drums、pad 可能不真实。请选择 SoundFont 并重新渲染 WAV」。
- **FluidSynth + SoundFont**：quality=soundfont，显示 SoundFont 名称与采样音源。
- **FluidSynth 无 SoundFont**：quality=basic，提示选择 SoundFont。
- **未知**：quality=unknown。

metadata 字段（udio_metadata.json / GET /api/v1/songs/{id}/assets 的 udio.metadata）：

`json
{
  "renderer": "fallback",
  "renderer_label": "Fallback Preview Renderer",
  "quality": "preview",
  "soundfont_id": null,
  "soundfont_name": null,
  "soundfont_path": null,
  "renderer_warnings": [{"code": "FALLBACK_RENDERER_QUALITY", "message": "..."}]
}
`

如果听起来像电子蜂鸣音，优先检查前端是否显示 fallback / preview：那是预览级音色，
选择 SoundFont 后需**重新渲染 WAV** 才会生效。
