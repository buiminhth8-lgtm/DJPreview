# Frontend Workspace QA Checklist

> T38-J 手工 QA 清单。用于验证 T38-A ~ T38-I 前端工作台改版结果。
> 项目无 Vitest / React Testing Library 依赖（仅 Playwright E2E），因此本阶段使用手工 QA 清单，
> 不新增自动测试框架。

## 环境准备

```powershell
# 后端（MockProvider，无 API Key）
cd D:\project\DJPreview\ai-music-mvp
$env:LLM_PROVIDER="mock"
$env:AUDIO_RENDERER="fallback"
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000

# 前端
cd apps\web
npm run dev
```

## First Load（首次打开页面）

- [ ] WorkspaceHeader 可见（标题 + Provider/状态 badges）
- [ ] GenerateConsole 可见
- [ ] ProjectOverviewPanel 可见（无工程时显示 Empty State）
- [ ] PlaybackDownloadPanel 可见（无资产时 Empty State）
- [ ] MusicSpecPanel 可见（无 MusicSpec 时 Empty State）
- [ ] WarningsPanel 可见（无 MusicSpec 时 Empty State）
- [ ] GenerationDebugPanel 可见（无请求时 Empty State）
- [ ] FormHarmonyPanel 可见（无 MusicSpec 时 Empty State）
- [ ] TrackInstrumentPanel 可见（无 MusicSpec 时 Empty State）
- [ ] PianoRollPanel 可见（无 MIDI 时 Empty State）
- [ ] MixerPanel 可见（无工程时 Empty State）
- [ ] StemsPanel 可见（无 MIDI/WAV 时 Empty State）
- [ ] VersionPanel 可见（无工程时 Empty State）
- [ ] EditSongPanel 可见（无工程时 Empty State）
- [ ] SoundfontPanel 可见（无音源时 Empty State）
- [ ] ProjectImportExportPanel 可见（无工程时可导入）
- [ ] RenderTasksPanel 可见（无工程时 Empty State）
- [ ] 页面无全局横向滚动
- [ ] 各模块不是空白，而是 Empty State

## Generation（生成）

- [ ] prompt 为空时「生成 MusicSpec」按钮 disabled，title 提示「请输入音乐描述」
- [ ] 输入 prompt 后按钮可用
- [ ] 点击生成 MusicSpec 后不白屏、无 React error
- [ ] 成功后 ProjectOverviewPanel 显示标题 / BPM / 调性 / 风格 / 段落数 / 轨道数
- [ ] 成功后 MusicSpecPanel 显示摘要 + JSON
- [ ] 成功后 FormHarmonyPanel 显示 timeline + harmony
- [ ] 成功后 TrackInstrumentPanel 显示轨道表
- [ ] WarningsPanel 显示校验警告（有 warning 时）
- [ ] GenerationDebugPanel 显示 request_id / provider / model（有 debug 时）

## MIDI / WAV（播放下载）

- [ ] 无 MIDI 时「下载 MIDI」disabled，原因「当前工程暂无 MIDI」
- [ ] 无 MIDI 时 PianoRollPanel 显示 Empty State，且**不请求** piano-roll endpoint
- [ ] 生成 MIDI 后 Piano Roll 可用，下载 MIDI 可用
- [ ] 无 WAV 时播放器显示 Empty State，下载 WAV disabled，原因「当前工程暂无 WAV 音频」
- [ ] 渲染 WAV 后播放器可用，下载 WAV 可用

## Editing（编辑与生产）

- [ ] MixerPanel 有工程时显示轨道控制（volume / pan / mute / solo）
- [ ] MixerPanel 无工程时 Empty State，不请求 mix endpoint
- [ ] StemsPanel 无 MIDI/WAV 时导出 disabled 并显示原因
- [ ] VersionPanel 有版本时列表、详情、Diff、恢复可用
- [ ] VersionPanel 恢复版本有确认提示（window.confirm）
- [ ] EditSongPanel 无工程时 Empty State；有工程时输入指令后「应用修改」可用
- [ ] 无 song_id 时不请求 mix / versions / edit endpoint

## Utilities（工具与工程管理）

- [ ] SoundFont 扫描无工程时可用
- [ ] 应用 SoundFont 到工程无工程时 disabled，原因「请先生成或导入工程」
- [ ] 导入工程无工程时可用（接受 .aimusic.zip / .zip）
- [ ] 导出工程无工程时 disabled
- [ ] 有工程时导出工程可用，下载 MIDI/WAV/Stems 状态正确
- [ ] RenderTasksPanel 无工程时不请求 tasks endpoint
- [ ] 有工程时有任务时显示任务状态 / 进度 / 错误 / 结果资产

## Network Safety（网络安全）

- [ ] 不出现 `GET /songs/null/...`
- [ ] 不出现 `GET /songs/undefined/...`
- [ ] 不出现 `GET /api/v1/songs//...`
- [ ] 点击 disabled 按钮不发请求

## Responsive（响应式）

在以下宽度检查（DevTools 设备模拟）：

- [ ] 1440px：桌面宽屏，hero 双列
- [ ] 1024px：平板横屏
- [ ] 768px：平板竖屏，hero 单列
- [ ] 390px：手机宽度，全部单列
- [ ] 无全局横向滚动
- [ ] JSON / Debug / 表格 / 长路径不撑破页面
- [ ] 按钮自动换行，不挤成很窄

## 回归确认

- [ ] T38-D：GenerateConsole / ProjectOverviewPanel 正常
- [ ] T38-E：Playback / MusicSpec / Warnings / Debug 正常
- [ ] T38-F：FormHarmony / Track / Piano Roll 正常
- [ ] T38-G：Mixer / Stems / Versions / EditSong 正常
- [ ] T38-H：Soundfont / ImportExport / RenderTasks 正常
- [ ] T38-I：视觉统一、无横向滚动、移动端可用
