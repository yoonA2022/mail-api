"""
REI 订单邮件筛选服务
用于从邮件列表中筛选 REI 订单确认邮件
"""

from config.database import get_db_connection
from typing import List, Dict, Any, Optional
import re
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor


class ReiEmailFilter:
    """REI 订单邮件筛选器"""
    
    # REI 订单邮件特征
    REI_FROM_EMAIL = "rei@notices.rei.com"
    REI_FROM_NAME = "REI Co-op"
    REI_SUBJECT_PATTERN = r"Thanks for your order!\s*\(#([A-Z0-9]+)\)"
    
    # 线程池（用于执行阻塞的数据库操作）
    _executor = ThreadPoolExecutor(max_workers=5)
    
    @staticmethod
    def extract_order_number(subject: str) -> Optional[str]:
        """
        从邮件主题中提取订单号
        
        Args:
            subject: 邮件主题
            
        Returns:
            订单号，如果不匹配返回 None
            
        Examples:
            "Thanks for your order! (#Y127241896)" -> "Y127241896"
            "Thanks for your order! (#A385076038)" -> "A385076038"
        """
        if not subject:
            return None
        
        match = re.search(ReiEmailFilter.REI_SUBJECT_PATTERN, subject)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def is_rei_order_email(email: Dict[str, Any]) -> bool:
        """
        判断是否为 REI 订单确认邮件
        
        Args:
            email: 邮件数据字典
            
        Returns:
            是否为 REI 订单邮件
        """
        # 检查发件人邮箱
        if email.get('from_email') != ReiEmailFilter.REI_FROM_EMAIL:
            return False
        
        # 检查主题是否匹配订单格式
        subject = email.get('subject', '')
        order_number = ReiEmailFilter.extract_order_number(subject)
        
        return order_number is not None
    
    @staticmethod
    def _filter_rei_emails_sync(
        account_id: Optional[int] = None,
        folder: str = 'INBOX',
        limit: int = 100,
        offset: int = 0,
        include_forwarded: bool = True
    ) -> Dict[str, Any]:
        """
        筛选 REI 订单邮件
        
        Args:
            account_id: 账户ID（可选，不指定则查询所有账户）
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
            include_forwarded: 是否包含转发的邮件
            
        Returns:
            {
                'success': True,
                'data': [...],
                'count': 10,
                'total': 25
            }
        """
        try:
            db = get_db_connection()
            
            # 构建查询条件
            where_conditions = ["folder = %s"]
            params = [folder]
            
            if account_id is not None:
                where_conditions.append("account_id = %s")
                params.append(account_id)
            
            # 基础查询条件：发件人是 REI
            if include_forwarded:
                # 包含转发邮件：主题包含 REI 订单格式
                where_conditions.append("subject LIKE %s")
                params.append("%Thanks for your order!%#%")
            else:
                # 只要直接来自 REI 的邮件
                where_conditions.append("from_email = %s")
                params.append(ReiEmailFilter.REI_FROM_EMAIL)
                where_conditions.append("subject LIKE %s")
                params.append("%Thanks for your order!%#%")
            
            # 过滤掉 Y 开头的礼品卡，只保留 A 开头的订单
            where_conditions.append("subject NOT LIKE %s")
            params.append("%#Y%")
            
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
                
                select_sql = f"""
                    SELECT 
                        id, account_id, uid, message_id, subject, 
                        from_email, from_name, to_emails, 
                        date, size, flags, has_attachments, 
                        attachment_count, text_preview, is_html, 
                        folder, synced_at, created_at
                    FROM email_list
                    WHERE {where_clause}
                    ORDER BY date DESC
                    LIMIT %s OFFSET %s
                """
                
                cursor.execute(select_sql, query_params)
                emails = cursor.fetchall()
                
                # 处理邮件数据，提取订单号
                processed_emails = []
                for email in emails:
                    email_dict = dict(email)
                    
                    # 提取订单号
                    order_number = ReiEmailFilter.extract_order_number(email_dict['subject'])
                    email_dict['order_number'] = order_number
                    
                    # 解析 JSON 字段
                    try:
                        email_dict['to_emails'] = json.loads(email_dict['to_emails']) if email_dict['to_emails'] else []
                    except:
                        email_dict['to_emails'] = []
                    
                    try:
                        email_dict['flags'] = json.loads(email_dict['flags']) if email_dict['flags'] else []
                    except:
                        email_dict['flags'] = []
                    
                    # 判断是否为转发邮件
                    email_dict['is_forwarded'] = email_dict['from_email'] != ReiEmailFilter.REI_FROM_EMAIL
                    
                    # 格式化日期
                    if email_dict['date']:
                        email_dict['date'] = email_dict['date'].isoformat()
                    if email_dict['synced_at']:
                        email_dict['synced_at'] = email_dict['synced_at'].isoformat()
                    if email_dict['created_at']:
                        email_dict['created_at'] = email_dict['created_at'].isoformat()
                    
                    processed_emails.append(email_dict)
                
                print(f"🔍 筛选 REI 订单邮件: 找到 {total} 封 | 返回 {len(processed_emails)} 封")
                
                return {
                    'success': True,
                    'data': processed_emails,
                    'count': len(processed_emails),
                    'total': total,
                    'filter': {
                        'account_id': account_id,
                        'folder': folder,
                        'include_forwarded': include_forwarded
                    }
                }
        
        except Exception as e:
            print(f"❌ 筛选 REI 邮件失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0,
                'total': 0
            }
    
    @staticmethod
    async def filter_rei_emails(
        account_id: Optional[int] = None,
        folder: str = 'INBOX',
        limit: int = 100,
        offset: int = 0,
        include_forwarded: bool = True
    ) -> Dict[str, Any]:
        """
        异步筛选 REI 订单邮件（使用线程池避免阻塞）
        
        Args:
            account_id: 账户ID（可选，不指定则查询所有账户）
            folder: 文件夹名称
            limit: 返回数量
            offset: 偏移量
            include_forwarded: 是否包含转发的邮件
            
        Returns:
            {
                'success': True,
                'data': [...],
                'count': 10,
                'total': 25
            }
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ReiEmailFilter._executor,
            ReiEmailFilter._filter_rei_emails_sync,
            account_id,
            folder,
            limit,
            offset,
            include_forwarded
        )
    
    @staticmethod
    def get_rei_email_by_order_number(
        order_number: str,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        根据订单号查询邮件
        
        Args:
            order_number: REI 订单号（如：Y127241896）
            account_id: 账户ID（可选）
            
        Returns:
            邮件数据或错误信息
        """
        try:
            db = get_db_connection()
            
            # 构建查询条件
            where_conditions = ["subject LIKE %s"]
            params = [f"%#{order_number}%"]
            
            if account_id is not None:
                where_conditions.append("account_id = %s")
                params.append(account_id)
            
            where_clause = " AND ".join(where_conditions)
            
            with db.get_cursor() as cursor:
                select_sql = f"""
                    SELECT 
                        id, account_id, uid, message_id, subject, 
                        from_email, from_name, to_emails, 
                        date, size, flags, has_attachments, 
                        attachment_count, text_preview, is_html, 
                        folder, synced_at, created_at
                    FROM email_list
                    WHERE {where_clause}
                    ORDER BY date DESC
                    LIMIT 1
                """
                
                cursor.execute(select_sql, params)
                email = cursor.fetchone()
                
                if not email:
                    return {
                        'success': False,
                        'error': f'未找到订单号为 {order_number} 的邮件'
                    }
                
                # 处理邮件数据
                email_dict = dict(email)
                email_dict['order_number'] = ReiEmailFilter.extract_order_number(email_dict['subject'])
                
                # 解析 JSON 字段
                try:
                    email_dict['to_emails'] = json.loads(email_dict['to_emails']) if email_dict['to_emails'] else []
                except:
                    email_dict['to_emails'] = []
                
                try:
                    email_dict['flags'] = json.loads(email_dict['flags']) if email_dict['flags'] else []
                except:
                    email_dict['flags'] = []
                
                # 判断是否为转发邮件
                email_dict['is_forwarded'] = email_dict['from_email'] != ReiEmailFilter.REI_FROM_EMAIL
                
                # 格式化日期
                if email_dict['date']:
                    email_dict['date'] = email_dict['date'].isoformat()
                if email_dict['synced_at']:
                    email_dict['synced_at'] = email_dict['synced_at'].isoformat()
                if email_dict['created_at']:
                    email_dict['created_at'] = email_dict['created_at'].isoformat()
                
                return {
                    'success': True,
                    'data': email_dict
                }
        
        except Exception as e:
            print(f"❌ 查询订单邮件失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_statistics(account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取 REI 订单邮件统计信息
        
        Args:
            account_id: 账户ID（可选）
            
        Returns:
            统计信息
        """
        try:
            db = get_db_connection()
            
            # 构建查询条件
            where_conditions = ["subject LIKE %s"]
            params = ["%Thanks for your order!%#%"]
            
            if account_id is not None:
                where_conditions.append("account_id = %s")
                params.append(account_id)
            
            where_clause = " AND ".join(where_conditions)
            
            with db.get_cursor() as cursor:
                # 总数统计
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_count,
                        SUM(CASE WHEN from_email = %s THEN 1 ELSE 0 END) as direct_count,
                        SUM(CASE WHEN from_email != %s THEN 1 ELSE 0 END) as forwarded_count
                    FROM email_list
                    WHERE {where_clause}
                """, [ReiEmailFilter.REI_FROM_EMAIL, ReiEmailFilter.REI_FROM_EMAIL] + params)
                
                stats = cursor.fetchone()
                
                # 按账户统计
                account_stats = []
                if account_id is None:
                    cursor.execute(f"""
                        SELECT 
                            account_id,
                            COUNT(*) as count
                        FROM email_list
                        WHERE {where_clause}
                        GROUP BY account_id
                        ORDER BY count DESC
                    """, params)
                    
                    account_stats = cursor.fetchall()
                
                return {
                    'success': True,
                    'total_count': stats['total_count'],
                    'direct_count': stats['direct_count'],
                    'forwarded_count': stats['forwarded_count'],
                    'account_stats': [dict(s) for s in account_stats] if account_stats else []
                }
        
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

