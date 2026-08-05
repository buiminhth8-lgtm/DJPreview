# 异步渲染任务（T30）

## 1. 为什么需要异步任务

MIDI / WAV / stems 渲染可能耗时（尤其是分轨 + 真实音源渲染）。同步接口会长时间阻塞请求；
异步任务让前端提交后立即获得 `task_id`，再轮询进度，避免接口超时与页面卡顿。

## 2. API 使用方式

```http
POST /api/v1/songs/{song_id}/tasks/render-midi       # 异步生成 MIDI
POST /api/v1/songs/{song_id}/tasks/render-audio      # 异步渲染 WAV（可选 body {soundfont_id}）
POST /api/v1/songs/{song_id}/tasks/export-stems      # 异步导出 stems
GET  /api/v1/tasks/{task_id}                          # 查询任务
GET  /api/v1/songs/{song_id}/tasks                    # 歌曲任务列表
```

创建任务返回 `202` 与任务对象；随后轮询 `GET /tasks/{task_id}` 直到终态。

```bash
curl -X POST http://localhost:8000/api/v1/songs/{song_id}/tasks/render-audio
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## 3. task status

```text
queued    -> 已创建，等待执行
running   -> 执行中
succeeded -> 成功（progress=100，result 含 assets / metadata）
failed    -> 失败（error 记录原因）
cancelled -> 预留状态（当前未提供取消接口）
```

## 4. progress 约定

```text
0   -> 已创建
10  -> 任务开始
30-60 -> MIDI 编排 / 写入
50-90 -> WAV 渲染 / 元数据
90-100 -> 收尾 / 完成
```

## 5. 前端轮询方式

`useRenderTasks`：启动任务后每 1000ms 轮询一次；`succeeded / failed / cancelled` 停止轮询；
成功后自动刷新资产（播放地址 / 下载地址）；组件卸载停止轮询。

## 6. 失败排查

- 任务 `failed` 时查看 `error` 字段。
- 常见原因：项目不存在、FluidSynth 未安装且 `AUDIO_RENDERER=fluidsynth`、音源缺失。
- 可回退：`AUDIO_RENDERER=fallback` 或 `auto`（自动回退 fallback）。

## 7. 旧同步接口兼容

旧接口保持不变，仍可用：

```text
POST /api/v1/songs/{song_id}/midi/generate
POST /api/v1/songs/{song_id}/audio/render
POST /api/v1/songs/{song_id}/stems/export
```

新异步任务接口为推荐方式（尤其耗时操作）。

## 8. 当前限制

- **进程内任务队列**：使用 `ThreadPoolExecutor(max_workers=2)`，同一进程内有效。
- **服务重启后运行中任务可能丢失**：任务仅保存在内存（`TaskStore`），未做持久化。
- **暂未引入 Redis / Celery / MQ**：如需跨进程 / 多实例，后续可替换为持久化队列。
- 同 `song_id` + 同任务类型去重：已有一个 `queued / running` 任务时返回该任务，避免文件互相覆盖。
- 暂未提供任务取消（`cancelled` 为预留状态）。
