# AI Music MVP

自然语言生成音乐的 MVP 工程。核心流程：

```text
一句话描述 → MusicSpec → MIDI → WAV → 网页试听 → 自然语言修改 → 版本管理 → 混音 / Piano Roll / 分轨导出 / 质量检查
```

## 当前已完成能力

- 自然语言生成 MusicSpec（一句话 → 结构化音乐方案）
- MockProvider（无 API Key 即可跑通全流程）
- DeepSeekProvider（OpenAI-compatible Chat Completions）
- MusicSpec 生成多轨标准 MIDI（旋律 / 和弦伴奏 / 贝斯 / 鼓组 / Pad）
- MIDI 渲染 WAV（FluidSynth；无 FluidSynth 时 fallback 合成）
- 前端试听与下载 MIDI / WAV
- 自然语言修改音乐（MusicEditSpec 真正执行）
- 版本管理（v1 自动初始化、每次修改建版本、恢复、版本详情与 diff）
- MixSpec 与轨道混音（volume / pan / mute / solo / velocity_scale）
- Piano Roll 数据与前端 SVG 可视化
- 分轨 MIDI / WAV / stems.zip 导出
- Quality Report（结构 / 轨道 / 音域 / 密度 / 和声 / 混音诊断，评分 0-100）
- 自动优化编曲（保守规则优化，创建新版本）
- 风格模板库（8 个内置模板）
- 参考 MIDI 分析（高层特征，不复制旋律）
- 基于参考 MIDI 高层特征生成新项目
- `.aimusic.zip` 工程导入导出（防 zip slip）
- Evaluation Runner（内置 8 个评估用例）
- 基础质量门禁（后端 pytest + 前端 npm ci / build，CI + 本地脚本）

## 当前暂不支持能力

- AI 人声演唱
- 歌词演唱合成
- 音色克隆
- VST 插件宿主
- 专业混音母带
- 音频波形级编辑
- 高精度音频转 MIDI
- 多人协作
- DAW 插件

## 项目结构

```text
apps/web          # React + TypeScript + Vite 前端
services/api      # FastAPI 后端（路由 / 协议模型 / 存储）
packages/llm      # LLM Provider 抽象（Mock / DeepSeek）+ Prompt Registry
packages/renderer # 音频渲染（FluidSynth / Fallback / stems）
packages/music_core # 编曲引擎 / 混音 / 分析 / 风格 / 评估 / 工程 IO
prompts           # LLM 提示词模板
tests             # pytest 测试
data/projects     # 生成的项目数据（gitignored）
scripts           # 本地质量检查脚本（PowerShell / shell）
```

## 后端本地启动

```bash
cd ai-music-mvp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

打开 http://localhost:8000/docs 查看交互式 API 文档。

## 前端本地启动

```bash
cd apps/web
npm ci
npm run dev
```

默认访问 http://localhost:5173。前端 API 默认使用相对路径 `/api/v1`（开发环境由 Vite 代理到后端，Docker 部署由 nginx 转发）；如需指定后端地址：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## MockProvider 与 DeepSeekProvider

开发环境推荐默认：

```env
LLM_PROVIDER=mock
AUDIO_RENDERER=fallback
```

DeepSeek 配置示例（不要提交真实 API Key）：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
```

### T11：LLM Provider 产品化

- **Prompt Registry**（`packages/llm/prompt_registry.py`）：统一读取 `prompts/` 目录，
  新增 `music_spec_generator.md`、`music_editor.md`、`json_repair.md`，支持 `{变量}` 渲染。
- **结构化调用**：`LLMProvider.generate_structured(system_prompt, user_prompt, response_model, task_name, ...)`，
  DeepSeekProvider 为核心实现；MockProvider 提供规则版（不依赖网络 / API Key）。
