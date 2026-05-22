#!/usr/bin/env python3
"""
動態資料字典探測系統 - 完整測試和演示
自動探測 Oracle 數據庫 Schema，進行 LLM 語意映射，生成完整的數據字典

使用方法：
  python run_schema_discovery.py --max-tables 5
  python run_schema_discovery.py --no-llm  # 只進行反射，不做 LLM 對齊
"""

import sys
import os
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema_discovery.oracle_introspector import OracleIntrospector
from schema_discovery.data_dictionary import DataDictionary, TypeMapper, CoreDataType
from core.config import get_db_config, DatabaseType

# 嘗試導入 LLM 對齐器
try:
    from schema_discovery.openai_semantic_aligner import OpenAISemanticAligner
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: LLM 模組不可用，將跳過語意對齄")

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchemaDictionaryGenerator:
    """資料字典生成器 - 集成反射和語意對齄"""
    
    def __init__(self):
        """初始化生成器"""
        self.config = get_db_config()
        self.introspector = None
        self.aligner = None
        self.data_dictionary = None
        self.type_mapper = TypeMapper()
        self.output_dir = Path("schema_output")
    
    def connect_to_database(self) -> bool:
        """連接到資料庫"""
        try:
            if self.config.db_type == DatabaseType.ORACLE:
                import oracledb
                
                # 初始化 Instant Client
                ic_path = Path("C:/instantclient_19_30/instantclient_19_30")
                if ic_path.exists():
                    oracledb.init_oracle_client(lib_dir=str(ic_path))
                    logger.info("✓ Oracle Instant Client 已初始化")
                
                # 建立連線
                conn_str = self.config.get_connection_string()
                connection = oracledb.connect(conn_str)
                
                self.introspector = OracleIntrospector(connection)
                logger.info(f"✓ 已連接到 Oracle 數據庫")
                logger.info(f"  主機: {self.config.host}:{self.config.port}")
                logger.info(f"  用戶: {self.config.username}")
                logger.info(f"  Schema: {self.introspector.schema}")
                return True
            else:
                logger.error(f"✗ 暫不支持的數據庫類型: {self.config.db_type}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 連接數據庫失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def discover_schema(self, max_tables: int = None) -> bool:
        """探測資料庫 Schema"""
        if not self.introspector:
            logger.error("✗ 未連接到數據庫")
            return False
        
        try:
            logger.info("\n探測資料庫 Schema 中...")
            
            schema = self.introspector.schema
            
            # 取得所有表格中繼資料
            all_metadata = self.introspector.get_all_tables_metadata(schema, max_tables)
            
            if not all_metadata:
                logger.warning("✗ 未找到任何表格")
                return False
            
            logger.info(f"✓ 找到 {len(all_metadata)} 個表格")
            
            # 準備表格列表
            tables_list = []
            for table_metadata in all_metadata:
                columns_list = []
                for column in table_metadata.columns:
                    # 轉換數據型別到系統標準型別
                    if self.config.db_type == DatabaseType.ORACLE:
                        core_type = TypeMapper.map_oracle_type(column.data_type)
                    elif self.config.db_type == DatabaseType.POSTGRESQL:
                        core_type = TypeMapper.map_postgresql_type(column.data_type)
                    elif self.config.db_type == DatabaseType.SQLITE:
                        core_type = TypeMapper.map_sqlite_type(column.data_type)
                    else:
                        core_type = CoreDataType.UNKNOWN
                    
                    columns_list.append({
                        "name": column.column_name,
                        "original_type": column.data_type,
                        "core_type": core_type.value,
                        "nullable": column.nullable,
                        "comment": column.comment,
                        "max_length": column.max_length,
                        "is_primary_key": column.is_primary_key,
                        "is_indexed": column.is_indexed
                    })
                
                tables_list.append({
                    "table_name": table_metadata.table_name,
                    "comment": table_metadata.table_comment,
                    "row_count": table_metadata.row_count,
                    "columns": columns_list
                })
            
            # 簡化的資料字典結構（不使用 DataDictionary 類）
            self.data_dictionary = {
                "schema_name": schema,
                "database_type": self.config.db_type.value,
                "discovered_at": datetime.now().isoformat(),
                "tables": {}
            }
            
            for table_dict in tables_list:
                self.data_dictionary["tables"][table_dict["table_name"]] = table_dict
            
            logger.info(f"✓ 資料字典已構建 ({len(self.data_dictionary['tables'])} 個表格)")
            return True
            
        except Exception as e:
            logger.error(f"✗ 探測 Schema 失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def perform_semantic_alignment(self, confidence_threshold: float = 0.5) -> bool:
        """執行 LLM 語意對齄"""
        if not self.data_dictionary:
            logger.error("✗ 資料字典未初始化")
            return False
        
        if not LLM_AVAILABLE:
            logger.warning("⊘ LLM 模組不可用，跳過語意對齄")
            return False
        
        try:
            logger.info("\n初始化 LLM 語意對齄器...")
            self.aligner = OpenAISemanticAligner()
            logger.info("✓ LLM 對齄器已初始化")
            
            logger.info("\n執行 LLM 語意對齄...")
            
            # 統計信息
            tables = self.data_dictionary.get("tables", {})
            total_tables = len(tables)
            aligned_tables = 0
            aligned_columns = 0
            
            # 遍歷所有表格和欄位進行對齄
            for table_idx, (table_name, table_data) in enumerate(tables.items(), 1):
                logger.info(f"  [{table_idx}/{total_tables}] 對齄表格: {table_name}")
                
                # 準備欄位信息
                columns = []
                for col in table_data.get("columns", []):
                    columns.append({
                        "name": col["name"],
                        "type": col["original_type"],
                        "comment": col.get("comment", "")
                    })
                
                if not columns:
                    continue
                
                # 使用 LLM 對齄整個表格
                try:
                    suggestions = self.aligner.align_table(table_name, columns)
                    
                    # 將建議添加到資料字典
                    suggestions_added = 0
                    for i, suggestion in enumerate(suggestions):
                        if i < len(table_data["columns"]):
                            table_data["columns"][i]["semantic_mapping"] = {
                                "mapped_entity": suggestion.suggested_entity,
                                "mapped_field": suggestion.suggested_entity_field,
                                "confidence": suggestion.confidence,
                                "reasoning": suggestion.reasoning,
                                "alternatives": suggestion.alternative_suggestions or []
                            }
                            
                            if suggestion.confidence >= confidence_threshold:
                                aligned_columns += 1
                                suggestions_added += 1
                    
                    if suggestions_added > 0:
                        aligned_tables += 1
                        logger.info(f"    ✓ 對齄了 {suggestions_added}/{len(columns)} 個欄位")
                        
                except Exception as e:
                    logger.warning(f"    ⊘ 表格對齄失敗: {e}")
            
            total_columns = sum(len(t.get("columns", [])) for t in tables.values())
            alignment_rate = (aligned_columns / total_columns * 100) if total_columns > 0 else 0
            
            logger.info(f"\n✓ 語意對齄完成")
            logger.info(f"  - 對齄的表格: {aligned_tables}/{total_tables}")
            logger.info(f"  - 對齄的欄位: {aligned_columns}")
            logger.info(f"  - 對齄率: {alignment_rate:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ LLM 語意對齄失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_output(self) -> Dict[str, str]:
        """生成輸出檔案"""
        if not self.data_dictionary:
            logger.error("✗ 資料字典未初始化")
            return {}
        
        try:
            # 建立輸出目錄
            self.output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_files = {}
            
            # 1. 生成 JSON 格式的數據字典
            logger.info("\n生成輸出檔案...")
            json_file = self.output_dir / f"data_dictionary_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data_dictionary, f, ensure_ascii=False, indent=2)
            output_files["json"] = str(json_file)
            logger.info(f"  ✓ JSON: {json_file.name}")
            
            # 2. 生成 YAML 格式的數據字典
            yaml_file = self.output_dir / f"data_dictionary_{timestamp}.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.data_dictionary, f, allow_unicode=True, default_flow_style=False)
            output_files["yaml"] = str(yaml_file)
            logger.info(f"  ✓ YAML: {yaml_file.name}")
            
            # 3. 生成對齄報告（如果有映射建議）
            tables = self.data_dictionary.get("tables", {})
            has_mappings = any("semantic_mapping" in col for table in tables.values() 
                             for col in table.get("columns", []))
            
            if has_mappings:
                report_file = self.output_dir / f"alignment_report_{timestamp}.json"
                
                alignment_report = {
                    "generated_at": datetime.now().isoformat(),
                    "schema": self.data_dictionary.get("schema_name"),
                    "database_type": self.data_dictionary.get("database_type"),
                    "total_tables": len(tables),
                    "mappings": []
                }
                
                # 統計信息
                high_confidence = 0
                medium_confidence = 0
                low_confidence = 0
                
                for table_name, table_data in tables.items():
                    for col in table_data.get("columns", []):
                        if "semantic_mapping" in col:
                            mapping = col["semantic_mapping"]
                            confidence = mapping["confidence"]
                            
                            # 統計信心度分布
                            if confidence >= 0.8:
                                high_confidence += 1
                            elif confidence >= 0.6:
                                medium_confidence += 1
                            else:
                                low_confidence += 1
                            
                            alignment_report["mappings"].append({
                                "table": table_name,
                                "column": col["name"],
                                "original_type": col["original_type"],
                                "core_type": col["core_type"],
                                "comment": col.get("comment", ""),
                                "mapped_entity": mapping["mapped_entity"],
                                "mapped_field": mapping["mapped_field"],
                                "confidence": confidence,
                                "reasoning": mapping["reasoning"],
                                "alternatives": mapping.get("alternatives", [])
                            })
                
                # 添加統計信息
                total_mappings = high_confidence + medium_confidence + low_confidence
                alignment_report["statistics"] = {
                    "total_mapped_columns": total_mappings,
                    "high_confidence": high_confidence,
                    "medium_confidence": medium_confidence,
                    "low_confidence": low_confidence,
                    "overall_accuracy_rate": f"{(high_confidence + medium_confidence) / total_mappings * 100:.1f}%" if total_mappings > 0 else "N/A"
                }
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(alignment_report, f, ensure_ascii=False, indent=2)
                output_files["report"] = str(report_file)
                logger.info(f"  ✓ 報告: {report_file.name}")
                
                # 列印統計信息
                logger.info(f"\n對齄統計:")
                logger.info(f"  - 高信心度 (≥80%): {high_confidence}")
                logger.info(f"  - 中信心度 (60-79%): {medium_confidence}")
                logger.info(f"  - 低信心度 (<60%): {low_confidence}")
                logger.info(f"  - 準確率: {alignment_report['statistics']['overall_accuracy_rate']}")
            
            return output_files
            
        except Exception as e:
            logger.error(f"✗ 生成輸出檔案失敗: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def run_full_pipeline(self, max_tables: int = None, use_llm: bool = True) -> bool:
        """執行完整的探測和對齄管道"""
        logger.info("=" * 80)
        logger.info("動態資料字典探測系統")
        logger.info("=" * 80)
        
        try:
            # 第 1 步：連接數據庫
            logger.info("\n[步驟 1/4] 連接到 Oracle 數據庫...")
            if not self.connect_to_database():
                return False
            
            # 第 2 步：探測 Schema
            logger.info("\n[步驟 2/4] 探測資料庫 Schema...")
            if not self.discover_schema(max_tables):
                return False
            
            # 第 3 步：LLM 語意對齄（可選）
            if use_llm and LLM_AVAILABLE:
                logger.info("\n[步驟 3/4] 執行 LLM 語意對齄...")
                self.perform_semantic_alignment()
            else:
                logger.info("\n[步驟 3/4] 跳過 LLM 語意對齄")
            
            # 第 4 步：生成輸出
            logger.info("\n[步驟 4/4] 生成輸出檔案...")
            output_files = self.generate_output()
            
            if output_files:
                logger.info("\n" + "=" * 80)
                logger.info("探測完成！")
                logger.info("=" * 80)
                logger.info(f"\n輸出目錄: {self.output_dir.absolute()}\n")
                for format_type, file_path in output_files.items():
                    logger.info(f"  ✓ {format_type.upper()}: {Path(file_path).name}")
                logger.info("")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"✗ 管道執行失敗: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="動態資料字典探測系統 - 自動探測 Oracle Schema 並進行 LLM 語意對齄"
    )
    parser.add_argument(
        "--max-tables", 
        type=int, 
        help="最多探測的表格數量（用於測試）"
    )
    parser.add_argument(
        "--no-llm", 
        action="store_true", 
        help="禁用 LLM 語意對齄"
    )
    parser.add_argument(
        "--output-dir", 
        default="schema_output", 
        help="輸出目錄（預設: schema_output）"
    )
    
    args = parser.parse_args()
    
    generator = SchemaDictionaryGenerator()
    if args.output_dir:
        generator.output_dir = Path(args.output_dir)
    
    success = generator.run_full_pipeline(
        max_tables=args.max_tables,
        use_llm=not args.no_llm
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
