"""
LLM 語意對齊實現 (LLM Semantic Alignment Implementation)
使用 LLM 智能地將資料庫欄位對應到系統核心實體
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import re

from dotenv import load_dotenv
import os

# 嘗試導入 LangChain，如果不可用則使用直接 API 調用
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    try:
        import openai
    except ImportError:
        openai = None

from .semantic_aligner import MappingSuggestion, LLMSemanticAligner
from .core_entities import CoreEntityCatalog, EntityType

logger = logging.getLogger(__name__)
load_dotenv()


class OpenAISemanticAligner(LLMSemanticAligner):
    """使用 OpenAI API 的語意對齊器"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        初始化 OpenAI 語意對齊器
        
        Args:
            api_key: OpenAI API 金鑰
            model: 使用的模型名稱
        """
        super().__init__(api_key)
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("OpenAI API 金鑰未設定")
        
        # 初始化 LangChain（如果可用）或 OpenAI 直接 API
        if LANGCHAIN_AVAILABLE:
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                model=self.model,
                temperature=0.3
            )
        else:
            import openai as openai_module
            openai_module.api_key = self.api_key
            self.llm = None
        
        # 建立核心實體目錄
        self.entity_catalog = CoreEntityCatalog()
        self.core_entities = self._build_entity_definitions()
    
    def _build_entity_definitions(self) -> Dict[str, Any]:
        """建立核心實體定義字典"""
        entities = {}
        
        # 建立各個核心實體
        patient_entity = self.entity_catalog.create_patient_entity()
        visit_entity = self.entity_catalog.create_visit_entity()
        medication_entity = self.entity_catalog.create_medication_entity()
        nursing_record_entity = self.entity_catalog.create_nursing_record_entity()
        lab_result_entity = self.entity_catalog.create_lab_result_entity()
        vital_sign_entity = self.entity_catalog.create_vital_sign_entity()
        
        for entity in [patient_entity, visit_entity, medication_entity, 
                       nursing_record_entity, lab_result_entity, vital_sign_entity]:
            entities[entity.entity_type.value] = entity.to_dict()
        
        return entities
    
    def _build_system_prompt(self) -> str:
        """建立 LLM 系統提示"""
        entities_json = json.dumps(self.core_entities, ensure_ascii=False, indent=2)
        
        return f"""你是一個資深的醫療數據工程師和語意對齊專家。

你的任務是分析資料庫中的未知欄位，並將其映射到系統標準的核心實體和欄位。

## 系統標準核心實體定義

```json
{entities_json}
```

## 映射規則

1. 分析欄位名稱的命名模式（如 PT_ 前綴表示 Patient）
2. 根據欄位註解/描述推斷其含義
3. 根據欄位數據型別確定合適的映射
4. 優先匹配完全一致的別名，然後考慮部分匹配
5. 為每個映射提供信心度（0.0-1.0）和推理說明

## 常見醫療欄位規律

- PT_, PATIENT_, PH_ 開頭 → Patient 實體
- VIS_, VISIT_, ADM_ 開頭 → Visit 實體
- MED_, MEDICATION_, RX_ 開頭 → Medication 實體
- LAB_, RESULT_, TEST_ 開頭 → LabResult 實體
- VITAL_, VS_, SIGN_ 開頭 → VitalSign 實體
- NUR_, NURSING_, NOTE_ 開頭 → NursingRecord 實體

## 輸出格式

返回 JSON 物件包含：
{{
    "source_column": "原始欄位名",
    "source_data_type": "原始數據型別",
    "source_comment": "欄位註解/描述",
    "suggested_entity_field": "建議的標準欄位名",
    "suggested_entity": "建議的實體類型",
    "confidence": 0.85,
    "reasoning": "詳細的推理說明",
    "alternative_suggestions": [
        {{"field_name": "備選欄位名", "confidence": 0.6}},
        ...
    ]
}}

確保輸出是有效的 JSON，可以直接解析。"""
    
    def align_column(self, 
                    column_name: str, 
                    data_type: str, 
                    comment: str = None) -> Optional[MappingSuggestion]:
        """
        使用 LLM 對齊單個欄位
        
        Args:
            column_name: 欄位名稱
            data_type: 數據型別
            comment: 欄位註解/描述
            
        Returns:
            MappingSuggestion 物件或 None
        """
        try:
            user_message = f"""請分析並映射以下資料庫欄位到系統標準實體：

