# Ollama 本地圖片識別設置指南

## 📋 概述

本項目集成了 **Ollama + llava** 本地圖片識別和 **Groq API** 備選方案。優先使用本地 Ollama（免費、無 API 費用），若失敗自動降級到 Groq。

---

## 🚀 快速開始（3 步）

### 1️⃣ 檢查和診斷

```powershell
# 進入項目目錄
cd C:\AI-Nursing-Summary-Clean\AI-Nursing-Summary-Clean

# 運行診斷工具
python ollama_diagnostic.py
```

**預期結果：**
- ✅ Ollama 已安裝
- ✅ Ollama 正在運行
- ✅ llava 模型可用
- ✅ 連接正常

如果任何項目顯示 ❌，請參考下方「問題排查」部分。

---

### 2️⃣ 啟動 Ollama 服務

選擇以下任意一種方式：

**方式 A：直接雙擊啟動（推薦）**
1. 在項目目錄中找到 `start_ollama.bat`
2. 雙擊執行
3. 稍等片刻，看到 `server starting on 127.0.0.1:11434` 訊息即可

**方式 B：PowerShell 啟動**
```powershell
# 進入項目目錄
cd C:\AI-Nursing-Summary-Clean\AI-Nursing-Summary-Clean

# 允許執行腳本（首次需要）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# 運行啟動腳本
.\start_ollama.ps1
```

**方式 C：手動啟動（調試用）**
```powershell
ollama serve
```

⚠️ **重要**：保持此終端窗口開啟（不要關閉）

---

### 3️⃣ 重新加載應用

在另一個 PowerShell 窗口中重啟 Streamlit：

```powershell
cd C:\AI-Nursing-Summary-Clean\AI-Nursing-Summary-Clean
streamlit run app.py
```

現在上傳醫療圖片並點擊「識別圖片文本」，應該會看到：
```
✅ 圖片識別成功！（🟢 Ollama）
```

---

## 🔧 完整安裝步驟（首次設置）

### 步驟 1：檢查 Ollama 是否已安裝

```powershell
ollama --version
```

**結果：**
- 顯示版本號 → 已安裝，跳到步驟 2
- "不是內部或外部命令" → 未安裝，進行步驟 1.1

### 步驟 1.1：安裝 Ollama（如未安裝）

1. 訪問 https://ollama.ai
2. 下載 **Ollama for Windows**
3. 執行安裝程式，完整安裝（默認路徑）
4. **重啟 PowerShell**
5. 驗證：`ollama --version`

---

### 步驟 2：啟動 Ollama 並安裝 llava

**終端 #1**：啟動 Ollama 服務
```powershell
ollama serve
```

預期看到：
```
2026/05/06 10:30:00 routes.go:936: INFO server starting on 127.0.0.1:11434
```

**終端 #2**：安裝 llava 模型（新開 PowerShell）
```powershell
ollama pull llava
```

⏳ 首次下載需要 5-15 分鐘（模型約 4.7GB），請耐心等待。

預期看到：
```
pulling manifest
pulling 8934d386fb37... 100%
...
success
```

---

### 步驟 3：驗證安裝

**終端 #3**：驗證連接（再新開一個 PowerShell）

```powershell
# 檢查本地模型
ollama list

# 檢查 API 連接
Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

預期看到 `llava` 在模型列表中。

---

### 步驟 4：運行診斷確認

```powershell
python ollama_diagnostic.py
```

所有項目都應顯示 ✅

---

## ❓ 問題排查

### 問題 1：「ollama 不是內部或外部命令」

**原因**：Ollama 未安裝或 PATH 設置不正確

**解決方案**：
1. 檢查 Ollama 是否已安裝：
   - Windows: 檢查 `C:\Users\{YourUsername}\AppData\Local\Programs\Ollama`
2. 若未安裝，從 https://ollama.ai 下載並安裝
3. 安裝完後重啟 PowerShell
4. 驗證：`ollama --version`

---

### 問題 2：「Ollama 連接失敗」或「無法連接到 Ollama」

**原因**：Ollama 服務未啟動

**解決方案**：
1. 打開新的 PowerShell 窗口
2. 執行 `ollama serve`
3. 確保看到 `server starting on 127.0.0.1:11434` 訊息
4. 保持此窗口開啟
5. 重新加載 Streamlit 應用

---

### 問題 3：「llava 未安裝」

**原因**：llava 模型未下載

**解決方案**：
1. 確保 Ollama 正在運行（看到 `server starting` 訊息）
2. 打開新 PowerShell，執行：`ollama pull llava`
3. 等待下載完成（可能需要 5-15 分鐘）
4. 驗證：`ollama list` 應顯示 `llava`

---

### 問題 4：下載 llava 時卡住或超時

**原因**：網路問題或模型下載中斷

**解決方案**：
1. 檢查網路連接
2. 若中斷，重新執行 `ollama pull llava`
3. Ollama 會自動恢復下載（不需要重新開始）
4. 耐心等待（首次下載可能需要 15-30 分鐘）

---

### 問題 5：內存不足或系統變慢

**原因**：llava 模型較大（約 4.7GB），需要 8GB+ RAM

**解決方案**：
1. 關閉其他應用程式
2. 給 Ollama 更多系統資源
3. 或使用 Groq API 備選方案（自動降級）

---

### 問題 6：「Groq 識別失敗」

**原因**：GROQ_API_KEY 環境變數未設置或無效

**解決方案**：
1. 檢查 `.env` 文件是否包含有效的 `GROQ_API_KEY`
2. 從 https://console.groq.com 取得 API 密鑰
3. 設置環境變數或在 `.env` 中配置
4. 重新加載應用

---

## 📊 使用流程

```
上傳醫療圖片（JPG/PNG）
       ↓
點擊「識別圖片文本」
       ↓
【優先】嘗試本地 Ollama (localhost:11434)
       ↓
  ✅ 成功 → 顯示「🟢 Ollama」
  ❌ 失敗 → 自動降級
           ↓
       【備選】Groq API
           ↓
        ✅ 成功 → 顯示「🔵 Groq API」
        ❌ 失敗 → 顯示錯誤
```

---

## 🎯 性能參考

| 後端 | 速度 | 成本 | 質量 | 優先級 |
|------|------|------|------|--------|
| Ollama (llava) | 🟡 5-30秒 | 💚 免費 | ⭐⭐⭐⭐ | 🥇 |
| Groq API | 🟢 2-5秒 | 💛 低成本 | ⭐⭐⭐ | 🥈 |

---

## 📝 診斷命令速查表

```powershell
# 檢查 Ollama 版本
ollama --version

# 列出本地模型
ollama list

# 檢查 Ollama 服務
Test-NetConnection -ComputerName localhost -Port 11434

# 運行診斷
python ollama_diagnostic.py

# 啟動 Ollama
ollama serve

# 安裝 llava
ollama pull llava

# 移除模型（釋放空間）
ollama rm llava
```

---

## 💡 Tips

- 首次運行 llava 時會花更多時間（模型初始化）
- Ollama 不支援多個客戶端同時使用同一個模型
- 若要節省空間，可只安裝 `llava`，移除其他模型
- Ollama 會自動緩存已下載的模型

---

## 📞 需要幫助？

1. 運行診斷工具：`python ollama_diagnostic.py`
2. 檢查本文件的「問題排查」部分
3. 查看 Streamlit 終端的錯誤訊息
4. 確保網路連接正常

---

**祝你使用愉快！** ✨
