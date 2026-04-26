# # /ai/ai_summarizer.py

# import os
# import re
# import streamlit as st
# from openai import OpenAI
# from dotenv import load_dotenv
# from db.template_service import get_all_templates
# # 引入翻譯官：包含標籤翻譯(get_chinese_name) 與 數值翻譯(translate_value)
# from data.metadata import get_chinese_name, translate_value 

# load_dotenv()

# # --- 新增：終極防彈版異常值判斷函數 ---
# def check_anomaly_v2(val, nh, nl):
#     """
#     利用 Regex 萃取數字，並相容 HIS 系統常見的異常標記
#     """
#     if val is None or str(val).strip() == "":
#         return ""
    
#     val_str = str(val).strip().upper()

#     # 防線一：HIS 系統原生異常標記
#     if "*" in val_str or val_str.endswith("H") or val_str.endswith("L"):
#         return " 【⚠️異常(系統標記)】"

#     # 防線二：危險文字攔截 (毒品、細菌培養等)
#     danger_keywords = ["POSITIVE", "+", "陽性", "ABNORMAL", "異常", "DETECTED"]
#     if any(keyword in val_str for keyword in danger_keywords) and "FALSE" not in val_str:
#         return " 【⚠️異常/陽性】"

#     # 防線三：Regex 數字萃取與精準比對
#     num_pattern = r"[-+]?\d*\.\d+|\d+" 
    
#     val_match = re.search(num_pattern, val_str)
#     nh_match = re.search(num_pattern, str(nh)) if nh else None
#     nl_match = re.search(num_pattern, str(nl)) if nl else None

#     if val_match:
#         v = float(val_match.group())
        
#         if nh_match:
#             h_limit = float(nh_match.group())
#             if v > h_limit:
#                 return " 【⚠️異常偏高】"
        
#         if nl_match:
#             l_limit = float(nl_match.group())
#             if v < l_limit:
#                 return " 【⚠️異常偏低】"

#     return ""

# # --- 修改：自動標籤化 + 數值翻譯 + 重複數據過濾 + 異常標記 ---
# def auto_label_data(data_list):
#     """將 list 中的 dict 轉換為中文標籤，並自動進行『數值代碼翻譯』、『去重』與『異常標記』"""
#     if not data_list:
#         return ""
    
#     result_lines = []
#     seen_records = set()
    
#     for item in data_list:
#         # 1. 去重邏輯：同一時間、同一項目、同一數值視為重複
#         item_name = item.get('CHHEAD') or item.get('SUBJECT') or "項目"
#         item_val = item.get('CHVAL') or item.get('DIAGNOSIS') or "數值"
#         timestamp = item.get('PROCDTTM') or item.get('CHRCPDTM') or item.get('CHSIGNDTTM') or ""
#         record_id = f"{timestamp}_{item_name}_{item_val}"
        
#         if record_id in seen_records:
#             continue
#         seen_records.add(record_id)

#         # 2. 取得此筆資料的結果值與參考上下限 (用於異常判斷)
#         raw_val = item.get('CHVAL')
#         raw_nh = item.get('CHNH')
#         raw_nl = item.get('CHNL')
        
#         # 呼叫異常判斷函數取得標籤 (如果是護理紀錄，這些值會是 None，函數會安全回傳空字串)
#         anomaly_tag = check_anomaly_v2(raw_val, raw_nh, raw_nl)

#         # 3. 遍歷欄位並進行翻譯與組裝
#         parts = []
#         for key, value in item.items():
#             # 跳過系統內部欄位與時間
#             if key in ['PROCDTTM', 'CHRCPDTM', 'CHAPPDTM', 'CHSIGNDTTM', 'VISITDT', 'ID', 'TRINO', 'PATID']:
#                 continue
            
#             val_str = str(value).strip()
#             # 過濾無效字串 (None / Null)
#             if not val_str or val_str.lower() in ["none", "none~none", "null"]:
#                 continue
            
#             # 欄位標籤與數值翻譯
#             label = get_chinese_name(key)            
#             final_val = translate_value(key, value)   
            
#             # 【關鍵修改】：如果是結果值 (CHVAL)，就把異常標籤黏在它後面！
#             if key == 'CHVAL':
#                 final_val = f"{final_val}{anomaly_tag}"
            
#             parts.append(f"{label}: {final_val}")
        
#         if parts:
#             result_lines.append(f"- {timestamp} | {' | '.join(parts)}")
    
