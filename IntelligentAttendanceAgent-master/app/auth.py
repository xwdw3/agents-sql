"""登录鉴权 + RBAC 数据范围解析（以 user_id 为唯一身份锚点）。"""
import hashlib
import hmac
import time
from typing import Optional

from sqlalchemy import text

from .config import settings
from .db.engine import ro_engine


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _make_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time())}"
    sig = hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_token(token: str) -> Optional[int]:
    try:
        payload, sig = token.rsplit(".", 1)
        expect = hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        user_id, _ts = payload.split(".", 1)
        return int(user_id)
    except Exception:
        return None


def login(username: str, password: str) -> Optional[dict]:
    """校验 sys_user，返回用户信息 + token（含角色与数据范围）。"""
    engine = ro_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT u.id, u.username, u.display_name, u.employee_id, u.is_admin, u.password_hash, "
                "r.data_scope, r.code AS role_code, r.name AS role_name "
                "FROM sys_user u "
                "LEFT JOIN user_role ur ON ur.user_id = u.id "
                "LEFT JOIN role r ON r.id = ur.role_id "
                "WHERE u.username = :u AND u.is_enabled = TRUE AND u.is_deleted = FALSE"
            ),
            {"u": username},
        ).fetchone()
        conn.rollback()

    if row is None:
        return None
    if _sha256(password) != row.password_hash:
        return None

    user = {
        "user_id": row.id,
        "username": row.username,
        "display_name": row.display_name,
        "employee_id": row.employee_id,
        "is_admin": bool(row.is_admin),
        "data_scope": row.data_scope or "self",
        "role_code": row.role_code,
        "role_name": row.role_name,
    }
    user["token"] = _make_token(row.id)
    return user


def resolve_user(token: str) -> Optional[dict]:
    """从 token 解析当前用户（RBAC 强制隔离的锚点）。"""
    user_id = _verify_token(token)
    if user_id is None:
        return None
    engine = ro_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT u.id, u.username, u.display_name, u.employee_id, u.is_admin, "
                "r.data_scope, r.code AS role_code, r.name AS role_name "
                "FROM sys_user u "
                "LEFT JOIN user_role ur ON ur.user_id = u.id "
                "LEFT JOIN role r ON r.id = ur.role_id "
                "WHERE u.id = :id AND u.is_enabled = TRUE AND u.is_deleted = FALSE"
            ),
            {"id": user_id},
        ).fetchone()
        conn.rollback()

    if row is None:
        return None
    return {
        "user_id": row.id,
        "username": row.username,
        "display_name": row.display_name,
        "employee_id": row.employee_id,
        "is_admin": bool(row.is_admin),
        "data_scope": row.data_scope or "self",
        "role_code": row.role_code,
        "role_name": row.role_name,
    }
