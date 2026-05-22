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
# load_dotenv()

# def get_db_connection():
#     """
#     嘗試建立 PostgreSQL 資料庫連線。
#     使用環境變數讀取設定，不依賴 streamlit。
#     """
#     try:
#         # 從環境變數讀取設定
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"),
#             port=os.getenv("DB_PORT"),
#             database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD")
#         )
#         return conn
#     except psycopg2.Error as e:
#         print(f"❌ 資料庫連線失敗: {e}")
#         return None
#     except Exception as e:
#         print(f"❌ 發生未預期的錯誤: {e}")
#         return None

import os
import oracledb
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# --- 在系統啟動時，一次性載入 Thick mode 翻譯機 ---
try:
    oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30\instantclient_19_30")
except Exception as e:
    # 這裡捕捉例外，防止 Streamlit 重整時重複載入報錯
    pass

def get_db_connection():
    try:
        # 從環境變數讀取設定
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        service_name = os.getenv("DB_NAME")  # ⚠️ 注意：在 Oracle 裡這代表 Service Name 或 SID
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        # 確保必要的環境變數存在，避免程式崩潰
        if not all([host, port, service_name, user, password]):
            print("❌ 環境變數缺失，請檢查 .env 檔案設定！")
            return None

        # 建立 Oracle 連線字串 (DSN)
        dsn = oracledb.makedsn(host, port, service_name=service_name)

        # 建立資料庫連線
        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        return conn

    except oracledb.Error as e:
        error_obj, = e.args
        print(f"❌ Oracle 資料庫連線失敗: {error_obj.message}")
        return None
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        return None

if __name__ == '__main__':
    print("--- 正在測試 醫院 Oracle 測試庫連線 (Local Test) ---")
    
    conn = get_db_connection()
    
    if conn:
        print("✅ 連線成功！")
        try:
            with conn.cursor() as cur:
                # 換成 Oracle 專用的查詢版本語法
                cur.execute("SELECT * FROM v$version WHERE ROWNUM = 1")
                db_version = cur.fetchone()
                print(f"ℹ️  資料庫版本: {db_version[0]}")
        except Exception as e:
            print(f"⚠️  連線成功但查詢失敗: {e}")
        finally:
            conn.close()
            print("--- 連線測試結束，連線已關閉 ---")
    else:
        print("❌ 連線失敗。請檢查 .env 檔案設定。")