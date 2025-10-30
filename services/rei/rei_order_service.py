"""
REI 订单服务
提供订单的查询和管理功能
"""

from config.database import get_db_connection
from typing import Dict, Any, Optional, List
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import traceback


class ReiOrderService:
    """REI 订单数据库服务类"""
    
    # 线程池（用于执行阻塞的数据库操作）
    _executor = ThreadPoolExecutor(max_workers=5)
    
    @staticmethod
    def save_order(
        order_data: Dict[str, Any],
        user_id: Optional[int] = None,
        account_id: Optional[int] = None,
        email_id: Optional[int] = None,
        email_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存订单到数据库（如果已存在则更新）
        
        Args:
            order_data: REI API 返回的完整订单数据
            user_id: 关联的用户ID（可选）
            account_id: 关联的邮箱账户ID（可选）
            email_id: 关联的邮件ID（可选）
            email_info: 从邮件中提取的额外信息（如账单地址、发货地址）
            
        Returns:
            {
                'success': True,
                'order_id': 'A385893454',
                'action': 'created' | 'updated',
                'db_id': 123
            }
        """
        try:
            from config.database import get_db_connection
            
            order_id = order_data.get('orderId')
            if not order_id:
                return {
                    'success': False,
                    'error': '订单数据缺少 orderId 字段'
                }
            
            print(f"💾 保存订单: {order_id}")
            
            # 准备数据
            save_data = ReiOrderService._prepare_order_data(order_data, email_info)
            save_data['user_id'] = user_id
            save_data['account_id'] = account_id
            save_data['email_id'] = email_id
            
            db = get_db_connection()
            
            # 检查订单是否已存在
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM rei_orders WHERE order_id = %s",
                    (order_id,)
                )
                existing = cursor.fetchone()
            
            # 保存或更新订单
            with db.get_cursor() as cursor:
                if existing:
                    # 更新现有订单
                    db_id = existing['id']
                    ReiOrderService._update_order(cursor, db_id, save_data)
                    action = 'updated'
                    print(f"   ✅ 订单已更新 (DB ID: {db_id})")
                else:
                    # 创建新订单
                    db_id = ReiOrderService._insert_order(cursor, save_data)
                    action = 'created'
                    print(f"   ✅ 订单已创建 (DB ID: {db_id})")
            
            return {
                'success': True,
                'order_id': order_id,
                'action': action,
                'db_id': db_id
            }
        
        except Exception as e:
            print(f"❌ 保存订单失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'order_id': order_data.get('orderId')
            }
    
    @staticmethod
    def _prepare_order_data(
        order_data: Dict[str, Any],
        email_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        准备要保存到数据库的订单数据
        
        Args:
            order_data: REI API 返回的数据
            email_info: 从邮件中提取的额外信息
            
        Returns:
            准备好的数据字典
        """
        # 基本信息
        data = {
            'order_id': order_data.get('orderId'),
            'is_guest': order_data.get('isGuest', False),
            'is_released': order_data.get('isReleased', False),
            'order_type': order_data.get('orderType', 'ONLINE'),
            'order_date': ReiOrderService._parse_datetime(order_data.get('orderDate')),
            'is_complete': order_data.get('isComplete', False),
            'est_rewards_earned': order_data.get('estRewardsEarned', 0.00),
            'has_dividend_refund': order_data.get('hasDividendRefund', False),
            'order_header_key': order_data.get('orderHeaderKey'),
            'remorse_deadline': ReiOrderService._parse_datetime(order_data.get('remorseDeadline')),
            'cancellability': order_data.get('cancellability'),
            'retail_store_info': json.dumps(order_data.get('retailStoreInfo')) if order_data.get('retailStoreInfo') else None,
        }
        
        # 金额信息
        data.update({
            'total_order_discount': order_data.get('totalOrderDiscount', 0.00),
            'total_discounted_order_amount': order_data.get('totalDiscountedOrderAmount', 0.00),
            'total_tax_amount': order_data.get('totalTaxAmount', 0.00),
            'total_shipping_amount': order_data.get('totalShippingAmount', 0.00),
            'order_total': order_data.get('orderTotal', 0.00),
            'amount_paid': order_data.get('amountPaid', 0.00),
        })
        
        # JSON 字段
        data.update({
            'fulfillment_groups': json.dumps(order_data.get('fulfillmentGroups', [])),
            'tenders': json.dumps(order_data.get('tenders', [])),
            'fees': json.dumps(order_data.get('fees')) if order_data.get('fees') else None,
            'shipping_charges': json.dumps(order_data.get('shippingCharges', [])),
            'discounts': json.dumps(order_data.get('discounts')) if order_data.get('discounts') else None,
            'billing_address': json.dumps(order_data.get('billingAddress')) if order_data.get('billingAddress') else None,
        })
        
        # 如果有邮件信息，合并账单地址和发货地址
        if email_info:
            # 如果 API 没有返回 billingAddress，使用邮件中的
            if not data['billing_address'] and email_info.get('billing_address'):
                billing_addr = {
                    'name': email_info.get('billing_name'),
                    'address': email_info.get('billing_address'),
                    'city': email_info.get('billing_city'),
                    'state': email_info.get('billing_state'),
                    'zipCode': email_info.get('billing_zip_code')
                }
                data['billing_address'] = json.dumps(billing_addr)
            
            # 如果 fulfillmentGroups 中没有 shipTo，添加邮件中的发货地址
            if email_info.get('shipping_address'):
                fulfillment_groups = json.loads(data['fulfillment_groups'])
                if fulfillment_groups and not fulfillment_groups[0].get('shipTo'):
                    ship_to = {
                        'name': email_info.get('shipping_name'),
                        'address': email_info.get('shipping_address'),
                        'city': email_info.get('shipping_city'),
                        'state': email_info.get('shipping_state'),
                        'zipCode': email_info.get('shipping_zip_code')
                    }
                    fulfillment_groups[0]['shipTo'] = ship_to
                    data['fulfillment_groups'] = json.dumps(fulfillment_groups)
        
        return data
    
    @staticmethod
    def _insert_order(cursor, data: Dict[str, Any]) -> int:
        """插入新订单"""
        sql = """
            INSERT INTO rei_orders (
                order_id, is_guest, is_released, order_type, order_date,
                is_complete, est_rewards_earned, has_dividend_refund,
                order_header_key, remorse_deadline, cancellability,
                retail_store_info, total_order_discount, total_discounted_order_amount,
                total_tax_amount, total_shipping_amount, order_total, amount_paid,
                fulfillment_groups, tenders, fees, shipping_charges, discounts,
                billing_address, user_id, account_id, email_id
            ) VALUES (
                %(order_id)s, %(is_guest)s, %(is_released)s, %(order_type)s, %(order_date)s,
                %(is_complete)s, %(est_rewards_earned)s, %(has_dividend_refund)s,
                %(order_header_key)s, %(remorse_deadline)s, %(cancellability)s,
                %(retail_store_info)s, %(total_order_discount)s, %(total_discounted_order_amount)s,
                %(total_tax_amount)s, %(total_shipping_amount)s, %(order_total)s, %(amount_paid)s,
                %(fulfillment_groups)s, %(tenders)s, %(fees)s, %(shipping_charges)s, %(discounts)s,
                %(billing_address)s, %(user_id)s, %(account_id)s, %(email_id)s
            )
        """
        cursor.execute(sql, data)
        return cursor.lastrowid
    
    @staticmethod
    def _update_order(cursor, db_id: int, data: Dict[str, Any]):
        """更新现有订单（智能保留原有数据）"""
        # 先查询现有数据
        cursor.execute(
            "SELECT order_date, billing_address, user_id FROM rei_orders WHERE id = %s",
            (db_id,)
        )
        existing = cursor.fetchone()
        
        # 智能保留原有数据
        if existing:
            # 如果新数据的 order_date 为 None，保留原有值
            if data.get('order_date') is None and existing.get('order_date'):
                data['order_date'] = existing['order_date']
            
            # 如果新数据的 billing_address 为 None，保留原有值
            if data.get('billing_address') is None and existing.get('billing_address'):
                data['billing_address'] = existing['billing_address']
            
            # 如果新数据的 user_id 为 None，保留原有值
            if data.get('user_id') is None and existing.get('user_id'):
                data['user_id'] = existing['user_id']
        
        sql = """
            UPDATE rei_orders SET
                is_guest = %(is_guest)s,
                is_released = %(is_released)s,
                order_type = %(order_type)s,
                order_date = %(order_date)s,
                is_complete = %(is_complete)s,
                est_rewards_earned = %(est_rewards_earned)s,
                has_dividend_refund = %(has_dividend_refund)s,
                order_header_key = %(order_header_key)s,
                remorse_deadline = %(remorse_deadline)s,
                cancellability = %(cancellability)s,
                retail_store_info = %(retail_store_info)s,
                total_order_discount = %(total_order_discount)s,
                total_discounted_order_amount = %(total_discounted_order_amount)s,
                total_tax_amount = %(total_tax_amount)s,
                total_shipping_amount = %(total_shipping_amount)s,
                order_total = %(order_total)s,
                amount_paid = %(amount_paid)s,
                fulfillment_groups = %(fulfillment_groups)s,
                tenders = %(tenders)s,
                fees = %(fees)s,
                shipping_charges = %(shipping_charges)s,
                discounts = %(discounts)s,
                billing_address = %(billing_address)s,
                user_id = %(user_id)s,
                updated_at = NOW()
            WHERE id = %(id)s
        """
        cursor.execute(sql, {**data, 'id': db_id})
    
    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[str]:
        """
        解析 ISO 8601 日期时间字符串
        
        Args:
            dt_str: ISO 8601 格式的日期时间字符串
            
        Returns:
            MySQL 格式的日期时间字符串
        """
        if not dt_str:
            return None
        
        try:
            # 解析 ISO 8601 格式（如 "2025-10-23T08:21:24-07:00"）
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            # 转换为 MySQL 格式
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return None
    
    @staticmethod
    def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
        """
        根据订单号查询订单
        
        Args:
            order_id: 订单号
            
        Returns:
            订单数据字典或 None
        """
        try:
            from config.database import get_db_connection
            
            db = get_db_connection()
            
            with db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rei_orders WHERE order_id = %s",
                    (order_id,)
                )
                return cursor.fetchone()
        
        except Exception as e:
            # 静默处理，不打印错误（这是正常的检查操作）
            return None
    
    @staticmethod
    def _order_exists_sync(order_id: str) -> bool:
        """
        检查订单是否已存在（同步版本）
        
        Args:
            order_id: 订单号
            
        Returns:
            True 如果存在，否则 False
        """
        return ReiOrderService.get_order_by_id(order_id) is not None
    
    @staticmethod
    async def order_exists(order_id: str) -> bool:
        """
        异步检查订单是否已存在
        
        Args:
            order_id: 订单号
            
        Returns:
            True 如果存在，否则 False
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ReiOrderService._executor,
            ReiOrderService._order_exists_sync,
            order_id
        )
    
    @staticmethod
    def get_orders_list(
        account_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取订单列表
        
        Args:
            account_id: 账户ID（可选）
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            订单列表
        """
        try:
            from config.database import get_db_connection
            
            db = get_db_connection()
            
            with db.get_cursor() as cursor:
                if account_id:
                    sql = """
                        SELECT * FROM rei_orders 
                        WHERE account_id = %s 
                        ORDER BY order_date DESC 
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(sql, (account_id, limit, offset))
                else:
                    sql = """
                        SELECT * FROM rei_orders 
                        ORDER BY order_date DESC 
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(sql, (limit, offset))
                
                return cursor.fetchall()
        
        except Exception as e:
            print(f"❌ 获取订单列表失败: {e}")
            return []
