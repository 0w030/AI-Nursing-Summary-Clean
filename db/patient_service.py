# import sys
# import os
# import psycopg2
# from datetime import datetime

# # --- 路徑修正區塊 ---
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)
# if parent_dir not in sys.path:
#     sys.path.append(parent_dir)

# from db.db_connector import get_db_connection
# from data.metadata import get_chinese_name

# def get_patient_full_history(patient_id, start_time=None, end_time=None, schema_queries=None, full_schema=None):
#     """
#     根據病歷號及前端勾選的欄位，動態生成 SQL 並從資料庫撈取數據。
    
#     Args:
#         patient_id (str): 病歷號
#         start_time (str, optional): 起始時間 (YYYYMMDDHHMMSS)
#         end_time (str, optional): 結束時間
#         schema_queries (dict): 前端傳來的勾選字典，格式如 {"ENSDATA": ["SUBJECT", "DIAGNOSIS"]}
#         full_schema (dict): 前端傳來的完整 JSON 藍圖 (依賴注入)
#     """
#     conn = get_db_connection()
#     if not conn:
#         print("無法建立連線，無法查詢病患資料。")
#         return None

#     # 初始化回傳結構，保持與 ai_summarizer 的相容性
#     patient_data = {
#         "nursing": [],
#         "vitals": [],
#         "labs": []
#     }

#     # 檢查是否都有收到資料 (包含欄位勾選字典 與 藍圖設定)
#     if not schema_queries or not full_schema:
#         print("沒有提供查詢條件或 Schema 藍圖。")
#         return patient_data

#     # 將 full_schema 中的 tables 轉為字典方便查詢
#     table_defs = {t["table_name"]: t for t in full_schema["tables"]}

#     try:
#         with conn.cursor() as cur:
#             # 遍歷使用者勾選的每一個資料表與欄位
#             for table_name, selected_columns in schema_queries.items():
#                 if not selected_columns:
#                     continue
                
#                 table_info = table_defs.get(table_name)
#                 if not table_info:
#                     print(f"警告：Schema 中找不到資料表 {table_name}")
#                     continue

#                 # 1. 取得該表的關聯設定
#                 pid_col = table_info["patient_id_col"]
#                 time_col = table_info["time_col"]

#                 # 2. 確保一定會撈出時間欄位 (供後續排序與顯示使用)
#                 select_cols_set = set(selected_columns)
#                 select_cols_set.add(time_col)
#                 select_cols_list = list(select_cols_set)
                
#                 cols_str = ", ".join(select_cols_list)

#                 # 3. 動態組裝 SQL 語法
#                 sql = f"SELECT {cols_str} FROM {table_name} WHERE {pid_col} = %s"
#                 params = [patient_id]

#                 if start_time:
#                     sql += f" AND {time_col} >= %s"
#                     params.append(start_time)
#                 if end_time:
#                     sql += f" AND {time_col} <= %s"
#                     params.append(end_time)
                
#                 sql += f" ORDER BY {time_col} ASC"
                
#                 print(f"🚀 [動態 SQL 執行]: {sql}")
#                 cur.execute(sql, tuple(params))
#                 rows = cur.fetchall()

#                 # 4. 將撈出的 Tuple 轉換成 Dictionary
#                 formatted_rows = []
#                 for row in rows:
#                     row_dict = {}
#                     for i, col_name in enumerate(select_cols_list):
#                         row_dict[col_name] = row[i]
#                     formatted_rows.append(row_dict)

#                 # 5. 針對 ai_summarizer 的特殊需求進行資料分類與合成
#                 if table_name == "ENSDATA":
#                     patient_data["nursing"].extend(formatted_rows)
                    
#                 elif table_name == "v_ai_hisensnes":
#                     # 特別處理：合成 GCS 指數，因為 ai_summarizer 有手動抓取 'GCS'
#                     for r in formatted_rows:
#                         if all(k in r for k in ["GCS_E", "GCS_V", "GCS_M"]):
#                             r["GCS"] = f"E{r['GCS_E']}V{r['GCS_V']}M{r['GCS_M']}"
#                     patient_data["vitals"].extend(formatted_rows)
                    
#                 elif table_name in ["DB_ADM_LABDATA_ER", "DB_ADM_LABORDER_ER", "DB_ADM_ORDER_ER"]:
#                     # 將各種檢驗結果與狀態統一放入 labs 區塊
#                     patient_data["labs"].extend(formatted_rows)

#         print(f"✅ 成功撈取資料表: {', '.join(schema_queries.keys())}")
#         return patient_data

#     except psycopg2.Error as e:
#         print(f"❌ 資料庫查詢失敗: {e}")
#         return None
#     finally:
#         conn.close()

# def get_all_patients_overview():
#     """
#     從 ENSDATA 撈取所有病患清單及其就診時間範圍，用於前端儀表板選擇。
#     """
#     conn = get_db_connection()
#     if not conn: return []

#     overview_list = []
#     try:
#         with conn.cursor() as cur:
#             query = """
#                 SELECT PATID, 
#                        MIN(PROCDTTM) as start_time, 
#                        MAX(PROCDTTM) as end_time, 
#                        COUNT(*) as record_count
#                 FROM ENSDATA
#                 GROUP BY PATID
#                 ORDER BY start_time DESC
#                 LIMIT 50;
#             """
#             cur.execute(query)
#             rows = cur.fetchall()
            
