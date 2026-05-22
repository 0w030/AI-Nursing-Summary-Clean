#!/usr/bin/env python3
"""
Oracle 資料庫連接測試 - 支持 Instant Client Thick Mode
(Oracle Database Connection Test with Instant Client Support)

此腳本自動尋找並配置 Oracle Instant Client 的 thick mode 連接
This script automatically finds and configures Oracle Instant Client for thick mode connections
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Oracle 連接設置
ORACLE_CONFIG = {
    'host': '172.16.100.71',
    'port': 1521,
    'user': 'NIS_BB_AdamAI',
    'password': 'NIS_BB_AdamAI',
    'service': 'cs1'
}


def find_oracle_instant_client() -> Optional[str]:
    """
    尋找 Oracle Instant Client 的位置
    Searches for Oracle Instant Client installation path
    """
    logger.info("=" * 60)
    logger.info("步驟 1：尋找 Oracle Instant Client")
    logger.info("=" * 60)
    
    # 可能的位置列表
    possible_paths = [
        "/workspaces/instantclient",           # Dev container local
        "/opt/oracle/instantclient",           # Standard Linux location
        "/opt/oracle/instantclient_19_30",     # Versioned
        "/opt/instantclient",
        os.path.expanduser("~/instantclient"), # User home
        os.path.expanduser("~/Oracle/instantclient"),
    ]
    
    # 環境變數中指定的路徑
    env_paths = []
    for env_var in ['ORACLE_HOME', 'LD_LIBRARY_PATH', 'INSTANTCLIENT_PATH']:
        if env_var in os.environ:
            path = os.environ[env_var]
            if path and path not in env_paths:
                env_paths.append(path)
                possible_paths.insert(0, path)
    
    logger.info("搜尋 Oracle Instant Client...")
    logger.info("")
    
    for path in possible_paths:
        if not path:
            continue
            
        path_obj = Path(path)
        lib_path = path_obj / "libclntsh.so" or path_obj / "libclntsh.so.19.1" or path_obj / "libclntsh.so.12.1"
        
        # 檢查直接路徑
        if path_obj.exists():
            logger.info(f"  檢查: {path}")
            if (path_obj / "libclntsh.so").exists():
                logger.info(f"  ✓ 找到 Instant Client: {path}")
                return str(path)
            
            # 檢查版本化的 .so 文件
            so_files = list(path_obj.glob("libclntsh.so*"))
            if so_files:
                logger.info(f"  ✓ 找到 Instant Client: {path}")
                logger.info(f"    庫文件: {so_files[0].name}")
                return str(path)
    
    logger.warning("⚠ 未找到 Oracle Instant Client")
    return None


def init_oracle_thick_mode(lib_dir: Optional[str] = None) -> bool:
    """
    初始化 Oracle Thick Mode（需要 Instant Client）
    Initialize Oracle Thick Mode (requires Instant Client)
    
    Args:
        lib_dir: Optional path to Instant Client directory
    
    Returns:
        True if successfully initialized, False otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 2：初始化 Oracle Thick Mode")
    logger.info("=" * 60)
    
    try:
        import oracledb
        
        if lib_dir:
            logger.info(f"使用指定的 Instant Client 位置: {lib_dir}")
            oracledb.init_oracle_client(lib_dir=lib_dir)
        else:
            # 嘗試自動偵測
            client_path = find_oracle_instant_client()
            if client_path:
                logger.info(f"自動偵測到的位置: {client_path}")
                oracledb.init_oracle_client(lib_dir=client_path)
            else:
                logger.warning("未指定 Instant Client 位置，嘗試使用系統預設...")
                oracledb.init_oracle_client()
        
        logger.info("✓ Oracle Thick Mode 已初始化")
        
        # 驗證初始化
        logger.info("  驗證: 檢查 oracledb 版本和模式")
        logger.info(f"    oracledb 版本: {oracledb.__version__}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Thick Mode 初始化失敗: {type(e).__name__}")
        logger.error(f"  錯誤: {str(e)[:200]}")
        
        if "DPI-1047" in str(e):
            logger.error("")
            logger.error("  💡 症狀: 無法定位 Oracle 客戶端庫")
            logger.error("")
            logger.error("  解決方案:")
            logger.error("    1. 安裝 Oracle Instant Client:")
            logger.error("       https://www.oracle.com/database/technologies/instant-client/downloads.html")
            logger.error("       選擇: Linux x86-64")
            logger.error("       下載: instantclient-basic-linux.x64-19.30.0.0.0dbru.zip")
            logger.error("")
            logger.error("    2. 解壓到 /opt/oracle/instantclient:")
            logger.error("       mkdir -p /opt/oracle")
            logger.error("       unzip instantclient-basic-linux.x64-*.zip -d /opt/oracle/")
            logger.error("")
            logger.error("    3. 再次運行此腳本")
        
        return False


