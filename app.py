# app.py

import streamlit as st
import os
import pandas as pd
import json
from dotenv import load_dotenv
from datetime import datetime, time, timedelta
# from feedback_component import show_feedback_ui

# 引入後端模組
from db.patient_service import get_patient_full_history
from db.template_service import (
    get_all_templates, create_template, update_template,
    parse_uploaded_template
)
from ai.ai_summarizer import generate_nursing_summary
from db.auth_service import (
    authenticate_user, create_user, user_exists,
    get_all_users, search_users, get_user_count,
    update_user, reset_password, soft_delete_user, restore_user
)
<<<<<<< HEAD
from ai.rag_service import RAGService
try:
    rag_service = RAGService()
except Exception as e:
    st.error(f"RAG 服務初始化失敗: {e}")
    rag_service = None
=======
from services.permission_service import User, Role

>>>>>>> origin/sql_test

# --- ⚠️ 關鍵新增：在這裡啟動 .env 讀取器 ---
load_dotenv()

# --- 初始化登入狀態 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user = None

# --- 初始化頁面導航狀態 ---
if "current_app_page" not in st.session_state:
    st.session_state.current_app_page = "main"  # "main" 或 "management"

# --- 引入配置管理器（取代靜態 JSON） ---
from services.config_manager import config_manager

# --- 設定網頁 ---
st.set_page_config(page_title="AI 醫療模板系統", layout="wide", page_icon="🏥")

# ===== session_state 初始化 =====
if "preview_prompt" not in st.session_state:
    st.session_state.preview_prompt = ""

if "last_template_name" not in st.session_state:
    st.session_state.last_template_name = None

if "last_style_option" not in st.session_state:
    st.session_state.last_style_option = None

# ===== 摘要生成器步驟追蹤 =====
if "summary_step" not in st.session_state:
    st.session_state.summary_step = 1  # 1: 病患選取, 2: 參數設定與生成

if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

if "patient_search_keyword" not in st.session_state:
    st.session_state.patient_search_keyword = ""

if "patient_search_requested" not in st.session_state:
    st.session_state.patient_search_requested = False

# ===== 全域預設（避免 NameError）=====
selected_info = None
target_patient_id = None
earliest_dt = None

# ===== 讀取環境變數 (全面取代原本會報錯的 st.secrets) =====
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# 讀取 GROQ API Key (請確保你的 .env 檔案裡有一行 GROQ_API_KEY=你的金鑰)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TAB_LIBRARY = "模板庫管理"
TAB_CREATE = "建立新模板"
TAB_IMPORT = " 模板導入"

# ==========================================
# 輔助函數
# ==========================================
def format_time_str(raw_time):
    if not raw_time or len(str(raw_time)) < 12:
        return raw_time
    s = str(raw_time)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"

def get_first_matching_field(record: dict, candidates: list):
    for name in candidates:
        for key in record.keys():
            if key.upper() == name:
                return record[key]
    return None


def format_time_value(raw_value):
    if not raw_value:
        return "20260101000000"
    if isinstance(raw_value, datetime):
        return raw_value.strftime("%Y%m%d%H%M%S")
    raw_text = str(raw_value).strip()
    digits = "".join(ch for ch in raw_text if ch.isdigit())
    if len(digits) >= 14:
        return digits[:14]
    return raw_text


def create_test_patient_payload(row_dict: dict):
    patient_id = get_first_matching_field(row_dict, [
        "PATIENT_ID", "PATID", "PID", "PATIENTID", "PERSON_ID"
    ]) or "測試病患"
    encounter_id = get_first_matching_field(row_dict, [
        "ENCOUNTER_ID", "ENCOUNTERID", "VISIT_ID", "VISITID", "ADMISSION_ID"
    ]) or "0000000000"
    name_value = get_first_matching_field(row_dict, [
        "NAME", "PAT_NAME", "FULL_NAME", "PATIENT_NAME", "CUSTOMER_NAME"
    ]) or "測試病患"

    time_candidates = [
        "RECORD_TIME", "CREATE_TIME", "PROCDTTM", "ADMISSION_TIME", "DISCHARGE_TIME",
        "TIMESTAMP", "DATE_TIME", "EVENT_TIME"
    ]
    time_values = []
    for candidate in time_candidates:
        raw_time = get_first_matching_field(row_dict, [candidate])
        if raw_time:
            time_values.append(format_time_value(raw_time))

    if time_values:
        earliest_time = min(time_values)
        latest_time = max(time_values)
    else:
        earliest_time = latest_time = "20260101000000"

    doc_count = get_first_matching_field(row_dict, [
        "DOC_COUNT", "RECORD_COUNT", "COUNT", "資料筆數"
    ])
    if doc_count is None:
        doc_count = 1
    try:
        doc_count = int(doc_count)
    except Exception:
        doc_count = 1

    return {
        "病歷號": str(patient_id),
        "就醫序號": str(encounter_id),
        "姓名": str(name_value),
        "資料筆數": doc_count,
        "最早紀錄": earliest_time,
        "最晚紀錄": latest_time,
        "最早紀錄_顯示": format_time_str(earliest_time),
        "最晚紀錄_顯示": format_time_str(latest_time),
        "label": f"病歷號: {patient_id} | 就醫序號: {encounter_id} (共 {doc_count} 筆)"
    }


def load_test_patient_list_dynamic(table_name: str = "NISHBED"):
    """從當前活動連線動態載入前 10 筆病患測試資料。"""
    active_connection = config_manager.get_active_connection()
    if not active_connection:
        return []

    db_type = (active_connection.db_type or "").lower()
    host = active_connection.host
    port = active_connection.port
    database = active_connection.database
    user = active_connection.username
    password = active_connection.password

    conn = None
    cursor = None
    try:
        if db_type == "oracle":
            try:
                import oracledb
            except ImportError:
                st.error("Oracle 驅動尚未安裝，無法連接 Oracle 資料庫。")
                return []
            dsn = oracledb.makedsn(host, port, service_name=database)
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            query = f"SELECT * FROM {table_name} WHERE ROWNUM <= 10"
        elif db_type in ["postgresql", "postgres"]:
            try:
                import psycopg2
            except ImportError:
                st.error("PostgreSQL 驅動尚未安裝，無法連接 PostgreSQL 資料庫。")
                return []
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password
            )
            query = f"SELECT * FROM {table_name} LIMIT 10"
        elif db_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(database)
            query = f"SELECT * FROM {table_name} LIMIT 10"
        else:
            st.error(f"尚未支援的資料庫類型：{active_connection.db_type}")
            return []

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description] if cursor.description else []

        patient_list = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            patient_list.append(create_test_patient_payload(row_dict))

        return patient_list

    except Exception as error:
        st.error(f"病患清單載入失敗，請檢查資料庫連線與表格設定。錯誤訊息：{error}")
        return []

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# =========================================================================
# 摘要生成器步驟函式
# =========================================================================
def render_patient_selection():
    """步驟一：病患篩選與選取"""
    st.header("步驟一：選擇病患與就醫紀錄")

    patients_list = load_test_patient_list_dynamic()
    if not patients_list:
        st.error("無法取得病患清單，請確認當前資料庫連線是否已啟用。")
        return

    # 搜尋功能
    with st.form(key="patient_search_form"):
        search_keyword = st.text_input(
            "搜尋病患",
            value=st.session_state.patient_search_keyword,
            placeholder="輸入病歷號、就醫序號或姓名關鍵字...",
            help="支援病歷號、就醫序號或姓名的部分匹配搜尋"
        )
        search_button = st.form_submit_button("執行查詢")

    if search_button:
        st.session_state.patient_search_keyword = search_keyword
        st.session_state.patient_search_requested = True

    if st.session_state.patient_search_requested:
        keyword = st.session_state.patient_search_keyword.strip()
        filtered_patients = [
            p for p in patients_list
            if keyword.lower() in str(p.get('病歷號', '')).lower()
            or keyword.lower() in str(p.get('就醫序號', '')).lower()
            or keyword.lower() in str(p.get('姓名', '')).lower()
            or keyword.lower() in str(p.get('label', '')).lower()
        ]
        st.write(f"找到 {len(filtered_patients)} 位病患")

        if not filtered_patients:
            st.warning("未找到符合條件的病患，請確認輸入後點擊「執行查詢」。")
            return
    else:
        filtered_patients = patients_list
        if search_keyword:
            st.info("輸入關鍵字後請點擊「執行查詢」，以便系統進行查詢。")
        else:
            st.info("請輸入搜尋關鍵字或直接從下方清單選擇病患。")

    # 病患清單展示
    if len(filtered_patients) <= 50:  # 小量數據使用 selectbox
        options = ["請選擇病患..."] + [p['label'] for p in filtered_patients]
        selected_label = st.selectbox("病患清單", options, index=0)

        selected_patient = None
        if selected_label != "請選擇病患...":
            selected_patient = next((p for p in filtered_patients if p['label'] == selected_label), None)
    else:  # 大量數據使用 dataframe
        # 準備顯示數據
        display_data = []
        for p in filtered_patients:
            display_data.append({
                '病歷號': p['病歷號'],
                '姓名': p.get('姓名', '未知'),
                '就醫序號': p['就醫序號'],
                '資料筆數': p['資料筆數'],
                '最早紀錄': p['最早紀錄_顯示'],
                '最晚紀錄': p['最晚紀錄_顯示']
            })

        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True)

        # 手動輸入選擇
        selected_patient_id = st.text_input(
            "請輸入欲選取的就醫序號",
            help="從上方表格中選擇對應的就醫序號"
        )

        selected_patient = None
        if selected_patient_id:
            selected_patient = next((p for p in filtered_patients if str(p['就醫序號']) == selected_patient_id), None)
            if not selected_patient:
                st.error("無效的就醫序號，請重新輸入。")

    # 確認選取按鈕
    if selected_patient:
        st.success(f"已選取病患：{selected_patient['病歷號']} / 就醫序號：{selected_patient['就醫序號']}")
        st.write("請按下方按鈕確認選取並進入下一步。")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("確定選擇並下一步", type="primary", use_container_width=True):
                st.session_state.selected_patient = selected_patient
                st.session_state.summary_step = 2
                st.rerun()

        with col2:
            if st.button("重新搜尋", use_container_width=True):
                st.session_state.patient_search_keyword = ""
                st.session_state.patient_search_requested = False


