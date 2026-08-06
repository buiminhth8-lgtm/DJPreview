# LLM Provider 配置指南（T32 / T33 / T34）

本工程支持多档 LLM Provider，按测试阶段使用：

```text
mock：稳定回归，不调用外部模型
lmstudio：本地真实 LLM 测试，不消耗线上 API
gemini：Gemini OpenAI-compatible 线上模型测试
deepseek：DeepSeek 线上模型测试
```

Provider 流程建议：`mock -> lmstudio -> gemini -> deepseek`。

## 多环境配置文件按需加载（T33）

支持通过 `LLM_ENV_PROFILE` 选择不同 Provider 配置文件，或通过 `LLM_ENV_FILE` 指定自定义文件：

```text
mock      -> .mock.env
lmstudio  -> .lmstudio.env
gemini    -> .gemini.env
deepseek  -> .deepseek.env
LLM_ENV_FILE -> .custom.env（优先于 profile file）
```

### 推荐工作流

```text
1. 复制 .mock.env.example 为 .mock.env
2. 使用 mock 跑稳定回归
3. 复制 .lmstudio.env.example 为 .lmstudio.env
4. 启动 LM Studio server
5. 用 lmstudio 跑本地真实 LLM 测试
6. 复制 .gemini.env.example 为 .gemini.env
7. 用 gemini 跑 Gemini OpenAI-compatible 线上模型测试
8. 复制 .deepseek.env.example 为 .deepseek.env
9. 最后显式切换 deepseek 测试线上模型
```

### 启动方式

PowerShell：

```powershell
Copy-Item .lmstudio.env.example .lmstudio.env
$env:LLM_ENV_PROFILE="lmstudio"
uvicorn services.api.main:app --reload
```

cmd：

```cmd
set LLM_ENV_PROFILE=lmstudio
uvicorn services.api.main:app --reload
```

bash：

```bash
LLM_ENV_PROFILE=lmstudio uvicorn services.api.main:app --reload
```

使用 `run_with_env.py`（推荐，避免手动设置环境变量）：

```bash
python scripts/run_with_env.py --profile mock -- python -m pytest tests/ -q
python scripts/run_with_env.py --profile lmstudio -- python scripts/test_llm_provider.py --generate-spec
python scripts/run_with_env.py --profile gemini -- python scripts/test_llm_provider.py --generate-spec
python scripts/run_with_env.py --profile deepseek -- python scripts/test_llm_provider.py --generate-spec
python scripts/run_with_env.py --profile lmstudio --print-env   # 只打印加载后的环境（敏感值打码）
```

### 加载优先级

```text
1. .env                      通用默认配置
2. profile env file          .mock.env / .lmstudio.env / .gemini.env / .deepseek.env
3. LLM_ENV_FILE 指定文件      如果设置，优先于 profile file
4. 系统环境变量               最高优先级，不被文件覆盖
```

### 安全规则

1. 不提交真实 `.env` 文件（`.gitignore` 已忽略 `.env` / `.env.*` / `.mock.env` / `.lmstudio.env` /
   `.gemini.env` / `.deepseek.env`）。
2. `.gemini.env` / `.deepseek.env` 包含真实 key，只保留本地；example 文件可提交。
3. 日志不会输出完整 key（`load_env` 只打印文件名；脚本只显示掩码）。
4. Gemini / DeepSeek 只有显式选择对应 profile 时才使用。

## 架构

```text
LLMProvider（抽象基类，packages/llm/base.py）
  ├── MockProvider                   规则驱动，无需网络 / API Key
  └── OpenAICompatibleProvider       OpenAI-compatible 通用实现
        ├── DeepSeekProvider         DEEPSEEK_* 环境变量
        ├── LMStudioProvider         LMSTUDIO_* 环境变量
        └── GeminiProvider           GEMINI_* 环境变量
```

`OpenAICompatibleProvider`（`packages/llm/openai_compatible_provider.py`）封装了
`POST {base_url}/chat/completions`、结构化输出（JSON 提取 → Pydantic 校验 → 二次修复 →
重试）、LLM 调用日志（自动剔除 API Key）等公共逻辑，可复用于任意 OpenAI-compatible 服务
（LM Studio / Ollama / vLLM / LocalAI 等）。

## Provider 环境变量

### mock（默认）

```env
LLM_PROVIDER=mock
```

无需任何配置即可跑通全流程，输出固定可复现，用于离线演示与回归测试。

### lmstudio（本地真实 LLM）

```env
LLM_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_MODEL=your-local-model
LMSTUDIO_TIMEOUT_SECONDS=120
```

- `LMSTUDIO_MODEL` 必须是 LM Studio 中**已加载**的模型名（可在 LM Studio 界面的 Server 标签页查看）。
- `LMSTUDIO_API_KEY` 允许占位值（如 `lm-studio`），LM Studio 不校验。
- 无需真实 DeepSeek API Key。

