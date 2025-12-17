# app.py

import streamlit as st
import os
import pandas as pd
import json
from dotenv import load_dotenv
from datetime import datetime, time
from feedback_component import show_feedback_ui

# 引入後端模組
from db.patient_service import get_patient_full_history, get_all_patients_overview
from db.template_service import get_all_templates, create_template, update_template
from ai.ai_summarizer import generate_nursing_summary

# --- 設定網頁 ---
st.set_page_config(page_title="AI 醫療模板系統", layout="wide", page_icon="")


# ===== 全域預設（避免 NameError）=====
selected_info = None
target_patient_id = None
earliest_dt = None
DB_HOST = st.secrets["database"]["host"]
DB_PORT = st.secrets["database"]["port"]
DB_NAME = st.secrets["database"]["name"]
DB_USER = st.secrets["database"]["user"]
DB_PASSWORD = st.secrets["database"]["password"]

# 讀取 GROQ API Key
GROQ_API_KEY = st.secrets["groq"]["api_key"]

with st.sidebar:
    st.subheader("🔍 Secrets 除錯（僅開發用）")

    try:
        groq_key = st.secrets["groq"]["api_key"]

        if groq_key:
            st.success("GROQ_API_KEY 已讀取")
            st.write("API Key 長度：", len(groq_key))
            st.write(
                "API Key 預覽：",
                f"{groq_key[:4]}****{groq_key[-4:]}"
            )
        else:
            st.error("GROQ_API_KEY 為空值")

    except KeyError as e:
        st.error("❌ 無法從 st.secrets 讀取 GROQ_API_KEY")
        st.code(str(e))

# ==========================================
# 輔助函數
# ==========================================
def format_time_str(raw_time):
    if not raw_time or len(str(raw_time)) < 12: return raw_time
    s = str(raw_time)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"

@st.cache_data(ttl=60)
def load_patient_list():
    raw_list = get_all_patients_overview()
    for p in raw_list:
        p['最早紀錄_顯示'] = format_time_str(p['最早紀錄'])
        p['最晚紀錄_顯示'] = format_time_str(p['最晚紀錄'])
        p['label'] = f"{p['病歷號']} (共 {p['資料筆數']} 筆資料)"
    return raw_list

patients_list = load_patient_list()

# ==========================================
# 側邊欄：全域導航
# ==========================================
with st.sidebar:
    st.title(" 醫療摘要系統")
    app_mode = st.radio("請選擇功能模式：", [" 摘要生成器", " 模板設計師"], index=0)
    st.divider()

# ==============================================================================
# 模式 A：摘要生成器 (使用者模式)
# ==============================================================================
if app_mode == " 摘要生成器":
    st.header(" AI 急診病程摘要生成")
    
    # 1. 選擇病患
    st.subheader("1. 選擇病患")
    options = ["請選擇..."] + [p['label'] for p in patients_list]
    selected_label = st.selectbox("病患清單：", options, index=0)
    
    target_patient_id = None
    selected_info = None
    if selected_label != "請選擇...":
        selected_info = next((p for p in patients_list if p['label'] == selected_label), None)
        target_patient_id = selected_info['病歷號']
        st.success(f"已選定：{target_patient_id}")
        # 解析病患最早就診時間（給時間篩選用）
        
earliest_dt = None

