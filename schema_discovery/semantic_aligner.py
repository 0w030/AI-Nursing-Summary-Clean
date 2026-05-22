"""
LLM 語意對齐模組 (LLM Semantic Alignment Module)
使用 LLM 智能地將未知欄位對應到系統標準實體
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import re

logger = logging.getLogger(__name__)


@dataclass
class MappingSuggestion:
    """LLM 映射建議"""
    source_column: str
    source_data_type: str
    source_comment: str
    suggested_entity_field: str  # 建議的標準欄位
    suggested_entity: str  # 建議的實體類型
    confidence: float  # 信心度 0-1
    reasoning: str  # AI 的推理說明
    alternative_suggestions: List[Tuple[str, float]] = None  # 備選建議 [(field_name, confidence), ...]
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "source_column": self.source_column,
            "source_data_type": self.source_data_type,
            "source_comment": self.source_comment,
            "suggested_entity_field": self.suggested_entity_field,
            "suggested_entity": self.suggested_entity,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternative_suggestions": self.alternative_suggestions or []
        }


class LLMSemanticAligner(ABC):
    """LLM 語意對齐基類"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 LLM 對齁器
        Args:
            api_key: API 金鑰（如適用）
        """
        self.api_key = api_key
    
    @abstractmethod
    def align_column(
        self, 
        column_name: str,
        data_type: str,
        comment: str,
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None
    ) -> MappingSuggestion:
        """
        對齁單個欄位到標準實體
        
        Args:
            column_name: 原始欄位名
            data_type: 原始資料型別
            comment: 欄位註解
            table_name: 表格名稱
            table_comment: 表格註解
            core_entities_context: 核心實體定義的上下文
        
        Returns:
            MappingSuggestion 物件
        """
        pass
    
    @abstractmethod
    def align_table(
        self,
        table_name: str,
        table_comment: str,
        column_descriptions: List[Dict[str, str]],
        core_entities_context: str = None
    ) -> Tuple[str, float, str]:
        """
        對齁資料表到標準實體
        
        Args:
            table_name: 表格名稱
            table_comment: 表格註解
            column_descriptions: 欄位描述列表
            core_entities_context: 核心實體定義的上下文
        
        Returns:
            (suggested_entity_type, confidence, reasoning)
        """
        pass
    
    @abstractmethod
    def batch_align_columns(
        self,
        columns: List[Dict[str, str]],
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None
    ) -> List[MappingSuggestion]:
        """批量對齁多個欄位"""
        pass


class OpenAISemanticAligner(LLMSemanticAligner):
    """基於 OpenAI API 的語意對齁器"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        初始化 OpenAI 對齁器
        
        Args:
            api_key: OpenAI API 金鑰
            model: 使用的模型（默認 gpt-4）
        """
        super().__init__(api_key)
        self.model = model
        try:
            import openai
            openai.api_key = api_key
            self.openai = openai
        except ImportError:
            raise ImportError("請安裝 openai 套件: pip install openai")
    
    def _create_system_prompt(self, core_entities_context: str) -> str:
        """建立系統提示詞 - 數據特徵優先分析"""
        return f"""你是一個資料庫架構分析專家。
你的任務是根據資料庫欄位名稱、資料型別、註解、以及 **數據特徵**（樣本值、數值範圍），
將其對應到預定義的醫療系統標準實體及欄位。

核心實體定義：
{core_entities_context}

**三層分析規則（按優先級）：**

**規則1：數據特徵優先分析**
- 檢查樣本值：M/F → 性別, A/B/O/AB → 血型
- 檢查數值範圍：
  * 35~40°C → 體溫 (body_temperature)
  * 80~120 mmHg → 收縮壓 (systolic_bp)
  * 40~80 mmHg → 舒張壓 (diastolic_bp)
  * 60~100 bpm → 心率 (heart_rate)
  * 90~100 → 血氧飽和度 (SpO2)
  * 12~20 次/分 → 呼吸速率 (respiratory_rate)