- **JSON 提取与二次修复**：`packages/llm/json_utils.py` 支持纯 JSON、```json 代码块、前后带文本；
  `packages/llm/structured_call.py` 在解析或 Pydantic 校验失败时调用 `json_repair` 提示词修复，最多重试 2 次，
  仍失败抛 `LLMOutputError`。
- **LLM 调用日志**：`packages/llm/call_logger.py` 记录 provider、model、prompt、响应、耗时、错误、解析结果。
  有 `project_id` 时写入 `data/projects/{project_id}/llm_calls/`，否则写入 `data/llm_calls/`；
  **日志自动剔除 API Key / Authorization，不会提交到 Git。**
- **错误响应**：API Key 缺失 / 网络失败 / 输出解析失败统一返回 `LLM_PROVIDER_ERROR`。
- **安全**：不要提交真实 API Key；`.env` 已被 `.gitignore` 忽略。

> MockProvider 仍是默认开发模式：`LLM_PROVIDER=mock` 时无需任何 API Key 即可跑通全流程。

## 测试与质量检查

Windows PowerShell：

```powershell
.\scripts\check-backend.ps1
.\scripts\check-frontend.ps1
.\scripts\check-all.ps1
```

Linux / macOS：

```bash
./scripts/check-backend.sh
./scripts/check-frontend.sh
./scripts/check-all.sh
```

手动执行：

```bash
pytest -q
cd apps/web
npm ci
npm run build
```

说明：后端测试默认 `LLM_PROVIDER=mock`、`AUDIO_RENDERER=fallback`；前端构建不调用真实后端；CI（`.github/workflows/ci.yml`）会在 push（main / master）与 pull request 时自动运行。

## 主要 API 示例

```http
GET  /api/v1/health
POST /api/v1/songs/generate
POST /api/v1/songs/{song_id}/midi/generate
POST /api/v1/songs/{song_id}/audio/render
POST /api/v1/songs/{song_id}/edit
GET  /api/v1/songs/{song_id}/versions
GET  /api/v1/songs/{song_id}/versions/{version_id}
GET  /api/v1/songs/{song_id}/versions/{version_id}/diff
GET  /api/v1/styles
POST /api/v1/reference/analyze
GET  /api/v1/evaluation/cases
```

更完整的接口清单请查看 http://localhost:8000/docs。

版本详情示例：

```bash
curl http://localhost:8000/api/v1/songs/{song_id}/versions/v1
```

返回 `song_id`、`version_id`、`is_current`、`metadata`、`music_spec`、`edit_spec`、`diff`（相对父版本）与 `assets`。

编辑接口支持 `auto_render`：

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/edit \
  -H "Content-Type: application/json" \
  -d '{"instruction":"把副歌改得更激烈","auto_render":false}'
```

说明：

- `auto_render=true`（默认）：编辑后自动重新渲染 WAV，兼容旧客户端。
- `auto_render=false`：编辑后跳过 WAV 渲染（仍重新生成 MIDI），适合快速编辑与批量修改，不会覆盖已有 `output.wav`。
- 响应新增 `auto_render` 与 `audio_rendered` 字段，明确标记本次是否执行了音频渲染。

版本 diff 示例：

```bash
curl http://localhost:8000/api/v1/songs/{song_id}/versions/v2/diff
```

返回 `song_id`、`version_id`、`parent_version_id`、`is_current`、`diff`（相对父版本）、`metadata` 与 `warnings`。

## API 错误响应

主要业务接口统一返回结构化错误：

```json
{
  "error_code": "PROJECT_NOT_FOUND",
  "message": "项目不存在",
  "details": {}
}
```

常见错误码：

```text
PROJECT_NOT_FOUND       项目不存在
VERSION_NOT_FOUND       版本不存在
ASSET_NOT_FOUND         资源不存在（MIDI / WAV / stems 等）
INVALID_REQUEST         请求无效（非法参数、非法 song_id 等）
INVALID_PROJECT_BUNDLE  工程文件无效
MUSIC_SPEC_VALIDATION_FAILED  MusicSpec 校验失败
LLM_PROVIDER_ERROR      LLM 调用失败
RENDER_FAILED           音频渲染失败
INTERNAL_ERROR          服务器内部错误
```

