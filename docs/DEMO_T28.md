# T28 产品演示指南（Demo Guide）

本文档用于现场 / 离线演示 ai-music-mvp。演示全程使用 **MockProvider**，不依赖真实 DeepSeek API，
不需要 API Key，可离线完成。

## 1. 演示前准备

- Python 3.10+ 与项目依赖已安装（`pip install -r requirements.txt`）。
- Node 20+ 与前端依赖已安装（`cd apps/web && npm ci`）。
- 示例 prompt 文件：`examples/demo_prompts.json`（8 个案例）。
- 演示讲稿：`docs/DEMO_SCRIPT.md`（10-15 分钟节奏）。

## 2. 明确启用 MockProvider

Linux / macOS：

```bash
export LLM_PROVIDER=mock
```

Windows PowerShell：

```powershell
$env:LLM_PROVIDER = "mock"
```

> 默认值就是 mock（`conftest.py` 与 `.env.example` 均以 mock 为默认），
> 只要不显式设置 `LLM_PROVIDER=deepseek` 即可。

## 3. 启动后端

```bash
uvicorn services.api.main:app --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

## 4. 启动前端

```bash
cd apps/web
npm run dev
```

浏览器打开 `http://localhost:5173`（开发代理会把 `/api/v1` 转发到 `http://localhost:8000`）。

## 5. 8 个示例 prompt（演示顺序）

文件：`examples/demo_prompts.json`

| # | id | title | 预期展示点 |
|---|----|-------|-----------|
| 1 | rainy_night_piano | 雨夜电影钢琴 | 忧郁小调、钢琴 + 弦乐 + pad、舒缓 72 BPM |
| 2 | chinese_cinematic | 中国风配乐 | 五声音阶、弦乐铺底、民族氛围 |
| 3 | lofi_hiphop | Lo-fi hiphop | swing、松弛鼓组、电钢 + warm pad |
| 4 | game_battle | 游戏战斗 | 快速、高能量、鼓点强烈 |
| 5 | meditation_ambient | 冥想氛围 | pad 长音、节奏极简、低密度 |
| 6 | pop_ballad | 流行情歌 | 主旋律清晰、副歌增强 |
| 7 | electronic_groove | 电子律动 | four-on-the-floor、低频明显 |
| 8 | rock_theme | 摇滚主题 | 电吉他、贝斯、强劲鼓组 |

## 6. 主流程演示

1. 输入 prompt（例如“生成一首雨夜电影感钢琴曲，情绪忧郁、节奏舒缓、适合片尾独白。”）。
2. 点击“生成 MusicSpec”：查看曲式 / 段落 / 轨道 / 调性 / 速度。
3. 点击“生成 MIDI”：查看轨道数、小节数、BPM，下载 MIDI。
4. 点击“渲染 WAV”：等待渲染完成，播放音频，下载 WAV。
5. 说明：WAV 使用 fallback 渲染器（`AUDIO_RENDERER=fallback`），不依赖 FluidSynth。

## 7. 高级流程演示

1. **修改副歌**：输入“副歌更亮一点” → 应用修改 → 查看 diff。
2. **版本列表**：点击“查看版本”，展示 v1 / v2。
3. **版本 diff**：查看修改字段（如 `form.chorus.energy`、`tempo.bpm`）。
4. **恢复旧版本**：点击“恢复此版本” → 当前版本切换、根目录资产同步。
5. **混音**：在 Mixer 调整 volume / pan / mute，点击应用。
6. **Piano Roll**：查看音符、小节与段落。
7. **Quality Check**：查看评分与问题列表；可执行自动优化。
8. **导出 stems**：分轨 MIDI / WAV 与 `stems.zip`。
9. **导出工程**：下载 `.aimusic.zip`。
10. **导入工程**：上传 `.aimusic.zip`，生成新 song_id。

## 8. 常见失败处理

| 现象 | 处理 |
|------|------|
| 端口被占用 | 换端口：`uvicorn ... --port 8001`，前端 `.env` 或 `VITE_API_BASE_URL` 指向新端口 |
| 依赖未安装 | `pip install -r requirements.txt`；`cd apps/web && npm ci` |
| WAV 渲染失败 | 确认 `AUDIO_RENDERER=fallback`（测试/演示默认）；检查 numpy 是否安装 |
| MockProvider 未启用 | 确认未设置 `LLM_PROVIDER=deepseek`；后端日志应显示 mock 生成 |
| 前端访问后端失败 | 确认后端在 8000 端口运行；检查 Vite proxy（`apps/web/vite.config.*`）与 `VITE_API_BASE_URL` |
| 生成非常慢 | 演示时一次只跑 1-2 个案例；`python scripts/demo_t28_smoke.py` 默认也只跑 2 个 |

## 9. 演示验收 Checklist

- [ ] 后端 `LLM_PROVIDER=mock` 启动，`/api/v1/health` 返回 ok
- [ ] 前端可访问并成功生成 MusicSpec
- [ ] MIDI 生成成功并可下载
- [ ] WAV 渲染成功并可播放 / 下载
- [ ] 自然语言修改生效，diff 可见
- [ ] 版本列表 / diff / restore 可用
- [ ] Mix 应用后播放更新
- [ ] Piano Roll 与 Quality Report 可查看
- [ ] stems 导出可用
- [ ] `.aimusic.zip` 导出 / 导入可用
- [ ] 全程未使用真实 DeepSeek API Key

## 10. 自动化 smoke

```bash
python scripts/demo_t28_smoke.py --base-url http://127.0.0.1:8000
python scripts/demo_t28_smoke.py --all
```

手工走查脚本（bash）：`scripts/demo_t28_walkthrough.sh`。
