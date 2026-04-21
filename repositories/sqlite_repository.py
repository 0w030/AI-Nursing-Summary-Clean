# repositories/sqlite_repository.py
"""
SQLite Repository 實作
用於本地開發和測試環境
"""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from models.base_model import Patient, NursingRecord
from repositories.base_repository import (
    IPatientRepository, INursingRecordRepository
)


class SQLitePatientRepository(IPatientRepository):
    """SQLite 患者 Repository 實作"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化數據庫"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY,
                patient_id TEXT UNIQUE NOT NULL,
                name TEXT,
                birth_date TEXT,
                gender TEXT,
                admission_date TEXT,
                department TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nursing_records (
                id INTEGER PRIMARY KEY,
                patient_id TEXT NOT NULL,
                record_time TEXT NOT NULL,
                nursing_note TEXT,
                assessment TEXT,
                intervention TEXT,
                response TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """)
        conn.commit()
        conn.close()

    async def get_by_id(self, entity_id: int) -> Optional[Patient]:
        """根據 ID 取得患者"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM patients WHERE id = ?
        """, (entity_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Patient]:
        """取得所有患者"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM patients ORDER BY id LIMIT ? OFFSET ?
        """, (limit, skip))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    async def create(self, entity: Patient) -> Patient:
        """新增患者"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO patients (patient_id, name, birth_date, gender,
                                 admission_date, department, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity.patient_id, entity.name, entity.birth_date,
              entity.gender, entity.admission_date, entity.department,
              now, now))
        conn.commit()
        entity.id = cursor.lastrowid
        entity.created_at = datetime.fromisoformat(now)
        entity.updated_at = datetime.fromisoformat(now)
        conn.close()
        return entity

    async def update(self, entity_id: int, entity: Patient) -> Optional[Patient]:
        """更新患者"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE patients SET
                patient_id = ?, name = ?, birth_date = ?,
                gender = ?, admission_date = ?, department = ?,
                updated_at = ?
            WHERE id = ?
        """, (entity.patient_id, entity.name, entity.birth_date,
              entity.gender, entity.admission_date, entity.department,
              now, entity_id))
        conn.commit()
        rows = cursor.rowcount
        conn.close()
        
        if rows > 0:
            entity.id = entity_id
            entity.updated_at = datetime.fromisoformat(now)
            return entity
        return None

    async def delete(self, entity_id: int) -> bool:
        """刪除患者"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patients WHERE id = ?", (entity_id,))
        conn.commit()
        rows = cursor.rowcount
        conn.close()
        return rows > 0

    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Patient]:
        """根據條件查詢"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = "SELECT * FROM patients WHERE 1=1"
        params = []
        
        if "patient_id" in filters:
            sql += " AND patient_id LIKE ?"
            params.append(f"%{filters['patient_id']}%")
        
        if "name" in filters:
            sql += " AND name LIKE ?"
            params.append(f"%{filters['name']}%")
        
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    async def get_by_patient_id(self, patient_id: str) -> Optional[Patient]:
        """根據病歷號取得患者"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    async def search_patients(self, query: str, skip: int = 0, limit: int = 20) -> List[Patient]:
        """搜尋患者"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM patients
            WHERE patient_id LIKE ? OR name LIKE ?
            LIMIT ? OFFSET ?
        """, (f"%{query}%", f"%{query}%", limit, skip))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    async def get_patient_full_history(
        self,
        patient_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取得患者完整病歷"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 護理紀錄
        query = "SELECT * FROM nursing_records WHERE patient_id = ?"
        params = [patient_id]
        
        if start_time:
            query += " AND record_time >= ?"
            params.append(start_time)
        if end_time:
            query += " AND record_time <= ?"
            params.append(end_time)
        
        query += " ORDER BY record_time ASC"
        cursor.execute(query, params)
        nursing_records = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "nursing": nursing_records,
            "vitals": [],
            "labs": [],
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
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
        )


class SQLiteNursingRecordRepository(INursingRecordRepository):
    """SQLite 護理紀錄 Repository 實作"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get_by_id(self, entity_id: int) -> Optional[NursingRecord]:
        """根據 ID 取得護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nursing_records WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_entity(row) if row else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[NursingRecord]:
        """取得所有護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM nursing_records ORDER BY record_time DESC LIMIT ? OFFSET ?
        """, (limit, skip))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    async def create(self, entity: NursingRecord) -> NursingRecord:
        """新增護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO nursing_records
            (patient_id, record_time, nursing_note, assessment,
             intervention, response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity.patient_id, entity.record_time.isoformat(),
              entity.nursing_note, entity.assessment,
              entity.intervention, entity.response, now, now))
        conn.commit()
        entity.id = cursor.lastrowid
        conn.close()
        return entity

    async def update(self, entity_id: int, entity: NursingRecord) -> Optional[NursingRecord]:
        """更新護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE nursing_records SET
                nursing_note = ?, assessment = ?, intervention = ?,
                response = ?, updated_at = ?
            WHERE id = ?
        """, (entity.nursing_note, entity.assessment,
              entity.intervention, entity.response, now, entity_id))
        conn.commit()
        rows = cursor.rowcount
        conn.close()
        
        return entity if rows > 0 else None

    async def delete(self, entity_id: int) -> bool:
        """刪除護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nursing_records WHERE id = ?", (entity_id,))
        conn.commit()
        rows = cursor.rowcount
        conn.close()
        return rows > 0

    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[NursingRecord]:
        """根據條件查詢"""
        pass

    async def get_by_patient_id(self, patient_id: str) -> List[NursingRecord]:
        """取得特定患者的護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM nursing_records
            WHERE patient_id = ?
            ORDER BY record_time DESC
        """, (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    async def get_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> List[NursingRecord]:
        """取得特定日期範圍內的護理紀錄"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM nursing_records
            WHERE patient_id = ? AND record_time >= ? AND record_time <= ?
            ORDER BY record_time DESC
        """, (patient_id, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_entity(row) for row in rows]

    @staticmethod
    def _row_to_entity(row) -> NursingRecord:
        """將資料庫列轉換為 NursingRecord 實體"""
        return NursingRecord(
            id=row['id'],
            patient_id=row['patient_id'],
            record_time=datetime.fromisoformat(row['record_time']),
            nursing_note=row['nursing_note'],
            assessment=row['assessment'],
            intervention=row['intervention'],
            response=row['response'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
        )
