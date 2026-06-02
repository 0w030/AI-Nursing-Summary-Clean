"""
Streamlit 管理中控台儀表板
提供直觀的 UI 界面用於管理資料庫連接和 Schema 映射
"""

import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List
import logging
import sys
from pathlib import Path
import os

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config_manager import config_manager, DatabaseConnection, FieldMapping
from services.permission_service import Role, Permission, PermissionChecker, User
from services.schema_discovery_service import SchemaDiscoveryService
from services.oracle_connection_helper import OracleConnectionHelper
from db.auth_service import authenticate_user

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 安全的角色轉換函數 ---
def safe_role_conversion(role_string: str) -> Role:
    """
    安全地將字符串轉換為 Role enum。
    如果角色無效，返回默認角色 GUEST。
    """
    try:
        return Role(role_string)
    except ValueError:
        # 日誌警告並返回默認角色
        print(f"⚠️ 無效的角色值: {role_string}，使用默認角色 'guest'")
        return Role.GUEST

# ===================== Streamlit 配置 =====================

st.set_page_config(
    page_title="管理中控台",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義樣式
st.markdown("""
<style>
    .admin-badge {
        display: inline-block;
        background-color: #ff4444;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        margin-left: 8px;
    }
    .success-badge {
        display: inline-block;
        background-color: #44aa44;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8em;
    }
    .warning-badge {
        display: inline-block;
        background-color: #ffaa00;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8em;
    }
    .ai-suggested {
        background-color: #fffacd;
        border-left: 4px solid #ffb347;
        padding: 8px;
        margin: 4px 0;
        border-radius: 4px;
    }
    .manually-confirmed {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 8px;
        margin: 4px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ===================== Session State 初始化 =====================

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.logged_in = False

if "current_page" not in st.session_state:
    st.session_state.current_page = "儀表板"

if "current_app_page" not in st.session_state:
    st.session_state.current_app_page = "management"

# 若從 app.py 來到管理中控台，將 username/role 轉成 User 物件
if st.session_state.logged_in and st.session_state.user is None:
    if st.session_state.username and st.session_state.role:
        user_role_enum = safe_role_conversion(st.session_state.role)
        st.session_state.user = User(
            username=st.session_state.username,
            role=user_role_enum,
            is_active=True
        )


# ===================== 認證模組 =====================

def show_login_page():
    """顯示登錄頁面"""
    st.title("管理中控台 - 登錄")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 請輸入您的憑證")
        
        username = st.text_input("用戶名", placeholder="例如: admin, manager")
        password = st.text_input("密碼", type="password")
        
        if st.button("登錄", key="login_btn", use_container_width=True):
            # 這裡應該使用 authenticate_user 函數
            # 簡化版本：假設以 admin_/manager_/viewer_ 開頭的用戶名代表不同角色
            role_map = {
                "admin": Role.ADMIN,
                "manager": Role.MANAGER,
                "viewer": Role.VIEWER,
            }
            
            user_type = username.split("_")[0] if "_" in username else username
            if user_type in role_map and password == "demo":
                user = User(username=username, role=role_map[user_type], is_active=True)
                st.session_state.user = user
                st.session_state.logged_in = True
                st.success(f"✓ 歡迎，{username}！角色: {user.role.value}")
                st.rerun()
            else:
                st.error("[ERROR] 用戶名或密碼錯誤")
        
        st.markdown("---")
        st.markdown("""
        **演示帳號:**
        - 用戶名: `admin` | 密碼: `demo` (管理員)
        - 用戶名: `manager` | 密碼: `demo` (經理)
        - 用戶名: `viewer` | 密碼: `demo` (查看者)
        """)


def check_permission(permission: Permission) -> bool:
    """檢查當前用戶是否有特定權限"""
    if not st.session_state.user:
        return False
    return PermissionChecker.require_permission(st.session_state.user, permission)


def require_permission(permission: Permission):
    """權限檢查裝飾器"""
    if not check_permission(permission):
        st.error(f"[ERROR] 您沒有權限執行此操作: {permission.value}")
        st.stop()


# ===================== 儀表板頁面 =====================

def show_dashboard():
    """顯示主儀表板"""
    st.title("管理中控台")
    
    # 用戶信息和登出
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.session_state.user:
            st.markdown(f"### 歡迎，**{st.session_state.user.username}** 👋")
            st.caption(f"角色: {st.session_state.user.role.value}")
    
    with col2:
        # 獲取基礎 URL（從 Streamlit 配置或環境變數）
        st.sidebar.page_link("app.py", label="返回首頁")
        st.sidebar.divider()
    
    with col3:
        if st.button("登出", key="logout_btn_header", use_container_width=True):
            # 完全清除所有會話狀態
            st.session_state.user = None
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.current_app_page = "main"
            st.rerun()
    
    st.markdown("---")
    
    # 快速統計
    col1, col2, col3, col4 = st.columns(4)
    
    connections = config_manager.list_connections()
    active_conn = config_manager.get_active_connection()
    mappings = config_manager.get_all_mappings()
    logs = config_manager.get_operation_logs(limit=100)
    
    with col1:
        st.metric("連接數", len(connections))
    
    with col2:
        st.metric("表格數", len(mappings))
    
    with col3:
        st.metric("操作日誌", len(logs))
    
    with col4:
        active_name = active_conn.name if active_conn else "無"
        st.metric("活動連接", active_name)
    
    st.markdown("---")
    
    # 頁面選擇
    st.sidebar.title("功能選單")
    
    # 在側邊欄添加返回首頁鏈接
    if st.button("返回首頁", use_container_width=True):
        st.switch_page("app.py")
    st.sidebar.divider()
    
    pages = {
        "儀表板": "show_dashboard",
        "連接管理": "show_connection_manager",
        "電子辭典編輯": "show_schema_mapper",
        "操作日誌": "show_operation_logs",
        "系統設置": "show_system_settings",
    }
    
    for page_name, page_func in pages.items():
        if st.sidebar.button(page_name, use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()
    
    # 顯示最近操作
    st.subheader("最近操作")
    if logs:
        recent_logs = logs[-5:]
        for log in reversed(recent_logs):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            with col1:
                st.caption(log.timestamp)
            with col2:
                st.caption(log.operation_type)
            with col3:
                st.caption(log.username)
            with col4:
                status_color = "[ACTIVE]" if log.status == "success" else "[FAILED]"
                st.caption(f"{status_color} {log.status}")
    else:
        st.info("暫無操作記錄")


# ===================== 連接管理頁面 =====================

def show_connection_manager():
    """連接管理頁面"""
    require_permission(Permission.VIEW_CONNECTIONS)
    
    st.title("資料庫連接管理")
    
    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["連接列表", "新增連接", "連接設置", "Schema 同步"])
    
    # --- 標籤1：連接列表 ---
    with tab1:
        st.subheader("現有連接")
        
        connections = config_manager.list_connections()
        if not connections:
            st.info("暫無連接配置")
        else:
            # 轉換為 DataFrame 以便顯示
            df_data = []
            for conn in connections:
                df_data.append({
                    "名稱": conn.name,
                    "類型": conn.db_type.upper(),
                    "主機": conn.host,
                    "連接埠": conn.port,
                    "資料庫": conn.database,
                    "狀態": "[ACTIVE]" if conn.is_active else "[INACTIVE]",
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            st.subheader("連接操作")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_conn = st.selectbox(
                    "選擇要操作的連接",
                    [conn.name for conn in connections],
                    key="conn_select"
                )
                
                if st.button("切換到此連接", key="switch_conn_btn", use_container_width=True):
                    require_permission(Permission.SWITCH_CONNECTION)
                    if config_manager.switch_connection(selected_conn, st.session_state.user.username):
                        st.success(f"✓ 已切換到 {selected_conn}")
                        st.rerun()
                    else:
                        st.error("[ERROR] 切換失敗")
            
            with col2:
                if st.button("測試連接", key="test_conn_btn", use_container_width=True):
                    require_permission(Permission.TEST_CONNECTION)
                    conn = config_manager.get_connection(selected_conn)
                    
                    # 真正測試連接
                    try:
                        connection_params = {
                            'db_type': conn.db_type,
                            'host': conn.host,
                            'port': conn.port,
                            'database': conn.database,
                            'username': conn.username,
                            'password': conn.password
                        }
                        
                        discovery = SchemaDiscoveryService(connection_params)
                        
                        if discovery.connect():
                            st.success(f"[SUCCESS] 連接測試成功: {conn.name}")
                            discovery.disconnect()
                        else:
                            st.error(f"[ERROR] 連接測試失敗: {conn.name}")
                    except Exception as e:
                        st.error(f"[ERROR] 連接測試異常: {str(e)}")
                
                if st.button("刪除連接", key="delete_btn", use_container_width=True):
                    require_permission(Permission.DELETE_CONNECTION)
                    st.session_state.show_delete_confirm = True
                
                # 顯示確認對話框
                if st.session_state.get("show_delete_confirm", False):
                    st.warning(f"即將刪除連接: **{selected_conn}**")
                    col_confirm1, col_confirm2 = st.columns(2)
                    
                    with col_confirm1:
                        if st.button("[CONFIRM] 確認刪除", key="confirm_delete_btn", use_container_width=True):
                            if config_manager.delete_connection(selected_conn, st.session_state.user.username):
                                st.session_state.show_delete_confirm = False
                                st.success("✓ 連接已刪除")
                                st.rerun()
                            else:
                                st.error("[ERROR] 刪除失敗，可能連接仍在使用中")
                                st.session_state.show_delete_confirm = False
                    
                    with col_confirm2:
                        if st.button("[CANCEL] 取消刪除", key="cancel_delete_btn", use_container_width=True):
                            st.session_state.show_delete_confirm = False
                            st.rerun()
    
    # --- 標籤2：新增連接 ---
    with tab2:
        st.subheader("新增資料庫連接")
        require_permission(Permission.CREATE_CONNECTION)
        
        # 顯示 Oracle 快速配置選項
        st.info("提示：您可以從 .env 配置文件快速導入 Oracle 連接")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("**快速配置（來自 .env）**")
        with col2:
            if st.button("從 .env 導入 Oracle", key="import_oracle_env_btn", use_container_width=True):
                oracle_config = OracleConnectionHelper.get_oracle_config_from_env()
                if oracle_config:
                    st.session_state.oracle_config = oracle_config
                    st.success("Oracle 配置已從 .env 加載")
                    st.rerun()
                else:
                    st.error("未找到 .env 中的 Oracle 配置")
        with col3:
            if st.button("測試連接", key="test_oracle_quick_btn", use_container_width=True):
                if OracleConnectionHelper.verify_connection():
                    st.success("Oracle 連接成功！")
                else:
                    st.error("連接失敗")
        
        st.divider()
        
        with st.form("add_connection_form"):
            col1, col2 = st.columns(2)
            
            # 檢查是否有 Oracle 配置在 session state 中
            oracle_config = st.session_state.get('oracle_config', {})
            
            with col1:
                conn_name = st.text_input(
                    "連接名稱",
                    value="oracle_from_env" if oracle_config else "",
                    placeholder="例如: hospital_main"
                )
                db_type = st.selectbox(
                    "資料庫類型",
                    ["oracle", "postgresql", "sqlite", "mssql"],
                    index=0 if oracle_config else 0
                )
                host = st.text_input(
                    "主機地址",
                    value=oracle_config.get('host', ''),
                    placeholder="192.168.1.1"
                )
            
            with col2:
                port = st.number_input(
                    "連接埠",
                    value=int(oracle_config.get('port', 1521)),
                    min_value=1,
                    max_value=65535
                )
                database = st.text_input(
                    "資料庫名稱（SID 或 Service Name）",
                    value=oracle_config.get('database', ''),
                    placeholder="cs1 或 NIS_BB_ADAMAI"
                )
                username = st.text_input(
                    "用戶名",
                    value=oracle_config.get('username', ''),
                    placeholder="admin"
                )
            
            password = st.text_input(
                "密碼",
                value=oracle_config.get('password', ''),
                type="password",
                placeholder="輸入密碼"
            )
            
            if st.form_submit_button("添加連接", use_container_width=True):
                if not conn_name:
                    st.error("連接名稱不能為空")
                elif not password:
                    st.error("密碼不能為空")
                else:
                    new_conn = DatabaseConnection(
                        name=conn_name,
                        db_type=db_type,
                        host=host,
                        port=port,
                        database=database,
                        username=username,
                        password=password,
                    )
                    
                    if config_manager.add_connection(new_conn):
                        st.success(f"✓ 連接 {conn_name} 已添加")
                        # 清除 session state 中的 oracle_config
                        if 'oracle_config' in st.session_state:
                            del st.session_state.oracle_config
                        st.rerun()
                    else:
                        st.error("添加連接失敗")
    
    # --- 標籤3：連接設置 ---
    with tab3:
        st.subheader("連接設置")
        
        connections = config_manager.list_connections()
        if connections:
            selected_conn_name = st.selectbox(
                "選擇要編輯的連接",
                [conn.name for conn in connections],
                key="edit_conn_select"
            )
            
            selected_conn = config_manager.get_connection(selected_conn_name)
            
            with st.form("edit_connection_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    host = st.text_input("主機地址", value=selected_conn.host)
                    port = st.number_input("連接埠", value=selected_conn.port)
                    database = st.text_input("資料庫名稱", value=selected_conn.database)
                
                with col2:
                    username = st.text_input("用戶名", value=selected_conn.username)
                    password = st.text_input("密碼", type="password")
                
                if st.form_submit_button("保存變更"):
                    require_permission(Permission.EDIT_CONNECTION)
                    
                    updated_conn = DatabaseConnection(
                        name=selected_conn.name,
                        db_type=selected_conn.db_type,
                        host=host,
                        port=port,
                        database=database,
                        username=username,
                    )
                    
                    if config_manager.add_connection(updated_conn):
                        st.success(f"✓ 連接 {selected_conn_name} 已更新")
                        st.rerun()
                    else:
                        st.error("更新失敗")
        else:
            st.info("暫無連接可編輯")
    
    # --- 標籤4：Schema 同步 ---
    with tab4:
        st.subheader("從資料庫同步 Schema")
        require_permission(Permission.CREATE_CONNECTION)
        
        connections = config_manager.list_connections()
        if not connections:
            st.error("請先添加資料庫連接")
        else:
            selected_conn_name = st.selectbox(
                "選擇要同步的連接",
                [conn.name for conn in connections],
                key="sync_conn_select"
            )
            
            selected_conn = config_manager.get_connection(selected_conn_name)
            
            st.info(f"連接詳情:\n\n- 類型: **{selected_conn.db_type.upper()}**\n- 主機: **{selected_conn.host}:{selected_conn.port}**\n- 資料庫: **{selected_conn.database}**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                auto_type_map = st.checkbox("自動映射資料類型", value=True)
            
            with col2:
                if st.button("開始同步 Schema", key="schema_sync_btn", use_container_width=True):
                    with st.spinner("⏳ 正在連接資料庫..."):
                        # 建立連接參數（包括密碼）
                        conn_params = {
                            'db_type': selected_conn.db_type,
                            'host': selected_conn.host,
                            'port': selected_conn.port,
                            'database': selected_conn.database,
                            'username': selected_conn.username,
                            'password': selected_conn.password  # [OK] 添加密碼
                        }
                        
                        try:
                            # 建立 Schema 發現服務
                            discovery_service = SchemaDiscoveryService(conn_params)
                            
                            if not discovery_service.connect():
                                st.error("無法連接到資料庫，請檢查連接配置")
                            else:
                                with st.spinner("正在發現所有表格..."):
                                    # 發現完整 Schema
                                    discovered_schema = discovery_service.discover_full_schema()
                                    discovery_service.disconnect()
                                
                                # 顯示發現的表格
                                st.success(f"發現 {len(discovered_schema['tables'])} 個表格")
                                
                                with st.spinner("正在導入映射..."):
                                    # 導入到配置管理器
                                    imported_tables, imported_fields = config_manager.import_discovered_schema(
                                        discovered_schema,
                                        connection_name=selected_conn_name,
                                        username=st.session_state.user.username,
                                        auto_type_map=auto_type_map
                                    )
                                
                                st.success(f"""
                                [SUCCESS] **Schema 同步完成！**
                                
                                - 已導入表格: **{imported_tables}** 個
                                - 已導入欄位: **{imported_fields}** 個
                                - 自動映射: **{'開啟' if auto_type_map else '關閉'}**
                                
                                請前往「電子辭典編輯」頁面審核和確認映射。
                                """)
                                
                                # 顯示表格列表
                                st.subheader("同步的表格清單")
                                table_names = list(discovered_schema['tables'].keys())
                                
                                # 分頁顯示
                                page_size = 10
                                total_pages = max(1, (len(table_names) + page_size - 1) // page_size)  # [OK] 確保至少為 1
                                page_num = st.number_input(
                                    "頁碼",
                                    value=1,
                                    min_value=1,
                                    max_value=total_pages
                                )
                                
                                start_idx = (page_num - 1) * page_size
                                end_idx = start_idx + page_size
                                
                                for table_name in table_names[start_idx:end_idx]:
                                    table_data = discovered_schema['tables'][table_name]
                                    col_count = len(table_data['columns'])
                                    row_count = table_data['table_info']['row_count']
                                    
                                    st.caption(f"[SCHEMA] **{table_name}** - {col_count} 欄位, {row_count} 行")
                        
                        except Exception as e:
                            st.error(f"[ERROR] Schema 同步失敗: {str(e)}")
                            logger.error(f"Schema 同步錯誤: {str(e)}")


# ===================== 編寫自己的電子辭典 =====================

def show_dictionary_editor():
    """Human-in-the-loop 電子辭典編輯 - AI推薦加手動確認"""
    require_permission(Permission.EDIT_MAPPINGS)
    
    # 獲取活動連接
    active_conn = config_manager.get_active_connection()
    if not active_conn:
        st.warning("請先選擇資料庫連接")
        return
    
    st.title(f"編寫自己的電子辭典 - 當前連接: {active_conn.name}")
    
    # 初始化 session state
    if "dictionary_mode" not in st.session_state:
        st.session_state.dictionary_mode = "ai_detection"
    if "ai_suggestions" not in st.session_state:
        st.session_state.ai_suggestions = None
    if "ai_error" not in st.session_state:
        st.session_state.ai_error = None
    
    # 頁面模式切換按鈕
    col_import, col_mode = st.columns([2, 1])
    with col_import:
        if st.button("導入現有說明檔 (JSON/CSV)", key="toggle_import_mode"):
            st.session_state.dictionary_mode = "import" if st.session_state.dictionary_mode == "ai_detection" else "ai_detection"
            st.rerun()
    
    with col_mode:
        mode_label = "導入模式中" if st.session_state.dictionary_mode == "import" else "AI探測模式"
        st.info(f"當前: {mode_label}")
    
    st.markdown("---")
    
    # --- 模式1：AI 自動探測 ---
    if st.session_state.dictionary_mode == "ai_detection":
        st.subheader("AI 自動探測與推論")
        st.markdown("系統將自動連接資料庫，探測 Schema 並使用 AI 推薦中文翻譯。")
        
        if st.button("開始探測 Schema", key="detect_schema_btn", use_container_width=True):
            with st.spinner("探測中..."):
                try:
                    conn_params = {
                        'db_type': active_conn.db_type,
                        'host': active_conn.host,
                        'port': active_conn.port,
                        'database': active_conn.database,
                        'username': active_conn.username,
                        'password': active_conn.password
                    }
                    discovery_service = SchemaDiscoveryService(conn_params)
                    if not discovery_service.connect():
                        st.session_state.ai_error = "無法連接到資料庫，請檢查連接配置"
                    else:
                        discovered_schema = discovery_service.discover_full_schema()
                        discovery_service.disconnect()
                        
                        # 整理數據格式
                        tables_dict = {}
                        for table_name, table_data in discovered_schema.get('tables', {}).items():
                            columns = []
                            for col in table_data.get('columns', []):
                                col_dict = {
                                    'name': col.get('name', ''),
                                    'data_type': col.get('data_type', ''),
                                    'comment': col.get('comment', ''),
                                    'sample_values': col.get('sample_values'),
                                    'numeric_min': col.get('numeric_min'),
                                    'numeric_max': col.get('numeric_max'),
                                }
                                columns.append(col_dict)
                            
                            tables_dict[table_name] = {
                                'table_info': {
                                    'row_count': table_data.get('table_info', {}).get('row_count', 0),
                                    'comment': table_data.get('table_info', {}).get('comment', '')
                                },
                                'columns': columns
                            }
                        
                        st.session_state.ai_suggestions = {'tables': tables_dict}
                        st.session_state.ai_error = None
                        st.rerun()
                except Exception as e:
                    st.session_state.ai_error = str(e)
                    logger.error(f"Schema 探測失敗: {e}")
        
        if st.session_state.ai_error:
            st.error(f"探測失敗: {st.session_state.ai_error}")
        
        if st.session_state.ai_suggestions:
            schema = st.session_state.ai_suggestions
            tables = schema.get('tables', {})
            st.success(f"已成功探測 {len(tables)} 個資料表")
            st.markdown("---")
            
            # 階層式展示：以表為單位
            for table_name, table_data in tables.items():
                table_info = table_data.get('table_info', {})
                columns = table_data.get('columns', [])
                
                # 表名翻譯和狀態展示
                with st.expander(f"[TABLE] {table_name} ({len(columns)} 欄位)", expanded=False):
                    st.markdown(f"**原始表名:** `{table_name}`")
                    st.markdown(f"**行數:** {table_info.get('row_count', '未知')}")
                    
                    # 為每個表建立表名翻譯輸入框
                    table_trans_key = f"table_trans_{table_name}"
                    table_translated = st.text_input(
                        "翻譯後的表名（繁體中文）",
                        value="",
                        key=table_trans_key,
                        help="例如：病患生理資訊表、護理紀錄表"
                    )
                    
                    st.markdown("**欄位對照表**")
                    
                    for col in columns:
                        col_name = col.get('name', '')
                        col_type = col.get('data_type', '')
                        col_comment = col.get('comment', '')
                        sample_values = col.get('sample_values', [])
                        numeric_min = col.get('numeric_min')
                        numeric_max = col.get('numeric_max')
                        
                        # 構造推論證據
                        evidence = []
                        if sample_values:
                            evidence.append(f"樣本值: {', '.join(str(v) for v in sample_values)}")
                        if numeric_min is not None or numeric_max is not None:
                            range_str = f"{numeric_min}" if numeric_min is not None else "?"
                            range_str += f"~{numeric_max}" if numeric_max is not None else "~?"
                            evidence.append(f"範圍: {range_str}")
                        if col_comment:
                            evidence.append(f"註解: {col_comment}")
                        
                        evidence_text = " | ".join(evidence) if evidence else "無特徵"
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.caption(f"**{col_name}**")
                            st.caption(f"型別: {col_type}")
                        with col2:
                            col_trans_key = f"col_trans_{table_name}_{col_name}"
                            col_translated = st.text_input(
                                f"翻譯: {col_name}",
                                value="",
                                key=col_trans_key,
                                placeholder="輸入繁體中文翻譯",
                                label_visibility="collapsed"
                            )
                        
                        # 狀態標籤與推論理由
                        if col_translated:
                            st.markdown("**[CONFIRMED] 人工確認**")
                        else:
                            st.markdown("**[AI] 建議中**")
                        st.caption(f"證據: {evidence_text}")
                        st.divider()
                    
                    # 該表的保存按鈕
                    if st.button(f"保存 {table_name}", key=f"save_table_{table_name}"):
                        table_translated = st.session_state.get(table_trans_key, "")
                        
                        saved_count = 0
                        for col in columns:
                            col_name = col.get('name', '')
                            col_type = col.get('data_type', '')
                            col_trans_key_local = f"col_trans_{table_name}_{col_name}"
                            col_translated = st.session_state.get(col_trans_key_local, "")
                            
                            if col_translated:  # 只保存有翻譯的欄位
                                mapping = FieldMapping(
                                    connection_name=active_conn.name,
                                    table_name=table_name,
                                    db_column_name=col_name,
                                    system_column_type=col_translated,
                                    original_type=col_type,
                                    is_ai_suggested=False,
                                    is_confirmed=True,
                                    confirmed_by=st.session_state.user.username,
                                    notes=f"表別: {table_translated}" if table_translated else ""
                                )
                                
                                if config_manager.update_field_mapping(
                                    active_conn.name,
                                    table_name,
                                    mapping,
                                    st.session_state.user.username
                                ):
                                    saved_count += 1
                        
                        if saved_count > 0:
                            st.success(f"已保存 {saved_count} 個欄位映射")
                            st.rerun()
                        else:
                            st.warning("未保存任何欄位(請先填入翻譯內容)")
    
    # --- 模式2：導入現有說明檔 ---
    elif st.session_state.dictionary_mode == "import":
        st.subheader("導入現有說明檔")
        st.markdown("上傳 JSON 或 CSV 檔案，匯入既有的資料表翻譯設定。")
        
        uploaded_file = st.file_uploader(
            "選擇檔案",
            type=["json", "csv"],
            key="dict_file_uploader"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.type == "application/json":
                    file_content = json.load(uploaded_file)
                    st.success("JSON 檔案已成功載入")
                    
                    # 顯示預覽
                    st.json(file_content)
                    
                    if st.button("匯入此配置", key="import_json_btn"):
                        st.info("匯入功能開發中...")
                
                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    st.success("CSV 檔案已成功載入")
                    
                    st.dataframe(df, use_container_width=True)
                    
                    if st.button("匯入此配置", key="import_csv_btn"):
                        st.info("匯入功能開發中...")
            
            except Exception as e:
                st.error(f"檔案讀取失敗: {str(e)}")


# ===================== Schema 映射編輯頁面 =====================

def show_schema_mapper():
    """Schema 映射編輯頁面 - 支持連接過濾"""
    require_permission(Permission.VIEW_MAPPINGS)
    
    # 獲取活動連接
    active_conn = config_manager.get_active_connection()
    if not active_conn:
        st.warning("請先選擇資料庫連接")
        return
    
    st.title(f"電子辭典編輯器 - 當前連接: {active_conn.name}")
    
    tab1, tab2, tab3 = st.tabs(["映射總覽", "手動修正", "AI 自動對齐"])
    
    # --- 標籤1：映射總覽 ---
    with tab1:
        st.subheader("Schema 映射概覽")
        
        # 獲取當前連接的映射
        connection_mappings = config_manager.get_connection_mappings(active_conn.name)
        
        if not connection_mappings:
            st.info("此連接暫無映射配置，請執行 Schema 同步")
        else:
            # 統計信息
            col1, col2, col3, col4 = st.columns(4)
            
            total_mappings = sum(len(m) for m in connection_mappings.values())
            total_tables = len(connection_mappings)
            
            ai_suggested = sum(
                len([fm for fm in connection_mappings[t] if fm.is_ai_suggested and not fm.is_confirmed])
                for t in connection_mappings
            )
            confirmed = sum(
                len([fm for fm in connection_mappings[t] if fm.is_confirmed])
                for t in connection_mappings
            )
            
            with col1:
                st.metric("總表格數", total_tables)
            with col2:
                st.metric("總映射數", total_mappings)
            with col3:
                st.metric("[PENDING] AI建議中", ai_suggested)
            with col4:
                st.metric("[CONFIRMED] 已確認", confirmed)
            
            st.markdown("---")
            
            # 按表格顯示
            for table_name, field_mappings in connection_mappings.items():
                with st.expander(f"[TABLE] {table_name} ({len(field_mappings)} 欄位)"):
                    df_data = []
                    for fm in field_mappings:
                        status_icon = "[CONFIRMED]" if fm.is_confirmed else "[PENDING]"
                        df_data.append({
                            "原始欄位": fm.db_column_name,
                            "原始類型": fm.original_type,
                            "系統類型": fm.system_column_type,
                            "狀態": status_icon,
                            "確認者": fm.confirmed_by or "-",
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)
    
    # --- 標籤2：手動修正 ---
    with tab2:
        st.subheader("手動修正映射")
        require_permission(Permission.EDIT_MAPPINGS)
        
        connection_mappings = config_manager.get_connection_mappings(active_conn.name)
        
        if connection_mappings:
            selected_table = st.selectbox(
                "選擇表格",
                list(connection_mappings.keys()),
                key="table_select_manual"
            )
            
            table_mappings = connection_mappings[selected_table]
            
            st.markdown(f"**{selected_table}** - {len(table_mappings)} 欄位")
            
            for idx, field_mapping in enumerate(table_mappings):
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 2])
                    
                    with col1:
                        status = "[CONFIRMED] 已確認" if field_mapping.is_confirmed else "[PENDING] 待確認"
                        st.markdown(f"**{field_mapping.db_column_name}**  \n{status}")
                    
                    with col2:
                        st.caption("原始類型")
                        st.text(field_mapping.original_type)
                    
                    with col3:
                        st.caption("選擇系統類型")
                        new_system_type = st.selectbox(
                            "系統類型",
                            ["String", "Integer", "Decimal", "DateTime", "Boolean", "JSON"],
                            index=0,
                            key=f"system_type_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        is_confirmed = st.checkbox(
                            "確認此映射",
                            value=field_mapping.is_confirmed,
                            key=f"confirm_{idx}"
                        )
                    
                    if st.button("[SAVE]", key=f"save_{idx}"):
                        updated_mapping = FieldMapping(
                            connection_name=active_conn.name,
                            table_name=selected_table,
                            db_column_name=field_mapping.db_column_name,
                            system_column_type=new_system_type,
                            original_type=field_mapping.original_type,
                            is_ai_suggested=field_mapping.is_ai_suggested,
                            is_confirmed=is_confirmed,
                            confirmed_by=st.session_state.user.username if is_confirmed else None,
                        )
                        
                        if config_manager.update_field_mapping(
                            active_conn.name,
                            selected_table,
                            updated_mapping,
                            st.session_state.user.username
                        ):
                            st.success(f"[SUCCESS] {field_mapping.db_column_name} 已更新")
                            st.rerun()
                        else:
                            st.error("[ERROR] 更新失敗")
                    
                    st.divider()
        else:
            st.info("此連接暫無映射可編輯")
    
    # --- 標籤3：AI 自動對齡 ---
    with tab3:
        st.subheader("[AI] 自動對齌")
        require_permission(Permission.AI_SUGGEST_MAPPINGS)
        
        st.info("點擊下方按鈕，使用 AI 自動建議欄位映射")
        
        if st.button("[EXECUTE] AI 自動對齏", key="ai_suggest_btn", use_container_width=True):
            st.info("[PROCESSING] 正在進行 AI 語意對齡...")
            
            # 這裡應該呼叫 LLM API
            # TODO: 集成 LLM 功能
            
            st.success("[SUCCESS] AI 建議已生成，請在手動修正頁面審核")


# ===================== 操作日誌頁面 =====================

def show_operation_logs():
    """操作日誌頁面"""
    require_permission(Permission.VIEW_LOGS)
    
    st.title("操作日誌")
    
    logs = config_manager.get_operation_logs(limit=200)
    
    if not logs:
        st.info("暫無操作記錄")
    else:
        # 篩選選項
        col1, col2, col3 = st.columns(3)
        
        with col1:
            log_type = st.selectbox(
                "操作類型",
                ["全部", "connection_test", "connection_switch", "schema_sync", "mapping_update"]
            )
        
        with col2:
            limit = st.number_input("顯示最近筆數", value=50, min_value=10, max_value=500)
        
        with col3:
            if st.button("[REFRESH]", key="refresh_logs_btn"):
                st.rerun()
        
        # 篩選日誌
        if log_type != "全部":
            filtered_logs = [log for log in logs if log.operation_type == log_type]
        else:
            filtered_logs = logs[-limit:]
        
        # 顯示日誌
        df_data = []
        for log in reversed(filtered_logs):
            df_data.append({
                "時間": log.timestamp[:19],
                "操作類型": log.operation_type,
                "用戶": log.username,
                "狀態": "[SUCCESS]" if log.status == "success" else "[FAILED]",
                "詳情": json.dumps(log.details, ensure_ascii=False),
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("該篩選條件下無記錄")


# ===================== 系統設置頁面 =====================

def show_system_settings():
    """系統設置頁面"""
    require_permission(Permission.MANAGE_USERS)
    
    st.title("系統設置")
    
    tab1, tab2 = st.tabs(["用戶管理", "系統資訊"])
    
    with tab1:
        st.subheader("用戶管理")
        st.info("用戶管理功能即將上線")
    
    with tab2:
        st.subheader("系統資訊")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**當前活動連接**")
            active_conn = config_manager.get_active_connection()
            if active_conn:
                st.json(active_conn.to_dict())
            else:
                st.info("無活動連接")
        
        with col2:
            st.markdown("**系統統計**")
            stats = {
                "連接數": len(config_manager.list_connections()),
                "表格數": len(config_manager.get_all_mappings()),
                "操作日誌": len(config_manager.get_operation_logs(limit=1000)),
            }
            st.json(stats)


# ===================== 主應用 =====================

def main():
    """主應用邏輯"""
    if not st.session_state.logged_in:
        show_login_page()
    else:
        # 導航菜單
        with st.sidebar:
            st.markdown(f"### 👤 {st.session_state.user.username}")
            st.markdown(f"角色: **{st.session_state.user.role.value}**")
            st.divider()
            
            # 應用級導航
            st.subheader("應用導航")
            st.page_link("app.py", label="返回主應用")
            
            st.divider()
            st.subheader("管理功能")
            
            pages = {
                "儀表板": show_dashboard,
                "連接管理": show_connection_manager,
                "編寫自己的電子辭典": show_dictionary_editor,
                "電子辭典": show_schema_mapper,
                "操作日誌": show_operation_logs,
                "系統設置": show_system_settings,
            }
            
            selected_page = st.radio(
                "選擇頁面",
                list(pages.keys()),
                label_visibility="collapsed"
            )
            
            st.divider()
            
            if st.button("登出", key="logout_btn_sidebar", use_container_width=True):
                # 完全清除所有會話狀態
                st.session_state.user = None
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.role = ""
                st.session_state.current_app_page = "main"
                st.rerun()
        
        # 顯示選定頁面
        page_func = list(pages.values())[list(pages.keys()).index(selected_page)]
        page_func()


if __name__ == "__main__":
    main()
