"""验证服务"""
from typing import Optional, Dict, Any
from config.database import get_db_connection
from utils.auth import AuthUtils


class VerificationService:
    """验证服务类 - 专门处理令牌验证相关功能"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证令牌
        
        Args:
            token: 访问令牌
            
        Returns:
            令牌payload或None
        """
        # 1. 解码JWT令牌
        payload = AuthUtils.decode_token(token)
        if not payload:
            return None
        
        # 2. 检查会话是否存在且未过期
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM user_sessions 
                WHERE token = %s AND expires_at > NOW()
                """,
                (token,)
            )
            session = cursor.fetchone()
            
            if not session:
                return None
            
            return payload
    
    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        通过令牌获取用户信息
        
        Args:
            token: 访问令牌
            
        Returns:
            用户信息或None
        """
        # 1. 验证令牌
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # 2. 获取用户信息
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, nickname, avatar, 
                       role, status, is_verified, last_login_at, created_at
                FROM users 
                WHERE id = %s AND deleted_at IS NULL
                """,
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None
            
            return {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "nickname": user['nickname'],
                "avatar": user['avatar'],
                "role": user['role'],
                "status": user['status'],
                "is_verified": user['is_verified'],
                "last_login_at": user['last_login_at'].isoformat() if user['last_login_at'] else None,
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            }
    
    def check_session_exists(self, token: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            token: 访问令牌
            
        Returns:
            会话是否存在
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM user_sessions 
                    WHERE token = %s AND expires_at > NOW()
                    """,
                    (token,)
                )
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            print(f"检查会话错误: {str(e)}")
            return False
    
    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新会话（使用refresh_token获取新的access_token）
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的令牌信息或None
        """
        try:
            with self.db.get_cursor() as cursor:
                # 查找refresh_token对应的会话
                cursor.execute(
                    """
                    SELECT user_id FROM user_sessions 
                    WHERE refresh_token = %s AND expires_at > NOW()
                    """,
                    (refresh_token,)
                )
                session = cursor.fetchone()
                
                if not session:
                    return None
                
                user_id = session['user_id']
                
                # 获取用户信息
                cursor.execute(
                    """
                    SELECT id, email, role FROM users 
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                # 生成新的access_token
                token_data = {
                    "user_id": user['id'],
                    "email": user['email'],
                    "role": user['role']
                }
                new_access_token = AuthUtils.create_access_token(token_data)
                
                # 更新会话中的token
                cursor.execute(
                    """
                    UPDATE user_sessions 
                    SET token = %s 
                    WHERE refresh_token = %s
                    """,
                    (new_access_token, refresh_token)
                )
                
                return {
                    "success": True,
                    "token": new_access_token,
                    "refresh_token": refresh_token
                }
                
        except Exception as e:
            print(f"刷新会话错误: {str(e)}")
            return None
