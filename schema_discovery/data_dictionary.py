"""
資料字典中繼層 (Metadata Dictionary Layer)
統一轉換不同資料庫的型別為系統標準型別
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class CoreDataType(Enum):
    """系統標準核心資料型別"""
    STRING = "String"
    INTEGER = "Integer"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    DATE = "Date"
    DATETIME = "DateTime"
    TIME = "Time"
    BINARY = "Binary"
    JSON = "JSON"
    UUID = "UUID"
    DECIMAL = "Decimal"
    UNKNOWN = "Unknown"


class TypeMapper:
    """
    資料庫型別對應器
    將各資料庫的特定型別統一轉換為系統標準型別
    """
    
    # Oracle 型別對應
    ORACLE_TYPE_MAP = {
        "VARCHAR2": CoreDataType.STRING,
        "NVARCHAR2": CoreDataType.STRING,
        "CHAR": CoreDataType.STRING,
        "NCHAR": CoreDataType.STRING,
        "CLOB": CoreDataType.STRING,
        "NCLOB": CoreDataType.STRING,
        "NUMBER": CoreDataType.DECIMAL,
        "INTEGER": CoreDataType.INTEGER,
        "INT": CoreDataType.INTEGER,
        "FLOAT": CoreDataType.FLOAT,
        "BINARY_FLOAT": CoreDataType.FLOAT,
        "BINARY_DOUBLE": CoreDataType.FLOAT,
        "DATE": CoreDataType.DATETIME,
        "TIMESTAMP": CoreDataType.DATETIME,
        "TIMESTAMP WITH TIME ZONE": CoreDataType.DATETIME,
        "TIMESTAMP WITH LOCAL TIME ZONE": CoreDataType.DATETIME,
        "INTERVAL YEAR TO MONTH": CoreDataType.STRING,
        "INTERVAL DAY TO SECOND": CoreDataType.STRING,
        "RAW": CoreDataType.BINARY,
        "BLOB": CoreDataType.BINARY,
        "BFILE": CoreDataType.BINARY,
    }
    
    # PostgreSQL 型別對應
    POSTGRESQL_TYPE_MAP = {
        "character varying": CoreDataType.STRING,
        "varchar": CoreDataType.STRING,
        "character": CoreDataType.STRING,
        "char": CoreDataType.STRING,
        "text": CoreDataType.STRING,
        "name": CoreDataType.STRING,
        "smallint": CoreDataType.INTEGER,
        "integer": CoreDataType.INTEGER,
        "int": CoreDataType.INTEGER,
        "bigint": CoreDataType.INTEGER,
        "decimal": CoreDataType.DECIMAL,
        "numeric": CoreDataType.DECIMAL,
        "real": CoreDataType.FLOAT,
        "double precision": CoreDataType.FLOAT,
        "boolean": CoreDataType.BOOLEAN,
        "bool": CoreDataType.BOOLEAN,
        "date": CoreDataType.DATE,
        "time": CoreDataType.TIME,
        "timestamp": CoreDataType.DATETIME,
        "timestamp without time zone": CoreDataType.DATETIME,
        "timestamp with time zone": CoreDataType.DATETIME,
        "bytea": CoreDataType.BINARY,
        "uuid": CoreDataType.UUID,
        "json": CoreDataType.JSON,
        "jsonb": CoreDataType.JSON,
    }
    
    # SQLite 型別對應
    SQLITE_TYPE_MAP = {
        "TEXT": CoreDataType.STRING,
        "CHAR": CoreDataType.STRING,
        "VARCHAR": CoreDataType.STRING,
        "INTEGER": CoreDataType.INTEGER,
        "INT": CoreDataType.INTEGER,
        "REAL": CoreDataType.FLOAT,
        "NUMERIC": CoreDataType.DECIMAL,
        "BLOB": CoreDataType.BINARY,
        "DATE": CoreDataType.DATE,
        "DATETIME": CoreDataType.DATETIME,
        "TIMESTAMP": CoreDataType.DATETIME,
        "BOOLEAN": CoreDataType.BOOLEAN,
    }
    
    # SQL Server 型別對應
    MSSQL_TYPE_MAP = {
        "varchar": CoreDataType.STRING,
        "nvarchar": CoreDataType.STRING,
        "char": CoreDataType.STRING,
        "nchar": CoreDataType.STRING,
        "text": CoreDataType.STRING,
        "ntext": CoreDataType.STRING,
        "smallint": CoreDataType.INTEGER,
        "int": CoreDataType.INTEGER,
        "bigint": CoreDataType.INTEGER,
        "decimal": CoreDataType.DECIMAL,
        "numeric": CoreDataType.DECIMAL,
        "real": CoreDataType.FLOAT,
        "float": CoreDataType.FLOAT,
        "date": CoreDataType.DATE,
        "time": CoreDataType.TIME,
        "datetime": CoreDataType.DATETIME,
        "datetime2": CoreDataType.DATETIME,
        "smalldatetime": CoreDataType.DATETIME,
        "timestamp": CoreDataType.DATETIME,
        "bit": CoreDataType.BOOLEAN,
        "binary": CoreDataType.BINARY,
        "varbinary": CoreDataType.BINARY,
        "image": CoreDataType.BINARY,
        "uniqueidentifier": CoreDataType.UUID,
    }
    
    @classmethod
    def map_oracle_type(cls, oracle_type: str) -> CoreDataType:
        """將 Oracle 型別對應到系統標準型別"""
        oracle_type_upper = oracle_type.upper().strip()
        
        # 精確匹配
        if oracle_type_upper in cls.ORACLE_TYPE_MAP:
            return cls.ORACLE_TYPE_MAP[oracle_type_upper]
        
        # 前綴匹配（例如 NUMBER(10,2) 應該對應 NUMBER）
        for db_type, core_type in cls.ORACLE_TYPE_MAP.items():
            if oracle_type_upper.startswith(db_type):
                return core_type
        
        logger.warning(f"未知的 Oracle 型別: {oracle_type}")
        return CoreDataType.UNKNOWN
    
    @classmethod
    def map_postgresql_type(cls, pg_type: str) -> CoreDataType:
        """將 PostgreSQL 型別對應到系統標準型別"""
        pg_type_lower = pg_type.lower().strip()
        
        # 精確匹配
        if pg_type_lower in cls.POSTGRESQL_TYPE_MAP:
            return cls.POSTGRESQL_TYPE_MAP[pg_type_lower]
        
        # 前綴匹配
        for db_type, core_type in cls.POSTGRESQL_TYPE_MAP.items():
            if pg_type_lower.startswith(db_type):
                return core_type
        
        logger.warning(f"未知的 PostgreSQL 型別: {pg_type}")
        return CoreDataType.UNKNOWN
    
    @classmethod
    def map_sqlite_type(cls, sqlite_type: str) -> CoreDataType:
        """將 SQLite 型別對應到系統標準型別"""
        sqlite_type_upper = sqlite_type.upper().strip()
        
        # 精確匹配
        if sqlite_type_upper in cls.SQLITE_TYPE_MAP:
            return cls.SQLITE_TYPE_MAP[sqlite_type_upper]
        
        # 前綴匹配
        for db_type, core_type in cls.SQLITE_TYPE_MAP.items():
            if sqlite_type_upper.startswith(db_type):
                return core_type
        
        logger.warning(f"未知的 SQLite 型別: {sqlite_type}")
        return CoreDataType.UNKNOWN
    
    @classmethod
    def map_mssql_type(cls, mssql_type: str) -> CoreDataType:
        """將 SQL Server 型別對應到系統標準型別"""
        mssql_type_lower = mssql_type.lower().strip()
        
        # 精確匹配
        if mssql_type_lower in cls.MSSQL_TYPE_MAP:
            return cls.MSSQL_TYPE_MAP[mssql_type_lower]
        
        # 前綴匹配
        for db_type, core_type in cls.MSSQL_TYPE_MAP.items():
            if mssql_type_lower.startswith(db_type):
                return core_type
        
        logger.warning(f"未知的 SQL Server 型別: {mssql_type}")
        return CoreDataType.UNKNOWN


@dataclass
class StandardizedColumn:
    """標準化欄位定義"""
    column_name: str
    core_data_type: CoreDataType
    native_data_type: str  # 原始資料庫型別
    nullable: bool
    comment: Optional[str] = None
    max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_indexed: bool = False
    
    # LLM 語意對齐欄位
    semantic_mapping: Optional[str] = None  # 對應的標準實體欄位 (e.g., "patient_name_zh")
    semantic_confidence: Optional[float] = None  # 對應信心度 0-1
    ai_suggestion: Optional[str] = None  # AI 的完整建議理由
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "column_name": self.column_name,
            "core_data_type": self.core_data_type.value,
            "native_data_type": self.native_data_type,
            "nullable": self.nullable,
            "comment": self.comment,
            "max_length": self.max_length,
            "numeric_precision": self.numeric_precision,
            "numeric_scale": self.numeric_scale,
            "default_value": self.default_value,
            "is_primary_key": self.is_primary_key,
            "is_unique": self.is_unique,
            "is_indexed": self.is_indexed,
            "semantic_mapping": self.semantic_mapping,
            "semantic_confidence": self.semantic_confidence,
            "ai_suggestion": self.ai_suggestion,
        }


@dataclass
class StandardizedTable:
    """標準化資料表定義"""
    table_name: str
    table_schema: str
    table_comment: Optional[str] = None
    row_count: Optional[int] = None
    columns: List[StandardizedColumn] = field(default_factory=list)
    
    # 實體映射欄位
    entity_mapping: Optional[str] = None  # 對應的標準實體 (e.g., "Patient")
    entity_confidence: Optional[float] = None  # 實體對應信心度
    entity_suggestion: Optional[str] = None  # AI 的實體對應建議
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "table_name": self.table_name,
            "table_schema": self.table_schema,
            "table_comment": self.table_comment,
            "row_count": self.row_count,
            "columns": [col.to_dict() for col in self.columns],
            "entity_mapping": self.entity_mapping,
            "entity_confidence": self.entity_confidence,
            "entity_suggestion": self.entity_suggestion,
        }


@dataclass
class DataDictionary:
    """
    完整的資料字典
    包含所有標準化的表格、欄位和型別定義
    """
    database_name: str
    database_type: str  # "oracle", "postgresql", "sqlite", etc.
    timestamp: str  # ISO format
    tables: List[StandardizedTable] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "database_name": self.database_name,
            "database_type": self.database_type,
            "timestamp": self.timestamp,
            "total_tables": len(self.tables),
            "total_columns": sum(len(t.columns) for t in self.tables),
            "tables": [t.to_dict() for t in self.tables]
        }
    
    def to_json(self) -> str:
        """轉換為 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_yaml_like_string(self) -> str:
        """轉換為類似 YAML 的字符串格式"""
        output = []
        output.append(f"=== 資料字典 ===")
        output.append(f"資料庫: {self.database_name}")
        output.append(f"型別: {self.database_type}")
        output.append(f"時間: {self.timestamp}")
        output.append(f"表格總數: {len(self.tables)}")
        output.append("")
        
        for table in self.tables:
            output.append(f"【表格】 {table.table_name}")
            if table.entity_mapping:
                output.append(f"  實體映射: {table.entity_mapping} (信心: {table.entity_confidence:.0%})")
            if table.table_comment:
                output.append(f"  說明: {table.table_comment}")
            output.append(f"  行數: {table.row_count}")
            output.append(f"  欄位數: {len(table.columns)}")
            output.append("")
            
            for col in table.columns:
                flags = []
                if col.is_primary_key:
                    flags.append("PRIMARY_KEY")
                if col.is_unique:
                    flags.append("UNIQUE")
                if col.is_indexed:
                    flags.append("INDEXED")
                if not col.nullable:
                    flags.append("NOT_NULL")
                
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                
                output.append(f"    • {col.column_name}")
                output.append(f"      型別: {col.native_data_type} → {col.core_data_type.value}{flag_str}")
                if col.comment:
                    output.append(f"      說明: {col.comment}")
                if col.semantic_mapping:
                    output.append(f"      語意映射: {col.semantic_mapping} (信心: {col.semantic_confidence:.0%})")
            
            output.append("")
        
        return "\n".join(output)
    
    def get_unmapped_columns(self) -> List[tuple]:
        """
        取得所有未映射的欄位
        返回 (table_name, column_name, data_type, comment)
        """
        unmapped = []
        for table in self.tables:
            for col in table.columns:
                if col.semantic_mapping is None:
                    unmapped.append((table.table_name, col.column_name, col.native_data_type, col.comment))
        return unmapped
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """取得映射統計資訊"""
        total_columns = sum(len(t.columns) for t in self.tables)
        mapped_columns = sum(
            1 for t in self.tables 
            for c in t.columns 
            if c.semantic_mapping is not None
        )
        
        avg_confidence = 0
        if mapped_columns > 0:
            avg_confidence = sum(
                c.semantic_confidence or 0 
                for t in self.tables 
                for c in t.columns 
                if c.semantic_mapping is not None
            ) / mapped_columns
        
        return {
            "total_tables": len(self.tables),
            "total_columns": total_columns,
            "mapped_columns": mapped_columns,
            "unmapped_columns": total_columns - mapped_columns,
            "mapping_rate": mapped_columns / total_columns if total_columns > 0 else 0,
            "average_confidence": avg_confidence
        }
