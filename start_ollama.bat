@echo off
REM Ollama 快速啟動腳本

echo.
echo ========================================================
echo  Ollama 服務啟動
echo ========================================================
echo.

REM 檢查是否安裝了 Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ Ollama 未安裝或未在 PATH 中
    echo.
    echo 請從以下地址下載並安裝：
    echo https://ollama.ai
    echo.
    echo 安裝完成後，請重啟 PowerShell 並再次運行此腳本
    echo.
    pause
    exit /b 1
)

echo ✅ Ollama 已安裝
echo.

REM 啟動 Ollama 服務
echo 🚀 啟動 Ollama 服務...
echo.
echo 請確保看到以下訊息：
echo "server starting on 127.0.0.1:11434"
echo.
echo 此窗口需保持開啟。若要停止，請按 Ctrl+C
echo.
echo ========================================================
echo.

ollama serve

pause
