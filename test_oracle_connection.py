#!/usr/bin/env python3
"""
Oracle 資料庫連接測試與資料字典生成
使用動態資料字典探測器連接到 Oracle 資料庫
"""

import logging
import os
from pathlib import Path
from datetime import datetime

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Oracle 連接資訊
ORACLE_CONFIG = {
    "host": "172.16.100.71",
    "port": 1521,
    "user": "NIS_BB_AdamAI",
    "password": "NIS_BB_AdamAI",
    "service_name": "cs1"
}


def test_oracle_import():
    """檢查 cx_Oracle 或 oracledb 驅動是否可用"""
    logger.info("=" * 60)
    logger.info("步驟 1：檢查 Oracle 驅動")
    logger.info("=" * 60)
    
    # 優先嘗試 cx_Oracle（更穩定）
    try:
        import cx_Oracle
        logger.info(f"✓ cx_Oracle 版本: {cx_Oracle.version}")
        return "cx_Oracle"
    except ImportError:
        pass
    
    # 嘗試 oracledb（新驅動）
    try:
        import oracledb
        logger.info(f"✓ oracledb 版本: {oracledb.__version__}")
        return "oracledb"
    except ImportError:
        pass
    
    logger.error("✗ 未找到 Oracle Python 驅動")
    logger.info("解決方案：執行以下命令安裝")
    logger.info("  pip install cx-Oracle  # 推薦")
    logger.info("  或")
    logger.info("  pip install oracledb")
    return None


def test_oracle_connection(driver_type):
    """測試 Oracle 資料庫連接"""
    logger.info("\n" + "=" * 60)
    logger.info("步驟 2：測試 Oracle 連接")
    logger.info("=" * 60)
    
    try:
        logger.info(f"\n使用驅動: {driver_type}")
        logger.info(f"連接信息:")
        logger.info(f"  主機: {ORACLE_CONFIG['host']}")
        logger.info(f"  端口: {ORACLE_CONFIG['port']}")
        logger.info(f"  用戶: {ORACLE_CONFIG['user']}")
        logger.info(f"  Service: {ORACLE_CONFIG['service_name']}")
        logger.info(f"\n正在連接...")
        
        if driver_type == "oracledb":
            import oracledb
            
            # 嘗試 thin mode（支持新版本 Oracle）
            try:
                logger.info("  [嘗試] Thin mode (適合 Oracle 12c+)")
                connection = oracledb.connect(
                    user=ORACLE_CONFIG['user'],
                    password=ORACLE_CONFIG['password'],
                    host=ORACLE_CONFIG['host'],
                    port=ORACLE_CONFIG['port'],
                    service_name=ORACLE_CONFIG['service_name']
                )
                logger.info("  ✓ Thin mode 連接成功")
            except Exception as e:
                # 檢查是否是版本不支持錯誤
                if "DPY-3010" in str(e):
                    logger.info("  ⚠ Thin mode 不支持此 Oracle 版本（可能是 Oracle 11g 或更舊）")
                    logger.info("\n  💡 此版本需要 Oracle Instant Client（Thick mode）")
                    logger.info("     請參考 ORACLE_CONNECTION_DIAGNOSTIC.md 進行設置")
                    logger.info("\n     快速修復（如已安裝 Instant Client）:")
                    logger.info('     oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")')
                    raise Exception("需要 Oracle Instant Client for thick mode") from e
                else:
                    raise
        else:  # cx_Oracle
            import cx_Oracle
            dsn = cx_Oracle.makedsn(
                host=ORACLE_CONFIG['host'],
                port=ORACLE_CONFIG['port'],
                service_name=ORACLE_CONFIG['service_name']
            )
            connection = cx_Oracle.connect(
                user=ORACLE_CONFIG['user'],
                password=ORACLE_CONFIG['password'],
                dsn=dsn
            )
        
        logger.info("✓ 連接成功！")
        
        # 取得版本信息
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM v$version WHERE rownum < 1")
        
        # 測試查詢
        cursor.execute("SELECT 1 FROM dual")
        result = cursor.fetchone()
        cursor.close()
        
        logger.info("✓ 查詢測試成功！")
        
        return connection
        
    except Exception as e:
        logger.error(f"✗ 連接失敗: {type(e).__name__}")
        if "DPY-3010" not in str(e):
            logger.error(f"詳細錯誤: {str(e)[:300]}")
        return None


