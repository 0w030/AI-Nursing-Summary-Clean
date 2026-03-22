# init_sqlite.py
import sqlite3
import os

def setup_local_database():
    # 建立一個 data 資料夾來放本地資料庫 (比較整齊)
    os.makedirs("local_data", exist_ok=True)
    db_path = "local_data/app_local.db"

    # 連線 (如果檔案不存在，SQLite 會自動幫你建立一個新的！)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 建立 Users (帳號) 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')

    # 2. 建立 Templates (模板) 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS templates (
        name TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        description TEXT
    )
    ''')

    # 3. 塞入預設的三組測試帳號 (防呆檢查，避免重複塞入)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users_data = [
            ('admin', '1234', 'admin'),
            ('manager', '1234', 'manager'),
            ('user', '1234', 'user')
        ]
        # 注意：SQLite 的變數綁定符號是「問號 (?)」
        cursor.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", users_data)
        print("✅ 已自動新增 3 組預設測試帳號！")

    # 儲存並關閉
    conn.commit()
    conn.close()
    print(f"🎉 本地 SQLite 資料庫建立完成！檔案位置：{db_path}")

if __name__ == "__main__":
    setup_local_database()