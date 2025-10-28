"""
REI 订单同步服务
协调邮件筛选、信息提取、API调用和数据保存的完整流程
"""

from services.rei.email.rei_email_filter import ReiEmailFilter
from services.rei.email.rei_email_content import ReiEmailContentService
from services.rei.email.rei_order_parser import ReiOrderParser
from services.rei.api.rei_order_api_service import ReiOrderApiService
from services.rei.rei_order_service import ReiOrderService
from services.rei.rei_order_data_service import ReiOrderDataService
from typing import Dict, Any, List, Optional
import traceback
import asyncio


class ReiOrderSyncService:
    """REI 订单同步服务类"""
    
    @staticmethod
    async def refresh_order_details_for_account(
        account_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        为指定账户刷新订单详情（步骤2：调用API获取完整数据）
        
        流程:
        1. 从数据库读取订单列表
        2. 提取账单姓名和邮编
        3. 调用 REI API 获取完整订单数据
        4. 更新到数据库
        
        Args:
            account_id: 邮箱账户ID
            limit: 最多处理多少个订单
            
        Returns:
            {
                'success': True,
                'account_id': 1,
                'orders_found': 10,
                'orders_updated': 8,
                'orders_failed': 2,
                'results': [...]
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 开始刷新订单详情 (账户ID: {account_id})")
            print(f"{'='*60}\n")
            
            results = {
                'orders_found': 0,
                'orders_updated': 0,
                'orders_failed': 0,
                'updated_orders': [],
                'failed_orders': []
            }
            
            # ============================================
            # 步骤1: 从数据库读取订单列表
            # ============================================
            print(f"📋 步骤1: 从数据库读取订单...")
            
            orders = ReiOrderService.get_orders_list(
                account_id=account_id,
                limit=limit
            )
            
            results['orders_found'] = len(orders)
            print(f"   ✅ 找到 {len(orders)} 个订单\n")
            
            if len(orders) == 0:
                print(f"⚠️ 没有找到订单，刷新结束\n")
                return {
                    'success': True,
                    'account_id': account_id,
                    'message': '没有找到订单',
                    'results': results
                }
            
            # ============================================
            # 步骤2-4: 处理每个订单
            # ============================================
            print(f"🔄 步骤2-4: 调用API并更新订单详情...\n")
            
            api_service = ReiOrderApiService()
            
            for i, order in enumerate(orders, 1):
                order_id = order.get('order_id')
                email_id = order.get('email_id')
                
                print(f"[{i}/{len(orders)}] 处理订单: {order_id}")
                
                try:
                    # 提取账单地址信息
                    billing_address = order.get('billing_address')
                    if not billing_address:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': '缺少账单地址信息'
                        })
                        print(f"    ❌ 缺少账单地址信息\n")
                        continue
                    
                    # 解析账单地址JSON
                    import json
                    try:
                        billing_info = json.loads(billing_address)
                        billing_name = billing_info.get('name', '')
                        billing_zip_code = billing_info.get('zipCode', '')
                    except:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': '账单地址格式错误'
                        })
                        print(f"    ❌ 账单地址格式错误\n")
                        continue
                    
                    if not billing_name or not billing_zip_code:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': '缺少账单姓名或邮编'
                        })
                        print(f"    ❌ 缺少账单姓名或邮编\n")
                        continue
                    
                    # 提取姓氏
                    last_name = ReiOrderApiService.extract_last_name(billing_name)
                    
                    if not last_name:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': '无法提取姓氏'
                        })
                        print(f"    ❌ 无法提取姓氏\n")
                        continue
                    
                    print(f"    👤 账单姓名: {billing_name} (姓氏: {last_name})")
                    print(f"    📮 账单邮编: {billing_zip_code}")
                    
                    # 步骤3: 调用 REI API 获取完整订单数据
                    api_result = await api_service.fetch_order_details(
                        order_number=order_id,
                        last_name=last_name,
                        zip_code=billing_zip_code
                    )
                    
                    if not api_result.get('success'):
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': api_result.get('error', 'API调用失败')
                        })
                        print(f"    ❌ API调用失败: {api_result.get('error')}\n")
                        continue
                    
                    order_data = api_result['order_data']
                    
                    # 步骤4: 更新到数据库
                    save_result = ReiOrderDataService.save_api_order_data(
                        order_data=order_data,
                        account_id=account_id,
                        email_id=email_id
                    )
                    
                    if save_result.get('success'):
                        results['orders_updated'] += 1
                        results['updated_orders'].append({
                            'order_id': order_id,
                            'db_id': save_result.get('db_id'),
                            'action': save_result.get('action')
                        })
                        print(f"    ✅ 订单详情更新成功 ({save_result.get('action')})\n")
                    else:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_id': order_id,
                            'error': save_result.get('error', '保存失败')
                        })
                        print(f"    ❌ 保存失败: {save_result.get('error')}\n")
                
                except Exception as e:
                    results['orders_failed'] += 1
                    results['failed_orders'].append({
                        'order_id': order_id,
                        'error': str(e)
                    })
                    print(f"    ❌ 处理失败: {e}\n")
                    traceback.print_exc()
            
            # ============================================
            # 返回结果
            # ============================================
            print(f"{'='*60}")
            print(f"✅ 刷新完成!")
            print(f"  📋 找到订单: {results['orders_found']}")
            print(f"  🔄 更新订单: {results['orders_updated']}")
            print(f"  ❌ 失败订单: {results['orders_failed']}")
            print(f"{'='*60}\n")
            
            return {
                'success': True,
                'account_id': account_id,
                'message': f"刷新完成：更新 {results['orders_updated']} 个订单",
                'results': results
            }
        
        except Exception as e:
            print(f"❌ 刷新订单详情失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id
            }
    
    @staticmethod
    async def sync_orders_for_account(
        account_id: int,
        limit: int = 100,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        为指定账户同步订单（步骤1：只解析邮件保存基本信息）
        
        流程:
        1. 筛选 REI 订单邮件
        2. 从邮件中提取基本信息（订单号、地址、金额等）
        3. 保存到数据库（不调用API）
        
        Args:
            account_id: 邮箱账户ID
            limit: 最多处理多少封邮件
            skip_existing: 是否跳过已存在的订单
            
        Returns:
            {
                'success': True,
                'account_id': 1,
                'emails_found': 10,
                'orders_synced': 8,
                'orders_skipped': 2,
                'orders_failed': 0,
                'results': [...]
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始同步订单 (账户ID: {account_id})")
            print(f"{'='*60}\n")
            
            results = {
                'emails_found': 0,
                'orders_synced': 0,
                'orders_skipped': 0,
                'orders_failed': 0,
                'synced_orders': [],
                'skipped_orders': [],
                'failed_orders': []
            }
            
            # ============================================
            # 步骤1: 筛选 REI 订单邮件
            # ============================================
            print(f"📧 步骤1: 筛选 REI 订单邮件...")
            
            filter_result = ReiEmailFilter.filter_rei_emails(
                account_id=account_id,
                folder='INBOX',
                limit=limit
            )
            
            if not filter_result.get('success'):
                return {
                    'success': False,
                    'error': filter_result.get('error', '筛选邮件失败'),
                    'account_id': account_id
                }
            
            emails = filter_result.get('data', [])  # 修复：使用 'data' 而不是 'emails'
            results['emails_found'] = len(emails)
            
            print(f"   ✅ 找到 {len(emails)} 封 REI 订单邮件\n")
            
            if len(emails) == 0:
                print(f"⚠️ 没有找到订单邮件，同步结束\n")
                return {
                    'success': True,
                    'account_id': account_id,
                    'message': '没有找到订单邮件',
                    'results': results
                }
            
            # ============================================
            # 步骤2-3: 处理每封邮件（只解析保存基本信息）
            # ============================================
            print(f"🔄 步骤2-3: 解析邮件并保存基本订单信息...\n")
            
            for i, email in enumerate(emails, 1):
                email_id = email.get('id')
                subject = email.get('subject', '')
                
                print(f"[{i}/{len(emails)}] 处理邮件: {subject}")
                
                try:
                    # 步骤2: 获取邮件完整内容
                    content_result = ReiEmailContentService.get_email_content_by_id(
                        email_id=email_id,
                        account_id=account_id
                    )
                    
                    if not content_result.get('success'):
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'email_id': email_id,
                            'subject': subject,
                            'error': '获取邮件内容失败'
                        })
                        print(f"    ❌ 获取邮件内容失败\n")
                        continue
                    
                    # 从返回的 data 字段中获取 html_content
                    html_content = content_result.get('data', {}).get('html_content', '')
                    
                    # 步骤3: 从邮件中提取基本信息
                    email_info = ReiOrderParser.parse_order_from_html(html_content)
                    
                    if not email_info or not email_info.get('order_number'):
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'email_id': email_id,
                            'subject': subject,
                            'error': '无法从邮件中提取订单号'
                        })
                        print(f"    ❌ 无法提取订单号\n")
                        continue
                    
                    order_number = email_info['order_number']
                    billing_name = email_info.get('billing_name', '')
                    billing_zip_code = email_info.get('billing_zip_code', '')
                    
                    print(f"    📝 订单号: {order_number}")
                    print(f"    👤 账单姓名: {billing_name}")
                    print(f"    📮 账单邮编: {billing_zip_code}")
                    print(f"    💰 订单总额: ${email_info.get('total', 0)}")
                    
                    # 检查是否跳过已存在的订单
                    if skip_existing and ReiOrderService.order_exists(order_number):
                        results['orders_skipped'] += 1
                        results['skipped_orders'].append({
                            'order_number': order_number,
                            'email_id': email_id,
                            'reason': '订单已存在'
                        })
                        print(f"    ⏭️ 订单已存在，跳过\n")
                        continue
                    
                    # 保存邮件解析的基本订单信息到数据库
                    save_result = ReiOrderDataService.save_email_parsed_order(
                        email_info=email_info,
                        account_id=account_id,
                        email_id=email_id
                    )
                    
                    if save_result.get('success'):
                        results['orders_synced'] += 1
                        results['synced_orders'].append({
                            'order_number': order_number,
                            'email_id': email_id,
                            'db_id': save_result.get('db_id'),
                            'action': save_result.get('action')
                        })
                        print(f"    ✅ 订单保存成功 ({save_result.get('action')})\n")
                    else:
                        results['orders_failed'] += 1
                        results['failed_orders'].append({
                            'order_number': order_number,
                            'email_id': email_id,
                            'error': save_result.get('error', '保存失败')
                        })
                        print(f"    ❌ 保存失败: {save_result.get('error')}\n")
                
                except Exception as e:
                    results['orders_failed'] += 1
                    results['failed_orders'].append({
                        'email_id': email_id,
                        'subject': subject,
                        'error': str(e)
                    })
                    print(f"    ❌ 处理失败: {e}\n")
                    traceback.print_exc()
            
            # ============================================
            # 返回结果
            # ============================================
            print(f"{'='*60}")
            print(f"✅ 同步完成!")
            print(f"  📧 找到邮件: {results['emails_found']}")
            print(f"  💾 同步订单: {results['orders_synced']}")
            print(f"  ⏭️ 跳过订单: {results['orders_skipped']}")
            print(f"  ❌ 失败订单: {results['orders_failed']}")
            print(f"{'='*60}\n")
            
            return {
                'success': True,
                'account_id': account_id,
                'message': f"成功同步 {results['orders_synced']} 个订单",
                'results': results
            }
        
        except Exception as e:
            print(f"❌ 同步订单失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'account_id': account_id
            }
    
    @staticmethod
    async def sync_single_order(
        order_number: str,
        last_name: str,
        zip_code: str,
        account_id: Optional[int] = None,
        email_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        同步单个订单（直接使用订单号、姓氏、邮编）
        
        Args:
            order_number: 订单号
            last_name: 姓氏
            zip_code: 邮政编码
            account_id: 账户ID（可选）
            email_id: 邮件ID（可选）
            
        Returns:
            同步结果
        """
        try:
            print(f"\n🔄 同步单个订单: {order_number}")
            
            # 调用 API
            api_service = ReiOrderApiService()
            api_result = await api_service.fetch_order_details(
                order_number=order_number,
                last_name=last_name,
                zip_code=zip_code
            )
            
            if not api_result.get('success'):
                return {
                    'success': False,
                    'error': api_result.get('error', 'API调用失败'),
                    'order_number': order_number
                }
            
            # 保存到数据库
            save_result = ReiOrderService.save_order(
                order_data=api_result['order_data'],
                account_id=account_id,
                email_id=email_id
            )
            
            if save_result.get('success'):
                print(f"✅ 订单同步成功\n")
                return {
                    'success': True,
                    'order_number': order_number,
                    'action': save_result.get('action'),
                    'db_id': save_result.get('db_id')
                }
            else:
                return {
                    'success': False,
                    'error': save_result.get('error', '保存失败'),
                    'order_number': order_number
                }
        
        except Exception as e:
            print(f"❌ 同步订单失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'order_number': order_number
            }
