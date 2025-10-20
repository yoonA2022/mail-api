"""
IMAP 邮件服务
负责邮件相关的查询和统计操作
"""

from config.database import get_db_connection
from typing import List, Dict, Optional


class ImapEmailService:
    """IMAP 邮件服务类"""
    
    @staticmethod
    def get_email_count(account_id: int, folder: str = 'INBOX') -> Dict:
        """
        获取指定账户的邮件总数
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称，默认 INBOX
            
        Returns:
            包含邮件数量的字典
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                """, (account_id, folder))
                
                result = cursor.fetchone()
                count = result['count'] if result else 0
                
                return {
                    'success': True,
                    'count': count,
                    'account_id': account_id,
                    'folder': folder
                }
        except Exception as e:
            print(f"❌ 获取邮件数量失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    @staticmethod
    def get_latest_emails(account_id: int, limit: int = 10, folder: str = 'INBOX') -> Dict:
        """
        获取指定账户的最新邮件
        
        Args:
            account_id: 账户ID
            limit: 返回数量，默认 10
            folder: 文件夹名称，默认 INBOX
            
        Returns:
            包含邮件列表的字典
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, 
                        has_attachments, attachment_count, attachment_names, 
                        text_preview, is_html, folder, synced_at
                    FROM email_list
                    WHERE account_id = %s AND folder = %s
                    ORDER BY date DESC
                    LIMIT %s
                """, (account_id, folder, limit))
                
                emails = cursor.fetchall()
                
                return {
                    'success': True,
                    'data': emails if emails else [],
                    'count': len(emails) if emails else 0,
                    'account_id': account_id,
                    'folder': folder
                }
        except Exception as e:
            print(f"❌ 获取最新邮件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }
    
    @staticmethod
    def get_unread_count(account_id: int, folder: str = 'INBOX') -> Dict:
        """
        获取未读邮件数量
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称，默认 INBOX
            
        Returns:
            包含未读邮件数量的字典
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                # 查询 flags 中不包含 \Seen 的邮件
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM email_list
                    WHERE account_id = %s 
                    AND folder = %s
                    AND (flags NOT LIKE '%\\\\Seen%' OR flags IS NULL)
                """, (account_id, folder))
                
                result = cursor.fetchone()
                count = result['count'] if result else 0
                
                return {
                    'success': True,
                    'unread_count': count,
                    'account_id': account_id,
                    'folder': folder
                }
        except Exception as e:
            print(f"❌ 获取未读邮件数量失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'unread_count': 0
            }
    
    @staticmethod
    def get_email_by_uid(account_id: int, uid: str, folder: str = 'INBOX') -> Optional[Dict]:
        """
        根据 UID 获取邮件详情
        
        Args:
            account_id: 账户ID
            uid: 邮件UID
            folder: 文件夹名称，默认 INBOX
            
        Returns:
            邮件详情字典，如果不存在返回 None
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, 
                        has_attachments, attachment_count, attachment_names, 
                        text_preview, is_html, folder, synced_at
                    FROM email_list
                    WHERE account_id = %s AND uid = %s AND folder = %s
                """, (account_id, uid, folder))
                
                email = cursor.fetchone()
                return email
        except Exception as e:
            print(f"❌ 获取邮件详情失败: {e}")
            return None
