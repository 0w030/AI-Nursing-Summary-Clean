"""
Oracle 資料庫反射實現 (Oracle Database Introspection)
從 ALL_TAB_COLUMNS 自動探測資料表、欄位、型別和註解
"""

from typing import List, Dict, Optional, Any
import oracledb
import logging
from .introspection import DatabaseIntrospector, TableMetadata, ColumnMetadata, DatabaseType

logger = logging.getLogger(__name__)


class OracleIntrospector(DatabaseIntrospector):
    """Oracle 資料庫反射器"""
    
    def __init__(self, connection, schema: str = None):
        """
        初始化 Oracle 反射器
        Args:
            connection: oracledb 連線物件
            schema: 預設 schema（若為空則為當前用戶）
        """
        super().__init__(connection)
        self.db_type = DatabaseType.ORACLE
        self.schema = schema or self._get_current_user()
    
    def _get_current_user(self) -> str:
        """取得當前連線用戶"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT USER FROM dual")
            user = cursor.fetchone()[0]
            cursor.close()
            return user
        except Exception as e:
            logger.error(f"取得當前用戶失敗: {e}")
            return "PUBLIC"
    
    def get_tables(self, schema: str = None) -> List[str]:
        """
        取得 schema 中所有資料表名稱
        
        Args:
            schema: schema 名稱，若為空則使用預設 schema
            
        Returns:
            資料表名稱列表
        """
        schema = schema or self.schema
        tables = []
        
        try:
            cursor = self.connection.cursor()
            
            # 查詢 ALL_TAB_COLUMNS 以取得表格列表
            # 排除系統表 (TS$, AUDTAB$ 等)
            query = """
                SELECT DISTINCT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = :owner
                AND TABLE_NAME NOT LIKE 'BIN$%'
                AND TABLESPACE_NAME IS NOT NULL
                ORDER BY TABLE_NAME
            """
            
            cursor.execute(query, {"owner": schema})
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            logger.info(f"找到 {len(tables)} 個表格在 {schema} 中")
            return tables
            
        except Exception as e:
            logger.error(f"查詢表格列表失敗: {e}")
            return []
    
    def get_table_columns(self, table_name: str, schema: str = None) -> List[ColumnMetadata]:
        """
        取得表格的所有欄位中繼資料
        
        Args:
            table_name: 資料表名稱
            schema: schema 名稱
            
        Returns:
            ColumnMetadata 列表
        """
        schema = schema or self.schema
        columns = []
        
        try:
            cursor = self.connection.cursor()
            
            # 主查詢：取得欄位基本信息
            query = """
                SELECT 
                    tc.COLUMN_NAME,
                    tc.DATA_TYPE,
                    tc.DATA_LENGTH,
                    tc.DATA_PRECISION,
                    tc.DATA_SCALE,
                    tc.NULLABLE,
                    tc.COLUMN_ID,
                    cc.COMMENTS,
                    CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS IS_PK
                FROM 
                    ALL_TAB_COLUMNS tc
                    LEFT JOIN ALL_COL_COMMENTS cc 
                        ON tc.OWNER = cc.OWNER 
                        AND tc.TABLE_NAME = cc.TABLE_NAME 
                        AND tc.COLUMN_NAME = cc.COLUMN_NAME
                    LEFT JOIN (
                        SELECT DISTINCT COLUMN_NAME 
                        FROM ALL_CONS_COLUMNS 
                        WHERE OWNER = :owner 
                        AND TABLE_NAME = :table_name
                        AND CONSTRAINT_NAME IN (
                            SELECT CONSTRAINT_NAME 
                            FROM ALL_CONSTRAINTS 
                            WHERE CONSTRAINT_TYPE = 'P'
                        )
                    ) pk ON tc.COLUMN_NAME = pk.COLUMN_NAME
                WHERE 
                    tc.OWNER = :owner 
                    AND tc.TABLE_NAME = :table_name
                ORDER BY 
                    tc.COLUMN_ID
            """
            
            cursor.execute(query, {
                "owner": schema,
                "table_name": table_name
            })
            
            rows = cursor.fetchall()
            
            for row in rows:
                col_name, data_type, data_length, precision, scale, nullable, col_id, comment, is_pk = row
                
                column = ColumnMetadata(
                    column_name=col_name,
                    data_type=data_type,
                    nullable=(nullable == "Y"),
                    comment=comment,
                    max_length=data_length,
                    numeric_precision=precision,
                    numeric_scale=scale,
                    is_primary_key=(is_pk == 1),
                    is_unique=False,  # TODO: 從約束中確定
                    is_indexed=False  # TODO: 從索引中確定
                )
                columns.append(column)
            
            cursor.close()
            logger.info(f"取得 {len(columns)} 個欄位從 {schema}.{table_name}")
            
            return columns
            
        except Exception as e:
            logger.error(f"查詢表格欄位失敗 {schema}.{table_name}: {e}")
            return []
    
    def get_table_metadata(self, table_name: str, schema: str = None) -> TableMetadata:
        """
        取得資料表完整中繼資料
        
        Args:
            table_name: 資料表名稱
            schema: schema 名稱
            
        Returns:
            TableMetadata 物件
        """
        schema = schema or self.schema
        
        try:
            # 取得欄位信息
            columns = self.get_table_columns(table_name, schema)
            
            # 取得表格註解
            cursor = self.connection.cursor()
            query = """
                SELECT COMMENTS 
                FROM ALL_TAB_COMMENTS 
                WHERE OWNER = :owner 
                AND TABLE_NAME = :table_name
            """
            cursor.execute(query, {
                "owner": schema,
                "table_name": table_name
            })
            result = cursor.fetchone()
            table_comment = result[0] if result else None
            
            # 取得表格行數（可選，對大表可能很慢）
            row_count = None
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
                row_count = cursor.fetchone()[0]
            except:
                pass
            
            cursor.close()
            
            metadata = TableMetadata(
                table_name=table_name,
                table_schema=schema,
                table_comment=table_comment,
                row_count=row_count,
                columns=columns
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"取得表格中繼資料失敗 {schema}.{table_name}: {e}")
            return TableMetadata(
                table_name=table_name,
                table_schema=schema,
                columns=[]
            )
    
    def get_all_tables_metadata(self, schema: str = None, max_tables: int = None) -> List[TableMetadata]:
        """
        取得 schema 中所有資料表的完整中繼資料
        
        Args:
            schema: schema 名稱
            max_tables: 最多取得的表格數量（用於測試）
            
        Returns:
            TableMetadata 列表
        """
        schema = schema or self.schema
        
        try:
            table_names = self.get_tables(schema)
            
            if max_tables:
                table_names = table_names[:max_tables]
            
            all_metadata = []
            for i, table_name in enumerate(table_names):
                logger.info(f"正在探測表格 {i+1}/{len(table_names)}: {table_name}")
                metadata = self.get_table_metadata(table_name, schema)
                all_metadata.append(metadata)
            
            return all_metadata
            
        except Exception as e:
            logger.error(f"取得所有表格中繼資料失敗: {e}")
            return []
    
    def search_tables_by_keyword(self, keyword: str, schema: str = None) -> List[str]:
        """
        根據關鍵字搜尋表格
        
        Args:
            keyword: 搜尋關鍵字
            schema: schema 名稱
            
        Returns:
            符合的表格名稱列表
        """
        schema = schema or self.schema
        tables = self.get_tables(schema)
        
        keyword_upper = keyword.upper()
        return [t for t in tables if keyword_upper in t]
    
    def search_columns_by_name(self, column_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """
        根據欄位名搜尋欄位（跨越所有表格）
        
        Args:
            column_name: 欄位名稱
            schema: schema 名稱
            
        Returns:
            包含 {table_name, column_name, data_type, comment} 的字典列表
        """
        schema = schema or self.schema
        results = []
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT 
                    tc.TABLE_NAME,
                    tc.COLUMN_NAME,
                    tc.DATA_TYPE,
                    cc.COMMENTS
                FROM 
                    ALL_TAB_COLUMNS tc
                    LEFT JOIN ALL_COL_COMMENTS cc 
                        ON tc.OWNER = cc.OWNER 
                        AND tc.TABLE_NAME = cc.TABLE_NAME 
                        AND tc.COLUMN_NAME = cc.COLUMN_NAME
                WHERE 
                    tc.OWNER = :owner 
                    AND UPPER(tc.COLUMN_NAME) LIKE :column_name
                ORDER BY 
                    tc.TABLE_NAME, tc.COLUMN_ID
            """
            
            cursor.execute(query, {
                "owner": schema,
                "column_name": f"%{column_name.upper()}%"
            })
            
            for row in cursor.fetchall():
                results.append({
                    "table_name": row[0],
                    "column_name": row[1],
                    "data_type": row[2],
                    "comment": row[3]
                })
            
            cursor.close()
            
            return results
            
        except Exception as e:
            logger.error(f"搜尋欄位失敗: {e}")
            return []