**規則2：上下文關聯分析**
- 如果表格包含：體溫+收縮壓+舒張壓 → 對應「病患生理監測表」
- 如果表格包含：血紅蛋白+白血球 → 對應「檢驗結果表」
- 如果表格包含：診斷代碼+診斷名稱 → 對應「診斷記錄表」

**規則3：名稱與註解匹配**
- 分析欄位名稱中的含義（中文/英文）
- 參考資料型別是否與建議的標準欄位相符
- 利用欄位註解進一步確認意義

**重要說明：**
- 始終優先使用 **數據特徵**（樣本值和範圍）來推斷欄位含義
- 如果數據特徵明確指向某個標準欄位，應該高度確信（confidence ≥ 0.85）
- 如果無法確定，給出信心度較低的建議

**你必須以嚴格的 JSON 格式回答：**
{{
    "db_table_name": "原始表格名稱",
    "mapped_table_name": "對應的中文表格名稱",
    "table_reasoning": "表格層級的對應理由（基於包含的欄位類型）",
    "columns": [
        {{
            "db_column_name": "原始欄位名",
            "mapped_column_name": "標準欄位名",
            "confidence": 0.95,
            "reasoning": "具體推理證據（包括數據特徵分析）"
        }},
        ...
    ]
}}"""
    
    def _create_column_prompt(
        self,
        column_name: str,
        data_type: str,
        comment: str,
        table_name: str = None,
        table_comment: str = None,
        sample_values: Optional[List[str]] = None,
        numeric_min: Optional[float] = None,
        numeric_max: Optional[float] = None
    ) -> str:
        """建立欄位映射的使用者提示詞 - 包含數據特徵"""
        prompt = f"""請對以下資料庫欄位進行語意對齁：

