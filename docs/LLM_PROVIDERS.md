# LLM Provider 配置指南（T32）

本工程支持三档 LLM Provider，按测试阶段使用：

```text
mock：默认，稳定回归，不调用外部服务
lmstudio：本地 OpenAI-compatible 服务，用于真实 LLM 本地链路测试
deepseek：线上 DeepSeek，用于最终质量测试
```

## 架构

```text
LLMProvider（抽象基类，packages/llm/base.py）
  ├── MockProvider                   规则驱动，无需网络 / API Key
  └── OpenAICompatibleProvider       OpenAI-compatible 通用实现
        ├── DeepSeekProvider         DEEPSEEK_* 环境变量
        └── LMStudioProvider         LMSTUDIO_* 环境变量
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
3. **deepseek 跑线上最终测试**：全部链路通过后再接入线上 DeepSeek 做最终质量测试。

## 本地健康检查脚本

```bash
python scripts/test_llm_provider.py                          # 默认 mock（离线）
python scripts/test_llm_provider.py --provider mock
python scripts/test_llm_provider.py --provider lmstudio
python scripts/test_llm_provider.py --provider lmstudio \
    --base-url http://localhost:1234/v1 --model local-model
python scripts/test_llm_provider.py --provider lmstudio \
    --generate-spec --song-prompt "生成一首雨夜电影感钢琴曲"
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
4. DeepSeek 仍需真实 API Key；请勿提交密钥。
