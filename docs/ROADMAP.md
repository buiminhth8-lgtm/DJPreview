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

## T12 版本资产目录式重构 ⬜

- 目标：每版本独立资产目录（spec / midi / wav / mix / quality）
- 优先级：P1
- 依赖：T05-T06
- 验收标准：版本切换/恢复指向对应目录；旧数据兼容迁移

## T13 版本资产恢复重构 ⬜

- 目标：restore 基于新版本目录恢复并同步根目录资源
- 优先级：P1
- 依赖：T12
- 验收标准：恢复后 assets 与版本一致；测试通过

## T14 工程导入导出适配新版本结构 ⬜

- 目标：`.aimusic.zip` 导入导出适配 T12 目录结构
- 优先级：P1
- 依赖：T12
- 验收标准：roundtrip 通过；zip slip 防护保留

## T15 Evaluation Runner 语义修复 ⬜

- 目标：修正 trait 打分（去重、加权、错误语义）
- 优先级：P2
- 依赖：T10
- 验收标准：报告字段合理；8 个用例全绿

## T16 MIDI Parser / Fallback Renderer 重叠音符修复 ⬜

- 目标：重叠同音 note_on 正确闭合，渲染不产生异常波形
- 优先级：P2
- 依赖：无
- 验收标准：解析测试与 WAV 渲染测试通过

## T17 乐器命名与 GM Program 映射统一 ⬜

- 目标：统一乐器名 → GM program 映射（单一来源）
- 优先级：P2
- 依赖：无
- 验收标准：未知乐器回退默认；映射表测试通过

## T18-T22 音乐质量增强 ⬜

- 目标：旋律动机、和声进行/终止式、能量曲线、节奏模板、编曲密度调优
- 优先级：P2
- 依赖：T16-T17
- 验收标准：质量报告平均分提升；可听性主观验收

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
