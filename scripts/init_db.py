# scripts/init_db.py
"""
數據庫初始化腳本
用於容器啟動時初始化 Schema
支援多資料庫類型
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加父目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_db_config, DatabaseType
import asyncpg
import psycopg2


async def init_postgresql():
    """初始化 PostgreSQL 數據庫"""
    config = get_db_config()
    
    print(f"🔄 正在初始化 PostgreSQL 主機 {config.host}:{config.port}/{config.database}...")
    
    try:
        # 連接到 PostgreSQL
        pool = await asyncpg.create_pool(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            min_size=1,
            max_size=1,
        )
        
        # 讀取 SQL 遷移檔案
        migration_dir = Path(__file__).parent.parent / "sql" / "migrations"
        migration_file = migration_dir / "001_init_schema.sql"
        
        if not migration_file.exists():
            print(f"⚠️  未找到遷移檔案: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 移除 PostgreSQL 部分之前的 Oracle 註釋
        if "-- ============================================" in sql_content:
            # 只執行 PostgreSQL 部分
            pg_part = sql_content.split("-- ============================================")[1]
            sql_statements = [s.strip() for s in pg_part.split(';') if s.strip()]
        else:
            sql_statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        # 執行 SQL 語句
        async with pool.acquire() as conn:
            for statement in sql_statements:
                if statement and not statement.startswith('--'):
                    try:
                        await conn.execute(statement)
                        print(f"✅ 執行: {statement[:50]}...")
                    except Exception as e:
                        print(f"⚠️  忽略: {str(e)[:80]}")
        
        await pool.close()
        print("✅ PostgreSQL 初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL 初始化失敗: {e}")
        return False


async def init_oracle():
    """初始化 Oracle 數據庫"""
    config = get_db_config()
    
    print(f"🔄 正在初始化 Oracle 主機 {config.host}:{config.port}/{config.database}...")
    
    try:
        import cx_Oracle
        
        conn = cx_Oracle.connect(config.get_connection_string())
        cursor = conn.cursor()
        
        # 讀取 SQL 遷移檔案
        migration_dir = Path(__file__).parent.parent / "sql" / "migrations"
        migration_file = migration_dir / "001_init_schema.sql"
        
        if not migration_file.exists():
            print(f"⚠️  未找到遷移檔案: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 只執行 Oracle 部分（在 /* */ 註釋中）
        if "/*" in sql_content and "*/" in sql_content:
            start = sql_content.find("/*") + 2
            end = sql_content.find("*/")
            oracle_part = sql_content[start:end]
        else:
            oracle_part = sql_content
        
        sql_statements = [s.strip() for s in oracle_part.split(';') if s.strip()]
        
        # 執行 SQL 語句
        for statement in sql_statements:
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    conn.commit()
                    print(f"✅ 執行: {statement[:50]}...")
                except cx_Oracle.DatabaseError as e:
                    print(f"⚠️  忽略: {str(e)[:80]}")
        
        cursor.close()
        conn.close()
        print("✅ Oracle 初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ Oracle 初始化失敗: {e}")
        return False


async def init_sqlite():
    """初始化 SQLite 數據庫"""
    config = get_db_config()
    
    print(f"🔄 正在初始化 SQLite 數據庫 {config.database}...")
    
    try:
        import sqlite3
        
        db_path = config.database
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 簡化的 SQLite schema
        schema_sql = """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            patient_id TEXT UNIQUE NOT NULL,
            name TEXT,
            birth_date TEXT,
            gender TEXT,
            admission_date TEXT,
            department TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS nursing_records (
            id INTEGER PRIMARY KEY,
            patient_id TEXT NOT NULL,
            record_time TEXT NOT NULL,
            nursing_note TEXT,
            assessment TEXT,
            intervention TEXT,
            response TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        );
        """
        
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()
        
        print("✅ SQLite 初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ SQLite 初始化失敗: {e}")
        return False


async def main():
    """主入口函數"""
    print("=" * 50)
    print("數據庫初始化工具")
    print("=" * 50)
    
    config = get_db_config()
    print(f"✅ 已載入配置: {config.db_type.value}")
    
    if config.db_type == DatabaseType.POSTGRESQL:
        success = await init_postgresql()
    elif config.db_type == DatabaseType.ORACLE:
        success = await init_oracle()
    elif config.db_type == DatabaseType.SQLITE:
        success = await init_sqlite()
    else:
        print(f"❌ 不支援的資料庫類型: {config.db_type}")
        return 1
    
    print("=" * 50)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
