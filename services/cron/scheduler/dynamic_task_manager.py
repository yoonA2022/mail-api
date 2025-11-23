"""
动态任务管理器
负责在运行时动态添加/移除调度器中的任务
"""

import logging
from typing import Optional, Dict, Any
from config.database import DatabaseConnection

logger = logging.getLogger(__name__)


class DynamicTaskManager:
    """动态任务管理器 - 在运行时管理调度器中的任务"""
    
    def __init__(self, scheduler_manager):
        """
        初始化动态任务管理器
        
        Args:
            scheduler_manager: CronSchedulerManager 实例
        """
        self.scheduler = scheduler_manager
    
    async def activate_task(self, task_id: int) -> Dict[str, Any]:
        """
        激活任务 - 将任务添加到调度器
        
        Args:
            task_id: 任务ID
            
        Returns:
            操作结果
        """
        try:
            logger.info(f"🔄 激活任务: task_id={task_id}")
            
            # 从数据库获取任务详情
            task = self._get_task_from_db(task_id)
            if not task:
                return {
                    'success': False,
                    'message': f'任务不存在: task_id={task_id}'
                }
            
            # 检查任务是否已在调度器中
            if task_id in self.scheduler.task_registry:
                logger.warning(f"⚠️ 任务已在调度器中: task_id={task_id}")
                return {
                    'success': True,
                    'message': f'任务已在调度器中',
                    'task_name': task['name']
                }
            
            # 添加任务到调度器
            await self.scheduler.add_task(
                task_id=task['id'],
                task_name=task['name'],
                cron_expression=task['cron_expression'],
                command=task['command'],
                parameters=task['parameters'],
                working_directory=task['working_directory'],
                environment_vars=task['environment_vars'],
                timeout_seconds=task['timeout_seconds'],
                max_retries=task['max_retries'],
                retry_interval=task['retry_interval'],
                timezone=task['timezone'] or 'Asia/Shanghai'
            )
            
            logger.info(f"✅ 任务已添加到调度器: {task['name']} [ID={task_id}]")
            
            # 获取下次执行时间
            task_info = self.scheduler.get_task_info(task_id)
            next_run_time = task_info.get('next_run_time') if task_info else None
            
            return {
                'success': True,
                'message': f'任务已激活并添加到调度器',
                'task_id': task_id,
                'task_name': task['name'],
                'next_run_time': next_run_time.strftime('%Y-%m-%d %H:%M:%S') if next_run_time else None
            }
            
        except Exception as e:
            logger.error(f"❌ 激活任务失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'激活任务失败: {str(e)}'
            }
    
    async def deactivate_task(self, task_id: int) -> Dict[str, Any]:
        """
        取消激活任务 - 从调度器移除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            操作结果
        """
        try:
            logger.info(f"🔄 取消激活任务: task_id={task_id}")
            
            # 从调度器移除任务
            success = await self.scheduler.remove_task(task_id)
            
            if success:
                logger.info(f"✅ 任务已从调度器移除: task_id={task_id}")
                return {
                    'success': True,
                    'message': f'任务已取消激活并从调度器移除',
                    'task_id': task_id
                }
            else:
                logger.warning(f"⚠️ 任务不在调度器中: task_id={task_id}")
                return {
                    'success': True,
                    'message': f'任务不在调度器中',
                    'task_id': task_id
                }
            
        except Exception as e:
            logger.error(f"❌ 取消激活任务失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'取消激活任务失败: {str(e)}'
            }
    
    def _get_task_from_db(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取任务详情
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务详情字典，如果不存在返回 None
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                query = """
                    SELECT id, name, cron_expression, command, parameters,
                           working_directory, environment_vars, timeout_seconds,
                           max_retries, retry_interval, timezone, is_active, status
                    FROM cron_tasks
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(query, (task_id,))
                task = cursor.fetchone()
                return task
                
        except Exception as e:
            logger.error(f"❌ 从数据库获取任务失败: {str(e)}")
            return None
    
    async def reload_task(self, task_id: int) -> Dict[str, Any]:
        """
        重新加载任务 - 先移除再添加（用于更新任务配置）
        
        Args:
            task_id: 任务ID
            
        Returns:
            操作结果
        """
        try:
            logger.info(f"🔄 重新加载任务: task_id={task_id}")
            
            # 先移除任务
            await self.scheduler.remove_task(task_id)
            
            # 重新添加任务
            result = await self.activate_task(task_id)
            
            if result['success']:
                logger.info(f"✅ 任务重新加载成功: task_id={task_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 重新加载任务失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'重新加载任务失败: {str(e)}'
            }
    
    def get_active_tasks_count(self) -> int:
        """
        获取调度器中的活跃任务数量
        
        Returns:
            任务数量
        """
        return len(self.scheduler.task_registry)
    
    def is_task_active(self, task_id: int) -> bool:
        """
        检查任务是否在调度器中
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否在调度器中
        """
        return task_id in self.scheduler.task_registry
