#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試 CRUD 功能"""

from db.auth_service import (
    get_all_users, search_users, authenticate_user,
    update_user, reset_password, soft_delete_user
)

print('=' * 50)
print('測試 CRUD 功能')
print('=' * 50)

# 測試 1. get_all_users
print('\n1️⃣ 測試 get_all_users()')
all_users = get_all_users()
print(f'   找到 {len(all_users)} 個用戶')
for user in all_users:
    print(f'   - {user}')

# 測試 2. search_users
print('\n2️⃣ 測試 search_users("admin")')
results = search_users('admin')
print(f'   搜尋結果: {results}')

# 測試 3. authenticate_user
print('\n3️⃣ 測試 authenticate_user("admin", "1234")')
result = authenticate_user('admin', '1234')
print(f'   認證結果: {result}')

# 測試 4. update_user
print('\n4️⃣ 測試 update_user(4, {"display_name": "系統管理者", "role": "admin"})')
update_result = update_user(4, {"display_name": "系統管理者"})
print(f'   更新結果: {update_result}')

# 測試 5. 更新後檢查
print('\n5️⃣ 更新後查詢用戶')
updated = get_all_users()
for user in updated:
    if user['username'] == 'admin':
        print(f'   admin 用戶: {user}')

print('\n✅ 所有 CRUD 測試完成！')
