# local_model_config.py
"""
本地模型與 Groq 的路由配置
"""

from enum import Enum
from typing import Literal

class AIModelSource(Enum):
    """AI 模型來源"""
    LOCAL = "local"        # 本地 Mistral 7B
    GROQ = "groq"         # 遠端 Groq API
    AUTO = "auto"         # 自動選擇 (優先本地)


# 模型選擇邏輯
MODEL_SELECTION_STRATEGY = {
    # 優先順序: local > groq
    "default": AIModelSource.AUTO,
    
    # 特定場景可強制使用某個模型
    "scenarios": {
        "high_precision_needed": AIModelSource.GROQ,      # 需要極高精度用 Groq
        "offline_mode": AIModelSource.LOCAL,              # 離線模式用本地
        "cost_sensitive": AIModelSource.LOCAL,            # 成本敏感用本地
    }
}

# 本地模型性能參考
LOCAL_MODEL_SPECS = {
    "model_name": "mistral",
    "parameters": "7B",
    "quantization": "bfloat16",  # 量化方式
    "vram_required": "6-8 GB",
    "inference_speed": "30-60 tokens/sec",
    "latency_per_request": "10-30 seconds (500-1000 tokens output)",
    "suitable_for": "病患摘要、診斷協助、紀錄整理",
    "not_suitable_for": "極高精度醫療決策"
}

# 回退策略
FALLBACK_CONFIG = {
    # 如果本地模型失敗，自動切換到 Groq
    "enable_fallback": True,
    "fallback_to": AIModelSource.GROQ,
    
    # 失敗重試次數
    "max_retries": 2,
    "retry_delay": 2,  # 秒
}

# ============================================================
# YOLOv8 OCR 配置
# ============================================================

# YOLOv8 OCR 全局配置
YOLOV8_OCR_CONFIG = {
    "enabled": False,              # 默認禁用（節省資源）
    "auto_download": True,         # 首次使用時自動下載模型
    "confidence_threshold": 0.5,   # 識別置信度 (0-1)
    "device": "cpu",               # 運行設備: 'cpu' 或 'cuda' 或 'mps'
    "model_size": "nano",          # 模型大小: 'nano' (6MB) 或 'small' (27MB)
    "cache_enabled": True,         # 是否快取模型到內存
    "language": "ch",              # OCR 語言: 'ch' (中文), 'en' (英文), 'auto' (自動)
}

# YOLOv8 模型規格參考
YOLOV8_MODEL_SPECS = {
    "nano": {
        "model_name": "yolov8n.pt",
        "size_mb": 6.3,
        "inference_speed_fps": "80-120",  # FPS
        "latency_ms": "8-12",             # 毫秒
        "vram_required": "100-200 MB",
        "suitable_for": "快速 OCR、邊界檢測、實時推理",
    },
    "small": {
        "model_name": "yolov8s.pt",
        "size_mb": 22.5,
        "inference_speed_fps": "30-50",
        "latency_ms": "20-30",
        "vram_required": "500-800 MB",
        "suitable_for": "高精度 OCR、精細檢測",
    }
}

# YOLOv8 模型路徑配置
YOLOV8_PATHS = {
    "models_dir": "local_data/models",
    "metadata_file": "local_data/models/yolov8_metadata.json",
    "cache_dir": "local_data/.yolov8_cache",
}

# 監控與日誌
MONITORING_CONFIG = {
    "log_model_selection": True,
    "track_performance_metrics": True,
    "compare_results": True,  # 並行調用記錄差異
}
