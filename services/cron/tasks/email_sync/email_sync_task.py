"""
邮件同步定时任务
负责定时从 IMAP 服务器同步邮件到本地数据库
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.imap.account import ImapAccountService
from services.imap.mail_service import MailService
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


class EmailSyncTask:
    """
    邮件同步任务
    
    功能：
    1. 获取所有启用自动同步的 IMAP 账户
    2. 依次同步每个账户的邮件
    3. 记录同步结果和统计信息
    4. 处理异常和错误
    """
    
    def __init__(self, **kwargs):
        """
        初始化任务
        
        Args:
            **kwargs: 任务参数
                - account_id: 可选，指定账户ID，如果不提供则同步所有账户
                - folder: 邮件文件夹，默认从账户配置读取，如果未配置则使用 'INBOX'
                - batch_size: 每批处理的邮件数量，默认从账户配置读取，如果未配置则使用 50
                - auto_sync_only: 是否只同步启用自动同步的账户，默认 True
        """
        self.account_id = kwargs.get('account_id')
        self.folder_override = kwargs.get('folder')  # 命令行覆盖的文件夹
        self.batch_size_override = kwargs.get('batch_size')  # 命令行覆盖的批量大小
        self.auto_sync_only = kwargs.get('auto_sync_only', True)
        
        logger.info("=" * 80)
        logger.info("📧 邮件同步任务初始化")
        logger.info(f"   参数: {kwargs}")
        logger.info("=" * 80)
    
    def run(self) -> Dict[str, Any]:
        """
        执行任务
        
        Returns:
            执行结果字典
        """
        start_time = datetime.now()
        logger.info("🚀 开始执行邮件同步任务")
        
        try:
            # 获取要同步的账户列表
            accounts = self._get_accounts_to_sync()
            
            if not accounts:
                logger.warning("⚠️ 没有找到需要同步的账户")
                return {
                    'success': True,
                    'message': '没有需要同步的账户',
                    'synced_accounts': 0,
                    'total_emails': 0,
                    'duration_seconds': 0
                }
            
            logger.info(f"📋 找到 {len(accounts)} 个账户需要同步")
            
            # 同步所有账户
            results = []
            total_emails = 0
            success_count = 0
            error_count = 0
            
            for account in accounts:
                try:
                    result = self._sync_account(account)
                    results.append(result)
                    
                    if result['success']:
                        success_count += 1
                        total_emails += result.get('synced_count', 0)
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"同步账户 {account['email']} 失败: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    logger.error(traceback.format_exc())
                    results.append({
                        'success': False,
                        'account_id': account['id'],
                        'account_email': account['email'],
                        'error': error_msg
                    })
            
            # 计算执行时长
            duration = (datetime.now() - start_time).total_seconds()
            
            # 汇总结果
            summary = {
                'success': error_count == 0,
                'message': f'同步完成: {success_count} 成功, {error_count} 失败',
                'synced_accounts': len(accounts),
                'success_accounts': success_count,
                'error_accounts': error_count,
                'total_emails': total_emails,
                'duration_seconds': duration,
                'results': results
            }
            
            logger.info("=" * 80)
            logger.info("✅ 邮件同步任务完成")
            logger.info(f"   同步账户: {len(accounts)} 个")
            logger.info(f"   成功: {success_count} 个")
            logger.info(f"   失败: {error_count} 个")
            logger.info(f"   同步邮件: {total_emails} 封")
            logger.info(f"   耗时: {duration:.2f} 秒")
            logger.info("=" * 80)
            
            return summary
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"邮件同步任务执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e),
                'duration_seconds': duration
            }
    
    def _get_accounts_to_sync(self) -> list:
        """
        获取需要同步的账户列表
        
        Returns:
            账户列表
        """
        try:
            # 如果指定了账户ID，只获取该账户
            if self.account_id:
                logger.info(f"📌 获取指定账户: ID={self.account_id}")
                account = ImapAccountService.get_account_by_id(
                    self.account_id,
                    include_password=True
                )
                return [account] if account else []
            
            # 获取所有账户
            logger.info("📌 获取所有账户")
            accounts = ImapAccountService.get_all_accounts(include_password=True)
            
            # 如果只同步启用自动同步的账户
            if self.auto_sync_only:
                original_count = len(accounts)
                accounts = [
                    acc for acc in accounts
                    if acc.get('auto_sync') == 1 and acc.get('status') == 1
                ]
                logger.info(f"   筛选启用自动同步的账户: {len(accounts)} 个 (总共 {original_count} 个)")
            
            return accounts
            
        except Exception as e:
            logger.error(f"❌ 获取账户列表失败: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _sync_account(self, account: Dict) -> Dict[str, Any]:
        """
        同步单个账户的邮件
        
        Args:
            account: 账户信息字典
            
        Returns:
            同步结果字典
        """
        account_id = account['id']
        account_email = account['email']
        
        # 从账户配置读取 folder 和 max_fetch，如果命令行有覆盖则使用命令行参数
        folder = self.folder_override if self.folder_override else account.get('folder', 'INBOX')
        batch_size = self.batch_size_override if self.batch_size_override else account.get('max_fetch', 50)
        
        logger.info("-" * 80)
        logger.info(f"📬 开始同步账户: {account_email} (ID: {account_id})")
        logger.info(f"   文件夹: {folder}")
        logger.info(f"   批量大小: {batch_size}")
        
        start_time = datetime.now()
        
        try:
            # 调用邮件服务同步
            result = MailService.sync_from_imap(
                account_id=account_id,
                folder=folder,
                batch_size=batch_size
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                synced_count = result.get('count', 0)
                logger.info(f"✅ 账户 {account_email} 同步成功")
                logger.info(f"   同步邮件: {synced_count} 封")
                logger.info(f"   文件夹: {folder}")
                logger.info(f"   耗时: {duration:.2f} 秒")
                
                # 更新账户的最后同步时间
                self._update_last_sync_time(account_id)
                
                return {
                    'success': True,
                    'account_id': account_id,
                    'account_email': account_email,
                    'folder': folder,
                    'batch_size': batch_size,
                    'synced_count': synced_count,
                    'duration_seconds': duration
                }
            else:
                error = result.get('error', '未知错误')
                logger.error(f"❌ 账户 {account_email} 同步失败: {error}")
                
                return {
                    'success': False,
                    'account_id': account_id,
                    'account_email': account_email,
                    'error': error,
                    'duration_seconds': duration
                }
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"同步账户异常: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'account_id': account_id,
                'account_email': account_email,
                'error': error_msg,
                'duration_seconds': duration
            }
    
    def _update_last_sync_time(self, account_id: int):
        """
        更新账户的最后同步时间
        
        Args:
            account_id: 账户ID
        """
        try:
            db = get_db_connection()
            with db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE imap_accounts
                    SET last_sync_time = %s
                    WHERE id = %s
                """, (datetime.now(), account_id))
                # commit 会在上下文管理器退出时自动执行
                logger.debug(f"✅ 更新账户 {account_id} 的最后同步时间")
        except Exception as e:
            logger.error(f"❌ 更新最后同步时间失败: {str(e)}")


