"""
IMAP 账户服务
负责管理 IMAP 账户的增删改查操作
"""

from config.database import get_db_connection
from typing import List, Dict, Optional


class ImapAccountService:
    """IMAP 账户服务类"""
    
    @staticmethod
    def get_all_accounts(include_password: bool = False) -> List[Dict]:
        """
        获取所有 IMAP 账户列表
        
        Args:
            include_password: 是否包含密码字段，默认 False
            
        Returns:
            账户列表
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                # 根据是否需要密码选择字段
                if include_password:
                    cursor.execute("""
                        SELECT 
                            id, email, password, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        ORDER BY id ASC
                    """)
                else:
                    cursor.execute("""
                        SELECT 
                            id, email, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        ORDER BY id ASC
                    """)
                
                accounts = cursor.fetchall()
                return accounts if accounts else []
        except Exception as e:
            print(f"❌ 获取账户列表失败: {e}")
            return []
    
    @staticmethod
    def get_account_by_id(account_id: int, include_password: bool = True) -> Optional[Dict]:
        """
        根据 ID 获取账户信息
        
        Args:
            account_id: 账户ID
            include_password: 是否包含密码字段，默认 True
            
        Returns:
            账户信息字典，如果不存在返回 None
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                if include_password:
                    cursor.execute("""
                        SELECT 
                            id, email, password, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE id = %s
                    """, (account_id,))
                else:
                    cursor.execute("""
                        SELECT 
                            id, email, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE id = %s
                    """, (account_id,))
                
                account = cursor.fetchone()
                return account
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            return None
    
    @staticmethod
    def get_account_by_email(email: str, include_password: bool = True) -> Optional[Dict]:
        """
        根据邮箱地址获取账户信息
        
        Args:
            email: 邮箱地址
            include_password: 是否包含密码字段，默认 True
            
        Returns:
            账户信息字典，如果不存在返回 None
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                if include_password:
                    cursor.execute("""
                        SELECT 
                            id, email, password, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE email = %s
                    """, (email,))
                else:
                    cursor.execute("""
                        SELECT 
                            id, email, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE email = %s
                    """, (email,))
                
                account = cursor.fetchone()
                return account
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            return None
    
    @staticmethod
    def get_active_accounts(include_password: bool = False) -> List[Dict]:
        """
        获取所有启用状态的账户
        
        Args:
            include_password: 是否包含密码字段，默认 False
            
        Returns:
            启用的账户列表
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                if include_password:
                    cursor.execute("""
                        SELECT 
                            id, email, password, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE status = 1
                        ORDER BY id ASC
                    """)
                else:
                    cursor.execute("""
                        SELECT 
                            id, email, nickname, platform, 
                            imap_host, imap_port, use_ssl, status, 
                            auto_sync, sync_interval, last_sync_time,
                            folder, max_fetch, remark, created_at, updated_at
                        FROM imap_accounts
                        WHERE status = 1
                        ORDER BY id ASC
                    """)
                
                accounts = cursor.fetchall()
                return accounts if accounts else []
        except Exception as e:
            print(f"❌ 获取启用账户列表失败: {e}")
            return []
    
    @staticmethod
    def update_last_sync_time(account_id: int) -> bool:
        """
        更新账户的最后同步时间
        
        Args:
            account_id: 账户ID
            
        Returns:
            是否更新成功
        """
        try:
            from datetime import datetime
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE imap_accounts
                    SET last_sync_time = %s
                    WHERE id = %s
                """, (datetime.now(), account_id))
                return True
        except Exception as e:
            print(f"❌ 更新同步时间失败: {e}")
            return False
    
    @staticmethod
    def update_account_status(account_id: int, status: int) -> bool:
        """
        更新账户状态
        
        Args:
            account_id: 账户ID
            status: 状态（0:禁用 1:启用）
            
        Returns:
            是否更新成功
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE imap_accounts
                    SET status = %s
                    WHERE id = %s
                """, (status, account_id))
                return True
        except Exception as e:
            print(f"❌ 更新账户状态失败: {e}")
            return False
