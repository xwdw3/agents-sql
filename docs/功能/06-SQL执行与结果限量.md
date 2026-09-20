# 功能：SQL 执行与结果限量（Executor）

## 定位
在只读连接上执行校验通过的 SQL，并做结果限量（行数/字节/单元格截断），防止超大结果拖垮系统与上下文。

## 涉及文件
- `app/db/executor.py` — `execute(sql, max_rows, max_bytes)`
- `app/db/engine.py` — `ro_engine()`（app_ro 只读连接池）

## 核心逻辑
1. 用 `app_ro` 连接执行（`options=-c statement_timeout=5000 -c default_transaction_read_only=on`）。
2. `fetchmany(max_rows+1)` 判断是否超行数 → 截断到 `max_rows`。
3. 单元格字符串截断（200 字符）+ 总字节上限（`max_result_bytes`）。
4. 事务回滚释放（只读不提交）。

## 关键设计点
- 只读连接是**数据库级物理兜底**（写操作在 DB 层直接被拒）。
- 结果以 JSON 返回 `{columns, rows, truncated, row_count}`。
- 打印 `[SQL执行]` 日志便于核对生成的 SQL。

## 依赖
- `app/db/engine.py`、`app/config.py`（statement_timeout_ms / max_rows / max_result_bytes）。