def main():
    """
    主函数 - 用于命令行直接执行
    
    支持命令行参数：
    - --account-id: 指定账户ID
    - --folder: 指定文件夹
    - --batch-size: 每批处理的邮件数量
    - --all: 同步所有账户（包括未启用自动同步的）
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='邮件同步任务')
    parser.add_argument('--account-id', type=int, help='指定账户ID')
    parser.add_argument('--folder', type=str, default='INBOX', help='邮件文件夹')
    parser.add_argument('--batch-size', type=int, default=50, help='每批处理的邮件数量')
    parser.add_argument('--all', action='store_true', help='同步所有账户（忽略 auto_sync 状态）')
    parser.add_argument('--auto-sync-only', action='store_true', default=True, 
                        help='只同步启用自动同步的账户（默认）')
    
    args = parser.parse_args()
    
    # 构建任务参数
    task_params = {
        'folder': args.folder,
        'batch_size': args.batch_size,
        'auto_sync_only': not args.all
    }
    
    if args.account_id:
        task_params['account_id'] = args.account_id
    
    # 执行任务
    task = EmailSyncTask(**task_params)
    result = task.run()
    
    # 输出结果
    print("\n" + "=" * 80)
    print("📊 执行结果:")
    print(f"   状态: {'成功' if result['success'] else '失败'}")
    print(f"   消息: {result['message']}")
    if 'total_emails' in result:
        print(f"   同步邮件: {result['total_emails']} 封")
    print(f"   耗时: {result['duration_seconds']:.2f} 秒")
    print("=" * 80)
    
    # 返回退出码
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
