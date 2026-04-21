# core/di_container.py
"""
依賴注入容器 (Dependency Injection Container)
根據配置動態構建並提供正確的 Repository 實現
"""

from typing import Type, TypeVar, Dict, Any, Optional
import asyncpg

from core.config import DatabaseConfig, DatabaseType, get_db_config
from repositories.base_repository import (
    IPatientRepository, INursingRecordRepository,
    IVitalSignsRepository, ILabResultRepository,
    IUserRepository, ITemplateRepository
)
from repositories.postgresql_repository import (
    PostgreSQLPatientRepository,
    PostgreSQLNursingRecordRepository,
)
from repositories.oracle_repository import OraclePatientRepository
from repositories.sqlite_repository import (
    SQLitePatientRepository,
    SQLiteNursingRecordRepository,
)

T = TypeVar('T')


class DIContainer:
    """
    依賴注入容器
    管理所有 Repository 的生命週期與依賴關係
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        初始化 DI 容器

        Args:
            config: 資料庫配置，如果為 None 則使用全域配置
        """
        self.config = config or get_db_config()
        self._postgres_pool: Optional[asyncpg.Pool] = None
        self._instances: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}

    async def initialize(self):
        """
        初始化容器資源（如資料庫連線池）
        應在應用啟動時呼叫
        """
        if self.config.db_type == DatabaseType.POSTGRESQL:
            await self._initialize_postgresql()
            print(f"✅ PostgreSQL 連線池已初始化 (pool_size={self.config.pool_size})")

    async def _initialize_postgresql(self):
        """初始化 PostgreSQL 連線池"""
        if self._postgres_pool is None:
            self._postgres_pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=self.config.pool_size // 2,
                max_size=self.config.pool_size,
                command_timeout=self.config.pool_timeout,
            )

    async def close(self):
        """
        關閉容器資源
        應在應用關閉時呼叫
        """
        if self._postgres_pool:
            await self._postgres_pool.close()
            print("✅ PostgreSQL 連線池已關閉")

    def get_patient_repository(self) -> IPatientRepository:
        """
        取得患者 Repository 實現
        根據配置的資料庫類型返回對應實現
        """
        cache_key = IPatientRepository

        # 檢查是否已有快取實例
        if cache_key in self._singletons:
            return self._singletons[cache_key]

        if self.config.db_type == DatabaseType.POSTGRESQL:
            if self._postgres_pool is None:
                raise RuntimeError(
                    "PostgreSQL 連線池未初始化。"
                    "請先呼叫 await container.initialize()"
                )
            repo = PostgreSQLPatientRepository(self._postgres_pool)
        elif self.config.db_type == DatabaseType.ORACLE:
            conn_string = self.config.get_connection_string()
            repo = OraclePatientRepository(conn_string)
        elif self.config.db_type == DatabaseType.SQLITE:
            repo = SQLitePatientRepository(self.config.database)
        else:
            raise ValueError(f"不支援的資料庫類型: {self.config.db_type}")

        self._singletons[cache_key] = repo
        return repo

    def get_nursing_record_repository(self) -> INursingRecordRepository:
        """
        取得護理紀錄 Repository 實現
        """
        cache_key = INursingRecordRepository

        if cache_key in self._singletons:
            return self._singletons[cache_key]

        if self.config.db_type == DatabaseType.POSTGRESQL:
            if self._postgres_pool is None:
                raise RuntimeError(
                    "PostgreSQL 連線池未初始化。"
                    "請先呼叫 await container.initialize()"
                )
            repo = PostgreSQLNursingRecordRepository(self._postgres_pool)
        elif self.config.db_type == DatabaseType.ORACLE:
            # TODO: 實作 OracleNursingRecordRepository
            raise NotImplementedError("Oracle 護理紀錄 Repository 尚未實現")
        elif self.config.db_type == DatabaseType.SQLITE:
            repo = SQLiteNursingRecordRepository(self.config.database)
        else:
            raise ValueError(f"不支援的資料庫類型: {self.config.db_type}")

        self._singletons[cache_key] = repo
        return repo

    def get_vital_signs_repository(self) -> IVitalSignsRepository:
        """取得生理監測 Repository 實現"""
        cache_key = IVitalSignsRepository

        if cache_key in self._singletons:
            return self._singletons[cache_key]

        if self.config.db_type == DatabaseType.POSTGRESQL:
            if self._postgres_pool is None:
                raise RuntimeError("PostgreSQL 連線池未初始化")
            # TODO: 實作 PostgreSQLVitalSignsRepository
            raise NotImplementedError("PostgreSQL 生理監測 Repository 尚未實現")
        elif self.config.db_type == DatabaseType.ORACLE:
            raise NotImplementedError("Oracle 生理監測 Repository 尚未實現")
        else:
            raise ValueError(f"不支援的資料庫類型: {self.config.db_type}")

    def get_lab_result_repository(self) -> ILabResultRepository:
        """取得檢驗結果 Repository 實現"""
        cache_key = ILabResultRepository

        if cache_key in self._singletons:
            return self._singletons[cache_key]

        raise NotImplementedError("檢驗結果 Repository 尚未實現")

    def get_user_repository(self) -> IUserRepository:
        """取得使用者 Repository 實現"""
        cache_key = IUserRepository

        if cache_key in self._singletons:
            return self._singletons[cache_key]

        raise NotImplementedError("使用者 Repository 尚未實現")

    def get_template_repository(self) -> ITemplateRepository:
        """取得模板 Repository 實現"""
        cache_key = ITemplateRepository

        if cache_key in self._singletons:
            return self._singletons[cache_key]

        raise NotImplementedError("模板 Repository 尚未實現")

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """
        註冊單例實例
        允許手動註冊自定義實現
        """
        self._singletons[interface] = instance

    def clear_singletons(self) -> None:
        """清除所有快取的單例"""
        self._singletons.clear()


# 全域 DI 容器實例
_global_container: Optional[DIContainer] = None


def get_di_container(config: Optional[DatabaseConfig] = None) -> DIContainer:
    """
    取得全域 DI 容器
    使用單例模式確保整個應用只有一個容器實例
    """
    global _global_container
    if _global_container is None:
        _global_container = DIContainer(config)
    return _global_container


async def initialize_di_container() -> DIContainer:
    """
    初始化全域 DI 容器
    應在應用啟動時呼叫一次
    """
    container = get_di_container()
    await container.initialize()
    return container


async def close_di_container() -> None:
    """
    關閉全域 DI 容器
    應在應用關閉時呼叫
    """
    global _global_container
    if _global_container:
        await _global_container.close()
        _global_container = None