#             for row in rows:
#                 overview_list.append({
#                     "病歷號": row[0],
#                     "最早紀錄": row[1],
#                     "最晚紀錄": row[2],
#                     "資料筆數": row[3]
#                 })
#         return overview_list
#     except psycopg2.Error as e:
#         print(f"查詢病患清單失敗: {e}")
#         return []
#     finally:
#         conn.close()

# def translate_to_chinese_view(data_list):
#     """
#     輔助函數：將資料列表中的英文 Key 翻譯成中文，僅供前端閱讀預覽使用。
#     """
#     if not data_list:
#         return []
    
#     view_list = []
#     for item in data_list:
#         new_item = {}
#         for key, value in item.items():
#             chinese_key = get_chinese_name(key)
#             new_item[chinese_key] = value
#         view_list.append(new_item)
#     return view_list


# 以下為oracle版本

import oracledb
from db.db_connector import get_db_connection

def get_all_patients_overview():
    """
    獲取所有病患的概況清單，用於前端介面的「選擇病患」下拉選單。
    這個函數會自己去 JOIN 主單與版本表，計算每位病人的資料筆數與時間範圍。
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            # Oracle 方言：使用 TO_CHAR 轉換時間格式，並用 LEFT JOIN 接上版本表
            sql = """
                SELECT 
                    r.PATIENT_ID, 
                    COUNT(r.POID) as doc_count,
                    MIN(TO_CHAR(rv.RECORD_TIME, 'YYYYMMDDHH24MISS')) as earliest_time,
                    MAX(TO_CHAR(rv.RECORD_TIME, 'YYYYMMDDHH24MISS')) as latest_time
                FROM RECORD r
                LEFT JOIN RECORD_VERSION rv ON r.POID = rv.RECORD_POID
                WHERE r.PATIENT_ID IS NOT NULL
                GROUP BY r.PATIENT_ID
                ORDER BY r.PATIENT_ID
            """
            cur.execute(sql)
            rows = cur.fetchall()

            result = []
            for row in rows:
                result.append({
                    "病歷號": row[0],
                    "資料筆數": row[1],
                    "最早紀錄": row[2] if row[2] else "",
                    "最晚紀錄": row[3] if row[3] else ""
                })
            return result
    except Exception as e:
        print(f"❌ 取得病患清單失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_patient_full_history(patient_id, start_time=None, schema_queries=None, full_schema=None):
    """
    根據使用者在畫面上勾選的 JSON 藍圖 (schema_queries)，
    動態組裝 Oracle SQL 語法，把三張表 JOIN 起來，並將結果轉換為 AI 容易閱讀的文字。
    """
    conn = get_db_connection()
    if not conn:
        return "無法連線到資料庫。"

    if not schema_queries:
        return "沒有選擇任何查詢欄位。"

    try:
        # 1. 動態組裝 SELECT 欄位
        select_cols = []
        
        # 設定資料表的縮寫 (Alias)，對應 SQL 語句
        table_aliases = {
            "RECORD": "r",
            "RECORD_VERSION": "rv",
            "RECORD_DETAIL": "rd"
        }

        # 根據前端傳來的 dictionary (如 {'RECORD': ['PATIENT_ID'], 'RECORD_DETAIL': ['CONTENT']})
        for table_name, cols in schema_queries.items():
            alias = table_aliases.get(table_name, "")
            for col in cols:
                select_cols.append(f"{alias}.{col}")

        # 將選取的欄位用逗號串接，如果沒選就預設全抓 (*)
        select_clause = ", ".join(select_cols) if select_cols else "*"

        # 2. 建立包含三張表關聯的 JOIN 語句 (使用 POID 與 RECORD_POID 串連)
        sql = f"""
            SELECT {select_clause}
            FROM RECORD r
            LEFT JOIN RECORD_VERSION rv ON r.POID = rv.RECORD_POID
            LEFT JOIN RECORD_DETAIL rd ON r.POID = rd.RECORD_POID
            WHERE r.PATIENT_ID = :patient_id
        """

        # 3. 綁定變數與時間篩選 (Oracle 使用 :變數名稱)
        params = {"patient_id": patient_id}
        
        if start_time:
            # Oracle 方言：使用 TO_DATE 把字串轉回時間格式進行比較
            sql += " AND rv.RECORD_TIME >= TO_DATE(:start_time, 'YYYYMMDDHH24MISS')"
            params["start_time"] = start_time
            
        # 依時間降序排列，讓最新的紀錄在最前面
        sql += " ORDER BY rv.RECORD_TIME DESC"

        # 4. 執行查詢
        with conn.cursor() as cur:
            cur.execute(sql, params)
            
            # 從 cursor.description 獲取真實的欄位名稱
            col_names = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            if not rows:
                return f"找不到病歷號 {patient_id} 的護理紀錄。"

            # 5. 格式化輸出給 AI 閱讀
            # 將資料庫撈出來的二維表格，轉換成一行一行的文字結構
            output_lines = [f"病歷號：{patient_id} 的護理紀錄\n" + "="*40]
            
            for row in rows:
                row_dict = dict(zip(col_names, row))
                record_block = []
                for key, value in row_dict.items():
                    if value is not None: 
                        # 處理特殊字元或時間物件，轉為字串
                        val_str = str(value).strip() 
                        record_block.append(f"[{key}]: {val_str}")
                
                output_lines.append("\n".join(record_block))
                output_lines.append("-" * 30)

            return "\n".join(output_lines)

    except Exception as e:
        error_msg = f"❌ 查詢病患紀錄失敗: {e}"
        print(error_msg)
        return error_msg
    finally:
        if conn:
            conn.close()