def test_oracle_connection_thin_mode() -> Optional[object]:
    """
    嘗試 Thin Mode 連接（不需要 Instant Client）
    Try Thin Mode connection (no Instant Client required)
    
    Returns:
        Connection object if successful, None otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 3a：嘗試 Thin Mode 連接")
    logger.info("=" * 60)
    
    try:
        import oracledb
        
        logger.info("嘗試無客戶端連接 (Thin Mode)...")
        logger.info(f"  主機: {ORACLE_CONFIG['host']}")
        logger.info(f"  端口: {ORACLE_CONFIG['port']}")
        logger.info(f"  Service: {ORACLE_CONFIG['service']}")
        logger.info("")
        
        dsn = f"{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"
        connection = oracledb.connect(
            user=ORACLE_CONFIG['user'],
            password=ORACLE_CONFIG['password'],
            dsn=dsn
        )
        
        logger.info("✓ Thin Mode 連接成功！")
        return connection
    
    except Exception as e:
        error_msg = str(e)
        if "DPY-3010" in error_msg or "thin mode" in error_msg.lower():
            logger.warning("⚠ 此 Oracle 版本不支持 Thin Mode")
            logger.info("  需要使用 Thick Mode（需要 Instant Client）")
            return None
        else:
            logger.error(f"✗ 連接失敗: {type(e).__name__}")
            logger.error(f"  錯誤: {str(e)[:200]}")
            return None


def test_oracle_connection_thick_mode(lib_dir: Optional[str] = None) -> Optional[object]:
    """
    嘗試 Thick Mode 連接（需要 Instant Client）
    Try Thick Mode connection (requires Instant Client)
    
    Args:
        lib_dir: Optional path to Instant Client
    
    Returns:
        Connection object if successful, None otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 3b：嘗試 Thick Mode 連接")
    logger.info("=" * 60)
    
    if not init_oracle_thick_mode(lib_dir):
        return None
    
    try:
        import oracledb
        
        logger.info("")
        logger.info("連接到 Oracle 數據庫...")
        logger.info(f"  主機: {ORACLE_CONFIG['host']}")
        logger.info(f"  端口: {ORACLE_CONFIG['port']}")
        logger.info(f"  用戶: {ORACLE_CONFIG['user']}")
        logger.info(f"  Service: {ORACLE_CONFIG['service']}")
        logger.info("")
        
        dsn = f"{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"
        connection = oracledb.connect(
            user=ORACLE_CONFIG['user'],
            password=ORACLE_CONFIG['password'],
            dsn=dsn
        )
        
        logger.info("✓ Thick Mode 連接成功！")
        return connection
    
    except Exception as e:
        logger.error(f"✗ Thick Mode 連接失敗: {type(e).__name__}")
        logger.error(f"  錯誤: {str(e)[:200]}")
        
        if "ORA-" in str(e):
            error_code = str(e).split("ORA-")[1][:5]
            logger.error(f"  Oracle 錯誤代碼: ORA-{error_code}")
            logger.info("")
            logger.info("  常見 Oracle 錯誤:")
            if "12514" in str(e) or "12505" in str(e):
                logger.info("    • ORA-12514/12505: 監聽器未識別服務名")
                logger.info("      解決: 驗證 'cs1' 服務名是否正確")
            elif "1017" in str(e):
                logger.info("    • ORA-01017: 用戶/密碼無效")
                logger.info("      解決: 驗證用戶名和密碼")
            elif "1034" in str(e):
                logger.info("    • ORA-01034: Oracle 不可用")
                logger.info("      解決: 驗證 Oracle 服務是否運行")
        
        return None


