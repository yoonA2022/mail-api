"""
订单同步定时任务
自动从邮件中提取订单信息并同步到数据库
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import traceback
import asyncio

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.imap.account import ImapAccountService
from services.rei.rei_order_sync_service_optimized import ReiOrderSyncServiceOptimized
from config.database import get_db_connection

# 配置日志 - 使用固定文件名方便读取
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# 固定日志文件名：task.log
log_file = log_dir / "task.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class OrderSyncTask:
    """订单同步任务"""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        初始化订单同步任务
        
        Args:
            parameters: 任务参数
                - limit: 每个账户最多处理多少封邮件 (默认: 100)
                - skip_existing: 是否跳过已存在的订单 (默认: True)
                - auto_sync_only: 是否只同步启用自动同步的账户 (默认: True)
                - account_ids: 指定要同步的账户ID列表 (可选)
        """
        self.parameters = parameters or {}
        self.limit = self.parameters.get('limit', 100)
        self.skip_existing = self.parameters.get('skip_existing', True)
        self.auto_sync_only = self.parameters.get('auto_sync_only', True)
        self.account_ids = self.parameters.get('account_ids', None)
        
        logger.info("=" * 80)
        logger.info("📦 订单同步任务初始化")
        logger.info(f"   参数: {self.parameters}")
        logger.info("=" * 80)
    
    def get_accounts_to_sync(self) -> List[Dict[str, Any]]:
        """
        获取需要同步的账户列表
        
        Returns:
            账户列表
        """
        logger.info("📌 获取所有账户")
        
        # 获取所有账户
        accounts = ImapAccountService.get_all_accounts(include_password=False)
        
        # 如果指定了账户ID，只同步指定的账户
        if self.account_ids:
            accounts = [acc for acc in accounts if acc['id'] in self.account_ids]
            logger.info(f"   筛选指定账户: {len(accounts)} 个")
        # 如果启用了 auto_sync_only，只同步启用自动同步的账户
        elif self.auto_sync_only:
            accounts = [acc for acc in accounts if acc.get('auto_sync', False)]
            logger.info(f"   筛选启用自动同步的账户: {len(accounts)} 个 (总共 {len(ImapAccountService.get_all_accounts())} 个)")
        
        return accounts
    
    async def sync_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步单个账户的订单
        
        Args:
            account: 账户信息
            
        Returns:
            同步结果
        """
        account_id = account['id']
        account_email = account['email']
        
        logger.info("-" * 80)
        logger.info(f"📦 开始同步账户: {account_email} (ID: {account_id})")
        
        start_time = datetime.now()
        
        try:
            # 调用优化版订单同步服务
            result = await ReiOrderSyncServiceOptimized.sync_orders_for_account_async(
                account_id=account_id,
                limit=self.limit,
                skip_existing=self.skip_existing,
                task_id=None  # 定时任务不需要任务ID
            )
            
            # 计算耗时
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.get('success'):
                results = result.get('results', {})
                orders_synced = results.get('orders_synced', 0)
                orders_skipped = results.get('orders_skipped', 0)
                orders_failed = results.get('orders_failed', 0)
                
                logger.info(f"✅ 账户 {account_email} 同步成功")
                logger.info(f"   同步订单: {orders_synced} 个")
                logger.info(f"   跳过订单: {orders_skipped} 个")
                logger.info(f"   失败订单: {orders_failed} 个")
                logger.info(f"   耗时: {duration:.2f} 秒")
                
                return {
                    'success': True,
                    'account_id': account_id,
                    'account_email': account_email,
                    'orders_synced': orders_synced,
                    'orders_skipped': orders_skipped,
                    'orders_failed': orders_failed,
                    'duration': duration
                }
            else:
                error = result.get('error', '未知错误')
                logger.error(f"❌ 账户 {account_email} 同步失败: {error}")
                
                return {
                    'success': False,
                    'account_id': account_id,
                    'account_email': account_email,
                    'error': error,
                    'duration': duration
                }
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"❌ 账户 {account_email} 同步异常: {error_msg}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'account_id': account_id,
                'account_email': account_email,
                'error': error_msg,
                'duration': duration
            }
    
    async def run(self) -> Dict[str, Any]:
        """
        执行订单同步任务
        
        Returns:
            任务执行结果
        """
        logger.info("🚀 开始执行订单同步任务")
        
        start_time = datetime.now()
        
        try:
            # 获取需要同步的账户
            accounts = self.get_accounts_to_sync()
            
            if not accounts:
                logger.warning("⚠️ 没有找到需要同步的账户")
                return {
                    'success': True,
                    'message': '没有需要同步的账户',
                    'accounts_total': 0,
                    'accounts_success': 0,
                    'accounts_failed': 0,
                    'orders_synced': 0
                }
            
            logger.info(f"📋 找到 {len(accounts)} 个账户需要同步")
            
            # 同步所有账户
            results = []
            for account in accounts:
                result = await self.sync_account(account)
                results.append(result)
            
            # 统计结果
            accounts_success = sum(1 for r in results if r['success'])
            accounts_failed = sum(1 for r in results if not r['success'])
            orders_synced = sum(r.get('orders_synced', 0) for r in results)
            
            # 计算总耗时
            total_duration = (datetime.now() - start_time).total_seconds()
            
            # 判断任务是否成功
            task_success = accounts_failed == 0
            
            logger.info("=" * 80)
            logger.info("📊 执行结果:")
            logger.info(f"   状态: {'成功' if task_success else '失败'}")
            logger.info(f"   消息: 同步完成: {accounts_success} 成功, {accounts_failed} 失败")
            logger.info(f"   同步订单: {orders_synced} 个")
            logger.info(f"   耗时: {total_duration:.2f} 秒")
            logger.info("=" * 80)
            
            return {
                'success': task_success,
                'message': f'同步完成: {accounts_success} 成功, {accounts_failed} 失败',
                'accounts_total': len(accounts),
                'accounts_success': accounts_success,
                'accounts_failed': accounts_failed,
                'orders_synced': orders_synced,
                'duration': total_duration,
                'details': results
            }
            
        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logger.error(f"❌ 订单同步任务执行失败: {error_msg}")
            logger.error(traceback.format_exc())
            
            logger.info("=" * 80)
            logger.info("📊 执行结果:")
            logger.info(f"   状态: 失败")
            logger.info(f"   错误: {error_msg}")
            logger.info(f"   耗时: {total_duration:.2f} 秒")
            logger.info("=" * 80)
            
            return {
                'success': False,
                'error': error_msg,
                'duration': total_duration
            }


async def main():
    """主函数"""
    import sys
    import json
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='订单同步任务')
    parser.add_argument('--limit', type=int, default=100, help='每个账户最多处理多少封邮件')
    
    # 布尔值参数：使用 store_true/store_false，不需要传递值
    parser.add_argument('--skip_existing', dest='skip_existing', action='store_true', default=True, help='跳过已存在的订单')
    parser.add_argument('--no_skip_existing', dest='skip_existing', action='store_false', help='不跳过已存在的订单')
    
    parser.add_argument('--auto_sync_only', dest='auto_sync_only', action='store_true', default=True, help='只同步启用自动同步的账户')
    parser.add_argument('--no_auto_sync_only', dest='auto_sync_only', action='store_false', help='同步所有账户')
    
    parser.add_argument('--account_ids', type=str, default=None, help='指定要同步的账户ID列表（JSON格式）')
    
    # 尝试解析参数
    try:
        args, unknown = parser.parse_known_args()
        
        # 构建参数字典
        parameters = {
            'limit': args.limit,
            'skip_existing': args.skip_existing,
            'auto_sync_only': args.auto_sync_only
        }
        
        # 解析 account_ids（如果提供）
        if args.account_ids:
            try:
                parameters['account_ids'] = json.loads(args.account_ids)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ 无法解析 account_ids: {args.account_ids}")
        
        logger.info(f"✅ 参数解析成功: {parameters}")
        
    except Exception as e:
        logger.warning(f"⚠️ 参数解析失败: {str(e)}，使用默认参数")
        parameters = {
            'limit': 100,
            'skip_existing': True,
            'auto_sync_only': True
        }
    
    # 创建并执行任务
    task = OrderSyncTask(parameters)
    result = await task.run()
    
    # 根据结果设置退出码
    exit_code = 0 if result['success'] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
