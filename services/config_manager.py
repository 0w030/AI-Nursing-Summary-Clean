"""
配置管理服務 - 管理資料庫連接和 Schema 映射配置
支持多資料庫配置切換，配置持久化到本地 JSON 文件
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config" / "management"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

DB_CONFIG_FILE = CONFIG_DIR / "db_connections.json"
SCHEMA_MAPPING_FILE = CONFIG_DIR / "schema_mappings.json"
OPERATION_LOG_FILE = CONFIG_DIR / "operation_logs.json"


@dataclass
class DatabaseConnection:
    """資料庫連接配置"""
    name: str
    db_type: str  # oracle, postgresql, sqlite, mssql
    host: str
    port: int
    database: str
    username: str
    password: str = ""  # 密碼字段（用於測試連接）
    is_active: bool = False
    created_at: str = None
    last_modified: str = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DatabaseConnection':
        return cls(**data)


@dataclass
class FieldMapping:
    """欄位映射配置 - 與資料庫連接綁定"""
    connection_name: str  # 資料庫連接名稱，用於標識此映射所屬的連接
    table_name: str
    db_column_name: str
    system_column_type: str
    original_type: str
    is_ai_suggested: bool = True
    is_confirmed: bool = False
    suggested_at: str = None
    confirmed_at: str = None
    confirmed_by: str = None
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FieldMapping':
        return cls(**data)


@dataclass
class OperationLog:
    """操作日誌"""
    timestamp: str
    operation_type: str  # connection_test, connection_switch, schema_sync, mapping_update
    username: str
    details: Dict[str, Any]
    status: str  # success, failed, warning
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ConfigManager:
    """配置管理器 - 統一管理所有配置
    
    映射存儲結構：
    schema_mappings: Dict[connection_name, Dict[table_name, List[FieldMapping]]]
    """
    
    def __init__(self):
        self.db_connections: Dict[str, DatabaseConnection] = {}
        self.schema_mappings: Dict[str, Dict[str, List[FieldMapping]]] = {}  # 修改為多層結構
        self.operation_logs: List[OperationLog] = []
        self._load_configs()
    
    # ===================== 資料庫連接管理 =====================
    
    def add_connection(self, connection: DatabaseConnection) -> bool:
        """添加或更新資料庫連接配置"""
        try:
            connection.created_at = connection.created_at or datetime.now().isoformat()
            connection.last_modified = datetime.now().isoformat()
            self.db_connections[connection.name] = connection
            # 初始化該連接的映射容器
            if connection.name not in self.schema_mappings:
                self.schema_mappings[connection.name] = {}
            self._save_db_connections()
            logger.info(f"[SUCCESS] 連接配置已保存: {connection.name}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 添加連接配置失敗: {e}")
            return False
    
    def get_connection(self, name: str) -> Optional[DatabaseConnection]:
        """根據名稱獲取連接配置"""
        return self.db_connections.get(name)
    
    def list_connections(self) -> List[DatabaseConnection]:
        """列表所有連接配置"""
        return list(self.db_connections.values())
    
    def get_active_connection(self) -> Optional[DatabaseConnection]:
        """獲取當前活動的連接"""
        for conn in self.db_connections.values():
            if conn.is_active:
                return conn
        return None
    
    def switch_connection(self, connection_name: str, username: str) -> Tuple[bool, str]:
        """切換活動連接
        
        Returns:
            (是否成功, 反饋信息)
        """
        try:
            # 取消當前活動連接
            for conn in self.db_connections.values():
                if conn.is_active:
                    conn.is_active = False
            
            # 設置新的活動連接
            if connection_name in self.db_connections:
                self.db_connections[connection_name].is_active = True
                self.db_connections[connection_name].last_modified = datetime.now().isoformat()
                self._save_db_connections()
                
                # 計算該連接的映射數量
                mapping_count = len(self.schema_mappings.get(connection_name, {}))
                if mapping_count > 0:
                    message = f"[SUCCESS] 已切換到資料庫連接: {connection_name} ({mapping_count} 個表格已映射)"
                else:
                    message = f"[WARNING] 已切換到資料庫連接: {connection_name} (暫無映射，請執行 Schema 同步)"
                
                # 記錄操作
                self._log_operation(
                    operation_type="connection_switch",
                    username=username,
                    details={"from": None, "to": connection_name, "mapping_count": mapping_count},
                    status="success"
                )
                logger.info(message)
                return True, message
            else:
                error_msg = f"[ERROR] 連接不存在: {connection_name}"
                logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"[ERROR] 切換連接失敗: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_connection(self, connection_name: str, username: str) -> bool:
        """刪除連接配置
        
        級聯刪除該連接的所有映射
        """
        try:
            if connection_name in self.db_connections:
                if self.db_connections[connection_name].is_active:
                    logger.error("[ERROR] 無法刪除活動中的連接")
                    return False
                
                # 級聯刪除該連接的所有映射
                deleted_mappings_count = len(self.schema_mappings.get(connection_name, {}))
                self.delete_connection_mappings(connection_name)
                
                # 刪除連接配置
                del self.db_connections[connection_name]
                self._save_db_connections()
                
                self._log_operation(
                    operation_type="connection_delete",
                    username=username,
                    details={
                        "connection": connection_name,
                        "cascade_deleted_mappings": deleted_mappings_count
                    },
                    status="success"
                )
                logger.info(f"[SUCCESS] 連接已刪除: {connection_name} (級聯刪除 {deleted_mappings_count} 個表格映射)")
                return True
            return False
        except Exception as e:
            logger.error(f"[ERROR] 刪除連接失敗: {e}")
            return False
    
    # ===================== Schema 映射管理 =====================
    
    def update_field_mapping(
        self,
        connection_name: str,
        table_name: str,
        field_mapping: FieldMapping,
        username: str
    ) -> bool:
        """更新欄位映射，綁定到指定連接
        
        Args:
            connection_name: 資料庫連接名稱
            table_name: 表格名稱
            field_mapping: 欄位映射對象
            username: 操作用戶
        """
        try:
            # 驗證連接存在
            if connection_name not in self.db_connections:
                logger.error(f"[ERROR] 連接不存在: {connection_name}")
                return False
            
            # 初始化連接的映射容器
            if connection_name not in self.schema_mappings:
                self.schema_mappings[connection_name] = {}
            
            if table_name not in self.schema_mappings[connection_name]:
                self.schema_mappings[connection_name][table_name] = []
            
            # 確保 FieldMapping 包含 connection_name
            field_mapping.connection_name = connection_name
            
            # 查找現有映射
            existing_index = None
            for idx, mapping in enumerate(self.schema_mappings[connection_name][table_name]):
                if mapping.db_column_name == field_mapping.db_column_name:
                    existing_index = idx
                    break
            
            # 更新或添加
            if existing_index is not None:
                self.schema_mappings[connection_name][table_name][existing_index] = field_mapping
            else:
                self.schema_mappings[connection_name][table_name].append(field_mapping)
            
            self._save_schema_mappings()
            
            # 記錄操作
            self._log_operation(
                operation_type="mapping_update",
                username=username,
                details={
                    "connection": connection_name,
                    "table": table_name,
                    "column": field_mapping.db_column_name,
                    "mapping": field_mapping.system_column_type
                },
                status="success"
            )
            logger.info(f"[SUCCESS] 欄位映射已更新: {connection_name}.{table_name}.{field_mapping.db_column_name}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 更新映射失敗: {e}")
            return False
    
    def get_table_mappings(self, connection_name: str, table_name: str) -> List[FieldMapping]:
        """獲取表格的所有欄位映射
        
        Args:
            connection_name: 資料庫連接名稱
            table_name: 表格名稱
        """
        return self.schema_mappings.get(connection_name, {}).get(table_name, [])
    
    def get_all_mappings(self) -> Dict[str, Dict[str, List[FieldMapping]]]:
        """獲取所有映射
        
        Returns:
            所有連接的映射: {connection_name: {table_name: [FieldMapping, ...]}}
        """
        return self.schema_mappings
    
    def get_connection_mappings(self, connection_name: str) -> Dict[str, List[FieldMapping]]:
        """根據連接名稱獲取該連接的所有映射
        
        Args:
            connection_name: 資料庫連接名稱
        
        Returns:
            該連接的所有表格映射 {table_name: [FieldMapping, ...]}
        """
        return self.schema_mappings.get(connection_name, {})
    
    def delete_connection_mappings(self, connection_name: str) -> bool:
        """刪除指定連接的所有映射
        
        Args:
            connection_name: 資料庫連接名稱
        
        Returns:
            是否刪除成功
        """
        if connection_name in self.schema_mappings:
            del self.schema_mappings[connection_name]
            self._save_schema_mappings()
            return True
        return False
    
    def bulk_update_mappings(
        self,
        mappings: Dict[str, List[FieldMapping]],
        connection_name: str,
        username: str
    ) -> bool:
        """批量更新映射
        
        Args:
            mappings: 表格映射 {table_name: [FieldMapping, ...]}
            connection_name: 資料庫連接名稱
            username: 操作用戶
        """
        try:
            # 驗證連接存在
            if connection_name not in self.db_connections:
                logger.error(f"[ERROR] 連接不存在: {connection_name}")
                return False
            
            # 整合新映射到連接
            self.schema_mappings[connection_name] = {}
            for table_name, field_mappings in mappings.items():
                # 确保每个 FieldMapping 都有 connection_name
                for mapping in field_mappings:
                    mapping.connection_name = connection_name
                self.schema_mappings[connection_name][table_name] = field_mappings
            
            self._save_schema_mappings()
            
            self._log_operation(
                operation_type="schema_sync",
                username=username,
                details={
                    "connection": connection_name,
                    "tables": len(mappings)
                },
                status="success"
            )
            logger.info(f"[SUCCESS] Schema 同步完成: {connection_name} - {len(mappings)} 個表格")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 批量更新失敗: {e}")
            return False
    
    def import_discovered_schema(
        self,
        discovered_schema: Dict[str, Any],
        connection_name: str,
        username: str,
        auto_type_map: bool = True
    ) -> Tuple[int, int]:
        """
        從發現的 Schema 導入映射
        
        Args:
            discovered_schema: 從 SchemaDiscoveryService 獲得的 Schema 字典
            connection_name: 資料庫連接名稱
            username: 執行操作的用戶名
            auto_type_map: 是否自動映射資料型別
            
        Returns:
            (導入的表格數, 導入的欄位數)
        """
        try:
            # 驗證連接存在
            if connection_name not in self.db_connections:
                logger.error(f"[ERROR] 連接不存在: {connection_name}")
                return 0, 0
            
            # 初始化連接的映射容器
            if connection_name not in self.schema_mappings:
                self.schema_mappings[connection_name] = {}
            
            imported_tables = 0
            imported_fields = 0
            
            # 導入映射的類型匹配規則
            type_mapping = {
                'VARCHAR2': 'String',
                'VARCHAR': 'String',
                'CHAR': 'String',
                'TEXT': 'String',
                'NVARCHAR': 'String',
                'NUMBER': 'Integer',
                'INTEGER': 'Integer',
                'INT': 'Integer',
                'BIGINT': 'Integer',
                'SMALLINT': 'Integer',
                'FLOAT': 'Decimal',
                'DECIMAL': 'Decimal',
                'NUMERIC': 'Decimal',
                'DOUBLE': 'Decimal',
                'TIMESTAMP': 'DateTime',
                'DATE': 'DateTime',
                'DATETIME': 'DateTime',
                'TIME': 'DateTime',
                'BOOLEAN': 'Boolean',
                'BOOL': 'Boolean',
                'JSON': 'JSON',
                'JSONB': 'JSON',
                'CLOB': 'String',
                'BLOB': 'String'
            }
            
            # 遍歷發現的表格
            for table_name, table_data in discovered_schema.get('tables', {}).items():
                table_mappings = []
                
                # 遍歷表格中的欄位
                for column_info in table_data.get('columns', []):
                    col_name = column_info['name']
                    col_type = column_info['data_type'].upper()
                    
                    # 自動映射類型
                    system_type = 'String'  # 默認類型
                    if auto_type_map:
                        for db_type, sys_type in type_mapping.items():
                            if db_type in col_type:
                                system_type = sys_type
                                break
                    
                    # 創建欄位映射
                    mapping = FieldMapping(
                        connection_name=connection_name,  # 新增：綁定連接
                        table_name=table_name,
                        db_column_name=col_name,
                        system_column_type=system_type,
                        original_type=col_type,
                        is_ai_suggested=True,
                        is_confirmed=False,
                        suggested_at=datetime.now().isoformat(),
                        notes=column_info.get('comment', '')
                    )
                    
                    table_mappings.append(mapping)
                    imported_fields += 1
                
                # 添加到映射集合
                if table_mappings:
                    self.schema_mappings[connection_name][table_name] = table_mappings
                    imported_tables += 1
            
            # 保存更新
            self._save_schema_mappings()
            
            # 記錄操作
            self._log_operation(
                operation_type="schema_import",
                username=username,
                details={
                    "connection": connection_name,
                    "tables": imported_tables,
                    "fields": imported_fields,
                    "auto_type_map": auto_type_map
                },
                status="success"
            )
            
            logger.info(f"[SUCCESS] Schema 導入完成: {connection_name} - {imported_tables} 個表格, {imported_fields} 個欄位")
            return imported_tables, imported_fields
            
        except Exception as e:
            logger.error(f"[ERROR] Schema 導入失敗: {e}")
            self._log_operation(
                operation_type="schema_import",
                username=username,
                details={"connection": connection_name, "error": str(e)},
                status="failed"
            )
            return 0, 0
    
    # ===================== 操作日誌 =====================
    
    def _log_operation(
        self,
        operation_type: str,
        username: str,
        details: Dict[str, Any],
        status: str
    ):
        """記錄操作"""
        log = OperationLog(
            timestamp=datetime.now().isoformat(),
            operation_type=operation_type,
            username=username,
            details=details,
            status=status
        )
        self.operation_logs.append(log)
        self._save_operation_logs()
    
    def get_operation_logs(self, limit: int = 50) -> List[OperationLog]:
        """獲取操作日誌"""
        return self.operation_logs[-limit:]
    
    def get_operation_logs_by_type(self, operation_type: str) -> List[OperationLog]:
        """按類型篩選操作日誌"""
        return [log for log in self.operation_logs if log.operation_type == operation_type]
    
    # ===================== 持久化 =====================
    
    def _save_db_connections(self):
        """保存資料庫連接配置"""
        try:
            data = {
                "connections": {
                    name: conn.to_dict()
                    for name, conn in self.db_connections.items()
                },
                "last_modified": datetime.now().isoformat()
            }
            with open(DB_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"[DEBUG] 連接配置已寫入: {DB_CONFIG_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] 保存連接配置失敗: {e}")
    
    def _save_schema_mappings(self):
        """保存 Schema 映射
        
        新結構: {connection_name: {table_name: [FieldMapping, ...]}}
        """
        try:
            data = {
                "mappings": {
                    conn_name: {
                        table_name: [m.to_dict() for m in mappings]
                        for table_name, mappings in tables_dict.items()
                    }
                    for conn_name, tables_dict in self.schema_mappings.items()
                },
                "last_modified": datetime.now().isoformat()
            }
            with open(SCHEMA_MAPPING_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"[DEBUG] Schema 映射已寫入: {SCHEMA_MAPPING_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] 保存 Schema 映射失敗: {e}")
    
    def _save_operation_logs(self):
        """保存操作日誌"""
        try:
            data = {
                "logs": [log.to_dict() for log in self.operation_logs],
                "total": len(self.operation_logs)
            }
            with open(OPERATION_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"[DEBUG] 操作日誌已寫入: {OPERATION_LOG_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] 保存操作日誌失敗: {e}")
    
    def _load_configs(self):
        """載入所有配置"""
        self._load_db_connections()
        self._load_schema_mappings()
        self._load_operation_logs()
    
    def _load_db_connections(self):
        """從文件載入資料庫連接配置"""
        try:
            if DB_CONFIG_FILE.exists():
                with open(DB_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, conn_data in data.get("connections", {}).items():
                        conn = DatabaseConnection.from_dict(conn_data)
                        self.db_connections[name] = conn
                        # 初始化連接的映射容器
                        if name not in self.schema_mappings:
                            self.schema_mappings[name] = {}
                logger.info(f"[INFO] 已載入 {len(self.db_connections)} 個連接配置")
            else:
                logger.info("[INFO] 沒有已保存的連接配置")
        except Exception as e:
            logger.error(f"[ERROR] 載入連接配置失敗: {e}")
    
    def _load_schema_mappings(self):
        """從文件載入 Schema 映射
        
        بییییبھڻںببڻںبںبڻببں: {connection_name: {table_name: [FieldMapping, ...]}}
        """
        try:
            if SCHEMA_MAPPING_FILE.exists():
                with open(SCHEMA_MAPPING_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    mappings_data = data.get("mappings", {})
                    
                    # 供接等上沒有上一个 schema_mappings.json 的旧結構
                    # 旧結構: {table_name: [FieldMapping, ...]}
                    # 新結構: {connection_name: {table_name: [FieldMapping, ...]}}
                    
                    # 梏測是旧結構還是新結構
                    if mappings_data and isinstance(next(iter(mappings_data.values()), None), dict):
                        # 新結構: {connection_name: {table_name: [...]}}
                        for conn_name, tables_dict in mappings_data.items():
                            self.schema_mappings[conn_name] = {}
                            for table_name, mappings_list in tables_dict.items():
                                self.schema_mappings[conn_name][table_name] = [
                                    FieldMapping.from_dict(m) for m in mappings_list
                                ]
                    else:
                        # 旧結構: {table_name: [...]}
                        # 將旧數據軽接戰並推謎到第一個活動連接
                        logger.warning("[WARNING] 偶測到旧的 Schema 映射結構，正在騎敖...")
                        active_conn = self.get_active_connection()
                        if active_conn:
                            for table_name, mappings_list in mappings_data.items():
                                if active_conn.name not in self.schema_mappings:
                                    self.schema_mappings[active_conn.name] = {}
                                self.schema_mappings[active_conn.name][table_name] = [
                                    FieldMapping.from_dict(m) for m in mappings_list
                                ]
                    
                total_tables = sum(len(tables) for tables in 
                                  [t for conn_tables in self.schema_mappings.values() 
                                   for t in (conn_tables.values() if isinstance(conn_tables, dict) else [])])
                logger.info(f"[INFO] 已載入 {total_tables} 個表格的映射")
            else:
                logger.info("[INFO] 沒有已保存的 Schema 映射")
        except Exception as e:
            logger.error(f"[ERROR] 載入 Schema 映射失敗: {e}")
    
    def _load_operation_logs(self):
        """從文件載入操作日誌"""
        try:
            if OPERATION_LOG_FILE.exists():
                with open(OPERATION_LOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.operation_logs = [
                        OperationLog(**log_data) for log_data in data.get("logs", [])
                    ]
                logger.info(f"[INFO] 已載入 {len(self.operation_logs)} 條操作日誌")
            else:
                logger.info("[INFO] 沒有操作日誌")
        except Exception as e:
            logger.error(f"[ERROR] 載入操作日誌失敗: {e}")


# 全局配置管理器實例
config_manager = ConfigManager()