欄位名稱: {column_name}
數據型別: {data_type}
欄位註解: {comment or "無"}

請提供映射建議。"""
            
            response = self._call_llm(user_message)
            
            if response:
                # 解析 LLM 回應
                suggestion_dict = self._parse_json_response(response)
                
                # 驗證和構建 MappingSuggestion
                if suggestion_dict:
                    return self._build_suggestion(
                        column_name,
                        data_type,
                        comment,
                        suggestion_dict
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"LLM 對齊欄位失敗 {column_name}: {e}")
            return None
    
    def align_table(self, 
                   table_name: str, 
                   columns: List[Dict[str, Any]]) -> List[MappingSuggestion]:
        """
        對齊整個表格的所有欄位
        
        Args:
            table_name: 表格名稱
            columns: 欄位列表 [{"name": "...", "type": "...", "comment": "..."}, ...]
            
        Returns:
            MappingSuggestion 列表
        """
        suggestions = []
        
        try:
            # 構建批量對齊的提示
            columns_text = "\n".join([
                f"  - {col['name']} ({col.get('type', 'Unknown')}): {col.get('comment', '無')}"
                for col in columns
            ])
            
            user_message = f"""請分析並映射表格 '{table_name}' 的所有欄位到系統標準實體：

表格欄位列表：
{columns_text}

請為每個欄位提供映射建議。返回一個 JSON 數組，每個元素包含映射資訊。"""
            
            response = self._call_llm(user_message)
            
            if response:
                # 嘗試解析為 JSON 陣列
                suggestions_data = self._parse_json_response(response, expect_array=True)
                
                if isinstance(suggestions_data, list):
                    for item in suggestions_data:
                        if isinstance(item, dict):
                            suggestion = self._build_suggestion(
                                item.get("source_column", ""),
                                item.get("source_data_type", ""),
                                item.get("source_comment", ""),
                                item
                            )
                            if suggestion:
                                suggestions.append(suggestion)
                elif isinstance(suggestions_data, dict):
                    # 單個物件響應
                    suggestion = self._build_suggestion(
                        columns[0]["name"] if columns else "",
                        columns[0].get("type", "") if columns else "",
                        columns[0].get("comment", "") if columns else "",
                        suggestions_data
                    )
                    if suggestion:
                        suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"LLM 對齊表格失敗 {table_name}: {e}")
            return suggestions
    
    def _call_llm(self, user_message: str) -> Optional[str]:
        """呼叫 LLM API"""
        try:
            if LANGCHAIN_AVAILABLE and self.llm:
                # 使用 LangChain
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._build_system_prompt()),
                    ("human", user_message)
                ])
                chain = prompt | self.llm
                response = chain.invoke({})
                return response.content if hasattr(response, 'content') else str(response)
            else:
                # 使用直接 OpenAI API
                import openai
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._build_system_prompt()},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"LLM API 呼叫失敗: {e}")
            return None
    
    def _parse_json_response(self, response: str, expect_array: bool = False) -> Optional[Dict[str, Any]]:
        """解析 LLM JSON 回應"""
        try:
            # 嘗試直接解析
            if expect_array:
                return json.loads(response)
            
            # 查找 JSON 物件
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            
            # 嘗試整個回應
            return json.loads(response)
            
        except Exception as e:
            logger.warning(f"JSON 解析失敗: {e}, 回應: {response[:100]}")
            return None
    
    def _build_suggestion(self, 
                         source_column: str,
                         source_data_type: str,
                         source_comment: str,
                         suggestion_dict: Dict[str, Any]) -> Optional[MappingSuggestion]:
        """從 LLM 回應構建 MappingSuggestion"""
        try:
            return MappingSuggestion(
                source_column=source_column,
                source_data_type=source_data_type,
                source_comment=source_comment or "",
                suggested_entity_field=suggestion_dict.get("suggested_entity_field", ""),
                suggested_entity=suggestion_dict.get("suggested_entity", ""),
                confidence=float(suggestion_dict.get("confidence", 0.0)),
                reasoning=suggestion_dict.get("reasoning", ""),
                alternative_suggestions=suggestion_dict.get("alternative_suggestions", [])
            )
        except Exception as e:
            logger.error(f"構建建議失敗: {e}")
            return None
