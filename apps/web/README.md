# AI Music MVP 前端

React + TypeScript + Vite 前端，用于生成 MusicSpec、MIDI 与 WAV 试听。

## 安装依赖

```bash
npm install
```

## 启动

```bash
npm run dev
```

打开 http://localhost:5173。

## 配置后端地址

默认 `http://localhost:8000`，可通过环境变量覆盖：

```bash
# Windows PowerShell
$env:VITE_API_BASE_URL="http://localhost:8000"
# macOS / Linux
# VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## 页面能力

- 输入一句话生成 MusicSpec
- 显示 MusicSpec 摘要、段落结构、轨道列表
- 生成 MIDI 并下载
- 渲染 WAV、在线试听（播放/暂停/进度）
- 下载 WAV

> 本阶段不实现音频混音、轨道静音/独奏、自然语言修改与版本管理。
