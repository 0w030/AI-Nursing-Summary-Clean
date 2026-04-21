"""
動態資料字典探測器主協調器 (Main Orchestrator)
整合所有模組：資料庫反射、型別轉換、LLM 語意對齁
"""

import logging
from typing import List, Optional
from datetime import datetime
import json

from .introspection import (
    DatabaseIntrospector, 
    create_introspector, 
    DatabaseType, 
    TableMetadata, 
    ColumnMetadata
)
from .data_dictionary import (
    DataDictionary,
    StandardizedTable,
    StandardizedColumn,
    CoreDataType,
    TypeMapper
)
from .core_entities import CoreEntityCatalog
from .semantic_aligner import (
    LLMSemanticAligner,
    create_semantic_aligner,
    MappingSuggestion
)

logger = logging.getLogger(__name__)


class SchemaDictionaryGenerator:
    """
    動態資料字典探測器
    
    主要功能：
    1. 從資料庫連線自動探測 Schema
    2. 轉換為統一的資料字典格式
    3. 使用 LLM 進行語意對齁
    4. 生成完整的 JSON/YAML 資料字典
    """
    
    def __init__(
        self,
        connection,
        db_type: DatabaseType,
        use_llm: bool = False,
        llm_api_key: Optional[str] = None,
        database_name: str = "Unknown"
    ):
        """
        初始化資料字典生成器
        
        Args:
            connection: 資料庫連線物件
            db_type: 資料庫型別
            use_llm: 是否使用 LLM 進行語意對齁
            llm_api_key: LLM API 金鑰（如需）
            database_name: 資料庫名稱
        """
        self.connection = connection
        self.db_type = db_type
        self.database_name = database_name
        self.introspector = create_introspector(connection, db_type)
        
        # 初始化語意對齁器
        try:
            self.semantic_aligner = create_semantic_aligner(
                use_openai=use_llm,
                api_key=llm_api_key
            )
            logger.info(f"語意對齁器初始化成功（使用 {'OpenAI' if use_llm else '本地規則'}）")
        except Exception as e:
            logger.warning(f"語意對齁器初始化失敗，使用本地規則：{e}")
            self.semantic_aligner = create_semantic_aligner(use_openai=False)
    
    def generate_dictionary(
        self,
        schema: Optional[str] = None,
        apply_semantic_alignment: bool = True
    ) -> DataDictionary:
        """
        生成完整的資料字典
        
        Args:
            schema: 資料庫 schema（如適用）
            apply_semantic_alignment: 是否應用 LLM 語意對齁
        
        Returns:
            DataDictionary 物件
        """
        logger.info("=" * 60)
        logger.info("開始生成資料字典")
        logger.info("=" * 60)
        
        # 第一步：從資料庫取得中繼資料
        logger.info(f"第一步：從資料庫反射 Schema...")
        table_metadatas = self.introspector.get_all_tables_metadata(schema)
        logger.info(f"✓ 探測到 {len(table_metadatas)} 個表格")
        
        # 第二步：標準化表格和欄位
        logger.info(f"第二步：標準化資料型別...")
        standardized_tables = []
        for table_metadata in table_metadatas:
            standardized_table = self._standardize_table(table_metadata)
            standardized_tables.append(standardized_table)
        logger.info(f"✓ 已標準化所有 {len(standardized_tables)} 個表格")
        
        # 第三步：應用 LLM 語意對齁（可選）
        if apply_semantic_alignment:
            logger.info(f"第三步：應用 LLM 語意對齁...")
            for table in standardized_tables:
                self._align_table_semantics(table)
            logger.info(f"✓ 語意對齁完成")
        
        # 第四步：建立資料字典物件
        logger.info(f"第四步：建立資料字典物件...")
        data_dict = DataDictionary(
            database_name=self.database_name,
            database_type=self.db_type.value,
            timestamp=datetime.now().isoformat(),
            tables=standardized_tables
        )
        
        # 列印統計資訊
        stats = data_dict.get_mapping_statistics()
        logger.info("=" * 60)
        logger.info("資料字典生成完成！統計資訊：")
        logger.info(f"  表格數: {stats['total_tables']}")
        logger.info(f"  欄位總數: {stats['total_columns']}")
        logger.info(f"  已映射欄位: {stats['mapped_columns']}/{stats['total_columns']} ({stats['mapping_rate']:.1%})")
        logger.info(f"  平均信心度: {stats['average_confidence']:.1%}")
        logger.info("=" * 60)
        
        return data_dict
    
    def _standardize_table(self, table_metadata: TableMetadata) -> StandardizedTable:
        """將原始表格中繼資料轉換為標準格式"""
        standardized_columns = [
            self._standardize_column(col) for col in table_metadata.columns
        ]
        
        return StandardizedTable(
            table_name=table_metadata.table_name,
            table_schema=table_metadata.table_schema,
            table_comment=table_metadata.table_comment,
            row_count=table_metadata.row_count,
            columns=standardized_columns
        )
    
    def _standardize_column(self, column: ColumnMetadata) -> StandardizedColumn:
        """將原始欄位中繼資料轉換為標準格式"""
        # 根據資料庫型別進行型別對應
        if self.db_type == DatabaseType.ORACLE:
            core_type = TypeMapper.map_oracle_type(column.data_type)
        elif self.db_type == DatabaseType.POSTGRESQL:
            core_type = TypeMapper.map_postgresql_type(column.data_type)
        elif self.db_type == DatabaseType.SQLITE:
            core_type = TypeMapper.map_sqlite_type(column.data_type)
        else:
            core_type = CoreDataType.UNKNOWN
        
        return StandardizedColumn(
            column_name=column.column_name,
            core_data_type=core_type,
            native_data_type=column.data_type,
            nullable=column.nullable,
            comment=column.comment,
            max_length=column.max_length,
            numeric_precision=column.numeric_precision,
            numeric_scale=column.numeric_scale,
            default_value=column.default_value,
            is_primary_key=column.is_primary_key,
            is_unique=column.is_unique,
            is_indexed=column.is_indexed
        )
    
    def _align_table_semantics(self, table: StandardizedTable):
        """使用 LLM 對齁表格和欄位的語意"""
        
        # 對齁表格本身
        logger.debug(f"正在對齁表格: {table.table_name}")
        
        # 準備欄位描述
        column_descriptions = [
            {
                "name": col.column_name,
                "type": col.core_data_type.value,
                "comment": col.comment or ""
            }
            for col in table.columns
        ]
        
        # 取得表格映射建議
        entity_type, entity_conf, entity_reason = self.semantic_aligner.align_table(
            table_name=table.table_name,
            table_comment=table.table_comment or "",
            column_descriptions=column_descriptions
        )
        
        if entity_type:
            table.entity_mapping = entity_type
            table.entity_confidence = entity_conf
            table.entity_suggestion = entity_reason
            logger.debug(f"  → 表格映射: {entity_type} (信心: {entity_conf:.0%})")
        
        # 對齁表格中的每個欄位
        for col in table.columns:
            suggestion = self.semantic_aligner.align_column(
                column_name=col.column_name,
                data_type=col.native_data_type,
                comment=col.comment or "",
                table_name=table.table_name,
                table_comment=table.table_comment
            )
            
            if suggestion and suggestion.suggested_entity_field:
                col.semantic_mapping = suggestion.suggested_entity_field
                col.semantic_confidence = suggestion.confidence
                col.ai_suggestion = suggestion.reasoning
                
                if suggestion.confidence >= 0.7:
                    logger.debug(f"  ✓ {col.column_name} → {suggestion.suggested_entity_field} ({suggestion.confidence:.0%})")
                elif suggestion.confidence >= 0.4:
                    logger.debug(f"  ~ {col.column_name} → {suggestion.suggested_entity_field} ({suggestion.confidence:.0%})")
                else:
                    logger.debug(f"  ? {col.column_name} → {suggestion.suggested_entity_field} ({suggestion.confidence:.0%})")
    
    def export_to_json(self, data_dict: DataDictionary, filepath: str):
        """匯出資料字典為 JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data_dict.to_json())
        logger.info(f"✓ 資料字典已匯出到: {filepath}")
    
    def export_to_yaml_like(self, data_dict: DataDictionary, filepath: str):
        """匯出資料字典為類似 YAML 的格式"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data_dict.to_yaml_like_string())
        logger.info(f"✓ 資料字典已匯出到: {filepath}")
    
    def get_unmapped_columns_report(self, data_dict: DataDictionary) -> str:
        """取得未映射欄位的報告"""
        unmapped = data_dict.get_unmapped_columns()
        
        if not unmapped:
            return "✓ 所有欄位都已成功映射！"
        
        report_lines = [
            f"⚠️  共有 {len(unmapped)} 個欄位未映射:\n"
        ]
        
        for table_name, col_name, data_type, comment in unmapped:
            report_lines.append(f"  • {table_name}.{col_name}")
            report_lines.append(f"    型別: {data_type}")
            if comment:
                report_lines.append(f"    說明: {comment}")
        
        return "\n".join(report_lines)
    
    def re_align_unmapped_columns(
        self,
        data_dict: DataDictionary,
        use_aggressive_mode: bool = False
    ):
        """
        重新對齁未映射的欄位
        
        Args:
            data_dict: 資料字典物件
            use_aggressive_mode: 是否使用激進模式（降低信心度門檻）
        """
        logger.info("正在重新對齁未映射的欄位...")
        
        realigned_count = 0
        for table in data_dict.tables:
            for col in table.columns:
                if col.semantic_mapping is None:
                    suggestion = self.semantic_aligner.align_column(
                        column_name=col.column_name,
                        data_type=col.native_data_type,
                        comment=col.comment or "",
                        table_name=table.table_name,
                        table_comment=table.table_comment
                    )
                    
                    # 激進模式：接受更低信心度的建議
                    min_confidence = 0.3 if use_aggressive_mode else 0.5
                    
                    if suggestion and suggestion.confidence >= min_confidence:
                        col.semantic_mapping = suggestion.suggested_entity_field
                        col.semantic_confidence = suggestion.confidence
                        col.ai_suggestion = suggestion.reasoning
                        realigned_count += 1
                        logger.info(f"  ✓ {table.table_name}.{col.column_name} → {suggestion.suggested_entity_field}")
        
        logger.info(f"✓ 重新對齁完成，新映射 {realigned_count} 個欄位")
    
    def close(self):
        """關閉資料庫連線"""
        try:
            self.introspector.close()
            logger.info("資料庫連線已關閉")
        except Exception as e:
            logger.error(f"關閉連線時出錯: {e}")


