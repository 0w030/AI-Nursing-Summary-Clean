# repositories/postgresql_repository.py
"""
PostgreSQL Repository 實作
使用 asyncpg 或 psycopg 驅動（不直接依賴 cx_Oracle）
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg  # 異步 PostgreSQL 驅動

from models.base_model import (
    Patient, NursingRecord, VitalSigns, LabResult, User, Template
)
from repositories.base_repository import (
    IPatientRepository, INursingRecordRepository,
    IVitalSignsRepository, ILabResultRepository,
    IUserRepository, ITemplateRepository
)


class PostgreSQLPatientRepository(IPatientRepository):
    """PostgreSQL 患者 Repository 實作"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_by_id(self, entity_id: int) -> Optional[Patient]:
        """根據 ID 取得患者"""
        query = """
            SELECT id, patient_id, name, birth_date, gender, 
                   admission_date, department, created_at, updated_at
            FROM patients WHERE id = $1
        """
        row = await self.db_pool.fetchrow(query, entity_id)
        return self._row_to_entity(row) if row else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Patient]:
        """取得所有患者（分頁）"""
        query = """
            SELECT id, patient_id, name, birth_date, gender,
                   admission_date, department, created_at, updated_at
            FROM patients ORDER BY id OFFSET $1 LIMIT $2
        """
        rows = await self.db_pool.fetch(query, skip, limit)
        return [self._row_to_entity(row) for row in rows]

    async def create(self, entity: Patient) -> Patient:
        """新增患者"""
        query = """
            INSERT INTO patients (patient_id, name, birth_date, gender,
                                  admission_date, department, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id, created_at, updated_at
        """
        row = await self.db_pool.fetchrow(
            query,
            entity.patient_id, entity.name, entity.birth_date,
            entity.gender, entity.admission_date, entity.department
        )
        entity.id = row['id']
        entity.created_at = row['created_at']
        entity.updated_at = row['updated_at']
        return entity

    async def update(self, entity_id: int, entity: Patient) -> Optional[Patient]:
        """更新患者"""
        query = """
            UPDATE patients SET
                patient_id = $1, name = $2, birth_date = $3,
                gender = $4, admission_date = $5, department = $6,
                updated_at = NOW()
            WHERE id = $7
            RETURNING id, created_at, updated_at
        """
        row = await self.db_pool.fetchrow(
            query,
            entity.patient_id, entity.name, entity.birth_date,
            entity.gender, entity.admission_date, entity.department,
            entity_id
        )
        if row:
            entity.id = row['id']
            entity.created_at = row['created_at']
            entity.updated_at = row['updated_at']
            return entity
        return None

    async def delete(self, entity_id: int) -> bool:
        """刪除患者"""
        result = await self.db_pool.execute(
            "DELETE FROM patients WHERE id = $1", entity_id
        )
        return result == "DELETE 1"

    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Patient]:
        """根據條件查詢患者"""
        query = "SELECT * FROM patients WHERE 1=1"
        params = []
        param_count = 1

        if "patient_id" in filters:
            query += f" AND patient_id LIKE ${param_count}"
            params.append(f"%{filters['patient_id']}%")
            param_count += 1

        if "name" in filters:
            query += f" AND name LIKE ${param_count}"
            params.append(f"%{filters['name']}%")
            param_count += 1

        query += f" ORDER BY id OFFSET ${param_count} LIMIT ${param_count + 1}"
        params.extend([skip, limit])

        rows = await self.db_pool.fetch(query, *params)
        return [self._row_to_entity(row) for row in rows]

    async def get_by_patient_id(self, patient_id: str) -> Optional[Patient]:
        """根據病歷號取得患者"""
        query = """
            SELECT id, patient_id, name, birth_date, gender,
                   admission_date, department, created_at, updated_at
            FROM patients WHERE patient_id = $1
        """
        row = await self.db_pool.fetchrow(query, patient_id)
        return self._row_to_entity(row) if row else None

    async def search_patients(self, query: str, skip: int = 0, limit: int = 20) -> List[Patient]:
        """搜尋患者"""
        sql = """
            SELECT id, patient_id, name, birth_date, gender,
                   admission_date, department, created_at, updated_at
            FROM patients
            WHERE patient_id LIKE $1 OR name LIKE $1
            ORDER BY patient_id
            OFFSET $2 LIMIT $3
        """
        rows = await self.db_pool.fetch(sql, f"%{query}%", skip, limit)
        return [self._row_to_entity(row) for row in rows]

    async def get_patient_full_history(
        self,
        patient_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取得患者完整病歷"""
        nursing_records = []
        vital_signs = []
        lab_results = []

        # 查詢護理紀錄
        nursing_query = """
            SELECT * FROM nursing_records
            WHERE patient_id = $1
        """
        params = [patient_id]
        param_count = 2

        if start_time:
            nursing_query += f" AND record_time >= ${param_count}"
            params.append(start_time)
            param_count += 1

        if end_time:
            nursing_query += f" AND record_time <= ${param_count}"
            params.append(end_time)
            param_count += 1

        nursing_query += " ORDER BY record_time ASC"
        rows = await self.db_pool.fetch(nursing_query, *params)
        nursing_records = [dict(row) for row in rows]

        # 查詢生理監測
        vital_query = """
            SELECT * FROM vital_signs
            WHERE patient_id = $1
        """
        params = [patient_id]
        param_count = 2

        if start_time:
            vital_query += f" AND record_time >= ${param_count}"
            params.append(start_time)
            param_count += 1

        if end_time:
            vital_query += f" AND record_time <= ${param_count}"
            params.append(end_time)
            param_count += 1

        vital_query += " ORDER BY record_time ASC"
        rows = await self.db_pool.fetch(vital_query, *params)
        vital_signs = [dict(row) for row in rows]

        # 查詢檢驗結果
        lab_query = """
            SELECT * FROM lab_results
            WHERE patient_id = $1
        """
        params = [patient_id]
        param_count = 2

        if start_time:
            lab_query += f" AND test_time >= ${param_count}"
            params.append(start_time)
            param_count += 1

        if end_time:
            lab_query += f" AND test_time <= ${param_count}"
            params.append(end_time)
            param_count += 1

        lab_query += " ORDER BY test_time ASC"
        rows = await self.db_pool.fetch(lab_query, *params)
        lab_results = [dict(row) for row in rows]

        return {
            "nursing": nursing_records,
            "vitals": vital_signs,
            "labs": lab_results,
        }

    @staticmethod
    def _row_to_entity(row) -> Patient:
        """將資料庫列轉換為 Patient 實體"""
        return Patient(
            id=row['id'],
            patient_id=row['patient_id'],
            name=row['name'],
            birth_date=row['birth_date'],
            gender=row['gender'],
            admission_date=row['admission_date'],
            department=row['department'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )


class PostgreSQLNursingRecordRepository(INursingRecordRepository):
    """PostgreSQL 護理紀錄 Repository 實作"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_by_id(self, entity_id: int) -> Optional[NursingRecord]:
        """根據 ID 取得護理紀錄"""
        query = """
            SELECT id, patient_id, record_time, nursing_note,
                   assessment, intervention, response, created_at, updated_at
            FROM nursing_records WHERE id = $1
        """
        row = await self.db_pool.fetchrow(query, entity_id)
        return self._row_to_entity(row) if row else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[NursingRecord]:
        """取得所有護理紀錄"""
        query = """
            SELECT id, patient_id, record_time, nursing_note,
                   assessment, intervention, response, created_at, updated_at
            FROM nursing_records ORDER BY record_time DESC OFFSET $1 LIMIT $2
        """
        rows = await self.db_pool.fetch(query, skip, limit)
        return [self._row_to_entity(row) for row in rows]

    async def create(self, entity: NursingRecord) -> NursingRecord:
        """新增護理紀錄"""
        query = """
            INSERT INTO nursing_records
            (patient_id, record_time, nursing_note, assessment,
             intervention, response, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id, created_at, updated_at
        """
        row = await self.db_pool.fetchrow(
            query,
            entity.patient_id, entity.record_time, entity.nursing_note,
            entity.assessment, entity.intervention, entity.response
        )
        entity.id = row['id']
        entity.created_at = row['created_at']
        entity.updated_at = row['updated_at']
        return entity

    async def update(self, entity_id: int, entity: NursingRecord) -> Optional[NursingRecord]:
        """更新護理紀錄"""
        query = """
            UPDATE nursing_records SET
                nursing_note = $1, assessment = $2, intervention = $3,
                response = $4, updated_at = NOW()
            WHERE id = $5
            RETURNING id, created_at, updated_at
        """
        row = await self.db_pool.fetchrow(
            query,
            entity.nursing_note, entity.assessment,
            entity.intervention, entity.response, entity_id
        )
        if row:
            entity.id = row['id']
            entity.created_at = row['created_at']
            entity.updated_at = row['updated_at']
            return entity
        return None

    async def delete(self, entity_id: int) -> bool:
        """刪除護理紀錄"""
        result = await self.db_pool.execute(
            "DELETE FROM nursing_records WHERE id = $1", entity_id
        )
        return result == "DELETE 1"

    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[NursingRecord]:
        """根據條件查詢"""
        pass

    async def get_by_patient_id(self, patient_id: str) -> List[NursingRecord]:
        """取得特定患者的護理紀錄"""
        query = """
            SELECT id, patient_id, record_time, nursing_note,
                   assessment, intervention, response, created_at, updated_at
            FROM nursing_records
            WHERE patient_id = $1
            ORDER BY record_time DESC
        """
        rows = await self.db_pool.fetch(query, patient_id)
        return [self._row_to_entity(row) for row in rows]

    async def get_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> List[NursingRecord]:
        """取得特定日期範圍內的護理紀錄"""
        query = """
            SELECT id, patient_id, record_time, nursing_note,
                   assessment, intervention, response, created_at, updated_at
            FROM nursing_records
            WHERE patient_id = $1 AND record_time >= $2 AND record_time <= $3
            ORDER BY record_time DESC
        """
        rows = await self.db_pool.fetch(query, patient_id, start_date, end_date)
        return [self._row_to_entity(row) for row in rows]

    @staticmethod
    def _row_to_entity(row) -> NursingRecord:
        """將資料庫列轉換為 NursingRecord 實體"""
        return NursingRecord(
            id=row['id'],
            patient_id=row['patient_id'],
            record_time=row['record_time'],
            nursing_note=row['nursing_note'],
            assessment=row['assessment'],
            intervention=row['intervention'],
            response=row['response'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )
