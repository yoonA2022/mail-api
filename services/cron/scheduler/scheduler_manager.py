"""
定时任务调度器管理器
支持高并发、容灾、不阻塞主线程
"""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from croniter import croniter

from config.database import DatabaseConnection
from .task_executor import TaskExecutor
from .task_monitor import TaskMonitor

logger = logging.getLogger(__name__)


class CronSchedulerManager:
    """
    定时任务调度器管理器
    
    特性：
    1. 基于 APScheduler 的异步调度
    2. 支持高并发任务执行（线程池隔离）
    3. 容灾机制（任务失败自动重试、异常捕获）
    4. 不阻塞主线程（异步执行）
    5. 实时监控和日志记录
    6. 动态任务管理（增删改查）
    """
    
    _instance: Optional['CronSchedulerManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self, max_workers: int = 20):
        """
        初始化调度器
        
        Args:
            max_workers: 最大工作线程数，用于并发执行任务
        """
        # APScheduler 调度器（异步模式）
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            executors={
                'default': ThreadPoolExecutor(max_workers=max_workers)
            },
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 3,  # 同一任务最多同时运行3个实例
                'misfire_grace_time': 60  # 错过任务的宽限时间（秒）
            }
        )
        
        # 任务执行器
        self.executor = TaskExecutor()
        
        # 任务监控器
        self.monitor = TaskMonitor()
        
        # 任务注册表（task_id -> job_id 映射）
        self.task_registry: Dict[int, str] = {}
        
        # 后台任务跟踪（用于优雅关闭）
        self.background_tasks: set = set()
        
        # 运行状态
        self.is_running = False
        
        # 注册事件监听器
        self._register_event_listeners()
        
        logger.info("🚀 定时任务调度器初始化完成")
    
    @classmethod
    async def get_instance(cls, max_workers: int = 20) -> 'CronSchedulerManager':
        """
        获取调度器单例
        
        Args:
            max_workers: 最大工作线程数
            
        Returns:
            调度器实例
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_workers)
        return cls._instance
    
    def _register_event_listeners(self):
        """注册 APScheduler 事件监听器"""
        
        # 任务执行成功
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )
        
        # 任务执行失败
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )
        
        # 任务错过执行
        self.scheduler.add_listener(
            self._on_job_missed,
            EVENT_JOB_MISSED
        )
    
    def _on_job_executed(self, event):
        """任务执行成功回调"""
        logger.info(f"✅ 任务执行成功: job_id={event.job_id}")
        self.monitor.record_success(event.job_id)
    
    def _on_job_error(self, event):
        """任务执行失败回调"""
        logger.error(f"❌ 任务执行失败: job_id={event.job_id}, exception={event.exception}")
        self.monitor.record_error(event.job_id, str(event.exception))
    
    def _on_job_missed(self, event):
        """任务错过执行回调"""
        logger.warning(f"⚠️ 任务错过执行: job_id={event.job_id}")
        self.monitor.record_missed(event.job_id)
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("⚠️ 调度器已在运行中")
            return
        
        try:
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            # 从数据库加载所有激活的任务
            await self._load_tasks_from_db()
            
            logger.info("🎯 定时任务调度器启动成功")
        except Exception as e:
            logger.error(f"❌ 启动调度器失败: {str(e)}")
            raise
    
    async def stop(self):
        """停止调度器（优雅关闭）"""
        if not self.is_running:
            logger.warning("⚠️ 调度器未运行")
            return
        
        try:
            logger.info("⏹️ 正在停止调度器...")
            
            # 1. 取消所有后台任务
            if self.background_tasks:
                logger.info(f"🔄 取消 {len(self.background_tasks)} 个后台任务...")
                for task in self.background_tasks:
                    if not task.done():
                        task.cancel()
                
                # 等待所有任务取消完成（最多等待5秒）
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.background_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                    logger.info("✅ 后台任务已全部取消")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ 部分后台任务取消超时")
            
            # 2. 关闭调度器（不等待任务完成，因为已经取消了）
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            
            logger.info("⏹️ 定时任务调度器已停止")
            
        except Exception as e:
            logger.error(f"❌ 调度器停止失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _load_tasks_from_db(self):
        """从数据库加载所有激活的任务"""
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                # 查询所有激活且未删除的任务
                query = """
                    SELECT id, name, cron_expression, command, parameters,
                           working_directory, environment_vars, timeout_seconds,
                           max_retries, retry_interval, timezone
                    FROM cron_tasks
                    WHERE is_active = 1 AND deleted_at IS NULL
                """
                
                cursor.execute(query)
                tasks = cursor.fetchall()
                
                if not tasks:
                    logger.info("📭 没有需要加载的定时任务")
                    return
                
                # 添加所有任务到调度器
                loaded_count = 0
                for task in tasks:
                    try:
                        await self.add_task(
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
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"❌ 加载任务失败 [ID={task.get('id', 'unknown')}]: {str(e)}")
                
                logger.info(f"📥 成功加载 {loaded_count}/{len(tasks)} 个定时任务")
                
        except Exception as e:
            logger.error(f"❌ 从数据库加载任务失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def add_task(
        self,
        task_id: int,
        task_name: str,
        cron_expression: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_interval: int = 60,
        timezone: str = 'Asia/Shanghai'
    ) -> str:
        """
        添加定时任务到调度器
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            cron_expression: Cron 表达式
            command: 执行命令
            parameters: 任务参数
            working_directory: 工作目录
            environment_vars: 环境变量
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            timezone: 时区
            
        Returns:
            job_id: APScheduler 任务ID
        """
        try:
            # 验证 Cron 表达式
            if not self._validate_cron_expression(cron_expression):
                raise ValueError(f"无效的 Cron 表达式: {cron_expression}")
            
            # 生成唯一的 job_id
            job_id = f"cron_task_{task_id}_{uuid.uuid4().hex[:8]}"
            
            # 解析 Cron 表达式（支持6位格式：秒 分 时 日 月 星期）
            cron_parts = cron_expression.strip().split()
            if len(cron_parts) == 6:
                # 6位格式：秒 分 时 日 月 星期
                # APScheduler 需要分别指定每个字段
                trigger = CronTrigger(
                    second=cron_parts[0],
                    minute=cron_parts[1],
                    hour=cron_parts[2],
                    day=cron_parts[3],
                    month=cron_parts[4],
                    day_of_week=cron_parts[5],
                    timezone=timezone
                )
            elif len(cron_parts) == 5:
                # 5位格式：分 时 日 月 星期（标准 crontab 格式）
                trigger = CronTrigger.from_crontab(cron_expression, timezone=timezone)
            else:
                raise ValueError(f"Cron 表达式格式错误，应为5位或6位: {cron_expression}")
            
            # 添加任务到调度器
            self.scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                id=job_id,
                name=task_name,
                args=[task_id, command, parameters, working_directory, 
                      environment_vars, timeout_seconds, max_retries, retry_interval],
                replace_existing=True
            )
            
            # 注册到任务表
            self.task_registry[task_id] = job_id
            
            # 计算下次执行时间
            next_run_time = self._get_next_run_time(cron_expression, timezone)
            
            # 更新数据库中的下次执行时间
            await self._update_next_run_time(task_id, next_run_time)
            
            logger.info(f"✅ 任务已添加: {task_name} [ID={task_id}, job_id={job_id}]")
            logger.info(f"   下次执行时间: {next_run_time}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ 添加任务失败 [{task_name}]: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def remove_task(self, task_id: int) -> bool:
        """
        从调度器移除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功移除
        """
        try:
            job_id = self.task_registry.get(task_id)
            if not job_id:
                logger.warning(f"⚠️ 任务不存在于调度器中: task_id={task_id}")
                return False
            
            # 从调度器移除
            self.scheduler.remove_job(job_id)
            
            # 从注册表移除
            del self.task_registry[task_id]
            
            logger.info(f"✅ 任务已移除: task_id={task_id}, job_id={job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 移除任务失败 [task_id={task_id}]: {str(e)}")
            return False
    
    async def pause_task(self, task_id: int) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功暂停
        """
        try:
            job_id = self.task_registry.get(task_id)
            if not job_id:
                logger.warning(f"⚠️ 任务不存在: task_id={task_id}")
                return False
            
            self.scheduler.pause_job(job_id)
            logger.info(f"⏸️ 任务已暂停: task_id={task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 暂停任务失败 [task_id={task_id}]: {str(e)}")
            return False
    
    async def resume_task(self, task_id: int) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功恢复
        """
        try:
            job_id = self.task_registry.get(task_id)
            if not job_id:
                logger.warning(f"⚠️ 任务不存在: task_id={task_id}")
                return False
            
            self.scheduler.resume_job(job_id)
            logger.info(f"▶️ 任务已恢复: task_id={task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 恢复任务失败 [task_id={task_id}]: {str(e)}")
            return False
    
    def _execute_task_wrapper(
        self,
        task_id: int,
        command: str,
        parameters: Optional[Dict[str, Any]],
        working_directory: Optional[str],
        environment_vars: Optional[Dict[str, str]],
        timeout_seconds: int,
        max_retries: int,
        retry_interval: int
    ):
        """
        任务执行包装器（供 APScheduler 调用）
        注意：这是一个同步方法，会在后台线程中执行
        """
        try:
            # 获取当前事件循环，如果没有则创建新的
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 在事件循环中执行异步任务
            loop.run_until_complete(
                self._execute_task_async(
                    task_id, command, parameters, working_directory,
                    environment_vars, timeout_seconds, max_retries, retry_interval
                )
            )
        except Exception as e:
            logger.error(f"❌ 定时任务执行失败: task_id={task_id}, error={str(e)}")
            logger.error(traceback.format_exc())
    
    async def execute_task_now(
        self,
        task_id: int,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        working_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        retry_interval: int = 60
    ) -> Dict[str, Any]:
        """
        立即执行任务（不等待定时触发）
        注意：使用 create_task 在后台执行，不阻塞主线程
        
        Args:
            task_id: 任务ID
            command: 执行命令
            parameters: 任务参数
            working_directory: 工作目录
            environment_vars: 环境变量
            timeout_seconds: 超时时间
            max_retries: 最大重试次数
            retry_interval: 重试间隔
            
        Returns:
            执行信息（包含 execution_id）
        """
        logger.info(f"🚀 立即执行任务: task_id={task_id}")
        
        # 生成 execution_id
        execution_id = str(uuid.uuid4())
        
        # 在后台异步执行，不阻塞
        task = asyncio.create_task(
            self._execute_task_async(
                task_id, command, parameters, working_directory,
                environment_vars, timeout_seconds, max_retries, retry_interval
            )
        )
        
        # 添加到后台任务集合
        self.background_tasks.add(task)
        
        # 任务完成后从集合中移除
        task.add_done_callback(lambda t: self.background_tasks.discard(t))
        
        # 立即返回，不等待任务完成
        logger.info(f"✅ 任务已提交到后台执行: task_id={task_id}, execution_id={execution_id}")
        
        return {
            'success': True,
            'message': '任务已开始执行',
            'execution_id': execution_id,
            'task_id': task_id
        }
    
    async def _execute_task_async(
        self,
        task_id: int,
        command: str,
        parameters: Optional[Dict[str, Any]],
        working_directory: Optional[str],
        environment_vars: Optional[Dict[str, str]],
        timeout_seconds: int,
        max_retries: int,
        retry_interval: int
    ) -> Dict[str, Any]:
        """
        异步任务执行逻辑
        
        Returns:
            执行结果字典
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.info(f"🎯 开始执行任务: task_id={task_id}, execution_id={execution_id}")
        
        try:
            # 更新任务状态为 running
            await self._update_task_status(task_id, 'running')
            
            # 记录任务开始执行
            await self.monitor.record_start(task_id, execution_id)
            
            # 检查是否被取消
            if asyncio.current_task().cancelled():
                logger.info(f"⚠️ 任务被取消: task_id={task_id}")
                await self._update_task_status(task_id, 'enabled')
                raise asyncio.CancelledError()
            
            # 执行任务（带重试机制）
            result = await self.executor.execute(
                task_id=task_id,
                execution_id=execution_id,
                command=command,
                parameters=parameters,
                working_directory=working_directory,
                environment_vars=environment_vars,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                retry_interval=retry_interval
            )
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 记录执行结果
            await self.monitor.record_finish(
                task_id=task_id,
                execution_id=execution_id,
                success=result['success'],
                duration_ms=duration_ms,
                output=result.get('output'),
                error=result.get('error')
            )
            
            # 根据执行结果更新任务状态
            if result['success']:
                # 成功，恢复为 enabled
                await self._update_task_status(task_id, 'enabled')
            else:
                # 失败，设为 error
                await self._update_task_status(task_id, 'error')
            
            logger.info(f"✅ 任务执行完成: task_id={task_id}, 耗时={duration_ms}ms")
            
            return result
        
        except asyncio.CancelledError:
            # 任务被取消
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.warning(f"⚠️ 任务被取消: task_id={task_id}, 已运行={duration_ms}ms")
            
            # 恢复任务状态
            await self._update_task_status(task_id, 'enabled')
            
            return {
                'success': False,
                'error': '任务被取消',
                'execution_id': execution_id,
                'cancelled': True
            }
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            # 记录执行失败
            await self.monitor.record_finish(
                task_id=task_id,
                execution_id=execution_id,
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )
            
            # 更新任务状态为 error
            await self._update_task_status(task_id, 'error')
            
            logger.error(f"❌ 任务执行失败: task_id={task_id}, error={error_msg}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'execution_id': execution_id
            }
    
    def _validate_cron_expression(self, cron_expression: str) -> bool:
        """
        验证 Cron 表达式是否有效
        
        Args:
            cron_expression: Cron 表达式
            
        Returns:
            是否有效
        """
        try:
            croniter(cron_expression)
            return True
        except Exception:
            return False
    
    def _get_next_run_time(self, cron_expression: str, timezone: str = 'Asia/Shanghai') -> datetime:
        """
        计算下次执行时间
        
        Args:
            cron_expression: Cron 表达式
            timezone: 时区
            
        Returns:
            下次执行时间
        """
        try:
            cron = croniter(cron_expression, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"❌ 计算下次执行时间失败: {str(e)}")
            return datetime.now() + timedelta(hours=1)
    
    async def _update_task_status(self, task_id: int, status: str):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 任务状态 ('enabled', 'disabled', 'running', 'error')
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                query = "UPDATE cron_tasks SET status = %s WHERE id = %s"
                cursor.execute(query, (status, task_id))
            logger.info(f"📝 更新任务状态: task_id={task_id}, status={status}")
        except Exception as e:
            logger.error(f"❌ 更新任务状态失败: task_id={task_id}, error={str(e)}")
    
    async def _update_next_run_time(self, task_id: int, next_run_time: datetime):
        """
        更新数据库中的下次执行时间
        
        Args:
            task_id: 任务ID
            next_run_time: 下次执行时间
        """
        try:
            db = DatabaseConnection()
            with db.get_cursor() as cursor:
                query = "UPDATE cron_tasks SET next_run_at = %s WHERE id = %s"
                cursor.execute(query, (next_run_time, task_id))
        except Exception as e:
            logger.error(f"❌ 更新下次执行时间失败 [task_id={task_id}]: {str(e)}")
    
    def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        job_id = self.task_registry.get(task_id)
        if not job_id:
            return None
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        return {
            'job_id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time,
            'trigger': str(job.trigger),
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            任务信息列表
        """
        jobs = self.scheduler.get_jobs()
        return [
            {
                'job_id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger),
            }
            for job in jobs
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取调度器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'is_running': self.is_running,
            'total_tasks': len(self.task_registry),
            'scheduler_state': self.scheduler.state,
            'monitor_stats': self.monitor.get_stats()
        }