## API Schema（OpenAPI）

主要接口已补齐 Pydantic `response_model`，可通过 FastAPI 自动生成的 OpenAPI 文档查看核心接口响应结构：

```text
http://localhost:8000/openapi.json
```

核心接口（生成 / 获取 / 编辑 / 版本列表 / 版本详情 / 版本 diff / 混音 / 质量 / 风格 / 参考 / 评估）均定义了稳定的响应模型。

## MusicSpec 语义校验（errors / warnings）

`packages/music_core/validation/spec_validator.py` 提供统一语义校验入口 `validate_music_spec_semantics`，
返回 `ValidationResult { valid, errors[], warnings[] }`，每条问题包含 `code / message / path / details`。
生成 / 一步生成（MIDI / 音频）接口会在响应中附带 `validation` 字段；`POST /api/v1/songs/{song_id}/midi/generate`
在 MusicSpec 非法时返回 `400 MUSIC_SPEC_VALIDATION_FAILED` 并附带错误明细。

校验清单（errors）：

```text
EMPTY_TRACKS                  tracks 为空
EMPTY_FORM                    form 为空
EMPTY_HARMONY                 harmony 为空
DUPLICATE_TRACK_ID            track_id 重复
DUPLICATE_SECTION_ID          section.id 重复
SECTION_OVERLAP               段落小节范围重叠
SECTION_OUT_OF_RANGE          段落超出整曲小节范围
UNKNOWN_HARMONY_SECTION       harmony.section 引用不存在的段落
UNKNOWN_ENABLED_SECTION       enabled_sections 引用不存在的段落
INVALID_CHORD_SYMBOL          和弦符号无法解析
INVALID_KEY                   非法调性主音
INVALID_MODE                  非法调式
INVALID_METER_DENOMINATOR     非法拍号分母
```

校验清单（warnings，不阻断生成）：

```text
SECTION_COVERAGE_GAP          存在未被任何段落覆盖的小节
```

## 版本资产目录式结构（T12 第一步）

- 新项目创建后即初始化目录式版本：`versions/v1/version_metadata.json` + `music_spec.json`，
  根目录写入 `current.json` 与 `current_version_id.txt`，`versions/index.json` 升级为 `schema_version=2`。
- 编辑 / 优化 / 重生成创建 `versions/vN/`，保存 `version_metadata.json`、`music_spec.json`、
  `edit_spec.json`、`diff.json`，并同步 MIDI / WAV / Mix / Quality / Stems 资产。
- 旧项目（`versions/vN.json` 快照）在首次访问版本接口时自动懒迁移为目录式，旧文件保留为兼容备份。
- 根目录继续保留当前版本兼容镜像（music_spec.json / output.mid / output.wav / mix_spec.json 等），现有 API 不受影响。
- 完整的历史资产恢复（restore 时复制 MIDI / WAV / Mix / Stems）将在 T13 完成；
  `.aimusic.zip` 工程导入导出完整适配新结构将在 T14 完成。

## 版本恢复完整资产（T13）

- `POST /api/v1/songs/{song_id}/versions/{version_id}/restore` 现在会从 `versions/vN/`
  复制该版本的完整资产（music_spec / output.mid / output.wav / audio_metadata / mix_spec / quality_report / stems）
  到根目录当前版本镜像，并更新 `current_version_id.txt`、`versions/index.json` 与 `current.json`。
- **恢复时不重新生成 MIDI、不重新渲染 WAV**，只基于版本目录已有资产复制/清理。
- 如果目标版本缺少某项可选资产，根目录对应的旧资产会被清理（例如恢复到无音频版本会删除旧 `output.wav`，
  `GET /assets` 返回 `has_audio=false`，下载接口返回 `ASSET_NOT_FOUND`）。
- 恢复接口返回 `restore_summary`（restored / removed / missing_optional）与 `has_mix / has_quality_report / has_stems` 状态。
- 旧 `versions/vN.json` 结构在恢复前自动迁移为目录式，旧文件保留。

