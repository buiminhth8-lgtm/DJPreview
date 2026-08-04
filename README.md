# AI Music MVP

自然语言生成音乐的 MVP 工程，已完成六个阶段：

- **第一阶段**：MusicSpec v0.1 / MusicEditSpec v0.1 协议、LLM 适配层（Mock/DeepSeek）、一句话生成 MusicSpec。
- **第二阶段**：MusicSpec → 多轨标准 MIDI（旋律/和弦/贝斯/鼓/pad）。
- **第三阶段**：MIDI → WAV（FluidSynth / fallback）、试听与下载。
- **第四阶段**：自然语言修改 + 版本管理（v1 初始化、每次修改建版本、恢复）。
- **第五阶段**：混音（MixSpec）、分轨导出、Piano Roll、质量检查、自动优化。
- **第六阶段**：风格模板库、Motif/Cadence/Arrangement Curve、局部重生成、参考 MIDI 分析、工程导入导出（.aimusic.zip）、Prompt Registry、批量评估。

> 当前不实现 AI 人声、歌词演唱、音色克隆、VST、专业混音母带、音频转 MIDI 高精度扒谱。

## 一、第六阶段新增能力

- **风格模板库**：8 个内置模板（cinematic_piano / lo_fi_hiphop / pop_ballad / chinese_cinematic / game_battle / ambient_meditation / electronic_pulse / rock_theme）
- **StyleApplier**：模板影响 tempo/mode/scale/tracks/patterns/harmony/energy，支持 `strength` 0-1
- **Motif Engine**：可复现的旋律动机（repeat/sequence/ornament/simplify/intensify 等 8 种变换），MelodyEngine 已接入
- **Cadence Engine**：大调/小调/五声终止式建议与和声增强
- **Arrangement Curve**：段落能量/密度/活跃轨道曲线
- **Regeneration Engine**：section / track / section_track / overall 局部重生成（创建新版本）
- **参考 MIDI 分析**：只提取 tempo/轨道/音域/密度/节奏/能量等高层特征，**不复制旋律**
- **工程导入导出**：`.aimusic.zip`（manifest + music_spec + versions + midi + wav + mix + quality），防 zip slip
- **Prompt Registry**：统一管理 prompts/ 下 5 个模板（music_planner / music_editor / style_planner / reference_planner / evaluation_prompt），带内容哈希版本
- **Evaluation Runner**：8 个内置评估用例，批量生成 + 质量检查 + 特征打分

## 二、风格模板说明

`GET /api/v1/styles` 返回全部模板；生成时传入 `style_template_id` 与 `style_strength`：

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"生成一段雨夜电影钢琴配乐","style_template_id":"cinematic_piano","style_strength":0.8}'
```

模板字段：`default_tempo` / `tempo_range` / `preferred_modes` / `default_tracks` / `harmony_presets` / `rhythm_presets` / `melody_profile` / `arrangement_curve` / `mix_hints`。模板是生成前的高级约束，不替代最终 MusicSpec。

## 三、Motif / Cadence / Arrangement Curve 简介

- **Motif**：按段落生成动机（强拍落和弦音、避免连续大跳），chorus 用 intensify、outro 用 simplify、verse 用 repeat+变奏；`random.Random(seed)` 保证可复现。
- **Cadence**：小调 `iv-V-i` / `VI-VII-i`，大调 `ii-V-I` / `IV-V-I`，中国风 `i-VII-VI-i`；返回和弦均可被解析。
- **Arrangement Curve**：intro 低 → verse 中 → chorus 高 → outro 降；cinematic 动态大、ambient 低密度、game_battle 高密度。

## 四、局部重生成

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/regenerate \
  -H "Content-Type: application/json" \
  -d '{"scope":"section","section_id":"chorus","instruction":"让副歌旋律变化更明显","keep_harmony":true,"variation_strength":0.7,"auto_render":true}'
```

支持 scope：section（只改目标段落）、track（只改目标轨道）、section_track、overall（改 seed）。每次重生成创建新版本，keep_harmony / keep_melody / keep_rhythm 控制保留项。

## 五、参考 MIDI 分析

