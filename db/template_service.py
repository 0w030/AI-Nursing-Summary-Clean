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