## Evaluation 音频渲染开关（T15）

- `POST /api/v1/evaluation/run` 的 `render_audio` 参数语义已明确：
  - `render_audio=false`（默认）：只生成 MusicSpec + MIDI + QualityReport，**不调用任何音频渲染器**；
  - `render_audio=true`：额外使用现有 renderer factory（测试环境 `AUDIO_RENDERER=fallback`）渲染 WAV，
    每个 case 输出到独立目录 `data/evaluations/{run_id}/cases/case_NNN_id/`。
- 每个 case 记录 `audio_rendered`、`audio_path`、`audio_duration_seconds`、`renderer`、`render_error`；
  report 记录 `audio_rendered_cases` / `audio_failed_cases`。
- 单个 case 音频渲染失败不会导致整轮评估失败，失败信息记录在该 case 的 `render_error` 与 warnings 中。

```bash
curl -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"render_audio": true}'
```

> 测试环境推荐 `AUDIO_RENDERER=fallback`，无需安装 FluidSynth。

## MIDI 重叠音符解析与渲染（T16）

- MIDI Parser（`packages/music_core/analysis/midi_parser.py`）与 Fallback Renderer
  （`packages/renderer/fallback_renderer.py`）改用 **list + FIFO** 记录活动音符：
  同一 `(channel, note)` 的多个 `note_on` 不再互相覆盖，同音高重叠可解析/渲染出多个音符。
- `note_on velocity=0` 按 MIDI 规范等价于 `note_off`。
- 未配对 `note_off` 与文件结束仍未关闭的 `note_on` 均不崩溃（未关闭 note 按现有行为丢弃）。
- Piano Roll、Quality Checker、Evaluation 均基于修复后的 parser，重叠音符数据更准确。

## 统一乐器注册表（T17）

- 新增 `packages/music_core/instruments/`：统一 **canonical instrument id**、**alias 映射** 与 **0-based GM program**。
- 常见别名解析：`piano -> acoustic_grand_piano`、`strings -> string_ensemble_1`、
  `bass -> electric_bass_finger`、`drums -> standard_drum_kit`、`pad / synth_pad -> pad_2_warm`；
  支持大小写、空格、短横线归一化。
- MIDI Writer 与 MixEngine 统一使用 `get_gm_program()` / `is_drum_instrument()`；
  drum 乐器（`standard_drum_kit`）不写 melodic program，走 GM drum channel 9。
- MockProvider 与内置 Style Template 已改用 canonical 乐器名；未知乐器在语义校验中产生
  `UNKNOWN_INSTRUMENT_ALIAS` **warning**（不阻断生成），MIDI 生成时回退默认音色（program 0）。

## 旋律质量增强（T18）

- 新增 melodic motif（1～2 小节，scale degree 表达，强拍落和弦音）与主题循环 A / A' / B / A''。
- question / answer phrase：question 结尾落在不稳定度（2/5/7），answer 结尾落在稳定音（1/3/5/和弦音）。
- 段落变奏：intro 稀疏低音区、verse 克制主题陈述、pre_chorus 上行张力、chorus 音区/力度/密度提升、
  bridge 轮廓对比变奏、outro 回收主题并以稳定音收尾。
- 旋律渲染时按 key/mode 量化到调内音（90%+ 调内、强拍优先和弦音），velocity 随段落与拍位变化；
  使用 `music_spec.seed` 确定性随机，同一 seed 结果可复现。
- 新增轻量旋律分析辅助（`analysis/melody_analysis.py`）：motif_repetition_score / phrase_balance_score /
  chorus_lift_detected / outro_theme_recall_detected（不改变 QualityReport 结构）。

## 和声质量增强（T19）

- 新增功能和声模型与进行库（`composer/harmony_models.py`、`composer/harmony_progressions.py`）：
  major / minor 常见进行、lo-fi / cinematic / chinese 模板。
