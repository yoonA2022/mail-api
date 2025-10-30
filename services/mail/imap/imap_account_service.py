"""IMAP账户服务层"""
from config.database import get_db_connection
from models.mail.imap.imap_account import ImapAccountCreate, ImapAccountUpdate, ImapAccountResponse
from typing import List, Optional
from datetime import datetime


class ImapAccountService:
    """IMAP账户服务类"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def get_all_accounts(self, user_id: Optional[int] = None) -> List[ImapAccountResponse]:
        """
        获取所有IMAP账户
        
        Args:
            user_id: 用户ID，如果提供则只返回该用户的账户
            
        Returns:
            IMAP账户列表
        """
        with self.db.get_cursor() as cursor:
            if user_id:
                sql = """
                    SELECT id, email, nickname, user_id, platform, imap_host, imap_port,
                           use_ssl, status, auto_sync, sync_interval, last_sync_time,
                           folder, max_fetch, remark, created_at, updated_at
                    FROM imap_accounts
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(sql, (user_id,))
            else:
                sql = """
                    SELECT id, email, nickname, user_id, platform, imap_host, imap_port,
                           use_ssl, status, auto_sync, sync_interval, last_sync_time,
                           folder, max_fetch, remark, created_at, updated_at
                    FROM imap_accounts
                    ORDER BY created_at DESC
                """
                cursor.execute(sql)
            
            rows = cursor.fetchall()
            
            # 转换为响应模型
            accounts = []
            for row in rows:
                # 转换布尔值
                row['use_ssl'] = bool(row['use_ssl'])
                row['status'] = bool(row['status'])
                row['auto_sync'] = bool(row['auto_sync'])
                
                accounts.append(ImapAccountResponse(**row))
            
            return accounts
    
    def get_account_by_id(self, account_id: int) -> Optional[ImapAccountResponse]:
        """
        根据ID获取IMAP账户
        
        Args:
            account_id: 账户ID
            
        Returns:
            IMAP账户信息，如果不存在返回None
        """
        with self.db.get_cursor() as cursor:
            sql = """
                SELECT id, email, nickname, user_id, platform, imap_host, imap_port,
                       use_ssl, status, auto_sync, sync_interval, last_sync_time,
                       folder, max_fetch, remark, created_at, updated_at
                FROM imap_accounts
                WHERE id = %s
            """
            cursor.execute(sql, (account_id,))
            row = cursor.fetchone()
            
            if row:
                # 转换布尔值
                row['use_ssl'] = bool(row['use_ssl'])
                row['status'] = bool(row['status'])
                row['auto_sync'] = bool(row['auto_sync'])
                
                return ImapAccountResponse(**row)
            
            return None
    
    def create_account(self, account_data: ImapAccountCreate) -> ImapAccountResponse:
        """
        创建IMAP账户
        
        Args:
            account_data: 账户数据
            
        Returns:
            创建的账户信息
        """
        with self.db.get_cursor() as cursor:
            sql = """
                INSERT INTO imap_accounts 
                (email, password, nickname, user_id, platform, imap_host, imap_port,
                 use_ssl, status, auto_sync, sync_interval, folder, max_fetch, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                account_data.email,
                account_data.password,
                account_data.nickname,
                account_data.user_id,
                account_data.platform,
                account_data.imap_host,
                account_data.imap_port,
                account_data.use_ssl,
                account_data.status,
                account_data.auto_sync,
                account_data.sync_interval,
                account_data.folder,
                account_data.max_fetch,
                account_data.remark
            ))
            
            # 获取插入的ID
            account_id = cursor.lastrowid
            
            # 返回创建的账户
            return self.get_account_by_id(account_id)
    
    def update_account(self, account_id: int, account_data: ImapAccountUpdate) -> Optional[ImapAccountResponse]:
        """
        更新IMAP账户
        
        Args:
            account_id: 账户ID
            account_data: 更新的账户数据
            
        Returns:
            更新后的账户信息，如果账户不存在返回None
        """
        # 检查账户是否存在
        existing_account = self.get_account_by_id(account_id)
        if not existing_account:
            return None
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        if account_data.password is not None:
            update_fields.append("password = %s")
            update_values.append(account_data.password)
        
        if account_data.nickname is not None:
            update_fields.append("nickname = %s")
            update_values.append(account_data.nickname)
        
        if account_data.imap_host is not None:
            update_fields.append("imap_host = %s")
            update_values.append(account_data.imap_host)
        
        if account_data.imap_port is not None:
            update_fields.append("imap_port = %s")
            update_values.append(account_data.imap_port)
        
        if account_data.use_ssl is not None:
            update_fields.append("use_ssl = %s")
            update_values.append(account_data.use_ssl)
        
        if account_data.status is not None:
            update_fields.append("status = %s")
            update_values.append(account_data.status)
        
        if account_data.auto_sync is not None:
            update_fields.append("auto_sync = %s")
            update_values.append(account_data.auto_sync)
        
        if account_data.sync_interval is not None:
            update_fields.append("sync_interval = %s")
            update_values.append(account_data.sync_interval)
        
        if account_data.folder is not None:
            update_fields.append("folder = %s")
            update_values.append(account_data.folder)
        
        if account_data.max_fetch is not None:
            update_fields.append("max_fetch = %s")
            update_values.append(account_data.max_fetch)
        
        if account_data.remark is not None:
            update_fields.append("remark = %s")
            update_values.append(account_data.remark)
        
        # 如果没有要更新的字段，直接返回原账户
        if not update_fields:
            return existing_account
        
        # 执行更新
        with self.db.get_cursor() as cursor:
            sql = f"UPDATE imap_accounts SET {', '.join(update_fields)} WHERE id = %s"
            update_values.append(account_id)
            cursor.execute(sql, tuple(update_values))
        
        # 返回更新后的账户
        return self.get_account_by_id(account_id)
    
    def delete_account(self, account_id: int) -> bool:
        """
        删除IMAP账户
        
        Args:
            account_id: 账户ID
            
        Returns:
            是否删除成功
        """
        with self.db.get_cursor() as cursor:
            sql = "DELETE FROM imap_accounts WHERE id = %s"
            cursor.execute(sql, (account_id,))
            return cursor.rowcount > 0
    
    def update_last_sync_time(self, account_id: int) -> bool:
        """
        更新账户的最后同步时间
        
        Args:
            account_id: 账户ID
            
        Returns:
            是否更新成功
        """
        with self.db.get_cursor() as cursor:
            sql = "UPDATE imap_accounts SET last_sync_time = %s WHERE id = %s"
            cursor.execute(sql, (datetime.now(), account_id))
            return cursor.rowcount > 0
