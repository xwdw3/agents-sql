# 功能：认证与权限（RBAC）

## 定位
登录鉴权 + 数据范围隔离：员工仅查本人（`self`）、管理员全局（`all`），以 **`user_id` 为唯一身份锚点**。

## 涉及文件
- `app/auth.py` — 登录/鉴权/身份解析
- `app/db/engine.py` — `ro_engine`（app_ro 只读连接，供鉴权查询）
- `sql/02_schema.sql` — `sys_user` / `role` / `user_role` / `chat_session` 表
- `sql/03_views.sql` — `app_ro` 授权（sys_user/role/user_role 只读）
- `sql/04_comments.sql` — 表/字段注释

## 核心逻辑
1. `login(username, password)`：查 `sys_user` → 校验 sha256 密码 → 返回 `{user_id, display_name, role, data_scope, employee_id, token}`。
2. `resolve_user(token)`：HMAC 校验 token → 查 `sys_user`+`role` 得到身份与数据范围。
3. token 用 `HMAC(secret, payload)` 生成/校验，演示级（生产建议 JWT/OAuth）。

## 关键设计点
- **强制隔离**：`data_scope=self` 的员工，SQL 生成强制注入 `employee_id = :current_employee_id`；管理员 `all` 才可全局。
- **管理员不打卡**：`admin` 的 `employee_id=NULL`，考勤表无其记录；问"我的考勤"直接答"管理员无需打卡"。
- 会话按 `user_id` 隔离（`chat_session` 表 + `/api/chat` 归属校验）。

## 依赖
- `app/db/engine.py`（ro_engine）、`app/config.py`（token_secret）。
