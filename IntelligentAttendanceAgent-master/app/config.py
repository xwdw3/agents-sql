"""集中配置：pydantic-settings 读取 .env / 环境变量。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（基于文件绝对路径，避免 PyCharm 工作目录不一致导致找不到 .env）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # PostgreSQL（超级用户，建表/灌数据用）
    pg_host: str = "127.0.0.1"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_db: str = "punch_in"

    # 运行时角色
    app_ro_user: str = "app_ro"
    app_ro_password: str = "app_ro_pwd"
    app_rw_user: str = "app_rw"
    app_rw_password: str = "app_rw_pwd"

    # 查询与安全参数
    statement_timeout_ms: int = 5000
    max_rows: int = 200
    max_result_bytes: int = 50_000
    token_secret: str = "dev-secret-change-me"

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # ---- 派生 DSN ----
    @property
    def admin_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @property
    def ro_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.app_ro_user}:{self.app_ro_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @property
    def rw_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.app_rw_user}:{self.app_rw_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @property
    def rw_psycopg_dsn(self) -> str:
        """psycopg3 原生连接串（供 langgraph PostgresSaver 使用，不含 SQLAlchemy 方言后缀）。"""
        return (
            f"postgresql://{self.app_rw_user}:{self.app_rw_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


settings = Settings()
