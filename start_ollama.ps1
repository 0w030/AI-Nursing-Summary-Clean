# Ollama 快速启动脚本 (PowerShell 版本)

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🚀 Ollama 服務啟動" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 檢查是否安裝了 Ollama
try {
    $version = ollama --version 2>$null
    Write-Host "✅ Ollama 已安裝：$version" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama 未安裝或未在 PATH 中" -ForegroundColor Red
    Write-Host ""
    Write-Host "請從以下地址下載並安裝：" -ForegroundColor Yellow
    Write-Host "https://ollama.ai" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "安裝完成後，請重啟 PowerShell 並再次運行此腳本" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按 Enter 鍵退出"
    exit 1
}

Write-Host ""
Write-Host "🟢 Ollama 服務啟動中..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  請確保看到以下訊息：" -ForegroundColor Yellow
Write-Host "📍 server starting on 127.0.0.1:11434" -ForegroundColor Yellow
Write-Host ""
Write-Host "此窗口需保持開啟。若要停止，請按 Ctrl+C" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

ollama serve
