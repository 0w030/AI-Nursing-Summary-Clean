# feedback_component.py

import streamlit as st
import psycopg2
from db.db_connector import get_db_connection

# ==========================================
# 1. 資料庫操作函數
# ==========================================

def init_feedback_table():
    """
    檢查並建立回饋資料表 (如果不存在的話)。
    這讓程式碼更強健，不用手動去 DB 建表。
    """
    conn = get_db_connection()
    if not conn:
        return
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ai_feedback_log (
        id SERIAL PRIMARY KEY,
        patient_id VARCHAR(50),
        template_type VARCHAR(50),
        rating INTEGER,
        comment TEXT,
        generated_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()
    except Exception as e:
        print(f"建立回饋資料表失敗: {e}")
    finally:
        conn.close()

def save_feedback_to_db(patient_id, template_type, rating, comment, summary_content):
    """
    將使用者的回饋寫入 PostgreSQL。
    """
    conn = get_db_connection()
    if not conn:
        st.error("資料庫連線失敗，無法儲存回饋。")
        return False

    insert_sql = """
    INSERT INTO ai_feedback_log (patient_id, template_type, rating, comment, generated_summary)
    VALUES (%s, %s, %s, %s, %s)
    """
    try:
        with conn.cursor() as cur:
            cur.execute(insert_sql, (patient_id, template_type, rating, comment, summary_content))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"儲存失敗: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# 2. UI 顯示元件
# ==========================================

def show_feedback_ui(patient_id, template_type):
    """
    顯示回饋表單的 UI 元件。
    此函數會被 app.py 呼叫。
    """
    
    # 確保資料表存在 (第一次執行時會建立)
    init_feedback_table()

    st.subheader("📝 協助優化 AI")
    st.info("您的回饋將直接用於改善此系統的準確度。")

    # 建立一個 Form，避免使用者每打一個字就重新整理頁面
    with st.form(key=f"feedback_form_{patient_id}"):
        
        # 1. 滿意度評分 (1-5 分)
        # 註：Streamlit 1.31+ 有 st.feedback("stars")，若版本較舊可用 st.slider
        try:
            rating = st.feedback("stars") # 需要 streamlit >= 1.31.0
        except AttributeError:
            # 相容性備案
            rating = st.slider("請評分 (1=非常不滿意, 5=非常滿意)", 1, 5, 3)
            # 轉換 slider 的值以配合邏輯 (st.feedback 回傳 0-4，slider 回傳 1-5，這裡統一看您後端需求)
            # 這裡我們讓 rating 保持 1-5 直觀邏輯
        
        # 如果是用 st.feedback，它回傳的是 0~4 (索引值)，我們加 1 變成 1~5 分
        final_rating = (rating + 1) if rating is not None else 0

        # 2. 文字回饋
        comment = st.text_area(
            "修正建議或備註 (選填)", 
            placeholder="例如：血壓數值抓錯了、語氣太生硬、漏掉了重要的過敏史...",
            height=100
        )

        # 3. 提交按鈕
        submit_btn = st.form_submit_button("送出回饋")

    if submit_btn:
        if final_rating == 0 and not comment:
            st.warning("請至少給予評分或填寫意見。")
        else:
            # 嘗試從 session_state 抓取當下的摘要內容，這樣才知道使用者是在評論哪一段文字
            current_summary = st.session_state.get("final_summary", "無摘要紀錄")

            with st.spinner("正在儲存您的寶貴意見..."):
                success = save_feedback_to_db(
                    patient_id, 
                    template_type, 
                    final_rating, 
                    comment, 
                    current_summary
                )
            
            if success:
                st.success("✅ 回饋已送出！感謝您的協助。")
                # 可以選擇是否隱藏 Form，或單純顯示成功訊息