- 新增罗马数字转换（`theory/roman_numerals.py`）：`I / ii / IV / V / vi / i / iv / VI / VII` 及
  `maj7 / m7 / 7 / sus2 / sus4 / add9 / 6 / dim / m7b5` 后缀，minor 中 V/V7 使用 harmonic minor 属和弦。
- Chord Parser 补齐 `add9 / 6 / dim / m7b5`；`sus4` 不含三音、`add9` 保留三和弦加九音、`maj7` 与 `7` 区分。
- 终止式：authentic（V/V7→I/i）、half（ii/IV→V）、plagal（IV→I）、deceptive（V→vi/VI）。
- `build_bar_harmony` 段落感知补强：verse 结尾 half、pre_chorus 结尾 dominant、chorus 结尾 authentic、
  bridge 用对比性进行 + deceptive、outro 回到 tonic；lo-fi 风格自动上色（maj7/m7/7）。
- 语义校验新增 `WEAK_SECTION_CADENCE` / `REPETITIVE_CHORD_PROGRESSION` **warning**（不阻断生成）；
  轻量和声分析辅助 `analysis/harmony_analysis.py`（cadence_score / harmonic_variety_score /
  chord_symbol_validity / section_tension_curve_detected）。

## 鼓组 groove 增强（T20）

- 风格化 groove：pop / rock / lo-fi（syncopated kick + ghost snare + swing 0.62）/ cinematic（稀疏低频 + tom）/
  chinese（tom 模拟民族鼓）/ electronic（four-on-the-floor + offbeat hats）。
- 段落强度：intro 仅 kick/hat 低力度、verse 基础 groove、pre_chorus 密度提升 + 段落末 fill、
  chorus 最强（crash 标记段首、力度 +8）、bridge 去 crash/ride 加 tom 对比、outro 收束（kick + 轻 hat）。
- fill：段落末尾（verse / pre_chorus / bridge / outro）与 chorus 每 8 小节，使用 snare / tom / hat 16th 填充，不越界。
- swing（`theory/rhythm.apply_swing`）：lo-fi 默认 0.62 后移 offbeat，pop/rock straight，不产生负时间。
- velocity accent：downbeat kick / snare 2-4 高力度、ghost snare 25-45、hat 强弱交替、段落力度修正，全部 clamp 1-127。
- 统一 GM drum note（kick 36 / snare 38 / clap 39 / toms / hats / crash 49 / ride 51），走 MIDI channel 9、
  不写 melodic program；MIDI Writer / Fallback Renderer / Evaluation 均不受影响。
- 轻量节奏分析辅助 `analysis/rhythm_analysis.py`（drum_density_score / section_fill_detected /
  chorus_intensity_lift_detected / swing_feel_detected / velocity_variation_score）。

## 贝斯 groove 增强（T21）

- 风格化贝斯型：pop（root/fifth/octave，跟随 kick）、rock（8 分音符 driving）、lo-fi（syncopated + swing 0.62）、
  cinematic（低频长音 + 少量 octave movement）、chinese（稳定根音/五度 + 低鼓呼应）、electronic（offbeat 插空）。
- 段落强度：intro 长根音低力度、verse 基础 groove、pre_chorus 密度提升 + 末小节 approach、
  chorus 最强（octave jump、力度 +10）、bridge 对比（低密度）、outro 回 tonic 收束。
- 和声关系：强拍优先和弦根音，次强拍 fifth/octave，弱拍调内 passing tone，段落衔接 approach note；
  复杂和弦（maj7/sus/add9）通过 chord parser 提取 root 与稳定和弦音。
- kick 对齐：默认使用风格隐含 kick 拍位；也可传入 DrumEngine 输出提取的 kick positions
  （`extract_kick_positions`），主要 kick 附近补根音，chorus 对齐率不低于 verse。
- 音区：统一 36-52（E2-E3，满足 ≥24 / ≤64 约束）；velocity：root 高、fifth/octave 中、passing -15、approach -10、
  ghost 30-50，段落力度修正（chorus +10 / outro -10 等），clamp 1-127。
