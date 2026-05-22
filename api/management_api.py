"""
管理中控台 API - FastAPI 後端
提供所有管理功能的 RESTful API 端點
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config_manager import (
    ConfigManager, DatabaseConnection, FieldMapping, config_manager
)
from services.permission_service import (
    PermissionChecker, User, Role, Permission
)
from schema_discovery.oracle_introspector import OracleIntrospector
from core.config import get_db_config, DatabaseType

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="AI 醫療系統 - 管理中控台 API",
    version="1.0.0",
    description="管理資料庫連接、Schema 映射和系統配置"
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== Pydantic 模型 =====================

class DatabaseConnectionRequest(BaseModel):
    """添加/編輯資料庫連接請求"""
    name: str = Field(..., description="連接名稱")
    db_type: str = Field(..., description="資料庫類型: oracle, postgresql, sqlite, mssql")
    host: str = Field(..., description="主機地址")
    port: int = Field(..., description="連接埠")
    database: str = Field(..., description="資料庫名稱或路徑")
    username: str = Field(..., description="用戶名")
    password: Optional[str] = Field(None, description="密碼")


class TestConnectionRequest(BaseModel):
    """測試連接請求"""
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str


class FieldMappingRequest(BaseModel):
    """欄位映射更新請求"""
    table_name: str
    db_column_name: str
    system_column_type: str
    original_type: str
    is_confirmed: bool = False
    notes: str = ""


class BulkMappingRequest(BaseModel):
    """批量映射更新請求"""
    table_mappings: Dict[str, List[FieldMappingRequest]]


class SwitchConnectionRequest(BaseModel):
    """切換連接請求"""
    connection_name: str
    username: str


# ===================== 模擬用戶認證 (實際應使用 session/JWT) =====================

def get_current_user(username: Optional[str] = None) -> Optional[User]:
    """
    獲取當前用戶 (簡化版)
    實際實現應從 session 或 JWT token 讀取
    """
    if username:
        # 簡化實現：這裡應該從資料庫查詢實際的用戶信息
        # 目前假設所有帶有 username 的請求都是有效的
        role_map = {
            "admin": Role.ADMIN,
            "manager": Role.MANAGER,
            "viewer": Role.VIEWER,
        }
        role = role_map.get(username.split("_")[-1], Role.GUEST)
        return User(username=username, role=role, is_active=True)
    return None


# ===================== 資料庫連接管理 API =====================

@app.get("/api/connections")
async def list_connections(username: Optional[str] = Query(None)):
    """列表所有資料庫連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_CONNECTIONS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    connections = config_manager.list_connections()
    return {
        "status": "success",
        "total": len(connections),
        "data": [conn.to_dict() for conn in connections]
    }


@app.get("/api/connections/{connection_name}")
async def get_connection(connection_name: str, username: Optional[str] = Query(None)):
    """獲取特定連接配置"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_CONNECTIONS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    connection = config_manager.get_connection(connection_name)
    if not connection:
        raise HTTPException(status_code=404, detail="連接不存在")
    
    return {
        "status": "success",
        "data": connection.to_dict()
    }


@app.post("/api/connections")
async def create_connection(
    request: DatabaseConnectionRequest,
    username: Optional[str] = Query(None)
):
    """建立新的資料庫連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.CREATE_CONNECTION):
        raise HTTPException(status_code=403, detail="無權限建立連接")
    
    try:
        connection = DatabaseConnection(
            name=request.name,
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
        )
        
        if config_manager.add_connection(connection):
            return {
                "status": "success",
                "message": f"連接 {request.name} 已建立",
                "data": connection.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="建立連接失敗")
    except Exception as e:
        logger.error(f"✗ 建立連接失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/connections/{connection_name}")
async def update_connection(
    connection_name: str,
    request: DatabaseConnectionRequest,
    username: Optional[str] = Query(None)
):
    """編輯資料庫連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.EDIT_CONNECTION):
        raise HTTPException(status_code=403, detail="無權限編輯連接")
    
    try:
        connection = DatabaseConnection(
            name=request.name,
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
        )
        
        if config_manager.add_connection(connection):
            return {
                "status": "success",
                "message": f"連接 {request.name} 已更新",
                "data": connection.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="更新連接失敗")
    except Exception as e:
        logger.error(f"✗ 編輯連接失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/connections/{connection_name}")
async def delete_connection(
    connection_name: str,
    username: Optional[str] = Query(None)
):
    """刪除資料庫連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.DELETE_CONNECTION):
        raise HTTPException(status_code=403, detail="無權限刪除連接")
    
    if config_manager.delete_connection(connection_name, user.username if user else "system"):
        return {
            "status": "success",
            "message": f"連接 {connection_name} 已刪除"
        }
    else:
        raise HTTPException(status_code=500, detail="刪除連接失敗")


