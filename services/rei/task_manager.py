"""
REI 订单同步后台任务管理器
支持异步任务队列、进度追踪和WebSocket通知
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import traceback
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskManager:
    """后台任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 3  # 最大并发任务数
        self.task_queue = asyncio.Queue()
        self.worker_tasks = []
        self.is_running = False
    
    async def start(self):
        """启动任务管理器"""
        if self.is_running:
            return
        
        self.is_running = True
        print(f"🚀 任务管理器启动，最大并发数: {self.max_concurrent_tasks}")
        
        # 启动工作协程
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(worker)
    
    async def stop(self):
        """停止任务管理器"""
        self.is_running = False
        
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            task.cancel()
        
        # 停止工作协程
        for worker in self.worker_tasks:
            worker.cancel()
        
        # 等待所有工作协程结束
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        print("⏹️ 任务管理器已停止")
    
    async def _worker(self, worker_id: int):
        """工作协程，从队列中取任务执行"""
        print(f"👷 Worker {worker_id} 启动")
        
        while self.is_running:
            try:
                # 从队列获取任务
                task_id, func, args, kwargs = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                print(f"👷 Worker {worker_id} 开始执行任务: {task_id}")
                
                # 更新任务状态
                self.tasks[task_id]['status'] = TaskStatus.RUNNING.value
                self.tasks[task_id]['started_at'] = datetime.now().isoformat()
                
                try:
                    # 执行任务
                    result = await func(*args, **kwargs)
                    
                    # 任务成功
                    self.tasks[task_id]['status'] = TaskStatus.COMPLETED.value
                    self.tasks[task_id]['result'] = result
                    self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                    
                    print(f"✅ Worker {worker_id} 完成任务: {task_id}")
                
                except Exception as e:
                    # 任务失败
                    self.tasks[task_id]['status'] = TaskStatus.FAILED.value
                    self.tasks[task_id]['error'] = str(e)
                    self.tasks[task_id]['traceback'] = traceback.format_exc()
                    self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                    
                    print(f"❌ Worker {worker_id} 任务失败: {task_id}, 错误: {e}")
                
                finally:
                    # 标记队列任务完成
                    self.task_queue.task_done()
                    
                    # 从运行中任务列表移除
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
            
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except asyncio.CancelledError:
                print(f"👷 Worker {worker_id} 被取消")
                break
            except Exception as e:
                print(f"❌ Worker {worker_id} 发生错误: {e}")
                traceback.print_exc()
    
    def create_task(
        self,
        func: Callable,
        *args,
        task_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        创建后台任务
        
        Args:
            func: 异步函数
            task_name: 任务名称
            *args: 函数参数
            **kwargs: 函数关键字参数
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        self.tasks[task_id] = {
            'id': task_id,
            'name': task_name or func.__name__,
            'status': TaskStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None,
            'progress': {
                'current': 0,
                'total': 0,
                'percentage': 0,
                'message': '等待开始...'
            }
        }
        
        # 添加到队列
        asyncio.create_task(self.task_queue.put((task_id, func, args, kwargs)))
        
        print(f"📋 创建任务: {task_id} - {task_name}")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        message: str = "",
        account_id: Optional[int] = None
    ):
        """更新任务进度"""
        if task_id in self.tasks:
            percentage = int((current / total * 100)) if total > 0 else 0
            self.tasks[task_id]['progress'] = {
                'current': current,
                'total': total,
                'percentage': percentage,
                'message': message
            }
            
            # 通过WebSocket推送进度
            if account_id:
                try:
                    import asyncio
                    from services.websocket.websocket_service import WebSocketService
                    
                    # 创建推送任务
                    asyncio.create_task(WebSocketService.push_to_account(account_id, {
                        'type': 'task_progress',
                        'task_id': task_id,
                        'current': current,
                        'total': total,
                        'percentage': percentage,
                        'message': message
                    }))
                except Exception as e:
                    print(f"⚠️ 推送进度失败: {e}")
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务"""
        return self.tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.tasks[task_id]['status'] = TaskStatus.CANCELLED.value
            self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
            return True
        return False


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
