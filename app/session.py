"""会话管理：chat_session 表（user_id ↔ thread_id 映射）+ 建立/列表/归属校验。"""
from sqlalchemy import text

from .db.engine import rw_engine


def create_session(user_id: int, thread_id: str, title: str | None = None) -> None:
    with rw_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_session (thread_id, user_id, title) "
                "VALUES (:thread_id, :user_id, :title)"
            ),
            {"thread_id": thread_id, "user_id": user_id, "title": title},
        )


def list_sessions(user_id: int) -> list[dict]:
    with rw_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT thread_id, title, created_at FROM chat_session "
                "WHERE user_id = :user_id AND is_enabled = TRUE AND is_deleted = FALSE "
                "ORDER BY created_at DESC"
            ),
            {"user_id": user_id},
        ).fetchall()
        conn.rollback()
    return [
        {"thread_id": r.thread_id, "title": r.title, "created_at": str(r.created_at)}
        for r in rows
    ]


def get_session(user_id: int, thread_id: str) -> bool:
    """校验会话归属：该 thread_id 是否存在且属于当前 user_id。"""
    with rw_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM chat_session WHERE thread_id = :t AND user_id = :u "
                "AND is_enabled = TRUE AND is_deleted = FALSE"
            ),
            {"t": thread_id, "u": user_id},
        ).fetchone()
        conn.rollback()
    return row is not None


def delete_session(user_id: int, thread_id: str) -> bool:
    """删除会话：软删 chat_session + 清空该 thread 的 LangGraph checkpoint 记录。返回是否删除成功。"""
    with rw_engine().begin() as conn:
        result = conn.execute(
            text(
                "UPDATE chat_session SET is_deleted = TRUE "
                "WHERE thread_id = :t AND user_id = :u AND is_deleted = FALSE"
            ),
            {"t": thread_id, "u": user_id},
        )
        if result.rowcount == 0:
            return False
        # 清空 checkpoint（先 writes/blobs，再 checkpoints；表名来自固定白名单）
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            conn.execute(text(f"DELETE FROM {table} WHERE thread_id = :t"), {"t": thread_id})
    return True
