# db/file_security.py
"""
🛡️ 檔案上傳安全檢查模組
- Magic Number 驗證（防止 Polyglot 攻擊）
- 檔案大小限制（防止 DoS 攻擊）
- 路徑消毒與 UUID 重新命名
- 檔名清理（移除特殊字元）
"""

import os
import uuid
import re
import logging
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ==================== 常數定義 ====================
# 檔案大小限制（單位：字節）
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_PDF_SIZE = 10 * 1024 * 1024  # PDF 允許 10 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 圖片 5 MB

# Magic Number 特徵碼（前幾個字節的十六進制）
MAGIC_NUMBERS = {
    'pdf': (b'%PDF', 'application/pdf'),
    'png': (b'\x89PNG\r\n\x1a\n', 'image/png'),
    'jpg': (b'\xff\xd8\xff', 'image/jpeg'),
    'jpeg': (b'\xff\xd8\xff', 'image/jpeg'),
    'docx': (b'PK\x03\x04', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'txt': (None, 'text/plain'),  # TXT 無特定 Magic Number
    'zip': (b'PK\x03\x04', 'application/zip'),
}

# ==================== 1️⃣ Magic Number 驗證 ====================

def verify_magic_number(file_bytes: bytes, expected_type: str) -> Tuple[bool, Optional[str]]:
    """
    驗證檔案的真實 Magic Number（特徵碼）
    
    參數：
        file_bytes: 檔案的字節內容（前 512 字節足夠）
        expected_type: 預期的檔案類型（'pdf', 'png', 'jpg', 'docx', 'txt', 'image'）
    
    返回：
        (是否有效, 錯誤訊息)
        成功時：(True, None)
        失敗時：(False, 錯誤訊息)
    """
    if not file_bytes:
        return False, "檔案為空"
    
    expected_type = expected_type.lower()
    
    # 🛡️ 特殊處理：'image' 類型應嘗試 PNG 或 JPG
    if expected_type == 'image':
        # 先嘗試 PNG
        valid_png, _ = verify_magic_number(file_bytes, 'png')
        if valid_png:
            return True, None
        
        # 再嘗試 JPG
        valid_jpg, jpg_error = verify_magic_number(file_bytes, 'jpg')
        if valid_jpg:
            return True, None
        
        # 都不符則返回錯誤
        return False, f"❌ 圖片格式不符：檔案不是有效的 PNG 或 JPG 格式（可能是偽裝檔案）"
    
    if expected_type not in MAGIC_NUMBERS:
        return False, f"不支援的檔案類型：{expected_type}"
    
    magic_sig, mime_type = MAGIC_NUMBERS[expected_type]
    
    # TXT 文件無特定 Magic Number，嘗試驗證為可讀文本
    if expected_type == 'txt':
        try:
            # 嘗試用 UTF-8 解碼前 512 字節
            file_bytes[:512].decode('utf-8', errors='ignore')
            return True, None
        except Exception:
            return False, "文本檔案無法解碼為可讀格式"
    
    # 其他格式驗證 Magic Number
    if magic_sig and not file_bytes.startswith(magic_sig):
        logger.warning(f"❌ Magic Number 不符：預期 {expected_type}，實際特徵碼 {file_bytes[:8].hex()}")
        return False, f"❌ 檔案格式不符：檔案內容與 {expected_type} 格式不匹配（可能是偽裝檔案）"
    
    return True, None


# ==================== 2️⃣ 檔案大小檢查 ====================

def check_file_size(file_bytes: bytes, file_type: str) -> Tuple[bool, Optional[str]]:
    """
    檢查檔案大小是否超過限制
    
    參數：
        file_bytes: 檔案字節內容
        file_type: 檔案類型（'pdf', 'image', 'docx', 'txt'）
    
    返回：
        (是否通過, 錯誤訊息)
    """
    file_size = len(file_bytes)
    file_type = file_type.lower()
    
    # 根據檔案類型設定不同的限制
    size_limit = MAX_FILE_SIZE_BYTES
    if file_type == 'pdf':
        size_limit = MAX_PDF_SIZE
    elif file_type == 'image':
        size_limit = MAX_IMAGE_SIZE
    
    if file_size > size_limit:
        size_mb = file_size / (1024 * 1024)
        limit_mb = size_limit / (1024 * 1024)
        logger.warning(f"❌ 檔案過大：{size_mb:.2f} MB，限制為 {limit_mb:.2f} MB")
        return False, f"❌ 檔案過大：{size_mb:.2f} MB（限制 {limit_mb:.2f} MB）"
    
    return True, None


# ==================== 3️⃣ 檔案重新命名（UUID） ====================

def generate_safe_filename(original_filename: str, file_type: str) -> str:
    """
    使用 UUID 生成安全的檔案名稱
    
    參數：
        original_filename: 原始檔案名稱（用於取得副檔名）
        file_type: 檔案類型 ('pdf', 'docx', 'txt', 'image' 等)
    
    返回：
        安全的檔案名稱（格式：uuid_timestamp.ext）
    """
    # 從原始檔名中提取副檔名
    ext = Path(original_filename).suffix.lower() or '.bin'
    
    # 生成 UUID（去掉連字符使其更短）
    safe_name = f"{uuid.uuid4().hex}{ext}"
    
    logger.info(f"✓ 檔名重新命名：{original_filename} → {safe_name}")
    return safe_name


# ==================== 4️⃣ 檔名清理（移除特殊字元） ====================

def sanitize_filename(filename: str) -> str:
    """
    清理檔名中的危險字元
    
    參數：
        filename: 原始檔案名稱
    
    返回：
        清理後的檔案名稱
    """
    # 移除路徑穿越字元
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # 允許的字元：英數字、下划線、點、連字符
    # 移除其他特殊字元（;|&$`<>等）
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # 移除連續空格
    filename = re.sub(r'\s+', '_', filename)
    
    # 限制長度（255 字元是 NTFS 限制）
    filename = filename[:255]
    
    # 避免空檔名
    if not filename or filename.startswith('.'):
        filename = 'file_unnamed'
    
    return filename


# ==================== 5️⃣ 綜合安全檢查 ====================

def perform_security_checks(
    file_bytes: bytes,
    original_filename: str,
    file_type: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    執行所有安全檢查並返回安全檔名
    
    參數：
        file_bytes: 檔案字節內容
        original_filename: 原始檔案名稱
        file_type: 檔案類型 ('pdf', 'docx', 'txt', 'image' 等)
    
    返回：
        (通過/失敗, 錯誤訊息, 安全檔名)
        成功時：(True, None, safe_filename)
        失敗時：(False, 錯誤訊息, None)
    """
    # 檢查 1：Magic Number
    valid_magic, magic_error = verify_magic_number(file_bytes, file_type)
    if not valid_magic:
        return False, magic_error, None
    
    # 檢查 2：檔案大小
    valid_size, size_error = check_file_size(file_bytes, file_type)
    if not valid_size:
        return False, size_error, None
    
    # 檢查 3：清理檔名 + UUID 重新命名
    sanitized_name = sanitize_filename(original_filename)
    safe_filename = generate_safe_filename(sanitized_name, file_type)
    
    logger.info(f"✓ 檔案通過所有安全檢查：{safe_filename}")
    return True, None, safe_filename


# ==================== 6️⃣ 檔案保存（可選） ====================

def save_uploaded_file_safely(
    file_bytes: bytes,
    safe_filename: str,
    upload_dir: str = "uploads"
) -> Tuple[bool, Optional[str]]:
    """
    安全地保存上傳的檔案到磁盤
    
    參數：
        file_bytes: 檔案字節內容
        safe_filename: 安全的檔案名稱
        upload_dir: 保存目錄
    
    返回：
        (成功/失敗, 保存路徑或錯誤訊息)
    """
    try:
        # 確保目錄存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 構建完整路徑
        full_path = os.path.join(upload_dir, safe_filename)
        
        # 寫入檔案（無執行權限）
        with open(full_path, 'wb') as f:
            f.write(file_bytes)
        
        # 移除執行權限
        os.chmod(full_path, 0o644)  # rw-r--r--
        
        logger.info(f"✓ 檔案已安全保存：{full_path}")
        return True, full_path
    
    except Exception as e:
        logger.error(f"❌ 檔案保存失敗：{str(e)}")
        return False, f"檔案保存失敗：{str(e)}"
