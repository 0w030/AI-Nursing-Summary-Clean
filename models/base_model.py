# models/base_model.py
"""
基礎模型抽象層 - 定義所有數據實體的基類
禁止在此層出現資料庫特定的 import（如 cx_Oracle）
"""

from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict
from datetime import datetime


class BaseEntity:
    """所有實體的基礎類別"""
    
    def to_dict(self) -> Dict[str, Any]:
        """將實體轉換為字典"""
        return {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


@dataclass
class Patient:
    """患者資料模型"""
    patient_id: str  # 病歷號
    id: Optional[int] = None
    name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    admission_date: Optional[datetime] = None
    department: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}

    @property
    def display_name(self) -> str:
        """用於顯示的名稱"""
        return f"{self.name}({self.patient_id})" if self.name else self.patient_id


@dataclass
class NursingRecord:
    """護理紀錄模型"""
    patient_id: str
    record_time: datetime
    id: Optional[int] = None
    nursing_note: Optional[str] = None
    assessment: Optional[str] = None
    intervention: Optional[str] = None
    response: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}


@dataclass
class VitalSigns:
    """生理監測模型"""
    patient_id: str
    record_time: datetime
    id: Optional[int] = None
    temperature: Optional[float] = None
    heart_rate: Optional[float] = None
    blood_pressure_sys: Optional[float] = None
    blood_pressure_dia: Optional[float] = None
    respiratory_rate: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    gcs_score: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}


@dataclass
class LabResult:
    """檢驗結果模型"""
    patient_id: str
    test_time: datetime
    test_name: str
    id: Optional[int] = None
    result_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}


@dataclass
class User:
    """使用者模型"""
    username: str
    id: Optional[int] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    is_deleted: bool = False
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}


@dataclass
class Template:
    """護理模板模型"""
    name: str
    id: Optional[int] = None
    description: Optional[str] = None
    category: str = "general"
    content: Optional[str] = None
    created_by: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.__dict__.items()}