#     return "\n".join(result_lines)

# def generate_nursing_summary(patient_id, patient_data, template_name, custom_system_prompt=None, focus_areas=None):
#     if not patient_data:
#         return "錯誤：無資料可分析。"

#     # === 1. 獲取模板 ===
#     db_templates = get_all_templates()
#     base_system_prompt = db_templates.get(template_name) if db_templates else "你是專業醫療人員。"
#     if not base_system_prompt and db_templates:
#         base_system_prompt = next(iter(db_templates.values()))

#     # === 2. 決定 System Prompt ===
#     selected_system_prompt = custom_system_prompt if custom_system_prompt else base_system_prompt

#     # === 3. 加入關注項目 (Focus Areas) ===
#     if focus_areas:
#         selected_system_prompt += f"\n\n**【⚠️ 特別指令：重點關注項目】**\n- {', '.join(focus_areas)}"

#     # === 4. 資料截斷 ===
#     nursing_list = patient_data.get('nursing', [])[-25:]
#     labs_list = patient_data.get('labs', [])[-60:] 
#     vitals_list = patient_data.get('vitals', [])[-25:]

#     # === 5. 建構 User Prompt (混合標籤化 + 數值轉換) ===
#     data_text = f"=== 病患 ID: {patient_id} 急診臨床資料摘要 ===\n\n"

#     # A. 護理紀錄 (自動標籤化 + 數值轉換)
#     if nursing_list:
#         data_text += f"【護理紀錄】\n{auto_label_data(nursing_list)}\n\n"
    
#     # B. 生理監測 (手動精排 + 特定數值轉換)
#     if vitals_list:
#         data_text += f"【生理監測】\n"
#         for item in vitals_list:
#             region = translate_value('ETREGION', item.get('ETREGION'))
#             t_kind = translate_value('ENESKIND', item.get('ENESKIND'))
            
#             v_str = (f"- {item.get('PROCDTTM', '')} | "
#                      f"類型: {t_kind} | "
#                      f"體溫: {item.get('ETEMPUTER', '')} ({region}) | 脈搏: {item.get('EPLUSE', '')} | "
#                      f"呼吸: {item.get('EBREATHE', '')} | 血壓: {item.get('EPRESSURE', '')}/{item.get('EDIASTOLIC', '')} | "
#                      f"血氧: {item.get('ESAO2', '')} | GCS: {item.get('GCS', '')}\n")
#             data_text += v_str
#         data_text += "\n"

#     # C. 檢驗報告 (自動標籤化 + 異常值標記)
#     if labs_list:
#         data_text += f"【檢驗報告】\n{auto_label_data(labs_list)}\n"

#     # === [Debug] 打印發送給 Groq 的內容 ===
#     print("\n" + "🚀" + "="*20 + " GROQ API 請求內容預覽 " + "="*20)
#     print(f"[System Prompt]:\n{selected_system_prompt[:300]}...") 
#     print(f"[User Data]:\n{data_text}")
#     print("="*65 + "\n")

#     # === 6. 呼叫 AI API (Groq) ===
#     client = OpenAI(
#         api_key=st.secrets["groq"]["api_key"], 
#         base_url="https://api.groq.com/openai/v1"
#     )
    
#     try:
#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {"role": "system", "content": selected_system_prompt},
#                 {"role": "user", "content": data_text}
#             ],
#             temperature=0.3, 
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"❌ API Error: {e}")
#         return f"AI 生成失敗: {e}"

#以下為oracle版本

# /ai/ai_summarizer.py

import os
import re
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from db.template_service import get_all_templates
# 引入翻譯官：包含標籤翻譯(get_chinese_name) 與 數值翻譯(translate_value)
from data.metadata import get_chinese_name, translate_value 

load_dotenv()

# ===== 本地模型支援 (新增) =====
try:
    from local_model_api_wrapper import get_local_client, is_local_model_available
    from local_model_config import AIModelSource, MODEL_SELECTION_STRATEGY, FALLBACK_CONFIG
    LOCAL_MODEL_AVAILABLE = True
except ImportError:
    print("⚠️ 本地模型支援未安裝，將使用 Groq")
    LOCAL_MODEL_AVAILABLE = False
# ===== 結束本地模型導入 =====

