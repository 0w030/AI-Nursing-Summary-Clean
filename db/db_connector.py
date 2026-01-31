# /db/db_connector.py

# import psycopg2
# import streamlit as st

# def get_db_connection():
#     """
#     嘗試建立 PostgreSQL 資料庫連線。
#     如果成功，回傳連線物件；如果失敗，回傳 None 並印出錯誤。
#     """
#     try:
#         # 嘗試連線，改用 st.secrets
#         conn = psycopg2.connect(
#             host=st.secrets["database"]["host"],
#             port=st.secrets["database"]["port"],
#             database=st.secrets["database"]["name"],
#             user=st.secrets["database"]["user"],
#             password=st.secrets["database"]["password"]
#         )
#         return conn
#     except psycopg2.Error as e:
#         print(f"❌ 資料庫連線失敗: {e}")
#         return None
#     except Exception as e:
#         print(f"❌ 發生未預期的錯誤: {e}")
#         return None

# if __name__ == '__main__':
#     print("--- 正在測試 Railway 資料庫連線 ---")
    
#     # 呼叫連線函數
#     conn = get_db_connection()
    
#     if conn:
#         print("✅ 連線成功！ (Connection Successful)")
        
#         # 進一步測試：嘗試查詢資料庫版本，確保不只是連上，還能執行指令
#         try:
#             with conn.cursor() as cur:
#                 cur.execute("SELECT version();")
#                 db_version = cur.fetchone()
#                 print(f"ℹ️  資料庫版本: {db_version[0]}")
#         except Exception as e:
#             print(f"⚠️  連線成功但查詢失敗: {e}")
#         finally:
#             conn.close()
#             print("--- 連線測試結束，連線已關閉 ---")
#     else:
#         print("❌ 連線失敗。")
#         print("請檢查您的 Streamlit Secrets 設定")

import os
import psycopg2
from dotenv import load_dotenv

# 讀取 .env 檔案中的環境變數
load_dotenv()

def get_db_connection():
    """
    嘗試建立 PostgreSQL 資料庫連線。
    使用環境變數讀取設定，不依賴 streamlit。
    """
    try:
        # 從環境變數讀取設定
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except psycopg2.Error as e:
        print(f"❌ 資料庫連線失敗: {e}")
        return None
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        return None

if __name__ == '__main__':
    print("--- 正在測試 Railway 資料庫連線 (Local Test) ---")
    
    conn = get_db_connection()
    
    if conn:
        print("✅ 連線成功！")
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                db_version = cur.fetchone()
                print(f"ℹ️  資料庫版本: {db_version[0]}")
        except Exception as e:
            print(f"⚠️  連線成功但查詢失敗: {e}")
        finally:
            conn.close()
            print("--- 連線測試結束，連線已關閉 ---")
    else:
        print("❌ 連線失敗。請檢查 .env 檔案設定。")
