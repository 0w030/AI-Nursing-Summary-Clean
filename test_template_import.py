"""
模板導入功能測試腳本 - 單個模板導入和圖片 OCR
"""

import sys
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, 'c:/AI-Nursing-Summary-Clean/AI-Nursing-Summary-Clean')

from db.template_service import extract_text_from_image, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, create_template, get_all_templates

print("=" * 60)
print("模板導入功能測試")
print("=" * 60)

# 測試 1: 創建文本圖片並進行 OCR
print("\n【測試 1】圖片 OCR 識別測試")
print("-" * 60)

try:
    # 建立一個簡單的圖片，包含中文文字
    img = Image.new('RGB', (400, 100), color='white')
    d = ImageDraw.Draw(img)
    
    # 注意：如果系統沒有安裝中文字體，可能無法正確渲染
    # 嘗試使用常見的系統字體
    try:
        # Windows 系統
        font = ImageFont.truetype('C:\\\\Windows\\\\Fonts\\\\SimSun.ttc', 30)
    except:
        try:
            # Linux 系統
            font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 30)
        except:
            # 如果沒有找到合適的字體，使用默認字體
            font = ImageFont.load_default()
    
    test_text = "這是護理模板測試文字"
    d.text((10, 30), test_text, fill='black', font=font)
    
    # 保存為字節流
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # 測試 OCR
    extracted_text, error = extract_text_from_image(img_byte_arr)
    
    if error:
        print(f"⚠️ 警告：{error}")
        print("   （初次運行 EasyOCR 需要下載模型，可能需要數分鐘）")
    else:
        print(f"✅ OCR 識別成功")
        print(f"   識別文字：{extracted_text}")

except Exception as e:
    print(f"❌ 錯誤：{str(e)}")
    print("   請確保已安裝 easyocr 和 pillow")

# 測試 2: 創建單個模板
print("\n【測試 2】創建單個模板")
print("-" * 60)

test_template_name = "護理評估模板"
test_template_content = "請評估患者的生命體徵、意識狀態和其他臨床指標"

result = create_template(test_template_name, test_template_content, "標準護理評估")

if result:
    print(f"✅ 成功創建模板：{test_template_name}")
else:
    print(f"❌ 創建模板失敗（可能已存在）")

# 測試 3: 驗證所有模板
print("\n【測試 3】驗證所有已導入的模板")
print("-" * 60)

all_templates = get_all_templates()

if all_templates:
    print(f"✅ 找到 {len(all_templates)} 個模板：")
    for idx, (name, content) in enumerate(all_templates.items(), 1):
        preview = content[:50] + "..." if len(content) > 50 else content
        print(f"   {idx}. {name}：{preview}")
else:
    print("⚠️ 暫無模板")

print("\n" + "=" * 60)
print("測試完成")
print("=" * 60)
