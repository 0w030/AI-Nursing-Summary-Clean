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
    獲取所有病患的「單次就醫」概況清單。
    改為使用 PATIENT_ID + ENCOUNTER_ID 進行群組化。
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            # 升級：同時撈取並 GROUP BY 就醫序號
            sql = """
                SELECT 
                    r.PATIENT_ID, 
                    r.ENCOUNTER_ID, 
                    COUNT(r.POID) as doc_count,
                    MIN(TO_CHAR(rv.RECORD_TIME, 'YYYYMMDDHH24MISS')) as earliest_time,
                    MAX(TO_CHAR(rv.RECORD_TIME, 'YYYYMMDDHH24MISS')) as latest_time
                FROM RECORD r
                LEFT JOIN RECORD_VERSION rv ON r.POID = rv.RECORD_POID AND rv.STATUS = 'Y'
                LEFT JOIN RECORD_DETAIL rd ON r.POID = rd.RECORD_POID
                WHERE r.PATIENT_ID IS NOT NULL AND r.ENCOUNTER_ID IS NOT NULL
                GROUP BY r.PATIENT_ID, r.ENCOUNTER_ID
                ORDER BY MAX(rv.RECORD_TIME) DESC
            """
            cur.execute(sql)
            rows = cur.fetchall()

            result = []
            for row in rows:
                result.append({
                    "病歷號": row[0],
                    "就醫序號": row[1],
                    "資料筆數": row[2],
                    "最早紀錄": row[3] if row[3] else "",
                    "最晚紀錄": row[4] if row[4] else ""
                })
            return result
    except Exception as e:
        print(f"❌ 取得就醫清單失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_patient_full_history(encounter_id, start_time=None, end_time=None, schema_queries=None, connection_mappings=None):
    """
    根據就醫序號和前端勾選的欄位，動態生成 SQL 並從資料庫撈取數據。
    
    改版：使用 config_manager 提供的電子辭典映射（connection_mappings），
    而不依賴靜態的 full_schema JSON 檔案。
    
    Args:
        encounter_id (str): 就醫序號，用於查詢單次就醫的紀錄
        start_time (str, optional): 起始時間 (YYYYMMDDHHMMSS)
        end_time (str, optional): 結束時間 (YYYYMMDDHHMMSS)
        schema_queries (dict): 前端傳來的勾選字典，格式如 {"RECORD": ["ENCOUNTER_ID", "SIGNSTATUS"]}
                              key: 表格名稱, value: 欄位的 db_column_name 清單
        connection_mappings (dict): 來自 config_manager.get_connection_mappings() 的映射資料
                                   格式為 {table_name: [FieldMapping, ...]}
    
    Returns:
        dict: 包含不同類型資料的字典，格式如 {"nursing": [...], "vitals": [...], "labs": [...]}
    """
    conn = get_db_connection()
    if not conn:
        print("無法建立連線，無法查詢病患資料。")
        return {"nursing": [], "vitals": [], "labs": []}

    # 初始化回傳結構，保持與 ai_summarizer 的相容性
    patient_data = {
        "nursing": [],
        "vitals": [],
        "labs": []
    }

    # 檢查是否都有收到必要資料
    # 若 schema_queries 和 connection_mappings 都未提供，返回空資料
    if not schema_queries or not connection_mappings:
        print("沒有提供查詢條件或 Schema 映射。")
        return patient_data

    try:
        with conn.cursor() as cur:
            # 遍歷使用者勾選的每一個資料表與欄位
            for table_name, selected_db_columns in schema_queries.items():
                if not selected_db_columns:
                    continue
                
                # 檢查該表在 connection_mappings 中是否存在
                if table_name not in connection_mappings:
                    print(f"警告：Schema 映射中找不到資料表 {table_name}")
                    continue
                
                table_field_mappings = connection_mappings[table_name]
                
                # 構建一個從 db_column_name 到 FieldMapping 的映射字典，方便查詢
                mapping_dict = {fm.db_column_name: fm for fm in table_field_mappings}
                
                # 驗證所有選中的欄位都在映射中存在
                valid_columns = []
                for db_col in selected_db_columns:
                    if db_col in mapping_dict:
                        valid_columns.append(db_col)
                    else:
                        print(f"警告：{table_name}.{db_col} 在 Schema 映射中不存在，跳過此欄位")
                
                if not valid_columns:
                    print(f"警告：{table_name} 沒有任何有效的欄位可查詢")
                    continue
                
                # 組裝 SQL SELECT 子句
                # 關鍵點：使用 db_column_name 而非系統欄位名稱來查詢
                cols_str = ", ".join(valid_columns)
                
                # 根據不同的表格確定時間過濾欄位
                # 此處假設主要查詢表使用 RECORD_TIME 作為時間欄位
                time_column = None
                for fm in table_field_mappings:
                    if "TIME" in fm.db_column_name.upper() and fm.is_confirmed:
                        time_column = fm.db_column_name
                        break
                
                # 取得該表的所有已知欄位 (大寫)
                all_db_cols = [fm.db_column_name.upper() for fm in table_field_mappings]
                
                # 判斷此表是用哪個欄位代表就醫序號
                encounter_col = None
                for candidate in ["ENCOUNTER_ID", "ENCOUNTERID", "VISIT_ID", "VISITID", "ADMISSION_ID", "HCASENO"]:
                    if candidate in all_db_cols:
                        encounter_col = candidate
                        break
                
                # 動態組裝 SQL 語法
                if encounter_col:
                    sql = f"SELECT {cols_str} FROM {table_name} WHERE {encounter_col} = :encounter_id"
                    params = {"encounter_id": encounter_id}
                else:
                    # 如果該表沒有就醫序號，尋找關聯欄位 (Fallback) 以支援「解法三」的主從表 JOIN
                    fk_col = None
                    # 尋找像是 RECORD_POID 這樣的外部鍵
                    for candidate in ["RECORD_POID", "RECORDPOID", "POID_REF", "MASTER_ID", "PARENT_ID"]:
                        if candidate in all_db_cols:
                            fk_col = candidate
                            break
                    
                    if fk_col:
                        # 嘗試猜測主表名稱 (通常是去掉 _DETAIL, _LOG 等後綴，或使用 RECORD)
                        parent_table = table_name.split('_')[0] if '_' in table_name else "RECORD"
                        # 許多系統的主表主鍵名稱為 POID 或 ID，這裡假設為 POID，並透過子查詢達成 JOIN 效果
                        sql = f"SELECT {cols_str} FROM {table_name} WHERE {fk_col} IN (SELECT POID FROM {parent_table} WHERE ENCOUNTER_ID = :encounter_id)"
                        params = {"encounter_id": encounter_id}
                        print(f"⚠️ 提示: 表格 {table_name} 無就醫序號欄位，嘗試使用關聯查詢: {sql}")
                    else:
                        print(f"❌ 錯誤: 資料表 {table_name} 中找不到 ENCOUNTER_ID 或已知的關聯欄位，跳過此表以防報錯。")
                        continue
                
                # 如果存在時間過濾，添加時間條件
                if time_column:
                    if start_time:
                        sql += f" AND {time_column} >= TO_TIMESTAMP(:start_time, 'YYYYMMDDHH24MISS')"
                        params["start_time"] = start_time
                    
                    if end_time:
                        sql += f" AND {time_column} <= TO_TIMESTAMP(:end_time, 'YYYYMMDDHH24MISS')"
                        params["end_time"] = end_time
                    
                    # 按時間排序
                    sql += f" ORDER BY {time_column} DESC"
                
                print(f"[動態 SQL 執行]: {sql}")
                print(f"[參數]: {params}")
                
                cur.execute(sql, params)
                col_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                # 將撈出的 Tuple 轉換成 Dictionary
                formatted_rows = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(col_names):
                        # 根據 system_column_type 進行資料清洗
                        if col_name in mapping_dict:
                            field_type = mapping_dict[col_name].system_column_type
                            value = row[i]
                            
                            # 簡單的資料清洗：去除空值和不必要的空格
                            if value is not None:
                                if field_type == "String":
                                    value = str(value).strip()
                                elif field_type in ["Integer", "Decimal"]:
                                    try:
                                        value = float(value) if "." in str(value) else int(value)
                                    except (ValueError, TypeError):
                                        value = None
                        
                        row_dict[col_name] = value
                    
                    formatted_rows.append(row_dict)
                
                # 根據表格名稱分類資料（保持與 ai_summarizer 的相容性）
                if "RECORD" in table_name.upper():
                    # 護理紀錄相關表
                    patient_data["nursing"].extend(formatted_rows)
                
                elif "VITAL" in table_name.upper() or "GCS" in table_name.upper():
                    # 生理監測相關表
                    patient_data["vitals"].extend(formatted_rows)
                
                elif any(lab_key in table_name.upper() for lab_key in ["LAB", "ORDER", "RESULT"]):
                    # 檢驗相關表
                    patient_data["labs"].extend(formatted_rows)
                
                else:
                    # 預設放入 nursing
                    patient_data["nursing"].extend(formatted_rows)
        
        print(f"成功撈取資料表: {', '.join(schema_queries.keys())}")
        return patient_data

    except Exception as e:
        print(f"❌ 資料庫查詢失敗: {e}")
        import traceback
        traceback.print_exc()
        return patient_data
    finally:
        if conn:
            conn.close()