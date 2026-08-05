# T28 现场演示讲稿（10-15 分钟）

> 前提：后端已用 `LLM_PROVIDER=mock` 启动，前端 `npm run dev` 已打开。
> 本讲稿按现场节奏编写，可适当裁剪。

## 1. 开场（1 分钟）

“这是 AI Music MVP：输入一句自然语言，就能得到一份结构化的音乐方案（MusicSpec）、
标准 MIDI、可试听的 WAV，并且支持自然语言修改、版本管理、混音、可视化、质量检查、
分轨导出和工程导入导出。”

“当前是 MVP：我们稳定支持生成结构化 MusicSpec、MIDI、WAV、版本、混音与工程导入导出；
暂不支持 AI 人声演唱 / 歌词演唱。”

## 2. Prompt 生成：雨夜电影钢琴（2 分钟）

输入：“生成一首雨夜电影感钢琴曲，情绪忧郁、节奏舒缓、适合片尾独白。”

点击“生成 MusicSpec”，讲解：

- 曲式：intro / verse / chorus / outro。
- 轨道：旋律 / 钢琴 / 贝斯 / 鼓 / pad / 弦乐。
- 调性 D 小调、72 BPM。

## 3. 资产生成：MIDI / WAV（2 分钟）

- 点击“生成 MIDI”，展示轨道数 / 小节数 / BPM，下载 MIDI。
- 点击“渲染 WAV”，等待渲染完成，点击播放；说明 fallback 渲染器无需 FluidSynth。

## 4. 自然语言修改：增强副歌（1.5 分钟）

输入：“副歌更亮一点”，点击“应用修改”。

讲解：系统生成 MusicEditSpec（target=chorus、energy 操作），展示 diff
（例如 `form.chorus.energy: 0.9 → 1.05`）。

## 5. 版本能力：diff / restore（2 分钟）

- 点击“查看版本”，展示 v1 / v2。
- 讲解版本 diff 字段。
- 点击“恢复此版本”，展示当前版本切换、MIDI / WAV 资产同步。

## 6. 分析能力：Piano Roll / Quality（2 分钟）

- 打开 Piano Roll：音符、小节、段落清晰可见。
- 打开 Quality：评分、问题列表、建议；可选执行自动优化。

## 7. 工程能力：stems / .aimusic.zip export / import（2 分钟）

- 导出 stems：分轨 MIDI / WAV + `stems.zip`。
- 导出 `.aimusic.zip`。
- 导入 `.aimusic.zip`：生成新的 song_id，工程完整可用。

## 8. 多风格展示：快速切换（1.5 分钟）

按 `examples/demo_prompts.json` 顺序快速演示 2-3 个风格（中国风、Lo-fi、摇滚），
强调风格差异：调式 / 鼓组 / 贝斯 / 弦乐层次不同。

## 9. 结尾：当前能力与下一步计划（1 分钟）

“当前 MVP 已覆盖：MusicSpec → MIDI → WAV → 修改/版本 → 混音/可视化/质量 → 风格/参考/评估/工程导入导出。
下一步方向：接入真实 LLM（DeepSeek）做更高质量生成、Docker 部署稳定化、更多音源与渲染质量。”

## 异常备用方案

- 生成失败：检查后端日志，确认 `LLM_PROVIDER=mock`；重新加载页面重试。
- WAV 渲染失败：确认 `AUDIO_RENDERER=fallback`；跳过播放，用 MIDI 下载代替。
- 前端连不上后端：检查 8000 端口与 Vite 代理；用 `VITE_API_BASE_URL` 指向正确地址。
