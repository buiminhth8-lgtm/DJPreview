# AI Music MVP

自然语言生成音乐的 MVP 工程。第一阶段实现基础工程骨架、音乐协议、LLM 适配层和 MusicSpec 生成接口：输入一句话，后端通过 LLM Provider 生成结构化的音乐方案（MusicSpec v0.1），前端展示摘要与完整 JSON。

> 本阶段不实现真正 MIDI 生成、WAV 渲染、播放器和版本管理，这些属于后续阶段。

## 一、第一阶段能力

- 后端 FastAPI 服务（健康检查、生成、查询）
- 前端 React + TypeScript + Vite 页面
- 音乐核心协议 `MusicSpec v0.1`
- 音乐修改协议 `MusicEditSpec v0.1`
- `LLMProvider` 抽象接口 + `MockProvider` / `DeepSeekProvider`
- 一句话描述 → MusicSpec 的生成 API
- MusicSpec JSON 校验（Pydantic + 语义校验）
- 项目 JSON 保存（`data/projects/{song_id}/music_spec.json`）
- pytest 测试

## 二、项目结构

```text
ai-music-mvp/
├── apps/
│   └── web/                  # 前端 React + TS + Vite
│       └── src/
│           ├── App.tsx
│           ├── main.tsx
│           ├── api/musicApi.ts
│           └── styles.css
├── services/
│   └── api/                  # 后端 FastAPI
│       ├── main.py
│       ├── routes/songs.py
│       ├── schemas/
│       │   ├── music_spec.py
│       │   ├── music_edit_spec.py
│       │   └── api_models.py
│       ├── dependencies/config.py
│       └── storage/project_store.py
├── packages/
│   ├── llm/                  # LLM 适配层
│   │   ├── base.py
│   │   ├── mock_provider.py
│   │   ├── deepseek_provider.py
│   │   └── factory.py
│   └── music_core/
│       ├── planner/music_planner.py
│       └── validation/spec_validator.py
├── prompts/
│   └── music_planner.md      # LLM 系统提示词模板
├── data/projects/            # 生成的项目 JSON
├── tests/                    # pytest 测试
├── requirements.txt
├── .env.example
└── README.md
```

## 三、后端安装与启动

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

## 四、前端安装与启动

要求：Node.js 18+

```bash
cd apps/web
npm install
npm run dev
```

打开 http://localhost:5173 即可使用。后端地址默认 `http://localhost:8000`，可通过环境变量覆盖：

```bash
# Windows PowerShell
$env:VITE_API_BASE_URL="http://localhost:8000"
# macOS / Linux
# VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## 五、使用 MockProvider（默认）

不配置任何密钥即可跑通全流程。复制 `.env.example` 为 `.env`，保持：

```env
LLM_PROVIDER=mock
```

MockProvider 规则：

- 包含「忧郁 / 悲伤 / 雨夜」→ D 小调，72 BPM
- 包含「欢快 / 明亮」→ C 大调，120 BPM
- 包含「中国风」→ pentatonic 调式
- 默认 32 小节，曲式 intro 4 / verse 8 / chorus 16 / outro 4
- 小调和弦 `Dm - Bb - F - C`，大调和弦 `C - G - Am - F`
- 默认轨道 melody / piano / bass / drums / pad

## 六、使用 DeepSeekProvider

在 `.env` 中配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

说明：

- API Key 只从环境变量读取，代码中不硬编码。
- 调用 OpenAI-compatible Chat Completions 接口，模型必须返回 JSON。
- 若未配置 `DEEPSEEK_API_KEY`，会抛出清晰错误并提示改用 MockProvider。
- 解析失败会返回明确错误信息，服务不会崩溃。

后续可扩展 `OpenAIProvider`、`OllamaProvider`、`LocalModelProvider`：实现 `LLMProvider` 接口并注册到 `packages/llm/factory.py` 即可。

## 七、API 示例

### 1. 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

```json
{ "status": "ok" }
```

### 2. 生成音乐方案

```bash
curl -X POST http://localhost:8000/api/v1/songs/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "生成一段忧郁空灵的钢琴配乐"}'
```

```json
{
  "song_id": "3f0f7f9a-...",
  "music_spec": { "version": "0.1", "title": "...", "...": "..." }
}
```

保存位置：`data/projects/{song_id}/music_spec.json`（UTF-8，中文不转义）。

### 3. 获取音乐方案

```bash
curl http://localhost:8000/api/v1/songs/{song_id}
```

不存在时返回 404。

## 八、测试

```bash
cd ai-music-mvp
pytest -v
```

测试覆盖：MusicSpec 协议校验（含 BPM 越界、缺轨道、段落越界）、MockProvider 规则、生成/查询 API 集成、MusicEditSpec 协议。测试数据写入 `data/test_projects/`，不影响正式数据。

## 九、后续阶段计划

1. **MusicEditSpec 应用**：将修改协议应用到已有 MusicSpec 并重新生成。
2. **MIDI 生成**：把 MusicSpec 渲染为标准 MIDI 文件。
3. **WAV 渲染**：音源 / 合成器渲染音频。
4. **播放器**：Web 端播放、波形展示。
5. **版本管理**：每次修改记录版本与 diff。
6. **更多 LLM Provider**：OpenAI、Ollama、本地模型。
7. **工程化**：Docker、CI、生产部署。