- bass 走 melodic channel（非 9），program 由 T17 registry 解析（electric_bass_finger→33 / synth_bass_1→38）；
  MIDI Writer / Fallback Renderer / Evaluation 不受影响。
- 轻量贝斯分析辅助 `analysis/bass_analysis.py`（bass_root_support_score / bass_kick_alignment_score /
  bass_motion_score / chorus_bass_lift_detected / bass_range_validity）。

## 弦乐 / Pad 编曲增强（T22）

- 新增 chord voicing（`composer/voicing.py`）与平滑 voice leading（`composer/voice_leading.py`）：
  按 register 生成 3-4 声部和弦排列，相邻和弦声部移动最小化、共同音保持、避免声部交叉；
  支持 maj7 / m7 / 7 / sus / add9 等扩展和弦。
- StringsEngine（`arrangement/strings_engine.py`）：sustained 长音 / light rhythmic stab /
  cinematic ostinato；intro 稀疏（2 声部）、verse 薄（3 声部低力度）、pre_chorus build（上行句 + 渐强）、
  chorus 加厚（4 声部 + 高音层，力度最高）、bridge 对比 register、outro thinning（2 声部 + 渐弱）。
- PadEngine（`arrangement/pad_engine.py`）：长音和弦铺底（长音比例 ≥0.5），voice leading 平滑；
  verse 薄、pre_chorus 增厚 + build、chorus 4 声部 + 高八度 layer、bridge 暗色 register、outro thinning。
- 音区冲突规避：pad 48-76、strings 55-84，高于 bass（24-64）且避开 melody 核心区；
  velocity 随段落变化（verse 低 / chorus 高 / outro 渐弱），clamp 1-127。
- composer 已把 pad / strings 轨道路由到专用引擎；program 来自 T17 registry
  （pad_2_warm→89、string_ensemble_1→48）；MIDI Writer / Fallback Renderer / Evaluation 不受影响。
- 轻量编曲分析辅助 `analysis/arrangement_analysis.py`（voice_leading_smoothness_score /
  arrangement_density_curve / chorus_layer_lift_detected / pad_register_validity /
  strings_register_validity / section_entry_exit_score）。

## 前端 API 层拆分（T23）

- `apps/web/src/api/` 按领域拆分：`client.ts`（统一 base URL / T08 错误解析 / apiFetch / apiDownloadBlob /
  ApiRequestError / resolveUrl）、`types.ts`（全部共享请求/响应类型）、`songApi.ts`、`versionApi.ts`、
  `audioApi.ts`、`mixApi.ts`、`analysisApi.ts`、`referenceApi.ts`、`evaluationApi.ts`、`projectApi.ts`、
  `styleApi.ts`、`index.ts`（统一导出）。
- `musicApi.ts` 保留为兼容 re-export 层，现有组件 `import { ... } from "./api/musicApi"` 不受影响；
  本阶段不改 UI 调用点，不拆 hooks（T24）不做布局重构（T25）。
- `VITE_API_BASE_URL` 可配置、默认相对路径 `/api/v1`；FormData 请求不设 JSON Content-Type；
  文件下载走 `apiDownloadBlob`，不被 JSON 解析。

## 前端状态拆分（T24）

- App 状态拆分到 `apps/web/src/hooks/`：`useSongProject`（songId / musicSpec / prompt / 编辑指令 /
  生成 / 读取 / 编辑 / 重置）、`useAudioAssets`（MIDI / WAV / assets / 下载 URL）、
  `useVersions`（版本列表 / 详情 / diff / 恢复）、`useMixer`、`useQuality`、`useEvaluation`、
  `useReferenceMidi`、`useStyles`（风格选中）。
- `App.tsx` 保留现有 UI 结构与交互流程，直接 API 调用移除，通过 hooks 编排联动
  （生成→加载、编辑→刷新版本/资产、MIDI/WAV→刷新资产、恢复→刷新歌曲/资产/版本）。
