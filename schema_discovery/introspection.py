"""
資料庫反射模組 (Database Introspection Module)
自動探測資料庫 Schema，支援 Oracle、PostgreSQL、SQLite
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """資料庫型別列舉"""
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MSSQL = "mssql"


@dataclass
class ColumnMetadata:
    """欄位中繼資料"""
    column_name: str
    data_type: str  # 原始資料庫型別
    nullable: bool
    comment: Optional[str] = None
    max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_indexed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)


@dataclass
class TableMetadata:
    """資料表中繼資料"""
    table_name: str
    table_schema: str
    table_comment: Optional[str] = None
    row_count: Optional[int] = None
    columns: List[ColumnMetadata] = None

    def __post_init__(self):
        if self.columns is None:
            self.columns = []

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "table_name": self.table_name,
            "table_schema": self.table_schema,
            "table_comment": self.table_comment,
            "row_count": self.row_count,
            "columns": [col.to_dict() for col in self.columns]
        }


class DatabaseIntrospector(ABC):
    """資料庫反射基類"""

    def __init__(self, connection):
        """
        初始化反射器
        Args:
            connection: 資料庫連線物件
        """
        self.connection = connection
        self.db_type = None

    @abstractmethod
    def get_tables(self, schema: str = None) -> List[str]:
        """取得所有資料表名稱"""
        pass

    @abstractmethod
    def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """取得資料表完整中繼資料"""
        pass

    @abstractmethod
    def get_all_tables_metadata(self, schema: str = None) -> List[TableMetadata]:
        """取得所有資料表中繼資料"""
        pass

    def close(self):
        """關閉連線"""
        try:
            self.connection.close()
        except Exception as e:
            logger.error(f"關閉連線時發生錯誤: {e}")


class OracleIntrospector(DatabaseIntrospector):
    """Oracle 資料庫反射器"""

    def __init__(self, connection):
        super().__init__(connection)
        self.db_type = DatabaseType.ORACLE

    def get_tables(self, schema: str = None) -> List[str]:
        """
        從 Oracle 取得所有資料表
        查詢 ALL_TABLES 或 USER_TABLES
        """
        try:
            cursor = self.connection.cursor()
            if schema:
                query = f"SELECT table_name FROM all_tables WHERE owner = '{schema.upper()}' ORDER BY table_name"
            else:
                query = "SELECT table_name FROM user_tables ORDER BY table_name"

            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            logger.error(f"取得表格列表失敗: {e}")
            return []

    def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """取得 Oracle 資料表的完整中繼資料"""
        try:
            cursor = self.connection.cursor()
            schema = schema or self._get_current_user()
            
            # 取得表格註解
            table_comment = self._get_table_comment(cursor, table_name, schema)
            
            # 取得行數
            row_count_query = f"SELECT count(*) FROM {schema}.{table_name}"
            cursor.execute(row_count_query)
            row_count = cursor.fetchone()[0]
            
            # 取得欄位資訊
            columns = self._get_columns_from_oracle(cursor, table_name, schema)
            
            cursor.close()
            
            return TableMetadata(
                table_name=table_name,
                table_schema=schema,
                table_comment=table_comment,
                row_count=row_count,
                columns=columns
            )
        except Exception as e:
            logger.error(f"取得表格中繼資料失敗 [{table_name}]: {e}")
            return TableMetadata(table_name=table_name, table_schema=schema)

    def _get_current_user(self) -> str:
        """取得當前 Oracle 使用者"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT user FROM dual")
            user = cursor.fetchone()[0]
            cursor.close()
            return user
        except Exception:
            return "USER"

    def _get_table_comment(self, cursor, table_name: str, schema: str) -> Optional[str]:
        """取得表格註解"""
        try:
            query = f"SELECT comments FROM all_tab_comments WHERE table_name = '{table_name.upper()}' AND owner = '{schema.upper()}'"
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception:
            return None

    def _get_columns_from_oracle(self, cursor, table_name: str, schema: str) -> List[ColumnMetadata]:
        """從 ALL_TAB_COLUMNS 取得欄位資訊"""
        columns = []
        try:
            # 主查詢：從 ALL_TAB_COLUMNS 取得欄位定義
            query = f"""
            SELECT 
                atc.column_name,
                atc.data_type,
                CASE WHEN atc.nullable = 'N' THEN 0 ELSE 1 END as nullable,
                acc.comments,
                atc.data_length,
                atc.data_precision,
                atc.data_scale
            FROM 
                all_tab_columns atc
            LEFT JOIN 
                all_col_comments acc 
                ON atc.table_name = acc.table_name 
                AND atc.column_name = acc.column_name
                AND atc.owner = acc.owner
            WHERE 
                atc.table_name = '{table_name.upper()}'
                AND atc.owner = '{schema.upper()}'
            ORDER BY 
                atc.column_id
            """
            cursor.execute(query)
            
            # 取得主鍵和唯一約束資訊
            pk_columns = self._get_primary_keys(cursor, table_name, schema)
            unique_columns = self._get_unique_columns(cursor, table_name, schema)
            
            for row in cursor.fetchall():
                col_name = row[0]
                columns.append(ColumnMetadata(
                    column_name=col_name,
                    data_type=row[1],
                    nullable=bool(row[2]),
                    comment=row[3],
                    max_length=row[4],
                    numeric_precision=row[5],
                    numeric_scale=row[6],
                    is_primary_key=col_name in pk_columns,
                    is_unique=col_name in unique_columns
                ))
        except Exception as e:
            logger.error(f"取得欄位資訊失敗: {e}")
        
        return columns

    def _get_primary_keys(self, cursor, table_name: str, schema: str) -> set:
        """取得主鍵欄位"""
        try:
            query = f"""
            SELECT column_name 
            FROM all_cons_columns 
            WHERE table_name = '{table_name.upper()}'
            AND owner = '{schema.upper()}'
            AND constraint_name IN (
                SELECT constraint_name 
                FROM all_constraints 
                WHERE table_name = '{table_name.upper()}'
                AND owner = '{schema.upper()}'
                AND constraint_type = 'P'
            )
            """
            cursor.execute(query)
            return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def _get_unique_columns(self, cursor, table_name: str, schema: str) -> set:
        """取得唯一約束欄位"""
        try:
            query = f"""
            SELECT column_name 
            FROM all_cons_columns 
            WHERE table_name = '{table_name.upper()}'
            AND owner = '{schema.upper()}'
            AND constraint_name IN (
                SELECT constraint_name 
                FROM all_constraints 
                WHERE table_name = '{table_name.upper()}'
                AND owner = '{schema.upper()}'
                AND constraint_type = 'U'
            )
            """
            cursor.execute(query)
            return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def get_all_tables_metadata(self, schema: str = None) -> List[TableMetadata]:
        """取得所有資料表的中繼資料"""
        tables = self.get_tables(schema)
        metadata_list = []
        
        for table_name in tables:
            try:
                metadata = self.get_table_metadata(table_name, schema)
                metadata_list.append(metadata)
                logger.info(f"✓ 已探測表格: {table_name} ({len(metadata.columns)} 欄位)")
            except Exception as e:
                logger.error(f"✗ 探測表格失敗 [{table_name}]: {e}")
        
        return metadata_list


