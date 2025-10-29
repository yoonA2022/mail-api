"""注册服务"""
from datetime import datetime
from typing import Dict, Any
from config.database import get_db_connection
from utils.auth import AuthUtils


class RegisterService:
    """注册服务类"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def register(
        self,
        username: str,
        email: str,
        password: str,
        nickname: str = None,
        ip_address: str = "unknown"
    ) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 用户邮箱
            password: 用户密码
            nickname: 昵称（可选）
            ip_address: 注册IP地址
            
        Returns:
            注册结果字典
        """
        try:
            # 1. 检查用户名是否已存在
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND deleted_at IS NULL",
                    (username,)
                )
                existing_username = cursor.fetchone()
                
                if existing_username:
                    return {
                        "success": False,
                        "message": "用户名已被使用"
                    }
                
                # 2. 检查邮箱是否已存在
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND deleted_at IS NULL",
                    (email,)
                )
                existing_email = cursor.fetchone()
                
                if existing_email:
                    return {
                        "success": False,
                        "message": "邮箱已被注册"
                    }
                
                # 3. 加密密码
                hashed_password = AuthUtils.hash_password(password)
                
                # 4. 如果没有提供昵称，使用用户名作为昵称
                if not nickname:
                    nickname = username
                
                # 5. 插入新用户
                cursor.execute(
                    """
                    INSERT INTO users 
                    (username, email, password, nickname, role, status, is_verified, last_login_ip)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (username, email, hashed_password, nickname, 'user', 1, 0, ip_address)
                )
                
                user_id = cursor.lastrowid
                
                # 6. 查询新创建的用户信息
                cursor.execute(
                    """
                    SELECT id, username, email, nickname, avatar, 
                           role, status, is_verified, created_at
                    FROM users 
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()
                
                if not user:
                    return {
                        "success": False,
                        "message": "注册失败，无法获取用户信息"
                    }
                
                # 7. 返回用户信息
                user_info = {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "nickname": user['nickname'],
                    "avatar": user['avatar'],
                    "role": user['role'],
                    "status": user['status'],
                    "is_verified": user['is_verified'],
                    "last_login_at": None,
                    "created_at": user['created_at'].isoformat() if user['created_at'] else None
                }
                
                return {
                    "success": True,
                    "message": "注册成功",
                    "user": user_info
                }
                
        except Exception as e:
            print(f"注册错误: {str(e)}")
            return {
                "success": False,
                "message": f"注册失败: {str(e)}"
            }
    
    def check_username_available(self, username: str) -> bool:
        """检查用户名是否可用"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND deleted_at IS NULL",
                    (username,)
                )
                result = cursor.fetchone()
                return result is None
        except Exception as e:
            print(f"检查用户名错误: {str(e)}")
            return False
    
    def check_email_available(self, email: str) -> bool:
        """检查邮箱是否可用"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND deleted_at IS NULL",
                    (email,)
                )
                result = cursor.fetchone()
                return result is None
        except Exception as e:
            print(f"检查邮箱错误: {str(e)}")
            return False
