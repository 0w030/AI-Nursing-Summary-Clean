# core/config.py
"""
資料庫配置層 - 統一管理環境變數與資料庫連線設定
支援多資料庫切換（Oracle、PostgreSQL、SQLite）
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# 加載 .env 文件
load_dotenv()

# Oracle Instant Client 初始化（自動檢測）
try:
    import oracledb
    ic_path = Path("C:/instantclient_19_30/instantclient_19_30")
    if ic_path.exists():
        oracledb.init_oracle_client(lib_dir=str(ic_path))
except Exception as e:
    pass  # Instant Client 可選，不影響其他資料庫類型


class DatabaseType(Enum):
    """支援的資料庫類型"""
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


@dataclass
class DatabaseConfig:
    """資料庫配置容器"""
    db_type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    driver: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo_sql: bool = False

    def get_connection_string(self) -> str:
        """
        生成對應資料庫類型的連線字串
        確保所有 DB 特定的邏輯都在此層被處理
        """
        if self.db_type == DatabaseType.ORACLE:
            # oracledb 連接字串格式: username/password@host:port/service_name
            # 或使用 DSN: user@dsn_alias
            return f"{self.username}/{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == DatabaseType.POSTGRESQL:
            # PostgreSQL: postgresql://user:password@host:port/database
            return (
                f"postgresql://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        elif self.db_type == DatabaseType.SQLITE:
            # SQLite: sqlite:////path/to/database.db
            return f"sqlite:///{self.database}"
        else:
            raise ValueError(f"不支援的資料庫類型: {self.db_type}")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "db_type": self.db_type.value,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "pool_size": self.pool_size,
            "echo": self.echo_sql,
        }


class ConfigManager:
    """
    環境配置管理員
    從 .env 檔案讀取設定，支援多組預設
    """

    def __init__(self):
        """初始化配置管理員"""
        load_dotenv()
        self._config: Optional[DatabaseConfig] = None

    @staticmethod
    def _parse_db_type(db_type_str: str) -> DatabaseType:
        """解析資料庫類型字串"""
        db_type_str = db_type_str.lower().strip()
        try:
            return DatabaseType(db_type_str)
        except ValueError:
            raise ValueError(
                f"不支援的資料庫類型: {db_type_str}。"
                f"請使用: {', '.join([db.value for db in DatabaseType])}"
            )

    def load_config(self) -> DatabaseConfig:
        """
        從環境變數載入配置
        優先順序：環境變數 > .env 檔案 > 預設值
        """
        db_type_str = os.getenv("DB_TYPE", "postgresql")
        db_type = self._parse_db_type(db_type_str)

        if db_type == DatabaseType.ORACLE:
            config = DatabaseConfig(
                db_type=db_type,
                host=os.getenv("ORACLE_HOST", "localhost"),
                port=int(os.getenv("ORACLE_PORT", 1521)),
                database=os.getenv("ORACLE_SID", "ORCL"),
                username=os.getenv("ORACLE_USER", "system"),
                password=os.getenv("ORACLE_PASSWORD", "oracle"),
                driver=os.getenv("ORACLE_DRIVER", "cx_Oracle"),
                pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
                echo_sql=os.getenv("DB_ECHO_SQL", "false").lower() == "true",
            )

        elif db_type == DatabaseType.POSTGRESQL:
            config = DatabaseConfig(
                db_type=db_type,
                host=os.getenv("POSTGRESQL_HOST", "localhost"),
                port=int(os.getenv("POSTGRESQL_PORT", 5432)),
                database=os.getenv("POSTGRESQL_DB", "nursing_db"),
                username=os.getenv("POSTGRESQL_USER", "postgres"),
                password=os.getenv("POSTGRESQL_PASSWORD", "postgres"),
                pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
                echo_sql=os.getenv("DB_ECHO_SQL", "false").lower() == "true",
            )

        elif db_type == DatabaseType.SQLITE:
            config = DatabaseConfig(
                db_type=db_type,
                database=os.getenv("SQLITE_PATH", "local_data/app.db"),
                pool_size=1,
                max_overflow=0,
                echo_sql=os.getenv("DB_ECHO_SQL", "false").lower() == "true",
            )

        else:
            raise ValueError(f"不支援的資料庫類型: {db_type}")

        self._config = config
        return config

    def get_config(self) -> DatabaseConfig:
        """取得當前配置"""
        if self._config is None:
            self.load_config()
        return self._config

    def reload_config(self) -> DatabaseConfig:
        """重新載入配置"""
        self._config = None
        return self.load_config()


# 全域配置管理員
_config_manager = ConfigManager()


def get_db_config() -> DatabaseConfig:
    """取得全域資料庫配置"""
    return _config_manager.get_config()


def reload_db_config() -> DatabaseConfig:
    """重新載入全域資料庫配置"""
    return _config_manager.reload_config()