def render_summary_config():
    """步驟二：生成參數設定與執行"""
    st.header("步驟二：設定生成參數")
    
    # 檢查是否已選取病患
    if not st.session_state.selected_patient:
        st.error("請先返回步驟一選取病患。")
        if st.button("返回病患選取"):
            st.session_state.summary_step = 1
            st.rerun()
        return
    
    selected_patient = st.session_state.selected_patient
    
    # 顯示已選取的病患資訊
    st.subheader("已選取的病患資訊")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("病歷號", selected_patient['病歷號'])
    with col2:
        st.metric("就醫序號", str(selected_patient['就醫序號']))
    with col3:
        st.metric("資料筆數", selected_patient['資料筆數'])
    
    st.write(f"最早紀錄：{selected_patient['最早紀錄_顯示']}")
    st.write(f"最晚紀錄：{selected_patient['最晚紀錄_顯示']}")
    
    if st.button("重新選擇病患"):
        st.session_state.selected_patient = None
        st.session_state.summary_step = 1
        st.rerun()
    
    st.divider()
    
    # 設定最早時間
    earliest_dt = None
    if selected_patient.get("最早紀錄"):
        raw_time = selected_patient["最早紀錄"]
        earliest_dt = datetime.strptime(raw_time, "%Y%m%d%H%M%S")
    
    # 檢查資料庫連接
    active_connection = config_manager.get_active_connection()
    if not active_connection:
        st.warning("請先至「管理中控台」設定並啟用資料庫連接。在完成連接設置前，無法生成摘要。")
        return
    
    connection_mappings = config_manager.get_connection_mappings(active_connection.name)
    if not connection_mappings or len(connection_mappings) == 0:
        st.warning(f"連接「{active_connection.name}」尚無 Schema 映射。請先至「管理中控台」進行 Schema 同步。")
        return
    
    # 資料來源範圍選擇
    st.subheader("資料來源範圍")
    selected_queries = {}
    
    for table_name, field_mappings in connection_mappings.items():
        if not field_mappings:
            continue
        
        # 特殊過濾規則：NISHBED 表
        if table_name.upper() == "NISHBED":
            nishbed_core_fields = {
                "PATIENT_ID", "BED_ID", "ADMISSION_TIME", "DISCHARGE_TIME", 
                "WARD_ID", "CLINICAL_STATUS", "VITAL_SIGNS", "CARE_PLAN", 
                "PROCEDURE_LOG", "DIAGNOSIS"
            }
            filtered_mappings = [
                fm for fm in field_mappings
                if fm.db_column_name.upper() in nishbed_core_fields and fm.is_confirmed
            ]
            if len(filtered_mappings) > 10:
                filtered_mappings = filtered_mappings[:10]
        else:
            filtered_mappings = [fm for fm in field_mappings if fm.is_confirmed]
        
        if not filtered_mappings:
            continue
        
        with st.expander(f"資料表：{table_name}", expanded=True):
            selected_cols = []
            cols = st.columns(3)
            
            for i, field_mapping in enumerate(filtered_mappings):
                db_col_name = field_mapping.db_column_name
                system_col_type = field_mapping.system_column_type
                
                checkbox_label = f"{db_col_name} ({system_col_type})"
                if field_mapping.is_ai_suggested:
                    checkbox_label += " [AI建議]"
                else:
                    checkbox_label += " [已確認]"
                
                is_checked = cols[i % 3].checkbox(
                    label=checkbox_label,
                    value=False,
                    key=f"chk_{table_name}_{db_col_name}"
                )
                
                if is_checked:
                    selected_cols.append(db_col_name)
            
            if selected_cols:
                selected_queries[table_name] = selected_cols
    
    # 模板選擇
    st.subheader("摘要模板選擇")
    db_templates = get_all_templates()
    template_names = list(db_templates.keys())
    
    if not template_names:
        st.error("資料庫中沒有模板，請聯繫管理員。")
        return
    
    selected_template_name = st.selectbox("請選擇適用情境", template_names, index=0)
    
    # 呈現風格
    style_option = st.radio("呈現風格", ["列點式 (Bullet Points)", "短文式 (Narrative)"], horizontal=True)
    
    # Prompt 處理
    if (selected_template_name != st.session_state.last_template_name or 
        style_option != st.session_state.last_style_option):
        base_prompt = db_templates[selected_template_name]
        style_instruction = (
            "\n\n【格式要求】：請整合為一篇流暢的短文，禁止使用列點。"
            if style_option == "短文式 (Narrative)"
            else "\n\n【格式要求】：請務必使用列點方式呈現，保持條理。"
        )
        st.session_state.preview_prompt = base_prompt + style_instruction
        st.session_state.last_template_name = selected_template_name
        st.session_state.last_style_option = style_option
    
    # Prompt 編輯
    st.subheader("Prompt 編輯")
    edited_prompt = st.text_area(
        "系統提示詞",
        value=st.session_state.preview_prompt,
        height=200
    )
    st.session_state.preview_prompt = edited_prompt
    
    # 關注項目
    st.subheader("重點關注項目")
    focus_options = ["生命徵象趨勢", "檢驗報告異常值", "護理處置經過", "病患主訴", "管路狀況", "意識狀態(GCS)"]
    
    default_focus = []
    if "會診" in selected_template_name:
        default_focus = ["檢驗報告異常值", "生命徵象趨勢"]
    elif "交班" in selected_template_name:
        default_focus = ["護理處置經過", "意識狀態(GCS)"]
    elif "出院" in selected_template_name:
        default_focus = ["護理處置經過", "生命徵象趨勢"]
    
    selected_focus_areas = []
    cols = st.columns(3)
    for i, option in enumerate(focus_options):
        if cols[i % 3].checkbox(option, value=option in default_focus):
            selected_focus_areas.append(option)
    
    # 時間篩選
    st.subheader("時間篩選")
    use_time_filter = st.toggle("啟用時間篩選", help="只分析指定時間之後的記錄")
    start_dt_str = None
    
    if use_time_filter:
        default_datetime = earliest_dt if earliest_dt else datetime.now() - timedelta(days=1)
        c1, c2 = st.columns(2)
        d1 = c1.date_input("開始日期", default_datetime.date())
        t1 = c2.time_input("開始時間", default_datetime.time())
        combined_dt = datetime.combine(d1, t1)
        start_dt_str = combined_dt.strftime("%Y%m%d%H%M%S")
    
    # 生成按鈕
    if not selected_queries:
        st.warning("請至少選擇一個資料來源的欄位。")
        return
    
    if st.button("開始生成摘要", type="primary", use_container_width=True):
        load_dotenv()
        if not os.getenv("GROQ_API_KEY"):
            st.error("未設定 API 金鑰")
            return
        
        with st.spinner("正在分析資料並生成摘要..."):
            active_conn = config_manager.get_active_connection()
            active_mappings = config_manager.get_connection_mappings(active_conn.name)
            
            p_data = get_patient_full_history(
                selected_patient['就醫序號'],
                start_time=start_dt_str,
                schema_queries=selected_queries,
                connection_mappings=active_mappings
            )
            
            summary = generate_nursing_summary(
                selected_patient['就醫序號'],
                p_data,
                selected_template_name,
                custom_system_prompt=st.session_state.preview_prompt,
                focus_areas=selected_focus_areas
            )
            
            st.markdown("### 生成結果")
            st.markdown("---")
            st.markdown(summary)


