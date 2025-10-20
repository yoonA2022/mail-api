"""
邮件搜索服务
提供邮件的高级搜索功能
"""

from config.database import get_db_connection
from typing import Optional, List, Dict, Any


class EmailSearchService:
    """邮件搜索服务 - 支持多字段搜索"""
    
    @staticmethod
    def search_emails(
        account_id: int,
        keyword: str,
        folder: str = 'INBOX',
        search_fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索邮件
        
        Args:
            account_id: 账户ID
            keyword: 搜索关键词
            folder: 文件夹名称
            search_fields: 搜索字段列表，默认['subject', 'from_name', 'from_email', 'text_preview']
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            {
                'success': True,
                'data': [...],
                'count': 10,
                'total': 25,
                'keyword': '搜索词'
            }
        """
        try:
            # 默认搜索字段
            if search_fields is None:
                search_fields = ['subject', 'from_name', 'from_email', 'text_preview']
            
            # 构建搜索条件
            search_conditions = []
            search_params = []
            
            for field in search_fields:
                search_conditions.append(f"{field} LIKE %s")
                search_params.append(f"%{keyword}%")
            
            # 基础查询条件
            base_conditions = "account_id = %s AND folder = %s"
            base_params = [account_id, folder]
            
            # 组合搜索条件
            where_clause = f"{base_conditions} AND ({' OR '.join(search_conditions)})"
            all_params = base_params + search_params
            
            db = get_db_connection()
            
            # 1. 查询总数
            with db.get_cursor() as cursor:
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM email_list
                    WHERE {where_clause}
                """
                cursor.execute(count_sql, all_params)
                total = cursor.fetchone()['total']
            
            # 2. 查询邮件列表
            with db.get_cursor() as cursor:
                # 分页查询参数
                query_params = all_params + [limit, offset]
                
                search_sql = f"""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, 
                        has_attachments, attachment_count, attachment_names, 
                        text_preview, is_html, folder, synced_at
                    FROM email_list
                    WHERE {where_clause}
                    ORDER BY date DESC
                    LIMIT %s OFFSET %s
                """
                
                cursor.execute(search_sql, query_params)
                emails = cursor.fetchall()
                
                print(f"🔍 搜索关键词: '{keyword}' | 找到 {total} 封邮件 | 返回 {len(emails)} 封")
                
                return {
                    'success': True,
                    'data': emails,
                    'count': len(emails),
                    'total': total,
                    'keyword': keyword,
                    'limit': limit,
                    'offset': offset
                }
        
        except Exception as e:
            print(f"❌ 搜索邮件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0,
                'total': 0
            }
    
    @staticmethod
    def search_by_sender(
        account_id: int,
        sender: str,
        folder: str = 'INBOX',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        按发件人搜索
        
        Args:
            account_id: 账户ID
            sender: 发件人（邮箱或名称）
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
        """
        return EmailSearchService.search_emails(
            account_id=account_id,
            keyword=sender,
            folder=folder,
            search_fields=['from_email', 'from_name'],
            limit=limit,
            offset=offset
        )
    
    @staticmethod
    def search_by_subject(
        account_id: int,
        subject: str,
        folder: str = 'INBOX',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        按主题搜索
        
        Args:
            account_id: 账户ID
            subject: 主题关键词
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
        """
        return EmailSearchService.search_emails(
            account_id=account_id,
            keyword=subject,
            folder=folder,
            search_fields=['subject'],
            limit=limit,
            offset=offset
        )
    
    @staticmethod
    def search_with_attachments(
        account_id: int,
        keyword: Optional[str] = None,
        folder: str = 'INBOX',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索有附件的邮件
        
        Args:
            account_id: 账户ID
            keyword: 可选的搜索关键词
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
        """
        try:
            db = get_db_connection()
            
            # 构建查询条件
            where_conditions = ["account_id = %s", "folder = %s", "has_attachments = 1"]
            params = [account_id, folder]
            
            # 如果有关键词，添加搜索条件
            if keyword:
                where_conditions.append("(subject LIKE %s OR from_name LIKE %s OR from_email LIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
            
            where_clause = " AND ".join(where_conditions)
            
            # 1. 查询总数
            with db.get_cursor() as cursor:
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM email_list
                    WHERE {where_clause}
                """
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']
            
            # 2. 查询邮件列表
            with db.get_cursor() as cursor:
                query_params = params + [limit, offset]
                
                search_sql = f"""
                    SELECT 
                        id, uid, message_id, subject, from_email, from_name,
                        to_emails, cc_emails, bcc_emails, date, size, flags, 
                        has_attachments, attachment_count, attachment_names, 
                        text_preview, is_html, folder, synced_at
                    FROM email_list
                    WHERE {where_clause}
                    ORDER BY date DESC
                    LIMIT %s OFFSET %s
                """
                
                cursor.execute(search_sql, query_params)
                emails = cursor.fetchall()
                
                print(f"🔍 搜索有附件的邮件 | 找到 {total} 封")
                
                return {
                    'success': True,
                    'data': emails,
                    'count': len(emails),
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        
        except Exception as e:
            print(f"❌ 搜索有附件邮件失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0,
                'total': 0
            }
