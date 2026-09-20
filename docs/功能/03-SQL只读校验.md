# 功能：SQL 只读校验（SQL Validator）

## 定位
保证 LLM 生成的 SQL **只读、只查白名单视图、无副作用**，是 SQL 安全的最后一道"确定性"闸门。

## 涉及文件
- `app/safety/sql_validator.py` — `validate(sql, max_rows)`、`SqlValidationError`、`ALLOWED_VIEWS` / `FORBIDDEN_FUNCS` / `SENSITIVE_COLUMNS`
- `app/prompts.py` — `SQL_CHECK_PROMPT`（LLM 语义复核）

## 核心逻辑
用 **sqlglot AST（PG 方言）** 做确定性校验：
1. 单语句（拒绝分号多语句）。
2. 仅 `SELECT` / `UNION` / 只读 `WITH`（拒绝 `SELECT INTO`、可写 CTE）。
3. **表白名单**：只允许 `v_` 视图，拒绝 schema 限定（information_schema/pg_catalog）。
4. 函数黑名单（`pg_read_file`/`lo_import`/`dblink`/`pg_sleep` 等）+ 敏感列（`password_hash` 等）。
5. 拒绝 `SELECT *`。
6. AST 注入 `LIMIT`。
- 之后 LLM 语义复核 `{is_read_only, risk_level, reason}`（带静态结论，减少误判）。

## 关键设计点
- 正则做不到的（可写 CTE、`SELECT INTO`、函数名提取）都用 AST 解决。
- `exp.Anonymous` 函数名要取 `f.this`（`sql_name()` 返回 "ANONYMOUS"）。
- **反馈纠错**：校验失败返回结构化错误（含"可用视图仅限…"），喂回 `sql_generate` 重生成。

## 依赖
- `sqlglot`、`app/db/schema_provider.py`（表名白名单来源）。
