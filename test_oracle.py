# test_oracle.py
import os
from dotenv import load_dotenv
import oracledb

# --- 新增這行：啟動 Thick mode (請把路徑換成你剛剛解壓縮的實際路徑) ---
try:
    oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30")
except Exception as e:
    print(f"初始化 Oracle Client 失敗: {e}")

# 載入 .env 變數
load_dotenv()

def test_connection():
    try:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        service_name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        print(f"嘗試連線至 Oracle 主機: {host}:{port} / 服務名稱: {service_name}")
        
        # 建立 DSN
        dsn = oracledb.makedsn(host, port, service_name=service_name)
        
        # 建立連線
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        print("✅ Python 成功連線到醫院 Oracle 資料庫！")

        # 執行一個超簡單的查詢，看看資料庫裡有哪些資料表 (Tables)
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM user_tables WHERE ROWNUM <= 5")
            rows = cur.fetchall()
            print("\n📁 你的資料庫裡有這些 Table (前 5 筆)：")
            for row in rows:
                print(f" - {row[0]}")
                
        conn.close()

    except Exception as e:
        print(f"❌ 連線失敗，錯誤訊息：{e}")

if __name__ == "__main__":
    test_connection()