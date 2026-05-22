"""
核心實體定義和語意對齐映射規則
定義系統標準的核心實體和欄位，用於 AI 語意對齐
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from enum import Enum


class EntityType(Enum):
    """核心實體型別"""
    PATIENT = "Patient"  # 患者
    VISIT = "Visit"  # 就診/住院
    MEDICATION = "Medication"  # 藥物/用藥
    NURSING_RECORD = "NursingRecord"  # 護理紀錄
    LAB_RESULT = "LabResult"  # 檢驗結果
    VITAL_SIGN = "VitalSign"  # 生命徵象
    DIAGNOSIS = "Diagnosis"  # 診斷
    ORDER = "Order"  # 醫囑
    PROCEDURE = "Procedure"  # 手術/處置
    ALLERGY = "Allergy"  # 過敏紀錄


@dataclass
class EntityField:
    """核心實體欄位定義"""
    field_name: str  # 標準欄位名 (e.g., "patient_name_zh")
    display_name: str  # 顯示名稱
    data_type: str  # 資料型別 (String, Integer, DateTime, etc.)
    description: str  # 欄位說明
    required: bool = True  # 是否為必填
    aliases: List[str] = field(default_factory=list)  # 常見別名
    patterns: List[str] = field(default_factory=list)  # 正則表達式模式
    keywords: List[str] = field(default_factory=list)  # 關鍵字搜尋
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            "field_name": self.field_name,
            "display_name": self.display_name,
            "data_type": self.data_type,
            "description": self.description,
            "required": self.required,
            "aliases": self.aliases,
            "patterns": self.patterns,
            "keywords": self.keywords,
        }


@dataclass
class CoreEntity:
    """核心實體定義"""
    entity_type: EntityType
    display_name: str
    description: str
    fields: List[EntityField] = field(default_factory=list)
    table_patterns: List[str] = field(default_factory=list)  # 表格名稱模式
    table_keywords: List[str] = field(default_factory=list)  # 表格關鍵字
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            "entity_type": self.entity_type.value,
            "display_name": self.display_name,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "table_patterns": self.table_patterns,
            "table_keywords": self.table_keywords,
        }
    
    def get_field(self, field_name: str) -> Optional[EntityField]:
        """根據欄位名取得欄位定義"""
        return next((f for f in self.fields if f.field_name == field_name), None)
    
    def get_all_field_names(self) -> Set[str]:
        """取得所有欄位名"""
        return {f.field_name for f in self.fields}
    
    def get_all_aliases(self) -> Set[str]:
        """取得所有別名"""
        aliases = set()
        for field in self.fields:
            aliases.update(field.aliases)
        return aliases


class CoreEntityCatalog:
    """核心實體目錄 - 包含系統所有標準實體定義"""
    
    @staticmethod
    def create_patient_entity() -> CoreEntity:
        """患者實體"""
        return CoreEntity(
            entity_type=EntityType.PATIENT,
            display_name="患者",
            description="患者基本資訊",
            table_patterns=[r"PATIENT", r"PATIENT_\w+", r"PATIENT_PROPS", r"PH_.*", r"PERSON"],
            table_keywords=["patient", "patient_info", "patients", "patient_props", "properties", "props", "人口", "個案", "個人"],
            fields=[
                EntityField(
                    field_name="patient_id",
                    display_name="病歷號",
                    data_type="String",
                    description="患者唯一識別碼（病歷號）",
                    required=True,
                    aliases=["PT_ID", "patient_number", "medical_record_no", 
                             "MRN", "PATIENT_NO", "PT_NO", "個案號"],
                    patterns=[r"PT_ID", r"PATIENT_ID", r"PATID", r"MRN", r"個案號"],
                    keywords=["patient_id", "病歷號", "個案號", "MRN"]
                ),
                EntityField(
                    field_name="patient_name_zh",
                    display_name="患者姓名（中文）",
                    data_type="String",
                    description="患者中文姓名",
                    required=True,
                    aliases=["PT_NAME", "PATIENT_NAME", "NAME_CN", "中文名", 
                             "姓名", "patient_name_cht"],
                    patterns=[r"PT_NAME.*CN", r"NAME_\w*CN", r".*名.*"],
                    keywords=["name", "姓名", "患者名", "patient_name"]
                ),
                EntityField(
                    field_name="patient_name_en",
                    display_name="患者姓名（英文）",
                    data_type="String",
                    description="患者英文姓名",
                    required=False,
                    aliases=["PT_NAME_EN", "PATIENT_NAME_EN", "NAME_EN", "英文名"],
                    patterns=[r"PT_NAME.*EN", r"NAME_\w*EN"],
                    keywords=["english_name", "name_en", "patient_name_en"]
                ),
                EntityField(
                    field_name="national_id",
                    display_name="身分證號",
                    data_type="String",
                    description="身分證號或統一編號",
                    required=False,
                    aliases=["ID_NO", "ID_NUMBER", "IDNO", "身份證", "統編"],
                    patterns=[r"ID_NO", r"IDNO", r"NATIONAL_ID", r"NAID"],
                    keywords=["id_number", "national_id", "身分證", "身份證"]
                ),
                EntityField(
                    field_name="birth_date",
                    display_name="出生日期",
                    data_type="DateTime",
                    description="患者出生日期",
                    required=False,
                    aliases=["DOB", "BIRTH_DAY", "生日", "出生年月日"],
                    patterns=[r"BIRTH", r"DOB", r"生日"],
                    keywords=["birth", "dob", "出生", "生日"]
                ),
                EntityField(
                    field_name="gender",
                    display_name="性別",
                    data_type="String",
                    description="患者性別（M/F 或 1/2）",
                    required=False,
                    aliases=["SEX", "GENDER", "性別"],
                    patterns=[r"GENDER", r"SEX", r"性別"],
                    keywords=["sex", "gender", "male", "female"]
                ),
                EntityField(
                    field_name="phone",
                    display_name="聯絡電話",
                    data_type="String",
                    description="患者聯絡電話",
                    required=False,
                    aliases=["PHONE", "TELEPHONE", "TEL", "電話"],
                    patterns=[r"PHONE", r"TEL", r"PHONE_NO"],
                    keywords=["phone", "telephone", "tel", "電話"]
                ),
                EntityField(
                    field_name="address",
                    display_name="地址",
                    data_type="String",
                    description="患者住址",
                    required=False,
                    aliases=["ADDR", "ADDRESS", "地址"],
                    patterns=[r"ADDRESS", r"ADDR"],
                    keywords=["address", "地址"]
                ),
            ]
        )
    
    @staticmethod
    def create_visit_entity() -> CoreEntity:
        """就診實體"""
        return CoreEntity(
            entity_type=EntityType.VISIT,
            display_name="就診/住院",
            description="患者就診或住院紀錄",
            table_patterns=[r"VISIT", r"ADMISSION", r".*ADMIT.*", r"ENCOUNTER"],
            table_keywords=["visit", "admission", "encounter", "住院", "就診", "掛號"],
            fields=[
                EntityField(
                    field_name="visit_id",
                    display_name="就診號",
                    data_type="String",
                    description="就診唯一識別碼",
                    required=True,
                    aliases=["VISIT_NO", "ENCOUNTER_ID", "ADMISSION_ID", "就診號"],
                    keywords=["visit_id", "visit_no", "encounter_id"]
                ),
                EntityField(
                    field_name="patient_id",
                    display_name="病歷號",
                    data_type="String",
                    description="對應的患者病歷號（外鍵）",
                    required=True,
                    keywords=["patient_id", "pt_id"]
                ),
                EntityField(
                    field_name="admission_date",
                    display_name="入院日期",
                    data_type="DateTime",
                    description="患者入院日期時間",
                    required=True,
                    aliases=["ADMIT_DATE", "ADMIT_DT", "入院日期"],
                    keywords=["admission", "admit", "入院"]
                ),
                EntityField(
                    field_name="discharge_date",
                    display_name="出院日期",
                    data_type="DateTime",
                    description="患者出院日期時間",
                    required=False,
                    aliases=["DISCHARGE_DATE", "DISCHARGE_DT", "出院日期"],
                    keywords=["discharge", "出院"]
                ),
                EntityField(
                    field_name="department",
                    display_name="科別",
                    data_type="String",
                    description="患者所在科別",
                    required=False,
                    aliases=["DEPT", "DEPARTMENT", "科別"],
                    keywords=["department", "dept", "科別"]
                ),
                EntityField(
                    field_name="ward",
                    display_name="病房",
                    data_type="String",
                    description="患者所在病房",
                    required=False,
                    aliases=["WARD_NO", "ROOM", "病房"],
                    keywords=["ward", "room", "病房"]
                ),
                EntityField(
                    field_name="bed",
                    display_name="床號",
                    data_type="String",
                    description="患者床號",
                    required=False,
                    aliases=["BED_NO", "BED", "床號"],
                    keywords=["bed", "bed_no", "床號"]
                ),
            ]
        )
    
    @staticmethod
    def create_nursing_record_entity() -> CoreEntity:
        """護理紀錄實體"""
        return CoreEntity(
            entity_type=EntityType.NURSING_RECORD,
            display_name="護理紀錄",
            description="護理人員的護理紀錄和觀察",
            table_patterns=[r"NURSING", r"RECORD", r"NOTES"],
            table_keywords=["nursing", "record", "notes", "護理紀錄", "護理筆記"],
            fields=[
                EntityField(
                    field_name="record_id",
                    display_name="紀錄編號",
                    data_type="String",
                    description="紀錄唯一編號",
                    required=True,
                    keywords=["record_id", "note_id"]
                ),
                EntityField(
                    field_name="patient_id",
                    display_name="病歷號",
                    data_type="String",
                    description="對應的患者病歷號",
                    required=True,
                    keywords=["patient_id"]
                ),
                EntityField(
                    field_name="record_datetime",
                    display_name="紀錄時間",
                    data_type="DateTime",
                    description="護理紀錄的時間",
                    required=True,
                    aliases=["RECORD_TIME", "NOTE_TIME", "紀錄時間"],
                    keywords=["record_time", "datetime", "紀錄時間"]
                ),
                EntityField(
                    field_name="record_content",
                    display_name="紀錄內容",
                    data_type="String",
                    description="護理紀錄的具體內容",
                    required=True,
                    aliases=["CONTENT", "NOTE", "NOTES", "紀錄內容"],
                    keywords=["content", "note", "紀錄"]
                ),
                EntityField(
                    field_name="nurse_id",
                    display_name="護理人員編號",
                    data_type="String",
                    description="記錄的護理人員編號",
                    required=False,
                    aliases=["NURSE_NO", "STAFF_ID"],
                    keywords=["nurse_id", "staff_id"]
                ),
            ]
        )
    
    @staticmethod
    def create_vital_sign_entity() -> CoreEntity:
        """生命徵象實體"""
        return CoreEntity(
            entity_type=EntityType.VITAL_SIGN,
            display_name="生命徵象",
            description="患者的生理監測數據（心跳、血壓、體溫等）",
            table_patterns=[r"VITAL", r"MONITOR", r".*SIGN.*"],
            table_keywords=["vital", "monitor", "生命徵象", "生理監測"],
            fields=[
                EntityField(
                    field_name="vital_id",
                    display_name="生命徵象紀錄編號",
                    data_type="String",
                    description="生命徵象紀錄唯一編號",
                    required=True,
                    keywords=["vital_id", "sign_id"]
                ),
                EntityField(
                    field_name="patient_id",
                    display_name="病歷號",
                    data_type="String",
                    description="對應的患者病歷號",
                    required=True,
                    keywords=["patient_id"]
                ),
                EntityField(
                    field_name="measurement_datetime",
                    display_name="測量時間",
                    data_type="DateTime",
                    description="生命徵象測量時間",
                    required=True,
                    aliases=["MEASURE_TIME", "VITAL_TIME"],
                    keywords=["measurement", "時間", "measure_time"]
                ),
                EntityField(
                    field_name="heart_rate",
                    display_name="心率",
                    data_type="Float",
                    description="心跳每分鐘次數（bpm）",
                    required=False,
                    aliases=["HR", "PULSE", "心跳"],
                    patterns=[r"HR", r"HEART_RATE", r"心率", r"心跳"],
                    keywords=["heart_rate", "hr", "pulse", "心率"]
                ),
                EntityField(
                    field_name="systolic_bp",
                    display_name="收縮壓",
                    data_type="Float",
                    description="血壓收縮壓（mmHg）",
                    required=False,
                    aliases=["SBP", "SYSTOLIC", "收縮壓"],
                    keywords=["systolic", "sbp", "收縮壓"]
                ),
                EntityField(
                    field_name="diastolic_bp",
                    display_name="舒張壓",
                    data_type="Float",
                    description="血壓舒張壓（mmHg）",
                    required=False,
                    aliases=["DBP", "DIASTOLIC", "舒張壓"],
                    keywords=["diastolic", "dbp", "舒張壓"]
                ),
                EntityField(
                    field_name="body_temperature",
                    display_name="體溫",
                    data_type="Float",
                    description="體溫（°C）",
                    required=False,
                    aliases=["TEMP", "TEMPERATURE", "體溫", "溫度"],
                    keywords=["temperature", "temp", "體溫"]
                ),
                EntityField(
                    field_name="respiratory_rate",
                    display_name="呼吸速率",
                    data_type="Float",
                    description="呼吸每分鐘次數（rpm）",
                    required=False,
                    aliases=["RR", "RESPIRATION", "呼吸速率"],
                    keywords=["respiratory", "rr", "呼吸"]
                ),
                EntityField(
                    field_name="oxygen_saturation",
                    display_name="血氧飽和度",
                    data_type="Float",
                    description="血氧飽和度（%）",
                    required=False,
                    aliases=["SPO2", "O2_SAT", "血氧"],
                    patterns=[r"SPO2", r"O2.*SAT"],
                    keywords=["oxygen", "spo2", "血氧"]
                ),
            ]
        )
    
    @staticmethod
    def create_lab_result_entity() -> CoreEntity:
        """檢驗結果實體"""
        return CoreEntity(
            entity_type=EntityType.LAB_RESULT,
            display_name="檢驗結果",
            description="患者的檢驗室檢驗結果",
            table_patterns=[r"LAB", r"RESULT", r"EXAM"],
            table_keywords=["lab", "laboratory", "result", "exam", "檢驗", "檢查"],
            fields=[
                EntityField(
                    field_name="lab_result_id",
                    display_name="檢驗結果編號",
                    data_type="String",
                    description="檢驗結果唯一編號",
                    required=True,
                    keywords=["lab_result_id", "result_id"]
                ),
                EntityField(
                    field_name="patient_id",
                    display_name="病歷號",
                    data_type="String",
                    description="對應的患者病歷號",
                    required=True,
                    keywords=["patient_id"]
                ),
                EntityField(
                    field_name="test_name",
                    display_name="檢驗項目名稱",
                    data_type="String",
                    description="檢驗項目的名稱",
                    required=True,
                    aliases=["TEST_NAME", "EXAM_NAME", "檢驗項目"],
                    keywords=["test_name", "exam_name"]
                ),
                EntityField(
                    field_name="test_result",
                    display_name="檢驗結果值",
                    data_type="String",
                    description="檢驗結果的具體數值或文字",
                    required=True,
                    aliases=["RESULT_VALUE", "VALUE"],
                    keywords=["result", "value", "結果"]
                ),
                EntityField(
                    field_name="reference_range",
                    display_name="參考範圍",
                    data_type="String",
                    description="檢驗結果的參考範圍",
                    required=False,
                    aliases=["REF_RANGE", "NORMAL_RANGE"],
                    keywords=["reference", "range", "參考範圍"]
                ),
                EntityField(
                    field_name="unit",
                    display_name="單位",
                    data_type="String",
                    description="檢驗結果的單位",
                    required=False,
                    keywords=["unit", "單位"]
                ),
                EntityField(
                    field_name="test_datetime",
                    display_name="檢驗時間",
                    data_type="DateTime",
                    description="檢驗的時間",
                    required=True,
                    keywords=["test_datetime", "datetime", "時間"]
                ),
            ]
        )
    
    @staticmethod
    def create_medication_entity() -> CoreEntity:
        """藥物/用藥實體"""
        return CoreEntity(
            entity_type=EntityType.MEDICATION,
            display_name="藥物/用藥",
            description="患者的用藥紀錄與藥物資訊",
            table_patterns=[r"MEDICATION", r"MEDICINE", r"DRUG", r"PRESCRIPTION"],
            table_keywords=["medication", "medicine", "drug", "prescription", "藥物", "用藥", "藥"],
            fields=[
                EntityField(
                    field_name="medication_id",
                    display_name="藥物編號",
                    data_type="String",
                    description="藥物唯一識別碼",
                    required=True,
                    keywords=["medication_id", "drug_id"]
                ),
                EntityField(
                    field_name="medication_name",
                    display_name="藥物名稱",
                    data_type="String",
                    description="藥物的名稱",
                    required=True,
                    aliases=["DRUG_NAME", "MED_NAME", "藥名"],
                    keywords=["medication_name", "drug_name", "name"]
                ),
                EntityField(
                    field_name="dosage",
                    display_name="劑量",
                    data_type="String",
                    description="單次用藥劑量",
                    required=False,
                    keywords=["dosage", "dose", "劑量"]
                ),
                EntityField(
                    field_name="unit",
                    display_name="單位",
                    data_type="String",
                    description="劑量單位（mg、ml 等）",
                    required=False,
                    keywords=["unit", "單位"]
                ),
                EntityField(
                    field_name="frequency",
                    display_name="用法頻率",
                    data_type="String",
                    description="用藥頻率（如 QID、TID）",
                    required=False,
                    aliases=["FREQ", "用法"],
                    keywords=["frequency", "freq", "用法"]
                ),
                EntityField(
                    field_name="route",
                    display_name="給藥途徑",
                    data_type="String",
                    description="給藥途徑（口服、靜脈等）",
                    required=False,
                    aliases=["ROUTE_OF_ADMINISTRATION", "途徑"],
                    keywords=["route", "途徑"]
                ),
                EntityField(
                    field_name="start_date",
                    display_name="開始日期",
                    data_type="DateTime",
                    description="開始用藥的日期",
                    required=False,
                    keywords=["start_date", "start_time"]
                ),
                EntityField(
                    field_name="end_date",
                    display_name="結束日期",
                    data_type="DateTime",
                    description="停止用藥的日期",
                    required=False,
                    keywords=["end_date", "stop_date"]
                ),
            ]
        )
    
    @staticmethod
    def create_diagnosis_entity() -> CoreEntity:
        """診斷實體"""
        return CoreEntity(
            entity_type=EntityType.DIAGNOSIS,
            display_name="診斷",
            description="患者的診斷紀錄",
            table_patterns=[r"DIAGNOSIS", r"DIAGNOSE", r"ICD"],
            table_keywords=["diagnosis", "diagnose", "icd", "diagnostic", "診斷"],
            fields=[
                EntityField(
                    field_name="diagnosis_id",
                    display_name="診斷編號",
                    data_type="String",
                    description="診斷唯一編號",
                    required=True,
                    keywords=["diagnosis_id"]
                ),
                EntityField(
                    field_name="diagnosis_code",
                    display_name="診斷代碼",
                    data_type="String",
                    description="ICD 或其他診斷代碼",
                    required=False,
                    aliases=["ICD_CODE", "代碼"],
                    keywords=["diagnosis_code", "icd_code", "code"]
                ),
                EntityField(
                    field_name="diagnosis_name",
                    display_name="診斷名稱",
                    data_type="String",
                    description="診斷的名稱或說明",
                    required=True,
                    keywords=["diagnosis_name", "name"]
                ),
                EntityField(
                    field_name="diagnosis_date",
                    display_name="診斷日期",
                    data_type="DateTime",
                    description="確認診斷的日期",
                    required=False,
                    keywords=["diagnosis_date", "date"]
                ),
                EntityField(
                    field_name="primary_flag",
                    display_name="主要診斷標記",
                    data_type="Boolean",
                    description="是否為主要診斷",
                    required=False,
                    keywords=["primary", "main"]
                ),
            ]
        )
    
    @staticmethod
    def create_order_entity() -> CoreEntity:
        """醫囑實體"""
        return CoreEntity(
            entity_type=EntityType.ORDER,
            display_name="醫囑",
            description="醫師下達的醫囑紀錄",
            table_patterns=[r"ORDER", r"PHYSICIAN_ORDER", r"^ORD"],
            table_keywords=["order", "physician_order", "醫囑"],
            fields=[
                EntityField(
                    field_name="order_id",
                    display_name="醫囑編號",
                    data_type="String",
                    description="醫囑唯一編號",
                    required=True,
                    keywords=["order_id"]
                ),
                EntityField(
                    field_name="order_type",
                    display_name="醫囑類型",
                    data_type="String",
                    description="醫囑類型（如用藥、檢驗等）",
                    required=False,
                    keywords=["order_type", "type"]
                ),
                EntityField(
                    field_name="order_description",
                    display_name="醫囑說明",
                    data_type="String",
                    description="醫囑的具體內容",
                    required=True,
                    keywords=["description", "order_description"]
                ),
                EntityField(
                    field_name="order_date",
                    display_name="醫囑時間",
                    data_type="DateTime",
                    description="下達醫囑的時間",
                    required=True,
                    keywords=["order_date", "datetime"]
                ),
                EntityField(
                    field_name="ordered_by",
                    display_name="醫囑醫師",
                    data_type="String",
                    description="下達醫囑的醫師名稱或代碼",
                    required=False,
                    keywords=["ordered_by", "physician", "doctor"]
                ),
            ]
        )
    
    @staticmethod
    def create_procedure_entity() -> CoreEntity:
        """手術/處置實體"""
        return CoreEntity(
            entity_type=EntityType.PROCEDURE,
            display_name="手術/處置",
            description="患者接受的手術或治療處置",
            table_patterns=[r"PROCEDURE", r"SURGERY", r"TREATMENT"],
            table_keywords=["procedure", "surgery", "treatment", "手術", "處置"],
            fields=[
                EntityField(
                    field_name="procedure_id",
                    display_name="處置編號",
                    data_type="String",
                    description="手術/處置唯一編號",
                    required=True,
                    keywords=["procedure_id"]
                ),
                EntityField(
                    field_name="procedure_code",
                    display_name="手術代碼",
                    data_type="String",
                    description="手術或處置代碼",
                    required=False,
                    keywords=["procedure_code", "code"]
                ),
                EntityField(
                    field_name="procedure_name",
                    display_name="手術名稱",
                    data_type="String",
                    description="手術或處置的名稱",
                    required=True,
                    keywords=["procedure_name", "name"]
                ),
                EntityField(
                    field_name="procedure_date",
                    display_name="手術日期",
                    data_type="DateTime",
                    description="執行手術或處置的日期",
                    required=True,
                    keywords=["procedure_date", "date"]
                ),
                EntityField(
                    field_name="surgeon",
                    display_name="主刀醫師",
                    data_type="String",
                    description="執行手術的醫師",
                    required=False,
                    keywords=["surgeon", "doctor", "physician"]
                ),
                EntityField(
                    field_name="procedure_result",
                    display_name="手術結果",
                    data_type="String",
                    description="手術的結果或狀態",
                    required=False,
                    keywords=["result", "status"]
                ),
            ]
        )
    
    @staticmethod
    def create_allergy_entity() -> CoreEntity:
        """過敏紀錄實體"""
        return CoreEntity(
            entity_type=EntityType.ALLERGY,
            display_name="過敏紀錄",
            description="患者的過敏史和過敏反應紀錄",
            table_patterns=[r"ALLERGY", r"ALLERGIC", r"REACTION"],
            table_keywords=["allergy", "allergic", "reaction", "過敏"],
            fields=[
                EntityField(
                    field_name="allergy_id",
                    display_name="過敏紀錄編號",
                    data_type="String",
                    description="過敏紀錄的唯一編號",
                    required=True,
                    keywords=["allergy_id"]
                ),
                EntityField(
                    field_name="allergen",
                    display_name="過敏原",
                    data_type="String",
                    description="引起過敏的物質或藥物",
                    required=True,
                    aliases=["ALLERGEN_NAME", "物質"],
                    keywords=["allergen", "substance"]
                ),
                EntityField(
                    field_name="reaction",
                    display_name="過敏反應",
                    data_type="String",
                    description="過敏反應的症狀或描述",
                    required=False,
                    aliases=["REACTION_TYPE", "症狀"],
                    keywords=["reaction", "symptom", "symptom"]
                ),
                EntityField(
                    field_name="severity",
                    display_name="嚴重程度",
                    data_type="String",
                    description="過敏反應的嚴重程度（輕、中、重）",
                    required=False,
                    keywords=["severity", "level"]
                ),
                EntityField(
                    field_name="recorded_date",
                    display_name="紀錄日期",
                    data_type="DateTime",
                    description="記錄過敏的日期",
                    required=False,
                    keywords=["recorded_date", "date"]
                ),
            ]
        )

    @staticmethod
    def get_all_entities() -> List[CoreEntity]:
        """取得所有核心實體"""
        return [
            CoreEntityCatalog.create_patient_entity(),
            CoreEntityCatalog.create_visit_entity(),
            CoreEntityCatalog.create_nursing_record_entity(),
            CoreEntityCatalog.create_vital_sign_entity(),
            CoreEntityCatalog.create_lab_result_entity(),
            CoreEntityCatalog.create_medication_entity(),
            CoreEntityCatalog.create_diagnosis_entity(),
            CoreEntityCatalog.create_order_entity(),
            CoreEntityCatalog.create_procedure_entity(),
            CoreEntityCatalog.create_allergy_entity(),
        ]
    
    @staticmethod
    def get_entity_by_type(entity_type: EntityType) -> Optional[CoreEntity]:
        """根據型別取得實體"""
        entities = CoreEntityCatalog.get_all_entities()
        return next((e for e in entities if e.entity_type == entity_type), None)
