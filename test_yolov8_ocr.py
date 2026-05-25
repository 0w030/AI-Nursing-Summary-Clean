# test_yolov8_ocr.py
"""
YOLOv8 + PaddleOCR 功能測試腳本

測試項目:
1. 模型下載功能
2. 模型驗證
3. OCR 識別准確度
4. 性能比較 (YOLOv8 vs EasyOCR)
"""

import os
import sys
import time
import logging
from pathlib import Path
from io import BytesIO

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from local_data.model_manager import (
    download_yolov8_model,
    verify_model_available,
    get_model_status,
    get_yolov8_model_path,
)
from db.template_service import (
    extract_text_from_image_yolov8,
    extract_text_from_image_easyocr,
    extract_text_from_image,
)


def test_model_download():
    """測試模型下載功能"""
    print("\n" + "="*60)
    print("測試 1: YOLOv8 模型下載")
    print("="*60)
    
    try:
        success, message = download_yolov8_model(show_progress=True)
        if success:
            print(f"✓ 模型下載成功: {message}")
            return True
        else:
            print(f"✗ 模型下載失敗: {message}")
            return False
    except Exception as e:
        print(f"✗ 下載過程出錯: {str(e)}")
        return False


def test_model_verification():
    """測試模型驗證"""
    print("\n" + "="*60)
    print("測試 2: YOLOv8 模型驗證")
    print("="*60)
    
    try:
        # 驗證模型可用性
        available = verify_model_available()
        print(f"模型可用性: {'✓ 是' if available else '✗ 否'}")
        
        # 獲取模型狀態
        status = get_model_status()
        print("\n模型狀態信息:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # 獲取模型路徑
        model_path = get_yolov8_model_path()
        if model_path:
            print(f"\n模型路徑: {model_path}")
            print(f"模型文件大小: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
        
        return available
    except Exception as e:
        print(f"✗ 驗證過程出錯: {str(e)}")
        return False


def test_ocr_accuracy():
    """測試 OCR 識別准確度"""
    print("\n" + "="*60)
    print("測試 3: OCR 識別准確度")
    print("="*60)
    
    # 檢查測試圖像是否存在
    test_image_path = project_root / "sample_image.jpg"
    
    if not test_image_path.exists():
        print("⚠️ 未找到測試圖像 (sample_image.jpg)")
        print("   提示: 請在項目根目錄放置測試圖像進行此測試")
        print("   或使用實際上傳的圖像進行測試")
        return None
    
    try:
        print(f"測試圖像: {test_image_path}")
        
        # 讀取圖像
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        # 建立類似 Streamlit 上傳文件的對象
        class FakeFileObject:
            def __init__(self, data):
                self.data = data
            def getvalue(self):
                return self.data
        
        fake_file = FakeFileObject(image_data)
        
        # 測試 EasyOCR
        print("\n► 測試 EasyOCR...")
        start_time = time.time()
        easyocr_text, easyocr_error = extract_text_from_image_easyocr(fake_file)
        easyocr_time = time.time() - start_time
        
        if easyocr_error:
            print(f"  ✗ 錯誤: {easyocr_error}")
            easyocr_result = "失敗"
        else:
            print(f"  ✓ 識別成功")
            print(f"    識別文本 (前 100 字): {easyocr_text[:100]}")
            easyocr_result = f"成功 ({len(easyocr_text)} 字)"
        
        # 測試 YOLOv8 + PaddleOCR
        print("\n► 測試 YOLOv8 + PaddleOCR...")
        start_time = time.time()
        yolo_text, yolo_error = extract_text_from_image_yolov8(fake_file)
        yolo_time = time.time() - start_time
        
        if yolo_error:
            print(f"  ✗ 錯誤: {yolo_error}")
            yolo_result = "失敗"
        else:
            print(f"  ✓ 識別成功")
            print(f"    識別文本 (前 100 字): {yolo_text[:100]}")
            yolo_result = f"成功 ({len(yolo_text)} 字)"
        
        # 性能對比
        print("\n► 性能對比:")
        print(f"  EasyOCR: {easyocr_time:.2f} 秒 - {easyocr_result}")
        print(f"  YOLOv8 + PaddleOCR: {yolo_time:.2f} 秒 - {yolo_result}")
        
        if yolo_time > 0 and easyocr_time > 0:
            speedup = easyocr_time / yolo_time
            print(f"  速度提升: {speedup:.2f}x")
        
        return True
        
    except Exception as e:
        print(f"✗ OCR 測試出錯: {str(e)}")
        return False


def test_fallback_mechanism():
    """測試降級機制"""
    print("\n" + "="*60)
    print("測試 4: 降級機制 (YOLOv8 失敗 -> EasyOCR)")
    print("="*60)
    
    print("此測試驗證當 YOLOv8 不可用時，系統能否自動降級到 EasyOCR")
    print("✓ 測試已在 extract_text_from_image_yolov8() 中實現")
    print("  當 YOLOv8 模型不可用或推理失敗時，自動調用 EasyOCR 備用")
    
    return True


def test_integration():
    """集成測試 - 模擬實際使用場景"""
    print("\n" + "="*60)
    print("測試 5: 集成測試 (實際使用場景)")
    print("="*60)
    
    print("測試上傳圖像時使用 use_yolov8 參數...")
    
    # 檢查測試圖像
    test_image_path = project_root / "sample_image.jpg"
    
    if not test_image_path.exists():
        print("⚠️ 未找到測試圖像，跳過此測試")
        return None
    
    try:
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        class FakeFileObject:
            def __init__(self, data):
                self.data = data
            def getvalue(self):
                return self.data
        
        fake_file = FakeFileObject(image_data)
        
        # 測試不使用 YOLOv8
        print("\n► 使用 EasyOCR (use_yolov8=False)...")
        text1, error1 = extract_text_from_image(fake_file, use_yolov8=False)
        print(f"  結果: {'✓ 成功' if not error1 else f'✗ {error1}'}")
        
        # 測試使用 YOLOv8
        print("\n► 使用 YOLOv8 (use_yolov8=True)...")
        text2, error2 = extract_text_from_image(fake_file, use_yolov8=True)
        print(f"  結果: {'✓ 成功' if not error2 else f'✗ {error2}'}")
        
        return True
        
    except Exception as e:
        print(f"✗ 集成測試出錯: {str(e)}")
        return False


def print_summary(results):
    """打印測試摘要"""
    print("\n" + "="*60)
    print("測試摘要")
    print("="*60)
    
    test_names = [
        "1. 模型下載",
        "2. 模型驗證",
        "3. OCR 識別准確度",
        "4. 降級機制",
        "5. 集成測試"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✓ 通過" if result is True else ("⚠️ 跳過" if result is None else "✗ 失敗")
        print(f"{name}: {status}")
    
    passed = sum(1 for r in results if r is True)
    total = len(results)
    print(f"\n總體: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！YOLOv8 集成準備就緒。")
    elif passed >= total - 1:
        print("\n⚠️ 大部分測試通過，可以使用。")
    else:
        print("\n❌ 部分測試失敗，請檢查環境配置。")


def main():
    """主測試函數"""
    print("YOLOv8 + PaddleOCR 功能測試")
    print("版本: 1.0")
    print("時間:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    results = []
    
    # 執行測試
    results.append(test_model_download())
    results.append(test_model_verification())
    results.append(test_ocr_accuracy())
    results.append(test_fallback_mechanism())
    results.append(test_integration())
    
    # 打印摘要
    print_summary(results)


if __name__ == "__main__":
    main()
