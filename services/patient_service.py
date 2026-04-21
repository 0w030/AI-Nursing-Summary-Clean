# services/patient_service.py
"""
業務邏輯層 - 患者服務
❌ 禁止導入任何資料庫驅動（cx_Oracle, psycopg2 等）
✅ 只透過 Repository 介面與資料層互動
"""

from typing import Optional, Dict, Any, List
from models.base_model import Patient, NursingRecord
from repositories.base_repository import IPatientRepository, INursingRecordRepository


class PatientService:
    """
    患者業務邏輯服務
    此層完全不知道底層使用何種資料庫
    """

    def __init__(self, patient_repo: IPatientRepository, nursing_repo: INursingRecordRepository):
        """
        初始化患者服務
        依賴注入確保可插拔性

        Args:
            patient_repo: 患者 Repository 實現
            nursing_repo: 護理紀錄 Repository 實現
        """
        self.patient_repo = patient_repo
        self.nursing_repo = nursing_repo

    async def get_patient_overview(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        取得患者概覽信息
        業務邏輯：組合多個 Repository 的數據
        """
        patient = await self.patient_repo.get_by_patient_id(patient_id)
        if not patient:
            return None

        nursing_records = await self.nursing_repo.get_by_patient_id(patient_id)

        return {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "admission_date": patient.admission_date.isoformat() if patient.admission_date else None,
            "department": patient.department,
            "recent_nursing_count": len(nursing_records),
            "last_record_time": nursing_records[0].record_time.isoformat() if nursing_records else None,
        }

    async def get_patient_full_history(
        self,
        patient_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        取得患者完整病歷
        業務邏輯：調用 Repository 方法，進行數據聚合

        Args:
            patient_id: 病歷號
            start_time: 起始時間 (YYYYMMDDHHMMSS)
            end_time: 結束時間 (YYYYMMDDHHMMSS)

        Returns:
            包含 nursing, vitals, labs 的字典
        """
        patient = await self.patient_repo.get_by_patient_id(patient_id)
        if not patient:
            return None

        # 呼叫 Repository 的統合方法
        history = await self.patient_repo.get_patient_full_history(
            patient_id=patient_id,
            start_time=start_time,
            end_time=end_time,
        )

        return {
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "admission_date": patient.admission_date.isoformat() if patient.admission_date else None,
            **history  # nursing, vitals, labs
        }

    async def list_patients(self, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """
        列出患者列表
        """
        patients = await self.patient_repo.get_all(skip=skip, limit=limit)
        return [
            {
                "patient_id": p.patient_id,
                "name": p.name,
                "admission_date": p.admission_date.isoformat() if p.admission_date else None,
                "department": p.department,
            }
            for p in patients
        ]

    async def search_patients(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜尋患者
        """
        patients = await self.patient_repo.search_patients(query, limit=limit)
        return [
            {
                "patient_id": p.patient_id,
                "name": p.name,
                "department": p.department,
            }
            for p in patients
        ]

    async def create_patient(self, patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        建立新患者
        """
        patient = Patient(
            patient_id=patient_data["patient_id"],
            name=patient_data.get("name"),
            birth_date=patient_data.get("birth_date"),
            gender=patient_data.get("gender"),
            admission_date=patient_data.get("admission_date"),
            department=patient_data.get("department"),
        )
        created = await self.patient_repo.create(patient)
        return {
            "id": created.id,
            "patient_id": created.patient_id,
            "name": created.name,
        } if created else None

    async def update_patient(self, patient_id: int, patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新患者信息
        """
        patient = Patient(
            id=patient_id,
            patient_id=patient_data.get("patient_id"),
            name=patient_data.get("name"),
            birth_date=patient_data.get("birth_date"),
            gender=patient_data.get("gender"),
            admission_date=patient_data.get("admission_date"),
            department=patient_data.get("department"),
        )
        updated = await self.patient_repo.update(patient_id, patient)
        return {
            "id": updated.id,
            "patient_id": updated.patient_id,
            "name": updated.name,
        } if updated else None

    async def delete_patient(self, patient_id: int) -> bool:
        """
        刪除患者
        """
        return await self.patient_repo.delete(patient_id)