```bash
# 分析
curl -X POST http://localhost:8000/api/v1/reference/analyze -F "file=@reference.mid"

# 基于参考生成（高层特征融合）
curl -X POST http://localhost:8000/api/v1/songs/generate-from-reference \
  -F "file=@reference.mid" \
  -F "prompt=生成一段类似能量变化但旋律不同的配乐" \
  -F "style_template_id=cinematic_piano" \
  -F "style_strength=0.6"
```

只接受 `.mid / .midi`（≤10MB）。分析输出 bpm、轨道数、音符数、音域、密度、节奏轮廓、能量曲线、可能角色与风格标签。**系统不复制参考旋律或完整和弦进行。**

## 六、工程导入导出（.aimusic.zip）

```bash
# 导出
curl -L http://localhost:8000/api/v1/songs/{song_id}/project/export -o project.aimusic.zip

# 导入（自动分配新 song_id，不覆盖现有项目）
curl -X POST http://localhost:8000/api/v1/projects/import -F "file=@project.aimusic.zip"
```

zip 内包含 manifest.json、music_spec.json、versions/、output.mid、output.wav、audio_metadata.json、mix_spec.json、quality_report.json 等；不含 `.env`、缓存与 `__pycache__`；导入校验 manifest 格式并拒绝 zip slip。

## 七、Evaluation Runner

```bash
# 获取内置用例
curl http://localhost:8000/api/v1/evaluation/cases

# 运行评估（默认不渲染 WAV）
curl -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"case_ids":["cinematic_piano","chinese_cinematic"],"render_audio":false}'
```

每个用例：MockProvider 生成 → 应用模板 → 生成 MIDI → Quality Checker → 特征匹配（tempo_range / mode / has_track_role / style_contains / min_quality_score），输出 EvalReport（总分/通过数/平均分/逐用例结果）。

## 八、Prompt Registry

`packages/llm/prompt_registry.py` 统一管理 `prompts/` 目录：

```python
from packages.llm.prompt_registry import list_prompts, get_prompt, get_prompt_version, render_prompt
```

- `music_planner.md`：自然语言 → MusicSpec
- `music_editor.md`：修改指令 → MusicEditSpec
- `style_planner.md`：描述 → 风格模板选择
- `reference_planner.md`：参考特征 + 描述 → MusicSpec
- `evaluation_prompt.md`：评估打分

版本号 = 内容 SHA-1 前 8 位。

## 九、前端使用流程

1. 输入一句话 + 选择风格模板与强度 → 生成 MusicSpec
2. 生成 MIDI / 渲染 WAV / 试听下载
3. 编曲检查（摘要/段落/轨道/钢琴卷帘/质量/自动优化）
4. 自然语言修改与版本管理
5. 混音器（保存 / 应用并重渲染）
6. 分轨导出（单轨 MIDI/WAV + stems.zip）
7. **局部重生成**（选择 scope/section/track 与参数）
8. **参考 MIDI**：上传分析 → 基于参考生成
9. **工程导入导出**：导出 .aimusic.zip / 导入并切换歌曲
10. **批量评估**：选择用例 → 运行 → 查看报告

## 十、后端安装与启动

```bash
cd ai-music-mvp
python -m venv .venv
pip install -r requirements.txt   # 含 python-multipart
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

覆盖六个阶段全部回归 + 第六阶段 12 个新测试文件（风格库/应用器、Motif、Cadence、重生成、参考分析、工程导入导出、评估、风格/参考/重生成/工程 API）。测试环境 `LLM_PROVIDER=mock`、`AUDIO_RENDERER=fallback`。

## 十二、当前不支持（第六阶段范围外）

- AI 人声、歌词演唱、音色克隆、VST 插件宿主
- 专业混音母带、DAW 深度集成、实时多人协作
- 音频波形级剪辑、音频转 MIDI 高精度扒谱、训练大型音乐模型
- 直接复制参考音乐的旋律或编曲

## 十三、第七阶段计划

1. 真实 LLM 深度接入：DeepSeek 生成 + 风格模板自动选择（style_planner 落地）
2. 音频可视化：波形/频谱、段落高亮联动
3. 钢琴卷帘编辑：拖拽、量化、力度编辑
4. 工程协作：云端同步、多人项目、评论
5. 音质提升：SoundFont 选择器、FluidSynth 参数调优
6. 生产化：Docker、CI、鉴权、存储后端
