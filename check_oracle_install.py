#!/usr/bin/env python3
"""
Oracle Instant Client 驗證腳本
Verify Oracle Instant Client Installation
"""

import os
import sys
from pathlib import Path

def check_instant_client():
    """檢查 Oracle Instant Client 是否已正確安裝"""
    
    print("\n" + "="*60)
    print("Oracle Instant Client 驗證工具")
    print("Oracle Instant Client Verification Tool")
    print("="*60 + "\n")
    
    possible_paths = [
        "/opt/oracle/instantclient_19_30",
        "/opt/oracle/instantclient",
        "/workspaces/instantclient/instantclient_19_30",
        "/workspaces/instantclient",
        os.path.expanduser("~/oracle/instantclient"),
        os.path.expanduser("~/instantclient"),
    ]
    
    found = False
    
    print("📍 搜尋 Oracle Instant Client...\n")
    
    for path in possible_paths:
        path_obj = Path(path)
        
        if path_obj.exists():
            print(f"✓ 找到目錄: {path}")
            
            # 檢查必要的文件
            libclntsh = list(path_obj.glob("libclntsh.so*"))
            if libclntsh:
                print(f"  ✓ 庫文件: {libclntsh[0].name}")
                found = True
                
                # 驗證環境變數
                ld_path = os.environ.get('LD_LIBRARY_PATH', '')
                if str(path) in ld_path:
                    print(f"  ✓ 環境變數配置正確")
                else:
                    print(f"  ⚠ 環境變數未配置")
                    print(f"    建議: export LD_LIBRARY_PATH={path}:$LD_LIBRARY_PATH")
                
                print(f"\n✅ Oracle Instant Client 安裝正確！\n")
                print("可以運行:")
                print("  cd /workspaces/AI-Nursing-Summary-Clean")
                print("  python test_oracle_setup.py")
                print()
                return True
    
    if not found:
        print("❌ 未找到 Oracle Instant Client\n")
        print("下一步:")
        print("  1. 參考 ORACLE_LINUX_SETUP.md 進行安裝")
        print("  2. 確保安裝到 /opt/oracle/instantclient_19_30")
        print("  3. 設置環境變數 LD_LIBRARY_PATH")
        print()
        return False

if __name__ == '__main__':
    success = check_instant_client()
    sys.exit(0 if success else 1)
