#!/usr/bin/env python3
"""
第三階段 - 管理中控台 快速啟動腳本
一鍵啟動前端和後端服務
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# 顏色輸出
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def check_requirements():
    """檢查必要的依賴"""
    print_info("檢查依賴...")
    
    required_packages = {
        'streamlit': 'Streamlit',
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'pandas': 'Pandas',
    }
    
    missing = []
    for package, name in required_packages.items():
        try:
            __import__(package)
            print_success(f"{name} 已安裝")
        except ImportError:
            print_error(f"{name} 未安裝")
            missing.append(package)
    
    if missing:
        print_warning(f"缺少依賴: {', '.join(missing)}")
        print_info(f"請運行: pip install {' '.join(missing)}")
        return False
    
    return True


def check_config_directory():
    """檢查配置目錄"""
    print_info("檢查配置目錄...")
    
    config_dir = Path("config/management")
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"創建目錄: {config_dir}")
    else:
        print_success(f"目錄已存在: {config_dir}")


def init_demo_data():
    """初始化演示數據"""
    print_info("初始化演示數據...")
    
    try:
        from scripts.init_management_console import init_demo_data as init_func
        init_func()
        print_success("演示數據初始化完成")
    except Exception as e:
        print_error(f"初始化失敗: {e}")
        return False
    
    return True


def start_backend():
    """啟動後端 API 服務"""
    print_header("🚀 啟動後端 API 服務")
    
    print_info("啟動 FastAPI 服務於 http://localhost:8000")
    print_info("API 文檔: http://localhost:8000/docs")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "api.management_api:app", "--reload"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print_warning("後端服務已停止")
    except Exception as e:
        print_error(f"啟動後端失敗: {e}")


def start_frontend():
    """啟動前端 Streamlit 應用"""
    print_header("🎛️ 啟動前端 Streamlit 應用")
    
    print_info("啟動 Streamlit 應用於 http://localhost:8501")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "pages/management_dashboard.py"],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print_warning("前端應用已停止")
    except Exception as e:
        print_error(f"啟動前端失敗: {e}")


def show_menu():
    """顯示菜單"""
    print_header("第三階段 - 管理中控台 快速啟動")
    
    menu = """
    請選擇要執行的操作：
    
    1. 🔧 檢查環境和初始化
    2. 🌐 啟動後端 API 服務
    3. 🎛️  啟動前端 Streamlit 應用
    4. 🚀 同時啟動前端和後端 (需要兩個終端窗口)
    5. 📚 顯示使用指南
    6. 📊 顯示系統狀態
    7. 🚪 退出
    """
    
    print(menu)


def show_status():
    """顯示系統狀態"""
    print_header("📊 系統狀態")
    
    from services.config_manager import config_manager
    
    connections = config_manager.list_connections()
    mappings = config_manager.get_all_mappings()
    logs = config_manager.get_operation_logs()
    
    print(f"連接數:       {len(connections)}")
    print(f"表格數:       {len(mappings)}")
    print(f"總欄位數:     {sum(len(m) for m in mappings.values())}")
    print(f"操作日誌:     {len(logs)}")
    
    if connections:
        print(f"\n當前連接:")
        for conn in connections:
            status = "🟢 活動" if conn.is_active else "⚪ 非活動"
            print(f"  • {conn.name} ({conn.db_type}) - {status}")


def show_guide():
    """顯示使用指南"""
    print_header("📚 使用指南")
    
    guide = """
    🎯 快速開始
    ═══════════════════════════════════════════════════════════════════
    
    1️⃣  首次設置：
        python scripts/start_management_console.py
        選擇 1 - 檢查環境和初始化
    
    2️⃣  啟動服務：
        
        方式 A：分別啟動（推薦開發時使用）
            終端 1: python scripts/start_management_console.py → 選擇 2
            終端 2: python scripts/start_management_console.py → 選擇 3
        
        方式 B：同時啟動（需要 2 個終端）
            python scripts/start_management_console.py → 選擇 4
    
    3️⃣  訪問應用：
        • 前端: http://localhost:8501
        • 後端: http://localhost:8000/docs
    
    4️⃣  登錄憑證：
        • 用戶名: admin | 密碼: demo (管理員)
        • 用戶名: manager | 密碼: demo (經理)
        • 用戶名: viewer | 密碼: demo (查看者)
    
    ═══════════════════════════════════════════════════════════════════
    
    💡 提示
    ═══════════════════════════════════════════════════════════════════
    
    • 使用 Ctrl+C 停止服務
    • 修改代碼後，服務會自動重新加載 (--reload)
    • 配置自動保存到 config/management/*.json
    • 查看操作日誌了解系統活動
    
    🔗 相關文檔
    ═══════════════════════════════════════════════════════════════════
    
    • 完整使用指南: MANAGEMENT_CONSOLE_GUIDE.md
    • 系統架構: MANAGEMENT_CONSOLE_ARCHITECTURE.md
    • API 文檔: http://localhost:8000/docs
    """
    
    print(guide)


def main():
    """主菜單"""
    os.chdir(Path(__file__).parent)
    
    while True:
        print_header("第三階段 - 管理中控台 啟動器")
        show_menu()
        
        try:
            choice = input(f"{Colors.BOLD}請輸入選擇 [1-7]: {Colors.ENDC}").strip()
            
            if choice == "1":
                if check_requirements():
                    check_config_directory()
                    init_demo_data()
                    print_success("環境設置完成！")
            
            elif choice == "2":
                start_backend()
            
            elif choice == "3":
                start_frontend()
            
            elif choice == "4":
                print_warning("需要兩個終端窗口")
                print_info("終端 1: 後端服務")
                print_info("終端 2: 前端應用")
                input(f"{Colors.BOLD}按 Enter 鍵開始...{Colors.ENDC}")
                
                try:
                    import threading
                    
                    backend_thread = threading.Thread(target=start_backend, daemon=True)
                    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
                    
                    backend_thread.start()
                    time.sleep(3)  # 等待後端啟動
                    frontend_thread.start()
                    
                    backend_thread.join()
                    frontend_thread.join()
                except Exception as e:
                    print_error(f"啟動失敗: {e}")
            
            elif choice == "5":
                show_guide()
            
            elif choice == "6":
                show_status()
            
            elif choice == "7":
                print_success("再見！")
                break
            
            else:
                print_error("無效選擇，請重試")
            
            input(f"\n{Colors.BOLD}按 Enter 鍵返回菜單...{Colors.ENDC}")
            
        except KeyboardInterrupt:
            print_warning("已取消")
            break
        except Exception as e:
            print_error(f"發生錯誤: {e}")
            input(f"{Colors.BOLD}按 Enter 鍵返回菜單...{Colors.ENDC}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("程序已中斷")
        sys.exit(0)