# --- 新增：終極防彈版異常值判斷函數 ---
def check_anomaly_v2(val, nh, nl):
    """
    利用 Regex 萃取數字，並相容 HIS 系統常見的異常標記
    """
    if val is None or str(val).strip() == "":
        return ""
    
    val_str = str(val).strip().upper()

    # 防線一：HIS 系統原生異常標記
    if "*" in val_str or val_str.endswith("H") or val_str.endswith("L"):
        return " 【⚠️異常(系統標記)】"

    # 防線二：危險文字攔截 (毒品、細菌培養等)
    danger_keywords = ["POSITIVE", "+", "陽性", "ABNORMAL", "異常", "DETECTED"]
    if any(keyword in val_str for keyword in danger_keywords) and "FALSE" not in val_str:
        return " 【⚠️異常/陽性】"

    # 防線三：Regex 數字萃取與精準比對
    num_pattern = r"[-+]?\d*\.\d+|\d+" 
    
    val_match = re.search(num_pattern, val_str)
    nh_match = re.search(num_pattern, str(nh)) if nh else None
    nl_match = re.search(num_pattern, str(nl)) if nl else None

    if val_match:
        v = float(val_match.group())
        
        if nh_match:
            h_limit = float(nh_match.group())
            if v > h_limit:
                return " 【⚠️異常偏高】"
        
        if nl_match:
            l_limit = float(nl_match.group())
            if v < l_limit:
                return " 【⚠️異常偏低】"

    return ""

# --- 修改：自動標籤化 + 數值翻譯 + 重複數據過濾 + 異常標記 ---
def auto_label_data(data_list):
    """將 list 中的 dict 轉換為中文標籤，並自動進行『數值代碼翻譯』、『去重』與『異常標記』"""
    if not data_list:
        return ""
    
    result_lines = []
    seen_records = set()
    
    for item in data_list:
        # 1. 去重邏輯：同一時間、同一項目、同一數值視為重複
        item_name = item.get('CHHEAD') or item.get('SUBJECT') or "項目"
        item_val = item.get('CHVAL') or item.get('DIAGNOSIS') or "數值"
        timestamp = item.get('PROCDTTM') or item.get('CHRCPDTM') or item.get('CHSIGNDTTM') or ""
        record_id = f"{timestamp}_{item_name}_{item_val}"
        
        if record_id in seen_records:
            continue
        seen_records.add(record_id)

        # 2. 取得此筆資料的結果值與參考上下限 (用於異常判斷)
        raw_val = item.get('CHVAL')
        raw_nh = item.get('CHNH')
        raw_nl = item.get('CHNL')
        
        # 呼叫異常判斷函數取得標籤 (如果是護理紀錄，這些值會是 None，函數會安全回傳空字串)
        anomaly_tag = check_anomaly_v2(raw_val, raw_nh, raw_nl)

        # 3. 遍歷欄位並進行翻譯與組裝
        parts = []
        for key, value in item.items():
            # 跳過系統內部欄位與時間
            if key in ['PROCDTTM', 'CHRCPDTM', 'CHAPPDTM', 'CHSIGNDTTM', 'VISITDT', 'ID', 'TRINO', 'PATID']:
                continue
            
            val_str = str(value).strip()
            # 過濾無效字串 (None / Null)
            if not val_str or val_str.lower() in ["none", "none~none", "null"]:
                continue
            
            # 欄位標籤與數值翻譯
            label = get_chinese_name(key)            
            final_val = translate_value(key, value)   
            
            # 【關鍵修改】：如果是結果值 (CHVAL)，就把異常標籤黏在它後面！
            if key == 'CHVAL':
                final_val = f"{final_val}{anomaly_tag}"
            
            parts.append(f"{label}: {final_val}")
        
        if parts:
            result_lines.append(f"- {timestamp} | {' | '.join(parts)}")
    
    return "\n".join(result_lines)

