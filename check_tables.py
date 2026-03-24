import os
from dotenv import load_dotenv
import oracledb

# 載入厚客戶端 (請確認路徑正確)
oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30")
load_dotenv()

def check_target_tables():
    try:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        service_name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        dsn = oracledb.makedsn(host, port, service_name=service_name)
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        cursor = conn.cursor()

        # 我們只鎖定這三個目標表 (注意：Oracle 查詢條件通常區分大小寫，需大寫)
        target_tables = ['RECORD', 'RECORD_DETAIL', 'RECORD_VERSION']

        print("🔍 開始精準掃描目標資料表...\n")

        for table_name in target_tables:
            print(f"🏥 資料表：【{table_name}】")
            
            # 查詢欄位名稱、資料型態與中文備註
            sql = """
            SELECT c.column_name, c.data_type, cc.comments 
            FROM user_tab_columns c
            LEFT JOIN user_col_comments cc 
              ON c.table_name = cc.table_name AND c.column_name = cc.column_name
            WHERE c.table_name = :1
            ORDER BY c.column_id
            """
            cursor.execute(sql, [table_name])
            columns = cursor.fetchall()

            if not columns:
                print("   (⚠️ 找不到這個表，或者權限不足/名稱不是全大寫)")
            else:
                for col in columns:
                    col_name = col[0]
                    col_type = col[1]
                    col_comment = col[2] if col[2] else "無註解"
                    print(f"   ├─ {col_name} ({col_type}) 📝 {col_comment}")
            print("-" * 50)

        conn.close()

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")

if __name__ == "__main__":
    check_target_tables()