def test_connection_via_sql_plus() -> bool:
    """
    使用 sqlplus 驗證連接（如果已安裝）
    Test connection using sqlplus if available
    
    Returns:
        True if connection successful, False otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 4：驗證連接 (SQLPlus)")
    logger.info("=" * 60)
    
    try:
        import subprocess
        
        dsn = f"{ORACLE_CONFIG['user']}/{ORACLE_CONFIG['password']}@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"
        cmd = ['sqlplus', '-v']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            logger.info("✓ SQLPlus 已安裝")
            logger.info(f"  可使用命令: sqlplus {dsn}")
            return True
        else:
            logger.info("⚠ SQLPlus 未安裝或不可用")
            return False
    
    except Exception as e:
        logger.info("⚠ SQLPlus 未找到")
        return False


def main():
    """
    主程序 - 嘗試所有連接方法
    Main program - Try all connection methods
    """
    logger.info("")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "Oracle 資料庫連接測試 (多模式)".center(58) + "║")
    logger.info("║" + "Oracle Database Connection Test (Multi-Mode)".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    
    connection = None
    
    # 嘗試 1: Thin Mode（推薦用於 Oracle 12c+）
    logger.info("")
    logger.info("嘗試 1: Thin Mode（無需 Instant Client）")
    connection = test_oracle_connection_thin_mode()
    
    if connection:
        logger.info("")
        logger.info("✅ 連接成功（使用 Thin Mode）")
    else:
        # 嘗試 2: 自動偵測 Instant Client
        logger.info("")
        logger.info("嘗試 2: Thick Mode（自動偵測 Instant Client）")
        connection = test_oracle_connection_thick_mode()
        
        if connection:
            logger.info("")
            logger.info("✅ 連接成功（使用 Thick Mode）")
        else:
            # 嘗試 3: 檢查環境變數指定的位置
            lib_dir = os.environ.get('ORACLE_INSTANTCLIENT_PATH')
            if lib_dir:
                logger.info("")
                logger.info(f"嘗試 3: 使用環境變數指定的位置: {lib_dir}")
                connection = test_oracle_connection_thick_mode(lib_dir)
                
                if connection:
                    logger.info("")
                    logger.info("✅ 連接成功（使用 Thick Mode）")
            else:
                logger.error("")
                logger.error("❌ 所有連接方式都失敗")
                logger.info("")
                logger.info("📋 建議步驟:")
                logger.info("  1. 確認網絡連接到 172.16.100.71:1521")
                logger.info("  2. 驗證用戶名和密碼是否正確")
                logger.info("  3. 安裝 Oracle Instant Client（如需要）")
                logger.info("     參考: ORACLE_TEST_SUMMARY.md")
                return 1
    
    # 如果連接成功
    if connection:
        try:
            # 測試查詢
            logger.info("")
            logger.info("=" * 60)
            logger.info("步驟 5：執行測試查詢")
            logger.info("=" * 60)
            
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM dual")
            result = cursor.fetchone()
            cursor.close()
            
            logger.info("✓ 查詢執行成功")
            logger.info("")
            logger.info("✅ Oracle 連接完全驗證成功！")
            logger.info("")
            logger.info("後續步驟:")
            logger.info("  • 運行 schema discovery 以生成數據字典")
            logger.info("  • 檢查生成的 oracle_dictionary_*.json/yaml 文件")
            
            connection.close()
            return 0
        
        except Exception as e:
            logger.error(f"✗ 查詢失敗: {e}")
            connection.close()
            return 1
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
