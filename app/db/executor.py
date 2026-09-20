"""SQL 执行工具：只读执行 + 结果限量 + 单元格截断。

安全前置：调用方必须先用 sql_validator 校验通过；本层是兜底（只读连接 + 硬上限）。
"""
import json
from typing import Any

from sqlalchemy import text

from ..config import settings
from .engine import ro_engine


def execute(sql: str, max_rows: int | None = None, max_bytes: int | None = None) -> dict[str, Any]:
    max_rows = max_rows or settings.max_rows
    max_bytes = max_bytes or settings.max_result_bytes

    engine = ro_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        rows = result.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        conn.rollback()  # 只读事务，回滚释放

    # 单元格截断 + 字节上限
    data = []
    total_bytes = 0
    for row in rows:
        item = {}
        for c, v in zip(cols, row):
            if v is None:
                item[c] = None
            elif isinstance(v, (str,)):
                item[c] = v[:200]
            else:
                item[c] = v
        data.append(item)
        total_bytes += len(json.dumps(item, ensure_ascii=False, default=str))
        if total_bytes > max_bytes:
            truncated = True
            break

    return {"columns": cols, "rows": data, "truncated": truncated, "row_count": len(data)}
