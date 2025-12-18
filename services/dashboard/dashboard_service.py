"""
用户仪表板服务
负责获取和处理用户仪表板的统计数据
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from config.database import get_db_connection


class DashboardService:
    """仪表板服务类 - 专门处理用户仪表板数据"""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户完整的仪表板统计数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含所有统计数据的字典
        """
        try:
            # 获取各项统计数据
            user_info = self._get_user_info(user_id)
            imap_stats = self._get_imap_stats(user_id)
            email_stats = self._get_email_stats(user_id)
            email_daily_stats = self._get_email_daily_stats(user_id)
            order_stats = self._get_order_stats(user_id)
            order_daily_stats = self._get_order_daily_stats(user_id)
            recent_emails = self._get_recent_emails(user_id)
            recent_orders = self._get_recent_orders(user_id)
            
            return {
                "user": user_info,
                "imap_accounts": imap_stats,
                "emails": email_stats,
                "email_daily_stats": email_daily_stats,
                "orders": order_stats,
                "order_daily_stats": order_daily_stats,
                "recent_emails": recent_emails,
                "recent_orders": recent_orders
            }
        except Exception as e:
            print(f"获取仪表板统计数据失败: {str(e)}")
            raise e
    
    def _get_user_info(self, user_id: int) -> Dict[str, Any]:
        """获取用户基本信息"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT username, email, nickname, avatar, role, plan, 
                       plan_expire_at, created_at, last_login_at
                FROM users 
                WHERE id = %s
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                raise ValueError("用户不存在")
            
            return {
                "username": user_data["username"],
                "email": user_data["email"],
                "nickname": user_data["nickname"] or user_data["username"],
                "avatar": user_data["avatar"] or "/assets/images/avatars/user.png",
                "role": user_data["role"],
                "plan": user_data["plan"],
                "plan_expire_at": user_data["plan_expire_at"].isoformat() if user_data["plan_expire_at"] else None,
                "created_at": user_data["created_at"].isoformat(),
                "last_login_at": user_data["last_login_at"].isoformat() if user_data["last_login_at"] else None,
            }
    
    def _get_imap_stats(self, user_id: int) -> Dict[str, Any]:
        """获取IMAP账户统计"""
        with self.db.get_cursor() as cursor:
            # 总账户数
            cursor.execute("""
                SELECT COUNT(*) as total FROM imap_accounts WHERE user_id = %s
            """, (user_id,))
            total_accounts = cursor.fetchone()["total"]
            
            # 启用的账户数
            cursor.execute("""
                SELECT COUNT(*) as active FROM imap_accounts 
                WHERE user_id = %s AND status = 1
            """, (user_id,))
            active_accounts = cursor.fetchone()["active"]
            inactive_accounts = total_accounts - active_accounts
            
            # 按平台分组统计
            cursor.execute("""
                SELECT platform, COUNT(*) as count 
                FROM imap_accounts 
                WHERE user_id = %s 
                GROUP BY platform
            """, (user_id,))
            platform_stats = cursor.fetchall()
            by_platform = {row["platform"]: row["count"] for row in platform_stats}
            
            return {
                "total": total_accounts,
                "active": active_accounts,
                "inactive": inactive_accounts,
                "by_platform": by_platform
            }
    
    def _get_email_stats(self, user_id: int) -> Dict[str, Any]:
        """获取邮件统计"""
        with self.db.get_cursor() as cursor:
            # 获取用户的所有 IMAP 账户 ID
            cursor.execute("""
                SELECT id FROM imap_accounts WHERE user_id = %s
            """, (user_id,))
            account_ids = [row["id"] for row in cursor.fetchall()]
            
            if not account_ids:
                return {
                    "total": 0,
                    "today": 0,
                    "this_week": 0,
                    "this_month": 0,
                    "with_attachments": 0,
                    "by_folder": {}
                }
            
            placeholders = ','.join(['%s'] * len(account_ids))
            
            # 总邮件数
            cursor.execute(f"""
                SELECT COUNT(*) as total FROM email_list 
                WHERE account_id IN ({placeholders})
            """, account_ids)
            total_emails = cursor.fetchone()["total"]
            
            # 今日邮件
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute(f"""
                SELECT COUNT(*) as today FROM email_list 
                WHERE account_id IN ({placeholders}) AND date >= %s
            """, account_ids + [today_start])
            today_emails = cursor.fetchone()["today"]
            
            # 本周邮件
            week_start = today_start - timedelta(days=today_start.weekday())
            cursor.execute(f"""
                SELECT COUNT(*) as week FROM email_list 
                WHERE account_id IN ({placeholders}) AND date >= %s
            """, account_ids + [week_start])
            week_emails = cursor.fetchone()["week"]
            
            # 本月邮件
            month_start = today_start.replace(day=1)
            cursor.execute(f"""
                SELECT COUNT(*) as month FROM email_list 
                WHERE account_id IN ({placeholders}) AND date >= %s
            """, account_ids + [month_start])
            month_emails = cursor.fetchone()["month"]
            
            # 带附件的邮件
            cursor.execute(f"""
                SELECT COUNT(*) as with_attachments FROM email_list 
                WHERE account_id IN ({placeholders}) AND has_attachments = 1
            """, account_ids)
            with_attachments = cursor.fetchone()["with_attachments"]
            
            # 按文件夹分组
            cursor.execute(f"""
                SELECT folder, COUNT(*) as count FROM email_list 
                WHERE account_id IN ({placeholders}) 
                GROUP BY folder
            """, account_ids)
            folder_stats = cursor.fetchall()
            by_folder = {row["folder"]: row["count"] for row in folder_stats}
            
            return {
                "total": total_emails,
                "today": today_emails,
                "this_week": week_emails,
                "this_month": month_emails,
                "with_attachments": with_attachments,
                "by_folder": by_folder
            }
    
    def _get_order_stats(self, user_id: int) -> Dict[str, Any]:
        """获取订单统计"""
        with self.db.get_cursor() as cursor:
            # 总订单数
            cursor.execute("SELECT COUNT(*) as total FROM rei_orders WHERE user_id = %s", (user_id,))
            total_orders = cursor.fetchone()["total"]
            
            # 已完成订单数
            cursor.execute("SELECT COUNT(*) as completed FROM rei_orders WHERE user_id = %s AND is_complete = 1", (user_id,))
            completed_orders = cursor.fetchone()["completed"]
            
            # 待处理订单数
            cursor.execute("SELECT COUNT(*) as pending FROM rei_orders WHERE user_id = %s AND is_complete = 0", (user_id,))
            pending_orders = cursor.fetchone()["pending"]
            
            # 总金额
            cursor.execute("SELECT COALESCE(SUM(order_total), 0) as total_amount FROM rei_orders WHERE user_id = %s", (user_id,))
            total_amount = float(cursor.fetchone()["total_amount"])
            
            # 本月订单金额
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COALESCE(SUM(order_total), 0) as month_amount 
                FROM rei_orders 
                WHERE user_id = %s AND order_date >= %s
            """, (user_id, month_start))
            month_amount = float(cursor.fetchone()["month_amount"])
            
            return {
                "total": total_orders,
                "completed": completed_orders,
                "pending": pending_orders,
                "cancelled": 0,
                "total_amount": total_amount,
                "this_month_amount": month_amount,
                "by_status": {
                    "completed": completed_orders,
                    "pending": pending_orders
                }
            }
    
    def _get_recent_emails(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的邮件"""
        with self.db.get_cursor() as cursor:
            # 获取用户的所有 IMAP 账户 ID
            cursor.execute("""
                SELECT id FROM imap_accounts WHERE user_id = %s
            """, (user_id,))
            account_ids = [row["id"] for row in cursor.fetchall()]
            
            if not account_ids:
                return []
            
            placeholders = ','.join(['%s'] * len(account_ids))
            cursor.execute(f"""
                SELECT id, subject, from_email, from_name, date, has_attachments
                FROM email_list 
                WHERE account_id IN ({placeholders})
                ORDER BY date DESC 
                LIMIT %s
            """, account_ids + [limit])
            email_records = cursor.fetchall()
            
            return [
                {
                    "id": email["id"],
                    "subject": email["subject"] or "(无主题)",
                    "from_email": email["from_email"],
                    "from_name": email["from_name"] or email["from_email"],
                    "date": email["date"].isoformat() if email["date"] else datetime.now().isoformat(),
                    "has_attachments": bool(email["has_attachments"])
                }
                for email in email_records
            ]
    
    def _get_recent_orders(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的订单"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, order_id, order_date, order_total, is_complete
                FROM rei_orders 
                WHERE user_id = %s
                ORDER BY order_date DESC 
                LIMIT %s
            """, (user_id, limit))
            order_records = cursor.fetchall()
            
            return [
                {
                    "id": order["id"],
                    "order_id": order["order_id"],
                    "order_date": order["order_date"].isoformat(),
                    "order_total": float(order["order_total"]),
                    "is_complete": bool(order["is_complete"])
                }
                for order in order_records
            ]
    
    def _get_order_daily_stats(self, user_id: int, days: int = 90) -> List[Dict[str, Any]]:
        """
        获取最近几天的订单统计数据（按天统计）
        
        Args:
            user_id: 用户ID
            days: 统计的天数，默认90天
            
        Returns:
            按日期统计的订单数据列表
        """
        with self.db.get_cursor() as cursor:
            # 获取最近N天的订单统计
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(order_date, '%%Y-%%m-%%d') as date,
                    COUNT(CASE WHEN is_complete = 1 THEN 1 END) as completed,
                    COUNT(CASE WHEN is_complete = 0 THEN 1 END) as pending,
                    0 as cancelled
                FROM rei_orders
                WHERE user_id = %s AND order_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY DATE_FORMAT(order_date, '%%Y-%%m-%%d')
                ORDER BY date ASC
            """, (user_id, days))
            
            daily_data = cursor.fetchall()
            
            result = []
            for row in daily_data:
                date_str = row["date"]  # 格式: "2024-11-24"
                # 转换为 "11-24" 格式
                month_day = date_str.split('-')[1] + '-' + date_str.split('-')[2]
                result.append({
                    "date": month_day,  # "11-24"
                    "completed": row["completed"],
                    "pending": row["pending"],
                    "cancelled": row["cancelled"]
                })
            
            return result
    
    def _get_email_daily_stats(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取最近几天的邮件统计数据（按天统计）
        
        Args:
            user_id: 用户ID
            days: 统计的天数，默认30天
            
        Returns:
            按日期统计的邮件数据列表
        """
        with self.db.get_cursor() as cursor:
            # 获取用户的所有 IMAP 账户 ID
            cursor.execute("""
                SELECT id FROM imap_accounts WHERE user_id = %s
            """, (user_id,))
            account_ids = [row["id"] for row in cursor.fetchall()]
            
            if not account_ids:
                # 如果没有账户，返回空数据
                return []
            
            placeholders = ','.join(['%s'] * len(account_ids))
            
            # 获取最近N天的邮件统计
            cursor.execute(f"""
                SELECT 
                    DATE_FORMAT(date, '%%Y-%%m-%%d') as date,
                    COUNT(*) as received,
                    0 as sent
                FROM email_list
                WHERE account_id IN ({placeholders})
                  AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY DATE_FORMAT(date, '%%Y-%%m-%%d')
                ORDER BY date ASC
            """, account_ids + [days])
            
            daily_data = cursor.fetchall()
            
            result = []
            for row in daily_data:
                date_str = row["date"]  # 格式: "2024-11-24"
                result.append({
                    "date": date_str,  # 保持完整日期格式
                    "received": row["received"],
                    "sent": row["sent"]  # 目前没有发送邮件统计，默认为0
                })
            
            return result
