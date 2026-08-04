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
```

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

## 当前项目状态

```text
后端测试：pytest -q passed（185 passed，2026-08-04 实测）
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
