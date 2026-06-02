"""
權限管理模塊 - 控制使用者存取和操作權限
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Role(Enum):
    """用戶角色枚舉"""
    ADMIN = "admin"              # 管理員 - 完全權限
    MANAGER = "manager"          # 經理 - 可管理連接和映射
    USER = "user"                # 一般使用者 - 摘要生成權限
    VIEWER = "viewer"            # 查看者 - 只讀權限
    GUEST = "guest"              # 訪客 - 基礎查看權限


class Permission(Enum):
    """權限枚舉"""
    # 連接管理
    VIEW_CONNECTIONS = "view_connections"
    CREATE_CONNECTION = "create_connection"
    EDIT_CONNECTION = "edit_connection"
    DELETE_CONNECTION = "delete_connection"
    TEST_CONNECTION = "test_connection"
    SWITCH_CONNECTION = "switch_connection"
    
    # Schema 映射
    VIEW_MAPPINGS = "view_mappings"
    EDIT_MAPPINGS = "edit_mappings"
    AI_SUGGEST_MAPPINGS = "ai_suggest_mappings"
    CONFIRM_MAPPINGS = "confirm_mappings"
    RESET_MAPPINGS = "reset_mappings"
    
    # 模板管理
    VIEW_TEMPLATES = "view_templates"
    CREATE_TEMPLATES = "create_templates"
    EDIT_TEMPLATES = "edit_templates"
    EXPORT_TEMPLATES = "export_templates"
    IMPORT_TEMPLATES = "import_templates"
    
    # 日誌
    VIEW_LOGS = "view_logs"
    EXPORT_LOGS = "export_logs"
    
    # 系統
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"


# 角色權限映射表
ROLE_PERMISSIONS: dict = {
    Role.ADMIN: [
        Permission.VIEW_CONNECTIONS,
        Permission.CREATE_CONNECTION,
        Permission.EDIT_CONNECTION,
        Permission.DELETE_CONNECTION,
        Permission.TEST_CONNECTION,
        Permission.SWITCH_CONNECTION,
        
        Permission.VIEW_MAPPINGS,
        Permission.EDIT_MAPPINGS,
        Permission.AI_SUGGEST_MAPPINGS,
        Permission.CONFIRM_MAPPINGS,
        Permission.RESET_MAPPINGS,
        
        Permission.VIEW_LOGS,
        Permission.EXPORT_LOGS,
        
        Permission.MANAGE_USERS,
        Permission.VIEW_ANALYTICS,
    ],
    
    Role.MANAGER: [
        Permission.VIEW_CONNECTIONS,
        Permission.CREATE_CONNECTION,
        Permission.EDIT_CONNECTION,
        Permission.TEST_CONNECTION,
        Permission.SWITCH_CONNECTION,
        
        Permission.VIEW_MAPPINGS,
        Permission.EDIT_MAPPINGS,
        Permission.AI_SUGGEST_MAPPINGS,
        Permission.CONFIRM_MAPPINGS,
        
        Permission.VIEW_LOGS,
    ],
    
    Role.USER: [
        Permission.VIEW_CONNECTIONS,
        Permission.VIEW_MAPPINGS,
        Permission.VIEW_LOGS,
        Permission.VIEW_TEMPLATES,
        Permission.CREATE_TEMPLATES,
        Permission.EDIT_TEMPLATES,
        Permission.VIEW_TEMPLATES,
        Permission.CREATE_TEMPLATES,
        Permission.EDIT_TEMPLATES,
    ],
    
    Role.VIEWER: [
        Permission.VIEW_CONNECTIONS,
        Permission.TEST_CONNECTION,
        
        Permission.VIEW_MAPPINGS,
        Permission.AI_SUGGEST_MAPPINGS,
        
        Permission.VIEW_LOGS,
    ],
    
    Role.GUEST: [
        Permission.VIEW_CONNECTIONS,
        Permission.VIEW_MAPPINGS,
    ],
}


@dataclass
class User:
    """使用者資訊"""
    username: str
    role: Role
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """檢查用戶是否有特定權限"""
        if not self.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def can_perform_action(self, required_permissions: List[Permission]) -> bool:
        """檢查用戶是否可以執行需要多個權限的操作"""
        return all(self.has_permission(perm) for perm in required_permissions)


class PermissionChecker:
    """權限檢查器"""
    
    @staticmethod
    def require_permission(user: Optional[User], permission: Permission) -> bool:
        """驗證用戶是否有特定權限"""
        if user is None:
            logger.warning("✗ 用戶未認證")
            return False
        
        has_perm = user.has_permission(permission)
        if not has_perm:
            logger.warning(f"✗ 用戶 {user.username} 無權執行: {permission.value}")
        return has_perm
    
    @staticmethod
    def require_role(user: Optional[User], min_role: Role) -> bool:
        """驗證用戶角色級別"""
        if user is None:
            logger.warning("✗ 用戶未認證")
            return False
        
        role_hierarchy = {
            Role.GUEST: 0,
            Role.VIEWER: 1,
            Role.MANAGER: 2,
            Role.ADMIN: 3,
        }
        
        user_level = role_hierarchy.get(user.role, -1)
        min_level = role_hierarchy.get(min_role, 0)
        
        if user_level < min_level:
            logger.warning(f"✗ 用戶 {user.username} 權限不足: {user.role.value} < {min_role.value}")
            return False
        return True
    
    @staticmethod
    def require_all_permissions(
        user: Optional[User],
        permissions: List[Permission]
    ) -> bool:
        """驗證用戶是否有所有指定權限"""
        if user is None:
            logger.warning("✗ 用戶未認證")
            return False
        
        return all(user.has_permission(perm) for perm in permissions)


# 常用權限組合
PERMISSION_GROUPS = {
    "read_only": [Permission.VIEW_CONNECTIONS, Permission.VIEW_MAPPINGS, Permission.VIEW_LOGS],
    "mapping_editor": [
        Permission.VIEW_MAPPINGS,
        Permission.EDIT_MAPPINGS,
        Permission.AI_SUGGEST_MAPPINGS,
        Permission.CONFIRM_MAPPINGS,
    ],
    "connection_manager": [
        Permission.VIEW_CONNECTIONS,
        Permission.CREATE_CONNECTION,
        Permission.EDIT_CONNECTION,
        Permission.TEST_CONNECTION,
        Permission.SWITCH_CONNECTION,
    ],
    "full_admin": list(Permission),
}
