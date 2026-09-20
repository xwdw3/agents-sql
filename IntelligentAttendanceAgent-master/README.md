# 智能考勤问答 Agent（LangChain + LangGraph + PostgreSQL）

基于《考勤管理制度》的对话式问答系统：自然语言提问 → 受控 LangGraph 流水线 → Text-to-SQL 只读检索 PostgreSQL → 流式回答。支持**员工（仅本人）/ 管理员（全局）**登录与数据范围隔离。

> 详细设计见 `技术方案.md`、`前端Web方案.md`、`方案评审记录-02-深度评审.md`。

## 目录结构

```
main.py                    # FastAPI：静态托管 web/ + /api/login + /api/chat(SSE)
app/
├── config.py / llm.py / schemas.py / prompts.py / auth.py / memory.py
├── graph/                 # LangGraph：state / nodes / build
├── safety/                # input_guard（输入护栏）+ sql_validator（sqlglot AST 只读校验）
├── db/                    # engine（app_ro 只读）/ schema_provider / executor
└── rules/                 # rule_store（制度规则拆分存储）+ fines（确定性罚款）
sql/   02_schema.sql / 03_views.sql
scripts/setup_db.py        # 一次性：建角色 + 建表 + 建视图 + 灌 3 人种子数据
web/   index.html / style.css / main.js   # 纯 HTML 前端（无构建）
Dockerfile / docker-compose.yml / .dockerignore
requirements.txt / requirements-dev.txt
```

## 快速开始

### 1. 配置环境变量
```bash
cp .env.example .env   # 按需修改 PG 连接、DeepSeek Key、运行时角色密码
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 初始化数据库（建角色 app_ro/app_rw + 建表 + 建视图 + 灌数据）
```bash
python scripts/setup_db.py
```
> 用超级用户 `PG_USER` 执行；会创建 `app_ro`（业务只读）/ `app_rw`（checkpointer 读写）两个角色，并灌入 3 名员工 + 1 名管理员账号（动态日期）。

### 4. 启动服务
```bash
uvicorn main:app --reload
```
打开 http://127.0.0.1:8000

### 5. 登录账号
| 账号 | 密码 | 角色 | 数据范围 |
|---|---|---|---|
| zhangsan / lisi / wangwu | 123456 | 普通员工 | 仅本人 |
| admin | admin123 | 管理员 | 全局（无需打卡，无打卡记录） |

## Docker 打包部署

> **仅打包运行镜像，不初始化数据**。数据库初始化在宿主机单独执行：`python scripts/setup_db.py`（见上方「快速开始」）。

```bash
# 构建并启动（PG 连接通过 .env 注入，指向已初始化的外部 PostgreSQL）
docker compose up -d --build

# 查看日志
docker compose logs -f agent

# 停止
docker compose down
```

### 打包镜像（不用 compose）
```bash
docker build -t attendance-agent .
docker run --rm -p 8000:8000 --env-file .env attendance-agent
```

> 说明：镜像入口 `uvicorn main:app --host 0.0.0.0 --port 8000`；`.env` 不打包进镜像（`.dockerignore`），由 `env_file` 注入。

## 关键安全设计

- **输入护栏**：规则黑名单 + LLM 结构化双检，拦截注入/敏感请求。
- **SQL 只读**：sqlglot AST 校验（单语句、仅 SELECT/只读 WITH、表白名单仅视图、函数黑名单、拒 SELECT *、AST 注入 LIMIT）+ LLM 语义复核 + **app_ro 只读角色**兜底。
- **RBAC 强制隔离**：以 `user_id` 为锚点，员工查询强制 `employee_id` 过滤；管理员全局。
- **软删除**：业务数据只查 `v_*` 视图（内固化 `is_deleted/is_enabled` 过滤），校验器拒绝查基表。
- **结果限量**：`statement_timeout` + 自动 LIMIT + 行数/字节硬上限。
- **间接注入**：查询结果 JSON 包裹、仅作事实引用；前端 `textContent` 渲染防 XSS。

## 说明

- 演示为单进程 demo：会话列表存内存，token 用 HMAC（`TOKEN_SECRET` 请在生产更换）。
- checkpointer 优先 `app_rw` 的 PostgresSaver，失败自动回退内存（保证无 checkpoint 表时也能跑）。
