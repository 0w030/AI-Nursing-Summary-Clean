"""
PostgreSQL 連接診斷腳本
用於測試 Railway 或其他 PostgreSQL 雲端資料庫連接
"""

import psycopg2
from services.schema_discovery_service import SchemaDiscoveryService

def test_postgresql_connection(host, port, database, username, password):
    """測試 PostgreSQL 連接"""
    
    print("\n" + "="*60)
    print("🧪 PostgreSQL 連接診斷")
    print("="*60 + "\n")
    
    # 連接配置
    config = {
        'host': host,
        'port': port,
        'database': database,
        'username': username,
        'password': password
    }
    
    print("📌 連接配置")
    print("-" * 60)
    print(f"主機: {config['host']}")
    print(f"埠口: {config['port']}")
    print(f"資料庫: {config['database']}")
    print(f"用戶: {config['username']}")
    print(f"密碼: {'*' * len(config['password'])}")
    
    # 步驟 1：直接測試 SSL 連接
    print("\n📌 步驟 1：測試 SSL 連接")
    print("-" * 60)
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['username'],
            password=config['password'],
            sslmode='require'
        )
        print("✅ SSL 連接成功！")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n📊 PostgreSQL 版本：\n{version}")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ SSL 連接失敗")
        print(f"錯誤: {str(e)}\n")
        
        # 步驟 2：嘗試非 SSL 連接
        print("\n📌 步驟 2：嘗試非 SSL 連接")
        print("-" * 60)
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['username'],
                password=config['password']
            )
            print("✅ 非 SSL 連接成功！")
            print("⚠️  警告：該資料庫不需要 SSL（不太可能是 Railway）")
            
            conn.close()
            return True
            
        except psycopg2.OperationalError as e2:
            print(f"❌ 非 SSL 連接也失敗")
            print(f"錯誤: {str(e2)}\n")
            
            print("\n📌 可能的問題：")
            print("-" * 60)
            print("1. ❌ 連接配置錯誤")
            print("   - 檢查主機名是否正確")
            print("   - 檢查端口是否正確")
            print("   - 檢查資料庫名稱是否正確")
            print("   - 檢查用戶名是否正確")
            print("   - 檢查密碼是否正確（特別注意特殊字符）")
            
            print("\n2. ⚠️  防火牆/網絡問題")
            print("   - 檢查防火牆是否阻止了連接")
            print("   - 嘗試 ping 該主機")
            print("   - 檢查網絡連接")
            
            print("\n3. 📌 Railway 特定問題")
            print("   - Railway PostgreSQL 使用了特殊的代理地址")
            print("   - 確保使用的是正確的 Connection String")
            print("   - 檢查 Railway 控制台中的連接信息")
            
            return False
    
    except Exception as e:
        print(f"❌ 發生未預期的錯誤：{str(e)}")
        return False


def test_postgresql_schema_discovery(host, port, database, username, password):
    """測試 PostgreSQL Schema 發現"""
    
    print("\n📌 測試 Schema 發現")
    print("-" * 60)
    
    config = {
        'db_type': 'postgresql',
        'host': host,
        'port': port,
        'database': database,
        'username': username,
        'password': password
    }
    
    try:
        discovery = SchemaDiscoveryService(config)
        
        if not discovery.connect():
            print("❌ 連接失敗")
            return False
        
        print("✅ 已連接")
        
        # 發現表格
        print("\n🔍 發現表格中...")
        tables = discovery.discover_tables()
        
        print(f"✅ 發現 {len(tables)} 個表格")
        
        if tables:
            print("\n📋 表格列表（前 10 個）：")
            for i, table in enumerate(tables[:10], 1):
                print(f"   {i}. {table.name}")
            
            if len(tables) > 10:
                print(f"   ... 以及 {len(tables) - 10} 個其他表格")
        
        discovery.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Schema 發現失敗：{str(e)}")
        return False


if __name__ == "__main__":
    # Railway PostgreSQL 連接信息（請根據您的實際信息修改）
    # 您可以從 Railway 控制台的 "Connect" 標籤中找到這些信息
    
    # 從截圖中提取的配置
    HOST = "shinkansen.proxy.rlwy.net"
    PORT = 25940
    DATABASE = "railway"
    USERNAME = "postgres"
    PASSWORD = input("請輸入 PostgreSQL 密碼: ")
    
    # 測試連接
    if test_postgresql_connection(HOST, PORT, DATABASE, USERNAME, PASSWORD):
        print("\n✅ 連接測試通過")
        
        # 測試 Schema 發現
        if test_postgresql_schema_discovery(HOST, PORT, DATABASE, USERNAME, PASSWORD):
            print("\n✅ Schema 發現測試通過")
        else:
            print("\n❌ Schema 發現失敗")
    else:
        print("\n❌ 連接測試失敗")
    
    print("\n" + "="*60)