欄位名稱: {column_name}
資料型別: {data_type}
欄位註解: {comment if comment else "無"}
"""
        if table_name:
            prompt += f"所屬表格: {table_name}\n"
        if table_comment:
            prompt += f"表格說明: {table_comment}\n"
        
        # 添加數據特徵信息
        if sample_values:
            prompt += f"樣本值: {', '.join(sample_values)}\n"
        if numeric_min is not None or numeric_max is not None:
            min_str = str(numeric_min) if numeric_min is not None else "?"
            max_str = str(numeric_max) if numeric_max is not None else "?"
            prompt += f"數值範圍: {min_str} ~ {max_str}\n"
        
        prompt += "\n請根據數據特徵優先進行分析，並回傳 JSON 格式的對應建議。"
        return prompt
    
    def align_column(
        self,
        column_name: str,
        data_type: str,
        comment: str,
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None,
        sample_values: Optional[List[str]] = None,
        numeric_min: Optional[float] = None,
        numeric_max: Optional[float] = None
    ) -> MappingSuggestion:
        """使用 OpenAI 對齁單個欄位 - 包含數據特徵"""
        try:
            if not core_entities_context:
                core_entities_context = self._get_default_entities_context()
            
            system_prompt = self._create_system_prompt(core_entities_context)
            user_prompt = self._create_column_prompt(
                column_name, data_type, comment, table_name, table_comment,
                sample_values, numeric_min, numeric_max
            )
            
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            # 支持新的結構化格式：從 columns 陣列中提取第一個欄位的映射
            if "columns" in result_json and result_json["columns"]:
                col_mapping = result_json["columns"][0]
                return MappingSuggestion(
                    source_column=column_name,
                    source_data_type=data_type,
                    source_comment=comment or "",
                    suggested_entity_field=col_mapping.get("mapped_column_name"),
                    suggested_entity=result_json.get("mapped_table_name", "Unknown"),
                    confidence=float(col_mapping.get("confidence", 0)),
                    reasoning=col_mapping.get("reasoning", ""),
                    alternative_suggestions=[
                        (alt["field"], alt["confidence"]) 
                        for alt in result_json.get("alternative_suggestions", [])
                    ]
                )
            else:
                # 向後兼容舊格式
                return MappingSuggestion(
                    source_column=column_name,
                    source_data_type=data_type,
                    source_comment=comment or "",
                    suggested_entity_field=result_json.get("suggested_entity_field"),
                    suggested_entity=result_json.get("suggested_entity"),
                    confidence=float(result_json.get("confidence", 0)),
                    reasoning=result_json.get("reasoning", ""),
                    alternative_suggestions=[
                        (alt["field"], alt["confidence"]) 
                        for alt in result_json.get("alternative_suggestions", [])
                    ]
                )
        except Exception as e:
            logger.error(f"OpenAI 對齁失敗 [{column_name}]: {e}")
            return MappingSuggestion(
                source_column=column_name,
                source_data_type=data_type,
                source_comment=comment or "",
                suggested_entity_field=None,
                suggested_entity=None,
                confidence=0,
                reasoning=f"Error: {str(e)}"
            )
    
    def align_table(
        self,
        table_name: str,
        table_comment: str,
        column_descriptions: List[Dict[str, str]],
        core_entities_context: str = None
    ) -> Tuple[str, float, str]:
        """使用 OpenAI 對齁資料表 - 數據特徵優先"""
        try:
            if not core_entities_context:
                core_entities_context = self._get_default_entities_context()
            
            # 構建欄位描述（包含數據特徵）
            columns_text_parts = []
            for col in column_descriptions:
                col_line = f"- {col.get('name', 'unknown')}: {col.get('type', 'unknown')}"
                if col.get('comment'):
                    col_line += f" ({col.get('comment')})"
                
                # 添加數據特徵
                if col.get('sample_values'):
                    col_line += f" [樣本: {', '.join(col.get('sample_values'))}]"
                if col.get('numeric_min') is not None or col.get('numeric_max') is not None:
                    min_val = col.get('numeric_min', '?')
                    max_val = col.get('numeric_max', '?')
                    col_line += f" [範圍: {min_val}~{max_val}]"
                
                columns_text_parts.append(col_line)
            
            columns_text = "\n".join(columns_text_parts)
            
            prompt = f"""請分析以下資料表並對應到醫療系統的標準實體。
**重點：優先分析數據特徵（樣本值和數值範圍）**：

表格名稱: {table_name}
表格說明: {table_comment if table_comment else "無"}

欄位列表:
{columns_text}