if selected_info and selected_info.get("最早紀錄"):
    raw_time = selected_info["最早紀錄"]
    earliest_dt = datetime.strptime(raw_time, "%Y%m%d%H%M%S")



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

    # 4. 關注點 (修改為 Checkbox 清單 + 智慧預設)
    st.subheader("3. 重點關注項目")
    st.write("請勾選 **重點關注項目** (AI 將加強分析)：")
    
    focus_options = ["生命徵象趨勢", "檢驗報告異常值", "護理處置經過", "病患主訴", "管路狀況", "意識狀態(GCS)"]
    
    # === 智慧預設勾選 (根據模板名稱自動判斷) ===
    default_focus = []
    if "會診" in selected_template_name: 
        default_focus = ["檢驗報告異常值", "生命徵象趨勢"]
    elif "交班" in selected_template_name: 
        default_focus = ["護理處置經過", "意識狀態(GCS)"]
    elif "出院" in selected_template_name: 
        default_focus = ["護理處置經過", "生命徵象趨勢"]
    
    selected_focus_areas = []
    # 使用 3 欄排列，讓版面更整齊
    cols = st.columns(3)
    for i, option in enumerate(focus_options):
        # 檢查該選項是否在預設清單中
        is_checked = option in default_focus
        if cols[i % 3].checkbox(option, value=is_checked):
            selected_focus_areas.append(option)

    # 5. 時間範圍篩選
    with st.expander(" 時間範圍篩選 (選填)"):
        use_time_filter = st.checkbox("啟用篩選")

        start_dt_str = None
        end_dt_str = None

    if use_time_filter:
        # 預設值邏輯
        if target_patient_id and earliest_dt:
            default_date = earliest_dt.date()
            default_time = earliest_dt.time()
        else:
            default_date = datetime.now().date()
            default_time = time(0, 0)

        c1, c2 = st.columns(2)
        d1 = c1.date_input("開始日期", default_date)
        t1 = c2.time_input("開始時間", default_time)

        start_dt_str = (
            f"{d1.year}{d1.month:02d}{d1.day:02d}"
            f"{t1.hour:02d}{t1.minute:02d}00"
        )



    # 6. 執行按鈕
    if target_patient_id:
        if st.button(" 開始生成摘要", type="primary", use_container_width=True):
            load_dotenv()
            if not st.secrets["groq"]["api_key"]:
                st.error("未設定 API Key")
                st.stop()
                
            with st.spinner("正在分析資料並撰寫摘要..."):
                # 撈資料
                p_data = get_patient_full_history(target_patient_id, start_time=start_dt_str)
                
                # 準備 Prompt 附加指令
                style_instruction = ""
                if style_option == "短文式 (Narrative)":
                    style_instruction = "\n\n**【格式要求】**：請整合為一篇流暢的短文，禁止使用列點。"
                else:
                    style_instruction = "\n\n**【格式要求】**：請務必使用列點方式呈現，保持條理。"
                
                # 從資料庫取出原始模板內容
                base_prompt = db_templates[selected_template_name]
                
                # 組合最終 Prompt
                final_system_prompt = base_prompt + style_instruction

                # 呼叫 AI
                summary = generate_nursing_summary(
                    target_patient_id, 
                    p_data, 
                    selected_template_name,
                    custom_system_prompt=final_system_prompt,
                    focus_areas=selected_focus_areas
                )
                
                st.markdown("###  生成結果")
                st.markdown("---")
                st.markdown(summary)
                
                show_feedback_ui(target_patient_id,template_names)
                

# ==============================================================================
# 模式 B：模板設計師 (管理後台)
# ==============================================================================
elif app_mode == " 模板設計師":
    st.header(" AI 模板設計中心")
    st.info("在此模式下，您可以新增或修改 AI 的思考邏輯 (Prompt)，客製化不同科別的需求。")

    db_templates = get_all_templates()
    template_list = list(db_templates.keys())

    tab_library, tab_create = st.tabs([" 模板庫管理", " 建立新模板"])

    # =======================
    # Tab 1：模板庫管理
    # =======================
    with tab_library:

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

            # 設定預設選擇第一個模板
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


    # --- Tab 2: 建立新模板 (保持原樣) ---
    with tab_create:
        st.markdown("####  Prompt 快速產生器")
        st.caption("選擇以下參數，系統會即時生成專業的 System Prompt 草稿。")
        
        c1, c2, c3 = st.columns(3)

        # 初始化 session_state
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

            # 情境文字
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

            # 格式文字
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

        # 角色、情境、格式選單，綁定 session_state，改變時即時更新
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

        # 顯示草稿區
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