"""登录服务"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.database import get_db_connection
from utils.auth import AuthUtils


class LoginService:
    """登录服务类 - 专门处理用户登录相关功能"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def login(self, email: str, password: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            email: 用户邮箱
            password: 用户密码
            ip_address: 登录IP地址
            user_agent: 用户代理
            
        Returns:
            登录结果字典
        """
        try:
            # 1. 查询用户
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, password, nickname, avatar, 
                           role, plan, plan_expire_at, status, is_verified, 
                           last_login_at, created_at
                    FROM users 
                    WHERE email = %s AND deleted_at IS NULL
                    """,
                    (email,)
                )
                user = cursor.fetchone()
            
            if not user:
                # 记录失败日志
                self._log_login_attempt(None, email, ip_address, user_agent, False, "用户不存在")
                return {
                    "success": False,
                    "message": "邮箱或密码错误"
                }
            
            # 2. 检查账户状态
            if user['status'] == 0:
                self._log_login_attempt(user['id'], email, ip_address, user_agent, False, "账户已禁用")
                return {
                    "success": False,
                    "message": "账户已被禁用"
                }
            
            if user['status'] == 2:
                self._log_login_attempt(user['id'], email, ip_address, user_agent, False, "账户已锁定")
                return {
                    "success": False,
                    "message": "账户已被锁定"
                }
            
            # 3. 验证密码
            if not AuthUtils.verify_password(password, user['password']):
                self._log_login_attempt(user['id'], email, ip_address, user_agent, False, "密码错误")
                return {
                    "success": False,
                    "message": "邮箱或密码错误"
                }
            
            # 4. 生成令牌
            token_data = {
                "user_id": user['id'],
                "email": user['email'],
                "role": user['role']
            }
            access_token = AuthUtils.create_access_token(token_data)
            refresh_token = AuthUtils.generate_refresh_token()
            
            # 5. 创建会话
            session_id = self._create_session(
                user['id'],
                access_token,
                refresh_token,
                ip_address,
                user_agent
            )
            
            # 6. 更新用户登录信息
            self._update_user_login_info(user['id'], ip_address)
            
            # 7. 记录成功日志
            self._log_login_attempt(user['id'], email, ip_address, user_agent, True, None)
            
            # 8. 返回用户信息（不包含密码）
            user_info = {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "nickname": user['nickname'],
                "avatar": user['avatar'],
                "role": user['role'],
                "plan": user.get('plan', 'free'),
                "plan_expire_at": user['plan_expire_at'].isoformat() if user.get('plan_expire_at') else None,
                "status": user['status'],
                "is_verified": user['is_verified'],
                "last_login_at": user['last_login_at'].isoformat() if user['last_login_at'] else None,
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            }
            
            return {
                "success": True,
                "message": "登录成功",
                "token": access_token,
                "refresh_token": refresh_token,
                "user": user_info
            }
            
        except Exception as e:
            print(f"登录错误: {str(e)}")
            return {
                "success": False,
                "message": f"登录失败: {str(e)}"
            }
    
    def logout(self, token: str) -> bool:
        """
        用户登出
        
        Args:
            token: 访问令牌
            
        Returns:
            是否成功登出
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM user_sessions WHERE token = %s",
                    (token,)
                )
                return True
        except Exception as e:
            print(f"登出错误: {str(e)}")
            return False
    
    def _create_session(
        self,
        user_id: int,
        token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str
    ) -> int:
        """创建用户会话"""
        expires_at = datetime.now() + timedelta(hours=24)
        
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_sessions 
                (user_id, token, refresh_token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, token, refresh_token, ip_address, user_agent, expires_at)
            )
            return cursor.lastrowid
    
    def _update_user_login_info(self, user_id: int, ip_address: str):
        """更新用户登录信息"""
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users 
                SET last_login_at = NOW(),
                    last_login_ip = %s,
                    login_count = login_count + 1
                WHERE id = %s
                """,
                (ip_address, user_id)
            )
    
    def _log_login_attempt(
        self,
        user_id: Optional[int],
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: Optional[str]
    ):
        """记录登录尝试日志"""
        try:
            with self.db.get_cursor() as cursor:
                # 如果user_id为None，尝试通过email查找
                if user_id is None:
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    result = cursor.fetchone()
                    if result:
                        user_id = result['id']
                    else:
                        # 用户不存在，无法记录日志
                        return
                
                cursor.execute(
                    """
                    INSERT INTO user_login_logs 
                    (user_id, login_type, ip_address, user_agent, status, failure_reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        'password',
                        ip_address,
                        user_agent,
                        1 if success else 0,
                        failure_reason
                    )
                )
        except Exception as e:
            print(f"记录登录日志失败: {str(e)}")
