# # db/auth_service.py

# import psycopg2
# from db.db_connector import get_db_connection

# def authenticate_user(input_username, input_password):
#     """
#     連線至 users 資料表驗證帳號密碼。
#     驗證成功回傳使用者的 role (如 'admin', 'manager', 'user')，失敗則回傳 None。
#     """
#     conn = get_db_connection()
#     if not conn:
#         print("無法建立連線，無法進行登入驗證。")
#         return None

#     try:
#         with conn.cursor() as cur:
#             # 去 users 表格找這個帳號
#             sql = "SELECT password, role FROM users WHERE username = %s"
#             cur.execute(sql, (input_username,))
#             result = cur.fetchone()

#             if result:
#                 db_password = result[0]
#                 db_role = result[1]
                
#                 # 比對密碼 (目前為明文比對，未來可升級為 Hash 比對)
#                 if input_password == db_password:
#                     return db_role  # 密碼正確，回傳他的權限角色
                    
#     except psycopg2.Error as e:
#         print(f"❌ 登入查詢失敗: {e}")
#     finally:
#         if conn:
#             conn.close()
        
#     return None # 帳號不存在或密碼錯誤

#以下為SQLite版本

# db/auth_service.py
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "local_data", "app_local.db")

def authenticate_user(input_username, input_password):
    """
    連線至本地 SQLite 驗證帳號密碼。
    """
    try:
        # 連線到剛剛建好的本地資料庫
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # SQLite 的變數綁定是使用問號 (?)
        sql = "SELECT password, role FROM users WHERE username = ?"
        cur.execute(sql, (input_username,))
        result = cur.fetchone()

        if result:
            db_password = result[0]
            db_role = result[1]
            
            if input_password == db_password:
                return db_role  # 密碼正確
                
    except sqlite3.Error as e:
        print(f"❌ 登入查詢失敗: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            
    return None # 帳號不存在或密碼錯誤