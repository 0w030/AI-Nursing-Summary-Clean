"""
Schema Discovery 模組初始化
動態資料字典探測器主要 API
"""

from .introspection import (
    DatabaseIntrospector,
    DatabaseType,
    ColumnMetadata,
    TableMetadata,
    create_introspector,
    OracleIntrospector,
    PostgreSQLIntrospector,
    SQLiteIntrospector
)

from .data_dictionary import (
    DataDictionary,
    StandardizedTable,
    StandardizedColumn,
    CoreDataType,
    TypeMapper
)

from .core_entities import (
    CoreEntity,
    EntityType,
    EntityField,
    CoreEntityCatalog
)

from .semantic_aligner import (
    LLMSemanticAligner,
    MappingSuggestion,
    create_semantic_aligner,
    OpenAISemanticAligner,
    LocalRulesSemanticAligner
)

from .generator import (
    SchemaDictionaryGenerator,
    example_usage_oracle,
    example_usage_sqlite
)

__all__ = [
    # Introspection
    "DatabaseIntrospector",
    "DatabaseType",
    "ColumnMetadata",
    "TableMetadata",
    "create_introspector",
    "OracleIntrospector",
    "PostgreSQLIntrospector",
    "SQLiteIntrospector",
    
    # Data Dictionary
    "DataDictionary",
    "StandardizedTable",
    "StandardizedColumn",
    "CoreDataType",
    "TypeMapper",
    
    # Core Entities
    "CoreEntity",
    "EntityType",
    "EntityField",
    "CoreEntityCatalog",
    
    # Semantic Alignment
    "LLMSemanticAligner",
    "MappingSuggestion",
    "create_semantic_aligner",
    "OpenAISemanticAligner",
    "LocalRulesSemanticAligner",
    
    # Generator
    "SchemaDictionaryGenerator",
    "example_usage_oracle",
    "example_usage_sqlite"
]
