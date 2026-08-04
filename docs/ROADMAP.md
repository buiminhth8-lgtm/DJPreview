# 路线图（Roadmap）

> 状态说明：✅ 已完成；🔄 进行中；⬜ 未开始。每个任务只记录目标、优先级、依赖、验收标准。

## T01 修复 `.aimusic.zip` 工程导入失败 ✅

- 目标：工程导入路径安全判断跨平台兼容，修复 Linux/macOS 误判越界
- 优先级：P0
- 依赖：无
- 验收标准：合法 zip 正常导入；`../evil.txt` 等 zip slip 被拒绝；专项与全量 pytest 通过

## T02 前端依赖与构建修复 ✅

- 目标：`npm ci` / `npm run build` 可稳定通过，依赖真实可安装
- 优先级：P0
- 依赖：无
- 验收标准：engines 兼容 npm 10+；vite 使用 registry 可安装稳定版；锁文件与 package.json 匹配

## T03 建立基础质量门禁 ✅

- 目标：push / PR 自动验证后端 pytest 与前端构建，并提供本地检查脚本
- 优先级：P0
- 依赖：T02
- 验收标准：CI 文件存在；`scripts/check-all.ps1` / `.sh` 可用；本地全量检查通过

## T04 更新 README 与 Review 状态 ✅

- 目标：README / 项目状态 / 路线图 / Review 摘要与代码状态一致
- 优先级：P0
- 依赖：T01-T03
- 验收标准：README 覆盖启动/测试/能力/限制；docs 三份文档存在且无虚假状态

## T05 补齐版本详情 API ✅

- 目标：`GET /songs/{song_id}/versions/{version_id}` 返回 metadata / music_spec / edit_spec / is_current / assets
- 优先级：P1
- 依赖：T03
- 验收标准：接口返回齐全；404/400 处理；pytest 覆盖

## T06 补齐版本 Diff API ✅

- 目标：`GET /songs/{song_id}/versions/{version_id}/diff` 返回与当前版本的字段级 diff
- 优先级：P1
- 依赖：T05
- 验收标准：diff 方向（old=指定版本，new=当前版本）正确；pytest 覆盖

## T07 `EditSongRequest` 增加 `auto_render` ✅

- 目标：自然语言修改后可选择是否自动重渲染 MIDI/WAV
- 优先级：P1
- 依赖：T04
- 验收标准：请求支持 `auto_render`；默认行为兼容现有接口

## T08 统一 API 错误响应格式 ✅

- 目标：所有错误统一为结构化响应（code / message / detail）
- 优先级：P1
- 依赖：T04
- 验收标准：异常处理器统一；pytest 校验关键错误响应结构

## T09 API Response Model 明确化 ✅

- 目标：消除裸 dict 响应，全部接口使用 Pydantic response_model
- 优先级：P1
- 依赖：T08
- 验收标准：OpenAPI 中无裸 dict 响应；前端类型与后端一致

## T10 MusicSpec 语义校验增强 ✅

- 目标：语义校验（track/section 唯一、重叠、harmony 引用、chord 可解析、key/mode 合法性）接入 API 报告
- 优先级：P1
- 依赖：T09
- 验收标准：生成/一步生成响应附带 `validation`；非法 MusicSpec 在 MIDI 生成时返回 `400 MUSIC_SPEC_VALIDATION_FAILED`
- 实现：`spec_validator.validate_music_spec_semantics` 返回 `ValidationResult{valid, errors[], warnings[]}`，
  覆盖 track/section 唯一性、段落重叠与越界、harmony/enabled_sections 引用、和弦可解析、key/mode/拍号合法性；
  前端 `musicApi.ts` 同步 `ValidationIssue / ValidationResult` 类型；`tests/test_semantic_validator.py` 覆盖

## T11 DeepSeek / LLM Provider 产品化 ✅

- 目标：真实 LLM 接入稳定（JSON 校验、重试、超时、降级）
- 优先级：P1
- 依赖：T10
- 验收标准：Prompt Registry 管理 prompt；`generate_structured` 统一入口；JSON 提取 + Pydantic 校验 + 二次修复；
  LLM 调用日志（不含 API Key）；mock httpx 测试通过；失败返回 `LLM_PROVIDER_ERROR`；MockProvider 行为不变
- 实现：`prompt_registry`（含 `music_spec_generator` / `music_editor` / `json_repair`）、`json_utils`、
  `structured_call`、`call_logger`、`models`；DeepSeekProvider 重构为结构化调用并接入 project_id 日志；
  新增 `tests/test_prompt_registry.py`、`tests/test_llm_json_utils.py`、`tests/test_deepseek_provider.py`、
  `tests/test_llm_call_logger.py`、`tests/test_llm_provider.py`

## T12 版本资产目录式重构 ✅（第一步完成）

- 目标：每版本独立资产目录（spec / midi / wav / mix / quality）
- 优先级：P1
- 依赖：T05-T06
- 验收标准：新项目创建目录式版本（versions/vN/）；旧 vN.json 懒迁移；根目录保留当前版本兼容镜像；
  MIDI / WAV / Mix / Quality / Stems 资产同步到版本目录；现有版本 API 不破坏
- 实现：`packages/music_core/versioning/`（version_migration / version_assets / version_models）；
  `project_store` 新项目 v1 + 编辑 vN 目录式写入；`save_midi_file` / `save_audio_metadata` 自动同步当前版本资产；
  `versions/index.json` 升级 schema_version=2 并写入 path/index/kind/prompt；
  根目录写入 `current.json` / `current_version_id.txt` 兼容指针
