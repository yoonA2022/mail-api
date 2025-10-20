"""
异步邮件服务 - 性能优化版
使用异步操作避免阻塞
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from imap_tools import MailBox, AND
from config.database import get_db_connection
from config.performance import IMAP_THREAD_POOL_SIZE
import json
from datetime import datetime
import traceback
import mailparser

# 创建线程池用于执行阻塞的IMAP操作
_thread_pool = ThreadPoolExecutor(max_workers=IMAP_THREAD_POOL_SIZE)

print(f"⚙️ IMAP线程池已创建: 工作线程数={IMAP_THREAD_POOL_SIZE}")


class AsyncMailService:
    """异步邮件服务 - 避免阻塞事件循环"""
    
    @staticmethod
    async def get_account(account_id: int):
        """异步获取账户信息"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            AsyncMailService._get_account_sync,
            account_id
        )
    
    @staticmethod
    def _get_account_sync(account_id: int):
        """同步获取账户信息（在线程池中执行）"""
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, email, password, imap_host, imap_port, use_ssl
                    FROM imap_accounts
                    WHERE id = %s
                """, (account_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            return None
    
    @staticmethod
    async def get_mail_list(account_id: int, folder: str = 'INBOX', limit: int = 100, offset: int = 0):
        """异步获取邮件列表"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            AsyncMailService._get_mail_list_sync,
            account_id, folder, limit, offset
        )
    
    @staticmethod
    def _get_mail_list_sync(account_id: int, folder: str, limit: int, offset: int):
        """同步获取邮件列表（在线程池中执行）"""
        try:
            db = get_db_connection()
            
            # 1. 查询数据库邮件总数
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                """, (account_id, folder))
                total = cursor.fetchone()['total']
            
            # 2. 如果数据库为空，从IMAP同步
            if total == 0:
                print(f"📥 数据库为空，开始同步账户 {account_id} 的邮件...")
                # 注意：这里仍然是同步操作，但在线程池中执行，不会阻塞主事件循环
                from services.imap.mail_service import MailService
                sync_result = MailService.sync_from_imap(account_id, folder)
                
                if not sync_result['success']:
                    return sync_result
                
                total = sync_result['count']
            
            # 3. 查询邮件列表
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, has_attachments, 
                        attachment_count, attachment_names, text_preview, 
                        is_html, folder, synced_at
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                    ORDER BY date DESC
                    LIMIT %s OFFSET %s
                """, (account_id, folder, limit, offset))
                
                emails = cursor.fetchall()
                
                return {
                    'success': True,
                    'data': emails,
                    'count': len(emails),
                    'total': total
                }
        
        except Exception as e:
            print(f"❌ 获取邮件列表失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0,
                'total': 0
            }
    
    @staticmethod
    async def sync_from_imap(account_id: int, folder: str = 'INBOX'):
        """异步同步邮件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            AsyncMailService._sync_from_imap_sync,
            account_id, folder
        )
    
    @staticmethod
    def _sync_from_imap_sync(account_id: int, folder: str):
        """同步邮件（在线程池中执行）"""
        # 调用原有的同步方法
        from services.imap.mail_service import MailService
        return MailService.sync_from_imap(account_id, folder)
    
    @staticmethod
    async def check_new_mail(account_id: int, folder: str = 'INBOX'):
        """异步检测新邮件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            AsyncMailService._check_new_mail_sync,
            account_id, folder
        )
    
    @staticmethod
    def _check_new_mail_sync(account_id: int, folder: str):
        """同步检测新邮件（在线程池中执行）"""
        # 调用原有的同步方法
        from services.imap.mail_service import MailService
        return MailService.check_new_mail(account_id, folder)

