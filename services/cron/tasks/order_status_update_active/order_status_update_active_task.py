"""
订单状态更新定时任务（仅活跃订单）
跳过已签收（0006）和取消发货（0001）的订单
"""

import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import traceback

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.rei.rei_order_sync_service_optimized import ReiOrderSyncServiceOptimized
from services.imap.account import ImapAccountService

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


class OrderStatusUpdateActiveTask:
    """
    订单状态更新任务（仅活跃订单）
    
    功能：
    1. 获取所有邮箱账户
    2. 调用现有的刷新订单详情方法
    3. 跳过已签收（0006）和取消发货（0001）的订单
    4. 记录执行结果和统计信息
    """
    
    # 需要跳过的订单状态代码
    SKIP_STATUS_CODES = ['0006', '0001']  # 0006=已签收, 0001=取消发货
    
    def __init__(self, **kwargs):
        """
        初始化任务
        
        Args:
            **kwargs: 任务参数
                - account_id: 可选，指定账户ID，如果不提供则更新所有账户
                - limit: 每个账户处理的订单数量限制，默认 100
        """
        self.account_id = kwargs.get('account_id')
        self.limit = kwargs.get('limit', 100)
        
        logger.info("=" * 80)
        logger.info("🔄 订单状态更新任务（仅活跃订单）初始化")
        logger.info(f"   参数: {kwargs}")
        logger.info(f"   跳过状态: {', '.join(self.SKIP_STATUS_CODES)} (已签收、取消发货)")
        logger.info("=" * 80)
    
    def run(self) -> Dict[str, Any]:
        """
        执行任务（同步方法，内部调用异步）
        
        Returns:
            执行结果字典
        """
        return asyncio.run(self._run_async())
    
    async def _run_async(self) -> Dict[str, Any]:
        """
        异步执行任务
        
        Returns:
            执行结果字典
        """
        start_time = datetime.now()
        logger.info("🚀 开始执行订单状态更新任务（仅活跃订单）")
        
        try:
            # 获取要处理的账户列表
            if self.account_id:
                # 指定账户
                account = ImapAccountService.get_account_by_id(self.account_id)
                if not account:
                    logger.error(f"❌ 账户不存在: ID={self.account_id}")
                    return {
                        'success': False,
                        'message': f'账户不存在: ID={self.account_id}',
                        'duration_seconds': 0
                    }
                accounts = [account]
            else:
                # 所有账户
                accounts = ImapAccountService.get_all_accounts()
            
            if not accounts:
                logger.warning("⚠️ 没有找到邮箱账户")
                return {
                    'success': True,
                    'message': '没有找到邮箱账户',
                    'processed_accounts': 0,
                    'total_orders_found': 0,
                    'total_orders_updated': 0,
                    'total_orders_skipped': 0,
                    'duration_seconds': 0
                }
            
            logger.info(f"📋 找到 {len(accounts)} 个账户需要处理")
            
            # 处理所有账户
            total_orders_found = 0
            total_orders_updated = 0
            total_orders_failed = 0
            total_orders_skipped = 0
            
            for account in accounts:
                account_id = account['id']
                email = account['email']
                
                logger.info(f"\n{'='*60}")
                logger.info(f"📬 处理账户: {email} (ID: {account_id})")
                logger.info(f"{'='*60}")
                
                try:
                    # 调用现有的刷新订单详情方法（带状态过滤）
                    result = await ReiOrderSyncServiceOptimized.refresh_order_details_async(
                        account_id=account_id,
                        limit=self.limit,
                        task_id=None,
                        skip_status_codes=self.SKIP_STATUS_CODES
                    )
                    
                    if result.get('success'):
                        results = result.get('results', {})
                        orders_found = results.get('orders_found', 0)
                        orders_updated = results.get('orders_updated', 0)
                        orders_failed = results.get('orders_failed', 0)
                        orders_skipped = results.get('orders_skipped', 0)
                        
                        total_orders_found += orders_found
                        total_orders_updated += orders_updated
                        total_orders_failed += orders_failed
                        total_orders_skipped += orders_skipped
                        
                        logger.info(f"✅ 账户处理完成:")
                        logger.info(f"   找到订单: {orders_found}")
                        logger.info(f"   更新成功: {orders_updated}")
                        logger.info(f"   跳过订单: {orders_skipped} (已签收/取消)")
                        logger.info(f"   更新失败: {orders_failed}")
                    else:
                        logger.error(f"❌ 账户处理失败: {result.get('error', '未知错误')}")
                        
                except Exception as e:
                    logger.error(f"❌ 处理账户 {email} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            # 计算执行时长
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"\n{'='*60}")
            logger.info("✅ 所有账户处理完成")
            logger.info(f"   处理账户: {len(accounts)}")
            logger.info(f"   找到订单: {total_orders_found}")
            logger.info(f"   更新成功: {total_orders_updated}")
            logger.info(f"   跳过订单: {total_orders_skipped} (已签收/取消)")
            logger.info(f"   更新失败: {total_orders_failed}")
            logger.info(f"   耗时: {duration:.2f} 秒")
            logger.info(f"{'='*60}")
            
            return {
                'success': True,
                'message': f'成功处理 {len(accounts)} 个账户',
                'processed_accounts': len(accounts),
                'total_orders_found': total_orders_found,
                'total_orders_updated': total_orders_updated,
                'total_orders_skipped': total_orders_skipped,
                'total_orders_failed': total_orders_failed,
                'duration_seconds': duration
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ 任务执行失败: {error_msg}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'message': error_msg,
                'duration_seconds': duration
            }


def main():
    """
    命令行入口
    
    支持参数:
    - --account-id: 指定账户ID
    - --limit: 每个账户处理的订单数量限制
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='订单状态更新任务（仅活跃订单）')
    parser.add_argument('--account-id', type=int, help='指定账户ID')
    parser.add_argument('--limit', type=int, default=100, help='每个账户处理的订单数量限制')
    
    args = parser.parse_args()
    
    # 构建任务参数
    task_params = {
        'limit': args.limit
    }
    
    if args.account_id:
        task_params['account_id'] = args.account_id
    
    # 执行任务
    task = OrderStatusUpdateActiveTask(**task_params)
    result = task.run()
    
    # 输出结果
    print("\n" + "=" * 80)
    print("📊 执行结果:")
    print(f"   状态: {'成功' if result['success'] else '失败'}")
    print(f"   消息: {result['message']}")
    if 'total_orders_updated' in result:
        print(f"   更新订单: {result['total_orders_updated']}")
    if 'total_orders_skipped' in result:
        print(f"   跳过订单: {result['total_orders_skipped']} (已签收/取消)")
    print(f"   耗时: {result['duration_seconds']:.2f} 秒")
    print("=" * 80)
    
    # 返回退出码
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