請判斷這個表格最可能對應哪個核心實體，並分析表格中所有欄位的對應情況。
回傳嚴格的 JSON 格式：
{{
    "db_table_name": "{table_name}",
    "mapped_table_name": "對應的標準表格名稱",
    "table_reasoning": "表格層級的對應理由（基於整體欄位類型和數據特徵）",
    "columns": [
        {{
            "db_column_name": "原始欄位名",
            "mapped_column_name": "標準欄位名",
            "confidence": 0.9,
            "reasoning": "對應理由（包括數據特徵分析）"
        }},
        ...
    ]
}}"""
            
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._create_system_prompt(core_entities_context)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            # 計算表格級別的信心度（基於所有欄位的平均）
            columns = result_json.get("columns", [])
            if columns:
                avg_confidence = sum(col.get("confidence", 0) for col in columns) / len(columns)
            else:
                avg_confidence = float(result_json.get("confidence", 0))
            
            return (
                result_json.get("mapped_table_name"),
                avg_confidence,
                result_json.get("table_reasoning", "")
            )
        except Exception as e:
            logger.error(f"表格對齁失敗 [{table_name}]: {e}")
            return None, 0, str(e)
    
    def batch_align_columns(
        self,
        columns: List[Dict[str, str]],
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None
    ) -> List[MappingSuggestion]:
        """批量對齁欄位 - 包含數據特徵"""
        results = []
        for col in columns:
            suggestion = self.align_column(
                column_name=col.get("name", "unknown"),
                data_type=col.get("type", "unknown"),
                comment=col.get("comment", ""),
                table_name=table_name,
                table_comment=table_comment,
                core_entities_context=core_entities_context,
                sample_values=col.get("sample_values"),
                numeric_min=col.get("numeric_min"),
                numeric_max=col.get("numeric_max")
            )
            results.append(suggestion)
        return results
    
    @staticmethod
    def _get_default_entities_context() -> str:
        """取得預設的核心實體上下文"""
        from .core_entities import CoreEntityCatalog
        entities = CoreEntityCatalog.get_all_entities()
        context_lines = []
        for entity in entities:
            context_lines.append(f"\n【{entity.display_name}】 ({entity.entity_type.value})")
            context_lines.append(f"說明: {entity.description}")
            context_lines.append("標準欄位:")
            for field in entity.fields:
                context_lines.append(f"  - {field.field_name}: {field.display_name} ({field.data_type})")
                if field.aliases:
                    context_lines.append(f"    別名: {', '.join(field.aliases)}")
        return "\n".join(context_lines)


class LocalRulesSemanticAligner(LLMSemanticAligner):
    """
    基於本地規則的語意對齁器（無需 API）
    使用模式匹配、關鍵字搜尋、編輯距離等啟發式方法
    """
    
    def __init__(self):
        """初始化本地規則對齁器"""
        super().__init__()
        from .core_entities import CoreEntityCatalog
        self.entities = CoreEntityCatalog.get_all_entities()
    
    def align_column(
        self,
        column_name: str,
        data_type: str,
        comment: str,
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None
    ) -> MappingSuggestion:
        """使用本地規則對齁欄位"""
        
        # 組合的搜尋文本
        search_text = f"{column_name} {comment or ''} {table_name or ''}".lower()
        
        # 尋找所有可能的匹配
        candidates = []
        
        for entity in self.entities:
            for field in entity.fields:
                confidence = self._calculate_match_score(
                    search_text, field, data_type, column_name, comment
                )
                
                if confidence > 0:
                    candidates.append({
                        "entity": entity.entity_type.value,
                        "field": field.field_name,
                        "confidence": confidence,
                        "reasoning": self._generate_reasoning(
                            column_name, data_type, comment, field
                        )
                    })
        
        # 排序並取最佳建議
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        
        if candidates:
            best = candidates[0]
            alternatives = [(c["field"], c["confidence"]) for c in candidates[1:4]]
            
            return MappingSuggestion(
                source_column=column_name,
                source_data_type=data_type,
                source_comment=comment or "",
                suggested_entity_field=best["field"],
                suggested_entity=best["entity"],
                confidence=best["confidence"],
                reasoning=best["reasoning"],
                alternative_suggestions=alternatives
            )
        else:
            return MappingSuggestion(
                source_column=column_name,
                source_data_type=data_type,
                source_comment=comment or "",
                suggested_entity_field=None,
                suggested_entity=None,
                confidence=0,
                reasoning="沒有找到合適的映射"
            )
    
    def _calculate_match_score(
        self,
        search_text: str,
        field,
        data_type: str,
        column_name: str,
        comment: str
    ) -> float:
        """計算匹配分數"""
        score = 0
        
        # 1. 別名精確匹配（最高優先級）
        for alias in field.aliases:
            if alias.lower() == column_name.lower():
                score += 0.9
                return score
        
        # 2. 欄位名稱中的關鍵字匹配
        col_lower = column_name.lower()
        for keyword in field.keywords:
            if keyword.lower() in col_lower:
                score += 0.5
        
        # 3. 註解中的關鍵字匹配
        if comment:
            comment_lower = comment.lower()
            for keyword in field.keywords:
                if keyword.lower() in comment_lower:
                    score += 0.4
        
        # 4. 別名的模糊匹配
        for alias in field.aliases:
            if self._fuzzy_match(column_name.lower(), alias.lower()):
                score += 0.3
        
        # 5. 資料型別驗證（如果不匹配則降低分數）
        expected_type = field.data_type.lower()
        actual_type = data_type.lower()
        if expected_type not in actual_type and actual_type not in expected_type:
            score *= 0.7
        
        return min(score, 1.0)
    
    def _fuzzy_match(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """簡單的模糊匹配"""
        # 檢查是否有重要的子串匹配
        shorter = s1 if len(s1) <= len(s2) else s2
        longer = s2 if shorter == s1 else s1
        
        # 計算編輯距離（簡化版）
        matching_chars = sum(1 for c in shorter if c in longer)
        similarity = matching_chars / len(longer) if longer else 0
        
        return similarity >= threshold
    
    def _generate_reasoning(self, column_name: str, data_type: str, comment: str, field) -> str:
        """生成對應的推理說明"""
        reasons = []
        
        col_lower = column_name.lower()
        for alias in field.aliases:
            if alias.lower() == col_lower:
                reasons.append(f"欄位名完全匹配別名 '{alias}'")
                break
        
        for keyword in field.keywords:
            if keyword.lower() in col_lower:
                reasons.append(f"欄位名包含關鍵字 '{keyword}'")
        
        if comment:
            comment_lower = comment.lower()
            for keyword in field.keywords:
                if keyword.lower() in comment_lower:
                    reasons.append(f"註解包含關鍵字 '{keyword}'")
        
        if not reasons:
            reasons.append("基於名稱和上下文的推測")
        
        return "; ".join(reasons)
    
    def align_table(
        self,
        table_name: str,
        table_comment: str,
        column_descriptions: List[Dict[str, str]],
        core_entities_context: str = None
    ) -> Tuple[str, float, str]:
        """使用規則對齁表格"""
        search_text = f"{table_name} {table_comment or ''}".lower()
        
        best_entity = None
        best_score = 0
        best_reasons = []
        
        for entity in self.entities:
            score = 0
            reasons = []
            
            # 檢查表格名稱
            for pattern in entity.table_keywords:
                if pattern.lower() in search_text:
                    score += 0.6
                    reasons.append(f"表格名包含 '{pattern}'")
            
            # 檢查欄位匹配
            matched_fields = 0
            for col in column_descriptions:
                for field in entity.fields:
                    if field.field_name.lower() in col.get("name", "").lower():
                        matched_fields += 1
            
            if matched_fields > 0:
                score += matched_fields * 0.15
                reasons.append(f"發現 {matched_fields} 個相符的標準欄位")
            
            if score > best_score:
                best_score = score
                best_entity = entity.entity_type.value
                best_reasons = reasons
        
        confidence = min(best_score / 2, 1.0) if best_score > 0 else 0
        reasoning = "; ".join(best_reasons) if best_reasons else "基於表格名稱和欄位組成推測"
        
        return best_entity, confidence, reasoning
    
    def batch_align_columns(
        self,
        columns: List[Dict[str, str]],
        table_name: str = None,
        table_comment: str = None,
        core_entities_context: str = None
    ) -> List[MappingSuggestion]:
        """批量對齁欄位"""
        results = []
        for col in columns:
            suggestion = self.align_column(
                column_name=col.get("name", "unknown"),
                data_type=col.get("type", "unknown"),
                comment=col.get("comment", ""),
                table_name=table_name,
                table_comment=table_comment,
                core_entities_context=core_entities_context
            )
            results.append(suggestion)
        return results


def create_semantic_aligner(use_openai: bool = False, api_key: str = None) -> LLMSemanticAligner:
    """
    工廠函式：建立合適的語意對齁器
    
    Args:
        use_openai: 是否使用 OpenAI API（需要 API 金鑰）
        api_key: OpenAI API 金鑰
    
    Returns:
        LLMSemanticAligner 實例
    """
    if use_openai:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("使用 OpenAI 時必須提供 API 金鑰，請在 .env 中設定 OPENAI_API_KEY")
        return OpenAISemanticAligner(api_key)
    else:
        return LocalRulesSemanticAligner()
