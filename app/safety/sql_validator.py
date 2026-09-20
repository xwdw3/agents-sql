"""SQL 只读校验器：sqlglot AST 级校验（替代正则）。

校验要点：
- 单语句、仅 SELECT / 只读 WITH / UNION；
- 表白名单（仅允许视图）、拒绝 schema 限定与系统目录；
- 拒绝 SELECT ... INTO、可写 CTE；
- 函数黑名单（危险系统函数）；
- 拒绝 SELECT *、敏感列；
- AST 级注入 LIMIT。
"""
import sqlglot
from sqlglot import exp

ALLOWED_VIEWS = {
    "v_department",
    "v_employee",
    "v_attendance_record",
    "v_leave_record",
    "v_overtime_record",
    "v_business_trip",
    "v_makeup_card",
    "v_holiday_calendar",
}

FORBIDDEN_FUNCS = {
    "PG_READ_FILE",
    "PG_READ_BINARY_FILE",
    "PG_LS_DIR",
    "LO_IMPORT",
    "LO_EXPORT",
    "DBLINK",
    "PG_SLEEP",
    "PG_TERMINATE_BACKEND",
    "PG_CANCEL_BACKEND",
    "CURRENT_SETTING",
    "SET_CONFIG",
    "QUERY_TO_XML",
    "DATABASE_TO_XML",
}

SENSITIVE_COLUMNS = {"password_hash", "password", "salary"}


class SqlValidationError(Exception):
    """SQL 校验不通过。"""


def _func_name(f: exp.Func) -> str:
    """提取函数名：Anonymous 类型的真实名字在 .this（sql_name() 返回 'ANONYMOUS'）。"""
    if isinstance(f, exp.Anonymous):
        return str(f.this).upper()
    return (f.sql_name() or "").upper()


def _has_bare_star(stmt: exp.Expression) -> bool:
    """检测 SELECT *（聚合函数内的 * 不计）。"""
    selects = [stmt.this, stmt.expression] if isinstance(stmt, exp.SetOperation) else [stmt]
    for s in selects:
        if isinstance(s, exp.Select):
            for e in s.expressions:
                if isinstance(e, exp.Star):
                    return True
    return False


def validate(sql: str, max_rows: int) -> tuple[str, dict]:
    """校验并返回 (最终 SQL, 校验报告)。不通过抛 SqlValidationError。"""
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as e:  # 解析失败
        raise SqlValidationError(f"SQL 解析失败: {e}") from e

    if len(statements) != 1:
        raise SqlValidationError("禁止多语句（分号分隔）")

    stmt = statements[0]

    # 1) 语句类型：仅 SELECT / UNION / 只读 WITH
    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise SqlValidationError(f"仅允许 SELECT 查询，收到: {type(stmt).__name__}")

    # 2) SELECT ... INTO（会建表）
    if isinstance(stmt, exp.Select) and stmt.args.get("into"):
        raise SqlValidationError("禁止 SELECT ... INTO")

    # 3) 可写 CTE
    for cte in stmt.find_all(exp.CTE):
        if not isinstance(cte.this, (exp.Select, exp.Union)):
            raise SqlValidationError("禁止可写 CTE（WITH ... INSERT/UPDATE/DELETE ...）")

    # 4) 表白名单（仅允许视图；拒绝 schema 限定）
    for t in stmt.find_all(exp.Table):
        if t.catalog or t.db:
            raise SqlValidationError(f"禁止 schema 限定表: {t.sql()}")
        name = (t.name or "").lower()
        if name not in ALLOWED_VIEWS:
            raise SqlValidationError(f"表不在白名单（只允许视图）: {name}")

    # 5) 函数黑名单
    bad_funcs = set()
    for f in stmt.find_all(exp.Func):
        name = _func_name(f)
        if name in FORBIDDEN_FUNCS or name.startswith("PG_") or name.startswith("LO_"):
            bad_funcs.add(name)
    if bad_funcs:
        raise SqlValidationError(f"禁止的函数: {sorted(bad_funcs)}")

    # 6) 敏感列
    for col in stmt.find_all(exp.Column):
        if (col.name or "").lower() in SENSITIVE_COLUMNS:
            raise SqlValidationError(f"禁止访问敏感列: {col.name}")

    # 7) SELECT *
    if _has_bare_star(stmt):
        raise SqlValidationError("禁止 SELECT *，必须显式列名")

    # 8) LIMIT 注入（AST 级）
    injected = False
    if isinstance(stmt, exp.Select) and not stmt.args.get("limit"):
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
        injected = True
    elif isinstance(stmt, exp.Union) and not stmt.args.get("limit"):
        raise SqlValidationError("UNION 查询必须显式带 LIMIT")

    final_sql = stmt.sql(dialect="postgres") if injected else sql
    report = {"limit_injected": injected, "tables": sorted({t.name for t in stmt.find_all(exp.Table) if t.name})}
    return final_sql, report
