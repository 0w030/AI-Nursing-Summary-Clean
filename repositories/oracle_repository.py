# repositories/oracle_repository.py
"""
Oracle Repository 實作
使用 oracledb 驅動（Python-oracledb，官方驅動）
完全隔離在此層，業務邏輯層不可見
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import oracledb
except ImportError:
    oracledb = None  # 允許在沒有安裝時定義此模塊

from models.base_model import (
    Patient, NursingRecord, VitalSigns, LabResult
)
from repositories.base_repository import (
    IPatientRepository, INursingRecordRepository, IVitalSignsRepository
)


class OraclePatientRepository(IPatientRepository):
    """Oracle 患者 Repository 實作"""

    def __init__(self, connection_string: str):
        """
        初始化 Oracle 連接
        connection_string 格式: 'username/password@host:port/service_name'
        """
        if oracledb is None:
            raise RuntimeError("oracledb 未安裝。請執行: pip install oracledb")

        # 解析連接字串
        # 格式: oracle+oracledb://user:password@host:port/database
        self.connection_string = connection_string
        self.conn = None
        self._connect()

    def _connect(self):
        """建立 Oracle 連接"""
        try:
            # 解析 DSN 格式
            # connection_string 應該是 oracle+oracledb://user:pass@host:port/db
            
            # 臨時使用簡單的連接格式
            # username/password@host:port/service_name
            print(f"🔄 正在連接 Oracle: {self.connection_string}")
            
            # 使用 oracledb 臨時連接進行測試
            self.conn = oracledb.connect(self.connection_string)
            print(f"✅ Oracle 連接成功")
        except Exception as e:
            raise RuntimeError(f"Oracle 連接失敗: {e}")

    async def get_by_id(self, entity_id: int) -> Optional[Patient]:
        """根據 ID 取得患者"""
        query = """
            SELECT ROWID, PATIENT_ID, NAME, BIRTH_DATE, GENDER,
                   ADMISSION_DATE, DEPARTMENT
            FROM PATIENTS WHERE ROWID = :id
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {"id": entity_id})
            row = cursor.fetchone()
            # Oracle 的 ROWID 與 SYSDATE 需轉換
            return self._row_to_entity(row) if row else None
        finally:
            cursor.close()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Patient]:
        """取得所有患者（分頁）"""
        query = """
            SELECT PATIENT_ID, NAME, BIRTH_DATE, GENDER,
                   ADMISSION_DATE, DEPARTMENT, ROWID
            FROM (
                SELECT * FROM PATIENTS
                ORDER BY ROWID
            )
            WHERE ROWNUM > :skip AND ROWNUM <= :skip + :limit
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {"skip": skip, "limit": limit})
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            cursor.close()

    async def create(self, entity: Patient) -> Patient:
        """新增患者"""
        query = """
            INSERT INTO PATIENTS (PATIENT_ID, NAME, BIRTH_DATE, GENDER,
                                 ADMISSION_DATE, DEPARTMENT)
            VALUES (:patient_id, :name, :birth_date, :gender,
                    :admission_date, :department)
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {
                "patient_id": entity.patient_id,
                "name": entity.name,
                "birth_date": entity.birth_date,
                "gender": entity.gender,
                "admission_date": entity.admission_date,
                "department": entity.department,
            })
            self.conn.commit()
            # 取得新插入的 ROWID
            query_id = "SELECT ROWID FROM PATIENTS WHERE PATIENT_ID = :pid"
            cursor.execute(query_id, {"pid": entity.patient_id})
            row = cursor.fetchone()
            entity.id = row[0] if row else None
            return entity
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"新增患者失敗: {e}")
        finally:
            cursor.close()

    async def update(self, entity_id: int, entity: Patient) -> Optional[Patient]:
        """更新患者"""
        query = """
            UPDATE PATIENTS SET
                PATIENT_ID = :patient_id, NAME = :name,
                BIRTH_DATE = :birth_date, GENDER = :gender,
                ADMISSION_DATE = :admission_date, DEPARTMENT = :department
            WHERE ROWID = :id
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {
                "patient_id": entity.patient_id,
                "name": entity.name,
                "birth_date": entity.birth_date,
                "gender": entity.gender,
                "admission_date": entity.admission_date,
                "department": entity.department,
                "id": entity_id,
            })
            self.conn.commit()
            entity.id = entity_id
            return entity if cursor.rowcount > 0 else None
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"更新患者失敗: {e}")
        finally:
            cursor.close()

    async def delete(self, entity_id: int) -> bool:
        """刪除患者"""
        query = "DELETE FROM PATIENTS WHERE ROWID = :id"
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {"id": entity_id})
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"刪除患者失敗: {e}")
        finally:
            cursor.close()

    async def query(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[Patient]:
        """根據條件查詢患者"""
        query = "SELECT * FROM PATIENTS WHERE 1=1"
        params = {}

        if "patient_id" in filters:
            query += " AND PATIENT_ID LIKE :patient_id"
            params["patient_id"] = f"%{filters['patient_id']}%"

        if "name" in filters:
            query += " AND NAME LIKE :name"
            params["name"] = f"%{filters['name']}%"

        query += f" ORDER BY ROWID OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY"
        params["skip"] = skip
        params["limit"] = limit

        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            cursor.close()

    async def get_by_patient_id(self, patient_id: str) -> Optional[Patient]:
        """根據病歷號取得患者"""
        query = """
            SELECT ROWID, PATIENT_ID, NAME, BIRTH_DATE, GENDER,
                   ADMISSION_DATE, DEPARTMENT
            FROM PATIENTS WHERE PATIENT_ID = :pid
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {"pid": patient_id})
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None
        finally:
            cursor.close()

    async def search_patients(self, query_str: str, skip: int = 0, limit: int = 20) -> List[Patient]:
        """搜尋患者"""
        query = """
            SELECT ROWID, PATIENT_ID, NAME, BIRTH_DATE, GENDER,
                   ADMISSION_DATE, DEPARTMENT
            FROM PATIENTS
            WHERE PATIENT_ID LIKE :query OR NAME LIKE :query
            ORDER BY PATIENT_ID
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, {"query": f"%{query_str}%"})
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            cursor.close()

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

        cursor = self.conn.cursor()
        try:
            # 護理紀錄
            nursing_query = """
                SELECT * FROM NURSING_RECORDS
                WHERE PATIENT_ID = :pid
            """
            params = {"pid": patient_id}

            if start_time:
                nursing_query += " AND RECORD_TIME >= TO_TIMESTAMP(:start, 'YYYYMMDDHH24MISS')"
                params["start"] = start_time

            if end_time:
                nursing_query += " AND RECORD_TIME <= TO_TIMESTAMP(:end, 'YYYYMMDDHH24MISS')"
                params["end"] = end_time

            nursing_query += " ORDER BY RECORD_TIME ASC"

            cursor.execute(nursing_query, params)
            nursing_records = [self._row_to_dict(row, cursor) for row in cursor.fetchall()]

            # 生理監測
            vital_query = """
                SELECT * FROM VITAL_SIGNS
                WHERE PATIENT_ID = :pid
            """
            params = {"pid": patient_id}

            if start_time:
                vital_query += " AND RECORD_TIME >= TO_TIMESTAMP(:start, 'YYYYMMDDHH24MISS')"
                params["start"] = start_time

            if end_time:
                vital_query += " AND RECORD_TIME <= TO_TIMESTAMP(:end, 'YYYYMMDDHH24MISS')"
                params["end"] = end_time

            vital_query += " ORDER BY RECORD_TIME ASC"

            cursor.execute(vital_query, params)
            vital_signs = [self._row_to_dict(row, cursor) for row in cursor.fetchall()]

            # 檢驗結果
            lab_query = """
                SELECT * FROM LAB_RESULTS
                WHERE PATIENT_ID = :pid
            """
            params = {"pid": patient_id}

            if start_time:
                lab_query += " AND TEST_TIME >= TO_TIMESTAMP(:start, 'YYYYMMDDHH24MISS')"
                params["start"] = start_time

            if end_time:
                lab_query += " AND TEST_TIME <= TO_TIMESTAMP(:end, 'YYYYMMDDHH24MISS')"
                params["end"] = end_time

            lab_query += " ORDER BY TEST_TIME ASC"

            cursor.execute(lab_query, params)
            lab_results = [self._row_to_dict(row, cursor) for row in cursor.fetchall()]

            return {
                "nursing": nursing_records,
                "vitals": vital_signs,
                "labs": lab_results,
            }
        finally:
            cursor.close()

    @staticmethod
    def _row_to_entity(row) -> Patient:
        """將資料庫列轉換為 Patient 實體"""
        return Patient(
            id=row[0],  # ROWID
            patient_id=row[1],
            name=row[2],
            birth_date=row[3],
            gender=row[4],
            admission_date=row[5],
            department=row[6],
        )

    @staticmethod
    def _row_to_dict(row, cursor) -> Dict[str, Any]:
        """將資料庫列轉換為字典"""
        col_names = [col[0].lower() for col in cursor.description]
        return dict(zip(col_names, row))

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
