"""管理员登录服务"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.database import get_db_connection
from utils.auth import AuthUtils


class AdminLoginService:
    """管理员登录服务类 - 专门处理管理员登录相关功能"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def login(self, username: str, password: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """
        管理员登录
        
        Args:
            username: 管理员用户名或邮箱
            password: 管理员密码
            ip_address: 登录IP地址
            user_agent: 用户代理
            
        Returns:
            登录结果字典
        """
        try:
            # 1. 查询管理员（支持用户名或邮箱登录）
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, password, nickname, avatar, 
                           real_name, department, position, role, status, 
                           is_verified, is_super_admin, two_factor_enabled,
                           last_login_at, created_at
                    FROM admins 
                    WHERE (username = %s OR email = %s) AND deleted_at IS NULL
                    """,
                    (username, username)
                )
                admin = cursor.fetchone()
            
            if not admin:
                # 记录失败日志
                self._log_login_attempt(None, username, ip_address, user_agent, False, "管理员不存在")
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 2. 检查账户状态
            if admin['status'] == 0:
                self._log_login_attempt(admin['id'], username, ip_address, user_agent, False, "账户已禁用")
                return {
                    "success": False,
                    "message": "账户已被禁用"
                }
            
            if admin['status'] == 2:
                self._log_login_attempt(admin['id'], username, ip_address, user_agent, False, "账户已锁定")
                return {
                    "success": False,
                    "message": "账户已被锁定"
                }
            
            # 3. 验证密码
            if not AuthUtils.verify_password(password, admin['password']):
                self._log_login_attempt(admin['id'], username, ip_address, user_agent, False, "密码错误")
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 4. 生成令牌
            token_data = {
                "admin_id": admin['id'],
                "username": admin['username'],
                "email": admin['email'],
                "role": admin['role'],
                "is_super_admin": admin['is_super_admin']
            }
            access_token = AuthUtils.create_access_token(token_data)
            refresh_token = AuthUtils.generate_refresh_token()
            
            # 5. 创建会话
            session_id = self._create_session(
                admin['id'],
                access_token,
                refresh_token,
                ip_address,
                user_agent
            )
            
            # 6. 更新管理员登录信息
            self._update_admin_login_info(admin['id'], ip_address)
            
            # 7. 记录成功日志
            self._log_login_attempt(admin['id'], username, ip_address, user_agent, True, None)
            
            # 8. 返回管理员信息（不包含密码）
            admin_info = {
                "id": admin['id'],
                "username": admin['username'],
                "email": admin['email'],
                "nickname": admin['nickname'],
                "avatar": admin['avatar'],
                "real_name": admin['real_name'],
                "department": admin['department'],
                "position": admin['position'],
                "role": admin['role'],
                "status": admin['status'],
                "is_verified": admin['is_verified'],
                "is_super_admin": admin['is_super_admin'],
                "two_factor_enabled": admin['two_factor_enabled'],
                "last_login_at": admin['last_login_at'].isoformat() if admin['last_login_at'] else None,
                "created_at": admin['created_at'].isoformat() if admin['created_at'] else None
            }
            
            return {
                "success": True,
                "message": "登录成功",
                "token": access_token,
                "refresh_token": refresh_token,
                "admin": admin_info,
                "requires_two_factor": admin['two_factor_enabled'] == 1
            }
            
        except Exception as e:
            print(f"管理员登录错误: {str(e)}")
            return {
                "success": False,
                "message": f"登录失败: {str(e)}"
            }
    
    def logout(self, token: str) -> bool:
        """
        管理员登出
        
        Args:
            token: 访问令牌
            
        Returns:
            是否成功登出
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM admin_sessions WHERE token = %s",
                    (token,)
                )
                return True
        except Exception as e:
            print(f"管理员登出错误: {str(e)}")
            return False
    
    def _create_session(
        self,
        admin_id: int,
        token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str
    ) -> int:
        """创建管理员会话"""
        expires_at = datetime.now() + timedelta(hours=24)
        
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_sessions 
                (admin_id, token, refresh_token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (admin_id, token, refresh_token, ip_address, user_agent, expires_at)
            )
            return cursor.lastrowid
    
    def _update_admin_login_info(self, admin_id: int, ip_address: str):
        """更新管理员登录信息"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE admins 
                SET last_login_at = NOW(),
                    last_login_ip = %s,
                    login_count = login_count + 1
                WHERE id = %s
                """,
                (ip_address, admin_id)
            )
    
    def _log_login_attempt(
        self,
        admin_id: Optional[int],
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str]
    ):
        """记录管理员登录尝试日志"""
        try:
            with self.db.get_cursor() as cursor:
                # 如果admin_id为None，尝试通过username查找
                if admin_id is None:
                    cursor.execute(
                        "SELECT id FROM admins WHERE username = %s OR email = %s", 
                        (username, username)
                    )
                    result = cursor.fetchone()
                    if result:
                        admin_id = result['id']
                    else:
                        # 管理员不存在，无法记录日志
                        return
                
                cursor.execute(
                    """
                    INSERT INTO admin_login_logs 
                    (admin_id, login_type, ip_address, user_agent, status, failure_reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        admin_id,
                        'password',
                        ip_address,
                        user_agent,
                        1 if success else 0,
                        failure_reason
                    )
                )
        except Exception as e:
            print(f"记录管理员登录日志失败: {str(e)}")