def generate_nursing_summary(
    encounter_id, 
    patient_data, 
    template_name, 
    custom_system_prompt=None, 
    focus_areas=None,
    model_source: str = "auto"
):
    """
    生成護理摘要 - 支持本地模型和 Groq
    
    Args:
        encounter_id: 就醫序號
        patient_data: 患者臨床資料
        template_name: 模板名稱
        custom_system_prompt: 自定系統提示
        focus_areas: 關注項目
        model_source: 模型來源 ("auto", "local", "groq")
    """
    
    # 因為 patient_data 現在是字串，我們直接檢查字串是否為空或包含錯誤訊息
    if not patient_data or "找不到" in patient_data:
        return "錯誤：無資料可分析。"

    # === 1. 獲取模板 ===
    db_templates = get_all_templates()
    base_system_prompt = db_templates.get(template_name) if db_templates else "你是專業醫療人員。"

    # === 2. 決定 System Prompt ===
    selected_system_prompt = custom_system_prompt if custom_system_prompt else base_system_prompt

    # === 3. 加入關注項目 (Focus Areas) ===
    if focus_areas:
        selected_system_prompt += f"\n\n**【⚠️ 特別指令：重點關注項目】**\n- {', '.join(focus_areas)}"

    # === 4. 建構 User Prompt ===
    data_text = f"=== 就醫序號: {encounter_id} 急診臨床資料 ===\n\n{patient_data}"

    # === 5. 決定使用哪個 AI 模型 ===
    selected_model = _select_ai_model(model_source)
    
    print("\n" + "🚀" + "="*50)
    print(f"模型選擇: {selected_model.value.upper()}")
    print("="*50)
    
    try:
        if selected_model == AIModelSource.LOCAL and LOCAL_MODEL_AVAILABLE:
            return _call_local_model(selected_system_prompt, data_text, encounter_id)
        else:
            return _call_groq_model(selected_system_prompt, data_text, encounter_id)
    
    except Exception as e:
        # 如果啟用回退策略，嘗試另一個模型
        if FALLBACK_CONFIG["enable_fallback"] and selected_model == AIModelSource.LOCAL:
            print(f"\n⚠️ 本地模型失敗: {e}")
            print("🔄 嘗試回退到 Groq...")
            return _call_groq_model(selected_system_prompt, data_text, encounter_id)
        else:
            raise


def _select_ai_model(model_source: str):
    """
    根據配置和可用性選擇模型
    
    Args:
        model_source: "auto" (自動選擇) / "local" (強制本地) / "groq" (強制 Groq)
    
    Returns:
        選定的模型來源
    """
    
    if model_source == "groq":
        return AIModelSource.GROQ
    elif model_source == "local":
        if not LOCAL_MODEL_AVAILABLE:
            print("❌ 本地模型不可用，強制使用 Groq")
            return AIModelSource.GROQ
        return AIModelSource.LOCAL
    elif model_source == "auto":
        # 自動邏輯：優先本地，備用 Groq
        if LOCAL_MODEL_AVAILABLE and is_local_model_available():
            return AIModelSource.LOCAL
        else:
            return AIModelSource.GROQ
    else:
        print(f"⚠️ 未知模型源: {model_source}，使用預設值")
        return MODEL_SELECTION_STRATEGY["default"]


def _call_local_model(system_prompt: str, data_text: str, encounter_id: str) -> str:
    """
    使用本地 Mistral 7B 模型生成摘要
    """
    print("\n🖥️ 本地模型推理中...")
    print(f"[System Prompt]:\n{system_prompt[:200]}...")
    print(f"[Patient Data]:\n{data_text[:200]}...\n(資料省略)")
    print("="*50 + "\n")
    
    try:
        client = get_local_client()
        result = client.chat_completion(
            system_prompt=system_prompt,
            user_message=data_text,
            temperature=0.3
        )
        
        summary = result["content"]
        model_name = result.get("model", "mistral")
        tokens_used = result["usage"]["completion_tokens"]
        
        print(f"✅ 本地模型成功生成 ({tokens_used} tokens)")
        return summary
        
    except Exception as e:
        print(f"❌ 本地模型錯誤: {str(e)}")
        raise


def _call_groq_model(system_prompt: str, data_text: str, encounter_id: str) -> str:
    """
    使用 Groq API 生成摘要 (原始邏輯)
    """
    print("\n☁️  Groq API 推理中...")
    print(f"[System Prompt]:\n{system_prompt[:200]}...")
    print(f"[Patient Data]:\n{data_text[:200]}...\n(資料省略)")
    print("="*50 + "\n")
    
    # ⚠️ 拔除舊的 st.secrets，改用 os.getenv 讀取 .env 的金鑰
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "錯誤：找不到 GROQ_API_KEY，請檢查 .env 檔案設定。"

    client = OpenAI(
        api_key=api_key, 
        base_url="https://api.groq.com/openai/v1"
    )
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data_text}
            ],
            temperature=0.3,
        )
        print("✅ Groq API 成功生成")
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ Groq API 錯誤: {e}")
        return f"AI 生成失敗: {e}"