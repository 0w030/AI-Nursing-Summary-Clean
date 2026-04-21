"""
第三階段演示初始化腳本
設置演示數據和初始配置
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config_manager import (
    config_manager, DatabaseConnection, FieldMapping
)

def init_demo_data():
    """初始化演示數據"""
    print("=" * 80)
    print("第三階段 - 管理中控台 演示初始化")
    print("=" * 80)
    
    # 1. 添加演示連接
    print("\n[步驟 1/3] 添加演示資料庫連接...")
    
    demo_connections = [
        DatabaseConnection(
            name="hospital_main",
            db_type="oracle",
            host="172.16.100.71",
            port=1521,
            database="NIS_BB_ADAMAI",
            username="NIS_BB_AdamAI",
            is_active=True,
        ),
        DatabaseConnection(
            name="hospital_test",
            db_type="oracle",
            host="192.168.1.100",
            port=1521,
            database="TEST_DB",
            username="test_user",
            is_active=False,
        ),
    ]
    
    for conn in demo_connections:
        config_manager.add_connection(conn)
        print(f"  ✓ 添加連接: {conn.name}")
    
    # 2. 添加演示 Schema 映射
    print("\n[步驟 2/3] 添加演示 Schema 映射...")
    
    demo_mappings = {
        "ABNORMAL_TREATMENT": [
            FieldMapping(
                table_name="ABNORMAL_TREATMENT",
                db_column_name="ID",
                system_column_type="String",
                original_type="VARCHAR2(16)",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
                confirmed_at=datetime.now().isoformat(),
            ),
            FieldMapping(
                table_name="ABNORMAL_TREATMENT",
                db_column_name="INTERVENTION_ID",
                system_column_type="String",
                original_type="VARCHAR2(20)",
                is_ai_suggested=True,
                is_confirmed=False,
            ),
            FieldMapping(
                table_name="ABNORMAL_TREATMENT",
                db_column_name="ABNORMAL_TYPE",
                system_column_type="String",
                original_type="VARCHAR2(30)",
                is_ai_suggested=True,
                is_confirmed=False,
            ),
            FieldMapping(
                table_name="ABNORMAL_TREATMENT",
                db_column_name="STATUS",
                system_column_type="String",
                original_type="VARCHAR2(1)",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
                confirmed_at=datetime.now().isoformat(),
            ),
            FieldMapping(
                table_name="ABNORMAL_TREATMENT",
                db_column_name="LAST_UPDATE_TIME",
                system_column_type="DateTime",
                original_type="TIMESTAMP(6)",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
                confirmed_at=datetime.now().isoformat(),
            ),
        ],
        "APIINTERTABLE": [
            FieldMapping(
                table_name="APIINTERTABLE",
                db_column_name="API_ID",
                system_column_type="String",
                original_type="VARCHAR2(50)",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
            ),
            FieldMapping(
                table_name="APIINTERTABLE",
                db_column_name="API_STATUS",
                system_column_type="String",
                original_type="VARCHAR2(20)",
                is_ai_suggested=True,
                is_confirmed=False,
            ),
        ],
        "APILOG": [
            FieldMapping(
                table_name="APILOG",
                db_column_name="LOG_ID",
                system_column_type="Integer",
                original_type="NUMBER(10)",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
            ),
            FieldMapping(
                table_name="APILOG",
                db_column_name="LOG_TIME",
                system_column_type="DateTime",
                original_type="TIMESTAMP",
                is_ai_suggested=False,
                is_confirmed=True,
                confirmed_by="admin",
            ),
            FieldMapping(
                table_name="APILOG",
                db_column_name="LOG_DETAIL",
                system_column_type="String",
                original_type="CLOB",
                is_ai_suggested=True,
                is_confirmed=False,
            ),
        ],
    }
    
    config_manager.bulk_update_mappings(demo_mappings, "system")
    print(f"  ✓ 添加 {len(demo_mappings)} 個表格的映射")
    
    # 3. 顯示統計信息
    print("\n[步驟 3/3] 演示數據統計...")
    
    connections = config_manager.list_connections()
    mappings = config_manager.get_all_mappings()
    logs = config_manager.get_operation_logs()
    
    print(f"\n📊 系統狀態:")
    print(f"  連接數: {len(connections)}")
    print(f"  表格數: {len(mappings)}")
    print(f"  總欄位數: {sum(len(m) for m in mappings.values())}")
    print(f"  操作日誌: {len(logs)}")
    
    print("\n" + "=" * 80)
    print("✅ 演示初始化完成！")
    print("=" * 80)
    print("\n快速開始:")
    print("  1. 啟動管理儀表板:")
    print("     streamlit run pages/management_dashboard.py")
    print("\n  2. 或啟動後端 API:")
    print("     python -m uvicorn api.management_api:app --reload")
    print("\n  3. 登錄帳號:")
    print("     - 用戶名: admin | 密碼: demo (管理員)")
    print("     - 用戶名: manager | 密碼: demo (經理)")
    print("     - 用戶名: viewer | 密碼: demo (查看者)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    init_demo_data()