- 各 hook 有独立 loading / error 状态，复用 T23 API 模块与统一错误解析（`getErrorMessage`）。

## 前端工作台布局（T25）

- `apps/web/src/components/workspace/`：WorkspaceLayout（两栏栅格：左生成/编辑/导入导出，右播放/版本/混音/分析，
  底部参考/评估/重生成）、WorkspaceHeader（song_id / 版本 / MIDI / WAV 状态）、GeneratePanel、PlayerPanel、
  EditPanel、VersionPanel、MixerPanel、AnalysisPanel、ReferencePanel、EvaluationPanel、ProjectPanel、
  StatusMessage（error / success / warning）。
- `App.tsx` 收敛为组合层：仅保留 hooks 调用、状态组合与跨模块回调（恢复→刷新歌曲/资产/版本等）。
- 未改后端接口、未重写 hooks / 业务逻辑；styles.css 增加工作台栅格、状态芯片与移动端单列。

## T28 Demo（离线可复现演示）

- 全程使用 **MockProvider**（默认），无需 DeepSeek API Key：`export LLM_PROVIDER=mock`（PowerShell：`$env:LLM_PROVIDER="mock"`）。
- 8 个示例 prompt：`examples/demo_prompts.json`（雨夜电影钢琴 / 中国风 / Lo-fi / 游戏战斗 / 冥想 / 流行情歌 / 电子 / 摇滚）。
- 演示指南：`docs/DEMO_T28.md`；现场讲稿：`docs/DEMO_SCRIPT.md`。
- 自动化 smoke（默认 2 案例，`--all` 全跑）：

```bash
python scripts/demo_t28_smoke.py --base-url http://127.0.0.1:8000
python scripts/demo_t28_smoke.py --all
```

- 手工走查（bash）：`scripts/demo_t28_walkthrough.sh`。
- 启动：后端 `uvicorn services.api.main:app --port 8000`，前端 `cd apps/web && npm run dev`。

## SoundFont / 音源管理（T29）

- 支持 `.sf2` / `.sf3`（可选 `.sfz`）音源，自动扫描 `data/soundfonts/`、`assets/soundfonts/` 或 `SOUNDFONT_DIR`。
- 无音源时系统不崩溃：fallback renderer 仍可用；有音源 + FluidSynth 可用时使用指定音源渲染。
- 项目级音源选择：`GET/PUT /api/v1/songs/{song_id}/soundfont`，设置保存在 `soundfont.json`（不含真实音源文件，
  恢复版本不覆盖；`.aimusic.zip` 只含引用 metadata）。
- 风格模板提供 `soundfont_hint` / `preferred_soundfont_tags`（仅提示，不强制）。
- 前端音源面板：列表 / 重新扫描 / 项目选择 / missing 提示（放入 `data/soundfonts/` 后重扫）。
- 详见 [docs/SOUNDFONTS.md](docs/SOUNDFONTS.md)（含版权说明与常见问题）。

## 当前项目状态

```text
后端测试：pytest -q passed（432 passed，2026-08-04 实测）
前端依赖：npm ci passed
前端构建：npm run build passed
```

详细状态见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)，路线图见 [docs/ROADMAP.md](docs/ROADMAP.md)，Review 归纳见 [docs/REVIEW_SUMMARY.md](docs/REVIEW_SUMMARY.md)。

## 云端构建 / Docker 部署

GitHub Actions 云端构建、GHCR 镜像发布与 Windows 本地 Docker 部署说明见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 下一阶段计划

1. `EditSongRequest` 增加 `auto_render`
2. 统一 API 错误响应格式
3. API Response Model 明确化
4. MusicSpec 语义校验接入 API / 生成链路
5. DeepSeek / LLM Provider 产品化
6. 版本资产目录式重构
7. 音乐生成质量增强（重叠音符、乐器映射等）
8. 前端工作台重构
9. Docker / GHCR 部署稳定化
10. SoundFont / 音源管理与渲染异步化