# =========================================================================
# 模板導入相關輔助函數
# =========================================================================
def show_single_template_import_form(content):
    """顯示單個模板導入表單"""
    st.subheader("第 2 步：設定模板信息")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            template_name = st.text_input(
                "模板名稱 *",
                placeholder="例如：重大創傷急救紀錄",
                help="此名稱會在模板庫中顯示"
            )
        
        with col2:
            template_description = st.text_input(
                "模板說明 (選填)",
                placeholder="例如：用於記錄重大創傷患者的急救流程",
                help="簡短說明此模板的用途"
            )
    
    st.subheader("第 2.5 步：編輯模板內容（可選）")
    st.caption("您可以直接編輯從文件中提取的內容，或保持原樣")
    
    edited_content = st.text_area(
        "模板內容 (Prompt)",
        value=content,
        height=350,
        help="這是將用於 AI 推理的 System Prompt"
    )
    
    st.divider()
    st.subheader("第 3 步：確認導入")
    
    col_submit, col_cancel = st.columns(2)
    
    with col_submit:
        if st.button("✅ 導入模板", type="primary", use_container_width=True):
            if not template_name:
                st.error("❌ 模板名稱不能為空！")
            elif not edited_content:
                st.error("❌ 模板內容不能為空！")
            else:
                with st.spinner("正在導入模板..."):
                    success = create_template(template_name, edited_content, template_description)
                
                if success:
                    st.success(f"✅ 模板「{template_name}」已成功導入！")
                    st.balloons()
                    st.cache_data.clear()
                    st.session_state.import_extracted_content = ""
                    st.session_state.import_uploaded_file = None
                    # 自動導向到模板庫
                    st.session_state.template_tab = TAB_LIBRARY
                    st.rerun()
                else:
                    st.error("❌ 導入失敗：模板名稱可能已存在或其他錯誤")
    
    with col_cancel:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state.import_extracted_content = ""
            st.session_state.import_uploaded_file = None
            st.rerun()

# ==========================================
# 登入與權限分流邏輯
# ==========================================
if not st.session_state.logged_in:
    # 🔴 畫面 A：未登入時，只顯示登入表單
    st.title(" AI 護理交班系統 - 請先登入")
    
    with st.form("login_form"):
        st.subheader("系統登入")
        username = st.text_input("帳號")
        password = st.text_input("密碼", type="password")
        submit = st.form_submit_button("登入")
        
        if submit:
            # 呼叫 auth_service 裡的真實資料庫驗證函數
            user_role = authenticate_user(username, password)
            
            if user_role:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user_role
                # 將字符串角色轉換為 Role 枚舉對象
                user_role_enum = Role(user_role)
                st.session_state.user = User(username=username, role=user_role_enum, is_active=True)
                st.rerun() # 重新整理網頁，進入系統
            else:
                st.error("帳號或密碼錯誤！")

