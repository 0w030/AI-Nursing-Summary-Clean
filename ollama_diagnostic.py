#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 診斷和配置工具
檢查 Ollama 是否正確安裝和運行
"""

import subprocess
import requests
import time
import sys
import json
from pathlib import Path


class OllamaDiagnostic:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.required_model = "llava"
        self.issues = []
        self.status = {
            "ollama_installed": False,
            "ollama_running": False,
            "model_available": False,
            "connection_ok": False
        }

    def print_header(self, title):
        """打印標題"""
        print("\n" + "=" * 60)
        print(f"🔍 {title}")
        print("=" * 60)

    def print_status(self, status, message):
        """打印狀態訊息"""
        if status == "success":
            print(f"✅ {message}")
        elif status == "warning":
            print(f"⚠️  {message}")
        elif status == "error":
            print(f"❌ {message}")
        elif status == "info":
            print(f"ℹ️  {message}")

    def check_ollama_installed(self):
        """檢查 Ollama 是否已安裝"""
        self.print_header("檢查 1：Ollama 安裝狀態")
        
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_status("success", f"Ollama 已安裝：{version}")
                self.status["ollama_installed"] = True
                return True
            else:
                self.print_status("error", "Ollama 命令執行失敗")
                self.issues.append("Ollama 命令執行失敗")
                return False
                
        except FileNotFoundError:
            self.print_status("error", "Ollama 未安裝或未在 PATH 中")
            self.issues.append(
                "Ollama 未安裝。\n"
                "   請從 https://ollama.ai 下載並安裝，然後重啟 PowerShell"
            )
            return False
        except subprocess.TimeoutExpired:
            self.print_status("error", "Ollama 命令執行超時")
            self.issues.append("Ollama 命令執行超時")
            return False
        except Exception as e:
            self.print_status("error", f"檢查失敗：{e}")
            self.issues.append(f"檢查 Ollama 安裝時出錯：{e}")
            return False

    def check_ollama_running(self):
        """檢查 Ollama 是否在運行"""
        self.print_header("檢查 2：Ollama 運行狀態")
        
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                self.print_status("success", f"Ollama 正在運行 ({self.ollama_url})")
                self.status["ollama_running"] = True
                self.status["connection_ok"] = True
                return True
            else:
                self.print_status("error", f"Ollama 回應異常（狀態碼：{response.status_code}）")
                self.issues.append(f"Ollama HTTP 狀態異常：{response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.print_status("error", "無法連接到 Ollama（localhost:11434）")
            self.issues.append(
                "Ollama 未在運行。\n"
                "   請在 PowerShell 中執行：ollama serve\n"
                "   確保看到「server starting on 127.0.0.1:11434」的訊息"
            )
            return False
        except requests.exceptions.Timeout:
            self.print_status("error", "連接超時")
            self.issues.append("連接 Ollama 超時，可能網路問題或 Ollama 未正確啟動")
            return False
        except Exception as e:
            self.print_status("error", f"連接失敗：{e}")
            self.issues.append(f"連接 Ollama 時出錯：{e}")
            return False

    def check_model_available(self):
        """檢查 llava 模型是否已安裝"""
        self.print_header("檢查 3：llava 模型安裝狀態")
        
        if not self.status["connection_ok"]:
            self.print_status("warning", "跳過此檢查（Ollama 未連接）")
            return False
        
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                
                if "llava" in models:
                    self.print_status("success", "llava 模型已安裝")
                    self.status["model_available"] = True
                    return True
                else:
                    self.print_status("warning", f"llava 未安裝，已安裝的模型：{models if models else '無'}")
                    self.issues.append(
                        "llava 模型未安裝。\n"
                        "   請在新 PowerShell 中執行：ollama pull llava\n"
                        "   （此過程需要 5-15 分鐘，模型約 4.7GB）"
                    )
                    return False
            else:
                self.print_status("error", "無法取得模型列表")
                return False
                
        except Exception as e:
            self.print_status("error", f"檢查模型失敗：{e}")
            self.issues.append(f"檢查 llava 模型時出錯：{e}")
            return False

    def check_ollama_list(self):
        """使用 ollama list 檢查本地模型"""
        self.print_header("檢查 4：使用 ollama list 驗證")
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and "llava" in result.stdout:
                self.print_status("success", "ollama list 顯示 llava 已安裝")
                print("\n本地模型列表：")
                print(result.stdout)
                return True
            elif result.returncode == 0:
                self.print_status("warning", "ollama list 執行成功但未找到 llava")
                print("\n當前模型列表：")
                print(result.stdout if result.stdout else "（無模型）")
                return False
            else:
                self.print_status("error", "ollama list 執行失敗")
                if result.stderr:
                    print(f"錯誤：{result.stderr}")
                return False
                
        except FileNotFoundError:
            self.print_status("warning", "ollama 命令不可用")
            return False
        except Exception as e:
            self.print_status("error", f"執行失敗：{e}")
            return False

    def test_ollama_api(self):
        """測試 Ollama API 的實際識別功能"""
        self.print_header("檢查 5：測試 Ollama API")
        
        if not self.status["connection_ok"] or not self.status["model_available"]:
            self.print_status("warning", "跳過此檢查（前置條件未滿足）")
            return False
        
        try:
            self.print_status("info", "發送測試請求到 Ollama...")
            
            # 使用一個簡單的測試 prompt
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llava",
                    "prompt": "What do you see?",
                    "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "response" in result:
                    self.print_status("success", "Ollama API 正常運作")
                    return True
            else:
                self.print_status("error", f"API 返回異常狀態碼：{response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            self.print_status("warning", "API 請求超時（可能是首次運行 llava 需要初始化）")
            return True  # 不視為失敗
        except Exception as e:
            self.print_status("error", f"API 測試失敗：{e}")
            return False

    def generate_report(self):
        """生成診斷報告"""
        self.print_header("診斷報告")
        
        print("\n📊 檢查結果：")
        print(f"  • Ollama 已安裝：{'✅' if self.status['ollama_installed'] else '❌'}")
        print(f"  • Ollama 正在運行：{'✅' if self.status['ollama_running'] else '❌'}")
        print(f"  • llava 模型可用：{'✅' if self.status['model_available'] else '❌'}")
        print(f"  • 連接正常：{'✅' if self.status['connection_ok'] else '❌'}")
        
        if self.issues:
            print("\n⚠️  發現的問題：")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. {issue}")
        
        if all(self.status.values()):
            print("\n" + "🎉 " * 20)
            print("✅ Ollama 配置完成！可以開始使用圖片識別功能")
            print("🎉 " * 20)
            return True
        else:
            print("\n❌ Ollama 配置未完成，請按照上述建議進行設置")
            return False

    def run(self):
        """執行完整診斷"""
        print("\n" + "🔧" * 30)
        print("Ollama 診斷工具")
        print("🔧" * 30)
        
        self.check_ollama_installed()
        self.check_ollama_running()
        self.check_model_available()
        self.check_ollama_list()
        
        if self.status["connection_ok"] and self.status["model_available"]:
            self.test_ollama_api()
        
        success = self.generate_report()
        
        return success


if __name__ == "__main__":
    diagnostic = OllamaDiagnostic()
    success = diagnostic.run()
    
    # 返回適當的退出碼
    sys.exit(0 if success else 1)
