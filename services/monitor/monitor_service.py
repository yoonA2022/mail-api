"""
监控服务 - 简洁版
负责：后台检测新邮件、自动推送
"""

import asyncio
from services.imap.mail_service import MailService
from services.websocket.websocket_service import WebSocketService

class MonitorService:
    """监控服务 - 后台检测新邮件并推送"""
    
    _is_running = False
    _check_interval = 15  # 检测间隔（秒）
    
    @classmethod
    async def start(cls):
        """
        启动监控服务
        
        工作流程：
        1. 获取所有在线账户
        2. 检测每个账户是否有新邮件
        3. 如果有新邮件，同步并推送到前端
        4. 等待15秒后继续
        """
        cls._is_running = True
        print(f"🌐 监控服务启动成功！检测间隔: {cls._check_interval}秒")
        
        while cls._is_running:
            try:
                # 1. 获取所有在线账户
                online_accounts = WebSocketService.get_online_accounts()
                
                if not online_accounts:
                    # 没有在线账户，等待1秒
                    await asyncio.sleep(1)
                    continue
                
                # 2. 并发检测所有账户
                tasks = []
                for account_id in online_accounts:
                    task = asyncio.create_task(cls._check_account(account_id))
                    tasks.append(task)
                
                # 等待所有检测完成
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # 3. 等待检测间隔
                await asyncio.sleep(cls._check_interval)
            
            except asyncio.CancelledError:
                print("⏹️ 监控服务被取消")
                break
            
            except Exception as e:
                print(f"❌ 监控服务异常: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒再继续
        
        print("⏹️ 监控服务已停止")
    
    @classmethod
    async def stop(cls):
        """停止监控服务"""
        cls._is_running = False
    
    @classmethod
    async def _check_account(cls, account_id: int, folder: str = 'INBOX'):
        """
        检测单个账户是否有新邮件
        
        Args:
            account_id: 账户ID
            folder: 文件夹名称
        """
        try:
            # 1. 检测是否有新邮件
            result = MailService.check_new_mail(account_id, folder)
            
            if not result.get('has_new'):
                return  # 没有新邮件
            
            new_count = result.get('new_count', 0)
            print(f"📬 检测到账户 {account_id} 有 {new_count} 封新邮件")
            
            # 2. 同步新邮件
            sync_result = MailService.sync_from_imap(account_id, folder)
            
            if not sync_result['success']:
                print(f"❌ 同步新邮件失败: {sync_result.get('error')}")
                return
            
            # 3. 获取新邮件列表（最新的N封）
            mail_list = MailService.get_mail_list(account_id, folder, limit=new_count, offset=0)
            
            if not mail_list['success']:
                print(f"❌ 获取新邮件列表失败: {mail_list.get('error')}")
                return
            
            # 4. 推送到前端
            await WebSocketService.push_new_mail(account_id, mail_list['data'])
        
        except Exception as e:
            print(f"❌ 检测账户 {account_id} 失败: {e}")
