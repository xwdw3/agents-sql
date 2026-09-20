# 功能：Docker 部署（Deployment）

## 定位
**仅打包运行镜像，不初始化数据**。数据库初始化在宿主机单独执行。

## 涉及文件
- `Dockerfile` — python:3.10-slim 镜像，入口 `uvicorn main:app --host 0.0.0.0 --port 8000`
- `docker-compose.yml` — 仅 `agent` 服务（build + env_file + ports + restart）
- `.dockerignore` — 排除 .env/.venv/__pycache__/文档等

## 核心逻辑
1. 依赖先行 `COPY requirements.txt` + `pip install`（利用层缓存）。
2. `COPY . .`（.env 被 .dockerignore 排除，由 env_file 注入）。
3. 暴露 8000，启动 uvicorn。

## 关键设计点
- **不初始化数据**：`db-init` 服务已移除；建角色/建表/灌数据在宿主机 `python scripts/setup_db.py` 完成。
- `.env` 不打包进镜像，密钥由 `env_file` 注入。
- 外部 PG（192.168.10.101）连接信息经环境变量传入容器。

## 依赖
- `requirements.txt`、`.env`。