def example_usage_oracle():
    """
    示例：使用 Oracle 資料庫
    """
    try:
        import oracledb
        
        # 建立連線
        connection = oracledb.connect(
            user="your_user",
            password="your_password",
            host="your_host",
            port=1521,
            service_name="your_service"
        )
        
        # 建立生成器
        generator = SchemaDictionaryGenerator(
            connection=connection,
            db_type=DatabaseType.ORACLE,
            use_llm=False,  # 使用本地規則（無需 API）
            database_name="YourOracleDB"
        )
        
        # 生成資料字典
        data_dict = generator.generate_dictionary()
        
        # 匯出結果
        generator.export_to_json(data_dict, "data_dictionary.json")
        generator.export_to_yaml_like(data_dict, "data_dictionary.yaml")
        
        # 檢查未映射的欄位
        print(generator.get_unmapped_columns_report(data_dict))
        
        # 關閉連線
        generator.close()
        
    except Exception as e:
        logger.error(f"執行失敗: {e}")


def example_usage_sqlite():
    """
    示例：使用 SQLite 資料庫
    """
    import sqlite3
    
    # 建立連線
    connection = sqlite3.connect("hospital_database.db")
    
    # 建立生成器
    generator = SchemaDictionaryGenerator(
        connection=connection,
        db_type=DatabaseType.SQLITE,
        use_llm=False,
        database_name="HospitalDB"
    )
    
    # 生成資料字典
    data_dict = generator.generate_dictionary()
    
    # 匯出結果
    generator.export_to_json(data_dict, "data_dictionary.json")
    
    # 列印統計
    stats = data_dict.get_mapping_statistics()
    print(f"\n映射率: {stats['mapping_rate']:.1%}")
    print(f"未映射欄位數: {stats['unmapped_columns']}")
    
    # 重新對齁未映射欄位
    generator.re_align_unmapped_columns(data_dict, use_aggressive_mode=True)
    
    generator.close()
