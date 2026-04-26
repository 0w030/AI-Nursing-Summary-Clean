# test_local_model.py
"""
快速測試本地模型集成
運行: python test_local_model.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_ollama_connection():
    """測試 Ollama 服務連線"""
    print("1️⃣ 測試 Ollama 連線...")
    try:
        from local_model_api_wrapper import is_local_model_available
        if is_local_model_available():
            print("   ✅ Ollama 服務正常")
            return True
        else:
            print("   ❌ Ollama 服務未連線")
            return False
    except ImportError:
        print("   ❌ 本地模型模組未安裝")
        return False


def test_model_inference():
    """測試模型推理"""
    print("\n2️⃣ 測試模型推理...")
    try:
        from local_model_api_wrapper import get_local_client
        
        client = get_local_client()
        result = client.chat_completion(
            system_prompt="你是醫療助手。簡潔回答。",
            user_message="什麼是高血壓?",
            temperature=0.3
        )
        
        if result["content"]:
            print(f"   ✅ 推理成功")
            print(f"   回應: {result['content'][:100]}...")
            return True
        else:
            print("   ❌ 推理返回空回應")
            return False
            
    except Exception as e:
        print(f"   ❌ 推理失敗: {e}")
        return False


def test_model_selection():
    """測試模型選擇邏輯"""
    print("\n3️⃣ 測試模型選擇邏輯...")
    try:
        from local_model_config import AIModelSource, MODEL_SELECTION_STRATEGY
        
        print(f"   預設模型源: {MODEL_SELECTION_STRATEGY['default'].value}")
        print("   ✅ 模型選擇邏輯正常")
        return True
    except Exception as e:
        print(f"   ❌ 模型配置錯誤: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("🧪 本地模型集成測試")
    print("="*60 + "\n")
    
    results = {
        "Ollama 連線": test_ollama_connection(),
        "模型推理": test_model_inference(),
        "模型選擇": test_model_selection(),
    }
    
    print("\n" + "="*60)
    print("測試結果摘要:")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{test_name:<20} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有測試通過！本地模型已準備就緒")
    else:
        print("⚠️  部分測試失敗，請檢查上述錯誤")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
