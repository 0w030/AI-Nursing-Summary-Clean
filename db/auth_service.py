# db/auth_service.py
import sqlite3
import os
import bcrypt
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "local_data", "app_local.db")

def hash_password(password: str) -> str:
    """
    使用 bcrypt 對密碼進行雜湊處理。
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(input_password: str, hashed_password: str) -> bool:
    """
    驗證輸入的密碼是否與雜湊密碼匹配。
    """
    try:
        return bcrypt.checkpw(input_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"❌ 密碼驗證失敗: {e}")
        return False

def authenticate_user(input_username: str, input_password: str):
    """
    連線至本地 SQLite 驗證帳號密碼。
    返回使用者的角色 (admin, manager, user) 或 None。
    注意：已刪除的帳號無法登入。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "SELECT password, role, is_deleted FROM users WHERE username = ? AND is_deleted = 0"
        cur.execute(sql, (input_username,))
        result = cur.fetchone()

        if result:
            db_password = result[0]
            db_role = result[1]
            
            if verify_password(input_password, db_password):
                return db_role  # 密碼正確，返回角色
                
    except sqlite3.Error as e:
        print(f"❌ 登入查詢失敗: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            
    return None  # 帳號不存在或密碼錯誤

def user_exists(username: str) -> bool:
    """
    檢查使用者是否已存在於資料庫。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "SELECT id FROM users WHERE username = ?"
        cur.execute(sql, (username,))
        result = cur.fetchone()
        
        return result is not None
    except sqlite3.Error as e:
        print(f"❌ 檢查使用者失敗: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_user_by_username(username: str):
    """
    根據用戶名獲取用戶信息。
    返回字典或 None。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "SELECT id, username, role FROM users WHERE username = ?"
        cur.execute(sql, (username,))
        result = cur.fetchone()
        
        if result:
            return {
                'id': result[0],
                'username': result[1],
                'role': result[2]
            }
        return None
    except sqlite3.Error as e:
        print(f"❌ 獲取使用者失敗: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def create_user(username: str, password: str, role: str = 'user') -> dict:
    """
    創建新的使用者帳號。
    
    參數:
        username: 帳號名稱（Email 或 Username）
        password: 明文密碼（將被 bcrypt 雜湊）
        role: 用戶角色 (admin, manager, user)
    
    返回:
        {
            'success': bool,
            'message': 錯誤信息或成功信息
        }
    """
    # 驗證密碼長度
    if len(password) < 6:
        return {
            'success': False,
            'message': '密碼長度至少為 6 個字符'
        }
    
    # 驗證帳號是否已存在
    if user_exists(username):
        return {
            'success': False,
            'message': f'帳號 "{username}" 已存在，請使用其他帳號'
        }
    
    # 驗證角色是否有效
    if role not in ['admin', 'manager', 'user']:
        return {
            'success': False,
            'message': f'無效的角色: {role}。必須是 admin, manager 或 user'
        }
    
    # 驗證 Email（如果輸入格式看起來像 Email）
    if '@' in username:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, username):
            return {
                'success': False,
                'message': 'Email 格式不正確'
            }
    
    try:
        # 對密碼進行雜湊處理
        hashed_password = hash_password(password)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "INSERT INTO users (username, password, role) VALUES (?, ?, ?)"
        cur.execute(sql, (username, hashed_password, role))
        
        conn.commit()
        
        return {
            'success': True,
            'message': f'已成功建立帳號 "{username}"（角色: {role}）'
        }
    except sqlite3.Error as e:
        print(f"❌ 建立帳號失敗: {e}")
        return {
            'success': False,
            'message': f'建立帳號失敗: {str(e)}'
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# ==========================================
# CRUD 操作：Read（讀取）
# ==========================================

def get_all_users(include_deleted: bool = False) -> list:
    """
    獲取所有用戶列表。
    
    參數:
        include_deleted: 是否包括已刪除的用戶
    
    返回:
        用戶列表（字典形式）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        if include_deleted:
            sql = "SELECT id, username, role, display_name, is_deleted, created_at FROM users ORDER BY created_at DESC"
        else:
            sql = "SELECT id, username, role, display_name, is_deleted, created_at FROM users WHERE is_deleted = 0 ORDER BY created_at DESC"
        
        cur.execute(sql)
        results = cur.fetchall()
        
        users = []
        for row in results:
            users.append({
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'display_name': row[3] or row[1],  # 如果沒有 display_name，使用 username
                'is_deleted': row[4],
                'created_at': row[5]
            })
        
        return users
    except sqlite3.Error as e:
        print(f"❌ 獲取用戶列表失敗: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def search_users(keyword: str = "", role_filter: str = "") -> list:
    """
    搜尋和篩選用戶。
    
    參數:
        keyword: 搜尋關鍵字（帳號或姓名）
        role_filter: 角色篩選（'admin', 'manager', 'user'，或空字符串表示全部）
    
    返回:
        匹配的用戶列表
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "SELECT id, username, role, display_name, is_deleted, created_at FROM users WHERE is_deleted = 0"
        params = []
        
        # 添加關鍵字篩選
        if keyword:
            sql += " AND (username LIKE ? OR display_name LIKE ?)"
            search_keyword = f"%{keyword}%"
            params.extend([search_keyword, search_keyword])
        
        # 添加角色篩選
        if role_filter:
            sql += " AND role = ?"
            params.append(role_filter)
        
        sql += " ORDER BY created_at DESC"
        
        cur.execute(sql, params)
        results = cur.fetchall()
        
        users = []
        for row in results:
            users.append({
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'display_name': row[3] or row[1],
                'is_deleted': row[4],
                'created_at': row[5]
            })
        
        return users
    except sqlite3.Error as e:
        print(f"❌ 搜尋用戶失敗: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_user_count(include_deleted: bool = False) -> int:
    """
    獲取用戶總數（用於分頁）。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        if include_deleted:
            sql = "SELECT COUNT(*) FROM users"
        else:
            sql = "SELECT COUNT(*) FROM users WHERE is_deleted = 0"
        
        cur.execute(sql)
        count = cur.fetchone()[0]
        return count
    except sqlite3.Error as e:
        print(f"❌ 獲取用戶計數失敗: {e}")
        return 0
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# ==========================================
# CRUD 操作：Update（更新）
# ==========================================

def update_user(user_id: int, updates: dict) -> dict:
    """
    更新用戶信息。
    
    參數:
        user_id: 用戶 ID
        updates: 要更新的字段字典
                 可包含：'display_name', 'role'
                 不允許修改：'username'（帳號）
    
    返回:
        {'success': bool, 'message': str}
    """
    # 不允許修改的字段
    forbidden_fields = ['id', 'username', 'password', 'is_deleted']
    
    # 檢查更新字段的合法性
    for field in updates.keys():
        if field in forbidden_fields:
            return {
                'success': False,
                'message': f'無法修改欄位：{field}'
            }
    
    # 驗證角色（如果有的話）
    if 'role' in updates:
        if updates['role'] not in ['admin', 'manager', 'user']:
            return {
                'success': False,
                'message': f'無效的角色: {updates["role"]}'
            }
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 動態構建 UPDATE 語句
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        params.append(user_id)  # WHERE 子句的參數
        
        sql = f"UPDATE users SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        cur.execute(sql, params)
        conn.commit()
        
        if cur.rowcount == 0:
            return {
                'success': False,
                'message': f'找不到 ID 為 {user_id} 的用戶'
            }
        
        return {
            'success': True,
            'message': f'已成功更新用戶信息'
        }
    except sqlite3.Error as e:
        print(f"❌ 更新用戶失敗: {e}")
        return {
            'success': False,
            'message': f'更新失敗: {str(e)}'
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def reset_password(user_id: int, new_password: str) -> dict:
    """
    重設用戶密碼。
    
    參數:
        user_id: 用戶 ID
        new_password: 新密碼
    
    返回:
        {'success': bool, 'message': str}
    """
    # 驗證密碼長度
    if len(new_password) < 6:
        return {
            'success': False,
            'message': '新密碼長度至少為 6 個字符'
        }
    
    try:
        # 密碼雜湊
        hashed_password = hash_password(new_password)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "UPDATE users SET password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(sql, (hashed_password, user_id))
        conn.commit()
        
        if cur.rowcount == 0:
            return {
                'success': False,
                'message': f'找不到 ID 為 {user_id} 的用戶'
            }
        
        return {
            'success': True,
            'message': '密碼已重設'
        }
    except sqlite3.Error as e:
        print(f"❌ 重設密碼失敗: {e}")
        return {
            'success': False,
            'message': f'重設失敗: {str(e)}'
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# ==========================================
# CRUD 操作：Delete（刪除）
# ==========================================

def soft_delete_user(user_id: int) -> dict:
    """
    軟刪除用戶（標記為已刪除，不直接刪除數據）。
    已刪除的用戶無法登入。
    
    參數:
        user_id: 用戶 ID
    
    返回:
        {'success': bool, 'message': str}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 不允許刪除 admin 账户
        cur.execute("SELECT role, username FROM users WHERE id = ?", (user_id,))
        result = cur.fetchone()
        
        if not result:
            return {
                'success': False,
                'message': f'找不到 ID 為 {user_id} 的用戶'
            }
        
        role, username = result
        if role == 'admin':
            return {
                'success': False,
                'message': '無法刪除管理員帳號'
            }
        
        # 執行軟刪除
        sql = "UPDATE users SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(sql, (user_id,))
        conn.commit()
        
        return {
            'success': True,
            'message': f'已刪除用戶 "{username}"'
        }
    except sqlite3.Error as e:
        print(f"❌ 刪除用戶失敗: {e}")
        return {
            'success': False,
            'message': f'刪除失敗: {str(e)}'
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def restore_user(user_id: int) -> dict:
    """
    恢復已刪除的用戶。
    
    參數:
        user_id: 用戶 ID
    
    返回:
        {'success': bool, 'message': str}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        sql = "UPDATE users SET is_deleted = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(sql, (user_id,))
        conn.commit()
        
        if cur.rowcount == 0:
            return {
                'success': False,
                'message': f'找不到 ID 為 {user_id} 的用戶'
            }
        
        return {
            'success': True,
            'message': '用戶已恢復'
        }
    except sqlite3.Error as e:
        print(f"❌ 恢復用戶失敗: {e}")
        return {
            'success': False,
            'message': f'恢復失敗: {str(e)}'
        }
    finally:
        if 'conn' in locals() and conn:
            conn.close()
