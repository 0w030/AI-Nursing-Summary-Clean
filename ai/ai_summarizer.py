# /ai/ai_summarizer.py

import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from db.template_service import get_all_templates
# 引入翻譯官：包含標籤翻譯(get_chinese_name) 與 數值翻譯(translate_value)
from data.metadata import get_chinese_name, translate_value 

load_dotenv()

# --- 輔助函數：自動標籤化 + 數值翻譯 + 重複數據過濾 ---
def auto_label_data(data_list):
    """將 list 中的 dict 轉換為中文標籤，並自動進行『數值代碼翻譯』與『去重』"""
    if not data_list:
        return ""
    
    result_lines = []
    seen_records = set()
    
    for item in data_list:
        # 1. 去重邏輯：同一時間、同一項目、同一數值視為重複
        item_name = item.get('CHHEAD') or item.get('SUBJECT') or "項目"
        item_val = item.get('CHVAL') or item.get('DIAGNOSIS') or "數值"
        timestamp = item.get('PROCDTTM') or item.get('CHRCPDTM') or ""
        record_id = f"{timestamp}_{item_name}_{item_val}"
        
        if record_id in seen_records:
            continue
        seen_records.add(record_id)

        # 2. 遍歷欄位並進行翻譯
        parts = []
        for key, value in item.items():
            # 跳過系統內部欄位與時間
            if key in ['PROCDTTM', 'CHRCPDTM', 'CHAPPDTM', 'VISITDT', 'ID', 'TRINO', 'PATID']:
                continue
            
            val_str = str(value).strip()
            # 過濾無效字串 (None / Null)
            if not val_str or val_str.lower() in ["none", "none~none", "null"]:
                continue
            
            # --- 雙重翻譯邏輯 ---
            label = get_chinese_name(key)            # 欄位標籤翻譯 (e.g., CHSTAT -> 狀態碼)
            final_val = translate_value(key, value)   # 數值內容翻譯 (e.g., 30 -> 檢驗中)
            # -----------------
            
            parts.append(f"{label}: {final_val}")
        
        if parts:
            result_lines.append(f"- {timestamp} | {' | '.join(parts)}")
    
    return "\n".join(result_lines)

def generate_nursing_summary(patient_id, patient_data, template_name, custom_system_prompt=None, focus_areas=None):
    if not patient_data:
        return "錯誤：無資料可分析。"

    # === 1. 獲取模板 ===
    db_templates = get_all_templates()
    base_system_prompt = db_templates.get(template_name) if db_templates else "你是專業醫療人員。"
    if not base_system_prompt and db_templates:
        base_system_prompt = next(iter(db_templates.values()))

    # === 2. 決定 System Prompt ===
    selected_system_prompt = custom_system_prompt if custom_system_prompt else base_system_prompt

    # === 3. 加入關注項目 (Focus Areas) ===
    if focus_areas:
        selected_system_prompt += f"\n\n**【⚠️ 特別指令：重點關注項目】**\n- {', '.join(focus_areas)}"

    # === 4. 資料截斷 ===
    nursing_list = patient_data.get('nursing', [])[-25:]
    labs_list = patient_data.get('labs', [])[-60:] 
    vitals_list = patient_data.get('vitals', [])[-25:]

    # === 5. 建構 User Prompt (混合標籤化 + 數值轉換) ===
    data_text = f"=== 病患 ID: {patient_id} 急診臨床資料摘要 ===\n\n"

    # A. 護理紀錄 (自動標籤化 + 數值轉換)
    if nursing_list:
        data_text += f"【護理紀錄】\n{auto_label_data(nursing_list)}\n\n"
    
    # B. 生理監測 (手動精排 + 特定數值轉換)
    if vitals_list:
        data_text += f"【生理監測】\n"
        for item in vitals_list:
            # 翻譯體溫部位 (ETREGION) 與 檢傷級數 (ENESKIND)
            region = translate_value('ETREGION', item.get('ETREGION'))
            t_kind = translate_value('ENESKIND', item.get('ENESKIND'))
            
            v_str = (f"- {item.get('PROCDTTM')} | "
                     f"類型: {t_kind} | "
                     f"體溫: {item.get('ETEMPUTER')} ({region}) | 脈搏: {item.get('EPLUSE')} | "
                     f"呼吸: {item.get('EBREATHE')} | 血壓: {item.get('EPRESSURE')}/{item.get('EDIASTOLIC')} | "
                     f"血氧: {item.get('ESAO2')} | GCS: {item.get('GCS')}\n")
            data_text += v_str
        data_text += "\n"

    # C. 檢驗報告 (自動標籤化 + 狀態碼轉換)
    if labs_list:
        data_text += f"【檢驗報告】\n{auto_label_data(labs_list)}\n"

    # === [Debug] 打印發送給 Groq 的內容 ===
    print("\n" + "🚀" + "="*20 + " GROQ API 請求內容預覽 " + "="*20)
    print(f"[System Prompt]:\n{selected_system_prompt[:300]}...") # 預覽前段
    print(f"[User Data]:\n{data_text}")
    print("="*65 + "\n")

    # === 6. 呼叫 AI API (Groq) ===
    client = OpenAI(
        api_key=st.secrets["groq"]["api_key"], 
        base_url="https://api.groq.com/openai/v1"
    )
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": selected_system_prompt},
                {"role": "user", "content": data_text}
            ],
            temperature=0.3, 
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ API Error: {e}")
        return f"AI 生成失敗: {e}"