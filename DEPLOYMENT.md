# 部署说明（GitHub Actions + GHCR + Windows Docker）

本文档覆盖：云端 CI 构建、GHCR 镜像发布、Windows 本地 Docker 部署、更新、回滚、日志、数据持久化与排错。

## 一、云端构建（GitHub Actions）

仓库中的 `.github/workflows/` 提供两个工作流：

- `ci.yml`：push / PR 到 `main` 时运行
  - 后端：Python 3.12 + `pip install -r requirements.txt` + `pytest -q`（`LLM_PROVIDER=mock`、`AUDIO_RENDERER=fallback`）
  - 前端：Node 22 + `npm ci` + `npm run build`
- `docker-publish.yml`：push 到 `main`、打 `v*` 标签或手动触发时
  - 使用 `permissions: packages: write` + `GITHUB_TOKEN` 登录 GHCR
  - 仓库名自动转小写（`${GITHUB_REPOSITORY,,}`），构建并推送：
    - `ghcr.io/<owner>/<repo>/api:latest` 与 `: <sha>`
    - `ghcr.io/<owner>/<repo>/web:latest` 与 `: <sha>`

## 二、Windows 本地 Docker 部署

### 前置条件

- 安装 Docker Desktop for Windows，并启动（WSL2 后端）。
- 本地首次使用 GHCR 需要登录（仅推拉私有镜像时需要；公开镜像可匿名拉取）。

### 1. 本地构建 + 启动（docker-compose.local-build.yml）

```powershell
cd D:\project\DJPreview\ai-music-mvp
Copy-Item .env.docker.example .env.docker

# 构建并启动
docker compose --env-file .env.docker -f docker-compose.local-build.yml up -d --build
```

访问：

- 前端：http://localhost:8080
- 健康检查：http://localhost:8080/api/v1/health（应返回 `{"status":"ok"}`）
- 后端直连（可选）：http://localhost:8000/docs

### 2. 使用 GHCR 远程镜像（docker-compose.prod.yml）

```powershell
# 登录 GHCR（如镜像为私有）
docker login ghcr.io -u <你的GitHub用户名> --password-stdin

# 设置镜像名（与 docker-publish.yml 输出一致，必须小写）
$env:API_IMAGE = "ghcr.io/<owner>/<repo>/api:latest"
$env:WEB_IMAGE = "ghcr.io/<owner>/<repo>/web:latest"

Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker -f docker-compose.prod.yml up -d
```

`docker-compose.prod.yml` 只依赖 `${API_IMAGE}` 与 `${WEB_IMAGE}`，不执行本地构建。

## 三、更新与回滚

```powershell
# 拉取最新镜像并滚动更新
docker compose --env-file .env.docker -f docker-compose.prod.yml pull
docker compose --env-file .env.docker -f docker-compose.prod.yml up -d

# 回滚到指定版本（tag 换成目标 sha 或旧 tag）
$env:API_IMAGE = "ghcr.io/<owner>/<repo>/api:<旧sha>"
$env:WEB_IMAGE = "ghcr.io/<owner>/<repo>/web:<旧sha>"
docker compose --env-file .env.docker -f docker-compose.prod.yml up -d
```

## 四、日志

```powershell
docker compose --env-file .env.docker -f docker-compose.prod.yml logs -f api
docker compose --env-file .env.docker -f docker-compose.prod.yml logs -f web
```

## 五、数据持久化

- 项目数据（MusicSpec / MIDI / WAV / 工程包）保存在命名卷 `runtime-data`（挂载到 `/app/data`）。
- 卷由 Docker 管理：`docker volume ls` 查看，`docker volume inspect ai-music-mvp_runtime-data` 查看详情。
- 如需备份，导出卷内容即可；不要删除卷，否则项目数据丢失。

## 六、排错

- **8080 无法访问**：检查 `docker compose ps` 是否 `Up`；查看 `docker compose logs -f web`。
- **健康检查不是 ok**：查看 `docker compose logs -f api`；确认 `.env.docker` 中 `AUDIO_RENDERER` 至少为 `fallback`。
- **镜像拉取 404 / 认证失败**：确认 GHCR 镜像名小写、仓库为 public（或已 `docker login`）、tag 存在。
- **端口冲突**：8000/8080 被占用时，修改 compose 文件中的端口映射（如 `"8081:80"`）后重启。
- **Windows 防火墙**：首次访问 localhost 端口弹窗时允许 Docker 服务。

## 七、安全说明

- 只提交 `.env.docker.example`，不要把真实 `DEEPSEEK_API_KEY` 写入 `.env.docker` 或提交到 Git。
- `.gitignore` 已忽略 `.env.docker` 与 `runtime-data/`。
- `.dockerignore` 排除了 `.env`、`.env.docker`、`data`、`node_modules`、生成的 mid/wav/zip 等，避免敏感或冗余文件进入镜像。
