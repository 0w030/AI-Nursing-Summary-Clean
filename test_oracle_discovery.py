"""
Oracle Schema 發現診斷腳本
用於測試 Oracle 連接和表格查詢
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from services.oracle_connection_helper import OracleConnectionHelper
from services.schema_discovery_service import SchemaDiscoveryService

# 加載環境變數
load_dotenv()

def test_oracle_discovery():
    """測試 Oracle Schema 發現"""
    
    print("\n" + "="*60)
    print("🧪 Oracle Schema 發現診斷")
    print("="*60 + "\n")
    
    # 步驟 1：讀取配置
    print("📌 步驟 1：讀取 Oracle 配置")
    print("-" * 60)
    
    oracle_config = OracleConnectionHelper.get_oracle_config_from_env()
    if not oracle_config:
        print("❌ 未找到 Oracle 配置")
        return False
    
    print(f"✅ 配置已加載")
    print(f"   - 主機: {oracle_config['host']}")
    print(f"   - 埠口: {oracle_config['port']}")
    print(f"   - 數據庫: {oracle_config['database']}")
    print(f"   - 用戶: {oracle_config['username']}")
    
    # 步驟 2：驗證連接
    print("\n📌 步驟 2：驗證 Oracle 連接")
    print("-" * 60)
    
    if not OracleConnectionHelper.verify_connection():
        print("❌ Oracle 連接失敗")
        return False
    
    print("✅ Oracle 連接成功")
    
    # 步驟 3：發現表格
    print("\n📌 步驟 3：發現 Oracle 表格")
    print("-" * 60)
    
    try:
        discovery_service = SchemaDiscoveryService(oracle_config)
        
        if not discovery_service.connect():
            print("❌ 無法連接到 Oracle 數據庫")
            return False
        
        print("✅ 已連接到 Oracle 數據庫")
        
        # 發現表格
        print("\n🔍 發現表格中...")
        tables = discovery_service.discover_tables()
        
        print(f"\n✅ 發現 {len(tables)} 個表格")
        
        if len(tables) == 0:
            print("\n⚠️  警告：沒有發現任何表格")
            print("   可能的原因：")
            print("   1. 用戶沒有表格")
            print("   2. 用戶沒有查詢 USER_TABLES 的權限")
            print("   3. 表格在其他 Schema 中")
        else:
            print("\n   發現的表格清單：")
            for i, table in enumerate(tables[:10], 1):  # 顯示前 10 個
                print(f"   {i}. {table.name} ({table.row_count} 行)")
            
            if len(tables) > 10:
                print(f"   ... 以及 {len(tables) - 10} 個其他表格")
        
        # 步驟 4：發現欄位
        if tables:
            print(f"\n📌 步驟 4：發現第一個表格的欄位")
            print("-" * 60)
            
            first_table = tables[0]
            print(f"\n🔍 發現表格 {first_table.name} 的欄位中...")
            
            columns = discovery_service.discover_columns(first_table.name)
            
            print(f"✅ 發現 {len(columns)} 個欄位")
            
            if columns:
                print("\n   欄位清單：")
                for col in columns[:5]:  # 顯示前 5 個
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    print(f"   - {col.name}: {col.data_type} ({nullable})")
                
                if len(columns) > 5:
                    print(f"   ... 以及 {len(columns) - 5} 個其他欄位")
        
        # 步驟 5：完整 Schema 發現
        if tables:
            print(f"\n📌 步驟 5：發現完整 Schema")
            print("-" * 60)
            
            print("\n🔍 發現完整 Schema 中（可能需要一些時間）...")
            schema = discovery_service.discover_full_schema()
            
            total_tables = len(schema['tables'])
            total_columns = sum(len(t['columns']) for t in schema['tables'].values())
            
            print(f"\n✅ 完整 Schema 發現完成")
            print(f"   - 表格數: {total_tables}")
            print(f"   - 欄位數: {total_columns}")
        
        discovery_service.disconnect()
        
        return True
        
    except Exception as e:
        print(f"❌ 診斷過程中出錯：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def show_oracle_user_info():
    """顯示 Oracle 用戶信息"""
    print("\n📌 Oracle 用戶信息")
    print("-" * 60)
    
    try:
        import oracledb
        
        oracle_config = OracleConnectionHelper.get_oracle_config_from_env()
        if not oracle_config:
            print("❌ 未找到 Oracle 配置")
            return
        
        try:
            oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30\instantclient_19_30")
        except:
            pass
        
        # 構建 DSN
        database = oracle_config['database']
        try:
            dsn = oracledb.makedsn(
                oracle_config['host'],
                oracle_config['port'],
                service_name=database
            )
        except:
            dsn = oracledb.makedsn(
                oracle_config['host'],
                oracle_config['port'],
                sid=database
            )
        
        # 連接
        conn = oracledb.connect(
            user=oracle_config['username'],
            password=oracle_config['password'],
            dsn=dsn
        )
        
        cursor = conn.cursor()
        
        # 查詢用戶信息
        cursor.execute("SELECT USER FROM DUAL")
        user = cursor.fetchone()[0]
        print(f"✅ 當前用戶: {user}")
        
        # 查詢用戶表數
        cursor.execute("SELECT COUNT(*) FROM user_tables")
        table_count = cursor.fetchone()[0]
        print(f"✅ 用戶表格數: {table_count}")
        
        # 查詢數據庫信息
        cursor.execute("""
            SELECT name 
            FROM v$database
        """)
        result = cursor.fetchone()
        if result:
            print(f"✅ 數據庫名: {result[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 無法獲取用戶信息: {str(e)}")


if __name__ == "__main__":
    # 顯示用戶信息
    show_oracle_user_info()
    
    # 運行診斷
    success = test_oracle_discovery()
    
    print("\n" + "="*60)
    if success:
        print("✅ 診斷完成 - 一切正常")
    else:
        print("❌ 診斷發現問題")
    print("="*60 + "\n")
