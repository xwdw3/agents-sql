"""数据库连接：app_ro（业务查询只读）+ admin（建表/灌数据）。"""
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..config import settings


@lru_cache(maxsize=1)
def ro_engine() -> Engine:
    """业务查询只读连接：statement_timeout + 事务只读。"""
    opts = f"-c statement_timeout={settings.statement_timeout_ms} -c default_transaction_read_only=on"
    return create_engine(
        settings.ro_dsn,
        connect_args={"options": opts},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


@lru_cache(maxsize=1)
def rw_engine() -> Engine:
    """app_rw 连接：应用状态写（chat_session 会话）+ 会话列表读取。"""
    return create_engine(settings.rw_dsn, pool_pre_ping=True)


@lru_cache(maxsize=1)
def admin_engine() -> Engine:
    """超级用户连接：仅用于建表/灌数据/建角色，运行期不用于业务查询。"""
    return create_engine(settings.admin_dsn, pool_pre_ping=True)