class PostgreSQLIntrospector(DatabaseIntrospector):
    """PostgreSQL 資料庫反射器"""

    def __init__(self, connection):
        super().__init__(connection)
        self.db_type = DatabaseType.POSTGRESQL

    def get_tables(self, schema: str = None) -> List[str]:
        """從 PostgreSQL INFORMATION_SCHEMA 取得表格"""
        try:
            cursor = self.connection.cursor()
            schema = schema or "public"
            query = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            logger.error(f"取得表格列表失敗: {e}")
            return []

    def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """取得 PostgreSQL 表格的完整中繼資料"""
        try:
            cursor = self.connection.cursor()
            schema = schema or "public"
            
            # 取得表格註解
            table_comment = self._get_table_comment(cursor, table_name, schema)
            
            # 取得行數
            row_count_query = f"SELECT count(*) FROM {schema}.{table_name}"
            cursor.execute(row_count_query)
            row_count = cursor.fetchone()[0]
            
            # 取得欄位資訊
            columns = self._get_columns_from_postgresql(cursor, table_name, schema)
            
            cursor.close()
            
            return TableMetadata(
                table_name=table_name,
                table_schema=schema,
                table_comment=table_comment,
                row_count=row_count,
                columns=columns
            )
        except Exception as e:
            logger.error(f"取得表格中繼資料失敗 [{table_name}]: {e}")
            return TableMetadata(table_name=table_name, table_schema=schema)

    def _get_table_comment(self, cursor, table_name: str, schema: str) -> Optional[str]:
        """取得 PostgreSQL 表格註解"""
        try:
            query = f"""
            SELECT obj_description(('{schema}.{table_name}')::regclass, 'pg_class')
            """
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception:
            return None

    def _get_columns_from_postgresql(self, cursor, table_name: str, schema: str) -> List[ColumnMetadata]:
        """從 INFORMATION_SCHEMA 取得欄位資訊"""
        columns = []
        try:
            query = f"""
            SELECT 
                c.column_name,
                c.udt_name,
                c.is_nullable = 'NO' as not_null,
                pg_catalog.col_description(t.oid, c.ordinal_position),
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.column_default
            FROM 
                information_schema.columns c
            JOIN 
                pg_catalog.pg_class t ON c.table_name = t.relname
            WHERE 
                c.table_name = '{table_name}'
                AND c.table_schema = '{schema}'
            ORDER BY 
                c.ordinal_position
            """
            cursor.execute(query)
            
            # 取得主鍵資訊
            pk_columns = self._get_primary_keys(cursor, table_name, schema)
            
            for row in cursor.fetchall():
                col_name = row[0]
                columns.append(ColumnMetadata(
                    column_name=col_name,
                    data_type=row[1],
                    nullable=not row[2],
                    comment=row[3],
                    max_length=row[4],
                    numeric_precision=row[5],
                    numeric_scale=row[6],
                    default_value=row[7],
                    is_primary_key=col_name in pk_columns
                ))
        except Exception as e:
            logger.error(f"取得欄位資訊失敗: {e}")
        
        return columns

    def _get_primary_keys(self, cursor, table_name: str, schema: str) -> set:
        """取得主鍵欄位"""
        try:
            query = f"""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
            AND a.attnum = ANY(i.indkey)
            JOIN pg_class t ON i.indrelid = t.oid
            WHERE t.relname = '{table_name}'
            AND i.indisprimary
            """
            cursor.execute(query)
            return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def get_all_tables_metadata(self, schema: str = None) -> List[TableMetadata]:
        """取得所有資料表的中繼資料"""
        tables = self.get_tables(schema)
        metadata_list = []
        
        for table_name in tables:
            try:
                metadata = self.get_table_metadata(table_name, schema)
                metadata_list.append(metadata)
                logger.info(f"✓ 已探測表格: {table_name} ({len(metadata.columns)} 欄位)")
            except Exception as e:
                logger.error(f"✗ 探測表格失敗 [{table_name}]: {e}")
        
        return metadata_list


