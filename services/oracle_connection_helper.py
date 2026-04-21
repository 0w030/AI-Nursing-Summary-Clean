"""
Oracle 連接助手 - 從 .env 讀取預配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict

# 載入環境變數
load_dotenv()


class OracleConnectionHelper:
    """Oracle 連接配置助手"""
    
    @staticmethod
    def get_oracle_config_from_env() -> Optional[Dict]:
        """
        從 .env 讀取 Oracle 配置
        
        Returns:
            連接配置字典，如果配置不完整則返回 None
        """
        try:
            host = os.getenv('ORACLE_HOST')
            port = os.getenv('ORACLE_PORT')
            sid_or_service = os.getenv('ORACLE_SID') or os.getenv('ORACLE_SERVICE_NAME')
            username = os.getenv('ORACLE_USER')
            password = os.getenv('ORACLE_PASSWORD')
            
            # 驗證所有必要的配置都存在
            if not all([host, port, sid_or_service, username, password]):
                return None
            
            # 轉換 port 為整數
            try:
                port = int(port)
            except ValueError:
                return None
            
            return {
                'db_type': 'oracle',
                'host': host,
                'port': port,
                'database': sid_or_service,  # 可以是 SID 或 Service Name
                'username': username,
                'password': password
            }
        except Exception as e:
            print(f"❌ 讀取 Oracle 配置失敗: {str(e)}")
            return None
    
    @staticmethod
    def display_oracle_config() -> str:
        """
        顯示 Oracle 配置摘要（隱藏密碼）
        """
        config = OracleConnectionHelper.get_oracle_config_from_env()
        if not config:
            return "❌ 未找到 Oracle 配置"
        
        return f"""
📌 **從 .env 讀取的 Oracle 配置：**

- 主機: `{config['host']}`
- 埠口: `{config['port']}`
- SID/Service: `{config['database']}`
- 用戶: `{config['username']}`
- 密碼: ••••••••（隱藏）
"""
    
    @staticmethod
    def verify_connection() -> bool:
        """
        驗證 Oracle 連接
        
        Returns:
            連接是否成功
        """
        try:
            import oracledb
            
            config = OracleConnectionHelper.get_oracle_config_from_env()
            if not config:
                print("❌ 未找到 Oracle 配置")
                return False
            
            # 嘗試連接
            try:
                oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30\instantclient_19_30")
            except:
                pass
            
            # 構建 DSN
            database = config['database']
            try:
                # 先嘗試 Service Name
                dsn = oracledb.makedsn(
                    config['host'],
                    config['port'],
                    service_name=database
                )
                conn_type = "Service Name"
            except:
                # 改用 SID
                dsn = oracledb.makedsn(
                    config['host'],
                    config['port'],
                    sid=database
                )
                conn_type = "SID"
            
            # 建立連接
            conn = oracledb.connect(
                user=config['username'],
                password=config['password'],
                dsn=dsn
            )
            conn.close()
            
            print(f"✅ Oracle 連接成功！（使用 {conn_type}）")
            return True
            
        except Exception as e:
            print(f"❌ Oracle 連接失敗: {str(e)}")
            return False


if __name__ == "__main__":
    print("🧪 Oracle 連接配置測試\n")
    
    # 顯示配置
    print(OracleConnectionHelper.display_oracle_config())
    
    # 驗證連接
    print("\n正在驗證連接...")
    OracleConnectionHelper.verify_connection()
