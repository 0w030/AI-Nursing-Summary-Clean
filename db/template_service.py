# import psycopg2
# from db.db_connector import get_db_connection

# def get_all_templates():
#     """取得所有模板的名稱與內容，回傳為字典格式 {name: content}"""
#     conn = get_db_connection()
#     if not conn: return {}

#     templates = {}
#     try:
#         with conn.cursor() as cur:
#             cur.execute("SELECT template_name, template_content FROM prompt_templates ORDER BY id ASC")
#             rows = cur.fetchall()
#             for row in rows:
#                 templates[row[0]] = row[1]
#         return templates
#     except Exception as e:
#         print(f"查詢模板失敗: {e}")
#         return {}
#     finally:
#         conn.close()

# def create_template(name, content, description=""):
#     """新增一個模板"""
#     conn = get_db_connection()
#     if not conn: return False

#     try:
#         with conn.cursor() as cur:
#             cur.execute("""
#                 INSERT INTO prompt_templates (template_name, template_content, description)
#                 VALUES (%s, %s, %s)
#             """, (name, content, description))
#         conn.commit()
#         return True
#     except Exception as e:
#         print(f"新增模板失敗: {e}")
#         conn.rollback()
#         return False
#     finally:
#         conn.close()

# def update_template(old_name, new_content):
#     """更新現有模板的內容"""
#     conn = get_db_connection()
#     if not conn: return False

#     try:
#         with conn.cursor() as cur:
#             cur.execute("""
#                 UPDATE prompt_templates 
#                 SET template_content = %s, updated_at = NOW()
#                 WHERE template_name = %s
#             """, (new_content, old_name))
#         conn.commit()
#         return True
#     except Exception as e:
#         print(f"更新模板失敗: {e}")
#         conn.rollback()
#         return False
#     finally:
#         conn.close()

# 以下為SQLite版本

# db/template_service.py
import sqlite3
import os
import json
from pypdf import PdfReader
from docx import Document
from PIL import Image
import io
import logging
import numpy as np

# 導入配置
from local_model_config import YOLOV8_OCR_CONFIG
from local_data.model_manager import (
    verify_model_available, 
    get_cached_yolov8_model, 
    get_model_status
)

# 🛡️ 導入安全檢查模塊
from db.file_security import verify_magic_number

# 設置日誌
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "local_data", "app_local.db")

