# repositories/base_repository.py
"""
Repository 模式 - 基礎接口層
業務邏輯透過此介面與數據庫互動，不直接依賴特定資料庫驅動
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar
from models.base_model import BaseEntity

T = TypeVar('T', bound=BaseEntity)


class IBaseRepository(ABC, Generic[T]):
    """
    通用 Repository 介面
    定義所有實體操作的基礎契約
    """

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        """根據 ID 取得單筆記錄"""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """取得所有記錄（分頁）"""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """新增記錄"""
        pass

    @abstractmethod
    async def update(self, entity_id: int, entity: T) -> Optional[T]:
        """更新記錄"""
        pass

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """刪除記錄"""
        pass

    @abstractmethod
    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[T]:
        """根據條件查詢記錄"""
        pass


class IPatientRepository(IBaseRepository["Patient"]):
    """患者特定的 Repository 介面"""

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str) -> Optional["Patient"]:
        """根據病歷號取得患者資料"""
        pass

    @abstractmethod
    async def search_patients(self, query: str, skip: int = 0, limit: int = 20) -> List["Patient"]:
        """搜尋患者"""
        pass

    @abstractmethod
    async def get_patient_full_history(
        self,
        patient_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取得患者完整病歷（包含護理、生理、檢驗記錄）"""
        pass


class INursingRecordRepository(IBaseRepository["NursingRecord"]):
    """護理紀錄特定的 Repository 介面"""

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str) -> List["NursingRecord"]:
        """取得特定患者的所有護理紀錄"""
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> List["NursingRecord"]:
        """取得特定日期範圍內的護理紀錄"""
        pass


class IVitalSignsRepository(IBaseRepository["VitalSigns"]):
    """生理監測特定的 Repository 介面"""

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str, limit: int = 100) -> List["VitalSigns"]:
        """取得特定患者的所有生理監測記錄"""
        pass

    @abstractmethod
    async def get_latest(self, patient_id: str) -> Optional["VitalSigns"]:
        """取得最新的生理監測記錄"""
        pass


class ILabResultRepository(IBaseRepository["LabResult"]):
    """檢驗結果特定的 Repository 介面"""

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str) -> List["LabResult"]:
        """取得特定患者的所有檢驗結果"""
        pass

    @abstractmethod
    async def get_by_test_type(self, patient_id: str, test_name: str) -> List["LabResult"]:
        """取得特定患者的特定檢驗結果"""
        pass


class IUserRepository(IBaseRepository["User"]):
    """使用者特定的 Repository 介面"""

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional["User"]:
        """根據使用者名稱取得使用者"""
        pass

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> Optional["User"]:
        """驗證使用者帳密"""
        pass

    @abstractmethod
    async def search_users(self, query: str) -> List["User"]:
        """搜尋使用者"""
        pass


class ITemplateRepository(IBaseRepository["Template"]):
    """模板特定的 Repository 介面"""

    @abstractmethod
    async def get_by_category(self, category: str) -> List["Template"]:
        """根據類別取得模板"""
        pass

    @abstractmethod
    async def get_active_templates(self) -> List["Template"]:
        """取得所有啟用的模板"""
        pass