### gemini（Gemini OpenAI-compatible 线上模型）

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-3.5-flash
GEMINI_TIMEOUT_SECONDS=120
GEMINI_TEMPERATURE=0.2
GEMINI_MAX_TOKENS=1800
GEMINI_REASONING_EFFORT=low
GEMINI_USE_RESPONSE_FORMAT=true
```

- `GEMINI_API_KEY` 为必填；缺失时创建 provider 报 `LLMConfigurationError`。
- `GEMINI_BASE_URL` 默认使用 Gemini OpenAI-compatible base URL（尾部斜杠，拼接时自动去重）。
- `GEMINI_REASONING_EFFORT` 支持 none / minimal / low / medium / high；为空则不发送该字段。
- `GEMINI_USE_RESPONSE_FORMAT=true` 时尝试发送 `response_format` 结构化输出；
  若服务拒绝（HTTP 400/422/404），自动 fallback 到普通 chat completions，
  再走现有 JSON extract / repair / MusicSpec validation。
- 支持 `GET /models` 与 `GET /models/{model}`（`fetch_models` / `retrieve_model`）。
- Gemini OpenAI compatibility 仍处 Beta；不要把 Gemini 输出直接信任为可作曲结果。

### deepseek（线上真实 LLM）

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_real_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
```

- `DEEPSEEK_API_KEY` 为必填；缺失时生成接口返回 `LLM_PROVIDER_ERROR`。
- 不要提交真实 API Key 到仓库（`.env` 已被 `.gitignore` 忽略）。

### openai_compatible（通用）

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=
OPENAI_COMPATIBLE_TIMEOUT_SECONDS=120
```

适用于 Ollama / vLLM / LocalAI 等其它 OpenAI-compatible 服务。API Key 可选。

## 推荐测试顺序

1. **mock 跑测试**：`pytest` 默认 `LLM_PROVIDER=mock`，保证回归稳定。
2. **lmstudio 跑本地真实 LLM**：验证真实 LLM 链路（HTTP / JSON 提取 / 修复 / MusicSpec 校验），
   不产生线上费用。
3. **gemini 跑线上 OpenAI-compatible**：Gemini OpenAI-compatible endpoint 测试线上模型链路。
4. **deepseek 跑线上最终测试**：全部链路通过后再接入线上 DeepSeek 做最终质量测试。

## 本地健康检查脚本

```bash
python scripts/test_llm_provider.py                          # 默认 mock（离线）
python scripts/test_llm_provider.py --provider mock
python scripts/test_llm_provider.py --provider lmstudio
python scripts/test_llm_provider.py --provider lmstudio \
    --base-url http://localhost:1234/v1 --model local-model
python scripts/test_llm_provider.py --provider lmstudio \
    --generate-spec --song-prompt "生成一首雨夜电影感钢琴曲"
python scripts/test_llm_provider.py --profile gemini --list-models
python scripts/test_llm_provider.py --profile gemini --retrieve-model gemini-3.5-flash
python scripts/test_llm_provider.py --profile gemini --generate-spec \
    --song-prompt "生成一首雨夜电影感钢琴曲"
```

脚本输出：provider / base_url / model / HTTP 可达性 / `/models` 结果 / JSON 解析结果 /
MusicSpec 校验结果；失败 exit 1。默认不生成 MIDI/WAV，仅显式传入
`--generate-midi` / `--render-audio` 时写入 `data/tmp_llm_provider_test/`。

## demo smoke 集成

```bash
python scripts/demo_t28_smoke.py --provider mock       # 默认
python scripts/demo_t28_smoke.py --provider lmstudio   # 跑 1 个案例
python scripts/demo_t28_smoke.py --provider deepseek   # 仅显式选择
```

`--provider` 只影响本次脚本的案例数与报告，不修改系统环境；后端需以对应
`LLM_PROVIDER` 启动。脚本只做 HTTP 检查，不直接调用 LLM。

## 限制与注意事项

1. 本地模型输出质量取决于 LM Studio 中加载的模型。
2. 本地模型可能输出非法 JSON / 解释文字 + JSON / markdown 代码块 / 多余注释，
   系统已通过 JSON 提取 + JSONC 清洗 + 二次修复 + Pydantic 校验兜底。
3. LM Studio 不保证音乐质量，只用于验证真实 LLM 链路。
4. Gemini OpenAI compatibility 仍处 Beta；若 `response_format` 不兼容，
   系统会 fallback 到普通 JSON extract / repair；Gemini 输出仍需经过
   MusicSpec normalize / repair / validation，不要直接信任为可作曲结果。
5. DeepSeek / Gemini 仍需真实 API Key；请勿提交密钥。