def test_schema_discovery(connection):
    """使用 schema_discovery 系統探測 Oracle 資料庫"""
    logger.info("\n" + "=" * 60)
    logger.info("步驟 3：使用 Schema Discovery 探測資料庫")
    logger.info("=" * 60)
    
    try:
        from schema_discovery import (
            DatabaseType,
            create_introspector,
            SchemaDictionaryGenerator
        )
        
        # 建立 Oracle 反射器
        logger.info("建立 Oracle 反射器...")
        introspector = create_introspector(connection, DatabaseType.ORACLE)
        logger.info("✓ 反射器建立成功")
        
        # 取得所有表格
        logger.info("\n取得所有表格...")
        tables = introspector.get_tables()
        logger.info(f"✓ 探測到 {len(tables)} 個表格:")
        
        # 顯示前 20 個表格
        for table_name in tables[:20]:
            logger.info(f"  • {table_name}")
        
        if len(tables) > 20:
            logger.info(f"  ... 還有 {len(tables) - 20} 個表格")
        
        # 詳細探測第一個表格
        if tables:
            first_table = tables[0]
            logger.info(f"\n詳細探測第一個表格: {first_table}")
            
            metadata = introspector.get_table_metadata(first_table)
            logger.info(f"  表格名: {metadata.table_name}")
            logger.info(f"  Schema: {metadata.table_schema}")
            logger.info(f"  行數: {metadata.row_count}")
            logger.info(f"  欄位數: {len(metadata.columns)}")
            
            if metadata.columns:
                logger.info(f"\n  欄位列表（前 10 個）:")
                for col in metadata.columns[:10]:
                    flags = []
                    if col.is_primary_key:
                        flags.append("PK")
                    if not col.nullable:
                        flags.append("NOT NULL")
                    if col.is_unique:
                        flags.append("UNIQUE")
                    
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    logger.info(f"    - {col.column_name}: {col.data_type}{flag_str}")
                    if col.comment:
                        logger.info(f"      說明: {col.comment}")
        
        return introspector, tables
        
    except Exception as e:
        logger.error(f"✗ 探測失敗: {e}")
        import traceback
        traceback.print_exc()
        return None, []


def generate_oracle_dictionary(connection):
    """生成 Oracle 資料庫的完整資料字典"""
    logger.info("\n" + "=" * 60)
    logger.info("步驟 4：生成完整資料字典")
    logger.info("=" * 60)
    
    try:
        from schema_discovery import (
            DatabaseType,
            SchemaDictionaryGenerator
        )
        
        # 建立生成器
        logger.info("建立資料字典生成器...")
        generator = SchemaDictionaryGenerator(
            connection=connection,
            db_type=DatabaseType.ORACLE,
            use_llm=False,  # 使用本地規則（無需 API）
            database_name="Oracle_NIS_BB"
        )
        logger.info("✓ 生成器建立成功")
        
        # 生成資料字典
        logger.info("\n正在生成資料字典...")
        data_dict = generator.generate_dictionary()
        logger.info("✓ 資料字典生成完成")
        
        # 顯示統計資訊
        stats = data_dict.get_mapping_statistics()
        logger.info("\n📊 統計資訊:")
        logger.info(f"  表格數: {stats['total_tables']}")
        logger.info(f"  欄位總數: {stats['total_columns']}")
        logger.info(f"  已映射欄位: {stats['mapped_columns']}")
        logger.info(f"  未映射欄位: {stats['unmapped_columns']}")
        logger.info(f"  映射率: {stats['mapping_rate']:.1%}")
        logger.info(f"  平均信心度: {stats['average_confidence']:.1%}")
        
        # 匯出為 JSON
        json_filename = f"oracle_dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        logger.info(f"\n匯出 JSON 檔案: {json_filename}")
        generator.export_to_json(data_dict, json_filename)
        logger.info(f"✓ JSON 檔案已保存")
        
        # 匯出為 YAML
        yaml_filename = f"oracle_dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        logger.info(f"\n匯出 YAML 檔案: {yaml_filename}")
        generator.export_to_yaml_like(data_dict, yaml_filename)
        logger.info(f"✓ YAML 檔案已保存")
        
        # 顯示未映射欄位
        unmapped_report = generator.get_unmapped_columns_report(data_dict)
        logger.info("\n" + unmapped_report)
        
        generator.close()
        
        return json_filename, yaml_filename
        
    except Exception as e:
        logger.error(f"✗ 生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """執行完整的 Oracle 連接測試"""
    logger.info("\n")
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + " "*58 + "║")
    logger.info("║" + "  Oracle 資料庫探測測試 (Oracle Database Introspection)  ".center(58) + "║")
    logger.info("║" + " "*58 + "║")
    logger.info("╚" + "="*58 + "╝")
    
    connection = None
    
    try:
        # 檢查驅動
        driver_type = test_oracle_import()
        if not driver_type:
            logger.error("✗ Oracle 驅動未安裝，停止測試")
            return
        
        # 測試連接
        connection = test_oracle_connection(driver_type)
        if not connection:
            logger.error("✗ Oracle 連接失敗，停止測試")
            return
        
        # 探測資料庫
        result = test_schema_discovery(connection)
        if result[0]:
            introspector, tables = result
            logger.info(f"✓ 探測成功，找到 {len(tables)} 個表格")
        else:
            logger.warning("⚠ 探測失敗，但嘗試繼續生成資料字典")
        
        # 生成資料字典
        json_file, yaml_file = generate_oracle_dictionary(connection)
        if json_file:
            logger.info(f"\n✅ 資料字典已成功生成:")
            logger.info(f"  JSON: {json_file}")
            logger.info(f"  YAML: {yaml_file}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ 所有測試完成！")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n✗ 執行出錯: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 關閉連接
        if connection:
            try:
                connection.close()
                logger.info("\n✓ Oracle 連接已關閉")
            except:
                pass


if __name__ == "__main__":
    main()
