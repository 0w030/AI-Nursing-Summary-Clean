#!/bin/bash
# Oracle Instant Client 在 Linux 中的安裝和配置指南
# Installation and Configuration Guide for Linux

echo "================================================"
echo "Oracle Instant Client 安裝指南 (Linux)"
echo "================================================"
echo ""

# 步驟 1: 檢查目前狀態
echo "📋 步驟 1: 檢查目前環境"
echo "================================"
echo "操作系統: $(uname -s)"
echo "機器架構: $(uname -m)"
echo "工作目錄: $PWD"
echo ""

# 步驟 2: 建立目錄
INSTALL_DIR="/opt/oracle/instantclient"
echo "📋 步驟 2: 準備安裝目錄"
echo "================================"
echo "安裝位置: $INSTALL_DIR"
echo ""

if [ ! -d "$INSTALL_DIR" ]; then
    echo "建立目錄: $INSTALL_DIR"
    # 無 sudo 權限時的替代方案
    INSTALL_DIR="/workspaces/instantclient"
    echo "使用替代位置: $INSTALL_DIR"
fi

mkdir -p "$INSTALL_DIR"
echo "✓ 目錄已準備"
echo ""

# 步驟 3: 下載指令
echo "📋 步驟 3: 下載 Instant Client (Linux x86-64)"
echo "================================"
echo "需要您手動下載，因為需要 Oracle 帳戶授權"
echo ""
echo "下載步驟:"
echo "1. 訪問: https://www.oracle.com/database/technologies/instant-client/downloads.html"
echo "2. 選擇 'Linux x86-64' 標籤"
echo "3. 選擇版本: Oracle Instant Client 19.30 (或更新)"
echo "4. 下載: instantclient-basic-linux.x64-19.30.0.0.0dbru.zip"
echo ""

# 步驟 4: 配置路徑
echo "📋 步驟 4: 環境變數配置"
echo "================================"
echo "在 Python 中使用以下代碼初始化:"
echo ""
echo "```python"
echo "import oracledb"
echo "try:"
echo "    oracledb.init_oracle_client(lib_dir='$INSTALL_DIR')"
echo "    print('✓ Oracle Instant Client 已初始化')"
echo "except Exception as e:"
echo "    print(f'✗ 初始化失敗: {e}')"
echo "```"
echo ""

# 步驟 5: 快速測試
echo "📋 步驟 5: 測試"
echo "================================"
echo "安裝完成後，運行:"
echo "  python /workspaces/AI-Nursing-Summary-Clean/test_oracle_connection.py"
echo ""

echo "================================================"
echo "詳見: ORACLE_TEST_SUMMARY.md"
echo "================================================"
