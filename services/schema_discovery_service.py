"""
Schema 發現服務 - 動態從資料庫探測表格和欄位
支持 Oracle, PostgreSQL, SQLite, MSSQL
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import oracledb
import psycopg2
import sqlite3
import pyodbc

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """表格信息"""
    name: str
    row_count: int = 0
    comment: str = ""


@dataclass
class ColumnInfo:
    """欄位信息"""
    name: str
    data_type: str
    nullable: bool = True
    max_length: Optional[int] = None
    comment: str = ""
    sample_values: Optional[List[str]] = None
    numeric_min: Optional[float] = None
    numeric_max: Optional[float] = None


class SchemaDiscoveryService:
    """Schema 發現和同步服務"""
    
    def __init__(self, connection_params: Dict):
        """
        初始化服務
        
        Args:
            connection_params: {
                'db_type': 'oracle'|'postgresql'|'sqlite'|'mssql',
                'host': str,
                'port': int,
                'database': str,
                'username': str,
                'password': str
            }
        """
        self.connection_params = connection_params
        self.db_type = connection_params.get('db_type', '').lower()
        self.connection = None
    
    def connect(self) -> bool:
        """建立資料庫連接"""
        try:
            if self.db_type == 'oracle':
                self._connect_oracle()
            elif self.db_type == 'postgresql':
                self._connect_postgresql()
            elif self.db_type == 'sqlite':
                self._connect_sqlite()
            elif self.db_type == 'mssql':
                self._connect_mssql()
            else:
                logger.error(f"不支持的資料庫類型: {self.db_type}")
                return False
            
            logger.info(f"✅ 成功連接到 {self.db_type} 資料庫")
            return True
        except Exception as e:
            logger.error(f"❌ 連接失敗: {str(e)}")
            return False
    
    def _connect_oracle(self):
        """連接 Oracle 資料庫"""
        try:
            oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30\instantclient_19_30")
        except:
            pass
        
        # 支持 SID 或 Service Name
        database = self.connection_params['database']
        
        # 嘗試構建 DSN
        # 如果 database 看起來像 SID（短名稱），使用 sid 參數
        # 否則使用 service_name 參數
        try:
            # 先嘗試作為 Service Name
            dsn = oracledb.makedsn(
                self.connection_params['host'],
                self.connection_params['port'],
                service_name=database
            )
            logger.info(f"使用 Service Name: {database}")
        except Exception as e:
            # 失敗則嘗試 SID
            logger.warning(f"Service Name 連接失敗，改用 SID: {str(e)}")
            dsn = oracledb.makedsn(
                self.connection_params['host'],
                self.connection_params['port'],
                sid=database
            )
            logger.info(f"使用 SID: {database}")
        
        self.connection = oracledb.connect(
            user=self.connection_params['username'],
            password=self.connection_params['password'],
            dsn=dsn
        )
    
    def _connect_postgresql(self):
        """連接 PostgreSQL 資料庫"""
        try:
            # Railway PostgreSQL 需要 SSL 連接
            self.connection = psycopg2.connect(
                host=self.connection_params['host'],
                port=self.connection_params['port'],
                database=self.connection_params['database'],
                user=self.connection_params['username'],
                password=self.connection_params['password'],
                sslmode='require'  # ✅ 對於 Railway 等雲端數據庫需要 SSL
            )
            logger.info("PostgreSQL SSL 連接成功")
        except Exception as e:
            logger.error(f"PostgreSQL SSL 連接失敗，嘗試非 SSL 連接: {str(e)}")
            # 如果 SSL 失敗，嘗試不使用 SSL
            try:
                self.connection = psycopg2.connect(
                    host=self.connection_params['host'],
                    port=self.connection_params['port'],
                    database=self.connection_params['database'],
                    user=self.connection_params['username'],
                    password=self.connection_params['password']
                )
                logger.info("✅ PostgreSQL 非 SSL 連接成功")
            except Exception as e2:
                logger.error(f"❌ PostgreSQL 連接失敗: {str(e2)}")
                raise
    
    def _connect_sqlite(self):
        """連接 SQLite 資料庫"""
        self.connection = sqlite3.connect(self.connection_params['database'])
    
    def _connect_mssql(self):
        """連接 MSSQL 資料庫"""
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={self.connection_params['host']},{self.connection_params['port']};"
            f"Database={self.connection_params['database']};"
            f"UID={self.connection_params['username']};"
            f"PWD={self.connection_params['password']}"
        )
        self.connection = pyodbc.connect(connection_string)
    
    def disconnect(self):
        """關閉資料庫連接"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("✅ 資料庫連接已關閉")
            except Exception as e:
                logger.error(f"關閉連接時出錯: {str(e)}")
    
    def discover_tables(self) -> List[TableInfo]:
        """發現所有表格"""
        try:
            if self.db_type == 'oracle':
                return self._discover_tables_oracle()
            elif self.db_type == 'postgresql':
                return self._discover_tables_postgresql()
            elif self.db_type == 'sqlite':
                return self._discover_tables_sqlite()
            elif self.db_type == 'mssql':
                return self._discover_tables_mssql()
        except Exception as e:
            logger.error(f"❌ 發現表格失敗: {str(e)}")
            return []
    
    def _discover_tables_oracle(self) -> List[TableInfo]:
        """Oracle 表格發現"""
        cursor = self.connection.cursor()
        
        # 查詢用戶表格（簡化查詢，先不使用註解以提高可靠性）
        cursor.execute("""
            SELECT table_name
            FROM user_tables
            ORDER BY table_name
        """)
        
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            tables.append(TableInfo(name=table_name, row_count=0, comment=""))
        
        cursor.close()
        logger.info(f"✅ 發現 {len(tables)} 個 Oracle 表格")
        return tables
    
    def _discover_tables_postgresql(self) -> List[TableInfo]:
        """PostgreSQL 表格發現"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            tables.append(TableInfo(name=table_name, row_count=0, comment=""))
        
        cursor.close()
        logger.info(f"✅ 發現 {len(tables)} 個表格")
        return tables
    
    def _discover_tables_sqlite(self) -> List[TableInfo]:
        """SQLite 表格發現"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            tables.append(TableInfo(name=table_name, row_count=0, comment=""))
        
        cursor.close()
        logger.info(f"✅ 發現 {len(tables)} 個表格")
        return tables
    
    def _discover_tables_mssql(self) -> List[TableInfo]:
        """MSSQL 表格發現"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            tables.append(TableInfo(name=table_name, row_count=0, comment=""))
        
        cursor.close()
        logger.info(f"✅ 發現 {len(tables)} 個表格")
        return tables
    
    def discover_columns(self, table_name: str) -> List[ColumnInfo]:
        """發現表格的所有欄位"""
        try:
            if self.db_type == 'oracle':
                return self._discover_columns_oracle(table_name)
            elif self.db_type == 'postgresql':
                return self._discover_columns_postgresql(table_name)
            elif self.db_type == 'sqlite':
                return self._discover_columns_sqlite(table_name)
            elif self.db_type == 'mssql':
                return self._discover_columns_mssql(table_name)
        except Exception as e:
            logger.error(f"❌ 發現欄位失敗 ({table_name}): {str(e)}")
            return []
    
    def _discover_columns_oracle(self, table_name: str) -> List[ColumnInfo]:
        """Oracle 欄位發現"""
        cursor = self.connection.cursor()
        
        # 簡化查詢，先只查欄位基本信息（不使用 LEFT JOIN 以提高穩定性）
        cursor.execute(f"""
            SELECT column_name, data_type, nullable, data_length
            FROM user_tab_columns
            WHERE table_name = '{table_name.upper()}'
            ORDER BY column_id
        """)
        
        columns = []
        for row in cursor.fetchall():
            col_name = row[0]
            data_type = row[1]
            nullable = row[2] == 'Y'
            max_length = row[3] if row[3] else None
            
            # 嘗試採集樣本值和數值範圍
            sample_values = self._get_sample_values_oracle(cursor, table_name, col_name)
            numeric_min, numeric_max = self._get_numeric_range_oracle(cursor, table_name, col_name, data_type)
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                nullable=nullable,
                max_length=max_length,
                comment="",
                sample_values=sample_values,
                numeric_min=numeric_min,
                numeric_max=numeric_max
            ))
        
        cursor.close()
        logger.info(f"[OK] 發現表格 {table_name} 的 {len(columns)} 個欄位")
        return columns
    
    def _get_sample_values_oracle(self, cursor, table_name: str, column_name: str) -> Optional[List[str]]:
        """從 Oracle 表中採集欄位樣本值"""
        try:
            query = f"SELECT DISTINCT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL AND ROWNUM <= 3"
            cursor.execute(query)
            values = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]
            return values if values else None
        except Exception:
            return None
    
    def _get_numeric_range_oracle(self, cursor, table_name: str, column_name: str, data_type: str) -> Tuple[Optional[float], Optional[float]]:
        """從 Oracle 表中採集數值欄位的範圍"""
        if 'NUMBER' not in data_type.upper() and 'INT' not in data_type.upper():
            return None, None
        try:
            query = f"SELECT MIN({column_name}), MAX({column_name}) FROM {table_name}"
            cursor.execute(query)
            row = cursor.fetchone()
            if row:
                min_val = float(row[0]) if row[0] is not None else None
                max_val = float(row[1]) if row[1] is not None else None
                return min_val, max_val
        except Exception:
            pass
        return None, None
    
    def _discover_columns_postgresql(self, table_name: str) -> List[ColumnInfo]:
        """PostgreSQL 欄位發現"""
        cursor = self.connection.cursor()
        
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        
        columns = []
        for row in cursor.fetchall():
            col_name = row[0]
            data_type = row[1]
            nullable = row[2] == 'YES'
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                nullable=nullable
            ))
        
        cursor.close()
        logger.info(f"✅ 發現表格 {table_name} 的 {len(columns)} 個欄位")
        return columns
    
    def _discover_columns_sqlite(self, table_name: str) -> List[ColumnInfo]:
        """SQLite 欄位發現"""
        cursor = self.connection.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        
        columns = []
        for row in cursor.fetchall():
            col_name = row[1]
            data_type = row[2]
            nullable = row[3] == 0
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                nullable=nullable
            ))
        
        cursor.close()
        logger.info(f"✅ 發現表格 {table_name} 的 {len(columns)} 個欄位")
        return columns
    
    def _discover_columns_mssql(self, table_name: str) -> List[ColumnInfo]:
        """MSSQL 欄位發現"""
        cursor = self.connection.cursor()
        
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = []
        for row in cursor.fetchall():
            col_name = row[0]
            data_type = row[1]
            nullable = row[2] == 'YES'
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type,
                nullable=nullable
            ))
        
        cursor.close()
        logger.info(f"✅ 發現表格 {table_name} 的 {len(columns)} 個欄位")
        return columns
    
    def discover_full_schema(self) -> Dict:
        """發現完整 Schema"""
        schema = {
            'discovered_at': datetime.now().isoformat(),
            'database': self.connection_params['database'],
            'db_type': self.db_type,
            'tables': {}
        }
        
        tables = self.discover_tables()
        for table in tables:
            columns = self.discover_columns(table.name)
            schema['tables'][table.name] = {
                'table_info': {
                    'name': table.name,
                    'row_count': table.row_count,
                    'comment': table.comment
                },
                'columns': [
                    {
                        'name': col.column_name,
                        'data_type': col.data_type,
                        'nullable': col.nullable,
                        'max_length': col.max_length,
                        'comment': col.comment,
                        'sample_values': col.sample_values if hasattr(col, 'sample_values') else None,
                        'numeric_min': col.numeric_min if hasattr(col, 'numeric_min') else None,
                        'numeric_max': col.numeric_max if hasattr(col, 'numeric_max') else None,
                    }
                    for col in columns
                ]
            }
        
        logger.info(f"[COMPLETE] 完整 Schema 發現完成: {len(tables)} 個表格")
        return schema
