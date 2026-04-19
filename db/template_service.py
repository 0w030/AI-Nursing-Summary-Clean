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
import easyocr
from PIL import Image
import io

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
        content = txt_file.getvalue().decode('utf-8')
        return content.strip(), None
    except Exception as e:
        return None, f"TXT 提取失敗: {str(e)}"


def extract_text_from_image(image_file):
    """
    從圖片文件中提取文本（使用 EasyOCR 識別）
    
    參數:
        image_file: 上傳的圖片文件對象 (JPG 或 PNG)
    
    返回:
        提取的文本內容，失敗時返回 None 和錯誤信息
    """
    try:
        # 讀取上傳的圖片文件
        image_data = image_file.getvalue()
        image = Image.open(io.BytesIO(image_data))
        
        # 初始化 EasyOCR 讀取器（支持繁體中文和英文）
        reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
        
        # 進行 OCR 識別
        results = reader.readtext(image)
        
        # 提取識別的文本
        text = "\n".join([result[1] for result in results])
        
        return text.strip() if text.strip() else "(未能識別出文字)", None
    except Exception as e:
        return None, f"圖片 OCR 提取失敗: {str(e)}"





def parse_uploaded_template(uploaded_file, file_type):
    """
    根據檔案類型解析上傳的模板文件
    
    參數:
        uploaded_file: 上傳的文件對象
        file_type: 檔案類型 ('pdf', 'docx', 'txt', 'image')
    
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
        return extract_text_from_image(uploaded_file)
    else:
        return None, f"不支援的檔案類型: {file_type}"