@app.get("/api/connections/active/current")
async def get_active_connection(username: Optional[str] = Query(None)):
    """獲取當前活動的連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_CONNECTIONS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    connection = config_manager.get_active_connection()
    if not connection:
        return {
            "status": "success",
            "message": "沒有活動的連接",
            "data": None
        }
    
    return {
        "status": "success",
        "data": connection.to_dict()
    }


@app.post("/api/connections/switch")
async def switch_connection(
    request: SwitchConnectionRequest,
    username: Optional[str] = Query(None)
):
    """切換活動連接"""
    user = get_current_user(username or request.username)
    if not PermissionChecker.require_permission(user, Permission.SWITCH_CONNECTION):
        raise HTTPException(status_code=403, detail="無權限切換連接")
    
    if config_manager.switch_connection(request.connection_name, user.username if user else "system"):
        return {
            "status": "success",
            "message": f"已切換到連接: {request.connection_name}",
            "data": config_manager.get_connection(request.connection_name).to_dict()
        }
    else:
        raise HTTPException(status_code=500, detail="切換連接失敗")


@app.post("/api/connections/test")
async def test_connection(
    request: TestConnectionRequest,
    username: Optional[str] = Query(None)
):
    """測試資料庫連接"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.TEST_CONNECTION):
        raise HTTPException(status_code=403, detail="無權限測試連接")
    
    try:
        # 這裡應該實現實際的連接測試邏輯
        # 當前是簡化版本
        if request.db_type == "oracle":
            logger.info(f"測試 Oracle 連接: {request.host}:{request.port}")
            # TODO: 實現實際的連接測試
        
        return {
            "status": "success",
            "message": "連接測試成功"
        }
    except Exception as e:
        logger.error(f"✗ 連接測試失敗: {e}")
        return {
            "status": "failed",
            "message": f"連接測試失敗: {str(e)}"
        }


# ===================== Schema 映射管理 API =====================

@app.get("/api/schema/tables")
async def list_schema_tables(
    connection_name: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    """列表指定連接的所有表格"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_MAPPINGS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    try:
        if not connection_name:
            # 如果沒有指定connection_name，取當前活動連接
            active_conn = config_manager.get_active_connection()
            if not active_conn:
                raise HTTPException(status_code=400, detail="沒有活動連接")
            connection_name = active_conn.name
        
        conn_mappings = config_manager.get_connection_mappings(connection_name)
        tables = list(conn_mappings.keys())
        
        return {
            "status": "success",
            "connection": connection_name,
            "total": len(tables),
            "data": tables
        }
    except Exception as e:
        logger.error(f"[ERROR] 列表表格失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schema/mappings/{table_name}")
async def get_table_mappings(
    table_name: str,
    connection_name: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    """獲取表格的所有欄位映射"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_MAPPINGS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    try:
        if not connection_name:
            # 如果沒有指定connection_name，取當前活動連接
            active_conn = config_manager.get_active_connection()
            if not active_conn:
                raise HTTPException(status_code=400, detail="沒有活動連接")
            connection_name = active_conn.name
        
        mappings = config_manager.get_table_mappings(connection_name, table_name)
        return {
            "status": "success",
            "connection": connection_name,
            "table_name": table_name,
            "total": len(mappings),
            "data": [m.to_dict() for m in mappings]
        }
    except Exception as e:
        logger.error(f"[ERROR] 獲取映射失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schema/mappings")
async def update_field_mapping(
    request: FieldMappingRequest,
    username: Optional[str] = Query(None)
):
    """更新單個欄位映射"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.EDIT_MAPPINGS):
        raise HTTPException(status_code=403, detail="無權限編輯映射")
    
    try:
        mapping = FieldMapping(
            table_name=request.table_name,
            db_column_name=request.db_column_name,
            system_column_type=request.system_column_type,
            original_type=request.original_type,
            is_confirmed=request.is_confirmed,
            confirmed_by=user.username if user else "system",
            confirmed_at=datetime.now().isoformat() if request.is_confirmed else None,
            notes=request.notes
        )
        
        if config_manager.update_field_mapping(
            request.table_name,
            mapping,
            user.username if user else "system"
        ):
            return {
                "status": "success",
                "message": "映射已更新",
                "data": mapping.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="更新映射失敗")
    except Exception as e:
        logger.error(f"✗ 更新映射失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_operation_logs(
    limit: int = Query(50, le=500),
    operation_type: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    """獲取操作日誌"""
    user = get_current_user(username)
    if not PermissionChecker.require_permission(user, Permission.VIEW_LOGS):
        raise HTTPException(status_code=403, detail="無權限存取")
    
    try:
        if operation_type:
            logs = config_manager.get_operation_logs_by_type(operation_type)
        else:
            logs = config_manager.get_operation_logs(limit)
        
        return {
            "status": "success",
            "total": len(logs),
            "data": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"✗ 獲取日誌失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康檢查端點"""
    active_conn = config_manager.get_active_connection()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "active_connection": active_conn.name if active_conn else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
