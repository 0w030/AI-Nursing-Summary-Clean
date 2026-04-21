#!/usr/bin/env python3
"""
Railway PostgreSQL 连接诊断工具
直接测试 PostgreSQL 连接，显示详细错误信息
"""

import psycopg2
from psycopg2 import sql
import sys
import socket
import time

print("=" * 80)
print("🔧 Railway PostgreSQL 连接诊断工具")
print("=" * 80)

# 用户配置
HOST = "shinkansen.proxy.rlwy.net"
PORT = 25940
DATABASE = "railway"
USER = "postgres"
PASSWORD = "pQntRrGNyqiuxLSwjFofptVsOZlakhba"

print(f"\n📋 连接配置:")
print(f"   主机: {HOST}")
print(f"   端口: {PORT}")
print(f"   数据库: {DATABASE}")
print(f"   用户名: {USER}")
print(f"   密码: {'*' * len(PASSWORD)}")

# 步骤 1: 网络连接测试
print(f"\n🌐 步骤 1: 测试网络连接到 {HOST}:{PORT}...")
try:
    sock = socket.create_connection((HOST, PORT), timeout=10)
    print(f"   ✅ 网络连接成功")
    sock.close()
except socket.timeout:
    print(f"   ❌ 网络连接超时（10秒）")
    print(f"      可能原因: 防火墙阻止，或服务器离线")
    sys.exit(1)
except socket.error as e:
    print(f"   ❌ 网络连接失败: {str(e)}")
    sys.exit(1)

# 步骤 2: PostgreSQL SSL 连接测试
print(f"\n🔐 步骤 2: 测试 PostgreSQL SSL 连接...")
try:
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        sslmode='require',
        connect_timeout=10
    )
    print(f"   ✅ SSL 连接成功!")
    
    # 获取连接信息
    print(f"\n📊 连接信息:")
    cursor = conn.cursor()
    
    # PostgreSQL 版本
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"   PostgreSQL 版本: {version.split(',')[0]}")
    
    # 当前用户
    cursor.execute("SELECT current_user;")
    current_user = cursor.fetchone()[0]
    print(f"   当前用户: {current_user}")
    
    # 数据库名
    cursor.execute("SELECT current_database();")
    current_db = cursor.fetchone()[0]
    print(f"   当前数据库: {current_db}")
    
    # 所有表格
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print(f"\n📁 发现表格 ({len(tables)} 个):")
    for table in tables[:10]:
        print(f"      - {table[0]}")
    if len(tables) > 10:
        print(f"      ... 以及 {len(tables) - 10} 个其他表格")
    
    cursor.close()
    conn.close()
    print(f"\n✅ 所有测试通过!")
    
except psycopg2.OperationalError as e:
    print(f"   ❌ PostgreSQL SSL 连接失败")
    error_msg = str(e)
    print(f"   错误信息: {error_msg}")
    
    # 分析常见错误
    if "password authentication failed" in error_msg:
        print(f"\n   💡 提示: 密码错误或用户不存在")
        print(f"      请检查:")
        print(f"      1. Railway 控制台确认密码")
        print(f"      2. 密码中是否有特殊字符")
        print(f"      3. 复制时是否有多余空格")
    elif "connection refused" in error_msg or "connect" in error_msg.lower():
        print(f"\n   💡 提示: 无法连接到服务器")
        print(f"      请检查:")
        print(f"      1. Railway 数据库是否在线")
        print(f"      2. 主机地址是否正确")
        print(f"      3. 端口是否正确")
        print(f"      4. 防火墙设置")
    elif "SSL" in error_msg or "ssl" in error_msg:
        print(f"\n   💡 提示: SSL 连接问题")
        print(f"      现在尝试非 SSL 连接...")
        
        try:
            conn = psycopg2.connect(
                host=HOST,
                port=PORT,
                database=DATABASE,
                user=USER,
                password=PASSWORD,
                sslmode='disable',
                connect_timeout=10
            )
            print(f"      ✅ 非 SSL 连接成功!")
            print(f"      → 系统应该自动回退到非 SSL")
            conn.close()
        except Exception as e2:
            print(f"      ❌ 非 SSL 连接也失败: {str(e2)}")
    
    sys.exit(1)

except psycopg2.Error as e:
    print(f"   ❌ PostgreSQL 错误: {str(e)}")
    sys.exit(1)

except Exception as e:
    print(f"   ❌ 未知错误: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