else:
    # 🟢 畫面 B：已登入，根據權限顯示對應功能
    with st.sidebar:
        st.title(" 醫療摘要系統")
        st.markdown(f"👤 登入者: **{st.session_state.username}** ({st.session_state.role})")
        
        # 頁面選擇（使用 key 來記住選擇）
        st.markdown("---")
        st.subheader("應用導航")
        
        current_page = st.radio(
            "選擇功能",
            ["主應用", "管理中控台"],
            label_visibility="collapsed",
            key="app_page_choice",
            index=0  # 預設選擇「主應用」
        )
        
        if current_page == "管理中控台":
            st.switch_page("pages/management_dashboard.py")
        
        st.markdown("---")
        if st.button("登出", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        st.divider()

        # 🔑 權限分流核心邏輯
        if st.session_state.role == "user":
            st.info("您目前的權限僅能使用「摘要生成」功能。")
            app_mode = " 摘要生成器"
        elif st.session_state.role == "admin":
            # Admin 可以訪問管理員功能
            app_mode = st.radio(
                "請選擇功能模式：",
                [" 摘要生成器", " 模板設計師", " 👥 人員管理", "測試視窗"],
                index=0
            )
        else:
            # Manager 和其他角色
            app_mode = st.radio(
                "請選擇功能模式：",
                [" 摘要生成器", " 模板設計師"],
                index=0
            )
            
        st.divider()

    # ==============================================================================
    # 模式 A：摘要生成器 (使用者模式)
    # ==============================================================================
    if app_mode == " 摘要生成器":
        st.header(" AI 急診病程摘要生成")
<<<<<<< HEAD
        
        # 1. 選擇病患 (升級版)
        st.subheader("1. 選擇病患與就醫紀錄")
        options = ["請選擇..."] + [p['label'] for p in patients_list]
        selected_label = st.selectbox("就醫清單：", options, index=0)
        
        target_encounter_id = None
        target_patient_id = None
        selected_info = None
        if selected_label != "請選擇...":
            selected_info = next((p for p in patients_list if p['label'] == selected_label), None)
            target_encounter_id = selected_info['就醫序號']
            target_patient_id = selected_info['病歷號']
            patient_id_display = selected_info['病歷號']
            st.success(f"已選定病患：{patient_id_display} / 就醫序號：{target_encounter_id}")
=======
>>>>>>> origin/sql_test

        # 添加步驟指示器
        step_names = ["病患選取", "參數設定與生成"]
        current_step_name = step_names[st.session_state.summary_step - 1]

        # 顯示進度條
        progress = (st.session_state.summary_step - 1) / len(step_names)
        st.progress(progress, text=f"步驟 {st.session_state.summary_step}: {current_step_name}")

        # 重置按鈕
        if st.button("🔄 重新開始", help="重置所有選擇並從頭開始"):
            st.session_state.summary_step = 1
            st.session_state.selected_patient = None
            st.session_state.patient_search_keyword = ""
            st.rerun()

        st.divider()

<<<<<<< HEAD
        # 2. 選擇模板
        st.subheader("2. 選擇摘要模板")
        db_templates = get_all_templates()
        template_names = list(db_templates.keys())
        
        if not template_names:
            st.error("資料庫中沒有模板，請先切換到「模板設計師」建立模板！")
            st.stop()
            
        selected_template_name = st.selectbox("請選擇適用情境：", template_names, index=0)

        # 3. 呈現風格
        style_option = st.radio("呈現風格：", ["列點式 (Bullet Points)", "短文式 (Narrative)"], horizontal=True)

        # ===== 模板或呈現風格變更時，自動刷新 Prompt =====
        if (
            selected_template_name != st.session_state.last_template_name
            or style_option != st.session_state.last_style_option
        ):
            base_prompt = db_templates[selected_template_name]

            style_instruction = (
                "\n\n【格式要求】：請整合為一篇流暢的短文，禁止使用列點。"
                if style_option == "短文式 (Narrative)"
                else "\n\n【格式要求】：請務必使用列點方式呈現，保持條理。"
            )

            st.session_state.preview_prompt = base_prompt + style_instruction
            st.session_state.last_template_name = selected_template_name
            st.session_state.last_style_option = style_option

        # ===== Prompt 預覽 / 修改 =====
        st.subheader("3. Prompt 預覽與編輯")
        edited_prompt = st.text_area(
            "即將送入 AI 的 System Prompt（可直接修改）",
            value=st.session_state.preview_prompt,
            height=300
        )
        st.session_state.preview_prompt = edited_prompt

        # 4. 關注點
        st.subheader("4. 重點關注項目")
        st.write("請勾選 **重點關注項目** (AI 將加強分析)：")
        
        focus_options = ["生命徵象趨勢", "檢驗報告異常值", "護理處置經過", "病患主訴", "管路狀況", "意識狀態(GCS)"]
        
        default_focus = []
        if "會診" in selected_template_name:
            default_focus = ["檢驗報告異常值", "生命徵象趨勢"]
        elif "交班" in selected_template_name:
            default_focus = ["護理處置經過", "意識狀態(GCS)"]
        elif "出院" in selected_template_name:
            default_focus = ["護理處置經過", "生命徵象趨勢"]
        
        selected_focus_areas = []
        cols = st.columns(3)
        for i, option in enumerate(focus_options):
            if cols[i % 3].checkbox(option, value=option in default_focus):
                selected_focus_areas.append(option)

        # 5. 起始時間篩選
        is_expanded = st.session_state.get("time_toggle_state", False)
        
        with st.expander("護理紀錄時間篩選 (選填)", expanded=is_expanded):
            # 加上 key="time_toggle_state" 讓系統記住狀態
            use_time_filter = st.toggle(
                "啟用時間篩選", 
                key="time_toggle_state",
                help="開啟後，AI 只會讀取指定時間點之後的護理紀錄"
            )
            start_dt_str = None

            if use_time_filter:
                default_datetime = earliest_dt if earliest_dt else datetime.now() - timedelta(days=1)
                default_date = default_datetime.date()
                default_time = default_datetime.time()

                st.caption("請選擇要從哪一個時間點開始讀取紀錄：")
                c1, c2 = st.columns(2)
                d1 = c1.date_input("開始日期", default_date)
                t1 = c2.time_input("開始時間", default_time)

                combined_dt = datetime.combine(d1, t1)
                start_dt_str = combined_dt.strftime("%Y%m%d%H%M%S")

        # ===== 新增：模型選擇 UI =====
        st.divider()
        st.subheader("⚙️ AI 模型設置")
        
        col_model, col_info = st.columns([2, 3])
        
        with col_model:
            model_choice = st.radio(
                "選擇 AI 模型：",
                options=["自動選擇 (優先本地)", "強制使用本地模型", "強制使用 Groq API"],
                index=0,
                help="本地模型快速離線 | Groq 高精度"
            )
        
        # 模型映射
        model_map = {
            "自動選擇 (優先本地)": "auto",
            "強制使用本地模型": "local",
            "強制使用 Groq API": "groq"
        }
        selected_model_source = model_map[model_choice]
        
        with col_info:
            if selected_model_source == "auto" or selected_model_source == "local":
                st.info("🖥️ **本地模型**: Mistral 7B\n- ✅ 離線運作\n- ✅ 隱私保護\n- ⚡ 推理快速", icon="ℹ️")
            else:
                st.info("☁️ **Groq API**: Llama 3.3 70B\n- ✅ 高精度\n- ⚠️ 需要網路\n- 💰 計費", icon="ℹ️")
        
        st.divider()
        # ===== 結束：模型選擇 UI =====

        # 6. 執行按鈕
        if target_encounter_id:
            if st.button(" 開始生成摘要", type="primary", use_container_width=True):
                
                load_dotenv()
                if not os.getenv("GROQ_API_KEY"):
                    st.error("未設定 API Key")
                    st.stop()
                    
                if not selected_queries:
                    st.error("請至少選擇一個資料來源的欄位。")
                    st.stop()
                    
                with st.spinner("正在分析資料並撰寫摘要..."):
                    p_data = get_patient_full_history(
                        target_encounter_id, 
                        start_time=start_dt_str, 
                        schema_queries=selected_queries,
                        full_schema= hospital_schema
                    )

                    summary = generate_nursing_summary(
                        target_encounter_id,
                        p_data,
                        selected_template_name,
                        custom_system_prompt=st.session_state.preview_prompt,
                        focus_areas=selected_focus_areas,
                        model_source=selected_model_source
                    )

                    st.markdown("###  生成結果 (請確認並可自由修改)")
                    st.markdown("---")
                    
                    # 讓使用者可以編輯生成的摘要
                    final_summary = st.text_area("摘要內容", value=summary, height=400)
                    
                    # 加入一個儲存按鈕
                    if st.button("💾 確認並儲存摘要 (這將幫助 AI 學習)", type="primary"):
                        if rag_service:
                            try:
                                # 把「原始病歷(p_data)」和「最終修改後的摘要(final_summary)」存起來
                                rag_service.add_memory(
                                    encounter_id=target_encounter_id,
                                    raw_data=p_data,
                                    final_summary=final_summary
                                )
                                st.success("✅ 摘要已儲存！AI 已經學習了您的修改，下次會表現得更好。")
                            except Exception as e:
                                st.error(f"儲存記憶失敗: {e}")
                        else:
                            st.warning("RAG 服務未啟動，無法儲存學習記憶。")
=======
        # 根據當前步驟渲染對應的介面
        if st.session_state.summary_step == 1:
            render_patient_selection()
        elif st.session_state.summary_step == 2:
            render_summary_config()
>>>>>>> origin/sql_test


    # ==============================================================================
    # 模式 C：人員管理 (Admin 專用)
    # ==============================================================================
    if app_mode == " 👥 人員管理":
        # 路由守衛：確保只有 admin 可以訪問
        if st.session_state.role != "admin":
            st.error(" 403 禁止訪問：您沒有權限訪問此頁面！")
            st.info("只有管理員（Admin）可以訪問人員管理功能。")
            st.stop()
        
        st.header("人員管理中心")
        st.markdown("在此頁面，您可以新增不同角色的使用者帳號。")
        
        # 頁籤：新增人員 / 帳號列表
        tab1, tab2 = st.tabs([" 新增人員", " 帳號管理"])
        
        # ======= Tab 1：新增人員 =======
        with tab1:
            st.subheader("新增人員帳號")
            st.markdown("請填寫以下表單，新增不同角色的帳號：")
            
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    full_name = st.text_input(
                        "姓名",
                        placeholder="例如：王小明",
                        help="新增人員的真實姓名"
                    )
                
                with col2:
                    username = st.text_input(
                        "帳號（Email 或 Username）",
                        placeholder="例如：wang.xiaoming@hospital.com 或 wwang",
                        help="帳號必須唯一，不可重複"
                    )
                
                col3, col4 = st.columns(2)
                
                with col3:
                    password = st.text_input(
                        "密碼",
                        type="password",
                        placeholder="至少 6 個字符",
                        help="密碼將被加密儲存"
                    )
                
                with col4:
                    password_confirm = st.text_input(
                        "確認密碼",
                        type="password",
                        placeholder="請再次輸入密碼",
                        help="必須與上方密碼相同"
                    )
                
                col5, col6 = st.columns(2)
                
                with col5:
                    role = st.selectbox(
                        "角色選擇",
                        options=["user", "manager"],
                        format_func=lambda x: {
                            "user": "一般使用者（User）",
                            "manager": "護理主任（Manager）"
                        }[x],
                        help="選擇新增人員的系統角色"
                    )
                
                with col6:
                    department = st.text_input(
                        "部門",
                        placeholder="例如：急診科",
                        help="這是額外參考信息，不影響系統權限"
                    )
                
                # 備註
                notes = st.text_area(
                    "備註（選填）",
                    placeholder="例如：新進人員，需要培訓...",
                    height=100,
                    help="適用於內部備忘"
                )
                
                submit_button = st.form_submit_button(
                    " 確認新增",
                    use_container_width=True,
                    type="primary"
                )
                
                # ===== 表單驗證與提交 =====
                if submit_button:
                    # 驗證輸入
                    errors = []
                    
                    if not full_name or len(full_name.strip()) < 2:
                        errors.append("姓名至少需要 2 個字符")
                    
                    if not username or len(username.strip()) < 3:
                        errors.append("帳號至少需要 3 個字符")
                    
                    if not password or len(password) < 6:
                        errors.append("密碼至少需要 6 個字符")
                    
                    if password != password_confirm:
                        errors.append("密碼與確認密碼不相符")
                    
                    if "@" in username and "." not in username.split("@")[1]:
                        errors.append("Email 格式不正確")
                    
                    # 顯示錯誤
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        # 調用後端 API 創建用戶
                        result = create_user(username, password, role)
                        
                        if result['success']:
                            st.success(result['message'])
                            st.info(
                                f"**帳號資訊彙總**\n\n"
                                f"- 帳號：`{username}`\n"
                                f"- 角色：{role}\n"
                                f"- 部門：{department if department else '未指定'}\n\n"
                                f"該帳號現在可以正常登入系統。"
                            )
                        else:
                            st.error(result['message'])
        
        # ======= Tab 2：帳號管理（完整 CRUD） =======
        with tab2:
            st.subheader("👥 帳號列表與管理")
            
            # 初始化分頁相關的 session state
            if "page_number" not in st.session_state:
                st.session_state.page_number = 1
            if "search_keyword" not in st.session_state:
                st.session_state.search_keyword = ""
            if "role_filter" not in st.session_state:
                st.session_state.role_filter = ""
            if "edit_user_id" not in st.session_state:
                st.session_state.edit_user_id = None
            if "delete_confirm_id" not in st.session_state:
                st.session_state.delete_confirm_id = None
            
            # ========== 搜尋和篩選 ==========
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                search_keyword = st.text_input(
                    "🔍 搜尋帳號或姓名",
                    value=st.session_state.search_keyword,
                    placeholder="輸入帳號或姓名以搜尋用戶"
                )
                st.session_state.search_keyword = search_keyword
            
            with col2:
                role_filter_selected = st.selectbox(
                    "🎯 按角色篩選",
                    options=["全部", "admin", "manager", "user"],
                    format_func=lambda x: {
                        "全部": "全部角色",
                        "admin": "管理員",
                        "manager": "護理主任",
                        "user": "一般使用者"
                    }.get(x, x),
                    index=0 if not st.session_state.role_filter else (
                        ["", "admin", "manager", "user"].index(st.session_state.role_filter)
                        if st.session_state.role_filter in ["", "admin", "manager", "user"]
                        else 0
                    )
                )
                # 轉換選中的值
                role_filter = "" if role_filter_selected == "全部" else role_filter_selected
                st.session_state.role_filter = role_filter
            
            with col3:
                if st.button("重置篩選", use_container_width=True):
                    st.session_state.search_keyword = ""
                    st.session_state.role_filter = ""
                    st.session_state.page_number = 1
                    st.rerun()
            
            st.divider()
            
            # ========== 獲取數據 ==========
            if st.session_state.search_keyword or st.session_state.role_filter:
                filtered_users = search_users(
                    st.session_state.search_keyword,
                    st.session_state.role_filter
                )
                total_users = len(filtered_users)
            else:
                filtered_users = get_all_users()
                total_users = get_user_count()
            
            # ========== 分頁設置 ==========
            items_per_page = 10
            total_pages = (total_users + items_per_page - 1) // items_per_page
            
            # 確保當前頁碼有效
            if st.session_state.page_number > total_pages and total_pages > 0:
                st.session_state.page_number = total_pages
            elif st.session_state.page_number < 1:
                st.session_state.page_number = 1
            
            # 計算當前頁的起始和結束索引
            start_idx = (st.session_state.page_number - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_users = filtered_users[start_idx:end_idx]
            
            # ========== 顯示用戶統計 ==========
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("總用戶數", total_users)
            with col_stats2:
                active_count = sum(1 for u in get_all_users() if not u['is_deleted'])
                st.metric("活躍用戶", active_count)
            with col_stats3:
                if total_pages > 0:
                    st.metric("當前頁", f"{st.session_state.page_number} / {total_pages}")
            
            st.divider()
            
            # ========== 用戶表格 ==========
            if page_users:
                # 準備表格數據
                table_data = []
                for user in page_users:
                    role_display = {
                        'admin': '👨‍💼 管理員',
                        'manager': '📋 護理主任',
                        'user': '👤 一般使用者'
                    }.get(user['role'], user['role'])
                    
                    status = "❌ 已停用" if user['is_deleted'] else "✅ 活躍"
                    
                    table_data.append({
                        'ID': user['id'],
                        '帳號': user['username'],
                        '姓名': user['display_name'],
                        '角色': role_display,
                        '狀態': status,
                        '建立時間': user['created_at'][:10]  # 只顯示日期部分
                    })
                
                # 顯示表格
                st.dataframe(
                    pd.DataFrame(table_data),
                    use_container_width=True,
                    hide_index=True
                )
                
                # ========== 操作按鈕 ==========
                st.markdown("**📝 操作**")
                
                for user in page_users:
                    col_id, col_user, col_actions = st.columns([1, 2, 3])
                    
                    with col_id:
                        st.write(f"ID: {user['id']}")
                    
                    with col_user:
                        st.write(f"{user['username']} ({user['display_name']})")
                    
                    with col_actions:
                        action_cols = st.columns([1, 1, 1])
                        
                        with action_cols[0]:
                            if st.button("✏️ 編輯", key=f"edit_{user['id']}", use_container_width=True):
                                st.session_state.edit_user_id = user['id']
                        
                        with action_cols[1]:
                            if st.button("🔐 重設密碼", key=f"reset_{user['id']}", use_container_width=True):
                                st.session_state.edit_mode = "reset_password"
                                st.session_state.edit_user_id = user['id']
                        
                        with action_cols[2]:
                            if not user['is_deleted'] and user['role'] != 'admin':
                                if st.button("🗑️ 刪除", key=f"delete_{user['id']}", use_container_width=True):
                                    st.session_state.delete_confirm_id = user['id']
                            elif user['is_deleted']:
                                if st.button("↩️ 恢復", key=f"restore_{user['id']}", use_container_width=True):
                                    result = restore_user(user['id'])
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
            else:
                st.info("📭 沒有找到符合條件的用戶")
            
            # ========== 分頁控制 ==========
            if total_pages > 1:
                st.divider()
                col_prev, col_page, col_next = st.columns([1, 3, 1])
                
                with col_prev:
                    if st.button("⬅️ 上一頁", use_container_width=True):
                        st.session_state.page_number = max(1, st.session_state.page_number - 1)
                        st.rerun()
                
                with col_page:
                    st.markdown(f"<div style='text-align:center'>📄 第 {st.session_state.page_number} / {total_pages} 頁</div>", 
                               unsafe_allow_html=True)
                
                with col_next:
                    if st.button("下一頁 ➡️", use_container_width=True):
                        st.session_state.page_number = min(total_pages, st.session_state.page_number + 1)
                        st.rerun()
            
            # ========== 編輯對話框 ==========
            if st.session_state.edit_user_id is not None:
                st.divider()
                st.subheader("✏️ 編輯用戶信息")
                
                # 獲取用戶信息
                current_user = None
                for u in get_all_users(include_deleted=True):
                    if u['id'] == st.session_state.edit_user_id:
                        current_user = u
                        break
                
                if current_user:
                    with st.form("edit_user_form"):
                        col_form1, col_form2 = st.columns(2)
                        
                        with col_form1:
                            st.text_input(
                                "帳號（唯讀）",
                                value=current_user['username'],
                                disabled=True,
                                help="帳號無法修改"
                            )
                        
                        with col_form2:
                            display_name = st.text_input(
                                "姓名",
                                value=current_user['display_name']
                            )
                        
                        new_role = st.selectbox(
                            "角色",
                            options=["admin", "manager", "user"],
                            index=["admin", "manager", "user"].index(current_user['role']),
                            format_func=lambda x: {
                                "admin": "👨‍💼 管理員",
                                "manager": "📋 護理主任",
                                "user": "👤 一般使用者"
                            }[x]
                        )
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            if st.form_submit_button("💾 保存修改", use_container_width=True):
                                updates = {}
                                if display_name != current_user['display_name']:
                                    updates['display_name'] = display_name
                                if new_role != current_user['role']:
                                    updates['role'] = new_role
                                
                                if updates:
                                    result = update_user(st.session_state.edit_user_id, updates)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.session_state.edit_user_id = None
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                                else:
                                    st.info("沒有進行任何修改")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ 取消", use_container_width=True):
                                st.session_state.edit_user_id = None
                                st.rerun()
            
            # ========== 重設密碼對話框 ==========
            if st.session_state.get("edit_mode") == "reset_password" and st.session_state.edit_user_id is not None:
                st.divider()
                st.subheader("🔐 重設密碼")
                
                current_user = None
                for u in get_all_users(include_deleted=True):
                    if u['id'] == st.session_state.edit_user_id:
                        current_user = u
                        break
                
                if current_user:
                    with st.form("reset_password_form"):
                        st.info(f"正在重設 {current_user['username']} 的密碼")
                        
                        new_password = st.text_input(
                            "新密碼",
                            type="password",
                            placeholder="至少 6 個字符"
                        )
                        
                        confirm_password = st.text_input(
                            "確認新密碼",
                            type="password",
                            placeholder="重新輸入密碼"
                        )
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            if st.form_submit_button("✅ 重設密碼", use_container_width=True):
                                if not new_password:
                                    st.error("請輸入新密碼")
                                elif new_password != confirm_password:
                                    st.error("密碼不相符，請重新輸入")
                                else:
                                    result = reset_password(st.session_state.edit_user_id, new_password)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.session_state.edit_user_id = None
                                        st.session_state.edit_mode = None
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                        
                        with col_cancel:
                            if st.form_submit_button("❌ 取消", use_container_width=True):
                                st.session_state.edit_user_id = None
                                st.session_state.edit_mode = None
                                st.rerun()
            
            # ========== 刪除確認對話框 ==========
            if st.session_state.delete_confirm_id is not None:
                st.divider()
                st.warning("⚠️ 確認刪除")
                
                current_user = None
                for u in get_all_users():
                    if u['id'] == st.session_state.delete_confirm_id:
                        current_user = u
                        break
                
                if current_user:
                    st.write(f"您確定要刪除用戶 **{current_user['username']}** (姓名：{current_user['display_name']}) 嗎？")
                    st.info("💡 該用戶將被標記為已刪除，無法登入系統，但數據會被保留以供審計。")
                    
                    col_del, col_cancel = st.columns(2)
                    with col_del:
                        if st.button("🗑️ 確認刪除", use_container_width=True, key="confirm_delete"):
                            result = soft_delete_user(st.session_state.delete_confirm_id)
                            if result['success']:
                                st.success(result['message'])
                                st.session_state.delete_confirm_id = None
                                st.rerun()
                            else:
                                st.error(result['message'])
                    
                    with col_cancel:
                        if st.button("❌ 取消", use_container_width=True, key="cancel_delete"):
                            st.session_state.delete_confirm_id = None
                            st.rerun()

    # ==============================================================================
    # 模式 B：模板設計師 (管理後台)
    # ==============================================================================
    elif app_mode == " 模板設計師":
        
        # 記住目前所在的 tab
        if "template_tab" not in st.session_state:
            st.session_state.template_tab = TAB_LIBRARY

        st.header(" AI 模板設計中心")
        st.info("在此模式下，您可以新增或修改 AI 的思考邏輯 (Prompt)，客製化不同科別的需求。")

        db_templates = get_all_templates()
        template_list = list(db_templates.keys())

        tab = st.radio(
        "功能頁籤",
        [TAB_LIBRARY, TAB_CREATE, TAB_IMPORT],
        horizontal=True,
        key="template_tab"
        )

        # =======================
        # Tab 1：模板庫管理
        # =======================
        if st.session_state.template_tab == TAB_LIBRARY:

            # ---------- 匯出模板 ----------
            with st.container():
                st.markdown("#### 匯出模板")

                export_scope = st.radio(
                    "匯出範圍：",
                    ["整個模板庫", "單一模板"],
                    horizontal=True
                )

                export_templates = db_templates
                export_label_suffix = "all"

                if export_scope == "單一模板":
                    selected_export_template = st.selectbox(
                        "選擇要匯出的模板：",
                        template_list
                    )
                    export_templates = {
                        selected_export_template: db_templates[selected_export_template]
                    }
                    export_label_suffix = selected_export_template
                    
                    with st.expander("模板預覽", expanded=True):
                        st.code(
                            db_templates[selected_export_template],
                            language="text",
                        )

                col1, col2 = st.columns(2)

                with col1:
                    export_format = st.selectbox(
                        "選擇匯出格式：",
                        ["CSV (Excel)", "JSON (程式用)", "Markdown (文件)", "TXT (純文字)"]
                    )

                with col2:
                    file_data = None
                    file_name = f"templates_export_{export_label_suffix}"
                    mime_type = "text/plain"

                    if export_format == "CSV (Excel)":
                        df_export = pd.DataFrame(
                            export_templates.items(),
                            columns=["模板名稱", "System Prompt 內容"]
                        )
                        file_data = df_export.to_csv(index=False).encode("utf-8-sig")
                        file_name += ".csv"
                        mime_type = "text/csv"

                    elif export_format == "JSON (程式用)":
                        file_data = json.dumps(
                            export_templates,
                            indent=4,
                            ensure_ascii=False
                        ).encode("utf-8")
                        file_name += ".json"
                        mime_type = "application/json"

                    elif export_format == "Markdown (文件)":
                        md_text = "# AI 醫療摘要模板\n\n"
                        for name, content in export_templates.items():
                            md_text += f"## {name}\n```text\n{content}\n```\n\n---\n\n"
                        file_data = md_text.encode("utf-8")
                        file_name += ".md"
                        mime_type = "text/markdown"

                    elif export_format == "TXT (純文字)":
                        txt_text = "AI 醫療摘要模板\n====================\n\n"
                        for name, content in export_templates.items():
                            txt_text += f"模板名稱：{name}\n內容：\n{content}\n\n--------------------\n\n"
                        file_data = txt_text.encode("utf-8")
                        file_name += ".txt"
                        mime_type = "text/plain"

                    if file_data:
                        st.download_button(
                            label=f"⬇ 下載 {export_format}",
                            data=file_data,
                            file_name=file_name,
                            mime=mime_type,
                            use_container_width=True
                        )

            st.divider()

            # ---------- 編輯模板 ----------
            with st.container():
                st.subheader(" 編輯模板")

                template_keys = list(db_templates.keys())
                if not template_keys:
                    st.warning("資料庫中沒有模板可編輯，請先建立模板！")
                    st.stop()

                if "edit_target" not in st.session_state or st.session_state.edit_target not in db_templates:
                    st.session_state.edit_target = template_keys[0]

                edit_target = st.selectbox(
                    "請選擇要修改的模板：",
                    template_keys,
                    index=template_keys.index(st.session_state.edit_target)
                )

                st.session_state.edit_target = edit_target
                current_content = db_templates.get(edit_target, "")

                with st.form("edit_form"):
                    st.write(f"**正在編輯：** `{edit_target}`")
                    new_content = st.text_area(
                        "模板內容 (System Prompt)",
                        value=current_content,
                        height=450
                    )

                    if st.form_submit_button(" 儲存修改", type="primary"):
                        if update_template(edit_target, new_content):
                            st.success(f"模板「{edit_target}」已成功更新！")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("更新失敗，請檢查資料庫連線。")

        # =======================
        # Tab 2: 建立新模板
        # =======================
        elif st.session_state.template_tab == TAB_CREATE:
            
            st.markdown("####  Prompt 快速產生器")
            st.caption("選擇以下參數，系統會即時生成專業的 System Prompt 草稿。")
            
            c1, c2, c3 = st.columns(3)

            if "role_type" not in st.session_state:
                st.session_state.role_type = "一般病房護理師 (Ward Nurse)"
            if "scenario_type" not in st.session_state:
                st.session_state.scenario_type = "急診轉住院 (Admission Note)"
            if "format_type" not in st.session_state:
                st.session_state.format_type = "SOAP 格式"
            if "new_template_draft" not in st.session_state:
                st.session_state.new_template_draft = ""

            def update_draft():
                role_type = st.session_state.role_type
                scenario_type = st.session_state.scenario_type
                format_type = st.session_state.format_type

                role_definitions = {
                    "加護病房護理師 (ICU Nurse)": {
                        "focus": "重症照護導向。持續性生命徵象監測、器官系統功能評估、維生管路 (CVC, A-line) 與呼吸器設定、精密液體平衡 (I/O)、鎮靜與疼痛評估。",
                        "tone": "嚴謹、數據導向、強調細節與趨勢分析。"
                    },
                    "一般病房護理師 (Ward Nurse)": {
                        "focus": "住院照護導向。入院護理評估、病人安全 (跌倒/壓傷風險)、給藥治療、主要照顧者與家庭支持系統、住院期間的護理計畫與衛教。",
                        "tone": "溫暖、完整、強調個別化照護與持續性。"
                    },
                    "傷口護理師 (Wound Care Nurse)": {
                        "focus": "傷口評估導向。傷口部位、大小、深度 (T.I.M.E. 原則)、滲出液性質、周圍皮膚狀況、敷料選擇與換藥頻率建議。",
                        "tone": "描述性強、精確、強調組織癒合進程。"
                    },
                    "專科護理師 (NP)": {
                        "focus": "協作導向。協助醫師撰寫病程紀錄、開立醫囑後的執行狀況、各項檢查報告的追蹤整理、出院衛教。",
                        "tone": "專業、精確、著重於醫療與護理的橋接。"
                    },
                    "急診護理師 (ER Nurse)": {
                        "focus": "照護導向。生命徵象的動態變化、給藥後的立即反應、管路照護（點滴、尿管）、病患的主觀不適與情緒反應。",
                        "tone": "觀察入微、強調病患當下狀態與執行面。"
                    },
                    "檢傷護理師 (Triage Nurse)": {
                        "focus": "風險導向。剛到院時的主訴、生命徵象是否穩定、檢傷級數判定、傳染病接觸史 (TOCC)。",
                        "tone": "簡潔、快速、強調危急程度。"
                    }
                }

                selected_role_config = role_definitions[role_type]

                role_prompt_part = f"""
你是一位專業的{role_type}。
【角色職責】：**{selected_role_config['focus']}**
【語氣風格】：請保持**{selected_role_config['tone']}**
"""

                scenario_text = ""
                if scenario_type == "急診轉住院 (Admission Note)":
                    scenario_text = "這份摘要將用於**急診轉住院**交接。請重點說明急診處置經過、目前生命徵象穩定度，以及後續住院需注意的檢查數值與待辦事項。"
                elif scenario_type == "急診出院/轉院 (Discharge Note)":
                    scenario_text = "這份摘要將作為**出院/轉院紀錄**。請總結病程、關鍵檢驗結果與離院時的狀態，供接收單位或家屬參考。請特別註明出院衛教與回診資訊。"
                elif scenario_type == "交班報告 (Shift Handoff / ISBAR)":
                    scenario_text = "這份摘要將用於**護理交班**。請依照 ISBAR 邏輯，著重於目前的病患狀況 (Status) 與待辦事項 (Pending Actions)。請特別標註尚未完成的檢查或給藥。"
                elif scenario_type == "專科會診 (Consultation)":
                    scenario_text = "這份摘要將提供給**專科醫師會診**使用。內容必須極度精簡、數據導向，突顯異常數值以利快速決策。請明確指出會診目的與急診已完成之處置。"
                elif scenario_type == "重大創傷/急救紀錄 (Trauma/Resuscitation)":
                    scenario_text = "這份摘要將用於**重大創傷或急救事件**的紀錄。請務必依**時間軸 (Timeline)** 詳細列出生命徵象變化、急救藥物給予時間與劑量、處置（如插管、輸血）及其反應。"
                elif scenario_type == "一般病程回顧 (General Review)":
                    scenario_text = "這份摘要為**一般病程回顧**。請整合所有資料，提供一份客觀、完整的病程敘述，包含主訴、檢查發現、處置經過與目前狀況。"

                format_text = ""
                if format_type == "SOAP 格式":
                    format_text = """
請嚴格遵守 **SOAP** 格式輸出：
### **S (Subjective)**: 病患主訴與自述症狀。
### **O (Objective)**: 生命徵象趨勢、異常檢驗數據、客觀觀察。
### **A (Assessment)**: 健康問題評估 (嚴禁臆測)。
### **P (Plan)**: 治療處置與後續計畫。"""
                elif format_type == "ISBAR 格式":
                    format_text = """
請使用 **ISBAR** 格式輸出：
### **I (Identity)**: 身分與檢傷。
### **S (Situation)**: 目前主訴與狀況。
### **B (Background)**: 病史與到院經過。
### **A (Assessment)**: 評估與異常發現。
### **R (Recommendation)**: 處置與建議。"""
                elif format_type == "時間軸敘述":
                    format_text = """
請嚴格按照**時間先後順序**撰寫，格式如下：
- [HH:MM] 發生事件 / 處置 / 數據變化
- [HH:MM] ...
請特別標註關鍵處置（如給藥、檢查）的時間點，並確保時序正確。"""
                elif format_type == "問題導向":
                    format_text = """
請將病程整理為數個**主要臨床問題 (Problems)**，格式如下：
1. **#問題名稱 (如：呼吸衰竭)**：相關數據變化與處置經過。
2. **#問題名稱 (如：高血壓)**：相關處置與反應。
請針對每個問題進行獨立的評估與總結。"""
                else:
                    format_text = """
請使用清晰的**條列式結構**，包含：
1. **【病況概述】**
2. **【重要檢查發現】** (標註異常值)
3. **【處置經過】**
4. **【目前狀態】"""

                rules_text = """
**【撰寫規則】**：
1. **絕對客觀**：僅陳述資料中顯示的事實，嚴禁進行無根據的診斷推測。
2. **數據佐證**：提及異常時，必須附上具體數值。
3. **專業用語**：使用台灣醫療慣用的繁體中文與英文術語。"""

                st.session_state.new_template_draft = f"{role_prompt_part}\n{scenario_text}\n{format_text}\n{rules_text}"

            c1.selectbox(
                "1. 設定角色視角",
                [
                    "加護病房護理師 (ICU Nurse)", 
                    "一般病房護理師 (Ward Nurse)",    
                    "傷口護理師 (Wound Care Nurse)",
                    "專科護理師 (NP)",
                    "急診護理師 (ER Nurse)",
                    "檢傷護理師 (Triage Nurse)"
                ],
                key="role_type",
                on_change=update_draft
            )

            c2.selectbox(
                "2. 設定使用情境 ",
                [
                    "急診轉住院 (Admission Note)",
                    "急診出院/轉院 (Discharge Note)",
                    "交班報告 (Shift Handoff / ISBAR)",
                    "專科會診 (Consultation)",
                    "重大創傷/急救紀錄 (Trauma/Resuscitation)",
                    "一般病程回顧 (General Review)"
                ],
                key="scenario_type",
                on_change=update_draft
            )

            c3.selectbox(
                "3. 設定輸出結構",
                ["SOAP 格式", "ISBAR 格式", "時間軸敘述","問題導向"],
                key="format_type",
                on_change=update_draft
            )

            new_name = st.text_input("新模板名稱 (例如：重大創傷急救紀錄)")
            new_desc = st.text_input("模板說明 (選填)")
            new_content = st.text_area("模板內容", value=st.session_state.new_template_draft, height=300)

            if st.button(" 建立模板"):
                if new_name and new_content:
                    if create_template(new_name, new_content, new_desc):
                        st.success(f"模板「{new_name}」建立成功！")
                        st.cache_data.clear()
                        if "new_template_draft" in st.session_state:
                            del st.session_state.new_template_draft
                        st.rerun()
                    else:
                        st.error("建立失敗 (名稱可能重複)。")
                else:
                    st.warning("名稱與內容不得為空。")
                    
        # =======================
        # Tab 3：模板導入
        # =======================
        elif st.session_state.template_tab == TAB_IMPORT:
            
            st.markdown("#### 📥 將模板從外部文件導入系統")
            st.caption("支持從 PDF、Word、Excel、TXT、JSON 等檔案中提取內容並作為模板導入。")
            
            # ===== 初始化 session state =====
            if "import_uploaded_file" not in st.session_state:
                st.session_state.import_uploaded_file = None
            if "import_extracted_content" not in st.session_state:
                st.session_state.import_extracted_content = ""
            if "import_file_type" not in st.session_state:
                st.session_state.import_file_type = None
            
            st.subheader("第 1 步：上傳文件")
            
            # 文件上傳
            col_upload_text, col_upload_info = st.columns([3, 1])
            with col_upload_text:
                uploaded_file = st.file_uploader(
                    "選擇要上傳的文件 (.pdf, .docx, .txt, .jpg, .png)：",
                    type=['pdf', 'docx', 'txt', 'jpg', 'png']
                )
            
            with col_upload_info:
                st.info("💡 提示：選擇包含模板 Prompt 內容的文件")
            
            # 文件處理邏輯
            if uploaded_file is not None:
                file_name = uploaded_file.name
                file_ext = file_name.split('.')[-1].lower()
                
                # 映射副檔名到文件類型
                file_type_mapping = {
                    'pdf': 'pdf',
                    'docx': 'docx',
                    'txt': 'txt',
                    'jpg': 'image',
                    'png': 'image'
                }
                
                file_type = file_type_mapping.get(file_ext, None)
                
                if file_type is None:
                    st.error(f"❌ 不支持的文件類型：{file_ext}")
                else:
                    # 顯示上傳成功信息
                    st.success(f"✅ 文件已上傳：{file_name} ({file_ext.upper()})")
                    
                    # 提取文件內容
                    with st.spinner("正在提取文件內容..."):
                        extracted_content, error_msg = parse_uploaded_template(uploaded_file, file_type)
                    
                    if error_msg:
                        st.error(f"❌ 提取失敗：{error_msg}")
                    else:
                        st.session_state.import_extracted_content = extracted_content
                        st.session_state.import_file_type = file_type
                        st.session_state.import_uploaded_file = file_name
                        
                        st.divider()
                        
                        # 預覽提取的內容
                        st.subheader("第 2 步：預覽與編輯提取的內容")
                        
                        # 作為單個模板導入
                        show_single_template_import_form(extracted_content)
            else:
                st.info("🔹 請上傳文件開始使用")

    # ==============================================================================
    # 模式 D：測試視窗 (Admin 專用)
    # ==============================================================================
    elif app_mode == "測試視窗":
        # 路由守衛：確保只有 admin 可以訪問
        if st.session_state.role != "admin":
            st.error("403 禁止訪問：您沒有權限訪問此頁面！")
            st.info("只有管理員（Admin）可以訪問測試視窗功能。")
            st.stop()

        st.header("資料庫測試視窗")
        st.info("此功能允許管理員直接測試目前啟用的資料庫連線，並執行基本查詢操作。")

        # 檢查活動連線
        active_connection = config_manager.get_active_connection()

        if not active_connection:
            st.warning("目前沒有啟用的資料庫連線。請先至「管理中控台」設定並啟用資料庫連線。")
            st.stop()

        # 顯示連線資訊
        st.subheader("當前連線資訊")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("連線名稱", active_connection.name)
        with col2:
            st.metric("資料庫類型", active_connection.db_type.upper())
        with col3:
            st.metric("主機位址", f"{active_connection.host}:{active_connection.port}")

        # 獲取該連線的 Schema 映射
        connection_mappings = config_manager.get_connection_mappings(active_connection.name)

        if not connection_mappings:
            st.warning(f"連線「{active_connection.name}」尚未進行 Schema 同步，無法執行測試操作。")
            st.stop()

        # 取得已同步的資料表列表
        available_tables = list(connection_mappings.keys())
        if not available_tables:
            st.warning("該連線沒有已同步的資料表。")
            st.stop()

        st.subheader("資料庫測試操作")

        # 資料表選擇下拉選單
        selected_table = st.selectbox(
            "選擇要測試的資料表：",
            available_tables,
            help="僅顯示已同步且存在於電子辭典的資料表"
        )

        # 測試按鈕區域
        st.markdown("### 測試操作")

        col_test1, col_test2, col_test3 = st.columns(3)

        # 按鈕 A：測試基礎連線
        with col_test1:
            if st.button("測試基礎連線", use_container_width=True):
                with st.spinner("正在測試連線..."):
                    try:
                        # 建立資料庫連線
                        if active_connection.db_type.lower() == "oracle":
                            import oracledb
                            dsn = oracledb.makedsn(active_connection.host, active_connection.port, service_name=active_connection.database)
                            conn = oracledb.connect(
                                user=active_connection.username,
                                password=active_connection.password,
                                dsn=dsn
                            )
                            # 執行簡單的 Ping 測試
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1 FROM DUAL")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        elif active_connection.db_type.lower() == "postgresql":
                            import psycopg2
                            conn = psycopg2.connect(
                                host=active_connection.host,
                                port=active_connection.port,
                                database=active_connection.database,
                                user=active_connection.username,
                                password=active_connection.password
                            )
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        elif active_connection.db_type.lower() == "sqlite":
                            import sqlite3
                            conn = sqlite3.connect(active_connection.database)
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        else:
                            raise ValueError(f"不支援的資料庫類型: {active_connection.db_type}")

                        st.success("✅ 連線測試成功！資料庫可正常連通。")

                    except Exception as e:
                        st.error(f"❌ 連線測試失敗：{str(e)}")

        # 按鈕 B：查詢資料表總筆數
        with col_test2:
            if st.button("查詢總筆數", use_container_width=True):
                with st.spinner("正在查詢資料表總筆數..."):
                    try:
                        # 建立資料庫連線
                        if active_connection.db_type.lower() == "oracle":
                            import oracledb
                            dsn = oracledb.makedsn(active_connection.host, active_connection.port, service_name=active_connection.database)
                            conn = oracledb.connect(
                                user=active_connection.username,
                                password=active_connection.password,
                                dsn=dsn
                            )
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        elif active_connection.db_type.lower() == "postgresql":
                            import psycopg2
                            conn = psycopg2.connect(
                                host=active_connection.host,
                                port=active_connection.port,
                                database=active_connection.database,
                                user=active_connection.username,
                                password=active_connection.password
                            )
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        elif active_connection.db_type.lower() == "sqlite":
                            import sqlite3
                            conn = sqlite3.connect(active_connection.database)
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()

                        else:
                            raise ValueError(f"不支援的資料庫類型: {active_connection.db_type}")

                        count = result[0] if result else 0
                        st.success(f"✅ 資料表 {selected_table} 總共有 {count:,} 筆資料。")

                    except Exception as e:
                        st.error(f"❌ 查詢失敗：{str(e)}")

        # 按鈕 C：提取前 10 筆資料
        with col_test3:
            if st.button("提取前10筆", use_container_width=True):
                with st.spinner("正在提取前10筆資料..."):
                    try:
                        # 建立資料庫連線
                        if active_connection.db_type.lower() == "oracle":
                            import oracledb
                            dsn = oracledb.makedsn(active_connection.host, active_connection.port, service_name=active_connection.database)
                            conn = oracledb.connect(
                                user=active_connection.username,
                                password=active_connection.password,
                                dsn=dsn
                            )
                            cursor = conn.cursor()
                            query = f'SELECT * FROM (SELECT * FROM "{selected_table}") WHERE ROWNUM <= 10'
                            st.info(f"調試：執行 SQL 語句：{query}")  # 調試用
                            cursor.execute(query)
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            cursor.close()
                            conn.close()

                        elif active_connection.db_type.lower() == "sqlite":
                            import sqlite3
                            conn = sqlite3.connect(active_connection.database)
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT * FROM {selected_table} LIMIT 10")
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            cursor.close()
                            conn.close()

                        else:
                            raise ValueError(f"不支援的資料庫類型: {active_connection.db_type}")

                        # 顯示結果
                        if rows:
                            import pandas as pd
                            df = pd.DataFrame(rows, columns=columns)
                            st.success(f"✅ 成功提取 {selected_table} 的前 {len(rows)} 筆資料：")
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info(f"資料表 {selected_table} 為空，沒有資料可顯示。")

                    except Exception as e:
                        st.error(f"❌ 提取資料失敗：{str(e)}")
