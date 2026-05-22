# api/main.py
"""
FastAPI 應用入口
展示如何使用依賴注入容器和 Repository 模式
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_db_config
from core.di_container import initialize_di_container, close_di_container, get_di_container
from services.patient_service import PatientService


# ============================================
# 生命週期管理
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 應用生命週期管理
    startup: 初始化資料庫連線與 DI 容器
    shutdown: 關閉連線與清理資源
    """
    # ========== 啟動 ==========
    print("🚀 應用啟動...")
    
    # 載入資料庫配置
    config = get_db_config()
    print(f"✅ 資料庫類型: {config.db_type.value}")
    print(f"✅ 連接字串: {config.get_connection_string()[:50]}...")
    
    # 初始化 DI 容器
    container = await initialize_di_container()
    print("✅ DI 容器已初始化")
    
    yield  # 應用運行
    
    # ========== 關閉 ==========
    print("🛑 應用關閉...")
    await close_di_container()
    print("✅ 資源已清理")


# ============================================
# 建立 FastAPI 應用
# ============================================

app = FastAPI(
    title="AI 醫療護理系統",
    description="支援多資料庫的醫療信息系統",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================
# CORS 配置
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 依賴函數
# ============================================

def get_patient_service() -> PatientService:
    """
    依賴注入: 取得患者服務
    FastAPI 會自動管理生命週期
    """
    container = get_di_container()
    patient_repo = container.get_patient_repository()
    nursing_repo = container.get_nursing_record_repository()
    return PatientService(patient_repo, nursing_repo)


# ============================================
# 健康檢查端點
# ============================================

@app.get("/health", tags=["系統"])
async def health_check():
    """系統健康檢查"""
    try:
        config = get_db_config()
        container = get_di_container()
        
        # 嘗試執行一個簡單的查詢驗證連接
        repo = container.get_patient_repository()
        
        return {
            "status": "healthy",
            "database_type": config.db_type.value,
            "connection": "ok",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }, 503


# ============================================
# 患者相關端點
# ============================================

@app.get("/api/patients/{patient_id}/overview", tags=["患者"])
async def get_patient_overview(
    patient_id: str,
    service: PatientService = Depends(get_patient_service),
):
    """
    取得患者概覽信息
    
    示範: 業務邏輯完全不知道底層使用哪種資料庫
    透過 Repository 介面與資料層互動
    """
    result = await service.get_patient_overview(patient_id)
    if not result:
        raise HTTPException(status_code=404, detail="患者不存在")
    return result


@app.get("/api/patients/{patient_id}/history", tags=["患者"])
async def get_patient_history(
    patient_id: str,
    start_time: str = None,
    end_time: str = None,
    service: PatientService = Depends(get_patient_service),
):
    """
    取得患者完整病歷（護理、生理、檢驗）
    
    示範: 代碼中沒有任何資料庫特定的導入或 SQL
    """
    result = await service.get_patient_full_history(
        patient_id=patient_id,
        start_time=start_time,
        end_time=end_time,
    )
    if not result:
        raise HTTPException(status_code=404, detail="患者不存在")
    return result


@app.get("/api/patients", tags=["患者"])
async def list_patients(
    skip: int = 0,
    limit: int = 20,
    service: PatientService = Depends(get_patient_service),
):
    """列出患者列表"""
    return await service.list_patients(skip=skip, limit=limit)


@app.get("/api/patients/search", tags=["患者"])
async def search_patients(
    q: str,
    limit: int = 20,
    service: PatientService = Depends(get_patient_service),
):
    """搜尋患者"""
    if not q:
        raise HTTPException(status_code=400, detail="查詢字串不能為空")
    return await service.search_patients(q, limit=limit)


# ============================================
# 系統信息端點
# ============================================

@app.get("/api/config", tags=["系統"])
async def get_system_config():
    """
    取得系統配置信息
    
    用途: 驗收標準 #2 - 驗證動態切換是否成功
    """
    config = get_db_config()
    return {
        "database_type": config.db_type.value,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "pool_size": config.pool_size,
        "echo_sql": config.echo_sql,
    }


# ============================================
# 根端點
# ============================================

@app.get("/", tags=["文檔"])
async def root():
    """根路由 - 重定向到 API 文檔"""
    return {
        "message": "歡迎使用 AI 醫療護理系統",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