class SQLiteIntrospector(DatabaseIntrospector):
    """SQLite 資料庫反射器"""

    def __init__(self, connection):
        super().__init__(connection)
        self.db_type = DatabaseType.SQLITE

    def get_tables(self, schema: str = None) -> List[str]:
        """從 SQLite 取得所有表格"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return tables
        except Exception as e:
            logger.error(f"取得表格列表失敗: {e}")
            return []

    def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """取得 SQLite 表格的完整中繼資料"""
        try:
            cursor = self.connection.cursor()
            
            # 取得行數
            row_count_query = f"SELECT count(*) FROM {table_name}"
            cursor.execute(row_count_query)
            row_count = cursor.fetchone()[0]
            
            # 取得欄位資訊
            columns = self._get_columns_from_sqlite(cursor, table_name)
            
            cursor.close()
            
            return TableMetadata(
                table_name=table_name,
                table_schema="main",
                row_count=row_count,
                columns=columns
            )
        except Exception as e:
            logger.error(f"取得表格中繼資料失敗 [{table_name}]: {e}")
            return TableMetadata(table_name=table_name, table_schema="main")

    def _get_columns_from_sqlite(self, cursor, table_name: str) -> List[ColumnMetadata]:
        """從 PRAGMA 取得 SQLite 欄位資訊"""
        columns = []
        try:
            # 先取得主鍵資訊
            cursor.execute(f"PRAGMA primary_key({table_name})")
            pk_info = cursor.fetchall()
            pk_columns = {row[1] for row in pk_info if row[1]}
            
            # 取得欄位資訊
            query = f"PRAGMA table_info({table_name})"
            cursor.execute(query)
            
            for row in cursor.fetchall():
                # PRAGMA table_info 返回: cid, name, type, notnull, dflt_value, pk
                col_name = row[1]
                columns.append(ColumnMetadata(
                    column_name=col_name,
                    data_type=row[2],
                    nullable=not bool(row[3]),
                    default_value=row[4],
                    is_primary_key=col_name in pk_columns
                ))
        except Exception as e:
            logger.error(f"取得欄位資訊失敗: {e}")
        
        return columns

    def get_all_tables_metadata(self, schema: str = None) -> List[TableMetadata]:
        """取得所有資料表的中繼資料"""
        tables = self.get_tables(schema)
        metadata_list = []
        
        for table_name in tables:
            try:
                metadata = self.get_table_metadata(table_name, schema)
                metadata_list.append(metadata)
                logger.info(f"✓ 已探測表格: {table_name} ({len(metadata.columns)} 欄位)")
            except Exception as e:
                logger.error(f"✗ 探測表格失敗 [{table_name}]: {e}")
        
        return metadata_list


def create_introspector(connection, db_type: DatabaseType) -> DatabaseIntrospector:
    """
    工廠函式：根據資料庫型別建立合適的反射器
    
    Args:
        connection: 資料庫連線
        db_type: 資料庫型別
    
    Returns:
        DatabaseIntrospector 實例
    """
    if db_type == DatabaseType.ORACLE:
        return OracleIntrospector(connection)
    elif db_type == DatabaseType.POSTGRESQL:
        return PostgreSQLIntrospector(connection)
    elif db_type == DatabaseType.SQLITE:
        return SQLiteIntrospector(connection)
    else:
        raise ValueError(f"不支援的資料庫型別: {db_type}")
