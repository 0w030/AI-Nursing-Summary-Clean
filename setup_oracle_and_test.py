#!/usr/bin/env python3
"""
自動化安裝 Oracle Instant Client 並測試連接
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

def setup_instant_client():
    """下載並安裝 Oracle Instant Client"""
    
    instant_client_dir = Path("D:/oracle_instant_client")
    
    print("=" * 60)
    print("🔧 Oracle Instant Client 自動化設置")
    print("=" * 60)
    print()
    
    # 檢查是否已存在
    if (instant_client_dir / "oci.dll").exists():
        print(f"✅ Oracle Instant Client 已存在於: {instant_client_dir}")
        return str(instant_client_dir)
    
    print("⚠️  需要下載 Oracle Instant Client")
    print()
    print("請執行以下步驟:")
    print()
    print("1️⃣  將下載的文件解壓到: D:\\oracle_instant_client")
    print("    下載地址: https://www.oracle.com/database/technologies/instant-client/downloads.html")
    print("    選擇: Windows (x64) → InstantClient 19c 或 21c")
    print()
    print("2️⃣  運行此命令添加到 PATH（需要以管理員身份）:")
    print()
    print("    [Environment]::SetEnvironmentVariable(")
    print("        'Path',")
    print("        $env:Path + ';D:\\oracle_instant_client\\instantclient_21_10',")
    print("        'Machine'")
    print("    )")
    print()
    print("3️⃣  重新啟動 PowerShell")
    print()
    print("=" * 60)
    
    return None

def test_oracle_connection():
    """測試 Oracle 連接"""
    
    print()
    print("=" * 60)
    print("🔌 測試 Oracle 資料庫連接")
    print("=" * 60)
    print()
    
    try:
        import oracledb
        
        # 讀取 .env 配置
        config = {}
        if Path(".env").exists():
            with open(".env") as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        
        # 提取 Oracle 參數
        host = config.get("ORACLE_HOST", "172.16.100.71")
        port = config.get("ORACLE_PORT", "1521")
        user = config.get("ORACLE_USER", "NIS_BB_AdamAI")
        pwd = config.get("ORACLE_PASSWORD", "NIS_BB_AdamAI")
        sid = config.get("ORACLE_SID", "cs1")
        
        print(f"連接信息:")
        print(f"  主機: {host}:{port}")
        print(f"  用戶: {user}")
        print(f"  SID: {sid}")
        print()
        
        # 檢查 Instant Client
        ic_path = Path("D:/oracle_instant_client")
        if not (ic_path / "oci.dll").exists():
            print("❌ 未找到 Oracle Instant Client")
            print()
            print("需要先安裝 Instant Client。執行此命令:")
            print("  python setup_oracle_and_test.py --install")
            return False
        
        print("✅ Oracle Instant Client 已就位")
        print()
        
        # 初始化 thick mode
        print("🔄 初始化 thick mode...")
        oracledb.init_oracle_client(lib_dir=str(ic_path / "instantclient_21_10"))
        print("✅ Thick mode 已初始化")
        print()
        
        # 連接測試
        print("🔄 正在連接資料庫...")
        conn_str = f"{user}/{pwd}@{host}:{port}/{sid}"
        connection = oracledb.connect(conn_str)
        
        print("✅ 連接成功！")
        print(f"   Oracle 版本: {connection.version}")
        print()
        
        # 執行測試查詢
        print("🔄 執行測試查詢...")
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM dual")
        result = cursor.fetchone()
        print(f"✅ 查詢成功！結果: {result[0]}")
        print()
        
        connection.close()
        
        print("=" * 60)
        print("✨ Oracle 資料庫連接正常！")
        print("=" * 60)
        print()
        print("系統已準備好與 Oracle 資料庫通信。")
        print("啟動應用: python -m uvicorn api.main:app --port 8000")
        
        return True
        
    except ImportError:
        print("❌ oracledb 模塊未找到")
        print("執行: pip install oracledb")
        return False
    except Exception as e:
        print(f"❌ 連接失敗: {str(e)}")
        print(f"類型: {type(e).__name__}")
        if "thick mode" in str(e) or "DPI-1047" in str(e):
            print()
            print("需要 Oracle Instant Client。執行:")
            print("  python setup_oracle_and_test.py --install")
        return False

if __name__ == "__main__":
    if "--install" in sys.argv:
        setup_instant_client()
    else:
        test_oracle_connection()
