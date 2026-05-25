# local_data/model_manager.py
"""
YOLOv8 模型管理模塊 - 處理模型下載、快取和驗證

功能:
- 自動下載 YOLOv8 Nano 模型到本地
- 模型驗證和快取管理
- 模型路徑解析
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict

# 設置日誌
logger = logging.getLogger(__name__)

# 模型配置
MODELS_DIR = Path(__file__).parent / "models"
YOLOV8_MODEL_NAME = "yolov8n.pt"
YOLOV8_MODEL_PATH = Path(r"C:\AI-Nursing-Summary-Clean\AI-Nursing-Summary-Clean\yolov8n.pt")
YOLOV8_METADATA_FILE = MODELS_DIR / "yolov8_metadata.json"

# 模型來源 (Hugging Face 快速下載)
YOLOV8_MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n.pt"

# 全局模型快取
_model_cache: Dict[str, object] = {}


def ensure_models_directory() -> Path:
    """確保模型目錄存在"""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR


def get_yolov8_model_path() -> Optional[str]:
    """
    獲取 YOLOv8 模型路徑
    如果模型不存在，返回 None
    """
    if YOLOV8_MODEL_PATH.exists():
        return str(YOLOV8_MODEL_PATH)
    return None


def download_yolov8_model(show_progress: bool = False) -> Tuple[bool, str]:
    """
    下載 YOLOv8 Nano 模型到本地
    
    參數:
        show_progress: 是否顯示下載進度
    
    返回:
        (成功與否, 訊息)
    """
    try:
        ensure_models_directory()
        
        # 如果模型已存在，直接返回
        if YOLOV8_MODEL_PATH.exists():
            logger.info(f"✓ YOLOv8 模型已存在: {YOLOV8_MODEL_PATH}")
            return True, f"模型已存在: {YOLOV8_MODEL_PATH}"
        
        logger.info(f"⏳ 正在下載 YOLOv8 模型: {YOLOV8_MODEL_URL}")
        
        # 使用 ultralytics 庫的官方下載方式
        try:
            from ultralytics import YOLO
            
            model = YOLO(r'C:\AI-Nursing-Summary-Clean\AI-Nursing-Summary-Clean\yolov8n.pt')
            
            # 驗證模型
            if model.model and YOLOV8_MODEL_PATH.exists():
                _save_metadata()
                logger.info(f"✓ YOLOv8 模型下載成功")
                return True, "YOLOv8 模型下載成功"
            else:
                return False, "模型下載後驗證失敗"
                
        except Exception as e:
            logger.error(f"✗ 模型下載失敗: {str(e)}")
            return False, f"模型下載失敗: {str(e)}"
            
    except Exception as e:
        logger.error(f"✗ 模型管理錯誤: {str(e)}")
        return False, f"模型管理錯誤: {str(e)}"


def verify_model_available() -> bool:
    """
    驗證 YOLOv8 模型是否可用
    
    返回:
        模型是否可用
    """
    if YOLOV8_MODEL_PATH.exists():
        # 簡單的文件大小檢查 (yolov8n.pt 應該 ~6-7MB)
        file_size_mb = YOLOV8_MODEL_PATH.stat().st_size / (1024 * 1024)
        if file_size_mb > 1:  # 至少 1MB
            logger.info(f"✓ YOLOv8 模型驗證成功 ({file_size_mb:.1f} MB)")
            return True
    
    logger.warning("✗ YOLOv8 模型未找到或無效")
    return False


def get_cached_yolov8_model():
    """
    獲取快取的 YOLOv8 模型實例
    
    如果模型不在快取中，會嘗試加載
    """
    if "yolov8_model" in _model_cache:
        return _model_cache["yolov8_model"]
    
    try:
        if not verify_model_available():
            logger.warning("YOLOv8 模型不可用")
            return None
        
        from ultralytics import YOLO
        model = YOLO(str(YOLOV8_MODEL_PATH))
        _model_cache["yolov8_model"] = model
        logger.info("✓ YOLOv8 模型已加載到快取")
        return model
        
    except Exception as e:
        logger.error(f"✗ 加載 YOLOv8 模型失敗: {str(e)}")
        return None


def clear_model_cache():
    """清空模型快取"""
    _model_cache.clear()
    logger.info("✓ 模型快取已清空")


def _save_metadata():
    """保存模型元數據"""
    try:
        metadata = {
            "model_name": YOLOV8_MODEL_NAME,
            "model_path": str(YOLOV8_MODEL_PATH),
            "downloaded_at": datetime.now().isoformat(),
            "model_size_mb": YOLOV8_MODEL_PATH.stat().st_size / (1024 * 1024) if YOLOV8_MODEL_PATH.exists() else None
        }
        with open(YOLOV8_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"無法保存元數據: {str(e)}")


def get_model_status() -> Dict:
    """
    獲取模型狀態信息
    
    返回:
        模型狀態字典
    """
    status = {
        "yolov8_available": verify_model_available(),
        "yolov8_path": str(YOLOV8_MODEL_PATH) if YOLOV8_MODEL_PATH.exists() else None,
        "yolov8_cached": "yolov8_model" in _model_cache,
    }
    
    # 添加文件大小信息
    if YOLOV8_MODEL_PATH.exists():
        status["yolov8_size_mb"] = YOLOV8_MODEL_PATH.stat().st_size / (1024 * 1024)
    
    return status


# 引入 datetime（放在末尾避免 forward reference）
from datetime import datetime

if __name__ == "__main__":
    # 測試代碼
    print("YOLOv8 模型管理器 - 測試")
    print("-" * 50)
    
    # 顯示模型狀態
    status = get_model_status()
    print(f"模型狀態: {json.dumps(status, ensure_ascii=False, indent=2)}")
    
    # 嘗試下載模型
    print("\n正在檢查模型...")
    success, message = download_yolov8_model(show_progress=True)
    print(f"結果: {message}")
    
    # 驗證模型
    print(f"\n模型驗證: {'✓ 成功' if verify_model_available() else '✗ 失敗'}")
