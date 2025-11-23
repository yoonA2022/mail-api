"""
REI 订单同步服务 - 优化版本
使用并发处理、连接池和批量操作提升性能
"""

from services.rei.email.rei_email_filter import ReiEmailFilter
from services.rei.email.rei_email_content import ReiEmailContentService
from services.rei.email.rei_order_parser import ReiOrderParser
from services.rei.api.rei_order_api_service import ReiOrderApiService
from services.rei.rei_order_service import ReiOrderService
from services.rei.rei_order_data_service import ReiOrderDataService
from services.rei.task_manager import get_task_manager
from typing import Dict, Any, List, Optional
import traceback
import asyncio
from imap_tools import MailBox
from concurrent.futures import ThreadPoolExecutor
import json


class ReiOrderSyncServiceOptimized:
    """REI 订单同步服务优化版"""
    
    # IMAP连接池
    _imap_connections = {}
    _connection_locks = {}
    
    @staticmethod
    async def sync_orders_for_account_async(
        account_id: int,
        limit: int = 100,
        skip_existing: bool = True,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步同步订单（优化版本，支持并发处理）
        
        Args:
            account_id: 邮箱账户ID
            limit: 最多处理多少封邮件
            skip_existing: 是否跳过已存在的订单
            task_id: 任务ID（用于进度更新）
        
        Returns:
            同步结果
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 [优化版] 开始同步订单 (账户ID: {account_id})")
            print(f"{'='*60}\n")
            
            task_manager = get_task_manager()
            
            results = {
                'emails_found': 0,
                'orders_synced': 0,
                'orders_skipped': 0,
                'orders_failed': 0,
                'synced_orders': [],
                'skipped_orders': [],
                'failed_orders': []
            }
            
            # 步骤1: 筛选邮件（使用异步方法避免阻塞）
            if task_id:
                task_manager.update_task_progress(task_id, 0, 100, "正在筛选邮件...", account_id=account_id)
            
            filter_result = await ReiEmailFilter.filter_rei_emails(
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
            
            emails = filter_result.get('data', [])
            results['emails_found'] = len(emails)
            
            if len(emails) == 0:
                return {
                    'success': True,
                    'account_id': account_id,
                    'message': '没有找到订单邮件',
                    'results': results
                }
            
            print(f"✅ 找到 {len(emails)} 封邮件\n")
            
            # 步骤2: 并发处理邮件
            if task_id:
                task_manager.update_task_progress(task_id, 10, 100, f"开始处理 {len(emails)} 封邮件...", account_id=account_id)
            
            # 使用信号量控制并发数（避免过多IMAP连接）
            semaphore = asyncio.Semaphore(5)  # 最多5个并发
            
            async def process_single_email(email, index):
                """处理单封邮件"""
                async with semaphore:
                    try:
                        email_id = email.get('id')
                        subject = email.get('subject', '')
                        order_number = email.get('order_number')  # 从筛选结果中获取订单号
                        
                        # 优化：先检查订单是否存在，避免不必要的IMAP连接
                        if skip_existing and order_number:
                            if await ReiOrderService.order_exists(order_number):
                                print(f"  ⏭️ 跳过已存在订单: {order_number}")
                                return {
                                    'success': True,
                                    'skipped': True,
                                    'order_number': order_number,
                                    'email_id': email_id,
                                    'reason': '订单已存在'
                                }
                        
                        # 订单不存在，才获取邮件内容（使用异步方法避免阻塞）
                        content_result = await ReiEmailContentService.get_email_content_by_id(
                            email_id=email_id,
                            account_id=account_id
                        )
                        
                        if not content_result.get('success'):
                            return {
                                'success': False,
                                'email_id': email_id,
                                'subject': subject,
                                'error': '获取邮件内容失败'
                            }
                        
                        html_content = content_result.get('data', {}).get('html_content', '')
                        
                        # 解析订单信息
                        email_info = ReiOrderParser.parse_order_from_html(html_content)
                        
                        if not email_info or not email_info.get('order_number'):
                            return {
                                'success': False,
                                'email_id': email_id,
                                'subject': subject,
                                'error': '无法提取订单号'
                            }
                        
                        order_number = email_info['order_number']
                        
                        # 保存订单（使用异步方法）
                        save_result = await ReiOrderDataService.save_email_parsed_order(
                            email_info=email_info,
                            account_id=account_id,
                            email_id=email_id
                        )
                        
                        if save_result.get('success'):
                            return {
                                'success': True,
                                'synced': True,
                                'order_number': order_number,
                                'email_id': email_id,
                                'db_id': save_result.get('db_id'),
                                'action': save_result.get('action')
                            }
                        else:
                            return {
                                'success': False,
                                'order_number': order_number,
                                'email_id': email_id,
                                'error': save_result.get('error', '保存失败')
                            }
                    
                    except Exception as e:
                        return {
                            'success': False,
                            'email_id': email.get('id'),
                            'subject': email.get('subject', ''),
                            'error': str(e)
                        }
                    finally:
                        # 更新进度
                        if task_id:
                            progress = 10 + int((index + 1) / len(emails) * 80)
                            task_manager.update_task_progress(
                                task_id, progress, 100,
                                f"已处理 {index + 1}/{len(emails)} 封邮件",
                                account_id=account_id
                            )
            
            # 并发处理所有邮件
            tasks = [process_single_email(email, i) for i, email in enumerate(emails)]
            process_results = await asyncio.gather(*tasks)
            
            # 汇总结果
            for result in process_results:
                if result.get('skipped'):
                    results['orders_skipped'] += 1
                    results['skipped_orders'].append({
                        'order_number': result['order_number'],
                        'email_id': result['email_id'],
                        'reason': result.get('reason', '')
                    })
                elif result.get('synced'):
                    results['orders_synced'] += 1
                    results['synced_orders'].append({
                        'order_number': result['order_number'],
                        'email_id': result['email_id'],
                        'db_id': result.get('db_id'),
                        'action': result.get('action')
                    })
                elif not result.get('success'):
                    results['orders_failed'] += 1
                    results['failed_orders'].append({
                        'email_id': result.get('email_id'),
                        'order_number': result.get('order_number'),
                        'error': result.get('error')
                    })
            
            # 完成
            if task_id:
                task_manager.update_task_progress(task_id, 100, 100, "同步完成！", account_id=account_id)
            
            # 通过WebSocket推送完成通知
            try:
                from services.websocket.websocket_service import WebSocketService
                await WebSocketService.push_to_account(account_id, {
                    'type': 'sync_complete',
                    'task_id': task_id,
                    'emails_found': results['emails_found'],
                    'orders_synced': results['orders_synced'],
                    'orders_skipped': results['orders_skipped'],
                    'orders_failed': results['orders_failed'],
                    'message': f"成功同步 {results['orders_synced']} 个订单"
                })
            except Exception as e:
                print(f"⚠️ 推送完成通知失败: {e}")
            
            print(f"\n{'='*60}")
            print(f"✅ 同步完成!")
            print(f"  📧 找到邮件: {results['emails_found']}")
            print(f"  💾 同步订单: {results['orders_synced']}")
            print(f"  ⏭️ 跳过订单: {results['orders_skipped']} (已存在，避免了 {results['orders_skipped']} 次IMAP连接)")
            print(f"  ❌ 失败订单: {results['orders_failed']}")
            if results['orders_skipped'] > 0:
                print(f"\n  跳过的订单号:")
                for skipped in results['skipped_orders'][:5]:  # 只显示前5个
                    print(f"    - {skipped['order_number']}")
                if len(results['skipped_orders']) > 5:
                    print(f"    ... 还有 {len(results['skipped_orders']) - 5} 个")
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
    async def refresh_order_details_async(
        account_id: int,
        limit: int = 100,
        task_id: Optional[str] = None,
        skip_status_codes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        异步刷新订单详情（优化版本，支持并发API调用）
        
        Args:
            account_id: 邮箱账户ID
            limit: 最多处理多少个订单
            task_id: 任务ID（用于进度更新）
            skip_status_codes: 需要跳过的订单状态代码列表（如 ['0006', '0001']）
        
        Returns:
            刷新结果
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 [优化版] 开始刷新订单详情 (账户ID: {account_id})")
            if skip_status_codes:
                print(f"   跳过状态: {', '.join(skip_status_codes)}")
            print(f"{'='*60}\n")
            
            task_manager = get_task_manager()
            
            results = {
                'orders_found': 0,
                'orders_updated': 0,
                'orders_failed': 0,
                'orders_skipped': 0,
                'updated_orders': [],
                'failed_orders': [],
                'skipped_orders': []
            }
            
            # 步骤1: 读取订单列表
            if task_id:
                task_manager.update_task_progress(task_id, 0, 100, "正在读取订单列表...", account_id=account_id)
            
            orders = ReiOrderService.get_orders_list(
                account_id=account_id,
                limit=limit
            )
            
            results['orders_found'] = len(orders)
            
            if len(orders) == 0:
                return {
                    'success': True,
                    'account_id': account_id,
                    'message': '没有找到订单',
                    'results': results
                }
            
            print(f"✅ 找到 {len(orders)} 个订单\n")
            
            # 步骤2: 并发调用API
            if task_id:
                task_manager.update_task_progress(task_id, 10, 100, f"开始处理 {len(orders)} 个订单...", account_id=account_id)
            
            # 使用信号量控制并发数（避免API限流）
            semaphore = asyncio.Semaphore(3)  # 最多3个并发API调用
            api_service = ReiOrderApiService()
            
            async def process_single_order(order, index):
                """处理单个订单"""
                async with semaphore:
                    try:
                        order_id = order.get('order_id')
                        email_id = order.get('email_id')
                        
                        # 检查是否需要跳过此订单（根据状态代码）
                        if skip_status_codes:
                            fulfillment_groups = order.get('fulfillment_groups')
                            if fulfillment_groups:
                                try:
                                    # 解析 JSON
                                    if isinstance(fulfillment_groups, str):
                                        fg_data = json.loads(fulfillment_groups)
                                    else:
                                        fg_data = fulfillment_groups
                                    
                                    # 检查所有配送组的状态
                                    should_skip = False
                                    for fg in fg_data:
                                        status = fg.get('status', {})
                                        summary_status_code = status.get('summaryStatusCode', '')
                                        
                                        if summary_status_code in skip_status_codes:
                                            should_skip = True
                                            break
                                    
                                    if should_skip:
                                        return {
                                            'success': True,
                                            'skipped': True,
                                            'order_id': order_id,
                                            'reason': f'订单状态为 {summary_status_code}，已跳过'
                                        }
                                except Exception as e:
                                    # JSON 解析失败，继续处理
                                    pass
                        
                        # 提取账单地址信息
                        billing_address = order.get('billing_address')
                        if not billing_address:
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': '缺少账单地址信息'
                            }
                        
                        # 解析账单地址
                        try:
                            billing_info = json.loads(billing_address)
                            billing_name = billing_info.get('name', '')
                            billing_zip_code = billing_info.get('zipCode', '')
                        except:
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': '账单地址格式错误'
                            }
                        
                        if not billing_name or not billing_zip_code:
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': '缺少账单姓名或邮编'
                            }
                        
                        # 提取姓氏
                        last_name = ReiOrderApiService.extract_last_name(billing_name)
                        if not last_name:
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': '无法提取姓氏'
                            }
                        
                        # 调用API
                        api_result = await api_service.fetch_order_details(
                            order_number=order_id,
                            last_name=last_name,
                            zip_code=billing_zip_code
                        )
                        
                        if not api_result.get('success'):
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': api_result.get('error', 'API调用失败')
                            }
                        
                        # 保存到数据库（从原订单数据中获取 user_id）
                        save_result = ReiOrderDataService.save_api_order_data(
                            order_data=api_result['order_data'],
                            user_id=order.get('user_id'),
                            account_id=account_id,
                            email_id=email_id
                        )
                        
                        if save_result.get('success'):
                            return {
                                'success': True,
                                'order_id': order_id,
                                'db_id': save_result.get('db_id'),
                                'action': save_result.get('action')
                            }
                        else:
                            return {
                                'success': False,
                                'order_id': order_id,
                                'error': save_result.get('error', '保存失败')
                            }
                    
                    except Exception as e:
                        return {
                            'success': False,
                            'order_id': order.get('order_id'),
                            'error': str(e)
                        }
                    finally:
                        # 更新进度
                        if task_id:
                            progress = 10 + int((index + 1) / len(orders) * 80)
                            task_manager.update_task_progress(
                                task_id, progress, 100,
                                f"已处理 {index + 1}/{len(orders)} 个订单",
                                account_id=account_id
                            )
            
            # 并发处理所有订单
            tasks = [process_single_order(order, i) for i, order in enumerate(orders)]
            process_results = await asyncio.gather(*tasks)
            
            # 汇总结果
            for result in process_results:
                if result.get('skipped'):
                    # 跳过的订单
                    results['orders_skipped'] += 1
                    results['skipped_orders'].append({
                        'order_id': result['order_id'],
                        'reason': result.get('reason')
                    })
                elif result.get('success'):
                    # 成功更新的订单
                    results['orders_updated'] += 1
                    results['updated_orders'].append({
                        'order_id': result['order_id'],
                        'db_id': result.get('db_id'),
                        'action': result.get('action')
                    })
                else:
                    # 失败的订单
                    results['orders_failed'] += 1
                    results['failed_orders'].append({
                        'order_id': result.get('order_id'),
                        'error': result.get('error')
                    })
            
            # 完成
            if task_id:
                task_manager.update_task_progress(task_id, 100, 100, "刷新完成！", account_id=account_id)
            
            # 通过WebSocket推送完成通知
            try:
                from services.websocket.websocket_service import WebSocketService
                await WebSocketService.push_to_account(account_id, {
                    'type': 'refresh_complete',
                    'task_id': task_id,
                    'orders_found': results['orders_found'],
                    'orders_updated': results['orders_updated'],
                    'orders_failed': results['orders_failed'],
                    'message': f"刷新完成：更新 {results['orders_updated']} 个订单"
                })
            except Exception as e:
                print(f"⚠️ 推送完成通知失败: {e}")
            
            print(f"{'='*60}")
            print(f"✅ 刷新完成!")
            print(f"  📋 找到订单: {results['orders_found']}")
            print(f"  🔄 更新订单: {results['orders_updated']}")
            if results['orders_skipped'] > 0:
                print(f"  ⏭️  跳过订单: {results['orders_skipped']}")
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
    async def refresh_single_order_async(order_id: str) -> Dict[str, Any]:
        """
        刷新单个订单详情
        
        Args:
            order_id: 订单号
        
        Returns:
            刷新结果
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 开始刷新单个订单: {order_id}")
            print(f"{'='*60}\n")
            
            # 步骤1: 从数据库获取订单信息
            order_data = ReiOrderDataService.get_order_by_order_id(order_id)
            
            if not order_data:
                return {
                    'success': False,
                    'error': f'订单 {order_id} 不存在'
                }
            
            # 提取账单信息
            billing_address = order_data.get('billing_address')
            if not billing_address:
                return {
                    'success': False,
                    'error': '订单缺少账单地址信息'
                }
            
            # 提取姓名和邮编
            name = billing_address.get('name') or f"{billing_address.get('firstName', '')} {billing_address.get('lastName', '')}".strip()
            zip_code = billing_address.get('zipCode') or billing_address.get('postalCode')
            
            if not name or not zip_code:
                return {
                    'success': False,
                    'error': '订单缺少必要的账单信息（姓名或邮编）'
                }
            
            # 提取姓氏
            from services.rei.api.rei_order_api_service import ReiOrderApiService
            last_name = ReiOrderApiService.extract_last_name(name)
            
            print(f"📋 订单信息:")
            print(f"   订单号: {order_id}")
            print(f"   姓名: {name}")
            print(f"   姓氏: {last_name}")
            print(f"   邮编: {zip_code}")
            
            # 步骤2: 调用 REI API 获取最新订单数据
            print(f"\n🌐 调用 REI API 获取订单详情...")
            
            # 创建 API 服务实例并调用
            api_service = ReiOrderApiService()
            api_result = await api_service.fetch_order_details(
                order_number=order_id,
                last_name=last_name,
                zip_code=zip_code
            )
            
            if not api_result.get('success'):
                return {
                    'success': False,
                    'error': api_result.get('error', 'API调用失败')
                }
            
            order_detail = api_result.get('order_data')
            if not order_detail:
                return {
                    'success': False,
                    'error': 'API返回数据为空'
                }
            
            print(f"✅ 成功获取订单详情")
            
            # 步骤3: 更新到数据库
            print(f"\n💾 更新订单到数据库...")
            
            save_result = ReiOrderService.save_order(
                order_data=order_detail,
                user_id=order_data.get('user_id'),
                account_id=order_data.get('account_id'),
                email_id=order_data.get('email_id')
            )
            
            if save_result.get('success'):
                print(f"✅ 订单更新成功 (DB ID: {save_result.get('db_id')})")
                
                # 获取更新后的订单数据
                updated_order = ReiOrderDataService.get_order_by_order_id(order_id)
                
                return {
                    'success': True,
                    'message': f'订单 {order_id} 刷新成功',
                    'data': {
                        'order_id': order_id,
                        'db_id': save_result.get('db_id'),
                        'action': save_result.get('action'),
                        'order': updated_order
                    }
                }
            else:
                return {
                    'success': False,
                    'error': save_result.get('error', '保存失败')
                }
        
        except Exception as e:
            print(f"❌ 刷新单个订单失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
