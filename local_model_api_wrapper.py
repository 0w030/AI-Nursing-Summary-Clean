# local_model_api_wrapper.py
"""
本地 Mistral 7B 推理服務 Wrapper
模擬 OpenAI API 格式，便於與 Groq API 互換
"""

import os
import json
import requests
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LocalModelConfig:
    """本地模型配置"""
    # 本地 Ollama 服務位置
    OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    
    # 模型名稱
    MODEL_NAME: str = os.getenv("LOCAL_MODEL_NAME", "mistral")
    
    # 推理參數
    TEMPERATURE: float = float(os.getenv("LOCAL_TEMP", "0.3"))
    TOP_P: float = float(os.getenv("LOCAL_TOP_P", "0.9"))
    MAX_TOKENS: int = int(os.getenv("LOCAL_MAX_TOKENS", "2000"))
    
    # 超時設定
    REQUEST_TIMEOUT: int = int(os.getenv("LOCAL_TIMEOUT", "120"))
    
    # 是否啟用本地模型
    ENABLED: bool = os.getenv("LOCAL_MODEL_ENABLED", "true").lower() == "true"
    
    # 是否使用量化版本 (節省 VRAM)
    USE_QUANTIZED: bool = os.getenv("USE_QUANTIZED", "false").lower() == "true"


class LocalModelClient:
    """本地 Mistral 模型客戶端 - OpenAI API 兼容"""
    
    def __init__(self, config: Optional[LocalModelConfig] = None):
        self.config = config or LocalModelConfig()
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """驗證與 Ollama 服務的連線"""
        try:
            response = requests.get(
                f"{self.config.OLLAMA_API_URL}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Ollama 服務已連線 ({self.config.OLLAMA_API_URL})")
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                print(f"   可用模型: {model_names}")
                return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Ollama 服務不可用: {e}")
            return False
    
    def chat_completion(self, 
                       system_prompt: str,
                       user_message: str,
                       temperature: Optional[float] = None) -> dict:
        """
        呼叫本地模型生成摘要
        
        Args:
            system_prompt: 系統角色提示
            user_message: 使用者查詢/病患資料
            temperature: 溫度參數 (覆蓋預設)
        
        Returns:
            {"content": "生成文本", "usage": {...}, "model": "mistral"}
        """
        
        if not self.config.ENABLED:
            raise RuntimeError("本地模型已禁用 (LOCAL_MODEL_ENABLED=false)")
        
        temperature = temperature or self.config.TEMPERATURE
        
        # 組合完整提示
        full_prompt = f"""{system_prompt}

用戶請求:
{user_message}"""
        
        try:
            # 呼叫 Ollama API (生成模式)
            response = requests.post(
                f"{self.config.OLLAMA_API_URL}/api/generate",
                json={
                    "model": self.config.MODEL_NAME,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "top_p": self.config.TOP_P,
                    "stream": False,  # 等待完整回應
                    "num_predict": self.config.MAX_TOKENS,
                },
                timeout=self.config.REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API 錯誤: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # 轉換為 OpenAI 格式
            return {
                "content": result.get("response", "").strip(),
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                },
                "model": self.config.MODEL_NAME,
                "source": "local"
            }
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"本地模型推理超時 ({self.config.REQUEST_TIMEOUT}s)")
        except Exception as e:
            raise RuntimeError(f"本地模型推理失敗: {str(e)}")


# 全局客戶端實例
_local_client = None

def get_local_client() -> LocalModelClient:
    """取得全局本地模型客戶端 (單例)"""
    global _local_client
    if _local_client is None:
        _local_client = LocalModelClient()
    return _local_client

def is_local_model_available() -> bool:
    """檢查本地模型是否可用"""
    try:
        client = get_local_client()
        return client._verify_connection()
    except Exception:
        return False
