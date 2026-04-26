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

# 監控與日誌
MONITORING_CONFIG = {
    "log_model_selection": True,
    "track_performance_metrics": True,
    "compare_results": True,  # 並行調用記錄差異
}
