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
DELETE /api/v1/tasks/{task_id}                        # 取消任务（queued 立即取消；running 标记取消并在检查点中止）
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
cancelled -> 已取消（DELETE /tasks/{task_id}；queued 立即取消，running 在进度检查点中止）
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

## 8. 持久化与并发

- 任务持久化到 `data/tasks/render_tasks.json`（轻量 JSON）；服务重启后重新加载，
  重启前 `queued / running` 的任务会被标记为 `failed`（“服务重启导致任务中断”），不会残留假 running。
- 同一歌曲的渲染在服务内**串行执行**（每首歌一把可重入锁，同步与异步渲染共用），
  避免 MIDI / WAV / stems 文件互相覆盖。

## 9. 当前限制

- **进程内任务队列**：使用 `ThreadPoolExecutor(max_workers=2)`，同一进程内有效。
- 任务已做轻量 JSON 持久化；但重启会中断正在执行的任务（标记为失败），不会恢复执行。
- 默认后端为进程内队列；**生产可选 Celery / Redis 后端**（见下节），默认无需外部依赖。
- 同 `song_id` + 同任务类型去重：已有一个 `queued / running` 任务时返回该任务，避免文件互相覆盖。
- 取消说明：`queued` 任务 DELETE 后立即 `cancelled`；`running` 任务标记 `cancel_requested`，
  在执行进度检查点中止（阻塞在子进程内的渲染可能等待其自然结束，但结果不会被写回成功状态）。

## 10. 生产级任务后端（Celery / Redis，可选）

执行器已抽象为可插拔后端（`services/api/tasks/task_executor.py`）：

```text
TASK_BACKEND 未设置 / inprocess → 进程内 ThreadPoolExecutor（默认，离线可用）
TASK_BACKEND=celery        → Celery + Redis（需单独部署 worker）
```

启用 Celery 后端：

```bash
pip install -r requirements-celery.txt
export TASK_BACKEND=celery
export CELERY_BROKER_URL=redis://localhost:6379/0
celery -A services.api.tasks.celery_app worker --loglevel=info
uvicorn services.api.main:app --port 8000
```

说明：

- worker 与 API 共享同一份 `data/tasks/render_tasks.json` 持久化与任务状态机
  （queued → running → succeeded/failed/cancelled），前端 API 不变。
- 需要多实例部署时，把任务存储迁移到共享存储（如 Redis），并把 API 与 worker 指向同一 broker。
- 默认不安装 celery/redis 依赖；未配置 `TASK_BACKEND=celery` 时完全不影响现有功能。