- 说明：完整 restore 历史资产同步留到 T13；`.aimusic.zip` 适配新结构留到 T14

## T13 版本资产恢复重构 ✅

- 目标：restore 基于新版本目录恢复并同步根目录资源
- 优先级：P1
- 依赖：T12
- 验收标准：恢复时从 `versions/vN/` 复制完整资产（music_spec / midi / wav / mix / quality / stems），
  缺失资产清理根目录旧镜像，不重新生成 MIDI / WAV；恢复后 assets 与版本一致
- 实现：`version_assets.restore_version_assets_to_current`（restored / removed / missing_optional 摘要）；
  `project_store.restore_version` 返回 (music_spec, summary) 并更新版本指针；
  restore 路由移除 `_regenerate_audio_for`，返回 `restore_summary`；`AssetsResponse` 增加 has_mix / has_quality_report / has_stems

## T14 工程导入导出适配新版本结构 ⬜

- 目标：`.aimusic.zip` 导入导出适配 T12 目录结构
- 优先级：P1
- 依赖：T12
- 验收标准：roundtrip 通过；zip slip 防护保留

## T15 Evaluation Runner 语义修复 ✅

- 目标：修正 `render_audio` 参数语义（false 不渲染、true 渲染 WAV）并完善报告音频字段
- 优先级：P1
- 依赖：T10
- 验收标准：`render_audio=false` 不调用渲染器；`render_audio=true` 使用 renderer factory 渲染 WAV；
  每个 case 记录 audio_rendered / audio_path / renderer / render_error；单个 case 渲染失败不影响整体报告
- 实现：`EvalResult` / `EvalReport` 增加音频字段（audio_rendered / audio_path / audio_duration_seconds /
  renderer / render_error / audio_rendered_cases / audio_failed_cases）；`eval_runner` 为每个 case 建立独立输出目录
  （`data/evaluations/{run_id}/cases/case_NNN_id/`）并按需调用 `get_audio_renderer()`；
  API 默认 `render_audio=false`；新增 `tests/test_evaluation_api.py`

## T16 MIDI Parser / Fallback Renderer 重叠音符修复 ✅

- 目标：重叠同音 note_on 正确闭合，渲染不产生异常波形
- 优先级：P2
- 依赖：无
- 验收标准：解析测试与 WAV 渲染测试通过；同音重叠不丢失；velocity=0 按 note_off；未配对/未关闭不崩溃
- 实现：parser 与 fallback renderer 的活动音符改为 `dict[(channel, note), list[(start_tick, velocity)]]`，
  note_off 按 FIFO pop(0) 配对；fallback 使用 note_on 的 velocity；新增重叠同音 / 多 channel / 边界用例测试

## T17 乐器命名与 GM Program 映射统一 ✅

- 目标：统一乐器名 → GM program 映射（单一来源）
- 优先级：P2
- 依赖：无
- 验收标准：Instrument Registry 统一 canonical id / alias / GM program；MIDI Writer 使用统一映射；
  MockProvider / Style Template 输出可解析乐器；未知乐器回退默认并在语义校验中给 warning；鼓组走 channel 9
- 实现：新增 `packages/music_core/instruments/`（gm.py / registry.py）；
  `midi_writer` / `mix_engine` 改用 `get_gm_program` / `is_drum_instrument`；
  `midi_constants.GM_PROGRAMS` 由注册表生成；MockProvider / Style Library 改用 canonical id；
  `spec_validator` 新增 `UNKNOWN_INSTRUMENT_ALIAS` warning；新增 `tests/test_instrument_registry.py`

## T18-T22 音乐质量增强（T18 旋律 ✅，T19-T22 进行中）

- 目标：旋律动机、和声进行/终止式、能量曲线、节奏模板、编曲密度调优
- 优先级：P2
- 依赖：T16-T17
- 验收标准：质量报告平均分提升；可听性主观验收
- T18 已完成：melodic motif（scale degree 表达）+ question/answer phrase + 段落变奏
  （intro 稀疏 / verse 克制 / pre_chorus 张力 / chorus lift / bridge 对比 / outro 回收）+ 调内量化渲染；
  新增 `composer/melodic_theme.py`、`composer/phrase_builder.py`、`composer/section_planner.py`、
  `analysis/melody_analysis.py`，重写 `melody/melody_engine.py`；确定性与现有 MIDI 输出不受影响

## T23-T25 前端工作台重构 ⬜

- 目标：按“生成 / 播放 / 编辑 / 混音 / 可视化 / 质量 / 导出”分区域重构，状态管理统一
- 优先级：P2
- 依赖：T08-T09
- 验收标准：tsc / build 通过；无功能回归

## T26-T27 Docker / GitHub Actions / GHCR 部署 ⬜

- 目标：镜像构建稳定、发布流程可用、本地部署文档准确
- 优先级：P1
- 依赖：T03
- 验收标准：镜像构建成功；compose 启动后 health 返回 ok

## T28 示例工程与演示脚本 ⬜

- 目标：提供可直接导入的示例 `.aimusic.zip` 与一键演示脚本
- 优先级：P2
- 依赖：T14
- 验收标准：示例导入成功并可试听

## T29 SoundFont / 音源管理增强 ⬜

- 目标：SoundFont 选择、自动发现、回退策略完善
- 优先级：P2
- 依赖：T03
- 验收标准：多 SoundFont 可配置；fallback 兜底正常

## T30 渲染任务异步化与进度反馈 ⬜

- 目标：WAV/stems 渲染异步执行并提供进度
- 优先级：P2
- 依赖：T03
- 验收标准：长任务不阻塞请求；前端展示进度
