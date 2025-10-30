"""
REI 订单数据保存服务
专门用于将 REI API 返回的完整订单数据保存到数据库
"""

from config.database import get_db_connection
from typing import Dict, Any, Optional
from datetime import datetime
import json
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor


class ReiOrderDataService:
    """REI 订单数据保存服务类"""
    
    # 线程池（用于执行阻塞的数据库操作）
    _executor = ThreadPoolExecutor(max_workers=5)
    
    @staticmethod
    def _save_email_parsed_order_sync(
        email_info: Dict[str, Any],
        account_id: int,
        email_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        保存从邮件解析的基本订单信息到数据库
        
        Args:
            email_info: 从邮件HTML解析的订单信息
            account_id: 邮箱账户ID
            email_id: 邮件ID
            user_id: 用户ID（可选，如果不提供则从 account_id 查询）
            
        Returns:
            {
                'success': True,
                'order_id': 'A385267303',
                'action': 'created' or 'updated',
                'db_id': 1
            }
        """
        try:
            order_id = email_info.get('order_number')
            if not order_id:
                return {
                    'success': False,
                    'error': '邮件信息缺少订单号'
                }
            
            db = get_db_connection()
            
            # 如果没有提供 user_id，从 account_id 查询
            if user_id is None and account_id:
                with db.get_cursor() as cursor:
                    cursor.execute("SELECT user_id FROM imap_accounts WHERE id = %s", (account_id,))
                    account = cursor.fetchone()
                    if account:
                        user_id = account.get('user_id')
            
            # 检查订单是否已存在
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM rei_orders WHERE order_id = %s", (order_id,))
                existing = cursor.fetchone()
            
            # 准备基本数据
            prepared_data = ReiOrderDataService._prepare_email_order_data(
                email_info,
                user_id,
                account_id,
                email_id
            )
            
            # 保存或更新订单
            with db.get_cursor() as cursor:
                if existing:
                    # 更新现有订单的邮件信息（不覆盖API数据）
                    result = ReiOrderDataService._update_email_order(
                        cursor,
                        order_id,
                        prepared_data
                    )
                    action = 'updated'
                    db_id = existing['id']
                else:
                    # 插入新订单（只有基本信息）
                    result = ReiOrderDataService._insert_email_order(
                        cursor,
                        prepared_data
                    )
                    action = 'created'
                    db_id = cursor.lastrowid
            
            return {
                'success': True,
                'order_id': order_id,
                'action': action,
                'db_id': db_id
            }
        
        except Exception as e:
            print(f"❌ 保存邮件解析订单失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    async def save_email_parsed_order(
        email_info: Dict[str, Any],
        account_id: int,
        email_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        异步保存从邮件解析的基本订单信息到数据库
        
        Args:
            email_info: 从邮件HTML解析的订单信息
            account_id: 邮箱账户ID
            email_id: 邮件ID
            user_id: 用户ID（可选，如果不提供则从 account_id 查询）
            
        Returns:
            保存结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            ReiOrderDataService._executor,
            ReiOrderDataService._save_email_parsed_order_sync,
            email_info,
            account_id,
            email_id,
            user_id
        )
    
    @staticmethod
    def save_api_order_data(
        order_data: Dict[str, Any],
        user_id: Optional[int] = None,
        account_id: Optional[int] = None,
        email_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        保存 REI API 返回的完整订单数据到数据库
        
        Args:
            order_data: REI API 返回的订单数据（完整 JSON）
            user_id: 关联的用户ID（可选）
            account_id: 关联的邮箱账户ID（可选）
            email_id: 关联的邮件ID（可选）
            
        Returns:
            {
                'success': True,
                'order_id': 'A385267303',
                'action': 'created' or 'updated',
                'db_id': 1
            }
        """
        try:
            order_id = order_data.get('orderId')
            if not order_id:
                return {
                    'success': False,
                    'error': '订单数据缺少 orderId 字段'
                }
            
            db = get_db_connection()
            
            # 检查订单是否已存在
            with db.get_cursor() as cursor:
                cursor.execute("SELECT id FROM rei_orders WHERE order_id = %s", (order_id,))
                existing = cursor.fetchone()
            
            # 准备数据
            prepared_data = ReiOrderDataService._prepare_order_data(
                order_data, 
                user_id,
                account_id, 
                email_id
            )
            
            # 保存或更新订单
            with db.get_cursor() as cursor:
                if existing:
                    # 更新现有订单
                    result = ReiOrderDataService._update_order(
                        cursor, 
                        order_id, 
                        prepared_data
                    )
                    action = 'updated'
                    db_id = existing['id']
                else:
                    # 插入新订单
                    result = ReiOrderDataService._insert_order(
                        cursor, 
                        prepared_data
                    )
                    action = 'created'
                    db_id = cursor.lastrowid
            
            return {
                'success': True,
                'order_id': order_id,
                'action': action,
                'db_id': db_id
            }
        
        except Exception as e:
            print(f"❌ 保存订单数据失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _prepare_order_data(
        order_data: Dict[str, Any],
        user_id: Optional[int],
        account_id: Optional[int],
        email_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        准备要保存到数据库的订单数据
        
        Args:
            order_data: API 返回的原始数据
            user_id: 用户ID
            account_id: 账户ID
            email_id: 邮件ID
            
        Returns:
            处理后的数据字典
        """
        # 解析订单日期
        order_date = None
        if order_data.get('orderDate'):
            try:
                # 解析 ISO 8601 格式：2025-10-06T04:04:28-07:00
                order_date_str = order_data['orderDate']
                # 移除时区信息进行解析
                if '+' in order_date_str or order_date_str.count('-') > 2:
                    # 简单处理：只取日期和时间部分
                    order_date_str = order_date_str[:19]
                order_date = datetime.fromisoformat(order_date_str).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"  ⚠️ 解析订单日期失败: {e}")
        
        # 解析后悔期截止时间
        remorse_deadline = None
        if order_data.get('remorseDeadline'):
            try:
                deadline_str = order_data['remorseDeadline'][:19]
                remorse_deadline = datetime.fromisoformat(deadline_str).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"  ⚠️ 解析后悔期截止时间失败: {e}")
        
        # 准备数据
        prepared = {
            # 基本信息
            'order_id': order_data.get('orderId'),
            'is_guest': bool(order_data.get('isGuest', False)),
            'is_released': bool(order_data.get('isReleased', False)),
            'order_type': order_data.get('orderType', 'ONLINE'),
            'order_date': order_date,
            'is_complete': bool(order_data.get('isComplete', False)),
            'est_rewards_earned': float(order_data.get('estRewardsEarned', 0)),
            'has_dividend_refund': bool(order_data.get('hasDividendRefund', False)),
            'order_header_key': order_data.get('orderHeaderKey'),
            'remorse_deadline': remorse_deadline,
            'cancellability': order_data.get('cancellability'),
            'retail_store_info': json.dumps(order_data.get('retailStoreInfo')) if order_data.get('retailStoreInfo') else None,
            
            # 金额信息
            'total_order_discount': float(order_data.get('totalOrderDiscount', 0)),
            'total_discounted_order_amount': float(order_data.get('totalDiscountedOrderAmount', 0)),
            'total_tax_amount': float(order_data.get('totalTaxAmount', 0)),
            'total_shipping_amount': float(order_data.get('totalShippingAmount', 0)),
            'order_total': float(order_data.get('orderTotal', 0)),
            'amount_paid': float(order_data.get('amountPaid', 0)),
            
            # JSON 字段
            'fulfillment_groups': json.dumps(order_data.get('fulfillmentGroups', [])),
            'tenders': json.dumps(order_data.get('tenders', [])),
            'fees': json.dumps(order_data.get('fees')) if order_data.get('fees') else None,
            'shipping_charges': json.dumps(order_data.get('shippingCharges', [])),
            'discounts': json.dumps(order_data.get('discounts', [])),
            'billing_address': json.dumps(order_data.get('billingAddress')) if order_data.get('billingAddress') else None,
            
            # 关联信息
            'user_id': user_id,
            'account_id': account_id,
            'email_id': email_id
        }
        
        return prepared
    
    @staticmethod
    def _insert_order(cursor, data: Dict[str, Any]) -> None:
        """
        插入新订单
        
        Args:
            cursor: 数据库游标
            data: 订单数据
        """
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
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        
        cursor.execute(sql, (
            data['order_id'], data['is_guest'], data['is_released'], 
            data['order_type'], data['order_date'],
            data['is_complete'], data['est_rewards_earned'], data['has_dividend_refund'],
            data['order_header_key'], data['remorse_deadline'], data['cancellability'],
            data['retail_store_info'], data['total_order_discount'], 
            data['total_discounted_order_amount'],
            data['total_tax_amount'], data['total_shipping_amount'], 
            data['order_total'], data['amount_paid'],
            data['fulfillment_groups'], data['tenders'], data['fees'], 
            data['shipping_charges'], data['discounts'],
            data['billing_address'], data.get('user_id'), data['account_id'], data['email_id']
        ))
    
    @staticmethod
    def _update_order(cursor, order_id: str, data: Dict[str, Any]) -> None:
        """
        更新现有订单（智能保留原有数据）
        
        规则：
        - 如果 API 返回的 billing_address 为 None，保留原有账单地址
        - 如果传入的 user_id 为 None，保留原有用户ID
        - 如果传入的 account_id 为 None，保留原有账户ID
        - 如果传入的 email_id 为 None，保留原有邮件ID
        
        Args:
            cursor: 数据库游标
            order_id: 订单号
            data: 订单数据
        """
        # 先查询现有数据
        cursor.execute(
            "SELECT billing_address, user_id, account_id, email_id FROM rei_orders WHERE order_id = %s",
            (order_id,)
        )
        existing = cursor.fetchone()
        
        # 智能保留原有数据
        if existing:
            # 如果新数据的 billing_address 为 None，保留原有值
            if data['billing_address'] is None and existing['billing_address']:
                data['billing_address'] = existing['billing_address']
            
            # 如果新数据的 user_id 为 None，保留原有值
            if data.get('user_id') is None and existing.get('user_id'):
                data['user_id'] = existing['user_id']
            
            # 如果新数据的 account_id 为 None，保留原有值
            if data['account_id'] is None and existing['account_id']:
                data['account_id'] = existing['account_id']
            
            # 如果新数据的 email_id 为 None，保留原有值
            if data['email_id'] is None and existing['email_id']:
                data['email_id'] = existing['email_id']
        
        sql = """
            UPDATE rei_orders SET
                is_guest = %s,
                is_released = %s,
                order_type = %s,
                order_date = %s,
                is_complete = %s,
                est_rewards_earned = %s,
                has_dividend_refund = %s,
                order_header_key = %s,
                remorse_deadline = %s,
                cancellability = %s,
                retail_store_info = %s,
                total_order_discount = %s,
                total_discounted_order_amount = %s,
                total_tax_amount = %s,
                total_shipping_amount = %s,
                order_total = %s,
                amount_paid = %s,
                fulfillment_groups = %s,
                tenders = %s,
                fees = %s,
                shipping_charges = %s,
                discounts = %s,
                billing_address = %s,
                user_id = %s,
                account_id = %s,
                email_id = %s,
                updated_at = NOW()
            WHERE order_id = %s
        """
        
        cursor.execute(sql, (
            data['is_guest'], data['is_released'], 
            data['order_type'], data['order_date'],
            data['is_complete'], data['est_rewards_earned'], data['has_dividend_refund'],
            data['order_header_key'], data['remorse_deadline'], data['cancellability'],
            data['retail_store_info'], data['total_order_discount'], 
            data['total_discounted_order_amount'],
            data['total_tax_amount'], data['total_shipping_amount'], 
            data['order_total'], data['amount_paid'],
            data['fulfillment_groups'], data['tenders'], data['fees'], 
            data['shipping_charges'], data['discounts'],
            data['billing_address'], data.get('user_id'), data['account_id'], data['email_id'],
            order_id
        ))
    
    @staticmethod
    def get_order_status_summary(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从订单数据中提取状态摘要信息
        
        Args:
            order_data: 订单数据
            
        Returns:
            状态摘要信息
        """
        try:
            summary = {
                'order_id': order_data.get('orderId'),
                'is_complete': order_data.get('isComplete', False),
                'order_total': order_data.get('orderTotal', 0),
                'fulfillment_status': []
            }
            
            # 提取配送状态
            fulfillment_groups = order_data.get('fulfillmentGroups', [])
            for group in fulfillment_groups:
                status = group.get('status', {})
                summary['fulfillment_status'].append({
                    'delivery_type': group.get('deliveryType'),
                    'carrier': group.get('carrier'),
                    'tracking_number': group.get('trackingNumber'),
                    'status_code': status.get('summaryStatusCode'),
                    'status_date': status.get('statusDate'),
                    'current_ead': group.get('currentEad')
                })
            
            return summary
        
        except Exception as e:
            print(f"❌ 提取状态摘要失败: {e}")
            return {}
    
    @staticmethod
    def extract_products_from_order(order_data: Dict[str, Any]) -> list:
        """
        从订单数据中提取商品列表
        
        Args:
            order_data: 订单数据
            
        Returns:
            商品列表
        """
        try:
            products = []
            fulfillment_groups = order_data.get('fulfillmentGroups', [])
            
            for group in fulfillment_groups:
                fulfillment_items = group.get('fulfillmentItems', [])
                for item in fulfillment_items:
                    products.append({
                        'sku': item.get('sku'),
                        'name': item.get('name'),
                        'brand': item.get('brand'),
                        'color': item.get('color'),
                        'size': item.get('size'),
                        'quantity': item.get('quantity'),
                        'unit_price': item.get('unitPrice'),
                        'discounted_price': item.get('discountedUnitPrice'),
                        'total_price': item.get('totalPrice'),
                        'total_discount': item.get('totalDiscount')
                    })
            
            return products
        
        except Exception as e:
            print(f"❌ 提取商品列表失败: {e}")
            return []
    
    @staticmethod
    def _prepare_email_order_data(
        email_info: Dict[str, Any],
        user_id: Optional[int],
        account_id: int,
        email_id: int
    ) -> Dict[str, Any]:
        """
        准备从邮件解析的订单数据
        
        Args:
            email_info: 邮件解析信息
            user_id: 用户ID
            account_id: 账户ID
            email_id: 邮件ID
            
        Returns:
            处理后的数据字典
        """
        # 解析订单日期
        order_date = None
        if email_info.get('order_date'):
            try:
                order_date = email_info['order_date']
            except Exception as e:
                print(f"  ⚠️ 解析订单日期失败: {e}")
        
        # 构建账单地址JSON
        billing_address = None
        if email_info.get('billing_name'):
            billing_address = json.dumps({
                'name': email_info.get('billing_name'),
                'address': email_info.get('billing_address'),
                'city': email_info.get('billing_city'),
                'state': email_info.get('billing_state'),
                'zipCode': email_info.get('billing_zip_code')
            })
        
        # 构建配送信息JSON（保存到 tracking_info 字段）
        tracking_info_data = []
        if email_info.get('shipping_name'):
            tracking_info_data.append({
                'shipTo': {
                    'name': email_info.get('shipping_name'),
                    'address': email_info.get('shipping_address'),
                    'city': email_info.get('shipping_city'),
                    'state': email_info.get('shipping_state'),
                    'zipCode': email_info.get('shipping_zip_code')
                },
                'deliveryType': email_info.get('shipping_method', 'Standard shipping')
            })
        
        prepared = {
            'order_id': email_info.get('order_number'),
            'order_date': order_date,
            'order_total': float(email_info.get('total', 0)),
            'amount_paid': float(email_info.get('paid', 0)),
            'total_tax_amount': float(email_info.get('tax', 0)),
            'total_shipping_amount': float(email_info.get('shipping_fee', 0)),
            'billing_address': billing_address,
            'fulfillment_groups': None,  # 邮件解析时不保存，留给API数据
            'tracking_info': json.dumps(tracking_info_data) if tracking_info_data else None,  # 保存邮件解析的配送信息
            'tracking_url': email_info.get('tracking_url'),  # 物流追踪URL
            'user_id': user_id,
            'account_id': account_id,
            'email_id': email_id
        }
        
        return prepared
    
    @staticmethod
    def _insert_email_order(cursor, data: Dict[str, Any]) -> None:
        """
        插入从邮件解析的基本订单信息
        
        Args:
            cursor: 数据库游标
            data: 订单数据
        """
        sql = """
            INSERT INTO rei_orders (
                order_id, order_date, order_total, amount_paid,
                total_tax_amount, total_shipping_amount,
                billing_address, fulfillment_groups,
                tracking_info, tracking_url,
                user_id, account_id, email_id
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s
            )
        """
        
        cursor.execute(sql, (
            data['order_id'], data['order_date'], data['order_total'], data['amount_paid'],
            data['total_tax_amount'], data['total_shipping_amount'],
            data['billing_address'], data['fulfillment_groups'],
            data['tracking_info'], data['tracking_url'],
            data['user_id'], data['account_id'], data['email_id']
        ))
    
    @staticmethod
    def _update_email_order(cursor, order_id: str, data: Dict[str, Any]) -> None:
        """
        更新订单的邮件解析信息（不覆盖API数据）
        
        Args:
            cursor: 数据库游标
            order_id: 订单号
            data: 订单数据
        """
        # 只更新邮件相关字段
        # tracking_info: 保存邮件解析的配送信息
        # fulfillment_groups: 不更新（留给API数据）
        sql = """
            UPDATE rei_orders SET
                user_id = COALESCE(user_id, %s),
                account_id = COALESCE(account_id, %s),
                email_id = COALESCE(email_id, %s),
                billing_address = COALESCE(billing_address, %s),
                tracking_info = COALESCE(tracking_info, %s),
                tracking_url = COALESCE(tracking_url, %s),
                updated_at = NOW()
            WHERE order_id = %s
        """
        
        cursor.execute(sql, (
            data['user_id'], data['account_id'], data['email_id'],
            data['billing_address'],
            data['tracking_info'], data['tracking_url'],
            order_id
        ))
    
    @staticmethod
    def get_order_by_order_id(order_id: str) -> Optional[Dict[str, Any]]:
        """
        根据订单号获取订单数据
        
        Args:
            order_id: 订单号
            
        Returns:
            订单数据字典，如果不存在返回 None
        """
        try:
            db = get_db_connection()
            
            with db.get_cursor() as cursor:
                sql = """
                    SELECT 
                        id, order_id, is_guest, is_released, order_type, order_date,
                        is_complete, est_rewards_earned, has_dividend_refund,
                        order_header_key, remorse_deadline, cancellability,
                        retail_store_info, total_order_discount, total_discounted_order_amount,
                        total_tax_amount, total_shipping_amount, order_total, amount_paid,
                        fulfillment_groups, tenders, fees, shipping_charges, discounts,
                        billing_address, tracking_info, tracking_url,
                        account_id, email_id, remark, created_at, updated_at
                    FROM rei_orders
                    WHERE order_id = %s
                """
                cursor.execute(sql, (order_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                # 解析 JSON 字段
                order_data = dict(result)
                
                # 解析 JSON 字段
                json_fields = [
                    'retail_store_info', 'fulfillment_groups', 'tenders', 
                    'fees', 'shipping_charges', 'discounts', 'billing_address',
                    'tracking_info'
                ]
                
                for field in json_fields:
                    if order_data.get(field):
                        try:
                            order_data[field] = json.loads(order_data[field])
                        except:
                            pass
                
                return order_data
        
        except Exception as e:
            print(f"❌ 获取订单失败: {e}")
            traceback.print_exc()
            return None
