#!/usr/bin/env python3
"""
使用 SQLAlchemy 測試 Oracle 連接與 Schema 探測
(Oracle Connection Test with SQLAlchemy and Schema Discovery)
"""

import logging
import json
import sys
import inspect
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

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


def print_header():
    """Print test header"""
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║                                                          ║")
    logger.info("║     Oracle 資料庫探測 (SQLAlchemy 模式)                   ║")
    logger.info("║     Oracle Database Discovery (SQLAlchemy Mode)          ║")
    logger.info("║                                                          ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")


def test_sqlalchemy_import() -> bool:
    """Test if SQLAlchemy is available"""
    logger.info("=" * 60)
    logger.info("步驟 1：檢查 SQLAlchemy 依賴")
    logger.info("=" * 60)
    
    try:
        import sqlalchemy
        logger.info(f"✓ SQLAlchemy 版本: {sqlalchemy.__version__}")
        return True
    except ImportError as e:
        logger.error(f"✗ SQLAlchemy 未安裝: {e}")
        logger.info("  安裝命令: pip install sqlalchemy")
        return False


def test_oracle_dialect() -> bool:
    """Test if Oracle dialect is available"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 2：檢查 Oracle 方言")
    logger.info("=" * 60)
    
    try:
        from sqlalchemy.dialects import oracle
        logger.info("✓ SQLAlchemy Oracle 方言已安裝")
        
        # Check available backends
        logger.info("  可用的後端驅動:")
        backends = ['oracledb', 'cx_oracle']
        for backend in backends:
            try:
                if backend == 'oracledb':
                    import oracledb
                    logger.info(f"    • {backend}: {oracledb.__version__}")
                else:
                    import cx_Oracle
                    logger.info(f"    • {backend}: {cx_Oracle.version}")
            except ImportError:
                logger.info(f"    • {backend}: ✗ 未安裝")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Oracle 方言未安裝: {e}")
        return False


def test_oracle_connection() -> bool:
    """Test Oracle connection using SQLAlchemy"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 3：測試 Oracle 連接")
    logger.info("=" * 60)
    
    try:
        from sqlalchemy import create_engine, inspect
        
        # Build connection URL
        # Format: oracle://user:password@host:port/?service_name=service
        conn_str = (
            f"oracle+oracledb://{ORACLE_CONFIG['user']}:{ORACLE_CONFIG['password']}"
            f"@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}"
            f"/?service_name={ORACLE_CONFIG['service']}"
        )
        
        logger.info(f"連接字符串: oracle+oracledb://user:***@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}")
        logger.info("正在連接...")
        
        engine = create_engine(conn_str, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 FROM dual")
            logger.info("✓ 連接成功")
            return True
    
    except Exception as e:
        logger.error(f"✗ 連接失敗: {type(e).__name__}: {str(e)[:200]}")
        
        # Provide troubleshooting advice
        error_msg = str(e).lower()
        if "thin mode" in error_msg or "dpy-3010" in error_msg:
            logger.info("")
            logger.info("💡 故障排除建議:")
            logger.info("  1. 此 Oracle 版本不支持 oracledb 的 thin mode")
            logger.info("  2. 解決方案:")
            logger.info("     a) 安裝 Oracle Instant Client:")
            logger.info("        - 下載自: https://www.oracle.com/database/technologies/instant-client/")
            logger.info("        - 配置環境變數: LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/path/to/instant_client")
            logger.info("     b) 或使用其他驅動 (cx_Oracle)")
            logger.info("     c) 或升級到更新的 Oracle 資料庫版本")
        
        return False


def discover_schema(engine) -> Dict[str, Any]:
    """Discover schema information"""
    try:
        from sqlalchemy import inspect as sa_inspect
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("步驟 4：探測 Schema")
        logger.info("=" * 60)
        
        inspector = sa_inspect(engine)
        schema_info = {
            'tables': [],
            'table_count': 0,
            'column_count': 0,
            'discovery_time': datetime.now().isoformat()
        }
        
        # Get all tables
        table_names = inspector.get_table_names(schema=ORACLE_CONFIG['user'])
        logger.info(f"發現 {len(table_names)} 張表")
        
        for table_name in table_names[:10]:  # Limit to first 10 tables
            columns = inspector.get_columns(table_name, schema=ORACLE_CONFIG['user'])
            table_info = {
                'name': table_name,
                'column_count': len(columns),
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col.get('nullable', True)
                    }
                    for col in columns
                ]
            }
            schema_info['tables'].append(table_info)
            schema_info['column_count'] += len(columns)
        
        schema_info['table_count'] = len(table_names)
        return schema_info
    
    except Exception as e:
        logger.error(f"✗ Schema 探測失敗: {e}")
        return None


def export_results(schema_info: Dict[str, Any]):
    """Export discovery results"""
    if not schema_info:
        return
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("步驟 5：導出結果")
    logger.info("=" * 60)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"oracle_schema_discovery_{timestamp}.json"
    filepath = Path(filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(schema_info, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ 結果已導出到: {filepath}")
    logger.info(f"  表數量: {schema_info['table_count']}")
    logger.info(f"  列數量: {schema_info['column_count']}")
    
    # Show sample
    if schema_info['tables']:
        logger.info("")
        logger.info("樣本表 (前 3 張):")
        for table in schema_info['tables'][:3]:
            logger.info(f"  • {table['name']} ({table['column_count']} 列)")
            for col in table['columns'][:3]:
                logger.info(f"      - {col['name']}: {col['type']}")
            if len(table['columns']) > 3:
                logger.info(f"      ... 還有 {len(table['columns']) - 3} 列")


def main():
    """Main test workflow"""
    print_header()
    
    # Step 1: Check SQLAlchemy
    if not test_sqlalchemy_import():
        logger.error("✗ 測試中止：缺少 SQLAlchemy")
        logger.info("\n推薦安裝:")
        logger.info("  pip install sqlalchemy[oracle]")
        return 1
    
    # Step 2: Check Oracle dialect
    if not test_oracle_dialect():
        logger.error("✗ 測試中止：缺少 Oracle 方言")
        return 1
    
    # Step 3: Test connection
    if not test_oracle_connection():
        logger.error("✗ 連接測試失敗")
        logger.info("")
        logger.info("📋 快速故障排除檢查單:")
        logger.info("  ☐ 驗證 Oracle 主機可達: ping 172.16.100.71")
        logger.info("  ☐ 驗證網絡連接: telnet 172.16.100.71 1521")
        logger.info("  ☐ 驗證憑證正確")
        logger.info("  ☐ 驗證服務名稱: cs1")
        logger.info("  ☐ 檢查防火牆設置")
        logger.info("  ☐ 安裝 Oracle Instant Client（如需要）")
        return 1
    
    # If connection succeeded, discover schema
    from sqlalchemy import create_engine
    conn_str = (
        f"oracle+oracledb://{ORACLE_CONFIG['user']}:{ORACLE_CONFIG['password']}"
        f"@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}"
        f"/?service_name={ORACLE_CONFIG['service']}"
    )
    engine = create_engine(conn_str, echo=False)
    schema_info = discover_schema(engine)
    
    if schema_info:
        export_results(schema_info)
        logger.info("")
        logger.info("✓ 所有測試完成")
        return 0
    else:
        logger.error("✗ Schema 探測失敗")
        return 1


if __name__ == '__main__':
    sys.exit(main())