def get_all_templates():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, content FROM templates")
        rows = cur.fetchall()
        # 轉成字典格式回傳給前端 { "模板名稱": "Prompt內容" }
        return {row[0]: row[1] for row in rows}
    except sqlite3.Error as e:
        print(f"❌ 讀取模板失敗: {e}")
        return {}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def create_template(name, content, description=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        sql = "INSERT INTO templates (name, content, description) VALUES (?, ?, ?)"
        cur.execute(sql, (name, content, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"❌ 模板建立失敗：名稱 '{name}' 已存在。")
        return False
    except sqlite3.Error as e:
        print(f"❌ 模板建立發生錯誤: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def update_template(name, content):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        sql = "UPDATE templates SET content = ? WHERE name = ?"
        cur.execute(sql, (content, name))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"❌ 模板更新失敗: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# =========================================================================
# 文件導入相關功能
# =========================================================================

def extract_text_from_pdf(pdf_file):
    """
    從 PDF 文件中提取文本
    
    參數:
        pdf_file: 上傳的 PDF 文件對象
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 🛡️ 讀取檔案字節進行 Magic Number 驗證
        current_pos = pdf_file.tell() if hasattr(pdf_file, 'tell') else 0
        pdf_file.seek(0)
        file_bytes = pdf_file.read(512)  # 讀取前 512 字節進行檢查
        pdf_file.seek(0)  # 重置指針
        
        # 🛡️ 驗證 Magic Number
        valid_magic, magic_error = verify_magic_number(file_bytes, 'pdf')
        if not valid_magic:
            logger.warning(f"❌ PDF Magic Number 驗證失敗：{magic_error}")
            return None, f"❌ PDF 格式驗證失敗：{magic_error}"
        
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            text += f"\n--- 第 {page_num + 1} 頁 ---\n"
            text += page.extract_text()
        return text.strip(), None
    except Exception as e:
        return None, f"PDF 提取失敗: {str(e)}"


def extract_text_from_docx(docx_file):
    """
    從 Word 文檔中提取文本
    
    參數:
        docx_file: 上傳的 DOCX 文件對象
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 🛡️ 讀取檔案字節進行 Magic Number 驗證
        docx_file.seek(0)
        file_bytes = docx_file.read(512)  # DOCX 是 ZIP 格式
        docx_file.seek(0)  # 重置指針
        
        # 🛡️ 驗證 Magic Number（DOCX 是 ZIP 格式，特徵碼為 PK）
        valid_magic, magic_error = verify_magic_number(file_bytes, 'docx')
        if not valid_magic:
            logger.warning(f"❌ DOCX Magic Number 驗證失敗：{magic_error}")
            return None, f"❌ DOCX 格式驗證失敗：{magic_error}"
        
        doc = Document(docx_file)
        text = ""
        
        # 提取段落文本
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
        
        # 提取表格內容（如果有）
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text for cell in row.cells])
                if row_text.strip():
                    text += row_text + "\n"
        
        return text.strip(), None
    except Exception as e:
        return None, f"DOCX 提取失敗: {str(e)}"


def extract_text_from_txt(txt_file):
    """
    從文本文件中提取內容
    
    參數:
        txt_file: 上傳的文本文件對象
    
    返回:
        文件內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 🛡️ 讀取檔案字節進行 Magic Number 驗證
        content_bytes = txt_file.getvalue()
        
        # 🛡️ 驗證 Magic Number（TXT 無特定特徵碼，進行基本格式檢查）
        valid_magic, magic_error = verify_magic_number(content_bytes, 'txt')
        if not valid_magic:
            logger.warning(f"❌ TXT Magic Number 驗證失敗：{magic_error}")
            return None, f"❌ 文本格式驗證失敗：{magic_error}"
        
        content = content_bytes.decode('utf-8')
        return content.strip(), None
    except Exception as e:
        return None, f"TXT 提取失敗: {str(e)}"


def extract_text_from_image(image_file, use_yolov8=False):
    """
    從圖片文件中提取文本
    
    參數:
        image_file: 上傳的圖片文件對象 (JPG 或 PNG)
        use_yolov8: 是否使用 YOLOv8 + PaddleOCR 進行識別 (默認 False 使用 EasyOCR)
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 🛡️ 讀取檔案字節進行 Magic Number 驗證
        image_file.seek(0)
        file_bytes = image_file.read(512)
        image_file.seek(0)  # 重置指針
        
        # 🛡️ 直接驗證為 'image' 類型（會自動嘗試 PNG 或 JPG）
        valid_magic, magic_error = verify_magic_number(file_bytes, 'image')
        if not valid_magic:
            logger.warning(f"❌ 圖片 Magic Number 驗證失敗：{magic_error}")
            return None, f"❌ 圖片格式驗證失敗：{magic_error}"
        
        # 如果選擇使用 YOLOv8，則調用 YOLOv8 版本
        if use_yolov8:
            return extract_text_from_image_yolov8(image_file)
        
        # 否則使用 EasyOCR (現有邏輯)
        return extract_text_from_image_easyocr(image_file)
        
    except Exception as e:
        return None, f"圖片 OCR 提取失敗: {str(e)}"


def extract_text_from_image_easyocr(image_file):
    """
    使用 EasyOCR 從圖片文件中提取文本（原有邏輯）
    
    參數:
        image_file: 上傳的圖片文件對象 (JPG 或 PNG)
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 延遲導入 easyocr，只在需要時才導入
        import easyocr
        import numpy as np
        
        # 讀取上傳的圖片文件
        image_data = image_file.getvalue()
        image = Image.open(io.BytesIO(image_data))
        
        # 將 PIL Image 轉換為 numpy array（easyocr 接受的格式）
        image_array = np.array(image)
        
        # 初始化 EasyOCR 讀取器（支持繁體中文和英文）
        logger.info("初始化 EasyOCR 讀取器...")
        reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
        
        # 進行 OCR 識別 - 傳遞 numpy array 而非 PIL Image
        logger.info("進行 EasyOCR 文字識別...")
        results = reader.readtext(image_array)
        
        # 提取識別的文本
        text = "\n".join([result[1] for result in results])
        
        return text.strip() if text.strip() else "(未能識別出文字)", None
    except Exception as e:
        error_msg = f"EasyOCR 提取失敗: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def extract_text_from_image_yolov8(image_file):
    """
    使用 YOLOv8 + PaddleOCR 從圖片文件中提取文本
    
    參數:
        image_file: 上傳的圖片文件對象 (JPG 或 PNG)
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        import numpy as np
        from paddleocr import PaddleOCR
        
        logger.info("🚀 開始使用 YOLOv8 + PaddleOCR 進行文字識別...")
        
        # 檢查 YOLOv8 模型是否可用
        if not verify_model_available():
            logger.warning("⚠️ YOLOv8 模型不可用，自動降級回 EasyOCR")
            return extract_text_from_image_easyocr(image_file)
        
        # 讀取上傳的圖片文件
        image_data = image_file.getvalue()
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)
        
        logger.info("✓ 圖片已加載")
        
        # 初始化 PaddleOCR（支持中文和英文）
        # use_angle_cls=True 表示進行方向分類（提高識別率）
        logger.info("初始化 PaddleOCR...")
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',  # 中文
            enable_mkldnn=True,  # 啟用 MKL-DNN 加速
            device='cpu'  # 使用 CPU
        )
        
        logger.info("進行 PaddleOCR 文字識別...")
        
        
        # 1. 將圖片轉為標準 RGB (去除透明通道避免報錯)
        # 2. 將 PIL 圖片轉換為 PaddleOCR 看得懂的 numpy 陣列
        img_array = np.array(image.convert('RGB'))

        # 3. 把轉換後的陣列丟給 ocr
        result = ocr.ocr(img_array)
        
        # 提取識別的文本
        text_lines = []
        for line in result:
            if line:
                for word_info in line:
                    text = word_info[1][0]
                    confidence = word_info[1][1]
                    
                    # 只保留高信度的識別結果
                    if confidence > YOLOV8_OCR_CONFIG.get("confidence_threshold", 0.5):
                        text_lines.append(text)
                        logger.debug(f"  識別: {text} (置信度: {confidence:.2%})")
        
        final_text = "\n".join(text_lines)
        logger.info(f"✓ YOLOv8 + PaddleOCR 識別完成，識別 {len(text_lines)} 個文本塊")
        
        return final_text.strip() if final_text.strip() else "(未能識別出文字)", None
        
    except Exception as e:
        error_msg = f"YOLOv8 + PaddleOCR 提取失敗: {str(e)}"
        logger.error(error_msg)
        logger.warning("自動降級回 EasyOCR...")
        
        # 失敗時自動降級回 EasyOCR
        try:
            return extract_text_from_image_easyocr(image_file)
        except Exception as e2:
            logger.error(f"EasyOCR 也失敗了: {str(e2)}")
            return None, error_msg


def parse_uploaded_template(uploaded_file, file_type, use_yolov8=False):
    """
    根據檔案類型解析上傳的模板文件
    
    參數:
        uploaded_file: 上傳的文件對象
        file_type: 檔案類型 ('pdf', 'docx', 'txt', 'image')
        use_yolov8: 對圖像文件是否使用 YOLOv8 + PaddleOCR 識別（默認 False）
    
    返回:
        (提取的文本內容, 錯誤信息) 的元組
    """
    if file_type == 'pdf':
        return extract_text_from_pdf(uploaded_file)
    elif file_type == 'docx':
        return extract_text_from_docx(uploaded_file)
    elif file_type == 'txt':
        return extract_text_from_txt(uploaded_file)
    elif file_type == 'image':
        return extract_text_from_image(uploaded_file, use_yolov8=use_yolov8)
    else:
        return None, f"不支援的檔案類型: {file_type}"


