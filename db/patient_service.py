import sys
import os
import psycopg2
from datetime import datetime

# --- 路徑修正區塊 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from db.db_connector import get_db_connection
from data.metadata import get_chinese_name

def get_patient_full_history(patient_id, start_time=None, end_time=None, tables=None):
    """
    根據病歷號及勾選的 Table 範圍，從資料庫撈取病患數據。
    
    Args:
        patient_id (str): 病歷號
        start_time (str, optional): 起始時間 (YYYYMMDDHHMMSS)
        end_time (str, optional): 結束時間
        tables (list, optional): 欲查詢的鍵值清單，例如 ['nursing', 'vitals', 'labs']
                                 若為 None 則預設查詢全部。
    """
    conn = get_db_connection()
    if not conn:
        print("無法建立連線，無法查詢病患資料。")
        return None

    # 初始化回傳結構，確保 AI 模組讀取時不會因缺少 Key 而報錯
    patient_data = {
        "nursing": [],
        "vitals": [],
        "labs": []
    }

    # 如果沒傳入 tables，預設抓取所有支援的資料表
    if tables is None:
        tables = ['nursing', 'vitals', 'labs']

    try:
        with conn.cursor() as cur:
            
            # ==========================================
            # 1. 護理紀錄 (ENSDATA)
            # ==========================================
            if 'nursing' in tables:
                sql_nursing = "SELECT PROCDTTM, SUBJECT, DIAGNOSIS FROM ENSDATA WHERE PATID = %s"
                params_nursing = [patient_id]

                if start_time:
                    sql_nursing += " AND PROCDTTM >= %s"
                    params_nursing.append(start_time)
                if end_time:
                    sql_nursing += " AND PROCDTTM <= %s"
                    params_nursing.append(end_time)
                
                sql_nursing += " ORDER BY PROCDTTM ASC"
                cur.execute(sql_nursing, tuple(params_nursing))
                
                for row in cur.fetchall():
                    patient_data["nursing"].append({
                        "PROCDTTM": row[0],
                        "SUBJECT": row[1],
                        "DIAGNOSIS": row[2]
                    })

            # ==========================================
            # 2. 生理監測 (v_ai_hisensnes)
            # ==========================================
            if 'vitals' in tables:
                sql_vitals = """
                    SELECT PROCDTTM, ETEMPUTER, EPLUSE, EBREATHE, EPRESSURE, EDIASTOLIC, ESAO2, 
                           GCS_E, GCS_V, GCS_M
                    FROM v_ai_hisensnes WHERE PATID = %s
                """
                params_vitals = [patient_id]

                if start_time:
                    sql_vitals += " AND PROCDTTM >= %s"
                    params_vitals.append(start_time)
                if end_time:
                    sql_vitals += " AND PROCDTTM <= %s"
                    params_vitals.append(end_time)
                
                sql_vitals += " ORDER BY PROCDTTM ASC"
                cur.execute(sql_vitals, tuple(params_vitals))
                
                for row in cur.fetchall():
                    patient_data["vitals"].append({
                        "PROCDTTM": row[0],
                        "ETEMPUTER": row[1],
                        "EPLUSE": row[2],
                        "EBREATHE": row[3],
                        "EPRESSURE": row[4],
                        "EDIASTOLIC": row[5],
                        "ESAO2": row[6],
                        "GCS": f"E{row[7]}V{row[8]}M{row[9]}"
                    })

            # ==========================================
            # 3. 檢驗結果 (DB_ADM_LABDATA_ER)
            # ==========================================
            if 'labs' in tables:
                sql_labs = """
                    SELECT CHRCPDTM, CHHEAD, CHVAL, CHUNIT, CHNL, CHNH
                    FROM DB_ADM_LABDATA_ER WHERE CHMRNO = %s
                """
                params_labs = [patient_id]

                if start_time:
                    sql_labs += " AND CHRCPDTM >= %s"
                    params_labs.append(start_time)
                if end_time:
                    sql_labs += " AND CHRCPDTM <= %s"
                    params_labs.append(end_time)
                
                sql_labs += " ORDER BY CHRCPDTM ASC"
                cur.execute(sql_labs, tuple(params_labs))
                
                for row in cur.fetchall():
                    patient_data["labs"].append({
                        "CHRCPDTM": row[0],
                        "CHHEAD": row[1],
                        "CHVAL": row[2],
                        "CHUNIT": row[3],
                        "REF_RANGE": f"{row[4]}~{row[5]}"
                    })

        print(f"✅ 成功撈取資料表: {', '.join(tables)}")
        return patient_data

    except psycopg2.Error as e:
        print(f"❌ 資料庫查詢失敗: {e}")
        return None
    finally:
        conn.close()

def get_all_patients_overview():
    """
    從 ENSDATA 撈取所有病患清單及其就診時間範圍，用於前端儀表板選擇。
    """
    conn = get_db_connection()
    if not conn: return []

    overview_list = []
    try:
        with conn.cursor() as cur:
            query = """
                SELECT PATID, 
                       MIN(PROCDTTM) as start_time, 
                       MAX(PROCDTTM) as end_time, 
                       COUNT(*) as record_count
                FROM ENSDATA
                GROUP BY PATID
                ORDER BY start_time DESC
                LIMIT 50;
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            for row in rows:
                overview_list.append({
                    "病歷號": row[0],
                    "最早紀錄": row[1],
                    "最晚紀錄": row[2],
                    "資料筆數": row[3]
                })
        return overview_list
    except psycopg2.Error as e:
        print(f"查詢病患清單失敗: {e}")
        return []
    finally:
        conn.close()

def translate_to_chinese_view(data_list):
    """
    輔助函數：將資料列表中的英文 Key 翻譯成中文，僅供前端閱讀預覽使用。
    """
    if not data_list:
        return []
    
    view_list = []
    for item in data_list:
        new_item = {}
        for key, value in item.items():
            chinese_key = get_chinese_name(key)
            new_item[chinese_key] = value
        view_list.append(new_item)
    return view_list