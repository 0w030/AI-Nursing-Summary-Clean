# init_sqlite.py
import sqlite3
import os
import bcrypt

def hash_password(password: str) -> str:
    """使用 bcrypt 對密碼進行雜湊處理。"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def migrate_add_is_deleted_column():
    """數據庫遷移：添加必要的欄位（軟刪除、時間戳等）"""
    db_path = os.path.join(os.path.dirname(__file__), "local_data", "app_local.db")
    if not os.path.exists(db_path):
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 檢查欄位是否已存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_deleted' not in columns:
            print("🔧 正在升級數據庫：添加 is_deleted 欄位...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
            conn.commit()
            print("✅ is_deleted 欄位已添加")
        
        if 'display_name' not in columns:
            print("🔧 正在升級數據庫：添加 display_name 欄位...")
            cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            conn.commit()
            print("✅ display_name 欄位已添加")
        
        if 'created_at' not in columns:
            print("🔧 正在升級數據庫：添加 created_at 欄位...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT NULL")
            cursor.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")
            conn.commit()
            print("✅ created_at 欄位已添加")
        
        if 'updated_at' not in columns:
            print("🔧 正在升級數據庫：添加 updated_at 欄位...")
            cursor.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT NULL")
            cursor.execute("UPDATE users SET updated_at = datetime('now') WHERE updated_at IS NULL")
            conn.commit()
            print("✅ updated_at 欄位已添加")
            
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"⚠️  數據庫欄位操作: {e}")

def setup_local_database():
    # 建立一個 data 資料夾來放本地資料庫 (比較整齊)
    os.makedirs("local_data", exist_ok=True)
    db_path = "local_data/app_local.db"

    # 首先執行遷移以確保表結構最新
    migrate_add_is_deleted_column()

    # 連線 (如果檔案不存在，SQLite 會自動幫你建立一個新的！)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 建立 Users (帳號) 表 - 包含軟刪除欄位
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        display_name TEXT,
        is_deleted BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_deleted = 0")
    existing_count = cursor.fetchone()[0]
    
    if existing_count == 0:
        # 密碼都是 "1234"，使用 bcrypt 雜湊
        users_data = [
            ('admin', hash_password('1234'), 'admin', '系統管理員', 0),
            ('manager', hash_password('1234'), 'manager', '護理主任', 0),
            ('user', hash_password('1234'), 'user', '一般使用者', 0)
        ]
        # 注意：SQLite 的變數綁定符號是「問號 (?)」
        cursor.executemany(
            "INSERT INTO users (username, password, role, display_name, is_deleted) VALUES (?, ?, ?, ?, ?)", 
            users_data
        )
        print("✅ 已自動新增 3 組預設測試帳號（密碼已使用 bcrypt 雜湊）！")
        print("   - admin / 1234  (角色: admin)")
        print("   - manager / 1234 (角色: manager)")
        print("   - user / 1234    (角色: user)")

    # 儲存並關閉
    conn.commit()
    conn.close()
    
    print(f"🎉 本地 SQLite 資料庫建立完成！檔案位置：{db_path}")

if __name__ == "__main__":
    setup_local_database()